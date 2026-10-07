"""The project manager is a prompt plus a job, not a separate service.

The same orchestrator will later run a backend prompt and a frontend
prompt. Only the text and the allowed tools change. This phase has no
tools: the PM returns JSON, and our code decides what is allowed to be saved.
"""

JSON_RULES = """
Reply with one JSON object and nothing else. No markdown fences.
Acceptance criteria must name an observable result: a status code, a stored
count, a response field, or a timing bound. "The system should handle errors"
is not a criterion.
Do not assign work to a full-stack role. Split it.
A task that would exceed one sitting must be split. Size is only "S" or "M".
Use zero-based indexes into the lists you are given. Do not invent ids.
""".strip()


def interpret_prompt(description: str, tech_preferences: str | None) -> tuple[str, str]:
    system = (
        "You are the project manager on a software team. "
        "Restate the request so the user can correct you, and ask at most 5 questions. "
        "Each question must name the decision it would settle. "
        + JSON_RULES
        + '\nShape: {"interpretation": string, "clarifications": [{"question": string, "resolves": string}]}'
    )
    user = _brief(description, tech_preferences)
    return system, user


def followup_prompt(transcript: str) -> tuple[str, str]:
    system = (
        "You are the project manager. Given the answers so far, either stop "
        "or ask at most 5 new questions about decisions that are still open. "
        + JSON_RULES
        + '\nShape: {"more": boolean, "clarifications": [{"question": string, "resolves": string}]}'
    )
    return system, transcript


def requirements_prompt(context: str) -> tuple[str, str]:
    system = (
        "You are the project manager. Write requirements a test can fail. "
        "Include functional requirements, one non-functional requirement, "
        "constraints if the user named any, and user stories. "
        + JSON_RULES
        + "\nShape: {"
        '"user_stories": [string], '
        '"requirements": [{"kind": "functional"|"non_functional"|"constraint", '
        '"title": string, "statement": string, "criteria": [string]}]}'
    )
    return system, context


def architecture_prompt(context: str) -> tuple[str, str]:
    system = (
        "You are the project manager. Propose an architecture a small team can build. "
        "Record each significant choice as a decision with context, options, the choice, "
        "and the consequences. Declare which directory globs each zone owns "
        "(use forms like backend/**, frontend/**, ai/** — covering files at every depth). "
        "Zones are only backend, frontend, and ai_engineer. "
        "Declare the exact commands that run unit, integration, and ui tests. "
        "Each command is one program plus arguments (no shell chaining). "
        "Commands must exercise acceptance behaviour (HTTP status/body, module asserts, "
        "served HTML/JS contracts) — never placeholder smokes like "
        "python3 -c \"print('unit ok')\" or node -e \"console.log('unit ok')\". "
        "Commands run from the repo root. Paths must match ownership "
        "(e.g. python3 -m pytest server/tests/unit, npm --prefix web test). "
        "If you name pytest, engineers must commit requirements.txt including pytest. "
        "If you name npm/node tests, engineers must commit package.json (root or web/). "
        "Prefer entrypoints such as node scripts/verify.js, npm test, or python -m pytest. "
        "Dependencies are installed into the sandbox copy before offline verify runs. "
        + JSON_RULES
        + "\nShape: {"
        '"summary": string, '
        '"test_strategy": {"unit": string, "integration": string, "ui": string}, '
        '"ownership": [{"glob": string, "zone": "backend"|"frontend"|"ai_engineer"}], '
        '"decisions": [{"title": string, "context": string, "options": [string], '
        '"decision": string, "consequences": string}]}'
    )
    return system, context


def tasks_prompt(context: str) -> tuple[str, str]:
    system = (
        "You are the project manager. Break the approved requirements into tasks. "
        "depends_on and requirement_indexes are zero-based indexes into your task list "
        "and the requirement list in the context. "
        "A task with no unmet dependency uses an empty depends_on list. "
        "Every task MUST include at least one requirement_indexes entry; "
        "never leave requirement_indexes empty. "
        + JSON_RULES
        + "\nShape: {"
        '"tasks": [{"title": string, "description": string, '
        '"zone": "backend"|"frontend"|"ai_engineer", "size": "S"|"M", '
        '"depends_on": [number], "requirement_indexes": [number]}]}'
    )
    return system, context


def _brief(description: str, tech_preferences: str | None) -> str:
    prefs = tech_preferences.strip() if tech_preferences else "none stated"
    return f"Technology preferences: {prefs}\n\nRequest:\n{description.strip()}"
