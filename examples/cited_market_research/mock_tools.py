"""Deterministic mock tools for the cited market-research demo workflow."""

from __future__ import annotations

import hashlib
import json
from typing import Any

COMPETITORS: list[dict[str, str]] = [
    {"name": "AlphaCorp", "url": "https://example.com/alphacorp", "segment": "enterprise"},
    {"name": "BetaStack", "url": "https://example.com/betastack", "segment": "mid-market"},
    {"name": "GammaFlow", "url": "https://example.com/gammaflow", "segment": "smb"},
    {"name": "DeltaMind", "url": "https://example.com/deltamind", "segment": "enterprise"},
    {"name": "EpsilonAI", "url": "https://example.com/epsilonai", "segment": "startup"},
    {"name": "ZetaWorks", "url": "https://example.com/zetaworks", "segment": "mid-market"},
    {"name": "EtaCloud", "url": "https://example.com/etacloud", "segment": "enterprise"},
    {"name": "ThetaOps", "url": "https://example.com/thetaops", "segment": "smb"},
]

SOURCE_SNIPPETS: dict[str, str] = {
    "AlphaCorp": "AlphaCorp reported 18% YoY growth in Q1 2026.",
    "BetaStack": "BetaStack expanded into EU with a Frankfurt data center.",
    "GammaFlow": "GammaFlow launched a freemium tier for teams under 10 users.",
    "DeltaMind": "DeltaMind raised Series C funding for agent orchestration.",
    "EpsilonAI": "EpsilonAI partners with three Fortune 500 pilot customers.",
    "ZetaWorks": "ZetaWorks open-sourced its evaluation toolkit.",
    "EtaCloud": "EtaCloud achieved SOC 2 Type II certification.",
    "ThetaOps": "ThetaOps cut inference costs by 22% after routing changes.",
}


def normalize_input(tool_name: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps({"tool": tool_name, "input": payload}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def search_competitors(query: str, *, include_duplicates: bool = False) -> dict[str, Any]:
    """Return synthetic competitor search results."""
    results = COMPETITORS[:8]
    calls = [{"query": query, "results": results}]
    if include_duplicates:
        calls.append({"query": query, "results": results})
    return {
        "query": query,
        "competitors": results,
        "call_count": len(calls),
        "normalized_input_hash": normalize_input("search_competitors", {"query": query}),
    }


def fetch_source(competitor_name: str, *, fail_first_attempt: bool = False) -> dict[str, Any]:
    """Fetch a synthetic source snippet for a competitor."""
    attempt = 2 if fail_first_attempt else 1
    snippet = SOURCE_SNIPPETS.get(competitor_name, f"No public data for {competitor_name}.")
    return {
        "competitor": competitor_name,
        "url": next((c["url"] for c in COMPETITORS if c["name"] == competitor_name), ""),
        "snippet": snippet,
        "attempt": attempt,
        "retries": 1 if fail_first_attempt else 0,
        "normalized_input_hash": normalize_input(
            "fetch_source", {"competitor_name": competitor_name}
        ),
    }


def synthesize_brief(
    evidence: list[dict[str, Any]], *, omit_citations: bool = False
) -> dict[str, Any]:
    """Produce a structured brief from verified evidence."""
    table = [
        {
            "competitor": item["competitor"],
            "claim": item["snippet"],
            "source": "" if omit_citations else item["url"],
        }
        for item in evidence
    ]
    return {
        "competitors_count": len(evidence),
        "comparison_table": table,
        "citations_valid": not omit_citations,
        "normalized_input_hash": normalize_input(
            "synthesize_brief", {"evidence_count": len(evidence)}
        ),
    }
