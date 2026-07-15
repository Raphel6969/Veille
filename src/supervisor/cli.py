"""Veille Local Integration Console CLI.

Reuses the existing runtime, analytics, policy, and explorer surface rather than
re-implementing them. All opt-in safety flags stay on the SUPERVISOR_* prefix; the
console owns the VEILLE_* connection/config layer. No secret is ever printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from supervisor.analytics import summarize
from supervisor.console.config import get_settings
from supervisor.console.connections import list_connections, validate_connection
from supervisor.console.doctor import doctor_payload
from supervisor.console.explorer import explore
from supervisor.console.run_registry import (
    get_workflow,
    list_adapters,
    list_runs,
    list_workflows,
    load_run,
    run_workflow,
)
from supervisor.contracts.events import RunEventBatch
from supervisor.contracts.preflight import ContextSource, PreflightRequest
from supervisor.io import load_task_contract, load_trace_fixture, save_trace_fixture
from supervisor.policy import evaluate_observe
from supervisor.runtime import run_script
from supervisor.sdk import Supervisor
from supervisor.telemetry import ConsoleOTelExporter

# Ensure repo-root packages (e.g. the ``examples`` package) are importable when
# veille is launched as a console script from an arbitrary working directory.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _print_summary(batch: RunEventBatch, show_policy: bool, show_otel: bool) -> int:
    summary = summarize(batch)
    print(summary.to_text())

    if show_policy:
        triggers, _ = evaluate_observe(batch)
        print("\nPolicy (observe-only):")
        if not triggers:
            print("  no triggers")
        for t in triggers:
            print(f"  - {t.policy_id}: {t.reason}")

    if show_otel:
        exporter = ConsoleOTelExporter()
        exporter.export_events(batch.events)
    return 0


def _run_live(scenario: str, show_policy: bool, show_otel: bool) -> int:
    from examples.cited_market_research.agent import run_scenario

    result = run_scenario(scenario)  # type: ignore[arg-type]
    return _print_summary(result["batch"], show_policy, show_otel)


def _doctor(args: argparse.Namespace) -> int:
    payload = doctor_payload()
    print("Veille Local Integration Console — doctor")
    print(f"  python:              {payload['python_version']}")
    print(f"  runtime version:     {payload['runtime_version']}")
    print(f"  installed adapters:  {', '.join(payload['installed_adapters']) or 'none'}")
    print(f"  registered workflows:{', '.join(payload['registered_workflows'])}")
    print(f"  registered providers:{', '.join(payload['registered_providers'])}")
    print(f"  registered models:   {', '.join(payload['registered_models'])}")
    print(f"  execution mode:      {payload['execution_mode']}")
    print(f"  policy mode:         {payload['policy_mode']} (warn/enforce via SUPERVISOR_ENFORCE)")
    print(f"  enforce enabled:     {payload['enforce_enabled']}")
    print(f"  optimize enabled:    {payload['optimize_enabled']}")
    print(
        f"  cross-run cache:     approved={payload['cache_approved']} "
        f"backend={payload['cache_backend']}"
    )
    print(f"  litellm status:      {payload['litellm_status']}")
    print(f"  openrouter status:   {payload['openrouter_status']}")
    print(f"  openai router:       {payload['router_status']}")
    print("  safe configuration warnings:")
    if not payload["warnings"]:
        print("    none")
        return 0
    for w in payload["warnings"]:
        print(f"    ! {w}")
    return 0


def _connections(args: argparse.Namespace) -> int:
    if args.action == "validate" and args.provider:
        ok, reason = validate_connection(args.provider, real=args.real)
        print(f"{'OK' if ok else 'FAIL'} {args.provider}: {reason}")
        return 0 if ok else 1
    for c in list_connections(real_mode=get_settings().real_mode):
        print(f"{c.provider:12} | status={c.status:12} | env={c.env_var:20} | key={c.masked_key}")
        print(f"               models: {', '.join(c.supported_models)}")
    return 0


def _workflows(args: argparse.Namespace) -> int:
    if args.action == "inspect" and args.name:
        wf = get_workflow(args.name)
        if wf is None:
            print(f"Unknown workflow: {args.name}", file=sys.stderr)
            return 2
        print(f"Workflow: {wf.name}")
        print(f"  description:    {wf.description}")
        print(f"  framework:      {wf.framework}")
        print(f"  supports real:  {wf.supports_real}")
        print(f"  read-only tools:{wf.read_only_tools}")
        print(f"  scenarios:      {', '.join(wf.default_scenarios)}")
        return 0
    for wf in list_workflows():
        print(f"{wf.name:22} | {wf.framework:10} | real={wf.supports_real} | {wf.description}")
    return 0


def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    scenario = "success"
    if args.input:
        p = Path(args.input)
        if p.exists():
            try:
                data = json.loads(p.read_text("utf-8"))
                scenario = data.get("scenario", scenario)
            except Exception:  # noqa: BLE001
                scenario = args.input
        else:
            scenario = args.input
    if settings.real_mode and not args.yes:
        print("Real execution requires confirmation. Re-run with --yes.", file=sys.stderr)
        return 1
    try:
        result = run_workflow(args.workflow, scenario=scenario)
    except Exception as exc:  # noqa: BLE001
        print(f"Workflow failed: {exc}", file=sys.stderr)
        return 1
    batch: RunEventBatch = result["batch"]
    save_trace_fixture(batch, Path("fixtures/traces") / f"{batch.run_id}.json")
    print(f"Run {batch.run_id} saved. Mode={settings.mode}.")
    return _print_summary(batch, show_policy=args.policy, show_otel=False)


def _runs(args: argparse.Namespace) -> int:
    if args.action == "show" and args.run_id:
        try:
            view = explore(load_run(args.run_id))
        except Exception as exc:  # noqa: BLE001
            print(f"Cannot load run: {exc}", file=sys.stderr)
            return 2
        print(f"Run {args.run_id} — task {view['task_id']}")
        s = view["summary"]
        c = view["cache"]
        p = view["policy"]
        print(
            f"  cost=${s['total_cost_usd']:.4f} "
            f"tokens in/out {s['total_tokens_in']}/{s['total_tokens_out']}"
        )
        print(f"  cache served={c['served']} misses={c['misses']}")
        print(
            f"  policy events={len(p['policy_events'])} "
            f"interventions={len(p['intervention_events'])}"
        )
        print(f"  validation: {view['validation']}")
        return 0
    for r in list_runs():
        print(f"{r.run_id} | task={r.task_id} | scenario={r.scenario}")
    return 0


def _providers(args: argparse.Namespace) -> int:
    for name in [c.provider for c in list_connections(real_mode=get_settings().real_mode)]:
        print(name)
    return 0


def _adapters(args: argparse.Namespace) -> int:
    for a in list_adapters():
        print(f"{a.name:16} | {a.status:14} | {a.description}")
    if getattr(args, "toggle", None) and not args.yes:
        print("Enable/disable requires confirmation (--yes).", file=sys.stderr)
        return 1
    return 0


def _demo(args: argparse.Namespace) -> int:
    settings = get_settings()
    if args.kind == "mock":
        result = run_workflow("cited_market_research", scenario="success")
        return _print_summary(result["batch"], show_policy=args.policy, show_otel=False)
    if args.kind == "real-world":
        if settings.real_mode and not args.yes:
            print("Real execution requires confirmation. Re-run with --yes.", file=sys.stderr)
            return 1
        from examples.real_world_demo.agent import run_scenario

        if args.cross_run:
            import tempfile

            from supervisor.optimize.cache import FileCacheBackend

            backend = FileCacheBackend(tempfile.mkdtemp(prefix="sup_cache_"))
            r1 = run_scenario("success", cache_backend=backend)
            r2 = run_scenario("success", cache_backend=backend)
            print(
                json.dumps(
                    {
                        "mode": "cross-run",
                        "run1_cost_usd": r1["total_cost_usd"],
                        "run2_cost_usd": r2["total_cost_usd"],
                        "cross_run_saving_usd": round(
                            r1["total_cost_usd"] - r2["total_cost_usd"], 4
                        ),
                    },
                    indent=2,
                )
            )
            return 0
        result = run_scenario("success")
        return _print_summary(result["batch"], show_policy=args.policy, show_otel=False)
    return 1


def _serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn  # lazy: optional dependency
    except Exception as exc:  # noqa: BLE001
        print(
            f"uvicorn is required for the web console. Install the 'ui' extra. ({exc})",
            file=sys.stderr,
        )
        return 1
    from supervisor.console.server import app

    print(f"Veille console serving on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def _exec(args: argparse.Namespace) -> int:
    """Run an application through the same runtime used by the SDK."""
    try:
        result = run_script(Path(args.script), args.script_args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except BaseException as exc:  # noqa: BLE001
        print(f"Application failed: {exc}", file=sys.stderr)
        return 1

    if args.trace_dir:
        destination = Path(args.trace_dir) / f"{result.batch.run_id}.json"
        save_trace_fixture(result.batch, destination)
        print(f"Veille trace saved: {destination}")
    print(f"Runtime mode=observe run={result.batch.run_id} exit={result.exit_code}")
    return result.exit_code


def _preflight(args: argparse.Namespace) -> int:
    try:
        task = load_task_contract(args.task_contract)
    except Exception as exc:  # noqa: BLE001
        print(f"Cannot load task contract: {exc}", file=sys.stderr)
        return 2
    context = [
        ContextSource(source_id=str(index), content=value)
        for index, value in enumerate(args.context or [])
    ]
    proposal = Supervisor(task).preflight(
        PreflightRequest(
            task_contract=task, master_context=context, allowed_models=args.model or []
        )
    )
    payload = proposal.model_dump(mode="json")
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Preflight proposal saved: {destination}")
    print(
        f"Proposal {proposal.proposal_id}: tier={proposal.execution_plan.selected_tier.value} "
        f"steps={len(proposal.execution_plan.steps)} routes={len(proposal.route_recommendations)}"
    )
    return 0


def _add_subparsers(sub: argparse._SubParsersAction[Any]) -> None:
    explore = sub.add_parser("explore", help="Inspect a supervised run.")
    src = explore.add_mutually_exclusive_group(required=True)
    src.add_argument("--run", metavar="PATH", help="Path to a trace fixture JSON.")
    src.add_argument("--live", action="store_true", help="Run the demo workflow live.")
    explore.add_argument("--scenario", default="success", help="Demo scenario (live only).")
    explore.add_argument("--policy", action="store_true", help="Show observe-only policy flags.")
    explore.add_argument("--otel", action="store_true", help="Print OTel-style spans.")

    def _explore_dispatch(a: argparse.Namespace) -> int:
        if a.live:
            return _run_live(a.scenario, a.policy, a.otel)
        return _explore_file(a)

    explore.set_defaults(func=_explore_dispatch)

    doctor = sub.add_parser("doctor", help="Report environment + safe-config status.")
    doctor.set_defaults(func=_doctor)

    connections = sub.add_parser("connections", help="List/validate provider connections.")
    connections.add_argument("action", nargs="?", choices=["list", "validate"], default="list")
    connections.add_argument("provider", nargs="?", help="Provider name (validate).")
    connections.add_argument("--real", action="store_true", help="Validate real (credential) mode.")
    connections.set_defaults(func=_connections)

    workflows = sub.add_parser("workflows", help="List/inspect registered workflows.")
    workflows.add_argument("action", nargs="?", choices=["list", "inspect"], default="list")
    workflows.add_argument("name", nargs="?", help="Workflow name (inspect).")
    workflows.set_defaults(func=_workflows)

    run = sub.add_parser("run", help="Execute a workflow through the runtime.")
    run.add_argument("workflow", help="Registered workflow name.")
    run.add_argument("--input", help="Scenario name or path to input JSON.")
    run.add_argument("--yes", action="store_true", help="Confirm real execution.")
    run.add_argument("--policy", action="store_true", help="Show observe-only policy flags.")
    run.set_defaults(func=_run)

    runs = sub.add_parser("runs", help="List/inspect saved runs.")
    runs.add_argument("action", nargs="?", choices=["list", "show"], default="list")
    runs.add_argument("run_id", nargs="?", help="Run id (show).")
    runs.set_defaults(func=_runs)

    providers = sub.add_parser("providers", help="List registered providers.")
    providers.add_argument("action", nargs="?", choices=["list"], default="list")
    providers.set_defaults(func=_providers)

    adapters = sub.add_parser("adapters", help="List installed adapters.")
    adapters.add_argument("action", nargs="?", choices=["list"], default="list")
    adapters.set_defaults(func=_adapters)

    demo = sub.add_parser("demo", help="Run a built-in demo.")
    demo.add_argument("kind", choices=["mock", "real-world"])
    demo.add_argument("--cross-run", action="store_true", help="Use durable cross-run cache.")
    demo.add_argument("--policy", action="store_true")
    demo.add_argument("--yes", action="store_true", help="Confirm real execution.")
    demo.set_defaults(func=_demo)

    serve = sub.add_parser("serve", help="Start the web console (FastAPI).")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=_serve)

    execute = sub.add_parser(
        "exec", help="Run a Python application through the shared observe-mode runtime."
    )
    execute.add_argument("script", help="Python application path.")
    execute.add_argument("--trace-dir", help="Optional directory for the normalized run trace.")
    execute.add_argument(
        "script_args",
        nargs="*",
        help="Arguments passed to the app (place them after --).",
    )
    execute.set_defaults(func=_exec)

    preflight = sub.add_parser("preflight", help="Create an advisory plan before agent execution.")
    preflight.add_argument("task_contract", help="Path to a task-contract YAML file.")
    preflight.add_argument("--context", action="append", help="Labelled master-context slice.")
    preflight.add_argument("--model", action="append", help="Allowed model (repeatable).")
    preflight.add_argument("--output", help="Write the proposal JSON to this path.")
    preflight.set_defaults(func=_preflight)


def _explore_file(args: argparse.Namespace) -> int:
    path = Path(args.run)
    if not path.exists():
        print(f"Fixture not found: {path}", file=sys.stderr)
        return 2
    try:
        batch = load_trace_fixture(path)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to load fixture: {exc}", file=sys.stderr)
        return 2
    return _print_summary(batch, args.policy, args.otel)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Veille Local Integration Console.")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_subparsers(sub)

    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
