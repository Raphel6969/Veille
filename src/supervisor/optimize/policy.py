"""Approved cache policy (v0.2.0 design-partner validated rules).

Encodes the three explicit cache rules approved from partner feedback:

  1. `search_competitors` is cacheable only for *identical normalized inputs*
     (exact match). Near-duplicate / semantic matches are never served.
  2. Cache keys MUST include tenant/project, tool version, policy version, and
     the relevant authorization + context boundaries.
  3. Default TTL of 300s is acceptable only once partners confirm freshness is
     sufficient; expired or uncertain results MUST re-execute (never served).

Serving additionally requires partner confirmation (gate): at least
``require_partner_confirmations`` partners must confirm the cacheable unit and
freshness policy, with no material stale-result concern. This is encoded as the
``approved`` property; it can be satisfied by enough confirmations or an
explicit override (e.g. ``SUPERVISOR_CACHE_APPROVED=1`` for demos/tests).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

DEFAULT_CACHEABLE_TOOLS = frozenset({"search_competitors"})
DEFAULT_CACHEABLE_MODELS: frozenset[str] = frozenset()
DEFAULT_TTL_SECONDS = 300.0
DEFAULT_CONFIRMATION_THRESHOLD = 3


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class CachePolicy:
    """Explicit, partner-validated caching rules."""

    cacheable_tools: set[str] = field(default_factory=lambda: set(DEFAULT_CACHEABLE_TOOLS))
    cacheable_models: set[str] = field(default_factory=lambda: set(DEFAULT_CACHEABLE_MODELS))
    require_exact_input: bool = True
    include_boundaries: bool = True
    default_ttl_seconds: float = DEFAULT_TTL_SECONDS
    require_partner_confirmations: int = DEFAULT_CONFIRMATION_THRESHOLD
    partner_confirmations: int = 0
    approved_override: bool = False

    @property
    def approved(self) -> bool:
        """True only when enough partners confirmed, or an explicit override is set."""
        return (
            self.approved_override
            or self.partner_confirmations >= self.require_partner_confirmations
        )

    def is_cacheable_tool(self, tool_name: str) -> bool:
        return tool_name in self.cacheable_tools

    def is_cacheable_model(self, model: str) -> bool:
        return model in self.cacheable_models

    def may_serve(self, match_type: str) -> bool:
        """Only exact, confident matches may be served; uncertain must re-execute."""
        if not self.require_exact_input:
            return True
        return match_type == "exact"


def build_cache_key(
    resource: str,
    normalized_input: str,
    *,
    tenant: str = "default",
    project: str = "default",
    tool_version: str = "unversioned",
    policy_version: str = "unversioned",
    auth_scope: str = "default",
    context_boundary: str = "default",
) -> str:
    """Composite cache key including isolation + version + boundary dimensions.

    Rule 2: tenant/project + tool/policy version + authorization/context boundaries
    are part of the key so a cached result is only reused within the same
    isolation and governance context.
    """
    if not isinstance(resource, str):
        resource = str(resource)
    parts = [
        f"tenant={tenant}",
        f"project={project}",
        f"resource={resource}",
        f"tool_version={tool_version}",
        f"policy_version={policy_version}",
        f"auth={auth_scope}",
        f"ctx={context_boundary}",
        f"input={_hash(normalized_input)}",
    ]
    return "|".join(parts)
