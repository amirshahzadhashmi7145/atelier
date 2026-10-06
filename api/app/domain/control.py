"""Human stop and go for a project.

A paused project keeps its artefacts. The orchestrator and planning
agents do not take the next step until a person unpauses it.

Revoking agents is narrower: agents may not act, but a person may still
approve gates, amend branches, and edit artefacts.
"""

from app.errors import DomainError

# Actions that start or continue an agent. Human edits and approvals stay.
_AGENT_ACTIONS = {
    "interpret",
    "answer_clarifications",
    "generate_requirements",
    "rewrite_requirements",
    "generate_architecture",
    "rewrite_architecture",
    "generate_tasks",
    "run_ready",
}


def require_active(*, paused: bool) -> None:
    if paused:
        raise DomainError("This project is paused. Unpause it before continuing.")


def require_agents(*, agents_revoked: bool) -> None:
    if agents_revoked:
        raise DomainError(
            "Agent authority is revoked. Restore it before agents can act."
        )


def filter_actions(actions: list[str], *, agents_revoked: bool) -> list[str]:
    if not agents_revoked:
        return actions
    return [action for action in actions if action not in _AGENT_ACTIONS]
