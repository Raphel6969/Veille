"""Provider connection discovery + validation (safe, masked)."""

from __future__ import annotations

from dataclasses import dataclass

from supervisor.adapters.providers import get_provider, list_providers
from supervisor.console.config import mask_secret, provider_env_var, secret_for_provider
from supervisor.routing.router import ModelCandidate


@dataclass
class ConnectionInfo:
    provider: str
    env_var: str
    key_present: bool
    masked_key: str
    status: str  # "mock" | "real-ready" | "real-missing"
    supported_models: list[str]


def list_connections(real_mode: bool = False) -> list[ConnectionInfo]:
    out: list[ConnectionInfo] = []
    for name in list_providers():
        env_var = provider_env_var(name)
        secret = secret_for_provider(name)
        if real_mode and secret:
            status = "real-ready"
        elif real_mode:
            status = "real-missing"
        else:
            status = "mock"
        # supported models: derive from the real candidate list in the registry
        models = [
            c.name for c in _registry_candidates() if _provider_for_model(c.name) == name
        ] or [f"{name}/<model>"]
        out.append(
            ConnectionInfo(
                provider=name,
                env_var=env_var,
                key_present=bool(secret),
                masked_key=mask_secret(secret),
                status=status,
                supported_models=models,
            )
        )
    return out


def _registry_candidates() -> list[ModelCandidate]:
    from supervisor.routing.router import ModelRegistry

    return ModelRegistry().candidates


def _provider_for_model(model: str) -> str:
    from supervisor._provider_util import _derive_provider

    return _derive_provider(model)


def validate_connection(provider: str, *, real: bool = False) -> tuple[bool, str]:
    """Validate a provider connection. Mock is always valid; real requires a key.

    Never performs a network call here — reachability is confirmed separately and
    only after explicit user confirmation.
    """
    if provider not in list_providers():
        return False, f"Unknown provider: {provider}"
    if not real:
        return True, "Mock mode: no credentials required."
    secret = secret_for_provider(provider)
    if not secret:
        return False, f"Missing credential for {provider} (set {provider_env_var(provider)})."
    prov = get_provider(provider, use_mock=False)
    if not prov.is_configured(use_mock=False):
        return False, f"Provider {provider} is not configured."
    return True, f"Real mode ready for {provider} (credential present, masked)."
