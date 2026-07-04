from orchestrator.evidence.domain_gate import (
    allowed_downstream_for_evidence,
    evaluate_evidence_domain,
)


def test_daily_bar_matched_cross_source_allows_vectorbt() -> None:
    decision = evaluate_evidence_domain(
        {
            "data_domain": "daily_bar",
            "cross_source_status": "matched",
            "normalized_payload": {
                "price_diff_pct": {"open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0}
            },
            "quality_flags": ["unit_unverified:amount"],
        }
    )

    assert decision.status == "warn"
    assert "vectorbt" in decision.allowed_downstream
    assert "alphasift_exploratory" in decision.allowed_downstream


def test_daily_bar_price_mismatch_blocks() -> None:
    decision = evaluate_evidence_domain(
        {
            "data_domain": "daily_bar",
            "cross_source_status": "mismatch",
            "normalized_payload": {"price_diff_pct": {"close": 1.2}},
            "quality_flags": [],
        }
    )

    assert decision.status == "block"
    assert "price" in decision.blocked_fields


def test_valuation_provider_error_blocks() -> None:
    decision = evaluate_evidence_domain(
        {
            "data_domain": "valuation",
            "cross_source_status": "unavailable",
            "quality_flags": ["provider_error:valuation_snapshot"],
        }
    )

    assert decision.status == "block"
    assert decision.allowed_downstream == []


def test_valuation_missing_fcf_warns_for_research_only() -> None:
    decision = evaluate_evidence_domain(
        {
            "data_domain": "valuation",
            "cross_source_status": "unchecked",
            "quality_flags": ["missing_field:fcf_yield"],
        }
    )

    assert decision.status == "warn"
    assert decision.allowed_downstream == ["research_evidence"]


def test_fundamentals_permission_error_blocks_without_affecting_daily_bar() -> None:
    decision = evaluate_evidence_domain(
        {
            "data_domain": "fundamentals",
            "cross_source_status": "unavailable",
            "quality_flags": ["permission_error:income"],
        }
    )

    assert decision.status == "block"
    assert decision.blocked_fields == ["provider"]


def test_allowed_downstream_prefers_existing_evidence_field() -> None:
    assert allowed_downstream_for_evidence({"allowed_downstream": ["vectorbt"]}) == ["vectorbt"]
