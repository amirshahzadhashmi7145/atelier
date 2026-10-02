import pytest

from app.domain.budget import BudgetExceeded, RunBudget
from app.domain.schedule import ClaimCandidate, choose_next
from app.domain.zones import require_inside_zone, zone_for
from app.errors import DomainError

RULES = [("server/**", "backend"), ("server/ai/**", "ai_engineer"), ("web/**", "frontend")]


def test_the_more_specific_directory_wins():
    assert zone_for("server/app.py", RULES) == "backend"
    assert zone_for("server/ai/pipeline.py", RULES) == "ai_engineer"
    assert zone_for("web/page.tsx", RULES) == "frontend"


def test_a_write_outside_the_role_is_rejected():
    with pytest.raises(DomainError):
        require_inside_zone("web/page.tsx", "backend", RULES)


def test_iteration_and_time_budgets_stop_the_run():
    budget = RunBudget(max_iterations=2, max_seconds=60, max_tokens=100)
    budget.charge(1)
    budget.charge(1)
    with pytest.raises(BudgetExceeded) as raised:
        budget.charge(1)
    assert raised.value.kind == "iteration"

    clock = {"now": 0.0}

    def tick() -> float:
        return clock["now"]

    timed = RunBudget(max_iterations=8, max_seconds=10, max_tokens=100, clock=tick)
    timed.charge(1)
    clock["now"] = 11
    with pytest.raises(BudgetExceeded) as raised:
        timed.charge(1)
    assert raised.value.kind == "wall-clock"


def test_a_busy_zone_is_not_claimed_again():
    tasks = [
        ClaimCandidate("TASK-001", "in_progress", "backend", 1),
        ClaimCandidate("TASK-002", "ready", "backend", 2),
        ClaimCandidate("TASK-003", "ready", "frontend", 3),
    ]
    assert choose_next(tasks) == "TASK-003"
