from app.domain.graph import find_cycle
from app.domain.plan_stage import PlanStage, transition as plan_transition
from app.domain.task_machine import TaskState, place, transition
from app.domain.validation import uncovered_requirements
from app.errors import DomainError
import pytest


def test_plan_cannot_skip_the_architecture_gate():
    with pytest.raises(DomainError):
        plan_transition(PlanStage.REQUIREMENTS_APPROVED, PlanStage.TASKS_READY)


def test_new_task_is_ready_only_when_nothing_blocks_it():
    assert place(blocked=False) is TaskState.READY
    assert place(blocked=True) is TaskState.BLOCKED


def test_a_gated_task_can_be_sent_back_after_a_failed_rebase():
    state, retries = transition(
        TaskState.GATED,
        TaskState.CHANGES_REQUESTED,
        retry_count=0,
        max_retries=2,
    )
    assert state is TaskState.CHANGES_REQUESTED
    assert retries == 0


def test_retry_budget_forces_an_escalation():
    state, retries = transition(TaskState.FAILED, TaskState.READY, retry_count=0, max_retries=2)
    assert state is TaskState.READY
    assert retries == 1
    state, retries = transition(TaskState.FAILED, TaskState.READY, retry_count=1, max_retries=2)
    assert retries == 2
    with pytest.raises(DomainError):
        transition(TaskState.FAILED, TaskState.READY, retry_count=2, max_retries=2)
    state, retries = transition(TaskState.FAILED, TaskState.ESCALATED, retry_count=2, max_retries=2)
    assert state is TaskState.ESCALATED
    assert retries == 2


def test_cycle_is_reported_as_a_loop():
    cycle = find_cycle(["A", "B"], [("A", "B"), ("B", "A")])
    assert cycle is not None
    assert cycle[0] == cycle[-1]


def test_uncovered_requirements_keep_their_order():
    missing = uncovered_requirements(["FR-001", "FR-002", "FR-003"], [["FR-001"], ["FR-003"]])
    assert missing == ["FR-002"]
