"""Public VEILLE SDK.

``import veille`` is the stable developer-facing entry point. It intentionally
re-exports the existing Runtime Supervisor rather than creating a second SDK.
"""

from supervisor.runtime import RuntimeSupervisor, Supervisor
from supervisor.sdk import RunCollector

__all__ = ["RunCollector", "RuntimeSupervisor", "Supervisor"]
