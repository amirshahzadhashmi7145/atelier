"""Claim one ready task and let its role write inside a branch.

The model proposes file contents. This module decides whether those
paths are legal, whether the run still has budget, and whether the
declared tests pass before a commit. A failed run is saved. Uncommitted
writes are discarded so the branch stays clean.
"""

from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.agents.developer import implement_prompt
from app.agents.qa import review_prompt
from app.config import Settings
from app.domain.budget import BudgetExceeded, RunBudget
from app.domain.control import require_active, require_agents
from app.domain.pull_request import CheckLine, compose
from app.domain.qa import Finding, decide_untestable, judge
from app.domain.gates import is_automatic
from app.domain.spend import require_spend_room, run_tokens, spend_exceeds_estimate, tokens_used
from app.domain.schedule import ClaimCandidate, choose_next
from app.domain.task_machine import TaskState, require_amendable, require_reassignable, transition
from app.domain.validation import ALLOWED_ZONES
from app.domain.zones import require_inside_zone
from app.errors import DomainError
from app.gateway.base import LlmClient
from app.models import (
    AgentRun,
    CheckRun,
    CriterionFinding,
    Defect,
    Event,
    GateDecision,
    Project,
    PullRequest,
    Task,
)
from app.services.checks import CheckResult, SandboxOptions, run_checks
from app.services import github as github_api
from app.schemas import (
    CheckOut,
    DefectOut,
    EventOut,
    FindingOut,
    ProjectSnapshot,
    PullRequestOut,
    RunOut,
    TaskDetailOut,
    TaskOut,
)
from app.services.planning import PlanningService, new_id
from app.services.workspace import Workspace

_DIFF_LIMIT = 20_000


class _Write(BaseModel):
    path: str = Field(min_length=1)
    content: str


class _Implement(BaseModel):
    summary: str = Field(min_length=1)
    done: bool = False
    writes: list[_Write] = []


class _FindingIn(BaseModel):
    criterion_key: str = Field(min_length=1)
    result: str
    note: str = ""
    reproduction: str = ""
    observed: str = ""
    expected: str = ""


class _ReviewIn(BaseModel):
    findings: list[_FindingIn] = Field(min_length=1)


class ExecutionService:
    def __init__(self, session: Session, llm: LlmClient, settings: Settings) -> None:
        self.session = session
        self.llm = llm
        self.settings = settings
        self.planning = PlanningService(session, llm, settings)

    def run_next(self, project_id: str) -> ProjectSnapshot:
        project = self.planning._project(project_id)
        require_active(paused=bool(project.paused))
        require_agents(agents_revoked=bool(project.agents_revoked))
        self._guard_spend(project)
        task = self._claim(project)
        try:
            self._execute(project, task)
        except DomainError as exc:
            self._fail(project, task, exc.message)
        return self.planning.snapshot(project.id)

    def review(self, project_id: str, task_id: str) -> ProjectSnapshot:
        project = self.planning._project(project_id)
        require_active(paused=bool(project.paused))
        require_agents(agents_revoked=bool(project.agents_revoked))
        self._guard_spend(project)
        task = self._task(project, task_id)
        if task.state != TaskState.IN_REVIEW.value:
            raise DomainError("Only a task that is in review can be checked.")
        if not task.branch_name:
            raise DomainError("This task has no branch to review.")
        criteria = self._criteria(project, task)
        workspace = Workspace(self._root(project))
        try:
            diff = workspace.diff(task.branch_name)
            workspace.start_branch(task.branch_name)
        except RuntimeError as exc:
            raise DomainError(f"The branch diff could not be read: {exc}") from exc
        sandbox = self._sandbox()
        checks = run_checks(
            workspace.root,
            project.test_strategy,
            self.settings.check_timeout_seconds,
            sandbox=sandbox,
        )
        self._replace_checks(project, task, checks)
        failed_checks = [item for item in checks if item.exit_code != 0]
        if failed_checks:
            self._send_back(
                project,
                task,
                [
                    (
                        f"tests/{item.tier}",
                        item.command,
                        item.excerpt or f"The command exited {item.exit_code}.",
                        "The command exits 0.",
                    )
                    for item in failed_checks
                ],
                "; ".join(f"{item.tier} exited {item.exit_code}" for item in failed_checks)
                + ". The task is ready for another attempt.",
            )
            return self.planning.snapshot(project.id)
        rendered = "\n".join(
            f"- {item.tier}: {item.command} exited {item.exit_code}\n  {item.excerpt}" for item in checks
        )
        system, user = review_prompt(
            task_key=task.key,
            title=task.title,
            criteria=criteria,
            checks=rendered,
            diff=diff,
        )
        result = self.llm.complete_json(purpose="qa", system=system, user=user)
        self._record_run(
            project,
            task,
            result.provider,
            result.model,
            result.input_tokens,
            result.output_tokens,
            role="qa",
            purpose="qa",
        )
        parsed = self._parse_review(result.data)
        findings = [
            Finding(
                criterion_key=item.criterion_key,
                result=item.result,
                note=item.note,
                reproduction=item.reproduction,
                observed=item.observed,
                expected=item.expected,
            )
            for item in parsed.findings
        ]
        verdict = judge([key for key, _statement in criteria], findings)
        self.session.execute(delete(CriterionFinding).where(CriterionFinding.task_id == task.id))
        for item in findings:
            self.session.add(
                CriterionFinding(
                    id=new_id("find"),
                    project_id=project.id,
                    task_id=task.id,
                    criterion_key=item.criterion_key,
                    result=item.result,
                    note=item.note.strip(),
                )
            )
        if verdict == "pass":
            task.state, task.retry_count = self._move(task, TaskState.GATED)
            self.planning._event(
                project,
                "qa.passed",
                actor_kind="agent",
                actor_role="qa",
                task_id=task.id,
                payload={"key": task.key, "summary": "Every criterion passed."},
            )
            if is_automatic(project.gate_policy, "merge"):
                return self.accept(project_id, task_id, actor_kind="system")
        elif verdict == "fail":
            failed = [item for item in findings if item.result == "fail"]
            self._send_back(
                project,
                task,
                [
                    (
                        item.criterion_key,
                        item.reproduction.strip(),
                        item.observed.strip(),
                        item.expected.strip(),
                    )
                    for item in failed
                ],
                f"{len(failed)} criteria failed. The task is ready for another attempt.",
            )
        else:
            flagged = [item.criterion_key for item in findings if item.result == "untestable"]
            self.planning._event(
                project,
                "qa.untestable",
                actor_kind="agent",
                actor_role="qa",
                task_id=task.id,
                payload={
                    "key": task.key,
                    "summary": "Could not test " + ", ".join(flagged) + ".",
                },
            )
        return self.planning.snapshot(project.id)

    def accept(self, project_id: str, task_id: str, *, actor_kind: str = "user") -> ProjectSnapshot:
        project = self.planning._project(project_id)
        require_active(paused=bool(project.paused))
        task = self._task(project, task_id)
        if task.state != TaskState.GATED.value:
            raise DomainError("Only a task that passed review can be accepted.")
        if not task.branch_name:
            raise DomainError("This task has no branch to merge.")
        workspace = Workspace(self._root(project))
        try:
            workspace.rebase_onto_main(task.branch_name)
        except RuntimeError as exc:
            self._send_back(
                project,
                task,
                [
                    (
                        "merge/rebase",
                        "git rebase main",
                        (str(exc).strip() or "The rebase stopped with a conflict."),
                        "The task branch rebases onto main cleanly.",
                    )
                ],
                "The branch could not be rebased onto main. The task is ready for another attempt.",
                event_type="merge.rebase_failed",
                actor_kind="system",
                actor_role=None,
            )
            return self.planning.snapshot(project.id)
        checks = run_checks(
            workspace.root,
            project.test_strategy,
            self.settings.check_timeout_seconds,
            sandbox=self._sandbox(),
        )
        self._replace_checks(project, task, checks)
        failed_checks = [item for item in checks if item.exit_code != 0]
        if failed_checks:
            self._send_back(
                project,
                task,
                [
                    (
                        f"tests/{item.tier}",
                        item.command,
                        item.excerpt or f"The command exited {item.exit_code}.",
                        "The command exits 0.",
                    )
                    for item in failed_checks
                ],
                "; ".join(f"{item.tier} exited {item.exit_code}" for item in failed_checks)
                + ". Checks failed after rebase. The task is ready for another attempt.",
                event_type="merge.checks_failed",
                actor_kind="system",
                actor_role=None,
            )
            return self.planning.snapshot(project.id)
        try:
            workspace.merge(task.branch_name, task.key)
        except RuntimeError as exc:
            raise DomainError(f"The branch could not be merged: {exc}") from exc
        task.state, task.retry_count = self._move(task, TaskState.DONE)
        for item in project.pull_requests:
            if item.task_id == task.id and item.state == "open":
                item.state = "merged"
        merge_note = "Approved by automatic policy." if actor_kind == "system" else None
        self.session.add(
            GateDecision(
                id=new_id("gate"),
                project_id=project.id,
                gate="merge",
                decision="approved",
                note=merge_note,
            )
        )
        self.planning._event(
            project,
            "gate.decided",
            actor_kind=actor_kind,
            task_id=task.id,
            payload={"gate": "merge", "decision": "approved", "note": merge_note, "mode": actor_kind},
        )
        self.planning._event(
            project,
            "task.accepted",
            actor_kind=actor_kind,
            task_id=task.id,
            payload={"key": task.key, "branch": task.branch_name},
        )
        self._unblock(project)
        return self.planning.snapshot(project.id)

    def resume(self, project_id: str, task_id: str) -> ProjectSnapshot:
        """A person returns an escalated task to the ready queue."""

        project = self.planning._project(project_id)
        require_active(paused=bool(project.paused))
        task = self._task(project, task_id)
        if task.state != TaskState.ESCALATED.value:
            raise DomainError("Only an escalated task can be resumed.")
        task.state, task.retry_count = self._move(task, TaskState.READY)
        task.retry_count = 0
        self.planning._event(
            project,
            "task.resumed",
            actor_kind="user",
            task_id=task.id,
            payload={
                "key": task.key,
                "summary": "A person returned the escalated task to ready.",
            },
        )
        return self.planning.snapshot(project.id)

    def task_detail(self, project_id: str, task_id: str) -> TaskDetailOut:
        """Drill from a task to its runs, checks, PR, and branch diff."""

        self.session.flush()
        project = self.planning._project(project_id)
        self.session.expire(project)
        task = self._task(project, task_id)
        key_by_id = {item.id: item.key for item in project.tasks}
        task_out = TaskOut(
            id=task.id,
            key=task.key,
            title=task.title,
            description=task.description,
            zone=task.zone,
            state=task.state,
            size=task.size,
            estimate_tokens=int(task.estimate_tokens or 0),
            requirement_keys=list(task.requirement_keys),
            depends_on=[key_by_id[dep.depends_on_id] for dep in task.dependencies],
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            branch_name=task.branch_name,
        )
        runs = [
            RunOut(
                id=item.id,
                role=item.role,
                purpose=item.purpose,
                provider=item.provider,
                model=item.model,
                input_tokens=item.input_tokens,
                output_tokens=item.output_tokens,
                task_id=item.task_id,
            )
            for item in sorted(project.runs, key=lambda item: item.created_at, reverse=True)
            if item.task_id == task.id
        ]
        checks = [
            CheckOut(
                id=item.id,
                task_id=item.task_id,
                tier=item.tier,
                command=item.command,
                exit_code=item.exit_code,
                excerpt=item.excerpt,
            )
            for item in project.checks
            if item.task_id == task.id
        ]
        findings = [
            FindingOut(
                id=item.id,
                task_id=item.task_id,
                criterion_key=item.criterion_key,
                result=item.result,
                note=item.note,
            )
            for item in project.findings
            if item.task_id == task.id
        ]
        defects = [
            DefectOut(
                id=item.id,
                task_id=item.task_id,
                criterion_key=item.criterion_key,
                reproduction=item.reproduction,
                observed=item.observed,
                expected=item.expected,
            )
            for item in project.defects
            if item.task_id == task.id
        ]
        pull_requests = [
            PullRequestOut(
                id=item.id,
                task_id=item.task_id,
                branch_name=item.branch_name,
                title=item.title,
                body=item.body,
                state=item.state,
                number=item.number,
                url=item.url,
            )
            for item in project.pull_requests
            if item.task_id == task.id
        ]
        events = [
            EventOut(
                id=item.id,
                type=item.type,
                actor_kind=item.actor_kind,
                actor_role=item.actor_role,
                payload=item.payload,
                input_tokens=item.input_tokens,
                output_tokens=item.output_tokens,
                occurred_at=item.occurred_at,
            )
            for item in sorted(project.events, key=lambda item: item.occurred_at, reverse=True)
            if item.task_id == task.id
        ]
        diff: str | None = None
        truncated = False
        if task.branch_name:
            try:
                text = Workspace(self._root(project)).diff(task.branch_name)
            except RuntimeError:
                text = ""
            if text:
                if len(text) > _DIFF_LIMIT:
                    text = text[:_DIFF_LIMIT] + "\n… truncated …\n"
                    truncated = True
                diff = text
        return TaskDetailOut(
            task=task_out,
            runs=runs,
            checks=checks,
            findings=findings,
            defects=defects,
            pull_requests=pull_requests,
            events=events,
            diff=diff,
            diff_truncated=truncated,
        )

    def amend(
        self,
        project_id: str,
        task_id: str,
        *,
        path: str,
        content: str,
        summary: str,
    ) -> TaskDetailOut:
        """A person edits a file on the task branch; the next run sees it."""

        project = self.planning._project(project_id)
        require_active(paused=bool(project.paused))
        task = self._task(project, task_id)
        require_amendable(task.state, branch_name=task.branch_name)
        relative = path.strip().replace("\\", "/").lstrip("./")
        if not relative:
            raise DomainError("A file path is required.", status_code=422)
        rules = [(rule.glob, rule.zone) for rule in project.ownership]
        require_inside_zone(relative, task.zone, rules)
        workspace = Workspace(self._root(project))
        try:
            workspace.ensure()
            workspace.start_branch(task.branch_name)
            workspace.commit(task.key, summary.strip(), [(relative, content)])
        except RuntimeError as exc:
            raise DomainError(f"The branch could not be amended: {exc}") from exc
        self.planning._event(
            project,
            "task.branch_amended",
            actor_kind="user",
            task_id=task.id,
            payload={
                "key": task.key,
                "path": relative,
                "summary": summary.strip(),
                "branch": task.branch_name,
            },
        )
        return self.task_detail(project_id, task_id)

    def reassign(self, project_id: str, task_id: str, zone: str) -> ProjectSnapshot:
        """A person moves a waiting task to another ownership zone."""

        project = self.planning._project(project_id)
        require_active(paused=bool(project.paused))
        task = self._task(project, task_id)
        require_reassignable(task.state)
        next_zone = zone.strip()
        if next_zone not in ALLOWED_ZONES:
            raise DomainError(
                f"Zone '{next_zone}' is not assignable. "
                "Use backend, frontend, or ai_engineer.",
                status_code=422,
            )
        known_zones = {rule.zone for rule in project.ownership}
        if next_zone not in known_zones:
            raise DomainError(
                f"Zone '{next_zone}' is not in this project's ownership map.",
                status_code=422,
            )
        if next_zone == task.zone:
            return self.planning.snapshot(project.id)
        previous = task.zone
        task.zone = next_zone
        self.planning._event(
            project,
            "task.reassigned",
            actor_kind="user",
            task_id=task.id,
            payload={
                "key": task.key,
                "from_zone": previous,
                "to_zone": next_zone,
                "summary": f"{task.key} moved from {previous} to {next_zone}.",
            },
        )
        return self.planning.snapshot(project.id)

    def resolve_untestable(self, project_id: str, task_id: str, decision: str) -> ProjectSnapshot:
        """A person settles criteria the review could not execute."""

        project = self.planning._project(project_id)
        require_active(paused=bool(project.paused))
        task = self._task(project, task_id)
        if task.state != TaskState.IN_REVIEW.value:
            raise DomainError("Only a task that is in review can be decided.")
        stored = [
            item
            for item in project.findings
            if item.task_id == task.id
        ]
        findings = [
            Finding(
                criterion_key=item.criterion_key,
                result=item.result,
                note=item.note,
            )
            for item in stored
        ]
        choice = decide_untestable(findings, decision)
        flagged = [item for item in stored if item.result == "untestable"]
        if choice == "waive":
            for item in flagged:
                item.result = "waived"
            task.state, task.retry_count = self._move(task, TaskState.GATED)
            self.planning._event(
                project,
                "qa.waived",
                actor_kind="user",
                task_id=task.id,
                payload={
                    "key": task.key,
                    "summary": "Accepted without testing "
                    + ", ".join(item.criterion_key for item in flagged)
                    + ".",
                },
            )
            return self.planning.snapshot(project.id)
        self._send_back(
            project,
            task,
            [
                (
                    item.criterion_key,
                    item.note.strip() or "The criterion could not be tested.",
                    "Not exercised in this review.",
                    "A person could verify the criterion, or the next attempt makes it testable.",
                )
                for item in flagged
            ],
            "A person rejected "
            + ", ".join(item.criterion_key for item in flagged)
            + ". The task is ready for another attempt.",
            event_type="qa.rejected_untestable",
            actor_kind="user",
            actor_role=None,
        )
        return self.planning.snapshot(project.id)

    def _claim(self, project: Project) -> Task:
        chosen = choose_next(
            [
                ClaimCandidate(task.key, task.state, task.zone, task.sort_order)
                for task in project.tasks
            ]
        )
        if chosen is None:
            raise DomainError("No task is ready to run.")
        task = next(item for item in project.tasks if item.key == chosen)
        # The state change is committed before any file is written, so a second
        # click sees the task as in progress and does not start it again.
        claimed = self.session.execute(
            update(Task)
            .where(Task.id == task.id, Task.state == TaskState.READY.value)
            .values(state=TaskState.IN_PROGRESS.value)
        )
        if claimed.rowcount != 1:
            raise DomainError("That task was already claimed.")
        self.session.commit()
        task.state = TaskState.IN_PROGRESS.value
        self.planning._event(
            project,
            "task.claimed",
            actor_kind="system",
            task_id=task.id,
            payload={"key": task.key, "zone": task.zone},
        )
        return task

    def _execute(self, project: Project, task: Task) -> None:
        workspace = Workspace(self._root(project))
        try:
            workspace.ensure()
            branch = f"task/{task.key}"
            workspace.start_branch(branch)
        except RuntimeError as exc:
            raise DomainError(f"The workspace could not be prepared: {exc}") from exc
        task.branch_name = branch
        rules = [(rule.glob, rule.zone) for rule in project.ownership]
        budget = RunBudget(
            max_iterations=self.settings.run_max_iterations,
            max_seconds=self.settings.run_max_seconds,
            max_tokens=self.settings.run_max_tokens,
        )
        previous: tuple | None = None
        summary = ""
        passed_checks: list[CheckResult] = []
        rework = self._rework_text(task)
        while True:
            budget.charge(0)
            ownership = "\n".join(f"{glob} -> {zone}" for glob, zone in rules)
            system, user = implement_prompt(
                zone=task.zone,
                task_key=task.key,
                title=task.title,
                description=task.description,
                ownership=ownership,
                rework=rework,
            )
            result = self.llm.complete_json(purpose="implement", system=system, user=user)
            run_id = self._record_run(
                project, task, result.provider, result.model, result.input_tokens, result.output_tokens
            )
            self._note_tokens(budget, result.input_tokens + result.output_tokens)
            parsed = self._parse(result.data)
            signature = tuple(sorted((item.path, item.content) for item in parsed.writes))
            if signature == previous:
                raise DomainError("The agent repeated the same change. The run was stopped.")
            previous = signature
            for item in parsed.writes:
                require_inside_zone(item.path, task.zone, rules)
            if not parsed.done:
                continue
            if not parsed.writes:
                raise DomainError("The agent finished without writing a file.", status_code=422)
            summary = parsed.summary.strip()
            writes = [(item.path, item.content) for item in parsed.writes]
            try:
                workspace.apply(writes)
            except RuntimeError as exc:
                raise DomainError(f"The branch could not be written: {exc}") from exc
            try:
                checks = run_checks(
                    workspace.root,
                    project.test_strategy,
                    self.settings.check_timeout_seconds,
                    sandbox=self._sandbox(),
                )
            except DomainError:
                try:
                    workspace.discard()
                except RuntimeError as exc:
                    raise DomainError(f"The failed change could not be discarded: {exc}") from exc
                raise
            self._replace_checks(project, task, checks)
            failed_checks = [item for item in checks if item.exit_code != 0]
            if failed_checks:
                try:
                    workspace.discard()
                except RuntimeError as exc:
                    raise DomainError(f"The failed change could not be discarded: {exc}") from exc
                for item in failed_checks:
                    self.session.add(
                        Defect(
                            id=new_id("def"),
                            project_id=project.id,
                            task_id=task.id,
                            criterion_key=f"tests/{item.tier}",
                            reproduction=item.command,
                            observed=item.excerpt or f"The command exited {item.exit_code}.",
                            expected="The command exits 0.",
                        )
                    )
                raise DomainError(
                    "; ".join(f"{item.tier} exited {item.exit_code}" for item in failed_checks)
                    + ". Declared tests must pass before a commit."
                )
            try:
                workspace.commit_staged(task.key, summary, role=task.zone, run_id=run_id)
            except RuntimeError as exc:
                raise DomainError(f"The branch could not be committed: {exc}") from exc
            passed_checks = checks
            break
        task.state, task.retry_count = self._move(task, TaskState.IN_REVIEW)
        self.planning._event(
            project,
            "task.in_review",
            actor_kind="agent",
            actor_role=task.zone,
            task_id=task.id,
            payload={"key": task.key, "branch": branch, "summary": summary},
        )
        self._open_pull_request(project, task, workspace, summary, passed_checks)

    def _sandbox(self) -> SandboxOptions | None:
        if not self.settings.check_sandbox:
            return None
        return SandboxOptions(
            image=self.settings.sandbox_image,
            memory=self.settings.sandbox_memory,
            cpus=self.settings.sandbox_cpus,
            pids_limit=self.settings.sandbox_pids_limit,
        )

    def _guard_spend(self, project: Project) -> None:
        spent = tokens_used(project.runs)
        ceiling = project.spend_ceiling_tokens
        if spent < ceiling:
            return
        if not project.paused:
            project.paused = True
            self.planning._event(
                project,
                "project.spend_ceiling",
                actor_kind="system",
                payload={
                    "spend_tokens": spent,
                    "spend_ceiling_tokens": ceiling,
                    "summary": f"Spend reached {spent} of {ceiling} tokens. The project was paused.",
                },
            )
            # Persist the pause even though the refused step will roll back.
            self.session.commit()
        require_spend_room(spent=spent, ceiling=ceiling)

    def _open_pull_request(
        self,
        project: Project,
        task: Task,
        workspace: Workspace,
        summary: str,
        checks: list[CheckResult],
    ) -> None:
        if any(item.task_id == task.id and item.state == "open" for item in project.pull_requests):
            return
        if not task.branch_name:
            raise DomainError("This task has no branch for a pull request.")
        draft = compose(
            task_key=task.key,
            title=task.title,
            summary=summary,
            requirement_keys=list(task.requirement_keys),
            checks=[
                CheckLine(
                    tier=item.tier,
                    command=item.command,
                    exit_code=item.exit_code,
                    excerpt=item.excerpt,
                )
                for item in checks
            ],
            assumptions=[item.statement for item in project.assumptions],
        )
        record = PullRequest(
            id=new_id("pr"),
            project_id=project.id,
            task_id=task.id,
            branch_name=task.branch_name,
            title=draft.title,
            body=draft.body,
            state="open",
        )
        if project.github_repo and self.settings.github_token.strip():
            remote = (
                f"https://x-access-token:{self.settings.github_token}"
                f"@github.com/{project.github_repo}.git"
            )
            try:
                workspace.push(remote, task.branch_name)
            except RuntimeError as exc:
                raise DomainError(f"The branch could not be pushed: {exc}") from exc
            remote_pr = github_api.open_pull_request(
                api_url=self.settings.github_api_url,
                token=self.settings.github_token,
                repo=project.github_repo,
                title=draft.title,
                body=draft.body,
                head=task.branch_name,
            )
            record.number = remote_pr.number
            record.url = remote_pr.url
        self.session.add(record)
        self.planning._event(
            project,
            "pr.opened",
            actor_kind="system",
            task_id=task.id,
            payload={
                "key": task.key,
                "branch": task.branch_name,
                "title": draft.title,
                "number": record.number,
                "url": record.url,
                "summary": draft.title,
            },
        )

    def _fail(self, project: Project, task: Task, cause: str) -> None:
        task.state, task.retry_count = self._move(task, TaskState.FAILED)
        self.session.flush()
        self.session.expire(project, ["runs"])
        spent = sum(run_tokens(run) for run in project.runs if run.task_id == task.id)
        estimate = int(task.estimate_tokens or 0)
        overspend = spend_exceeds_estimate(
            spent=spent,
            estimate=estimate,
            multiple=self.settings.spend_estimate_multiple,
        )
        if overspend:
            task.state, task.retry_count = self._move(task, TaskState.ESCALATED)
            outcome = "escalated"
            self.planning._event(
                project,
                "task.spend_overspend",
                actor_kind="system",
                task_id=task.id,
                payload={
                    "key": task.key,
                    "spend_tokens": spent,
                    "estimate_tokens": estimate,
                    "multiple": self.settings.spend_estimate_multiple,
                    "summary": (
                        f"{task.key} spent {spent} tokens against an estimate of {estimate}. "
                        "It was escalated instead of retried."
                    ),
                },
            )
        else:
            try:
                task.state, task.retry_count = self._move(task, TaskState.READY)
                outcome = "ready"
            except DomainError:
                task.state, task.retry_count = self._move(task, TaskState.ESCALATED)
                outcome = "escalated"
        self.planning._event(
            project,
            "task.failed",
            actor_kind="system",
            task_id=task.id,
            payload={
                "key": task.key,
                "cause": cause,
                "outcome": outcome,
                "retry_count": task.retry_count,
                "spend_tokens": spent,
                "estimate_tokens": estimate,
            },
        )

    def _unblock(self, project: Project) -> None:
        done = {task.id for task in project.tasks if task.state == TaskState.DONE.value}
        for task in project.tasks:
            if task.state != TaskState.BLOCKED.value:
                continue
            waiting_on = [item.depends_on_id for item in task.dependencies]
            if waiting_on and all(dep in done for dep in waiting_on):
                task.state, task.retry_count = self._move(task, TaskState.READY)
                self.planning._event(
                    project,
                    "task.unblocked",
                    actor_kind="system",
                    task_id=task.id,
                    payload={"key": task.key},
                )

    def _move(self, task: Task, target: TaskState) -> tuple[str, int]:
        state, retries = transition(
            TaskState(task.state),
            target,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
        )
        return state.value, retries

    def _record_run(
        self,
        project: Project,
        task: Task,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        *,
        role: str | None = None,
        purpose: str = "implement",
    ) -> str:
        actor = role or task.zone
        before = tokens_used(project.runs)
        run = AgentRun(
            id=new_id("run"),
            project_id=project.id,
            task_id=task.id,
            role=actor,
            purpose=purpose,
            status="succeeded",
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self.session.add(run)
        self.session.flush()
        self.session.add(
            Event(
                id=new_id("evt"),
                project_id=project.id,
                type=f"agent.{purpose}",
                task_id=task.id,
                actor_kind="agent",
                actor_role=actor,
                run_id=run.id,
                payload={"provider": provider, "model": model},
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        )
        after = before + int(input_tokens) + int(output_tokens)
        self.planning._alert_spend_thresholds(project, before=before, after=after)
        return run.id

    def _replace_checks(self, project: Project, task: Task, checks: list[CheckResult]) -> None:
        self.session.execute(delete(CheckRun).where(CheckRun.task_id == task.id))
        for item in checks:
            self.session.add(
                CheckRun(
                    id=new_id("chk"),
                    project_id=project.id,
                    task_id=task.id,
                    tier=item.tier,
                    command=item.command,
                    exit_code=item.exit_code,
                    excerpt=item.excerpt,
                )
            )

    def _send_back(
        self,
        project: Project,
        task: Task,
        rows: list[tuple[str, str, str, str]],
        summary: str,
        *,
        event_type: str = "qa.failed",
        actor_kind: str = "agent",
        actor_role: str | None = "qa",
    ) -> None:
        for criterion_key, reproduction, observed, expected in rows:
            self.session.add(
                Defect(
                    id=new_id("def"),
                    project_id=project.id,
                    task_id=task.id,
                    criterion_key=criterion_key,
                    reproduction=reproduction,
                    observed=observed,
                    expected=expected,
                )
            )
        task.state, task.retry_count = self._move(task, TaskState.CHANGES_REQUESTED)
        task.state, task.retry_count = self._move(task, TaskState.READY)
        self.planning._event(
            project,
            event_type,
            actor_kind=actor_kind,
            actor_role=actor_role,
            task_id=task.id,
            payload={"key": task.key, "summary": summary},
        )

    def _criteria(self, project: Project, task: Task) -> list[tuple[str, str]]:
        wanted = set(task.requirement_keys)
        rows: list[tuple[str, str]] = []
        for requirement in sorted(project.requirements, key=lambda item: item.sort_order):
            if requirement.key not in wanted:
                continue
            for criterion in requirement.criteria:
                rows.append((f"{requirement.key}/{criterion.key}", criterion.statement))
        if not rows:
            raise DomainError("This task has no acceptance criteria to review.")
        return rows

    def _rework_text(self, task: Task) -> str:
        rows = self.session.scalars(select(Defect).where(Defect.task_id == task.id)).all()
        return "\n".join(
            f"{item.criterion_key}: expected {item.expected}; observed {item.observed}. Reproduce: {item.reproduction}"
            for item in rows
        )

    def _parse_review(self, data: dict) -> _ReviewIn:
        try:
            return _ReviewIn.model_validate(data)
        except ValidationError as exc:
            loc = ".".join(str(part) for part in exc.errors()[0]["loc"])
            raise DomainError(
                f"The model reply failed validation at '{loc}'. Nothing was recorded.",
                status_code=502,
            ) from exc

    def _note_tokens(self, budget: RunBudget, tokens: int) -> None:
        budget.tokens += tokens
        if budget.tokens > budget.max_tokens:
            raise BudgetExceeded("token")

    def _parse(self, data: dict) -> _Implement:
        try:
            return _Implement.model_validate(data)
        except ValidationError as exc:
            loc = ".".join(str(part) for part in exc.errors()[0]["loc"])
            raise DomainError(
                f"The model reply failed validation at '{loc}'. Nothing was written.",
                status_code=502,
            ) from exc

    def _task(self, project: Project, task_id: str) -> Task:
        for task in project.tasks:
            if task.id == task_id:
                return task
        raise DomainError("Task not found.", status_code=404)

    def _root(self, project: Project) -> Path:
        return Path(self.settings.workspaces_dir) / project.id
