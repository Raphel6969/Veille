"""Local daemon host for durable VEILLE pilot state."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException

from supervisor.contracts.preflight import PreflightProposal
from supervisor.storage import SQLiteProposalRepository


def create_daemon_app(
    database: str | Path = ".veille/veille.db", *, token: str | None = None
) -> FastAPI:
    repository = SQLiteProposalRepository(database)
    required_token = token or os.getenv("VEILLE_DAEMON_TOKEN")
    app = FastAPI(title="Veille Daemon", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "storage": str(repository.path)}

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
        repository.save_project_proposal(project_id, proposal)
        return {"proposal_id": proposal.proposal_id, "project_id": project_id}

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
