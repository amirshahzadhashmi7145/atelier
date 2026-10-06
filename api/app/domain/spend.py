"""Project spend against a token ceiling.

Spend is the sum of tokens already recorded on agent runs. A run that
would start at or above the ceiling is refused, and the project is
expected to pause so a person can raise the ceiling.
"""

from app.errors import DomainError


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
