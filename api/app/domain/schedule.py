"""Which ready task may start.

Two runs whose write zones overlap are not scheduled together.
A frontend task can run beside a backend task. A second backend task waits.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimCandidate:
    key: str
    state: str
    zone: str
    sort_order: int


def choose_next(tasks: list[ClaimCandidate]) -> str | None:
    busy = {task.zone for task in tasks if task.state == "in_progress"}
    ready = [task for task in tasks if task.state == "ready" and task.zone not in busy]
    if not ready:
        return None
    ready.sort(key=lambda task: task.sort_order)
    return ready[0].key
