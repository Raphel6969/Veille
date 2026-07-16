"""Dependency-free SQLite storage for durable preflight proposals."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from supervisor.contracts.events import RunEventBatch
from supervisor.contracts.preflight import PreflightProposal


class SQLiteProposalRepository:
    def __init__(self, path: str | Path = ".veille/veille.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS proposals "
                "(proposal_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS project_proposals "
                "(project_id TEXT NOT NULL, proposal_id TEXT NOT NULL, payload TEXT NOT NULL, "
                "PRIMARY KEY(project_id, proposal_id))"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def save(self, proposal: PreflightProposal) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO proposals(proposal_id, payload) VALUES (?, ?)",
                (proposal.proposal_id, proposal.model_dump_json()),
            )

    def load(self, proposal_id: str) -> PreflightProposal | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM proposals WHERE proposal_id = ?", (proposal_id,)
            ).fetchone()
        return PreflightProposal.model_validate_json(row[0]) if row else None

    def list_ids(self) -> list[str]:
        with self._connect() as conn:
            return [
                str(row[0])
                for row in conn.execute("SELECT proposal_id FROM proposals ORDER BY proposal_id")
            ]

    def save_run(self, batch: RunEventBatch) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs(run_id, payload) VALUES (?, ?)",
                (batch.run_id, batch.model_dump_json()),
            )

    def load_run(self, run_id: str) -> RunEventBatch | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return RunEventBatch.model_validate_json(row[0]) if row else None

    def save_project_proposal(self, project_id: str, proposal: PreflightProposal) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO project_proposals(project_id, proposal_id, payload) "
                "VALUES (?, ?, ?)",
                (project_id, proposal.proposal_id, proposal.model_dump_json()),
            )

    def load_project_proposal(self, project_id: str, proposal_id: str) -> PreflightProposal | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM project_proposals WHERE project_id = ? AND proposal_id = ?",
                (project_id, proposal_id),
            ).fetchone()
        return PreflightProposal.model_validate_json(row[0]) if row else None
