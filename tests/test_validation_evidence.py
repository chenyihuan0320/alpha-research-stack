from __future__ import annotations


def test_validation_evidence_round_trip() -> None:
    from orchestrator.validation.models import ValidationEvidence

    evidence = ValidationEvidence(
        validation_id="val-1",
        run_id="run-validation",
        market="CN",
        ticker="600519.SH",
        event_date="2026-07-02",
        validation_source="fallback_event_baseline",
        holding_period=1,
        forward_return=0.02,
        max_favorable_excursion=0.03,
        max_adverse_excursion=-0.01,
        hit_take_profit=None,
        hit_stop_loss=None,
        provider_evidence_ids=["ev-1"],
        panel_rows_used=2,
        quality_flags=["cross_source_panel_unavailable"],
        raw_payload={"close_start": 100.0, "close_end": 102.0},
        gate_status="warn",
        allowed_next_steps=["research"],
        notes="ValidationEvidence only; not signal.",
    )

    restored = ValidationEvidence.from_dict(evidence.to_dict())

    assert restored == evidence
    assert "confidence" not in restored.to_dict()


def test_validation_ledger_append_load_summarize(tmp_path) -> None:
    from orchestrator.validation.ledger import append_validation, load_validations, summarize_validations
    from orchestrator.validation.models import ValidationEvidence

    path = tmp_path / "validation_evidence.jsonl"
    append_validation(
        ValidationEvidence(
            validation_id="val-1",
            run_id="run-validation",
            market="CN",
            ticker="600519.SH",
            event_date="2026-07-02",
            validation_source="fallback_event_baseline",
            holding_period=1,
            forward_return=0.02,
            max_favorable_excursion=0.03,
            max_adverse_excursion=-0.01,
            hit_take_profit=None,
            hit_stop_loss=None,
            provider_evidence_ids=["ev-1"],
            panel_rows_used=2,
            quality_flags=[],
            raw_payload={},
            gate_status="warn",
            allowed_next_steps=["research"],
            notes=None,
        ),
        path,
    )

    rows = load_validations(path)
    summary = summarize_validations(path)

    assert len(rows) == 1
    assert summary["total"] == 1
    assert summary["by_source"] == {"fallback_event_baseline": 1}
    assert summary["by_gate_status"] == {"warn": 1}
