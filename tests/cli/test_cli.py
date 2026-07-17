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


def test_preflight_writes_an_advisory_proposal(tmp_path: object, capsys: object) -> None:
    output = tmp_path / "proposal.json"  # type: ignore[operator]

    rc = main(
        [
            "preflight",
            "examples/cited_market_research/task_contract.yaml",
            "--context",
            "Research question: competitors",
            "--output",
            str(output),
        ]
    )

    assert rc == 0
    assert "Proposal" in capsys.readouterr().out  # type: ignore[attr-defined]
    assert output.exists()  # type: ignore[union-attr]


def test_run_proposal_requires_approval(tmp_path: object, capsys: object) -> None:
    proposal = tmp_path / "proposal.json"  # type: ignore[operator]
    proposal.write_text('{"status":"advisory"}')  # type: ignore[union-attr]

    rc = main(["run", "cited_market_research", "--proposal", str(proposal)])

    assert rc == 1
    assert "requires explicit --approve" in capsys.readouterr().err  # type: ignore[attr-defined]


def test_run_approved_proposal_uses_registered_workflow(tmp_path: object) -> None:
    proposal = tmp_path / "proposal.json"  # type: ignore[operator]
    proposal.write_text('{"status":"advisory"}')  # type: ignore[union-attr]

    assert main(["run", "cited_market_research", "--proposal", str(proposal), "--approve"]) == 0


def test_compare_prints_normalized_run_metrics(capsys: object) -> None:
    rc = main(["compare", "fixtures/traces/success_run.json", "fixtures/traces/expensive_run.json"])

    assert rc == 0
    assert "cost_usd" in capsys.readouterr().out  # type: ignore[attr-defined]
