from app.domain.spend import (
    estimate_tokens_for_size,
    require_spend_room,
    spend_by_role,
    spend_by_task,
    spend_diverges_from_estimate,
    spend_exceeds_estimate,
    thresholds_crossed,
    tokens_used,
)
from app.errors import DomainError


class _Run:
    def __init__(
        self,
        input_tokens: int,
        output_tokens: int,
        *,
        role: str = "pm",
        task_id: str | None = None,
    ) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.role = role
        self.task_id = task_id


def test_tokens_used_sums_runs():
    assert tokens_used([_Run(10, 5), _Run(3, 2)]) == 20


def test_spend_at_the_ceiling_is_refused():
    try:
        require_spend_room(spent=100, ceiling=100)
    except DomainError as exc:
        assert exc.status_code == 409
        assert "100" in exc.message
    else:
        raise AssertionError("expected a rejection")


def test_spend_under_the_ceiling_is_allowed():
    require_spend_room(spent=99, ceiling=100)


def test_thresholds_crossed_reports_newly_reached_percents():
    assert thresholds_crossed(before=0, after=49, ceiling=100) == []
    assert thresholds_crossed(before=49, after=50, ceiling=100) == [50]
    assert thresholds_crossed(before=0, after=95, ceiling=100) == [50, 80, 95]
    assert thresholds_crossed(before=50, after=79, ceiling=100) == []
    assert thresholds_crossed(before=79, after=80, ceiling=100) == [80]


def test_thresholds_respect_custom_list():
    assert thresholds_crossed(
        before=0,
        after=60,
        ceiling=100,
        thresholds=(25, 60),
    ) == [25, 60]


def test_spend_by_role_groups_tokens():
    assert spend_by_role(
        [
            _Run(10, 0, role="pm"),
            _Run(5, 5, role="backend"),
            _Run(20, 0, role="pm"),
        ]
    ) == [("pm", 30), ("backend", 10)]


def test_spend_by_task_skips_planning_runs():
    assert spend_by_task(
        [
            _Run(10, 0, role="pm", task_id=None),
            _Run(4, 1, role="backend", task_id="tsk_a"),
            _Run(2, 0, role="qa", task_id="tsk_a"),
            _Run(8, 0, role="frontend", task_id="tsk_b"),
        ],
        {"tsk_a": "TASK-001", "tsk_b": "TASK-002"},
    ) == [("tsk_b", "TASK-002", 8), ("tsk_a", "TASK-001", 7)]


def test_estimate_tokens_follow_task_size():
    assert estimate_tokens_for_size("S", s_tokens=2000, m_tokens=8000) == 2000
    assert estimate_tokens_for_size("m", s_tokens=2000, m_tokens=8000) == 8000


def test_spend_exceeds_estimate_uses_the_multiple():
    assert spend_exceeds_estimate(spent=4001, estimate=2000, multiple=2.0) is True
    assert spend_exceeds_estimate(spent=4000, estimate=2000, multiple=2.0) is False


def test_spend_diverges_from_estimate_uses_the_margin():
    assert spend_diverges_from_estimate(spent=3001, estimate=2000, margin=1.5) is True
    assert spend_diverges_from_estimate(spent=3000, estimate=2000, margin=1.5) is False
