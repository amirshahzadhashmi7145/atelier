"""Detect stalled work that needs a person (FR-PLAN-21).

Two cases:
- a task has been IN_PROGRESS longer than the run budget
- unfinished work remains but nothing is ready (or otherwise progressing)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

_PROGRESSING = {
    "ready",
    "in_progress",
    "in_review",
    "gated",
    "changes_requested",
}
_TERMINAL = {"done", "cancelled"}


@dataclass(frozen=True)
class StallTask:
    id: str
    key: str
    state: str


@dataclass(frozen=True)
class Stall:
    task_id: str
    key: str
    reason: str
    summary: str


def find_stalls(
    tasks: list[StallTask],
    *,
    claimed_at: dict[str, datetime],
    now: datetime | None = None,
    budget_seconds: float,
) -> list[Stall]:
    """Return tasks that should be escalated for stall."""

    clock = now or datetime.now(timezone.utc)
    found: list[Stall] = []
    for task in tasks:
        if task.state != "in_progress":
            continue
        started = claimed_at.get(task.id)
        if started is None:
            continue
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        age = (clock - started).total_seconds()
        if age > budget_seconds:
            found.append(
                Stall(
                    task_id=task.id,
                    key=task.key,
                    reason="budget",
                    summary=(
                        f"{task.key} has been in progress for {int(age)}s "
                        f"(budget {int(budget_seconds)}s)."
                    ),
                )
            )

    unfinished = [task for task in tasks if task.state not in _TERMINAL]
    if unfinished and not any(task.state in _PROGRESSING for task in unfinished):
        for task in unfinished:
            if task.state in {"blocked", "failed"}:
                found.append(
                    Stall(
                        task_id=task.id,
                        key=task.key,
                        reason="deadlock",
                        summary=(
                            f"{task.key} is stalled: unfinished work remains "
                            "but no task is ready to run."
                        ),
                    )
                )
    # Stable unique by task_id (budget wins over deadlock if both)
    by_id: dict[str, Stall] = {}
    for item in found:
        by_id.setdefault(item.task_id, item)
    return list(by_id.values())
