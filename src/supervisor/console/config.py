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
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
# Generated dynamically from provider class attributes to avoid drift.
_PROVIDER_ENV_VARS: dict[str, str] | None = None


def _build_provider_env_vars() -> dict[str, str]:
    from supervisor.adapters.providers import get_provider, list_providers

    result: dict[str, str] = {}
    for name in list_providers():
        inst = get_provider(name)
        env_key = getattr(inst, "api_key_env", None)
        result[name] = env_key or f"{name.upper()}_API_KEY"
    return result


def provider_env_var(provider: str) -> str:
    global _PROVIDER_ENV_VARS
    if _PROVIDER_ENV_VARS is None:
        _PROVIDER_ENV_VARS = _build_provider_env_vars()
    return _PROVIDER_ENV_VARS.get(provider.lower(), f"{provider.upper()}_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> VeilleSettings:
    return VeilleSettings()


def secret_for_provider(provider: str) -> str | None:
    return os.getenv(provider_env_var(provider))
