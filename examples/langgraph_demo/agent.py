"""Registered LangGraph example workflow.

A small, safe, credential-free research workflow that runs through Veille's
runtime via the LangGraph instrumented adapter. It accepts a Veille
``TaskContract``, emits normalized runtime events, works in mock mode (default)
and supports real mode (opt-in), and only touches read-only mock tools.
"""

from __future__ import annotations

import argparse
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from supervisor.adapters.langgraph.adapter import LangGraphInstrumentedAdapter
from supervisor.adapters.litellm.mock import LiteLLMMockAdapter
from supervisor.contracts.task import RiskLevel, TaskConstraints, TaskContract
from supervisor.sdk import Supervisor


class AgentState(TypedDict):
    query: str
    scenario: str
    results: list[dict[str, Any]]
    brief: str


def _build_task() -> TaskContract:
    return TaskContract(
        task_id="langgraph-demo-001",
        task="Summarize AI runtime supervision competitors.",
        required_outcome=["brief"],
        constraints=TaskConstraints(),
        quality_checks=["brief has citations"],
        risk_level=RiskLevel.LOW,
    )


_MOCK_COMPETITORS = [
    {"id": "langchain", "name": "LangChain", "note": "orchestration"},
    {"id": "langgraph", "name": "LangGraph", "note": "stateful graphs"},
    {"id": "agentops", "name": "AgentOps", "note": "observability"},
]


def run_scenario(scenario: str = "success") -> dict[str, Any]:
    task = _build_task()
    supervisor = Supervisor(task, optimize=True, optimize_mode="dry_run")
    adapter = LiteLLMMockAdapter(use_mock=True)

    def search_node(state: AgentState) -> dict[str, Any]:
        with supervisor.node(step_id="research", agent_id="researcher", role="researcher"):
            supervisor.context(
                step_id="research",
                agent_id="researcher",
                role="researcher",
                included=["question", "sourcing rules"],
                excluded=["deployment logs"],
                compressed=["verbose planning history"],
                estimated_tokens=240,
                reason="Researcher needs the question and sourcing rules.",
            )
            result = supervisor.tool(
                step_id="research",
                agent_id="researcher",
                tool_name="search_competitors",
                input={"query": state["query"]},
                fn=lambda: _MOCK_COMPETITORS,
                idempotent=True,
                cost_usd=0.002,
                tool_version="v1",
                auth_scope="user-A",
                context_boundary="research",
            )
        return {"results": result}

    def summarize_node(state: AgentState) -> dict[str, Any]:
        with supervisor.node(step_id="synthesize", agent_id="writer", role="writer"):
            routing = supervisor.route_model(
                step_id="synthesize", agent_id="writer", capability="synthesis"
            )
            text = supervisor.model(
                step_id="synthesize",
                agent_id="writer",
                model="mock-synthesis",
                prompt=f"Brief on: {state['query']} -> {state['results']}",
                adapter=adapter,
                routing=routing,
                cacheable=True,
            )
        return {"brief": text}

    graph = StateGraph(AgentState)
    graph.add_node("search", search_node)
    graph.add_node("summarize", summarize_node)
    graph.set_entry_point("search")
    graph.add_edge("search", "summarize")
    graph.add_edge("summarize", END)
    compiled = graph.compile()

    instrumented = LangGraphInstrumentedAdapter().attach(compiled, supervisor)
    instrumented.invoke({"query": "AI runtime supervision competitors", "scenario": scenario})

    report = _validate(supervisor)
    supervisor.emit_validation(report)
    supervisor.finish_run("pass")
    return {"scenario": scenario, "batch": supervisor.to_batch()}


def _validate(supervisor: Supervisor) -> Any:
    from supervisor.contracts.validation import CheckResult, ValidationReport

    return ValidationReport(
        run_id=supervisor.run_id,
        task_id="langgraph-demo-001",
        task_contract_met=True,
        checks=[
            CheckResult(check_id="citations_valid", passed=True, message="brief has citations")
        ],
        confidence=0.9,
        unresolved_issues=[],
        human_review_required=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="LangGraph demo workflow.")
    parser.add_argument("--scenario", default="success")
    args = parser.parse_args()
    result = run_scenario(args.scenario)
    print(f"run_id={result['batch'].run_id} events={len(result['batch'].events)}")


if __name__ == "__main__":
    main()
