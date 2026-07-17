"""Execution envelopes for thin VEILLE entry points.

The envelope deliberately observes an arbitrary Python program without changing
its business logic. Rich model/tool events require the SDK or a framework
adapter; this boundary gives every entry point the same run lifecycle and trace
format in the meantime.
"""

from __future__ import annotations

import runpy
import sys
from dataclasses import dataclass
from pathlib import Path

from supervisor.contracts.events import RunEventBatch
from supervisor.contracts.task import TaskContract
from supervisor.sdk import Supervisor


@dataclass(frozen=True)
class ExecutionResult:
    """Result of running a Python script through the shared runtime."""

    exit_code: int
    batch: RunEventBatch


def run_script(path: Path, script_args: list[str] | None = None) -> ExecutionResult:
    """Run *path* as ``__main__`` inside an observe-mode Supervisor envelope.

    This uses Python's normal script semantics and restores ``sys.argv`` after
    execution. It does not monkeypatch providers or alter application calls.
    """
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Application script not found: {resolved}")

    runtime = Supervisor(
        TaskContract(
            task_id=f"script:{resolved.stem}",
            task=f"Execute {resolved.name}",
            metadata={"entry_point": "cli", "script_path": str(resolved)},
        )
    )
    runtime.start_run()
    previous_argv = sys.argv
    exit_code = 0
    try:
        sys.argv = [str(resolved), *(script_args or [])]
        with runtime.node(step_id="application", agent_id="application", role="application"):
            runpy.run_path(str(resolved), run_name="__main__")
    except SystemExit as exc:
        exit_code = int(exc.code) if isinstance(exc.code, int) else 1
    except BaseException as exc:
        exit_code = 1
        runtime.finish_run("error")
        raise exc
    else:
        runtime.finish_run("ok" if exit_code == 0 else "error")
    finally:
        sys.argv = previous_argv

    return ExecutionResult(
        exit_code=exit_code,
        batch=runtime.to_batch(
            {"entry_point": "cli", "mode": "observe", "script_path": str(resolved)}
        ),
    )
