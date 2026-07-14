"""Environment + safe-configuration diagnostics for `veille doctor`."""

from __future__ import annotations

import platform
from typing import Any

from supervisor.console.config import get_settings, secret_for_provider
from supervisor.console.connections import list_connections
from supervisor.console.run_registry import list_adapters, list_workflows
from supervisor.routing.router import ModelRegistry


def _runtime_version() -> str:
    try:
        from supervisor import __version__

        return __version__
    except Exception:  # noqa: BLE001
        return "0.2.0"


def doctor_payload() -> dict[str, Any]:
    settings = get_settings()
    adapters = list_adapters()
    connections = list_connections(real_mode=settings.real_mode)
    models = [c.name for c in ModelRegistry().candidates]
    warnings: list[str] = []
    if settings.real_mode and any(c.status == "real-missing" for c in connections):
        warnings.append("Real mode enabled but one or more providers are missing credentials.")
    if settings.cache_approved and not settings.optimize:
        warnings.append(
            "Cross-run cache approval set but optimization is off; cache will not serve."
        )
    if settings.enforce and not settings.real_mode:
        warnings.append("Enforcement enabled in mock mode; only advisory policies will trigger.")

    return {
        "python_version": platform.python_version(),
        "runtime_version": _runtime_version(),
        "installed_adapters": [a.name for a in adapters if a.status == "installed"],
        "registered_workflows": [w.name for w in list_workflows()],
        "registered_providers": [c.provider for c in connections],
        "registered_models": models,
        "execution_mode": settings.mode,
        "policy_mode": "observe",
        "enforce_enabled": settings.enforce,
        "optimize_enabled": settings.optimize,
        "cross_run_cache": {
            "approved": settings.cache_approved,
            "backend": settings.cache_backend,
        },
        "litellm_status": "real-ready" if _ready("litellm", settings) else "mock",
        "openrouter_status": "real-ready" if _ready("openrouter", settings) else "mock",
        "openai_router_status": "real-ready" if _ready("openai", settings) else "mock",
        "safe_config_warnings": warnings,
    }


def _ready(name: str, settings: Any) -> bool:
    return settings.real_mode and bool(secret_for_provider(name))
