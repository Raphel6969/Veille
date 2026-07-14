"""Phase 1 run-explorer CLI.

Examples
--------
    python -m supervisor.cli explore --run fixtures/traces/expensive_run.json
    python -m supervisor.cli explore --live --scenario expensive --otel
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Literal

from supervisor.analytics import summarize
from supervisor.contracts.events import RunEventBatch
from supervisor.io import load_trace_fixture
from supervisor.policy import evaluate_observe
from supervisor.telemetry import ConsoleOTelExporter


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
    from typing import cast

    from examples.cited_market_research.agent import run_scenario

    scenario_lit = cast(
        "Literal['success', 'expensive', 'failed_validation']", scenario
    )
    result = run_scenario(scenario_lit)
    return _print_summary(result["batch"], show_policy, show_otel)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI Runtime Supervisor run explorer (Phase 1).")
    sub = parser.add_subparsers(dest="command", required=True)

    explore = sub.add_parser("explore", help="Inspect a supervised run.")
    src = explore.add_mutually_exclusive_group(required=True)
    src.add_argument("--run", metavar="PATH", help="Path to a trace fixture JSON.")
    src.add_argument("--live", action="store_true", help="Run the demo workflow live.")
    explore.add_argument("--scenario", default="success", help="Demo scenario (live only).")
    explore.add_argument("--policy", action="store_true", help="Show observe-only policy flags.")
    explore.add_argument("--otel", action="store_true", help="Print OTel-style spans.")

    args = parser.parse_args(argv)

    if args.command == "explore":
        if args.live:
            return _run_live(args.scenario, args.policy, args.otel)
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

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
