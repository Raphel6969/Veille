"""
Synthetic cited market-research LangGraph workflow (Phase 1).

The agent business logic is unchanged from Phase 0, but run instrumentation now
goes through the Supervisor SDK instead of a manual event collector. Wasteful
patterns (duplicate search, retries) are embedded for policy testing and are
recorded but never acted on (observe-only).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from langgraph.graph import END, StateGraph

from examples.cited_market_research.mock_tools import (
    fetch_source,
    normalize_input,
    search_competitors,
    synthesize_brief,
)
from examples.cited_market_research.trace_capture import validate_brief
from supervisor.adapters.langgraph.adapter import LangGraphInstrumentedAdapter
from supervisor.adapters.litellm.mock import LiteLLMMockAdapter
from supervisor.contracts.events import EventType
from supervisor.io import load_task_contract, save_trace_fixture
from supervisor.memory import MemoryTier
from supervisor.policy import StopRun, evaluate, evaluate_observe
from supervisor.sdk import Supervisor


def _enforcement_enabled() -> bool:
    return os.environ.get("SUPERVISOR_ENFORCE", "").lower() in ("1", "true", "yes")


def _planning_enabled() -> bool:
    return os.environ.get("SUPERVISOR_PLAN", "").lower() in ("1", "true", "yes")


def _memory_enabled() -> bool:
    return os.environ.get("SUPERVISOR_MEMORY", "").lower() in ("1", "true", "yes")


MASTER_CONTEXT: list[str] = [
    "question What AI runtime supervision competitors exist in 2026?",
    "policy Approved sources must be dated within 12 months and vendor-neutral.",
    "competitor LangChain and LangGraph are the most cited orchestration frameworks.",
    "competitor AgentOps and LangSmith focus on observability for agent runs.",
    "evidence Verified evidence requires a linked primary source per material claim.",
    "rubric Brief must compare at least eight competitors with a comparison table.",
    "constraint Cost must stay under the task contract budget; retries are bounded.",
    "audience The brief is read by a platform engineering lead making a build/buy call.",
    "format Output must be a markdown table plus a short risk summary.",
    "This is a very long planning history slice that should be compressed when not "
    "directly relevant to the current step because it contains verbose background "
    "notes about earlier meetings, internal debates, and deprecated alternatives "
    "that are no longer part of the recommended approach for this engagement.",
]

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


def researcher_node(
    state: AgentState, supervisor: Supervisor, adapter: LiteLLMMockAdapter
) -> AgentState:
    with supervisor.node(step_id="research", agent_id="researcher", role="researcher"):
        if _planning_enabled():
            supervisor.context(
                step_id="research",
                agent_id="researcher",
                role="researcher",
                master_context=MASTER_CONTEXT,
            )
            routing = supervisor.route_model(
                step_id="research", agent_id="researcher", capability="research"
            )
        else:
            supervisor.context(
                step_id="research",
                agent_id="researcher",
                role="researcher",
                included=["question", "source policy", "open questions"],
                excluded=["UI choices", "deployment logs"],
                compressed=["planning history -> decision summary"],
                estimated_tokens=600,
                reason="Researcher needs the question, sourcing rules, and open questions.",
            )
            routing = None
        include_duplicates = state["scenario"] == "expensive"
        search = search_competitors(state["query"], include_duplicates=include_duplicates)
        query_hash = normalize_input("search_competitors", {"query": state["query"]})
        supervisor.tool(
            step_id="research",
            agent_id="researcher",
            tool_name="search_competitors",
            input={"query": state["query"]},
            fn=lambda: search,
            normalized_input_hash=query_hash,
            duration_ms=80.0,
            cost_usd=0.002,
            idempotent=True,
        )
        if include_duplicates:
            supervisor.tool(
                step_id="research",
                agent_id="researcher",
                tool_name="search_competitors",
                input={"query": state["query"]},
                fn=lambda: search,
                normalized_input_hash=query_hash,
                duplicate=True,
                duration_ms=80.0,
                cost_usd=0.002,
                idempotent=True,
            )
        if routing is not None:
            supervisor.model(
                step_id="research",
                agent_id="researcher",
                model=routing.model,
                prompt=f"Plan evidence collection for: {state['query']}",
                adapter=adapter,
                routing=routing,
            )
        else:
            supervisor.model(
                step_id="research",
                agent_id="researcher",
                model="mock-research",
                prompt=f"Plan evidence collection for: {state['query']}",
                adapter=adapter,
            )
        if _memory_enabled():
            supervisor.remember(
                step_id="research",
                agent_id="researcher",
                content=f"Prior query context: {state['query']}",
                tier=MemoryTier.LONG,
                confidence=0.9,
            )
            supervisor.retrieve_memory(
                step_id="research",
                agent_id="researcher",
                role="researcher",
                query=state["query"],
            )
        return {
            **state,
            "role": "analyst",
            "competitors": search["competitors"],
            "duplicate_search_count": search["call_count"] - 1,
        }


def analyst_node(
    state: AgentState, supervisor: Supervisor, adapter: LiteLLMMockAdapter
) -> AgentState:
    with supervisor.node(step_id="analysis", agent_id="analyst", role="analyst"):
        if _planning_enabled():
            supervisor.context(
                step_id="analysis",
                agent_id="analyst",
                role="analyst",
                master_context=MASTER_CONTEXT,
            )
            analysis_routing = supervisor.route_model(
                step_id="analysis", agent_id="analyst", capability="analysis"
            )
        else:
            supervisor.context(
                step_id="analysis",
                agent_id="analyst",
                role="analyst",
                included=["verified evidence", "rubric", "constraints"],
                excluded=["duplicate pages", "stale traces"],
                compressed=["raw browsing -> verified claims"],
                estimated_tokens=1200,
                reason="Analyst needs verified evidence and the acceptance rubric.",
            )
            analysis_routing = None
        evidence: list[dict[str, Any]] = []
        fail_retries = state["scenario"] == "expensive"
        for competitor in state["competitors"]:
            first = fetch_source(competitor["name"], fail_first_attempt=fail_retries)
            if fail_retries:
                supervisor.retry(
                    step_id="analysis",
                    agent_id="analyst",
                    tool_name="fetch_source",
                    competitor=competitor["name"],
                    attempt=1,
                )
                def _fetch_failed(f: Any = first) -> Any:
                    return f

                supervisor.tool(
                    step_id="analysis",
                    agent_id="analyst",
                    tool_name="fetch_source",
                    input={"competitor_name": competitor["name"]},
                    fn=_fetch_failed,
                    normalized_input_hash=normalize_input(
                        "fetch_source", {"competitor_name": competitor["name"]}
                    ),
                    failed=True,
                    duration_ms=60.0,
                    cost_usd=0.001,
                    idempotent=True,
                    status="error",
                    error_message="transient_fetch_error",
                )
                supervisor.retry(
                    step_id="analysis",
                    agent_id="analyst",
                    tool_name="fetch_source",
                    competitor=competitor["name"],
                    attempt=2,
                )
                result = fetch_source(competitor["name"], fail_first_attempt=False)
            else:
                result = first

            def _fetch_ok(r: Any = result) -> Any:
                return r

            h = normalize_input("fetch_source", {"competitor_name": competitor["name"]})
            supervisor.tool(
                step_id="analysis",
                agent_id="analyst",
                tool_name="fetch_source",
                input={"competitor_name": competitor["name"]},
                fn=_fetch_ok,
                normalized_input_hash=h,
                duration_ms=45.0,
                cost_usd=0.001,
                idempotent=True,
            )
            evidence.append(result)
        if analysis_routing is not None:
            supervisor.model(
                step_id="analysis",
                agent_id="analyst",
                model=analysis_routing.model,
                prompt="Verify evidence coverage and open questions.",
                adapter=adapter,
                routing=analysis_routing,
            )
        else:
            supervisor.model(
                step_id="analysis",
                agent_id="analyst",
                model="mock-research",
                prompt="Verify evidence coverage and open questions.",
                adapter=adapter,
            )
        return {**state, "role": "writer", "evidence": evidence, "retry_count": 0}


def writer_node(
    state: AgentState, supervisor: Supervisor, adapter: LiteLLMMockAdapter
) -> AgentState:
    with supervisor.node(step_id="writing", agent_id="writer", role="writer"):
        if _planning_enabled():
            supervisor.context(
                step_id="writing",
                agent_id="writer",
                role="writer",
                master_context=MASTER_CONTEXT,
            )
            writing_routing = supervisor.route_model(
                step_id="writing", agent_id="writer", capability="synthesis"
            )
        else:
            supervisor.context(
                step_id="writing",
                agent_id="writer",
                role="writer",
                included=["verified facts", "audience", "format"],
                excluded=["tool errors", "unused raw context"],
                compressed=["evidence -> draft sections"],
                estimated_tokens=1400,
                reason="Writer needs verified facts and the output format.",
            )
            writing_routing = None
        omit_citations = state["scenario"] == "failed_validation"
        brief = synthesize_brief(state["evidence"], omit_citations=omit_citations)
        supervisor.tool(
            step_id="writing",
            agent_id="writer",
            tool_name="synthesize_brief",
            input={"evidence_count": len(state["evidence"])},
            fn=lambda: brief,
            normalized_input_hash=normalize_input(
                "synthesize_brief", {"evidence_count": len(state["evidence"])}
            ),
            duration_ms=90.0,
            cost_usd=0.003,
            idempotent=True,
        )
        if writing_routing is not None:
            supervisor.model(
                step_id="writing",
                agent_id="writer",
                model=writing_routing.model,
                prompt="Draft cited competitor brief.",
                adapter=adapter,
                routing=writing_routing,
            )
        else:
            supervisor.model(
                step_id="writing",
                agent_id="writer",
                model="mock-synthesis",
                prompt="Draft cited competitor brief.",
                adapter=adapter,
            )
        return {**state, "role": "done", "brief": brief}


def build_graph(supervisor: Supervisor, adapter: LiteLLMMockAdapter) -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("researcher", lambda s: researcher_node(s, supervisor, adapter))
    graph.add_node("analyst", lambda s: analyst_node(s, supervisor, adapter))
    graph.add_node("writer", lambda s: writer_node(s, supervisor, adapter))
    graph.set_entry_point("researcher")
    graph.add_edge("researcher", "analyst")
    graph.add_edge("analyst", "writer")
    graph.add_edge("writer", END)
    return graph.compile()


def run_scenario(scenario: Literal["success", "expensive", "failed_validation"]) -> dict[str, Any]:
    task = load_task_contract(TASK_CONTRACT_PATH)
    enforce = _enforcement_enabled()
    supervisor = Supervisor(task, enforce=enforce)
    supervisor.scenario = scenario
    adapter = LiteLLMMockAdapter(use_mock=True)

    if _planning_enabled():
        supervisor.plan()
    supervisor.start_run()
    graph = build_graph(supervisor, adapter)
    instrumented = LangGraphInstrumentedAdapter().attach(
        graph, supervisor, auto_run_lifecycle=False
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
    final: AgentState = initial
    stopped = False
    try:
        final = instrumented.invoke(initial)
    except StopRun:
        stopped = True

    if stopped:
        report = validate_brief(supervisor.run_id, task.task_id, {})
        supervisor.finish_run("error")
    else:
        report = validate_brief(supervisor.run_id, task.task_id, final["brief"])
        supervisor.emit_validation(report)
        supervisor.finish_run("pass" if report.task_contract_met else "fail")

    batch = supervisor.to_batch()
    if enforce:
        _, policy_events = evaluate(
            batch,
            enforce=True,
            max_cost_usd=task.constraints.max_cost_usd,
            max_latency_seconds=task.constraints.max_latency_seconds,
        )
    else:
        _, policy_events = evaluate_observe(batch)
    for event in policy_events:
        supervisor.collector.append(event)
    batch = supervisor.to_batch(
        metadata={
            "scenario": scenario,
            "enforcement_enabled": enforce,
            "task_contract_met": report.task_contract_met,
            "total_cost_usd": round(
                sum(e.cost_usd or 0.0 for e in supervisor.collector.events()), 4
            ),
            "duplicate_search_count": final.get("duplicate_search_count", 0),
            "retry_count": sum(
                1
                for e in supervisor.collector.events()
                if e.event_type == EventType.RETRY_SCHEDULED
            ),
            "validation": report.model_dump(),
        }
    )
    return {
        "run_id": supervisor.run_id,
        "scenario": scenario,
        "brief": final.get("brief", {}),
        "batch": batch,
        "validation": report,
        "total_cost_usd": sum(e.cost_usd or 0.0 for e in batch.events),
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
        scenarios = [
            cast("Literal['success', 'expensive', 'failed_validation']", args.scenario)
        ]

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
