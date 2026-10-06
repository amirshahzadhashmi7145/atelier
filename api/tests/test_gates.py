from app.domain.gates import (
    DEFAULT_GATE_POLICY,
    gates_newly_automatic,
    is_automatic,
    normalize_gate_policy,
    require_automation_acknowledgement,
)
from app.errors import DomainError


def test_default_policy_keeps_merge_human():
    policy = normalize_gate_policy(None)
    assert policy == DEFAULT_GATE_POLICY
    assert policy["merge"] == "human"
    assert policy["deployment"] == "human"


def test_normalize_accepts_overrides():
    policy = normalize_gate_policy({"requirements": "automatic", "architecture": "AUTOMATIC"})
    assert policy["requirements"] == "automatic"
    assert policy["architecture"] == "automatic"
    assert policy["merge"] == "human"


def test_normalize_rejects_unknown_gate_or_mode():
    try:
        normalize_gate_policy({"mystery": "human"})
    except DomainError as exc:
        assert exc.status_code == 422
    else:
        raise AssertionError("expected rejection")
    try:
        normalize_gate_policy({"merge": "maybe"})
    except DomainError as exc:
        assert exc.status_code == 422
    else:
        raise AssertionError("expected rejection")


def test_is_automatic_reads_normalized_policy():
    assert is_automatic({"requirements": "automatic"}, "requirements") is True
    assert is_automatic(None, "requirements") is False


def test_gates_newly_automatic_lists_irreversible_promotions():
    assert gates_newly_automatic(before=None, after={"merge": "automatic"}) == ["merge"]
    assert gates_newly_automatic(
        before={"merge": "automatic"},
        after={"merge": "automatic", "deployment": "automatic"},
    ) == ["deployment"]
    assert gates_newly_automatic(before=None, after={"requirements": "automatic"}) == []


def test_automation_acknowledgement_is_required_for_merge():
    try:
        require_automation_acknowledgement(
            before=None,
            after={"merge": "automatic"},
            acknowledgement="",
        )
    except DomainError as exc:
        assert exc.status_code == 422
        assert "acknowledgement" in exc.message.lower()
    else:
        raise AssertionError("expected rejection")
    assert (
        require_automation_acknowledgement(
            before=None,
            after={"merge": "automatic"},
            acknowledgement="  I accept unattended merges.  ",
        )
        == "I accept unattended merges."
    )
    assert (
        require_automation_acknowledgement(
            before=None,
            after={"requirements": "automatic"},
            acknowledgement=None,
        )
        is None
    )
