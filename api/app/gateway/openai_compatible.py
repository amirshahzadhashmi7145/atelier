"""An OpenAI-compatible chat endpoint.

Any host that speaks POST /chat/completions can sit behind this class:
OpenAI itself, a proxy, or a local server. The planning service only
sees LlmResult.
"""

import json

import httpx

from app.errors import DomainError
from app.gateway.base import LlmResult


class OpenAiCompatibleLlm:
    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self.provider = "openai"
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def complete_json(self, *, purpose: str, system: str, user: str) -> LlmResult:
        if not self._api_key:
            raise DomainError(
                "LLM_API_KEY is empty. Set it, or switch LLM_PROVIDER back to fake.",
                status_code=503,
            )
        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self.model,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=90,
            )
            response.raise_for_status()
            body = response.json()
        except DomainError:
            raise
        except httpx.HTTPError as exc:
            raise DomainError(f"The model provider failed: {exc}", status_code=502) from exc

        try:
            content = body["choices"][0]["message"]["content"]
            data = _extract_json(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise DomainError(
                "The model did not return a JSON object. Nothing was saved.",
                status_code=502,
            ) from exc
        usage = body.get("usage") or {}
        return LlmResult(
            data=data,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            provider=self.provider,
            model=self.model,
        )


def _extract_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.startswith("json"):
            text = text[4:]
        fence = text.rfind("```")
        if fence != -1:
            text = text[:fence]
    parsed = json.loads(text.strip())
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("expected an object", text, 0)
    return parsed
