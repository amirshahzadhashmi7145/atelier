"""The task lifecycle.

Agents are not trusted to stop themselves. This module is the rulebook
the orchestrator will enforce once agents start running in a later phase.
Phase 1 only places new tasks into ready or blocked. The rest of the
machine is already tested, because a wrong transition later would be
expensive to discover.

Retry rule: a task may return from failed to ready at most `max_retries`
times (default 2). The next failure must escalate to a human.
"""

from enum import StrEnum

from app.errors import DomainError


class TaskState(StrEnum):
    DRAFT = "draft"
    BLOCKED = "blocked"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    GATED = "gated"
    CHANGES_REQUESTED = "changes_requested"
    DONE = "done"
    FAILED = "failed"
    ESCALATED = "escalated"


_ALLOWED: dict[TaskState, set[TaskState]] = {
    TaskState.DRAFT: {TaskState.BLOCKED, TaskState.READY},
    TaskState.BLOCKED: {TaskState.READY},
    TaskState.READY: {TaskState.IN_PROGRESS},
    TaskState.IN_PROGRESS: {TaskState.FAILED, TaskState.IN_REVIEW},
    TaskState.FAILED: {TaskState.READY, TaskState.ESCALATED},
    TaskState.ESCALATED: {TaskState.READY},
    TaskState.IN_REVIEW: {TaskState.GATED, TaskState.CHANGES_REQUESTED},
    TaskState.GATED: {TaskState.DONE, TaskState.CHANGES_REQUESTED},
    TaskState.CHANGES_REQUESTED: {TaskState.READY},
    TaskState.DONE: set(),
}


def place(blocked: bool) -> TaskState:
    """Where a brand-new task sits once its dependencies are known."""

    return TaskState.BLOCKED if blocked else TaskState.READY


def transition(
    state: TaskState,
    target: TaskState,
    *,
    retry_count: int,
    max_retries: int,
) -> tuple[TaskState, int]:
    if target not in _ALLOWED[state]:
        raise DomainError(
            f"Task cannot move from {state.value} to {target.value}."
        )
    if state is TaskState.FAILED and target is TaskState.READY and retry_count >= max_retries:
        raise DomainError(
            f"Retry budget is {max_retries}. This task has to be escalated to a human."
        )
    if state is TaskState.FAILED and target is TaskState.READY:
        retry_count += 1
    return target, retry_count
