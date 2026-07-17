"""Durable repositories used by local/self-hosted VEILLE hosts."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from supervisor.storage.postgres import PostgresRepository
from supervisor.storage.sqlite import SQLiteProposalRepository


class _StorageSettings(BaseSettings):
    """Environment-backed storage configuration for every runtime entry point."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_url: str = ""


def make_repository(db_url: str | None = None) -> PostgresRepository | SQLiteProposalRepository:
    """Use Postgres when DB_URL is configured; otherwise use local SQLite."""
    url = db_url or os.getenv("DB_URL") or _StorageSettings().db_url
    # Accept a value pasted as ``DB_URL=postgresql://...`` into an env editor.
    url = url.removeprefix("DB_URL=").strip()
    return PostgresRepository(url) if url else SQLiteProposalRepository()


__all__ = ["PostgresRepository", "SQLiteProposalRepository", "make_repository"]
