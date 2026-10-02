"""Checks that run before a model reply is allowed into the database.

A requirement the QA agent cannot test is not a requirement (FR-PLAN-9).
A task that does not point at a requirement cannot be traced (FR-PLAN-22).
"""

from app.errors import DomainError

ALLOWED_ZONES = {"backend", "frontend", "ai_engineer"}
ALLOWED_KINDS = {"functional", "non_functional", "constraint"}
ALLOWED_SIZES = {"S", "M"}


def require_criteria(kind: str, criteria: list[str]) -> None:
    cleaned = [item.strip() for item in criteria if item.strip()]
    if kind == "functional" and not cleaned:
        raise DomainError(
            "A functional requirement needs at least one acceptance criterion "
            "that names an observable result. Nothing was saved.",
            status_code=422,
        )


def uncovered_requirements(
    requirement_ids: list[str],
    task_requirement_ids: list[list[str]],
) -> list[str]:
    covered: set[str] = set()
    for ids in task_requirement_ids:
        covered.update(ids)
    return [req_id for req_id in requirement_ids if req_id not in covered]


def check_task_shape(
    *,
    zone: str,
    size: str,
    requirement_ids: list[str],
    known_requirements: set[str],
    known_zones: set[str],
) -> None:
    if zone not in ALLOWED_ZONES:
        raise DomainError(
            f"Zone '{zone}' is not assignable. Full-stack is not used in this phase; "
            "split the work into backend and frontend.",
            status_code=422,
        )
    if zone not in known_zones:
        raise DomainError(
            f"Zone '{zone}' is not in this project's ownership map.",
            status_code=422,
        )
    if size not in ALLOWED_SIZES:
        raise DomainError(
            f"Task size '{size}' is too large for one agent run. Split it before assignment.",
            status_code=422,
        )
    if not requirement_ids:
        raise DomainError("Every task must trace to at least one requirement.", status_code=422)
    unknown = [req_id for req_id in requirement_ids if req_id not in known_requirements]
    if unknown:
        raise DomainError(
            "Task points at unknown requirements: " + ", ".join(unknown),
            status_code=422,
        )
