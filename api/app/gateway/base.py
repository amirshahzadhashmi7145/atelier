"""The only way planning code is allowed to talk to a model.

Callers ask for JSON and get a typed result. They never see a vendor SDK.
Swapping Ollama, OpenAI, or the local fake provider does not change the
project manager.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LlmResult:
    data: dict
    input_tokens: int
    output_tokens: int
    provider: str
    model: str


class LlmClient(Protocol):
    provider: str
    model: str

    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        """Return one JSON object. Raise DomainError if the call fails."""
