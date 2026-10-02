"""How a review becomes a task transition.

The model may only report a result per criterion. This module decides
whether that report is complete, and whether the task may leave review.
A missing criterion is not a pass. A failure without a reproduction is
not a defect.
"""

from dataclasses import dataclass

from app.errors import DomainError

_RESULTS = {"pass", "fail", "untestable"}


@dataclass(frozen=True)
class Finding:
    criterion_key: str
    result: str
    note: str = ""
    reproduction: str = ""
    observed: str = ""
    expected: str = ""


def judge(expected_keys: list[str], findings: list[Finding]) -> str:
    """Return pass, fail, or untestable.

    pass: every criterion passed.
    fail: at least one failed, and each failure names a reproduction.
    untestable: nothing failed, but at least one criterion could not be checked.
    """

    seen = [item.criterion_key for item in findings]
    if len(seen) != len(set(seen)):
        raise DomainError("A criterion was judged twice. Nothing was recorded.", status_code=502)
    expected = set(expected_keys)
    reported = set(seen)
    if reported != expected:
        missing = ", ".join(sorted(expected - reported)) or "none"
        raise DomainError(
            f"The review did not cover every criterion (missing: {missing}). Nothing was recorded.",
            status_code=502,
        )
    for item in findings:
        if item.result not in _RESULTS:
            raise DomainError(
                f"'{item.result}' is not a review result. Nothing was recorded.",
                status_code=502,
            )
        if item.result == "fail" and not (
            item.reproduction.strip() and item.observed.strip() and item.expected.strip()
        ):
            raise DomainError(
                f"{item.criterion_key} failed without a reproduction. Nothing was recorded.",
                status_code=502,
            )
        if item.result == "untestable" and not item.note.strip():
            raise DomainError(
                f"{item.criterion_key} was marked untestable without a reason. Nothing was recorded.",
                status_code=502,
            )
    if any(item.result == "fail" for item in findings):
        return "fail"
    if any(item.result == "untestable" for item in findings):
        return "untestable"
    return "pass"
