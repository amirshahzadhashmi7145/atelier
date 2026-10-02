"""The project's planning stages.

A project walks a fixed path. Code generation is not on this path.
The stage is what stops the system from writing tasks before a human
has approved the architecture, which is requirement FR-PLAN-15.

Task states (ready, blocked, in progress) are a different machine.
Those describe one unit of work. This machine describes the project.
"""

from enum import StrEnum

from app.errors import DomainError


class PlanStage(StrEnum):
    INTAKE = "intake"
    INTERPRETED = "interpreted"
    CLARIFYING = "clarifying"
    REQUIREMENTS_DRAFT = "requirements_draft"
    REQUIREMENTS_APPROVED = "requirements_approved"
    ARCHITECTURE_DRAFT = "architecture_draft"
    ARCHITECTURE_APPROVED = "architecture_approved"
    TASKS_READY = "tasks_ready"


# What a stage is allowed to become. Anything else is a bug or a skipped gate.
_ALLOWED: dict[PlanStage, set[PlanStage]] = {
    PlanStage.INTAKE: {PlanStage.INTERPRETED, PlanStage.CLARIFYING},
    PlanStage.CLARIFYING: {PlanStage.CLARIFYING, PlanStage.INTERPRETED},
    PlanStage.INTERPRETED: {PlanStage.REQUIREMENTS_DRAFT},
    PlanStage.REQUIREMENTS_DRAFT: {PlanStage.REQUIREMENTS_APPROVED},
    PlanStage.REQUIREMENTS_APPROVED: {PlanStage.ARCHITECTURE_DRAFT},
    PlanStage.ARCHITECTURE_DRAFT: {PlanStage.ARCHITECTURE_APPROVED},
    PlanStage.ARCHITECTURE_APPROVED: {PlanStage.TASKS_READY},
    PlanStage.TASKS_READY: set(),
}


def transition(current: PlanStage, target: PlanStage) -> PlanStage:
    if target not in _ALLOWED[current]:
        raise DomainError(
            f"Cannot move from {current.value} to {target.value}. "
            "The planning gates have to be passed in order."
        )
    return target


def next_actions(stage: PlanStage) -> list[str]:
    """Actions the server will accept right now.

    The dashboard renders these. It does not decide them.
    """

    return {
        PlanStage.INTAKE: ["interpret"],
        PlanStage.CLARIFYING: ["answer_clarifications", "proceed_on_assumptions", "edit_interpretation"],
        PlanStage.INTERPRETED: ["edit_interpretation", "generate_requirements"],
        PlanStage.REQUIREMENTS_DRAFT: ["edit_requirements", "rewrite_requirements", "approve_requirements"],
        PlanStage.REQUIREMENTS_APPROVED: ["generate_architecture"],
        PlanStage.ARCHITECTURE_DRAFT: ["rewrite_architecture", "approve_architecture"],
        PlanStage.ARCHITECTURE_APPROVED: ["generate_tasks"],
        PlanStage.TASKS_READY: [],
    }[stage]
