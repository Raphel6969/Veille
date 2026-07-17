from __future__ import annotations

from supervisor.console.server import PreflightConsoleRequest, preflight_endpoint


def test_preflight_endpoint_projects_shared_runtime_proposal() -> None:
    proposal = preflight_endpoint(
        PreflightConsoleRequest(
            task_contract_path="examples/cited_market_research/task_contract.yaml",
            context=["Research question: competitors"],
        )
    )

    assert proposal["status"] == "advisory"
    assert proposal["execution_plan"]["steps"]
    assert proposal["route_recommendations"]
