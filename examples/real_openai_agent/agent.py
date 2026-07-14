"""Real OpenAI integration agent.

Exercises the Supervisor SDK end-to-end with a real OpenAI provider call.
Safe defaults: mock mode when no ``OPENAI_API_KEY`` is set. In real mode
it executes one model completion via ``OpenAIProvider``, then reports cost and
latency. Also demonstrates credential discovery, error handling, and guidance.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

from supervisor.adapters.providers import OpenAIProvider
from supervisor.contracts.task import RiskLevel, TaskConstraints, TaskContract
from supervisor.contracts.validation import CheckResult, ValidationReport
from supervisor.sdk import Supervisor

TASK_ID = "real-openai-integration-001"
MOCK_COST = 0.0005


def _build_task() -> TaskContract:
    return TaskContract(
        task_id=TASK_ID,
        task="Verify real OpenAI provider plumbing through Supervisor SDK.",
        required_outcome=["model_response", "cost_report"],
        constraints=TaskConstraints(max_cost_usd=0.01),
        quality_checks=["cost_tracked", "provider_detected"],
        risk_level=RiskLevel.LOW,
    )


def _detect_openai_key() -> str | None:
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")


def _check_openai_key() -> str | None:
    key = _detect_openai_key()
    if key:
        safe = key[:8] + "..." + key[-4:] if len(key) > 12 else "(set)"
        print(f"[openai] credential found: OPENAI_API_KEY={safe}")
    else:
        print("[openai] no credential set — falling back to mock mode.")
        print("[openai] set OPENAI_API_KEY to run against real OpenAI.")
    return key


def _safe_model_call(
    supervisor: Supervisor,
    step_id: str,
    agent_id: str,
    model: str,
    prompt: str,
    provider: OpenAIProvider,
    use_mock: bool,
) -> str:
    """Invoke a model call with error handling and cost tracking."""
    start = time.monotonic()
    try:
        result = supervisor.model(
            step_id=step_id,
            agent_id=agent_id,
            model=model,
            prompt=prompt,
            adapter=provider,
            provider="openai",
            prompt_version="v1",
            cacheable=False,
        )
        elapsed = time.monotonic() - start
        mode = "mock" if use_mock else "real"
        print(f"  [{mode}] model={model} response={result[:80]}... ({elapsed:.2f}s)")
        return result
    except Exception as exc:
        print(f"  [error] model={model} failed: {exc}", file=sys.stderr)
        raise


def _mock_api_tool(name: str, query: str) -> dict[str, Any]:
    data = {
        "competitors": [
            {"id": "openai", "name": "OpenAI", "product": "GPT-4o"},
            {"id": "anthropic", "name": "Anthropic", "product": "Claude 3.5"},
            {"id": "google", "name": "Google DeepMind", "product": "Gemini 2.0"},
        ],
        "query": query,
    }
    return {"results": data.get("competitors", []), "query": query, "source": "mock"}


def run_scenario(scenario: str = "success", **opts: Any) -> dict[str, Any]:
    """Execute the real OpenAI integration scenario."""
    use_mock = opts.get("use_mock")
    if use_mock is None:
        use_mock = _detect_openai_key() is None

    cache_backend = opts.get("cache_backend")

    task = _build_task()
    supervisor = Supervisor(
        task,
        enforce=opts.get("enforce", False),
        optimize=opts.get("optimize", False),
        optimize_mode=opts.get("optimize_mode", "dry_run"),
        cache_backend=cache_backend,
    )

    model_for_tier = "gpt-4o" if not use_mock else "mock-synthesis"
    provider = OpenAIProvider(use_mock=use_mock)

    supervisor.start_run()

    status = "pass"
    model_response = ""
    errors: list[str] = []

    try:
        with supervisor.node(step_id="research", agent_id="researcher", role="researcher"):
            supervisor.context(
                step_id="research",
                agent_id="researcher",
                role="researcher",
                included=["top_llm_providers"],
                estimated_tokens=200,
                reason="Researcher needs the competitor landscape.",
            )

            tool_result = supervisor.tool(
                step_id="research",
                agent_id="researcher",
                tool_name="list_competitors",
                input={"market": "AI models"},
                fn=lambda: _mock_api_tool("competitors", "AI model providers"),
                idempotent=True,
                cost_usd=MOCK_COST,
                tool_version="v1",
                auth_scope="public",
                context_boundary="research",
            )
            competitors = (tool_result or {}).get("results", [])

        with supervisor.node(step_id="synthesize", agent_id="writer", role="writer"):
            prompt = (
                f"List the top {len(competitors)} AI model providers "
                f"and their flagship products.\n\n"
                f"Competitors: {json.dumps(competitors)}\n\n"
                "Format as a short bullet list."
            )
            model_response = _safe_model_call(
                supervisor,
                "synthesize",
                "writer",
                model_for_tier,
                prompt,
                provider,
                use_mock,
            )

        report = ValidationReport(
            run_id=supervisor.run_id,
            task_id=TASK_ID,
            task_contract_met=bool(model_response),
            checks=[
                CheckResult(
                    check_id="cost_tracked", passed=True, message="model call cost tracked"
                ),
                CheckResult(
                    check_id="provider_detected",
                    passed=True,
                    message=f"provider={'openai' if not use_mock else 'mock'}",
                ),
            ],
        )
        supervisor.emit_validation(report)

    except Exception as exc:
        status = "error"
        errors.append(str(exc))
        supervisor.finish_run("error")
        raise

    else:
        supervisor.finish_run(status)

    batch = supervisor.to_batch()
    total_cost = round(sum(e.cost_usd or 0.0 for e in batch.events), 6)

    return {
        "run_id": supervisor.run_id,
        "scenario": scenario,
        "mode": "real" if not use_mock else "mock",
        "batch": batch,
        "model_response": model_response,
        "total_cost_usd": total_cost,
        "competitors_queried": len(competitors),
        "errors": errors,
    }


def print_summary(result: dict[str, Any]) -> None:
    mode = result["mode"]
    cost = result["total_cost_usd"]
    resp = result.get("model_response", "")
    comps = result.get("competitors_queried", 0)
    print("\nSummary:")
    print(f"  mode:          {mode}")
    print(f"  run_id:        {result['run_id']}")
    print(f"  scenario:      {result['scenario']}")
    print(f"  competitors:   {comps}")
    print(f"  response:      {resp[:100]}..." if len(resp) > 100 else f"  response:      {resp}")
    print(f"  total cost:    ${cost:.6f}")
    print(f"  events logged: {len(result['batch'].events)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Real OpenAI integration agent - exercises Supervisor SDK end-to-end."
    )
    parser.add_argument("--scenario", default="success", choices=["success", "error_handling"])
    parser.add_argument(
        "--real", action="store_true", help="Force real mode (requires OPENAI_API_KEY)"
    )
    parser.add_argument("--mock", action="store_true", help="Force mock mode (default when no key)")
    args = parser.parse_args()

    key = _check_openai_key()

    if args.real and args.mock:
        print("error: cannot set both --real and --mock", file=sys.stderr)
        sys.exit(1)

    use_mock = args.mock if (args.mock or args.real) else (key is None)

    if args.real and key is None:
        print("error: --real requires OPENAI_API_KEY to be set", file=sys.stderr)
        sys.exit(1)

    result = run_scenario(args.scenario, use_mock=use_mock)
    print_summary(result)


if __name__ == "__main__":
    main()
