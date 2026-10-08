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
    workspace_tree: str = "",
    existing_sources: str = "",
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
        "QA reads the pytest/npm excerpts: assertions must mention the status code and "
        "response fields from the criteria so the review can mark them pass. "
        "Keep existing passing harness or feature tests; extend them for this task's "
        "criteria instead of deleting them. "
        "Do NOT rewrite scripts/verify_ui.js, *harness* test files, or tests/harness.test.mjs "
        "— those are scaffold harnesses. Add sibling feature tests and app code instead. "
        "CRITICAL — edit like Cursor, do not clobber: for files that already exist, prefer "
        "edits (search/replace) over full writes. old_string must be a non-empty exact "
        "snippet that appears once. Never send old_string as \"\". "
        "New files MUST use writes with full content — not edits with an empty old_string. "
        "If you must use writes on an existing .py file, copy the existing contents forward "
        "and only ADD your task's code (keep helpers like reset_store). The runtime also "
        "re-attaches any top-level symbols a rewrite drops, but do not rely on that. "
        "The full suite still runs — breaking earlier tasks fails this run. "
        "On the first implementation that introduces tests, also write the manifests the "
        "architecture's commands need: requirements.txt (include pytest when using "
        "python -m pytest) and/or package.json with a working test script when using npm. "
        "Put test files on the paths the architecture named (e.g. tests/unit or "
        "server/tests/unit). "
        "Wire the UI to the backend: do not leave missing entrypoints (e.g. script.js) or "
        "unused React islands the HTML never loads. "
        "If the project uses npm, keep package.json scripts runnable after install "
        "(Atelier installs dependencies into the sandbox before checks). "
        "package.json content must be a real JSON object (with real newlines), never a "
        "quoted string full of \\n and \\\" escapes. "
        "Unit tests run in Node: do not start requestAnimationFrame / DOM loops at "
        "module import time — export start/stop helpers and let the app or tests call them. "
        "Respect tech preferences and architecture: if the project forbids a UI "
        "framework / React, do NOT write JSX, .tsx, React components, or "
        "@testing-library/react tests — use plain TypeScript/DOM (or Canvas) and "
        "Vitest assertions on exported functions or document DOM APIs. "
        + JSON_RULES
        + '\nShape: {"summary": string, "done": boolean, '
        '"needs_clarification": boolean, "clarification": string, '
        '"writes": [{"path": string, "content": string}], '
        '"edits": [{"path": string, "old_string": string, "new_string": string}]}'
    )
    user = (
        f"Zone: {zone}\n"
        f"Task: {task_key} {title}\n"
        f"{description}\n"
    )
    if requirements.strip():
        user += "\nLinked requirements and acceptance criteria:\n" + requirements.strip() + "\n"
    user += f"\nOwnership:\n{ownership}"
    if workspace_tree.strip():
        user += "\n\nCurrent branch files (read-only context):\n" + workspace_tree.strip()
    if existing_sources.strip():
        user += (
            "\n\nExisting source to extend (copy forward, then add your changes):\n"
            + existing_sources.strip()
        )
    if rework.strip():
        user += "\n\nPrevious review failed:\n" + rework.strip()
    return system, user
