"""Validation for the cited market-research demo workflow.

Run-collection moved into the Supervisor SDK (``supervisor.sdk.RunCollector``);
this module keeps the demo-specific output validation only.
"""

from __future__ import annotations

from typing import Any

from supervisor.contracts.validation import CheckResult, ValidationReport


def validate_brief(
    run_id: str,
    task_id: str,
    brief: dict[str, Any],
) -> ValidationReport:
    checks: list[CheckResult] = []

    fields_ok = bool(brief.get("competitors_count", 0) >= 8) and bool(brief.get("comparison_table"))
    checks.append(
        CheckResult(
            check_id="required_fields_present",
            passed=fields_ok,
            message="Eight competitors and comparison table required.",
        )
    )

    table = brief.get("comparison_table") or []
    citations_ok = all(bool(row.get("source")) for row in table)
    checks.append(
        CheckResult(
            check_id="citations_valid",
            passed=citations_ok,
            message="Every material claim must have a linked source.",
        )
    )

    names = [row.get("competitor") for row in table]
    no_dups = len(names) == len(set(names))
    checks.append(
        CheckResult(
            check_id="no_duplicate_competitors",
            passed=no_dups,
            message="Competitor list must not contain duplicates.",
        )
    )

    passed = all(c.passed for c in checks)
    return ValidationReport(
        run_id=run_id,
        task_id=task_id,
        task_contract_met=passed,
        checks=checks,
        confidence=1.0 if passed else 0.4,
        unresolved_issues=[] if passed else ["validation_failed"],
    )
