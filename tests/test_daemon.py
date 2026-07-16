from __future__ import annotations

from supervisor.daemon import create_daemon_app


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
