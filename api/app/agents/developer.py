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
        "When you return writes, set done true in the same reply — do not stream "
        "partial edits across turns. "
        "Every write path must match your zone ownership globs (for example "
        "frontend/**/* means paths like frontend/Foo.js — never src/ or web/ "
        "unless those globs are listed). "
        "Use the linked requirements and acceptance criteria as the source of truth. "
        "Only set needs_clarification true when those criteria truly cannot answer the "
        "question; do not ask for details already listed below. "
        "Never set needs_clarification for timeouts, retries, or missing tests — implement "
        "from the criteria instead. "
        "If clarifying, put one concrete question in clarification, leave writes empty, "
        "and set done false. "
        "Declared tests run on your writes before commit. Add or update verify scripts that "
        "assert the linked acceptance criteria (HTTP status/body, module behaviour, or that "
        "the served page loads its real script and talks to the API). "
        "On the first implementation that introduces tests, also write the manifests the "
        "architecture's commands need: requirements.txt (include pytest when using "
        "python -m pytest) and/or package.json with a working test script when using npm. "
        "Put test files on the paths the architecture named (e.g. tests/unit or "
        "server/tests/unit). "
        "Wire the UI to the backend: do not leave missing entrypoints (e.g. script.js) or "
        "unused React islands the HTML never loads. "
        "If the project uses npm, keep package.json scripts runnable after install "
        "(Atelier installs dependencies into the sandbox before checks). "
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
