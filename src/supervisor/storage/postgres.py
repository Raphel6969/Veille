"""Optional PostgreSQL repository for self-hosted and Supabase deployments."""

from __future__ import annotations

from typing import Any

from supervisor.contracts.events import RunEventBatch
from supervisor.contracts.preflight import PreflightProposal


class PostgresRepository:
    def __init__(self, db_url: str) -> None:
        import psycopg
        from psycopg.types.json import Jsonb

        self._psycopg = psycopg
        self._jsonb = Jsonb
        self.db_url = db_url
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS veille_project_proposals "
                "(project_id TEXT NOT NULL, proposal_id TEXT NOT NULL, payload JSONB NOT NULL, "
                "PRIMARY KEY(project_id, proposal_id))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS veille_project_runs "
                "(project_id TEXT NOT NULL, run_id TEXT NOT NULL, payload JSONB NOT NULL, "
                "PRIMARY KEY(project_id, run_id))"
            )

    def _connect(self) -> Any:
        return self._psycopg.connect(self.db_url)

    def save_project_proposal(self, project_id: str, proposal: PreflightProposal) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO veille_project_proposals(project_id, proposal_id, payload) "
                "VALUES (%s, %s, %s) "
                "ON CONFLICT(project_id, proposal_id) DO UPDATE SET payload = EXCLUDED.payload",
                (project_id, proposal.proposal_id, self._jsonb(proposal.model_dump(mode="json"))),
            )

    def load_project_proposal(self, project_id: str, proposal_id: str) -> PreflightProposal | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM veille_project_proposals "
                "WHERE project_id = %s AND proposal_id = %s",
                (project_id, proposal_id),
            ).fetchone()
        return PreflightProposal.model_validate(row[0]) if row else None

    def save_project_run(self, project_id: str, batch: RunEventBatch) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO veille_project_runs(project_id, run_id, payload) VALUES (%s, %s, %s) "
                "ON CONFLICT(project_id, run_id) DO UPDATE SET payload = EXCLUDED.payload",
                (project_id, batch.run_id, self._jsonb(batch.model_dump(mode="json"))),
            )

    def load_project_run(self, project_id: str, run_id: str) -> RunEventBatch | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM veille_project_runs WHERE project_id = %s AND run_id = %s",
                (project_id, run_id),
            ).fetchone()
        return RunEventBatch.model_validate(row[0]) if row else None
