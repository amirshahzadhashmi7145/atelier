"""Runtime settings, read from the environment.

The default model provider is `fake`: a local stand-in that returns
structurally valid plans so the loop can be learned without an API key.
Set LLM_PROVIDER=openai and LLM_API_KEY to call a real model.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./atelier.db"
    llm_provider: str = "fake"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    run_max_iterations: int = 16
    run_max_seconds: float = 300
    run_max_tokens: int = 40000
    check_timeout_seconds: int = 120
    check_sandbox: bool = True
    sandbox_image: str = "python:3.12-slim"
    sandbox_node_image: str = "node:20-slim"
    sandbox_memory: str = "256m"
    sandbox_cpus: str = "1"
    sandbox_pids_limit: int = 64
    github_token: str = ""
    github_api_url: str = "https://api.github.com"
    # Comma-separated hosts agents may pull packages from (FR-DEV-8).
    allowed_dependency_hosts: str = (
        "pypi.org,files.pythonhosted.org,registry.npmjs.org,"
        "proxy.golang.org,sum.golang.org,crates.io,static.crates.io,rubygems.org"
    )
    default_spend_ceiling_tokens: int = 1_000_000
    spend_alert_thresholds: str = "50,80,95"
    task_estimate_s_tokens: int = 12_000
    task_estimate_m_tokens: int = 24_000
    spend_estimate_multiple: float = 2.0
    spend_estimate_margin: float = 1.5
    workspaces_dir: str = "./workspaces"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def spend_alert_threshold_list(self) -> list[int]:
        values: list[int] = []
        for part in self.spend_alert_thresholds.split(","):
            text = part.strip()
            if not text:
                continue
            values.append(int(text))
        return values

    @property
    def allowed_dependency_host_set(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_dependency_hosts.split(",") if item.strip()}
