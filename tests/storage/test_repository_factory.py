from __future__ import annotations

import supervisor.storage as storage


def test_factory_uses_sqlite_when_database_url_is_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("DB_URL", raising=False)
    monkeypatch.setattr(storage, "_StorageSettings", lambda: type("Settings", (), {"db_url": ""})())

    assert isinstance(storage.make_repository(), storage.SQLiteProposalRepository)


def test_factory_accepts_env_assignment_pasted_as_value(monkeypatch) -> None:
    captured: list[str] = []
    monkeypatch.setenv("DB_URL", "DB_URL=postgresql://example.test/veille")
    monkeypatch.setattr(storage, "PostgresRepository", captured.append)

    storage.make_repository()

    assert captured == ["postgresql://example.test/veille"]
