from pathlib import Path

from supervisor.io import load_task_contract


def test_load_task_contract_from_yaml() -> None:
    path = Path("examples/cited_market_research/task_contract.yaml")
    contract = load_task_contract(path)
    assert contract.task == "Produce a cited competitor brief"
