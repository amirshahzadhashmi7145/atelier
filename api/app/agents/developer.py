"""Backend, frontend, and AI engineer prompts.

Same runtime as the project manager. The difference is the prompt and
the directory the orchestrator will allow the reply to touch.
"""

from app.agents.pm import JSON_RULES


def implement_prompt(
    *,
    zone: str,
    task_key: str,
    title: str,
    description: str,
    ownership: str,
    rework: str = "",
) -> tuple[str, str]:
    system = (
        "You are the "
        + zone.replace("_", " ")
        + " engineer. Implement only this task. "
        "Write files inside your zone and stop. "
        "If the task is under-specified, do not invent requirements: set "
        "needs_clarification true, put one concrete question in clarification, "
        "leave writes empty, and set done false. "
        + JSON_RULES
        + '\nShape: {"summary": string, "done": boolean, '
        '"needs_clarification": boolean, "clarification": string, '
        '"writes": [{"path": string, "content": string}]}'
    )
    user = (
        f"Zone: {zone}\n"
        f"Task: {task_key} {title}\n"
        f"{description}\n\n"
        f"Ownership:\n{ownership}"
    )
    if rework.strip():
        user += "\n\nPrevious review failed:\n" + rework.strip()
    return system, user
