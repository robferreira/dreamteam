from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config import CONFIG_DIR, DEFAULT_AGENTS_BUNDLE_DIR, PROJECTS_DIR


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_version: str = "1.0.0"

    database_url: str = "postgresql+asyncpg://dreamteam:dreamteam@localhost:5432/dreamteam"
    database_url_sync: str = "postgresql+psycopg://dreamteam:dreamteam@localhost:5432/dreamteam"
    redis_url: str = "redis://localhost:6379/0"
    projects_dir: Path = PROJECTS_DIR
    agents_bundle_dir: Path = DEFAULT_AGENTS_BUNDLE_DIR

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    vllm_base_url: str = "http://localhost:8001/v1"

    embedding_model: str = "all-MiniLM-L6-v2"
    vector_dimension: int = 384

    allow_unknown_models: bool = True
    request_timeout_seconds: int = 120
    max_iterations: int = 20
    max_agent_revisits: int = 3
    display_timezone: str = "America/Sao_Paulo"

    qa_run_tests: bool = True
    qa_auto_start_servers: bool = True
    qa_api_timeout_seconds: int = 120
    qa_playwright_timeout_seconds: int = 300

    auto_provision: bool = True
    provision_skip_if_installed: bool = True
    provision_npm_timeout_seconds: int = 300
    provision_pip_timeout_seconds: int = 180

    max_recovery_attempts: int = 3

    @field_validator("projects_dir", mode="before")
    @classmethod
    def resolve_projects_dir(cls, v: Any) -> Path:
        if isinstance(v, Path):
            return v
        if isinstance(v, str) and v:
            return Path(v)
        return PROJECTS_DIR

    @field_validator("agents_bundle_dir", mode="before")
    @classmethod
    def resolve_agents_bundle_dir(cls, v: Any) -> Path:
        if isinstance(v, Path):
            return v
        if isinstance(v, str) and v:
            return Path(v)
        return DEFAULT_AGENTS_BUNDLE_DIR


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def load_providers_config() -> dict[str, Any]:
    return _load_yaml("providers.yaml")


@lru_cache
def load_system_defaults() -> dict[str, Any]:
    return _load_yaml("system_defaults.yaml")


@lru_cache
def load_cost_tiers() -> dict[str, Any]:
    return _load_yaml("cost_tiers.yaml")


@lru_cache
def load_global_settings() -> dict[str, Any]:
    defaults = load_system_defaults()
    return {
        "max_iterations": defaults.get("max_iterations", 20),
        "max_agent_revisits": defaults.get("max_agent_revisits", 3),
        "max_revisions": defaults.get("max_revisions", 2),
        "max_recovery_attempts": get_settings().max_recovery_attempts,
    }
