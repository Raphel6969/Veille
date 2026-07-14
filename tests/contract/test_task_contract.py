from pathlib import Path

import yaml

from supervisor.contracts.task import RiskLevel, TaskContract

TASK_YAML = Path("examples/cited_market_research/task_contract.yaml")


def test_task_contract_round_trip() -> None:
    with TASK_YAML.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    contract = TaskContract.from_yaml_dict(data)
    assert contract.task_id == "cited-competitor-brief-001"
    assert contract.risk_level == RiskLevel.MEDIUM
    assert contract.constraints.max_cost_usd == 1.0
    assert len(contract.quality_checks) == 3

    dumped = contract.model_dump()
    restored = TaskContract.model_validate(dumped)
    assert restored == contract


def test_task_contract_schema_version() -> None:
    contract = TaskContract(
        task_id="t1",
        task="test",
    )
    assert contract.schema_version == "0.1.0"
