"""Local Integration Console — developer-facing CLI + web dashboard.

Extends (never replaces) the existing runtime, SDK, analytics, and policy surface.
All opt-in safety flags remain on the SUPERVISOR_* prefix; this package owns the
VEILLE_* connection/config layer and the developer-facing presentation.
"""

from supervisor.console.config import VeilleSettings, get_settings, mask_secret

__all__ = ["VeilleSettings", "get_settings", "mask_secret"]
