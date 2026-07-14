"""Utilities for loading contracts and capturing trace fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from supervisor.contracts.events import RunEventBatch
from supervisor.contracts.task import TaskContract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = PROJECT_ROOT / "fixtures"
TRACES_DIR = FIXTURES_DIR / "traces"


def load_task_contract(path: Path | str) -> TaskContract:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return TaskContract.from_yaml_dict(data)


def load_trace_fixture(path: Path | str) -> RunEventBatch:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return RunEventBatch.model_validate(data)


def save_trace_fixture(batch: RunEventBatch, path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(batch.model_dump(mode="json"), f, indent=2)
