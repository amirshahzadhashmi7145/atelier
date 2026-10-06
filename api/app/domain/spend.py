"""Project spend against a token ceiling.

Spend is the sum of tokens already recorded on agent runs. A run that
would start at or above the ceiling is refused, and the project is
expected to pause so a person can raise the ceiling. Crossing a
configured percentage of the ceiling is an alert, not a stop. The
dashboard also shows the same total broken down by role and by task.
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence

from app.errors import DomainError

DEFAULT_ALERT_THRESHOLDS = (50, 80, 95)


def run_tokens(run) -> int:
    return int(run.input_tokens) + int(run.output_tokens)


def tokens_used(runs: list) -> int:
    return sum(run_tokens(run) for run in runs)


def spend_by_role(runs: list) -> list[tuple[str, int]]:
    totals: dict[str, int] = defaultdict(int)
    for run in runs:
        totals[str(run.role)] += run_tokens(run)
    return sorted(totals.items(), key=lambda item: (-item[1], item[0]))


def spend_by_task(runs: list, task_keys: Mapping[str, str]) -> list[tuple[str, str, int]]:
    """Return (task_id, task_key, tokens) for runs that belong to a task."""

    totals: dict[str, int] = defaultdict(int)
    for run in runs:
        task_id = getattr(run, "task_id", None)
        if not task_id:
            continue
        totals[str(task_id)] += run_tokens(run)
    rows = [
        (task_id, task_keys.get(task_id, task_id), tokens)
        for task_id, tokens in totals.items()
    ]
    return sorted(rows, key=lambda item: (-item[2], item[1], item[0]))


def require_spend_room(*, spent: int, ceiling: int) -> None:
    if ceiling < 1:
        raise DomainError("The spend ceiling must be at least 1 token.", status_code=422)
    if spent >= ceiling:
        raise DomainError(
            f"Spend ceiling of {ceiling} tokens is reached ({spent} used). "
            "Raise the ceiling before continuing.",
            status_code=409,
        )


def thresholds_crossed(
    *,
    before: int,
    after: int,
    ceiling: int,
    thresholds: Sequence[int] = DEFAULT_ALERT_THRESHOLDS,
) -> list[int]:
    """Return alert percents newly reached between before and after.

    A threshold of P is crossed when spend moves from below P% of the
    ceiling to at least P%. Already-crossed thresholds are not returned.
    """

    if ceiling < 1 or after <= before:
        return []
    crossed: list[int] = []
    for percent in sorted({int(item) for item in thresholds if 1 <= int(item) <= 100}):
        # before * 100 < ceiling * percent <= after * 100
        if before * 100 < ceiling * percent <= after * 100:
            crossed.append(percent)
    return crossed
