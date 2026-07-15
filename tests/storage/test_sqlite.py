from __future__ import annotations

from supervisor.contracts import PreflightRequest, TaskContract
from supervisor.preflight import build_preflight
from supervisor.storage import SQLiteProposalRepository


def test_sqlite_proposal_repository_survives_new_instance(tmp_path: object) -> None:
    proposal = build_preflight(
        PreflightRequest(task_contract=TaskContract(task_id="t", task="demo"))
    )
    path = tmp_path / "veille.db"  # type: ignore[operator]
    SQLiteProposalRepository(path).save(proposal)  # type: ignore[arg-type]

    restored = SQLiteProposalRepository(path).load(proposal.proposal_id)  # type: ignore[arg-type]
    assert restored == proposal
