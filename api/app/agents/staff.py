"""Full-stack staff engineer — reviews every branch before QA.

Does not own a write zone. Rejects incomplete work, clobbered APIs, and
green harnesses that never assert acceptance criteria.
"""

from app.agents.pm import JSON_RULES


def staff_review_prompt(
    *,
    task_key: str,
    title: str,
    zone: str,
    criteria: list[tuple[str, str]],
    checks: str,
    diff: str,
    gate_notes: str,
) -> tuple[str, str]:
    listed = "\n".join(f"- {key}: {statement}" for key, statement in criteria)
    system = (
        "You are the full-stack staff engineer. Review this task branch before QA. "
        "You do not write files. "
        "Reject (verdict fail) when: prior public APIs/helpers were removed, tests do not "
        "assert the linked acceptance criteria, the implementing zone left the other side "
        "broken, or the diff is a from-scratch rewrite of a working module. "
        "Pass only when the implementation plus test excerpts clearly cover every criterion. "
        "If the deterministic gate already listed problems, verdict must be fail. "
        + JSON_RULES
        + '\nShape: {"verdict": "pass" | "fail", "summary": string, '
        '"issues": [{"code": string, "detail": string}]}'
    )
    user = (
        f"Task: {task_key} {title}\n"
        f"Implementing zone: {zone}\n\n"
        "Acceptance criteria:\n"
        f"{listed}\n\n"
        "Deterministic staff gate:\n"
        f"{gate_notes or '(no deterministic issues)'}\n\n"
        "Test results:\n"
        f"{checks}\n\n"
        "Diff:\n"
        f"{diff}"
    )
    return system, user
