from __future__ import annotations

from datetime import datetime, timezone

from orchestrator.evidence.ledger import append_evidence
from orchestrator.evidence.models import ProviderEvidence


def test_candidate_engine_benchmark_report_is_generated_without_running_engines(tmp_path) -> None:
    import scripts.benchmark_candidate_engines as benchmark

    evidence_path = tmp_path / "provider_evidence.jsonl"
    report_path = tmp_path / "candidate_engine_benchmark.md"
    now = datetime(2026, 7, 4, tzinfo=timezone.utc)
    append_evidence(
        ProviderEvidence(
            evidence_id="ev-1",
            run_id="run-benchmark",
            market="CN",
            ticker="600519.SH",
            data_domain="daily_bar",
            provider="akshare+tushare",
            provider_ticker="akshare:600519;tushare:600519.SH",
            source_updated_at=now,
            observed_at=now,
            normalized_payload={"price_diff_pct": {"close": 0.0}},
            raw_field_mapping={},
            quality_flags=["adjustment_unverified:none"],
            cross_source_status="matched",
            gate_status="warn",
            allowed_downstream=["alphasift_exploratory", "vectorbt"],
            notes="test evidence",
        ),
        evidence_path,
    )

    result = benchmark.benchmark_candidate_engines(
        evidence_path=evidence_path,
        report_path=report_path,
    )
    report = report_path.read_text(encoding="utf-8")

    assert result["engine_count"] == 3
    assert "| alphasift | candidate_engine_candidate | pending_runtime |" in report
    assert "| qlib | factor_model_research_backbone | blocked_by_panel_data |" in report
    assert "| vectorbt_event_baseline | validation_baseline | ready |" in report
    assert "Not run by this benchmark" in report
    assert "stock recommendation" not in report.lower()
