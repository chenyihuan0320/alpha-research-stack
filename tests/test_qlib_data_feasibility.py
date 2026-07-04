from __future__ import annotations

from datetime import datetime, timezone

from orchestrator.evidence.ledger import append_evidence
from orchestrator.evidence.models import ProviderEvidence


def test_qlib_data_feasibility_report_marks_current_summary_as_not_runtime_ready(tmp_path) -> None:
    import scripts.check_qlib_data_feasibility as script

    evidence_path = tmp_path / "provider_evidence.jsonl"
    report_path = tmp_path / "qlib_data_feasibility.md"
    now = datetime(2026, 7, 4, tzinfo=timezone.utc)
    append_evidence(
        ProviderEvidence(
            evidence_id="ev-1",
            run_id="run-qlib",
            market="CN",
            ticker="600519.SH",
            data_domain="daily_bar",
            provider="akshare+tushare",
            provider_ticker="akshare:600519;tushare:600519.SH",
            source_updated_at=now,
            observed_at=now,
            normalized_payload={
                "compared_fields": ["open", "high", "low", "close", "volume"],
                "sample_summary": "latest common trading day summary only",
            },
            raw_field_mapping={},
            quality_flags=["adjustment_unverified:none"],
            cross_source_status="matched",
            gate_status="warn",
            allowed_downstream=["alphasift_exploratory", "vectorbt"],
            notes="summary only",
        ),
        evidence_path,
    )

    result = script.check_qlib_data_feasibility(evidence_path=evidence_path, report_path=report_path)
    report = report_path.read_text(encoding="utf-8")

    assert result["qlib_runtime_ready"] == "no"
    assert result["feasibility_status"] == "partial"
    assert "| time_series_panel | warn | complete daily_bars panel missing; current evidence is summary-level |" in report
    assert "Does not run Qlib" in report


def test_candidate_engine_benchmark_uses_qlib_feasibility_status(tmp_path) -> None:
    import scripts.benchmark_candidate_engines as benchmark

    evidence_path = tmp_path / "provider_evidence.jsonl"
    report_path = tmp_path / "candidate_engine_benchmark.md"
    now = datetime(2026, 7, 4, tzinfo=timezone.utc)
    append_evidence(
        ProviderEvidence(
            evidence_id="ev-1",
            run_id="run-qlib",
            market="CN",
            ticker="600519.SH",
            data_domain="daily_bar",
            provider="akshare+tushare",
            provider_ticker="akshare:600519;tushare:600519.SH",
            source_updated_at=now,
            observed_at=now,
            normalized_payload={"compared_fields": ["open", "high", "low", "close", "volume"]},
            raw_field_mapping={},
            quality_flags=[],
            cross_source_status="matched",
            gate_status="warn",
            allowed_downstream=["vectorbt"],
            notes="summary only",
        ),
        evidence_path,
    )

    result = benchmark.benchmark_candidate_engines(evidence_path=evidence_path, report_path=report_path)
    qlib_row = next(row for row in result["rows"] if row["engine"] == "qlib")

    assert qlib_row["status"] == "blocked_by_panel_data"
    assert "panel" in qlib_row["current_blocker"]
