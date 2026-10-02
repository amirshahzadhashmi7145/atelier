"""A stand-in model for learning the loop with no API key and no spend.

It does not reason about the product. It returns a plan that passes the
same validators a real model has to pass, and it quotes the user's
description so the dashboard is obviously about that project.
"""

from app.gateway.base import LlmResult


class FakeLlm:
    provider = "fake"
    model = "fake-planner"

    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        builder = {
            "interpret": _interpret,
            "followup": _followup,
            "requirements": _requirements,
            "architecture": _architecture,
            "tasks": _tasks,
            "implement": _implement,
            "qa": _qa,
        }[purpose]
        return LlmResult(
            data=builder(user),
            input_tokens=0,
            output_tokens=0,
            provider=self.provider,
            model=self.model,
        )


def _interpret(user: str) -> dict:
    return {
        "interpretation": (
            "Treat the request below as a small web application with a server API "
            "and a browser client. The first release covers the behaviour the user "
            "described, with signed-in access assumed only if they say so.\n\n"
            + user
        ),
        "clarifications": [
            {
                "question": "Who is the primary user, and what must they finish on the first visit?",
                "resolves": "the first-release scope",
            },
            {
                "question": "Do people need accounts, or is this single-user for now?",
                "resolves": "authentication",
            },
            {
                "question": "What should the system do when input is missing or too large?",
                "resolves": "rejection behaviour",
            },
        ],
    }


def _followup(_user: str) -> dict:
    return {"more": False, "clarifications": []}


def _requirements(user: str) -> dict:
    subject = _subject(user)
    return {
        "user_stories": [
            "As a user, I can complete the main job described in the request and see that it was stored.",
        ],
        "requirements": [
            {
                "kind": "functional",
                "title": "Create the main record",
                "statement": f"An authenticated session can create the primary record for: {subject}",
                "criteria": [
                    "A request without a valid session returns 401 and stores nothing.",
                    "A valid request returns 201 with an id, and a following GET of that id returns the same fields.",
                ],
            },
            {
                "kind": "functional",
                "title": "Reject bad input",
                "statement": "The system refuses input that breaks the limits named for this project.",
                "criteria": [
                    "A missing required field returns 422 and the stored record count is unchanged.",
                    "A payload over the declared size limit returns 413 and stores nothing.",
                ],
            },
            {
                "kind": "functional",
                "title": "List what was saved",
                "statement": "The user can read back the records they are allowed to see.",
                "criteria": [
                    "GET of the collection returns only records owned by the caller.",
                    "An unknown id returns 404.",
                ],
            },
            {
                "kind": "non_functional",
                "title": "Stay responsive",
                "statement": "Ordinary reads answer quickly enough to use in a form.",
                "criteria": [
                    "A collection GET with under 100 rows responds in under 300 ms on the local machine.",
                ],
            },
        ],
    }


def _architecture(user: str) -> dict:
    ownership = [
        {"glob": "server/**", "zone": "backend"},
        {"glob": "web/**", "zone": "frontend"},
    ]
    lowered = user.lower()
    if any(word in lowered for word in ("llm", "chatbot", "embedding", "rag")):
        ownership.append({"glob": "server/ai/**", "zone": "ai_engineer"})
    return {
        "summary": (
            "A browser client talks to a JSON API. The API owns validation, "
            "persistence, and authorisation. The client owns screens and form state. "
            "Shared response shapes live in one server-owned schema file that the "
            "client may import but not edit."
        ),
        "test_strategy": {
            "unit": "pytest",
            "integration": "pytest -m integration",
            "ui": "npm test",
        },
        "ownership": ownership,
        "decisions": [
            {
                "title": "Split the client and the API",
                "context": "The request needs both screens and stored data.",
                "options": [
                    "One server-rendered app",
                    "A separate client and API",
                ],
                "decision": "A separate client and API, so each agent owns one directory tree.",
                "consequences": "Contract changes are a backend task. The frontend consumes the contract and does not edit it.",
            }
        ],
    }


def _subject(user: str) -> str:
    marker = "Request:\n"
    body = user.split(marker, 1)[1] if marker in user else user
    line = body.strip().split("\n", 1)[0].strip()
    return line[:140] or "the requested product"


def _implement(user: str) -> dict:
    if "Zone: frontend" in user:
        path = "web/page.tsx"
        content = "export default function Page() {\n  return <p>Ready</p>;\n}\n"
    elif "Zone: ai_engineer" in user:
        path = "server/ai/pipeline.py"
        content = "def run() -> None:\n    return None\n"
    else:
        path = "server/app.py"
        content = "def create_record() -> dict:\n    return {\"id\": \"1\"}\n"
    if "Previous review failed" in user:
        content += "# revised after review\n"
    return {
        "summary": "Added the first file for this task.",
        "done": True,
        "writes": [{"path": path, "content": content}],
    }


def _qa(user: str) -> dict:
    keys: list[str] = []
    reading = False
    for line in user.splitlines():
        if line == "Criteria:":
            reading = True
            continue
        if line == "Diff:":
            break
        if reading and line.startswith("- "):
            keys.append(line[2:].split(":", 1)[0].strip())
    return {
        "findings": [
            {
                "criterion_key": key,
                "result": "pass",
                "note": "The change matches this criterion.",
                "reproduction": "",
                "observed": "",
                "expected": "",
            }
            for key in keys
        ]
    }


def _tasks(user: str) -> dict:
    tasks = [
        {
            "title": "Persist the main record",
            "description": "Add the table, the constraints, and a migration for the primary record.",
            "zone": "backend",
            "size": "S",
            "depends_on": [],
            "requirement_indexes": [0],
        },
        {
            "title": "Expose create, read, and rejection",
            "description": "Add the API for create and read, including the 401, 404, 413, and 422 cases.",
            "zone": "backend",
            "size": "M",
            "depends_on": [0],
            "requirement_indexes": [1, 3],
        },
        {
            "title": "Build the screen that uses the API",
            "description": "A form and a list bound to the API. Show the error from a rejected request.",
            "zone": "frontend",
            "size": "M",
            "depends_on": [1],
            "requirement_indexes": [2],
        },
    ]
    if any(word in user.lower() for word in ("llm", "chatbot", "embedding", "rag")):
        tasks.append(
            {
                "title": "Add the model-backed step",
                "description": "Call the model from the server AI zone and record a result on the main record.",
                "zone": "ai_engineer",
                "size": "M",
                "depends_on": [0],
                "requirement_indexes": [0],
            }
        )
    return {"tasks": tasks}
