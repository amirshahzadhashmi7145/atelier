"""Human stop and go for a project.

A paused project keeps its artefacts. The orchestrator and planning
agents do not take the next step until a person unpauses it.
"""

from app.errors import DomainError


def require_active(*, paused: bool) -> None:
    if paused:
        raise DomainError("This project is paused. Unpause it before continuing.")
