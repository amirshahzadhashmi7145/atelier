"""Per-project approval policy for human-in-the-loop gates.

Each gate is either human (a person must decide) or automatic (the
system records an approval and continues). Merge and deployment default
to human so irreversible steps stay under a person's hand.
"""

from app.errors import DomainError

GATE_NAMES = (
    "requirements",
    "architecture",
    "merge",
    "deployment",
    "external_side_effects",
    "spend_increase",
)

GATE_MODES = ("human", "automatic")

DEFAULT_GATE_POLICY: dict[str, str] = {
    "requirements": "human",
    "architecture": "human",
    "merge": "human",
    "deployment": "human",
    "external_side_effects": "human",
    "spend_increase": "human",
}

# Setting these to automatic removes a person from an irreversible step.
IRREVERSIBLE_GATES = frozenset({"merge", "deployment", "external_side_effects"})


def normalize_gate_policy(raw: dict | None) -> dict[str, str]:
    policy = dict(DEFAULT_GATE_POLICY)
    if not raw:
        return policy
    for key, value in raw.items():
        name = str(key)
        mode = str(value).strip().lower()
        if name not in GATE_NAMES:
            raise DomainError(f"Unknown gate '{name}'.", status_code=422)
        if mode not in GATE_MODES:
            raise DomainError(
                f"Gate '{name}' must be human or automatic, not {value!r}.",
                status_code=422,
            )
        policy[name] = mode
    return policy


def is_automatic(policy: dict | None, gate: str) -> bool:
    return normalize_gate_policy(policy).get(gate) == "automatic"


def gates_newly_automatic(*, before: dict | None, after: dict | None) -> list[str]:
    """Irreversible gates that move from human (or unset) to automatic."""

    previous = normalize_gate_policy(before)
    current = normalize_gate_policy(after)
    return sorted(
        gate
        for gate in IRREVERSIBLE_GATES
        if previous.get(gate) != "automatic" and current.get(gate) == "automatic"
    )


def require_automation_acknowledgement(
    *,
    before: dict | None,
    after: dict | None,
    acknowledgement: str | None,
) -> str | None:
    """Demand a separate acknowledgement when irreversible gates go automatic.

    Returns the cleaned acknowledgement when one was required, else None.
    """

    newly = gates_newly_automatic(before=before, after=after)
    if not newly:
        return None
    text = (acknowledgement or "").strip()
    if not text:
        names = ", ".join(newly)
        raise DomainError(
            f"Setting {names} to automatic needs an explicit acknowledgement "
            "that irreversible steps may run without a person.",
            status_code=422,
        )
    return text
