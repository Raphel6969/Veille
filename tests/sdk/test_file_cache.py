"""Durable (cross-run) cache backend tests + cross-run serving via Supervisor."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

from examples.real_world_demo.agent import run_scenario

from supervisor.contracts.events import EventType
from supervisor.optimize.cache import FileCacheBackend


def test_file_backend_put_get_and_expiry() -> None:
    d = tempfile.mkdtemp()
    b = FileCacheBackend(d, default_ttl_seconds=300.0)
    b.put("k", {"v": 1}, ttl_seconds=300.0)
    assert b.get("k") == {"v": 1}
    data = {"k2": {"value": "x", "expires_at": time.time() - 1}}
    Path(d, "cache.json").write_text(json.dumps(data))
    assert b.get("k2") is None


def test_file_backend_cross_run_instance() -> None:
    d = tempfile.mkdtemp()
    w = FileCacheBackend(d)
    w.put("shared", "payload", ttl_seconds=300.0)
    r = FileCacheBackend(d)
    assert r.get("shared") == "payload"


def test_supervisor_cross_run_serves_duplicate() -> None:
    d = tempfile.mkdtemp()
    env = {
        "SUPERVISOR_OPTIMIZE": "1",
        "SUPERVISOR_OPTIMIZE_MODE": "active",
        "SUPERVISOR_CACHE_APPROVED": "1",
    }
    prev = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        run1 = run_scenario("success", cache_backend=FileCacheBackend(d))
        run2 = run_scenario("success", cache_backend=FileCacheBackend(d))
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    assert run1["total_cost_usd"] == 0.008
    # Run 2 serves all three searches cross-run (exact-identical inputs cached by
    # run 1); only the two fetches execute -> 0.004 vs run 1's 0.008.
    assert run2["total_cost_usd"] == 0.004
    applied = [e for e in run2["batch"].events if e.event_type == EventType.OPTIMIZATION_APPLIED]
    assert len(applied) >= 2
