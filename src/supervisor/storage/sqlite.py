"""Dependency-free SQLite storage for durable preflight proposals."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from supervisor.contracts.preflight import PreflightProposal


class SQLiteProposalRepository:
    def __init__(self, path: str | Path = ".veille/veille.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS proposals (proposal_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
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
