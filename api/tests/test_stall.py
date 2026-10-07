from datetime import datetime, timedelta, timezone

from app.domain.stall import StallTask, find_stalls


def test_in_progress_past_budget_is_stalled():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    claimed = {"t1": now - timedelta(seconds=90)}
    stalls = find_stalls(
        [StallTask("t1", "TASK-001", "in_progress")],
        claimed_at=claimed,
        now=now,
        budget_seconds=60,
    )
    assert len(stalls) == 1
    assert stalls[0].reason == "budget"
    assert stalls[0].key == "TASK-001"


def test_in_progress_inside_budget_is_not_stalled():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    stalls = find_stalls(
        [StallTask("t1", "TASK-001", "in_progress")],
        claimed_at={"t1": now - timedelta(seconds=10)},
        now=now,
        budget_seconds=60,
    )
    assert stalls == []


def test_blocked_graph_with_no_ready_task_is_stalled():
    stalls = find_stalls(
        [
            StallTask("t1", "TASK-001", "blocked"),
            StallTask("t2", "TASK-002", "blocked"),
        ],
        claimed_at={},
        budget_seconds=60,
    )
    assert {item.key for item in stalls} == {"TASK-001", "TASK-002"}
    assert all(item.reason == "deadlock" for item in stalls)


def test_a_ready_task_means_the_graph_is_not_deadlocked():
    stalls = find_stalls(
        [
            StallTask("t1", "TASK-001", "ready"),
            StallTask("t2", "TASK-002", "blocked"),
        ],
        claimed_at={},
        budget_seconds=60,
    )
    assert stalls == []


def test_an_escalated_task_is_not_treated_as_a_deadlock():
    """A person is already needed — do not cascade-escalate the blocked graph."""

    stalls = find_stalls(
        [
            StallTask("t1", "TASK-001", "escalated"),
            StallTask("t2", "TASK-002", "blocked"),
        ],
        claimed_at={},
        budget_seconds=60,
    )
    assert stalls == []
