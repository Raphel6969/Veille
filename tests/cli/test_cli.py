from supervisor.cli import main


def test_explore_run_fixture(capsys: object) -> None:
    rc = main(["explore", "--run", "fixtures/traces/success_run.json"])
    assert rc == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Run" in out
    assert "validation" in out
