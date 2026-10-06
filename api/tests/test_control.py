from app.domain.control import require_active
from app.errors import DomainError


def test_an_active_project_may_continue():
    require_active(paused=False)


def test_a_paused_project_is_blocked():
    try:
        require_active(paused=True)
    except DomainError as exc:
        assert "paused" in exc.message
    else:
        raise AssertionError("expected a rejection")
