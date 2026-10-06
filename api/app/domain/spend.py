"""Project spend against a token ceiling.

Spend is the sum of tokens already recorded on agent runs. A run that
would start at or above the ceiling is refused, and the project is
expected to pause so a person can raise the ceiling. Crossing a
configured percentage of the ceiling is an alert, not a stop.
"""

from collections.abc import Sequence

from app.errors import DomainError

DEFAULT_ALERT_THRESHOLDS = (50, 80, 95)


def tokens_used(runs: list) -> int:
    return sum(int(run.input_tokens) + int(run.output_tokens) for run in runs)


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
