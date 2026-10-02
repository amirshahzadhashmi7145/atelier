"""Claim one ready task and let its role write inside a branch.

The model proposes file contents. This module decides whether those
paths are legal, whether the run still has budget, and whether the
branch may be merged. A failed run is saved. It is not rolled back,
because the failure is the record a person needs to see.
"""

from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.agents.developer import implement_prompt
from app.agents.qa import review_prompt
from app.config import Settings
from app.domain.budget import BudgetExceeded, RunBudget
from app.domain.qa import Finding, judge
from app.domain.schedule import ClaimCandidate, choose_next
from app.domain.task_machine import TaskState, transition
from app.domain.zones import require_inside_zone
from app.errors import DomainError
from app.gateway.base import LlmClient
from app.models import AgentRun, CheckRun, CriterionFinding, Defect, Event, Project, Task
from app.services.checks import CheckResult, run_checks
from app.schemas import ProjectSnapshot
from app.services.planning import PlanningService, new_id
from app.services.workspace import Workspace


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
        self.planning = PlanningService(session, llm)

    def run_next(self, project_id: str) -> ProjectSnapshot:
        project = self.planning._project(project_id)
        task = self._claim(project)
        try:
            self._execute(project, task)
        except DomainError as exc:
            self._fail(project, task, exc.message)
        return self.planning.snapshot(project.id)

    def review(self, project_id: str, task_id: str) -> ProjectSnapshot:
        project = self.planning._project(project_id)
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
        checks = run_checks(workspace.root, project.test_strategy, self.settings.check_timeout_seconds)
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

    def accept(self, project_id: str, task_id: str) -> ProjectSnapshot:
        project = self.planning._project(project_id)
        task = self._task(project, task_id)
        if task.state != TaskState.GATED.value:
            raise DomainError("Only a task that passed review can be accepted.")
        if not task.branch_name:
            raise DomainError("This task has no branch to merge.")
        try:
            Workspace(self._root(project)).merge(task.branch_name, task.key)
        except RuntimeError as exc:
            raise DomainError(f"The branch could not be merged: {exc}") from exc
        task.state, task.retry_count = self._move(task, TaskState.DONE)
        self.planning._event(
            project,
            "task.accepted",
            actor_kind="user",
            task_id=task.id,
            payload={"key": task.key, "branch": task.branch_name},
        )
        self._unblock(project)
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
            self._record_run(project, task, result.provider, result.model, result.input_tokens, result.output_tokens)
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
            try:
                workspace.commit(task.key, summary, [(item.path, item.content) for item in parsed.writes])
            except RuntimeError as exc:
                raise DomainError(f"The branch could not be committed: {exc}") from exc
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

    def _fail(self, project: Project, task: Task, cause: str) -> None:
        task.state, task.retry_count = self._move(task, TaskState.FAILED)
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
            payload={"key": task.key, "cause": cause, "outcome": outcome, "retry_count": task.retry_count},
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
    ) -> None:
        actor = role or task.zone
        run = AgentRun(
            id=new_id("run"),
            project_id=project.id,
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

    def _send_back(self, project: Project, task: Task, rows: list[tuple[str, str, str, str]], summary: str) -> None:
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
            "qa.failed",
            actor_kind="agent",
            actor_role="qa",
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
