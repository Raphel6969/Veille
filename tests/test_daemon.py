from __future__ import annotations

from supervisor.daemon import create_daemon_app


def test_daemon_app_has_health_endpoint(tmp_path: object) -> None:
    app = create_daemon_app(tmp_path / "veille.db")  # type: ignore[operator]
    assert any(route.path == "/health" for route in app.routes)
