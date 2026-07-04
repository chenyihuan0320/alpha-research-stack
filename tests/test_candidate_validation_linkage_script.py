from __future__ import annotations

from orchestrator.candidates.ledger import append_candidate
from orchestrator.candidates.models import CandidateEvidence
from orchestrator.validation.ledger import append_validation
from orchestrator.validation.models import ValidationEvidence


def _candidate(candidate_id: str = "cand-1", ticker: str = "600519.SH") -> CandidateEvidence:
    return CandidateEvidence(
        candidate_id=candidate_id,
        run_id="run-candidate-linkage",
        market="CN",
        ticker=ticker,
        candidate_date="2026-07-02",
        candidate_source="alphasift",
        candidate_direction="unknown",
        candidate_score=None,
        reasons=["fixture"],
        provider_evidence_ids=["ev-1"],
        provider_evidence_domains=["daily_bar"],
        quality_flags=[],
        raw_payload={},
        gate_status="warn",
        allowed_next_steps=["vectorbt_validation"],
        notes="CandidateEvidence fixture only.",
    )


def _validation(validation_id: str = "val-1", ticker: str = "600519.SH") -> ValidationEvidence:
    return ValidationEvidence(
        validation_id=validation_id,
        run_id="run-validation-linkage",
        market="CN",
        ticker=ticker,
        event_date="2026-07-02",
        validation_source="fallback_event_baseline",
        holding_period=1,
        forward_return=0.01,
        max_favorable_excursion=0.02,
        max_adverse_excursion=-0.01,
        hit_take_profit=None,
        hit_stop_loss=None,
        provider_evidence_ids=["ev-1"],
        panel_rows_used=2,
        quality_flags=["cross_source_panel_unavailable"],
        raw_payload={},
        gate_status="warn",
        allowed_next_steps=["research"],
        notes="ValidationEvidence fixture only.",
    )


def test_build_candidate_validation_links_links_same_ticker_and_date(tmp_path) -> None:
    import scripts.build_candidate_validation_links as script

    candidate_path = tmp_path / "candidate_evidence.jsonl"
    validation_path = tmp_path / "validation_evidence.jsonl"
    link_path = tmp_path / "candidate_validation_links.jsonl"
    report_path = tmp_path / "candidate_validation_linkage.md"
    append_candidate(_candidate(), candidate_path)
    append_validation(_validation(), validation_path)

    result = script.build_candidate_validation_links(
        candidate_path=candidate_path,
        validation_path=validation_path,
        link_path=link_path,
        report_path=report_path,
    )
    report = report_path.read_text(encoding="utf-8").lower()

    assert result["links_created"] == 1
    assert result["linked_count"] == 1
    assert '"linkage_status": "linked"' in link_path.read_text(encoding="utf-8")
    assert "recommendation" not in report
    assert "signal" not in report
    assert "confidence" not in report


def test_build_candidate_validation_links_records_orphan_validation_without_fake_candidate(
    tmp_path,
) -> None:
    import scripts.build_candidate_validation_links as script

    validation_path = tmp_path / "validation_evidence.jsonl"
    link_path = tmp_path / "candidate_validation_links.jsonl"
    report_path = tmp_path / "candidate_validation_linkage.md"
    append_validation(_validation(), validation_path)

    result = script.build_candidate_validation_links(
        candidate_path=tmp_path / "missing_candidates.jsonl",
        validation_path=validation_path,
        link_path=link_path,
        report_path=report_path,
    )
    payload = link_path.read_text(encoding="utf-8")
    report = report_path.read_text(encoding="utf-8")

    assert result["orphan_validations"] == 1
    assert result["linked_count"] == 0
    assert '"candidate_id": ""' in payload
    assert '"linkage_status": "missing_candidate"' in payload
    assert "validation_orphaned_no_candidate" in report
    assert "cand-" not in payload


def test_build_candidate_validation_links_records_pending_candidate(tmp_path) -> None:
    import scripts.build_candidate_validation_links as script

    candidate_path = tmp_path / "candidate_evidence.jsonl"
    link_path = tmp_path / "candidate_validation_links.jsonl"
    report_path = tmp_path / "candidate_validation_linkage.md"
    append_candidate(_candidate(), candidate_path)

    result = script.build_candidate_validation_links(
        candidate_path=candidate_path,
        validation_path=tmp_path / "missing_validations.jsonl",
        link_path=link_path,
        report_path=report_path,
    )
    payload = link_path.read_text(encoding="utf-8")

    assert result["pending_candidates"] == 1
    assert result["linked_count"] == 0
    assert '"linkage_status": "pending_validation"' in payload


def test_benchmark_reports_orphaned_validation_without_linkage(tmp_path) -> None:
    import scripts.benchmark_candidate_engines as benchmark

    validation_path = tmp_path / "validation_evidence.jsonl"
    report_path = tmp_path / "candidate_engine_benchmark.md"
    append_validation(_validation(), validation_path)

    result = benchmark.benchmark_candidate_engines(
        validation_ledger_path=validation_path,
        linkage_ledger_path=tmp_path / "missing_links.jsonl",
        report_path=report_path,
    )
    vectorbt_row = next(row for row in result["rows"] if row["engine"] == "vectorbt_event_baseline")

    assert vectorbt_row["status"] == "baseline_validated"
    assert "validation_orphaned_no_candidate" in vectorbt_row["current_blocker"]


def test_benchmark_reports_candidate_validation_linked(tmp_path) -> None:
    import scripts.benchmark_candidate_engines as benchmark
    from orchestrator.validation.linkage import CandidateValidationLink
    from orchestrator.validation.linkage_ledger import append_link

    validation_path = tmp_path / "validation_evidence.jsonl"
    link_path = tmp_path / "candidate_validation_links.jsonl"
    report_path = tmp_path / "candidate_engine_benchmark.md"
    append_validation(_validation(), validation_path)
    append_link(
        CandidateValidationLink(
            link_id="link-1",
            candidate_id="cand-1",
            validation_ids=["val-1"],
            ticker="600519.SH",
            market="CN",
            candidate_date="2026-07-02",
            validation_window="holding_period=1",
            linkage_status="linked",
            quality_flags=[],
            notes=None,
        ),
        link_path,
    )

    result = benchmark.benchmark_candidate_engines(
        validation_ledger_path=validation_path,
        linkage_ledger_path=link_path,
        report_path=report_path,
    )
    vectorbt_row = next(row for row in result["rows"] if row["engine"] == "vectorbt_event_baseline")

    assert vectorbt_row["status"] == "candidate_validation_linked"
