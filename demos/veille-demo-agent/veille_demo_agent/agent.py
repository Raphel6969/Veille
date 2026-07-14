"""Minimal agent that runs under Veille's runtime supervisor.

No API keys needed — runs in mock mode by default.
"""

import json

from supervisor.adapters.litellm.mock import LiteLLMMockAdapter
from supervisor.contracts.task import RiskLevel, TaskConstraints, TaskContract
from supervisor.contracts.validation import CheckResult, ValidationReport
from supervisor.sdk import Supervisor

MOCK_COMPETITORS = [
    {"id": "agent_a", "name": "Agent A", "note": "fast"},
    {"id": "agent_b", "name": "Agent B", "note": "accurate"},
]


def run() -> dict:
    task = TaskContract(
        task_id="demo-001",
        task="Quickstart demo: research + summarise.",
        constraints=TaskConstraints(max_cost_usd=0.01),
        risk_level=RiskLevel.LOW,
    )
    supervisor = Supervisor(task)
    adapter = LiteLLMMockAdapter(use_mock=True)

    supervisor.start_run()

    with supervisor.node(step_id="research", agent_id="researcher", role="researcher"):
        supervisor.context(
            step_id="research",
            agent_id="researcher",
            role="researcher",
            included=["query"],
            estimated_tokens=50,
            reason="Researcher needs the query.",
        )
        result = supervisor.tool(
            step_id="research",
            agent_id="researcher",
            tool_name="search",
            input={"q": "agent supervision tools"},
            fn=lambda: MOCK_COMPETITORS,
            cost_usd=0.001,
        )

    with supervisor.node(step_id="synthesize", agent_id="writer", role="writer"):
        text = supervisor.model(
            step_id="synthesize",
            agent_id="writer",
            model="mock-synthesis",
            prompt=f"Summarise: {json.dumps(result)}",
            adapter=adapter,
        )

    report = ValidationReport(
        run_id=supervisor.run_id,
        task_id="demo-001",
        task_contract_met=True,
        checks=[CheckResult(check_id="demo", passed=True, message="demo complete")],
    )
    supervisor.emit_validation(report)
    supervisor.finish_run("pass")

    batch = supervisor.to_batch()
    total_cost = round(sum(e.cost_usd or 0.0 for e in batch.events), 6)

    print(f"run_id={supervisor.run_id}  events={len(batch.events)}  cost=${total_cost}")
    print(f"response: {text[:100]}...")
    return {"run_id": supervisor.run_id, "cost": total_cost}


if __name__ == "__main__":
    run()
