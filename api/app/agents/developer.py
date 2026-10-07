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
    requirements: str = "",
    rework: str = "",
) -> tuple[str, str]:
    system = (
        "You are the "
        + zone.replace("_", " ")
        + " engineer. Implement only this task. "
        "Write files inside your zone and stop. "
        "Use the linked requirements and acceptance criteria as the source of truth. "
        "Only set needs_clarification true when those criteria truly cannot answer the "
        "question; do not ask for details already listed below. "
        "If clarifying, put one concrete question in clarification, leave writes empty, "
        "and set done false. "
        "Declared tests run on your writes before commit: if the project uses npm scripts, "
        "include a package.json (in-zone) whose scripts run offline without installs. "
        + JSON_RULES
        + '\nShape: {"summary": string, "done": boolean, '
        '"needs_clarification": boolean, "clarification": string, '
        '"writes": [{"path": string, "content": string}]}'
    )
    user = (
        f"Zone: {zone}\n"
        f"Task: {task_key} {title}\n"
        f"{description}\n"
    )
    if requirements.strip():
        user += "\nLinked requirements and acceptance criteria:\n" + requirements.strip() + "\n"
    user += f"\nOwnership:\n{ownership}"
    if rework.strip():
        user += "\n\nPrevious review failed:\n" + rework.strip()
    return system, user
