from __future__ import annotations

from datetime import datetime, timezone

from orchestrator.evidence.ledger import append_evidence
from orchestrator.evidence.models import ProviderEvidence


def test_validate_alphasift_reuse_without_local_repo_writes_pending_report(
    tmp_path,
    monkeypatch,
) -> None:
    import scripts.validate_alphasift_reuse as validate_script

    ledger_path = tmp_path / "provider_evidence.jsonl"
    report_path = tmp_path / "alphasift_reuse_validation.md"
    candidate_path = tmp_path / "candidate_evidence.jsonl"
    now = datetime(2026, 7, 4, tzinfo=timezone.utc)
    append_evidence(
        ProviderEvidence(
            evidence_id="ev-1",
            run_id="run-009",
            market="CN",
            ticker="600519.SH",
            data_domain="daily_bar",
            provider="akshare+tushare",
            provider_ticker="akshare:600519;tushare:600519.SH",
            source_updated_at=now,
            observed_at=now,
            normalized_payload={"compared_fields": ["close"], "price_diff_pct": {"close": 0.0}},
            raw_field_mapping={"akshare": {"close": "收盘"}, "tushare": {"close": "close"}},
            quality_flags=["adjustment_unverified:none"],
            cross_source_status="matched",
            gate_status="warn",
            allowed_downstream=["alphasift_exploratory"],
            notes="test evidence",
        ),
        ledger_path,
    )
    monkeypatch.delenv("ALPHASIFT_PATH", raising=False)

    result = validate_script.validate_alphasift_reuse(
        evidence_path=ledger_path,
        report_path=report_path,
        candidate_path=candidate_path,
        local_project_paths=[tmp_path / "missing-alphasift"],
    )

    report = report_path.read_text(encoding="utf-8")
    assert result["reuse_validation_status"] == "pending_external_project_validation"
    assert result["candidate_evidence_written"] is False
    assert "missing_repo" in report
    assert "adapter_input_preview" in report
    assert not candidate_path.exists()
