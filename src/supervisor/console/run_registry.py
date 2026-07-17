"""Registry of workflows, adapters, providers, and saved runs.

A single source of truth the CLI and web UI query. Discovering workflows is static
(we register the known, safe, read-only demos); adapters are detected by import
probing; providers come from the provider package. Runs are indexed from a traces
directory of ``RunEventBatch`` JSON fixtures.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from supervisor.adapters.providers import list_providers
from supervisor.contracts.events import RunEventBatch
from supervisor.io import load_trace_fixture


@dataclass
class WorkflowInfo:
    name: str
    description: str
    framework: str
    supports_real: bool
    read_only_tools: bool
    default_scenarios: list[str] = field(default_factory=list)
    run_fn: Callable[..., dict[str, Any]] | None = None


@dataclass
class AdapterInfo:
    name: str
    status: str  # "installed" | "not installed"
    description: str


@dataclass
class RunInfo:
    run_id: str
    task_id: str
    scenario: str | None
    path: str
    timestamp: str = ""


_WORKFLOWS: dict[str, WorkflowInfo] = {}


def register_workflow(info: WorkflowInfo) -> None:
    _WORKFLOWS[info.name] = info


def _register_builtins() -> None:
    if _WORKFLOWS:
        return
    from examples.cited_market_research.agent import run_scenario as mr_run
    from examples.real_world_demo.agent import run_scenario as rw_run

    register_workflow(
        WorkflowInfo(
            name="cited_market_research",
            description="Synthetic cited competitor-brief agent (mock tools).",
            framework="langgraph",
            supports_real=False,
            read_only_tools=True,
            default_scenarios=["success", "expensive", "failed_validation"],
            run_fn=lambda scenario="success", **kw: mr_run(
                scenario, apply_preflight=bool(kw.get("apply_preflight", False))
            ),
        )
    )
    register_workflow(
        WorkflowInfo(
            name="real_world_demo",
            description="SDK-embed research workflow against a read-only HTTP API.",
            framework="sdk",
            supports_real=True,
            read_only_tools=True,
            default_scenarios=["success", "expensive"],
            run_fn=lambda scenario="success", **kw: rw_run(scenario, kw.get("cache_backend")),
        )
    )
    try:  # real OpenAI integration agent (mock-first, real-opt-in)
        from examples.real_openai_agent.agent import run_scenario as ro_run

        register_workflow(
            WorkflowInfo(
                name="real_openai_agent",
                description="End-to-end OpenAI provider integration test via Supervisor SDK.",
                framework="sdk",
                supports_real=True,
                read_only_tools=True,
                default_scenarios=["success"],
                run_fn=lambda scenario="success", **kw: ro_run(scenario, **kw),
            )
        )
    except Exception:  # noqa: BLE001
        pass

    try:  # optional; only present after the langgraph_demo example is added
        from examples.langgraph_demo.agent import run_scenario as lg_run

        register_workflow(
            WorkflowInfo(
                name="langgraph_demo",
                description="Registered LangGraph workflow emitting normalized events.",
                framework="langgraph",
                supports_real=False,
                read_only_tools=True,
                default_scenarios=["success"],
                run_fn=lambda scenario="success", **kw: lg_run(scenario),
            )
        )
    except Exception:  # noqa: BLE001
        pass


def list_workflows() -> list[WorkflowInfo]:
    _register_builtins()
    return list(_WORKFLOWS.values())


def get_workflow(name: str) -> WorkflowInfo | None:
    _register_builtins()
    return _WORKFLOWS.get(name)


def run_workflow(name: str, scenario: str = "success", **opts: Any) -> dict[str, Any]:
    info = get_workflow(name)
    if info is None or info.run_fn is None:
        raise KeyError(f"Unknown workflow: {name}")
    return info.run_fn(scenario=scenario, **opts)


def list_adapters() -> list[AdapterInfo]:
    probes = [
        (
            "langgraph",
            "LangGraph callback instrumentation adapter",
            "supervisor.adapters.langgraph",
        ),
        ("openai_agents", "OpenAI Agents SDK adapter", "supervisor.adapters.openai_agents"),
        (
            "openai_responses",
            "OpenAI Responses API adapter",
            "supervisor.adapters.openai_responses",
        ),
    ]
    out: list[AdapterInfo] = []
    for name, desc, module in probes:
        try:
            __import__(module)
            status = "installed"
        except Exception:  # noqa: BLE001
            status = "not installed"
        out.append(AdapterInfo(name=name, status=status, description=desc))
    return out


def list_provider_names() -> list[str]:
    return list_providers()


def list_runs(traces_dir: str | Path = "fixtures/traces") -> list[RunInfo]:
    base = Path(traces_dir)
    if not base.exists():
        return []
    runs: list[RunInfo] = []
    for p in base.glob("*.json"):
        try:
            data = json.loads(p.read_text("utf-8"))
        except Exception:  # noqa: BLE001
            continue

        timestamp = ""
        events = data.get("events", [])
        if events:
            timestamp = events[0].get("timestamp", "")

        runs.append(
            RunInfo(
                run_id=data.get("run_id", p.stem),
                task_id=data.get("task_id", ""),
                scenario=(data.get("metadata") or {}).get("scenario"),
                path=str(p),
                timestamp=timestamp,
            )
        )
    runs.sort(key=lambda r: r.timestamp, reverse=True)
    return runs


def load_run(run_id: str, traces_dir: str | Path = "fixtures/traces") -> RunEventBatch:
    base = Path(traces_dir)
    direct = base / f"{run_id}.json"
    if direct.exists():
        return load_trace_fixture(direct)
    for p in base.glob("*.json"):
        try:
            data = json.loads(p.read_text("utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if data.get("run_id") == run_id:
            return load_trace_fixture(p)
    raise KeyError(f"Run not found: {run_id}")
