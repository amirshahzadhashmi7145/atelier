from app.domain.control import filter_actions, require_active, require_agents
from app.errors import DomainError


def test_an_active_project_may_continue():
    require_active(paused=False)
    require_agents(agents_revoked=False)


def test_a_paused_project_is_blocked():
    try:
        require_active(paused=True)
    except DomainError as exc:
        assert "paused" in exc.message
    else:
        raise AssertionError("expected a rejection")


def test_revoked_agents_cannot_act():
    try:
        require_agents(agents_revoked=True)
    except DomainError as exc:
        assert "revoked" in exc.message
    else:
        raise AssertionError("expected a rejection")


def test_revoked_agents_drop_agent_actions_but_keep_human_ones():
    kept = filter_actions(
        ["interpret", "approve_requirements", "run_ready", "edit_requirements"],
        agents_revoked=True,
    )
    assert kept == ["approve_requirements", "edit_requirements"]
    assert filter_actions(["run_ready"], agents_revoked=False) == ["run_ready"]
