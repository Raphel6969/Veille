from __future__ import annotations

import pytest

from supervisor.evaluation import sanitize_batch
from supervisor.io import load_trace_fixture

_FIXTURES = [
    "fixtures/traces/success_run.json",
    "fixtures/traces/failed_validation_run.json",
    "fixtures/traces/expensive_run.json",
]
_SENSITIVE_PARTS = (
    "prompt",
    "payload",
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "api_key",
)


def _assert_sanitized(value: object, key: str = "") -> None:
    normalized_key = key.lower().replace("-", "_")
    if any(part in normalized_key for part in _SENSITIVE_PARTS):
        assert value == "[REDACTED]"
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            _assert_sanitized(child_value, str(child_key))
    if isinstance(value, list):
        for child_value in value:
            _assert_sanitized(child_value, key)


@pytest.mark.parametrize("path", _FIXTURES)
def test_fixture_sanitization_is_deterministic_and_redacts_sensitive_fields(path: str) -> None:
    batch = load_trace_fixture(path)

    first = sanitize_batch(batch)
    second = sanitize_batch(batch)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
