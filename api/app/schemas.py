"""The JSON the dashboard sends and receives.

Indexes in model output become stable keys here (FR-001, TASK-001).
The model is not trusted to mint those keys itself.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    tech_preferences: str | None = None
    github_repo: str | None = None
    spend_ceiling_tokens: int | None = Field(default=None, ge=1)


class SpendCeilingUpdate(BaseModel):
    spend_ceiling_tokens: int = Field(ge=1)


class GatePolicyUpdate(BaseModel):
    gate_policy: dict[str, Literal["human", "automatic"]]
    acknowledgement: str | None = None


class InterpretationUpdate(BaseModel):
    interpretation: str = Field(min_length=1)


class AnswerIn(BaseModel):
    id: str
    answer: str = ""


class ClarificationSubmit(BaseModel):
    answers: list[AnswerIn] = []
    proceed: bool = False


class RequirementWrite(BaseModel):
    kind: Literal["functional", "non_functional", "constraint"]
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1)
    criteria: list[str] = []


class GateSubmit(BaseModel):
    gate: Literal["requirements", "architecture"]
    decision: Literal["approved", "rejected"]
    note: str | None = None


class UntestableSubmit(BaseModel):
    decision: Literal["waive", "reject"]


class TaskReassign(BaseModel):
    zone: Literal["backend", "frontend", "ai_engineer"]


class TaskAmend(BaseModel):
    path: str = Field(min_length=1, max_length=400)
    content: str
    summary: str = Field(default="Person amended the branch.", min_length=1, max_length=200)


class CriterionOut(BaseModel):
    id: str
    key: str
    statement: str


class RequirementOut(BaseModel):
    id: str
    key: str
    kind: str
    title: str
    statement: str
    criteria: list[CriterionOut]


class ClarificationOut(BaseModel):
    id: str
    round_number: int
    question: str
    resolves: str
    answer: str | None
    status: str


class AssumptionOut(BaseModel):
    id: str
    statement: str


class StoryOut(BaseModel):
    id: str
    statement: str


class DecisionOut(BaseModel):
    id: str
    title: str
    context: str
    options: list[str]
    decision: str
    consequences: str


class OwnershipOut(BaseModel):
    id: str
    glob: str
    zone: str


class TaskOut(BaseModel):
    id: str
    key: str
    title: str
    description: str
    zone: str
    state: str
    size: str
    estimate_tokens: int = 0
    requirement_keys: list[str]
    depends_on: list[str]
    retry_count: int
    max_retries: int
    branch_name: str | None = None


class FindingOut(BaseModel):
    id: str
    task_id: str
    criterion_key: str
    result: str
    note: str


class DefectOut(BaseModel):
    id: str
    task_id: str
    criterion_key: str
    reproduction: str
    observed: str
    expected: str


class CheckOut(BaseModel):
    id: str
    task_id: str
    tier: str
    command: str
    exit_code: int
    excerpt: str


class PullRequestOut(BaseModel):
    id: str
    task_id: str
    branch_name: str
    title: str
    body: str
    state: str
    number: int | None = None
    url: str | None = None


class GateOut(BaseModel):
    id: str
    gate: str
    decision: str
    note: str | None
    created_at: datetime


class EventOut(BaseModel):
    id: str
    type: str
    actor_kind: str
    actor_role: str | None
    payload: dict
    input_tokens: int
    output_tokens: int
    occurred_at: datetime


class RunOut(BaseModel):
    id: str
    role: str
    purpose: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    task_id: str | None = None


class TaskDetailOut(BaseModel):
    task: TaskOut
    runs: list[RunOut]
    checks: list[CheckOut]
    findings: list[FindingOut]
    defects: list[DefectOut]
    pull_requests: list[PullRequestOut]
    events: list[EventOut]
    diff: str | None = None
    diff_truncated: bool = False


class SpendByRoleOut(BaseModel):
    role: str
    tokens: int


class SpendByTaskOut(BaseModel):
    task_id: str
    task_key: str
    tokens: int


class BlockedTaskOut(BaseModel):
    task_key: str
    blocked_by: list[str]


class AgentStatusOut(BaseModel):
    role: str
    state: str


class ProjectStatusOut(BaseModel):
    task_counts: dict[str, int] = {}
    blocked: list[BlockedTaskOut] = []
    open_gates: list[str] = []
    agents: list[AgentStatusOut] = []
    needs_you: list[str] = []


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    tech_preferences: str | None
    interpretation: str | None
    stage: str
    clarification_round: int
    max_questions: int
    max_rounds: int
    architecture_summary: str | None
    test_strategy: dict | None
    github_repo: str | None = None
    paused: bool = False
    spend_ceiling_tokens: int
    spend_tokens: int
    spend_alerts: list[int] = []
    spend_by_role: list[SpendByRoleOut] = []
    spend_by_task: list[SpendByTaskOut] = []
    estimate_tokens: int = 0
    spend_over_estimate: bool = False
    gate_policy: dict[str, str] = {}
    status: ProjectStatusOut = ProjectStatusOut()
    created_at: datetime
    next_actions: list[str]
    uncovered_requirement_keys: list[str]


class ProjectSnapshot(BaseModel):
    project: ProjectOut
    clarifications: list[ClarificationOut]
    assumptions: list[AssumptionOut]
    stories: list[StoryOut]
    requirements: list[RequirementOut]
    decisions: list[DecisionOut]
    ownership: list[OwnershipOut]
    tasks: list[TaskOut]
    findings: list[FindingOut]
    defects: list[DefectOut]
    checks: list[CheckOut]
    pull_requests: list[PullRequestOut]
    gates: list[GateOut]
    events: list[EventOut]
    runs: list[RunOut]


class ProjectListItem(BaseModel):
    id: str
    name: str
    stage: str
    created_at: datetime
