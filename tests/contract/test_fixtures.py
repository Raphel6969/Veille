from pathlib import Path

import pytest

from supervisor.io import load_trace_fixture

TRACES_DIR = Path("fixtures/traces")

EXPECTED_FIXTURES = [
    "success_run.json",
    "expensive_run.json",
    "failed_validation_run.json",
]


@pytest.mark.parametrize("filename", EXPECTED_FIXTURES)
def test_trace_fixture_loads_and_validates(filename: str) -> None:
    path = TRACES_DIR / filename
    assert path.exists(), f"Missing fixture: {path}. Run agent with --write-fixtures."
    batch = load_trace_fixture(path)
    assert batch.schema_version == "0.1.0"
    assert batch.run_id
    assert batch.task_id == "cited-competitor-brief-001"
    assert len(batch.events) > 0


def test_success_fixture_metadata() -> None:
    batch = load_trace_fixture(TRACES_DIR / "success_run.json")
    assert batch.metadata.get("scenario") == "success"
    assert batch.metadata.get("task_contract_met") is True


def test_expensive_fixture_has_duplicates_and_retries() -> None:
    batch = load_trace_fixture(TRACES_DIR / "expensive_run.json")
    assert batch.metadata.get("scenario") == "expensive"
    dup_events = [
        e
        for e in batch.events
        if e.tool_name == "search_competitors" and e.attributes.get("duplicate")
    ]
    assert len(dup_events) >= 1
    retry_events = [e for e in batch.events if e.event_type.value.startswith("retry.")]
    assert len(retry_events) >= 1


def test_failed_validation_fixture() -> None:
    batch = load_trace_fixture(TRACES_DIR / "failed_validation_run.json")
    assert batch.metadata.get("task_contract_met") is False
