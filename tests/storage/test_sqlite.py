from __future__ import annotations

from supervisor.contracts import PreflightRequest, TaskContract
from supervisor.contracts.events import RunEventBatch
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


def test_sqlite_repository_persists_normalized_run_batch(tmp_path: object) -> None:
    path = tmp_path / "veille.db"  # type: ignore[operator]
    batch = RunEventBatch(run_id="run-1", task_id="t", events=[])
    SQLiteProposalRepository(path).save_run(batch)  # type: ignore[arg-type]

    assert SQLiteProposalRepository(path).load_run("run-1") == batch  # type: ignore[arg-type]


def test_project_proposals_are_isolated(tmp_path: object) -> None:
    repo = SQLiteProposalRepository(tmp_path / "veille.db")  # type: ignore[arg-type,operator]
    proposal = build_preflight(
        PreflightRequest(task_contract=TaskContract(task_id="t", task="demo"))
    )
    repo.save_project_proposal("alpha", proposal)

    assert repo.load_project_proposal("alpha", proposal.proposal_id) == proposal
    assert repo.load_project_proposal("beta", proposal.proposal_id) is None
