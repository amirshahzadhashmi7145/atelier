"""Hard ceilings for one agent run.

A run stops when it uses too many steps, too many tokens, or too much
time. Stopping is a failure of the run, which the orchestrator then
retries or escalates. The agent is not asked to stop politely.
"""

import time
from collections.abc import Callable

from app.errors import DomainError


class BudgetExceeded(DomainError):
    def __init__(self, kind: str) -> None:
        super().__init__(f"The run hit its {kind} budget and was stopped.")
        self.kind = kind


class RunBudget:
    def __init__(
        self,
        *,
        max_iterations: int,
        max_seconds: float,
        max_tokens: int,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.max_iterations = max_iterations
        self.max_seconds = max_seconds
        self.max_tokens = max_tokens
        self.iterations = 0
        self.tokens = 0
        self._clock = clock or time.monotonic
        self._started = self._clock()

    def charge(self, tokens: int) -> None:
        self.iterations += 1
        self.tokens += tokens
        if self.iterations > self.max_iterations:
            raise BudgetExceeded("iteration")
        if self.tokens > self.max_tokens:
            raise BudgetExceeded("token")
        if self._clock() - self._started > self.max_seconds:
            raise BudgetExceeded("wall-clock")
