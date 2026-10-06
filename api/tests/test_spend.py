from app.domain.spend import require_spend_room, thresholds_crossed, tokens_used
from app.errors import DomainError


class _Run:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


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
