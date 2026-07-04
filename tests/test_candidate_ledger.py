from __future__ import annotations

from orchestrator.candidates.ledger import append_candidate, load_candidates, summarize_candidates
from orchestrator.candidates.models import CandidateEvidence


def _candidate(candidate_id: str, ticker: str) -> CandidateEvidence:
    return CandidateEvidence(
        candidate_id=candidate_id,
        run_id="run-009",
        market="CN",
        ticker=ticker,
        candidate_date="2026-07-04",
        candidate_source="alphasift",
        candidate_direction="unknown",
        candidate_score=None,
        reasons=["contract test"],
        provider_evidence_ids=[f"ev-{ticker}"],
        provider_evidence_domains=["daily_bar"],
        quality_flags=["test_only"],
        raw_payload={"status": "parsed"},
        gate_status="warn",
        allowed_next_steps=["research"],
        notes="candidate evidence is not a recommendation",
    )


def test_candidate_ledger_append_load_and_summarize(tmp_path) -> None:
    path = tmp_path / "candidate_evidence.jsonl"
    append_candidate(_candidate("candidate-1", "600519.SH"), path)
    append_candidate(_candidate("candidate-2", "000001.SZ"), path)

    rows = load_candidates(path)
    summary = summarize_candidates(path)

    assert [row.ticker for row in rows] == ["600519.SH", "000001.SZ"]
    assert summary["total"] == 2
    assert summary["by_source"] == {"alphasift": 2}
    assert summary["by_gate_status"] == {"warn": 2}
