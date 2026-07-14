"""
Synthetic cited market-research LangGraph workflow.

Phase 0: standalone agent with mock tools and manual trace capture.
Wasteful patterns (duplicate search, retries) are embedded for future policy tests.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal, TypedDict
from uuid import uuid4

from langgraph.graph import END, StateGraph

from examples.cited_market_research.mock_tools import (
    fetch_source,
    search_competitors,
    synthesize_brief,
)
from examples.cited_market_research.trace_capture import TraceCapture, validate_brief
from supervisor.adapters.litellm.mock import LiteLLMMockAdapter
from supervisor.contracts.events import EventType
from supervisor.io import load_task_contract, save_trace_fixture

TASK_CONTRACT_PATH = Path(__file__).parent / "task_contract.yaml"
FIXTURES_OUT = Path(__file__).resolve().parents[2] / "fixtures" / "traces"


class AgentState(TypedDict):
    role: str
    query: str
    competitors: list[dict[str, str]]
    evidence: list[dict[str, Any]]
    brief: dict[str, Any]
    scenario: str
    total_cost_usd: float
    duplicate_search_count: int
    retry_count: int


def _model_call(
    capture: TraceCapture,
    *,
    step_id: str,
    agent_id: str,
    model: str,
    prompt: str,
    adapter: LiteLLMMockAdapter,
) -> str:
    capture.emit(
        EventType.MODEL_REQUESTED,
        step_id=step_id,
        agent_id=agent_id,
        model_name=model,
        attributes={"prompt_preview": prompt[:120]},
    )
    result = adapter.complete(model, prompt)
    capture.emit(
        EventType.MODEL_COMPLETED,
        step_id=step_id,
        agent_id=agent_id,
        model_name=model,
        duration_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=result.cost_usd,
        status="ok",
    )
    return result.content


def researcher_node(
    state: AgentState, capture: TraceCapture, adapter: LiteLLMMockAdapter
) -> AgentState:
    capture.emit(
        EventType.AGENT_STARTED,
        step_id="research",
        agent_id="researcher",
        attributes={"role": "researcher"},
    )
    include_duplicates = state["scenario"] == "expensive"
    search = search_competitors(state["query"], include_duplicates=include_duplicates)

    capture.emit(
        EventType.TOOL_REQUESTED,
        step_id="research",
        agent_id="researcher",
        tool_name="search_competitors",
        attributes={
            "input": {"query": state["query"]},
            "normalized_input_hash": search["normalized_input_hash"],
        },
    )
    capture.emit(
        EventType.TOOL_COMPLETED,
        step_id="research",
        agent_id="researcher",
        tool_name="search_competitors",
        duration_ms=80.0,
        cost_usd=0.002,
        status="ok",
        attributes={"call_count": search["call_count"]},
    )
    if include_duplicates:
        capture.emit(
            EventType.TOOL_REQUESTED,
            step_id="research",
            agent_id="researcher",
            tool_name="search_competitors",
            attributes={
                "input": {"query": state["query"]},
                "normalized_input_hash": search["normalized_input_hash"],
                "duplicate": True,
            },
        )
        capture.emit(
            EventType.TOOL_COMPLETED,
            step_id="research",
            agent_id="researcher",
            tool_name="search_competitors",
            duration_ms=80.0,
            cost_usd=0.002,
            status="ok",
            attributes={"duplicate": True},
        )

    _model_call(
        capture,
        step_id="research",
        agent_id="researcher",
        model="mock-research",
        prompt=f"Plan evidence collection for: {state['query']}",
        adapter=adapter,
    )
    capture.emit(EventType.AGENT_FINISHED, step_id="research", agent_id="researcher", status="ok")
    return {
        **state,
        "role": "analyst",
        "competitors": search["competitors"],
        "duplicate_search_count": search["call_count"] - 1,
    }


def analyst_node(
    state: AgentState, capture: TraceCapture, adapter: LiteLLMMockAdapter
) -> AgentState:
    capture.emit(
        EventType.AGENT_STARTED,
        step_id="analysis",
        agent_id="analyst",
        attributes={"role": "analyst"},
    )
    evidence: list[dict[str, Any]] = []
    fail_retries = state["scenario"] == "expensive"

    for competitor in state["competitors"]:
        first = fetch_source(competitor["name"], fail_first_attempt=fail_retries)
        if fail_retries:
            capture.emit(
                EventType.RETRY_SCHEDULED,
                step_id="analysis",
                agent_id="analyst",
                tool_name="fetch_source",
                attributes={"competitor": competitor["name"], "attempt": 1},
            )
            capture.emit(
                EventType.TOOL_REQUESTED,
                step_id="analysis",
                agent_id="analyst",
                tool_name="fetch_source",
                attributes={
                    "input": {"competitor_name": competitor["name"]},
                    "normalized_input_hash": first["normalized_input_hash"],
                    "failed": True,
                },
            )
            capture.emit(
                EventType.TOOL_COMPLETED,
                step_id="analysis",
                agent_id="analyst",
                tool_name="fetch_source",
                duration_ms=60.0,
                cost_usd=0.001,
                status="error",
                error_message="transient_fetch_error",
            )
            capture.emit(
                EventType.RETRY_COMPLETED,
                step_id="analysis",
                agent_id="analyst",
                tool_name="fetch_source",
                attributes={"competitor": competitor["name"], "attempt": 2},
            )
            result = fetch_source(competitor["name"], fail_first_attempt=False)
        else:
            result = first

        capture.emit(
            EventType.TOOL_REQUESTED,
            step_id="analysis",
            agent_id="analyst",
            tool_name="fetch_source",
            attributes={
                "input": {"competitor_name": competitor["name"]},
                "normalized_input_hash": result["normalized_input_hash"],
            },
        )
        capture.emit(
            EventType.TOOL_COMPLETED,
            step_id="analysis",
            agent_id="analyst",
            tool_name="fetch_source",
            duration_ms=45.0,
            cost_usd=0.001,
            status="ok",
        )
        evidence.append(result)

    _model_call(
        capture,
        step_id="analysis",
        agent_id="analyst",
        model="mock-research",
        prompt="Verify evidence coverage and open questions.",
        adapter=adapter,
    )
    capture.emit(EventType.AGENT_FINISHED, step_id="analysis", agent_id="analyst", status="ok")
    retries = sum(1 for e in evidence) if fail_retries else 0
    return {**state, "role": "writer", "evidence": evidence, "retry_count": retries}


def writer_node(
    state: AgentState, capture: TraceCapture, adapter: LiteLLMMockAdapter
) -> AgentState:
    capture.emit(
        EventType.AGENT_STARTED,
        step_id="writing",
        agent_id="writer",
        attributes={"role": "writer"},
    )
    omit_citations = state["scenario"] == "failed_validation"
    brief = synthesize_brief(state["evidence"], omit_citations=omit_citations)

    capture.emit(
        EventType.TOOL_REQUESTED,
        step_id="writing",
        agent_id="writer",
        tool_name="synthesize_brief",
        attributes={
            "input": {"evidence_count": len(state["evidence"])},
            "normalized_input_hash": brief["normalized_input_hash"],
        },
    )
    capture.emit(
        EventType.TOOL_COMPLETED,
        step_id="writing",
        agent_id="writer",
        tool_name="synthesize_brief",
        duration_ms=90.0,
        cost_usd=0.003,
        status="ok",
    )
    _model_call(
        capture,
        step_id="writing",
        agent_id="writer",
        model="mock-synthesis",
        prompt="Draft cited competitor brief.",
        adapter=adapter,
    )
    capture.emit(EventType.AGENT_FINISHED, step_id="writing", agent_id="writer", status="ok")
    return {**state, "role": "done", "brief": brief}


def build_graph(capture: TraceCapture, adapter: LiteLLMMockAdapter) -> StateGraph:
    graph: StateGraph = StateGraph(AgentState)

    graph.add_node("researcher", lambda s: researcher_node(s, capture, adapter))
    graph.add_node("analyst", lambda s: analyst_node(s, capture, adapter))
    graph.add_node("writer", lambda s: writer_node(s, capture, adapter))

    graph.set_entry_point("researcher")
    graph.add_edge("researcher", "analyst")
    graph.add_edge("analyst", "writer")
    graph.add_edge("writer", END)
    return graph


def run_scenario(scenario: Literal["success", "expensive", "failed_validation"]) -> dict[str, Any]:
    task = load_task_contract(TASK_CONTRACT_PATH)
    run_id = str(uuid4())
    capture = TraceCapture(run_id=run_id, task_id=task.task_id)
    adapter = LiteLLMMockAdapter(use_mock=True)

    capture.emit(
        EventType.RUN_STARTED,
        attributes={"scenario": scenario, "task": task.task},
    )

    initial: AgentState = {
        "role": "researcher",
        "query": "AI runtime supervision competitors 2026",
        "competitors": [],
        "evidence": [],
        "brief": {},
        "scenario": scenario,
        "total_cost_usd": 0.0,
        "duplicate_search_count": 0,
        "retry_count": 0,
    }

    app = build_graph(capture, adapter).compile()
    final = app.invoke(initial)

    report = validate_brief(run_id, task.task_id, final["brief"])
    capture.emit(
        EventType.VALIDATION_COMPLETED,
        status="pass" if report.task_contract_met else "fail",
        attributes={"checks": [c.model_dump() for c in report.checks]},
    )
    capture.emit(
        EventType.RUN_COMPLETED,
        status="pass" if report.task_contract_met else "fail",
        attributes={
            "duplicate_search_count": final["duplicate_search_count"],
            "retry_count": final["retry_count"],
        },
    )

    total_cost = sum(e.cost_usd or 0.0 for e in capture._events)
    batch = capture.to_batch(
        metadata={
            "scenario": scenario,
            "task_contract_met": report.task_contract_met,
            "total_cost_usd": round(total_cost, 4),
            "duplicate_search_count": final["duplicate_search_count"],
            "retry_count": final["retry_count"],
            "validation": report.model_dump(),
        }
    )
    return {
        "run_id": run_id,
        "scenario": scenario,
        "brief": final["brief"],
        "batch": batch,
        "validation": report,
        "total_cost_usd": total_cost,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run cited market-research demo scenarios.")
    parser.add_argument(
        "--scenario",
        choices=["success", "expensive", "failed_validation", "all"],
        default="success",
    )
    parser.add_argument("--write-fixtures", action="store_true", help="Write trace JSON fixtures.")
    args = parser.parse_args()

    scenarios: list[Literal["success", "expensive", "failed_validation"]]
    if args.scenario == "all":
        scenarios = ["success", "expensive", "failed_validation"]
    else:
        scenarios = [args.scenario]  # type: ignore[list-item]

    for scenario in scenarios:
        result = run_scenario(scenario)
        print(
            json.dumps(
                {
                    "scenario": scenario,
                    "run_id": result["run_id"],
                    "task_contract_met": result["validation"].task_contract_met,
                    "total_cost_usd": round(result["total_cost_usd"], 4),
                    "competitors_count": result["brief"].get("competitors_count", 0),
                },
                indent=2,
            )
        )

        if args.write_fixtures:
            out = FIXTURES_OUT / f"{scenario}_run.json"
            save_trace_fixture(result["batch"], out)
            print(f"Wrote fixture: {out}")


if __name__ == "__main__":
    main()
