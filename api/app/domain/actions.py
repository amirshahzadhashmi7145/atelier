"""Classify recorded events for the action log (FR-UI-3).

The dashboard shows decisions, tools, artefacts and outcomes — not raw
model traces. Classification is derived from the event type so older
rows stay legible without a migration.
"""

from __future__ import annotations

# Exact types first; prefixes second.
_DECISIONS = {
    "gate.decided",
    "project.paused",
    "project.unpaused",
    "project.agents_revoked",
    "project.agents_restored",
    "project.gate_policy",
    "project.spend_ceiling_raised",
    "qa.waived",
    "qa.rejected_untestable",
    "task.reassigned",
    "task.resumed",
    "task.branch_amended",
    "task.cancelled",
}

_ARTEFACTS = {
    "project.created",
    "pr.opened",
    "task.in_review",
    "task.defect_routed",
    "requirement.added",
    "requirement.edited",
    "requirement.removed",
    "requirements.rewritten",
    "architecture.rewritten",
    "interpretation.edited",
    "assumption.recorded",
    "plan.stage_changed",
}

_OUTCOMES = {
    "qa.passed",
    "qa.failed",
    "qa.untestable",
    "qa.tests_weakened",
    "task.accepted",
    "task.failed",
    "task.claimed",
    "task.unblocked",
    "task.defect_resolved",
    "task.spend_overspend",
    "merge.rebase_failed",
    "merge.checks_failed",
    "project.spend_ceiling",
    "project.spend_threshold",
    "clarification.budget_exhausted",
}


def action_kind(event_type: str) -> str:
    """Return decision, tool, artefact, or outcome for an event type."""

    if event_type in _DECISIONS:
        return "decision"
    if event_type in _ARTEFACTS:
        return "artefact"
    if event_type in _OUTCOMES:
        return "outcome"
    if event_type.startswith("agent."):
        return "tool"
    return "outcome"
