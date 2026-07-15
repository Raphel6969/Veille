"""Local daemon host for durable VEILLE pilot state."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from supervisor.storage import SQLiteProposalRepository


def create_daemon_app(database: str | Path = ".veille/veille.db") -> FastAPI:
    repository = SQLiteProposalRepository(database)
    app = FastAPI(title="Veille Daemon", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "storage": str(repository.path)}

    return app
