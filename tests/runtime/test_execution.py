from __future__ import annotations

from supervisor.runtime import run_script


def test_run_script_uses_normal_main_semantics_and_restores_argv(tmp_path: object) -> None:
    path = tmp_path / "app.py"  # type: ignore[operator]
    path.write_text("import sys\nassert sys.argv[1:] == ['--name', 'veil']\n")  # type: ignore[union-attr]

    result = run_script(path, ["--name", "veil"])  # type: ignore[arg-type]

    assert result.exit_code == 0
    assert result.batch.metadata["entry_point"] == "cli"
    assert [event.event_type.value for event in result.batch.events] == [
        "run.started",
        "agent.started",
        "agent.finished",
        "run.completed",
    ]
