from supervisor.cli import main


def test_explore_run_fixture(capsys: object) -> None:
    rc = main(["explore", "--run", "fixtures/traces/success_run.json"])
    assert rc == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Run" in out
    assert "validation" in out


def test_exec_runs_a_python_application_and_saves_a_trace(tmp_path: object, capsys: object) -> None:
    app = tmp_path / "app.py"  # type: ignore[operator]
    app.write_text("print('application ran')\n")  # type: ignore[union-attr]
    traces = tmp_path / "traces"  # type: ignore[operator]

    rc = main(["exec", str(app), "--trace-dir", str(traces)])  # type: ignore[arg-type]

    assert rc == 0
    assert "application ran" in capsys.readouterr().out  # type: ignore[attr-defined]
    assert list(traces.glob("*.json"))  # type: ignore[union-attr]
