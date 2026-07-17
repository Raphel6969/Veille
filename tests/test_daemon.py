from __future__ import annotations

from fastapi.testclient import TestClient

from supervisor.contracts import PreflightRequest, TaskContract
from supervisor.daemon import create_daemon_app
from supervisor.preflight import build_preflight


def test_daemon_app_has_health_endpoint(tmp_path: object) -> None:
    app = create_daemon_app(tmp_path / "veille.db")  # type: ignore[operator]
    assert any(route.path == "/health" for route in app.routes)


def test_daemon_project_endpoint_declares_token_header(tmp_path: object) -> None:
    app = create_daemon_app(tmp_path / "veille.db", token="test-token")  # type: ignore[operator]
    route = next(
        route
        for route in app.routes
        if route.path == "/projects/{project_id}/proposals/{proposal_id}"
    )
    assert route.path == "/projects/{project_id}/proposals/{proposal_id}"


def test_daemon_persists_project_proposal_with_token(tmp_path: object) -> None:
    client = TestClient(create_daemon_app(tmp_path / "veille.db", token="test-token"))  # type: ignore[operator]
    proposal = build_preflight(
        PreflightRequest(task_contract=TaskContract(task_id="t", task="demo"))
    )

    denied = client.post("/projects/alpha/proposals", json=proposal.model_dump(mode="json"))
    saved = client.post(
        "/projects/alpha/proposals",
        json=proposal.model_dump(mode="json"),
        headers={"X-Veille-Token": "test-token"},
    )
    loaded = client.get(
        f"/projects/alpha/proposals/{proposal.proposal_id}",
        headers={"X-Veille-Token": "test-token"},
    )

    assert denied.status_code == 401
    assert saved.status_code == 200
    assert loaded.json()["proposal_id"] == proposal.proposal_id
