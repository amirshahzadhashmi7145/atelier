"""Rows the planning loop stores.

Agent configuration (the prompt, the tools, the model) is code, not a row.
An agent run is a row: one bounded execution, with the tokens it spent.
That split is deliberate. A prompt can be versioned. A run is an audit record.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    tech_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage: Mapped[str] = mapped_column(String(40), default="intake")
    clarification_round: Mapped[int] = mapped_column(Integer, default=0)
    max_questions: Mapped[int] = mapped_column(Integer, default=5)
    max_rounds: Mapped[int] = mapped_column(Integer, default=3)
    architecture_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_strategy: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    github_repo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    paused: Mapped[bool] = mapped_column(default=False)
    spend_ceiling_tokens: Mapped[int] = mapped_column(Integer, default=1_000_000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    clarifications: Mapped[list["Clarification"]] = relationship(cascade="all, delete-orphan")
    assumptions: Mapped[list["Assumption"]] = relationship(cascade="all, delete-orphan")
    requirements: Mapped[list["Requirement"]] = relationship(cascade="all, delete-orphan")
    stories: Mapped[list["UserStory"]] = relationship(cascade="all, delete-orphan")
    decisions: Mapped[list["ArchitectureDecision"]] = relationship(cascade="all, delete-orphan")
    ownership: Mapped[list["OwnershipRule"]] = relationship(cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(cascade="all, delete-orphan")
    findings: Mapped[list["CriterionFinding"]] = relationship(cascade="all, delete-orphan")
    defects: Mapped[list["Defect"]] = relationship(cascade="all, delete-orphan")
    checks: Mapped[list["CheckRun"]] = relationship(cascade="all, delete-orphan")
    pull_requests: Mapped[list["PullRequest"]] = relationship(cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(cascade="all, delete-orphan")
    gates: Mapped[list["GateDecision"]] = relationship(cascade="all, delete-orphan")
    runs: Mapped[list["AgentRun"]] = relationship(cascade="all, delete-orphan")


class Clarification(Base):
    __tablename__ = "clarifications"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    round_number: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    resolves: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")


class Assumption(Base):
    __tablename__ = "assumptions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    statement: Mapped[str] = mapped_column(Text)
    clarification_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    statement: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    criteria: Mapped[list["AcceptanceCriterion"]] = relationship(cascade="all, delete-orphan")


class AcceptanceCriterion(Base):
    __tablename__ = "acceptance_criteria"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(20))
    statement: Mapped[str] = mapped_column(Text)


class UserStory(Base):
    __tablename__ = "user_stories"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    statement: Mapped[str] = mapped_column(Text)


class ArchitectureDecision(Base):
    __tablename__ = "architecture_decisions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    context: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON)
    decision: Mapped[str] = mapped_column(Text)
    consequences: Mapped[str] = mapped_column(Text)


class OwnershipRule(Base):
    __tablename__ = "ownership_rules"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    glob: Mapped[str] = mapped_column(String(200))
    zone: Mapped[str] = mapped_column(String(40))


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    zone: Mapped[str] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(30))
    size: Mapped[str] = mapped_column(String(4))
    requirement_keys: Mapped[list] = mapped_column(JSON)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=2)
    branch_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    dependencies: Mapped[list["TaskDependency"]] = relationship(
        foreign_keys="TaskDependency.task_id",
        cascade="all, delete-orphan",
    )


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    depends_on_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)


class CriterionFinding(Base):
    __tablename__ = "criterion_findings"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    criterion_key: Mapped[str] = mapped_column(String(40))
    result: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")


class Defect(Base):
    __tablename__ = "defects"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    criterion_key: Mapped[str] = mapped_column(String(40))
    reproduction: Mapped[str] = mapped_column(Text)
    observed: Mapped[str] = mapped_column(Text)
    expected: Mapped[str] = mapped_column(Text)


class CheckRun(Base):
    __tablename__ = "check_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    tier: Mapped[str] = mapped_column(String(20))
    command: Mapped[str] = mapped_column(String(400))
    exit_code: Mapped[int] = mapped_column(Integer)
    excerpt: Mapped[str] = mapped_column(Text, default="")


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    branch_name: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), default="open")
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(40))
    purpose: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(80))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GateDecision(Base):
    __tablename__ = "gate_decisions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    gate: Mapped[str] = mapped_column(String(40))
    decision: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(60))
    task_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    actor_kind: Mapped[str] = mapped_column(String(20))
    actor_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
