from __future__ import annotations

from orchestrator.candidates.models import CandidateEvidence


def test_candidate_evidence_round_trip_keeps_provider_evidence_ids() -> None:
    candidate = CandidateEvidence(
        candidate_id="candidate-1",
        run_id="run-009",
        market="CN",
        ticker="600519.SH",
        candidate_date="2026-07-04",
        candidate_source="alphasift",
        candidate_direction="unknown",
        candidate_score=None,
        reasons=["reuse validation payload only"],
        provider_evidence_ids=["ev-1"],
        provider_evidence_domains=["daily_bar"],
        quality_flags=["pending_external_project_validation"],
        raw_payload={"status": "pending_external_project_validation"},
        gate_status="warn",
        allowed_next_steps=["research"],
        notes="Not a signal or recommendation.",
    )

    payload = candidate.to_dict()
    restored = CandidateEvidence.from_dict(payload)

    assert restored == candidate
    assert restored.provider_evidence_ids == ["ev-1"]
    assert "final_confidence" not in payload
    assert restored.candidate_score is None
