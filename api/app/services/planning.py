"""One project, walked from a sentence to a task graph.

Each public method is one step the dashboard can press. A step either
finishes and commits with the request, or raises DomainError and the
request rolls back. A bad model reply cannot leave half a plan behind.

The model proposes. This module disposes: it checks the stage, checks
the shape, then writes rows and an event.
"""

from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import pm
from app.config import Settings
from app.domain.control import require_active
from app.domain.graph import require_acyclic
from app.domain.plan_stage import PlanStage, next_actions, transition
from app.domain.spend import (
    DEFAULT_ALERT_THRESHOLDS,
    require_spend_room,
    thresholds_crossed,
    tokens_used,
)
from app.domain.task_machine import place
from app.domain.validation import check_task_shape, require_criteria, uncovered_requirements
from app.errors import DomainError
from app.gateway.base import LlmClient, LlmResult
from app.models import (
    AcceptanceCriterion,
    AgentRun,
    ArchitectureDecision,
    Assumption,
    Clarification,
    Event,
    GateDecision,
    OwnershipRule,
    Project,
    Requirement,
    Task,
    TaskDependency,
    UserStory,
    utcnow,
)
from app.schemas import (
    AssumptionOut,
    ClarificationOut,
    CheckOut,
    CriterionOut,
    DecisionOut,
    DefectOut,
    EventOut,
    FindingOut,
    GateOut,
    OwnershipOut,
    PullRequestOut,
    ProjectListItem,
    ProjectOut,
    ProjectSnapshot,
    RequirementOut,
    RequirementWrite,
    RunOut,
    StoryOut,
    TaskOut,
)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _actions(stage: str, tasks: list, *, paused: bool) -> list[str]:
    if paused:
        return ["unpause"]
    actions = next_actions(PlanStage(stage))
    if any(task.state == "ready" for task in tasks):
        actions = [*actions, "run_ready"]
    if any(task.state == "escalated" for task in tasks):
        actions = [*actions, "resume_escalated"]
    return [*actions, "pause"]


class _Question(BaseModel):
    question: str = Field(min_length=1)
    resolves: str = Field(min_length=1)


class _Interpret(BaseModel):
    interpretation: str = Field(min_length=1)
    clarifications: list[_Question] = []


class _Followup(BaseModel):
    more: bool = False
    clarifications: list[_Question] = []


class _RequirementIn(BaseModel):
    kind: str
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    criteria: list[str] = []


class _RequirementsIn(BaseModel):
    user_stories: list[str] = []
    requirements: list[_RequirementIn] = Field(min_length=1)


class _DecisionIn(BaseModel):
    title: str = Field(min_length=1)
    context: str = Field(min_length=1)
    options: list[str] = Field(min_length=1)
    decision: str = Field(min_length=1)
    consequences: str = Field(min_length=1)


class _OwnershipIn(BaseModel):
    glob: str = Field(min_length=1)
    zone: str


class _ArchitectureIn(BaseModel):
    summary: str = Field(min_length=1)
    test_strategy: dict[str, str]
    ownership: list[_OwnershipIn] = Field(min_length=1)
    decisions: list[_DecisionIn] = Field(min_length=1)


class _TaskIn(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    zone: str
    size: str
    depends_on: list[int] = []
    requirement_indexes: list[int] = []


class _TasksIn(BaseModel):
    tasks: list[_TaskIn] = Field(min_length=1)


def _parse(model: type[BaseModel], data: dict) -> BaseModel:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        loc = ".".join(str(part) for part in exc.errors()[0]["loc"])
        raise DomainError(
            f"The model reply failed validation at '{loc}'. Nothing was saved.",
            status_code=502,
        ) from exc


class PlanningService:
    def __init__(self, session: Session, llm: LlmClient, settings: Settings | None = None) -> None:
        self.session = session
        self.llm = llm
        self.settings = settings or Settings()

    def create_project(
        self,
        *,
        name: str,
        description: str,
        tech_preferences: str | None,
        github_repo: str | None = None,
        spend_ceiling_tokens: int = 1_000_000,
    ) -> ProjectSnapshot:
        repo = (github_repo or "").strip() or None
        if repo and (repo.count("/") != 1 or any(part.strip() == "" for part in repo.split("/"))):
            raise DomainError("github_repo must look like owner/name.", status_code=422)
        if spend_ceiling_tokens < 1:
            raise DomainError("The spend ceiling must be at least 1 token.", status_code=422)
        project = Project(
            id=new_id("prj"),
            name=name.strip(),
            description=description.strip(),
            tech_preferences=(tech_preferences or "").strip() or None,
            github_repo=repo,
            spend_ceiling_tokens=spend_ceiling_tokens,
            stage=PlanStage.INTAKE.value,
        )
        self.session.add(project)
        self.session.flush()
        self._event(project, "project.created", actor_kind="user", payload={"name": project.name})
        return self.snapshot(project.id)

    def pause(self, project_id: str) -> ProjectSnapshot:
        project = self._project(project_id)
        if project.paused:
            return self.snapshot(project_id)
        project.paused = True
        project.updated_at = utcnow()
        self._event(
            project,
            "project.paused",
            actor_kind="user",
            payload={"summary": "A person paused the project."},
        )
        return self.snapshot(project_id)

    def unpause(self, project_id: str) -> ProjectSnapshot:
        project = self._project(project_id)
        if not project.paused:
            return self.snapshot(project_id)
        project.paused = False
        project.updated_at = utcnow()
        self._event(
            project,
            "project.unpaused",
            actor_kind="user",
            payload={"summary": "A person unpaused the project."},
        )
        return self.snapshot(project_id)

    def set_spend_ceiling(self, project_id: str, spend_ceiling_tokens: int) -> ProjectSnapshot:
        project = self._project(project_id)
        if spend_ceiling_tokens < 1:
            raise DomainError("The spend ceiling must be at least 1 token.", status_code=422)
        spent = tokens_used(project.runs)
        if spend_ceiling_tokens < spent:
            raise DomainError(
                f"The ceiling cannot be below spend already used ({spent} tokens).",
                status_code=422,
            )
        project.spend_ceiling_tokens = spend_ceiling_tokens
        project.updated_at = utcnow()
        self._event(
            project,
            "project.spend_ceiling_raised",
            actor_kind="user",
            payload={
                "spend_ceiling_tokens": spend_ceiling_tokens,
                "spend_tokens": spent,
                "summary": f"Spend ceiling set to {spend_ceiling_tokens} tokens.",
            },
        )
        return self.snapshot(project_id)

    def list_projects(self) -> list[ProjectListItem]:
        rows = self.session.scalars(select(Project).order_by(Project.created_at.desc())).all()
        return [
            ProjectListItem(id=row.id, name=row.name, stage=row.stage, created_at=row.created_at)
            for row in rows
        ]

    def snapshot(self, project_id: str) -> ProjectSnapshot:
        # Flush and reload so rows added in this step show up on the response.
        # Without the reload, SQLAlchemy can hand back a collection it loaded
        # earlier, before those rows existed.
        self.session.flush()
        project = self._project(project_id)
        self.session.expire(project)
        requirements = sorted(project.requirements, key=lambda item: item.sort_order)
        tasks = sorted(project.tasks, key=lambda item: item.sort_order)
        key_by_id = {task.id: task.key for task in tasks}
        task_out = []
        for task in tasks:
            task_out.append(
                TaskOut(
                    id=task.id,
                    key=task.key,
                    title=task.title,
                    description=task.description,
                    zone=task.zone,
                    state=task.state,
                    size=task.size,
                    requirement_keys=list(task.requirement_keys),
                    depends_on=[key_by_id[dep.depends_on_id] for dep in task.dependencies],
                    retry_count=task.retry_count,
                    max_retries=task.max_retries,
                    branch_name=task.branch_name,
                )
            )
        uncovered = uncovered_requirements(
            [req.key for req in requirements],
            [list(task.requirement_keys) for task in tasks],
        )
        # Traceability is only meaningful once tasks exist.
        if project.stage != PlanStage.TASKS_READY.value:
            uncovered = []
        return ProjectSnapshot(
            project=ProjectOut(
                id=project.id,
                name=project.name,
                description=project.description,
                tech_preferences=project.tech_preferences,
                interpretation=project.interpretation,
                stage=project.stage,
                clarification_round=project.clarification_round,
                max_questions=project.max_questions,
                max_rounds=project.max_rounds,
                architecture_summary=project.architecture_summary,
                test_strategy=project.test_strategy,
                github_repo=project.github_repo,
                paused=bool(project.paused),
                spend_ceiling_tokens=project.spend_ceiling_tokens,
                spend_tokens=tokens_used(project.runs),
                spend_alerts=self._spend_alerts(project),
                created_at=project.created_at,
                next_actions=_actions(project.stage, tasks, paused=bool(project.paused)),
                uncovered_requirement_keys=uncovered,
            ),
            clarifications=[
                ClarificationOut(
                    id=item.id,
                    round_number=item.round_number,
                    question=item.question,
                    resolves=item.resolves,
                    answer=item.answer,
                    status=item.status,
                )
                for item in sorted(project.clarifications, key=lambda item: (item.round_number, item.id))
            ],
            assumptions=[
                AssumptionOut(id=item.id, statement=item.statement) for item in project.assumptions
            ],
            stories=[StoryOut(id=item.id, statement=item.statement) for item in project.stories],
            requirements=[
                RequirementOut(
                    id=req.id,
                    key=req.key,
                    kind=req.kind,
                    title=req.title,
                    statement=req.statement,
                    criteria=[
                        CriterionOut(id=crit.id, key=crit.key, statement=crit.statement)
                        for crit in req.criteria
                    ],
                )
                for req in requirements
            ],
            decisions=[
                DecisionOut(
                    id=item.id,
                    title=item.title,
                    context=item.context,
                    options=list(item.options),
                    decision=item.decision,
                    consequences=item.consequences,
                )
                for item in project.decisions
            ],
            ownership=[
                OwnershipOut(id=item.id, glob=item.glob, zone=item.zone) for item in project.ownership
            ],
            tasks=task_out,
            findings=[
                FindingOut(
                    id=item.id,
                    task_id=item.task_id,
                    criterion_key=item.criterion_key,
                    result=item.result,
                    note=item.note,
                )
                for item in sorted(project.findings, key=lambda item: item.criterion_key)
            ],
            defects=[
                DefectOut(
                    id=item.id,
                    task_id=item.task_id,
                    criterion_key=item.criterion_key,
                    reproduction=item.reproduction,
                    observed=item.observed,
                    expected=item.expected,
                )
                for item in project.defects
            ],
            checks=[
                CheckOut(
                    id=item.id,
                    task_id=item.task_id,
                    tier=item.tier,
                    command=item.command,
                    exit_code=item.exit_code,
                    excerpt=item.excerpt,
                )
                for item in sorted(project.checks, key=lambda item: item.tier)
            ],
            pull_requests=[
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
                for item in sorted(project.pull_requests, key=lambda item: item.created_at)
            ],
            gates=[
                GateOut(
                    id=item.id,
                    gate=item.gate,
                    decision=item.decision,
                    note=item.note,
                    created_at=item.created_at,
                )
                for item in sorted(project.gates, key=lambda item: item.created_at)
            ],
            events=[
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
                for item in sorted(project.events, key=lambda item: item.occurred_at, reverse=True)[:100]
            ],
            runs=[
                RunOut(
                    id=item.id,
                    role=item.role,
                    purpose=item.purpose,
                    provider=item.provider,
                    model=item.model,
                    input_tokens=item.input_tokens,
                    output_tokens=item.output_tokens,
                )
                for item in sorted(project.runs, key=lambda item: item.created_at, reverse=True)
            ],
        )

    def update_interpretation(self, project_id: str, interpretation: str) -> ProjectSnapshot:
        project = self._project(project_id)
        self._require_stage(project, {PlanStage.CLARIFYING, PlanStage.INTERPRETED})
        project.interpretation = interpretation.strip()
        project.updated_at = utcnow()
        self._event(
            project,
            "interpretation.edited",
            actor_kind="user",
            payload={"interpretation": project.interpretation},
        )
        return self.snapshot(project.id)

    def interpret(self, project_id: str) -> ProjectSnapshot:
        project = self._project(project_id)
        require_active(paused=bool(project.paused))
        self._require_stage(project, {PlanStage.INTAKE})
        system, user = pm.interpret_prompt(project.description, project.tech_preferences)
        result = self._complete(project, "interpret", system, user)
        parsed = _parse(_Interpret, result.data)
        project.interpretation = parsed.interpretation.strip()
        questions = parsed.clarifications[: project.max_questions]
        for question in questions:
            self.session.add(
                Clarification(
                    id=new_id("clr"),
                    project_id=project.id,
                    round_number=1,
                    question=question.question.strip(),
                    resolves=question.resolves.strip(),
                    status="open",
                )
            )
        if questions:
            project.clarification_round = 1
            self._move(project, PlanStage.CLARIFYING)
        else:
            project.clarification_round = 0
            self._move(project, PlanStage.INTERPRETED)
        return self.snapshot(project.id)

    def answer_clarifications(
        self,
        project_id: str,
        answers: list[tuple[str, str]],
        *,
        proceed: bool,
    ) -> ProjectSnapshot:
        project = self._project(project_id)
        require_active(paused=bool(project.paused))
        self._guard_spend(project)
        self._require_stage(project, {PlanStage.CLARIFYING})
        by_id = {item_id: text for item_id, text in answers}
        open_items = [item for item in project.clarifications if item.status == "open"]
        unknown = [item_id for item_id in by_id if item_id not in {item.id for item in open_items}]
        if unknown:
            raise DomainError("Those questions are not open on this project.", status_code=422)

        still_open: list[Clarification] = []
        for item in open_items:
            text = by_id.get(item.id, "").strip()
            if text:
                item.answer = text
                item.status = "answered"
            else:
                still_open.append(item)

        if still_open and not proceed:
            raise DomainError(
                "Answer every open question, or proceed on recorded assumptions.",
                status_code=422,
            )

        if proceed:
            for item in still_open:
                self._assume(project, item)
            self._move(project, PlanStage.INTERPRETED)
            return self.snapshot(project.id)

        system, user = pm.followup_prompt(self._transcript(project))
        result = self._complete(project, "followup", system, user)
        followup = _parse(_Followup, result.data)
        more = followup.clarifications[: project.max_questions] if followup.more else []
        if more and project.clarification_round < project.max_rounds:
            project.clarification_round += 1
            for question in more:
                self.session.add(
                    Clarification(
                        id=new_id("clr"),
                        project_id=project.id,
                        round_number=project.clarification_round,
                        question=question.question.strip(),
                        resolves=question.resolves.strip(),
                        status="open",
                    )
                )
            self._move(project, PlanStage.CLARIFYING)
            return self.snapshot(project.id)

        if more:
            for question in more:
                self.session.add(
                    Assumption(
                        id=new_id("asm"),
                        project_id=project.id,
                        statement=(
                            "Clarification budget exhausted. Proceeding on this assumption: "
                            + question.question.strip()
                        ),
                    )
                )
            self._event(
                project,
                "clarification.budget_exhausted",
                actor_kind="system",
                payload={"max_rounds": project.max_rounds},
            )
        self._move(project, PlanStage.INTERPRETED)
        return self.snapshot(project.id)

    def generate_requirements(self, project_id: str) -> ProjectSnapshot:
        project = self._project(project_id)
        require_active(paused=bool(project.paused))
        rewriting = project.stage == PlanStage.REQUIREMENTS_DRAFT.value
        if not rewriting:
            self._require_stage(project, {PlanStage.INTERPRETED})
        system, user = pm.requirements_prompt(self._transcript(project))
        result = self._complete(project, "requirements", system, user)
        parsed = _parse(_RequirementsIn, result.data)
        for item in parsed.requirements:
            if item.kind not in {"functional", "non_functional", "constraint"}:
                raise DomainError(f"Unknown requirement kind '{item.kind}'.", status_code=502)
            require_criteria(item.kind, item.criteria)

        self._clear_requirements(project)
        for index, item in enumerate(parsed.requirements, start=1):
            requirement = Requirement(
                id=new_id("req"),
                project_id=project.id,
                key=f"FR-{index:03d}",
                kind=item.kind,
                title=item.title.strip(),
                statement=item.statement.strip(),
                sort_order=index,
            )
            self._attach_criteria(requirement, item.criteria)
            self.session.add(requirement)
        for statement in parsed.user_stories:
            text = statement.strip()
            if text:
                self.session.add(UserStory(id=new_id("sty"), project_id=project.id, statement=text))
        if not rewriting:
            self._move(project, PlanStage.REQUIREMENTS_DRAFT)
        else:
            project.updated_at = utcnow()
            self._event(project, "requirements.rewritten", actor_kind="agent", actor_role="pm", payload={})
        return self.snapshot(project.id)

    def add_requirement(self, project_id: str, body: RequirementWrite) -> ProjectSnapshot:
        project = self._project(project_id)
        self._require_stage(project, {PlanStage.REQUIREMENTS_DRAFT})
        require_criteria(body.kind, body.criteria)
        requirement = Requirement(
            id=new_id("req"),
            project_id=project.id,
            key=self._next_requirement_key(project),
            kind=body.kind,
            title=body.title.strip(),
            statement=body.statement.strip(),
            sort_order=len(project.requirements) + 1,
        )
        self._attach_criteria(requirement, body.criteria)
        self.session.add(requirement)
        project.updated_at = utcnow()
        self._event(project, "requirement.added", actor_kind="user", payload={"key": requirement.key})
        return self.snapshot(project.id)

    def update_requirement(self, project_id: str, requirement_id: str, body: RequirementWrite) -> ProjectSnapshot:
        project = self._project(project_id)
        self._require_stage(project, {PlanStage.REQUIREMENTS_DRAFT})
        requirement = self._requirement(project, requirement_id)
        require_criteria(body.kind, body.criteria)
        requirement.kind = body.kind
        requirement.title = body.title.strip()
        requirement.statement = body.statement.strip()
        for criterion in list(requirement.criteria):
            self.session.delete(criterion)
        self.session.flush()
        self._attach_criteria(requirement, body.criteria)
        project.updated_at = utcnow()
        self._event(project, "requirement.edited", actor_kind="user", payload={"key": requirement.key})
        return self.snapshot(project.id)

    def delete_requirement(self, project_id: str, requirement_id: str) -> ProjectSnapshot:
        project = self._project(project_id)
        self._require_stage(project, {PlanStage.REQUIREMENTS_DRAFT})
        requirement = self._requirement(project, requirement_id)
        key = requirement.key
        self.session.delete(requirement)
        project.updated_at = utcnow()
        self._event(project, "requirement.removed", actor_kind="user", payload={"key": key})
        return self.snapshot(project.id)

    def generate_architecture(self, project_id: str) -> ProjectSnapshot:
        project = self._project(project_id)
        require_active(paused=bool(project.paused))
        rewriting = project.stage == PlanStage.ARCHITECTURE_DRAFT.value
        if not rewriting:
            self._require_stage(project, {PlanStage.REQUIREMENTS_APPROVED})
        system, user = pm.architecture_prompt(self._transcript(project))
        result = self._complete(project, "architecture", system, user)
        parsed = _parse(_ArchitectureIn, result.data)
        self._check_test_strategy(parsed.test_strategy)
        for rule in parsed.ownership:
            if rule.zone not in {"backend", "frontend", "ai_engineer"}:
                raise DomainError(f"Unknown ownership zone '{rule.zone}'.", status_code=502)

        self._clear_architecture(project)
        project.architecture_summary = parsed.summary.strip()
        project.test_strategy = {key: value.strip() for key, value in parsed.test_strategy.items()}
        for rule in parsed.ownership:
            self.session.add(
                OwnershipRule(
                    id=new_id("own"),
                    project_id=project.id,
                    glob=rule.glob.strip(),
                    zone=rule.zone,
                )
            )
        for item in parsed.decisions:
            self.session.add(
                ArchitectureDecision(
                    id=new_id("adr"),
                    project_id=project.id,
                    title=item.title.strip(),
                    context=item.context.strip(),
                    options=[option.strip() for option in item.options if option.strip()],
                    decision=item.decision.strip(),
                    consequences=item.consequences.strip(),
                )
            )
        if not rewriting:
            self._move(project, PlanStage.ARCHITECTURE_DRAFT)
        else:
            project.updated_at = utcnow()
            self._event(project, "architecture.rewritten", actor_kind="agent", actor_role="pm", payload={})
        return self.snapshot(project.id)

    def generate_tasks(self, project_id: str) -> ProjectSnapshot:
        project = self._project(project_id)
        require_active(paused=bool(project.paused))
        self._require_stage(project, {PlanStage.ARCHITECTURE_APPROVED})
        requirements = sorted(project.requirements, key=lambda item: item.sort_order)
        if not requirements:
            raise DomainError("There are no requirements to decompose.", status_code=422)
        system, user = pm.tasks_prompt(self._transcript(project))
        result = self._complete(project, "tasks", system, user)
        parsed = _parse(_TasksIn, result.data)
        known_zones = {rule.zone for rule in project.ownership}
        known_requirements = {req.key for req in requirements}
        keys = [f"TASK-{index:03d}" for index in range(1, len(parsed.tasks) + 1)]
        edges: list[tuple[str, str]] = []
        prepared: list[tuple[_TaskIn, str, list[str], list[str]]] = []
        for index, item in enumerate(parsed.tasks):
            if any(dep == index for dep in item.depends_on):
                raise DomainError(f"{keys[index]} cannot depend on itself.", status_code=422)
            if any(dep < 0 or dep >= len(parsed.tasks) for dep in item.depends_on):
                raise DomainError(f"{keys[index]} depends on a task that is not in the graph.", status_code=422)
            requirement_keys = []
            for req_index in item.requirement_indexes:
                if req_index < 0 or req_index >= len(requirements):
                    raise DomainError(
                        f"{keys[index]} points at a requirement that does not exist.",
                        status_code=422,
                    )
                requirement_keys.append(requirements[req_index].key)
            check_task_shape(
                zone=item.zone,
                size=item.size,
                requirement_ids=requirement_keys,
                known_requirements=known_requirements,
                known_zones=known_zones,
            )
            depends = [keys[dep] for dep in dict.fromkeys(item.depends_on)]
            for dep_key in depends:
                edges.append((keys[index], dep_key))
            prepared.append((item, keys[index], requirement_keys, depends))
        require_acyclic(keys, edges)

        id_by_key: dict[str, str] = {}
        for item, key, requirement_keys, depends in prepared:
            task_id = new_id("tsk")
            id_by_key[key] = task_id
            self.session.add(
                Task(
                    id=task_id,
                    project_id=project.id,
                    key=key,
                    title=item.title.strip(),
                    description=item.description.strip(),
                    zone=item.zone,
                    state=place(blocked=bool(depends)).value,
                    size=item.size,
                    requirement_keys=requirement_keys,
                    sort_order=int(key.split("-")[1]),
                )
            )
        self.session.flush()
        for _item, key, _requirement_keys, depends in prepared:
            for dep_key in depends:
                self.session.add(
                    TaskDependency(
                        id=new_id("dep"),
                        task_id=id_by_key[key],
                        depends_on_id=id_by_key[dep_key],
                    )
                )
        self._move(project, PlanStage.TASKS_READY)
        return self.snapshot(project.id)

    def decide_gate(self, project_id: str, *, gate: str, decision: str, note: str | None) -> ProjectSnapshot:
        project = self._project(project_id)
        if gate == "requirements":
            self._require_stage(project, {PlanStage.REQUIREMENTS_DRAFT})
            if decision == "approved":
                if not project.requirements:
                    raise DomainError("There is nothing to approve yet.", status_code=422)
                for requirement in project.requirements:
                    require_criteria(
                        requirement.kind,
                        [criterion.statement for criterion in requirement.criteria],
                    )
        elif gate == "architecture":
            self._require_stage(project, {PlanStage.ARCHITECTURE_DRAFT})
            if decision == "approved":
                if not project.architecture_summary or not project.ownership or not project.test_strategy:
                    raise DomainError("The architecture is incomplete.", status_code=422)
                self._check_test_strategy(project.test_strategy)
        else:
            raise DomainError("Unknown gate.", status_code=422)

        self.session.add(
            GateDecision(
                id=new_id("gate"),
                project_id=project.id,
                gate=gate,
                decision=decision,
                note=(note or "").strip() or None,
            )
        )
        self._event(
            project,
            "gate.decided",
            actor_kind="user",
            payload={"gate": gate, "decision": decision, "note": note},
        )
        if decision == "approved" and gate == "requirements":
            self._move(project, PlanStage.REQUIREMENTS_APPROVED)
        elif decision == "approved" and gate == "architecture":
            self._move(project, PlanStage.ARCHITECTURE_APPROVED)
        else:
            project.updated_at = utcnow()
        return self.snapshot(project.id)

    def _guard_spend(self, project: Project) -> None:
        spent = tokens_used(project.runs)
        ceiling = project.spend_ceiling_tokens
        if spent < ceiling:
            return
        if not project.paused:
            project.paused = True
            project.updated_at = utcnow()
            self._event(
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

    def _spend_alerts(self, project: Project) -> list[int]:
        ceiling = project.spend_ceiling_tokens
        seen: set[int] = set()
        ordered: list[int] = []
        for event in project.events:
            if event.type != "project.spend_threshold":
                continue
            payload = event.payload or {}
            if payload.get("spend_ceiling_tokens") != ceiling:
                continue
            percent = payload.get("percent")
            if not isinstance(percent, int) or percent in seen:
                continue
            seen.add(percent)
            ordered.append(percent)
        return sorted(ordered)

    def _alert_spend_thresholds(self, project: Project, *, before: int, after: int) -> None:
        ceiling = project.spend_ceiling_tokens
        already = set(self._spend_alerts(project))
        for percent in thresholds_crossed(
            before=before,
            after=after,
            ceiling=ceiling,
            thresholds=self.settings.spend_alert_threshold_list or DEFAULT_ALERT_THRESHOLDS,
        ):
            if percent in already:
                continue
            self._event(
                project,
                "project.spend_threshold",
                actor_kind="system",
                payload={
                    "percent": percent,
                    "spend_tokens": after,
                    "spend_ceiling_tokens": ceiling,
                    "summary": (
                        f"Spend reached {percent}% of the ceiling "
                        f"({after} of {ceiling} tokens)."
                    ),
                },
            )
            already.add(percent)

    def _complete(self, project: Project, purpose: str, system: str, user: str) -> LlmResult:
        self._guard_spend(project)
        before = tokens_used(project.runs)
        result = self.llm.complete_json(purpose=purpose, system=system, user=user)
        run = AgentRun(
            id=new_id("run"),
            project_id=project.id,
            role="pm",
            purpose=purpose,
            status="succeeded",
            provider=result.provider,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
        self.session.add(run)
        self.session.flush()
        self._event(
            project,
            f"agent.{purpose}",
            actor_kind="agent",
            actor_role="pm",
            run_id=run.id,
            payload={"provider": result.provider, "model": result.model},
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
        after = before + int(result.input_tokens) + int(result.output_tokens)
        self._alert_spend_thresholds(project, before=before, after=after)
        return result

    def _assume(self, project: Project, item: Clarification) -> None:
        item.status = "assumed"
        statement = f"Proceeding without an answer to: {item.question}"
        self.session.add(
            Assumption(
                id=new_id("asm"),
                project_id=project.id,
                statement=statement,
                clarification_id=item.id,
            )
        )
        self._event(
            project,
            "assumption.recorded",
            actor_kind="user",
            payload={"statement": statement},
        )

    def _move(self, project: Project, target: PlanStage) -> None:
        previous = project.stage
        project.stage = transition(PlanStage(project.stage), target).value
        project.updated_at = utcnow()
        self._event(
            project,
            "plan.stage_changed",
            actor_kind="system",
            payload={"from": previous, "to": project.stage},
        )

    def _event(
        self,
        project: Project,
        type_: str,
        *,
        actor_kind: str,
        payload: dict,
        actor_role: str | None = None,
        run_id: str | None = None,
        task_id: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        self.session.add(
            Event(
                id=new_id("evt"),
                project_id=project.id,
                type=type_,
                task_id=task_id,
                actor_kind=actor_kind,
                actor_role=actor_role,
                run_id=run_id,
                payload=payload,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        )

    def _clear_requirements(self, project: Project) -> None:
        for story in list(project.stories):
            self.session.delete(story)
        for requirement in list(project.requirements):
            self.session.delete(requirement)
        self.session.flush()

    def _clear_architecture(self, project: Project) -> None:
        for decision in list(project.decisions):
            self.session.delete(decision)
        for rule in list(project.ownership):
            self.session.delete(rule)
        self.session.flush()

    def _attach_criteria(self, requirement: Requirement, criteria: list[str]) -> None:
        number = 1
        for statement in criteria:
            text = statement.strip()
            if not text:
                continue
            requirement.criteria.append(
                AcceptanceCriterion(
                    id=new_id("ac"),
                    key=f"AC-{number}",
                    statement=text,
                )
            )
            number += 1

    def _next_requirement_key(self, project: Project) -> str:
        numbers = []
        for requirement in project.requirements:
            try:
                numbers.append(int(requirement.key.split("-")[1]))
            except (IndexError, ValueError):
                continue
        return f"FR-{max(numbers, default=0) + 1:03d}"

    def _check_test_strategy(self, strategy: dict) -> None:
        missing = [name for name in ("unit", "integration", "ui") if not str(strategy.get(name, "")).strip()]
        if missing:
            raise DomainError(
                "The architecture must name commands for: " + ", ".join(missing),
                status_code=422,
            )

    def _transcript(self, project: Project) -> str:
        lines = [
            f"Name: {project.name}",
            f"Technology preferences: {project.tech_preferences or 'none stated'}",
            "",
            "Request:",
            project.description.strip(),
        ]
        if project.interpretation:
            lines += ["", "Interpretation:", project.interpretation.strip()]
        for item in sorted(project.clarifications, key=lambda row: row.round_number):
            lines += [
                "",
                f"Q (round {item.round_number}, {item.status}): {item.question}",
                f"Resolves: {item.resolves}",
                f"A: {item.answer or '(none)'}",
            ]
        for item in project.assumptions:
            lines += ["", f"Assumption: {item.statement}"]
        if project.requirements:
            lines += ["", "Requirements:"]
            for requirement in sorted(project.requirements, key=lambda row: row.sort_order):
                lines.append(f"{requirement.key} [{requirement.kind}] {requirement.title}: {requirement.statement}")
                for criterion in requirement.criteria:
                    lines.append(f"  {criterion.key}: {criterion.statement}")
        if project.architecture_summary:
            lines += ["", "Architecture:", project.architecture_summary]
            lines.append(f"Test commands: {project.test_strategy}")
            for rule in project.ownership:
                lines.append(f"Ownership {rule.glob} -> {rule.zone}")
        return "\n".join(lines)

    def _project(self, project_id: str) -> Project:
        project = self.session.get(Project, project_id)
        if project is None:
            raise DomainError("Project not found.", status_code=404)
        return project

    def _requirement(self, project: Project, requirement_id: str) -> Requirement:
        for requirement in project.requirements:
            if requirement.id == requirement_id:
                return requirement
        raise DomainError("Requirement not found.", status_code=404)

    def _require_stage(self, project: Project, allowed: set[PlanStage]) -> None:
        if PlanStage(project.stage) not in allowed:
            names = ", ".join(sorted(stage.value for stage in allowed))
            raise DomainError(
                f"This step is available from {names}. The project is in {project.stage}."
            )
