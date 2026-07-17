"""Local daemon host for durable VEILLE pilot state."""

from __future__ import annotations

import os
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import FastAPI, Header, HTTPException

from supervisor.contracts.events import RunEventBatch
from supervisor.contracts.preflight import PreflightProposal
from supervisor.storage import SQLiteProposalRepository


def create_daemon_app(
    database: str | Path = ".veille/veille.db",
    *,
    token: str | None = None,
    max_inflight_writes: int = 16,
) -> FastAPI:
    repository = SQLiteProposalRepository(database)
    required_token = token or os.getenv("VEILLE_DAEMON_TOKEN")
    if max_inflight_writes < 1:
        raise ValueError("max_inflight_writes must be at least 1")
    write_slots = BoundedSemaphore(max_inflight_writes)
    app = FastAPI(title="Veille Daemon", version="0.1.0")
    app.state.write_slots = write_slots

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "storage": str(repository.path)}

    @app.get("/ready")
    def ready() -> dict[str, int | str]:
        return {
            "status": "ready",
            "storage": str(repository.path),
            "max_inflight_writes": max_inflight_writes,
        }

    def require_token(x_veille_token: str | None = Header(default=None)) -> None:
        if not required_token or x_veille_token != required_token:
            raise HTTPException(status_code=401, detail="Valid X-Veille-Token required.")

    @app.post("/projects/{project_id}/proposals")
    def save_proposal(
        project_id: str,
        proposal: PreflightProposal,
        x_veille_token: str | None = Header(default=None),
    ) -> dict[str, str]:
        require_token(x_veille_token)
        if not write_slots.acquire(blocking=False):
            raise HTTPException(
                status_code=429,
                detail="Write capacity saturated; retry with backoff.",
                headers={"Retry-After": "1"},
            )
        try:
            repository.save_project_proposal(project_id, proposal)
        finally:
            write_slots.release()
        return {"proposal_id": proposal.proposal_id, "project_id": project_id}

    @app.post("/projects/{project_id}/runs")
    def save_run(
        project_id: str,
        batch: RunEventBatch,
        x_veille_token: str | None = Header(default=None),
    ) -> dict[str, str]:
        require_token(x_veille_token)
        if not write_slots.acquire(blocking=False):
            raise HTTPException(
                status_code=429,
                detail="Write capacity saturated; retry with backoff.",
                headers={"Retry-After": "1"},
            )
        try:
            repository.save_project_run(project_id, batch)
        finally:
            write_slots.release()
        return {"run_id": batch.run_id, "project_id": project_id}

    @app.get("/projects/{project_id}/runs/{run_id}")
    def run(
        project_id: str, run_id: str, x_veille_token: str | None = Header(default=None)
    ) -> dict[str, str]:
        require_token(x_veille_token)
        found = repository.load_project_run(project_id, run_id)
        if found is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        return {"run_id": found.run_id, "project_id": project_id}

    @app.get("/projects/{project_id}/proposals/{proposal_id}")
    def proposal(
        project_id: str, proposal_id: str, x_veille_token: str | None = Header(default=None)
    ) -> dict[str, str]:
        require_token(x_veille_token)
        found = repository.load_project_proposal(project_id, proposal_id)
        if found is None:
            raise HTTPException(status_code=404, detail="Proposal not found.")
        return {"proposal_id": found.proposal_id, "project_id": project_id}

    return app
