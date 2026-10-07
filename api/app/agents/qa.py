"""The QA engineer is a prompt, not a second service.

Criteria are listed before the diff on purpose. The review is supposed
to come from the requirement, and the implementation is evidence, not
the brief.
"""

from app.agents.pm import JSON_RULES


def review_prompt(
    *,
    task_key: str,
    title: str,
    criteria: list[tuple[str, str]],
    checks: str,
    diff: str,
) -> tuple[str, str]:
    listed = "\n".join(f"- {key}: {statement}" for key, statement in criteria)
    system = (
        "You are the QA engineer. Judge every acceptance criterion. "
        "Do not propose file changes. "
        "Pass only when the test-result excerpt or an executable reproduction proves the "
        "criterion — never pass because the diff merely looks plausible. "
        "If checks exited 0 but their output does not speak to the criterion, mark "
        "untestable (not pass). "
        "A criterion you cannot execute is untestable, never a pass. "
        + JSON_RULES
        + '\nShape: {"findings": [{"criterion_key": string, "result": "pass" | "fail" | "untestable", '
        '"note": string, "reproduction": string, "observed": string, "expected": string}]}'
    )
    user = (
        f"Task: {task_key} {title}\n\n"
        "Criteria:\n"
        f"{listed}\n\n"
        "Test results:\n"
        f"{checks}\n\n"
        "Diff:\n"
        f"{diff}"
    )
    return system, user
