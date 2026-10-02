from app.config import Settings
from app.gateway.base import LlmClient
from app.gateway.fake import FakeLlm
from app.gateway.openai_compatible import OpenAiCompatibleLlm


def build_llm(settings: Settings) -> LlmClient:
    if settings.llm_provider == "fake":
        return FakeLlm()
    if settings.llm_provider == "openai":
        return OpenAiCompatibleLlm(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
    raise RuntimeError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Use fake or openai.")
