"""The single VEILLE runtime boundary used by every entry point.

SDKs, the CLI, future IDE integrations, and daemon hosts are thin adapters over
this module. Runtime capabilities are implemented in :class:`Supervisor` only.
"""

from supervisor.runtime.execution import ExecutionResult, run_script
from supervisor.runtime.session import ApprovedRunSession
from supervisor.sdk import Supervisor

RuntimeSupervisor = Supervisor

__all__ = ["ApprovedRunSession", "ExecutionResult", "RuntimeSupervisor", "Supervisor", "run_script"]
