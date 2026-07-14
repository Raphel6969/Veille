"""Local Integration Console — configuration (VEILLE_* namespace).

Keeps the runtime opt-in flags on the existing SUPERVISOR_* prefix (read directly
by the SDK) and introduces VEILLE_* only for the console/connection layer:
real-mode, provider selection, model, cache backend, and local tool API base URL.

No secret is ever stored on a model field that serializes to JSON. Provider keys
are read on demand via os.getenv and only ever displayed masked.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class VeilleSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    real_mode: bool = False
    provider: str = "litellm"
    model: str = ""
    tool_api_base_url: str = ""
    cache_backend: str = "memory"
    cache_approved: bool = False
    optimize: bool = False
    enforce: bool = False
    context_compression: bool = False
    context_diversification: bool = False

    @property
    def mode(self) -> str:
        return "real" if self.real_mode else "mock"


def mask_secret(value: str | None) -> str:
    if not value:
        return "(not set)"
    if len(value) <= 4:
        return "•" * len(value)
    return "…" + value[-4:]


# Provider -> environment variable that holds its credential.
PROVIDER_ENV_VARS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "litellm": "OPENAI_API_KEY",  # litellm routes through OpenAI-compatible creds by default
    "ollama": "OLLAMA_BASE_URL",
    "lmstudio": "LMSTUDIO_BASE_URL",
}


def provider_env_var(provider: str) -> str:
    return PROVIDER_ENV_VARS.get(provider.lower(), f"{provider.upper()}_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> VeilleSettings:
    return VeilleSettings()


def secret_for_provider(provider: str) -> str | None:
    return os.getenv(provider_env_var(provider))
