from orchestrator.data.quality_gate import (
    evaluate_cross_source_comparison,
    evaluate_daily_bar_quality,
    evaluate_valuation_quality,
)


def test_provider_error_blocks() -> None:
    decision = evaluate_daily_bar_quality(["provider_error"])

    assert decision.status == "block"
    assert "provider" in decision.blocked_fields


def test_asof_mismatch_warns() -> None:
    decision = evaluate_valuation_quality(["asof_mismatch:market_cap=2026-07-01,pe=2026-07-02"])

    assert decision.status == "warn"
    assert any("as-of mismatch" in reason or "asof_mismatch" in reason for reason in decision.reasons)


def test_missing_close_or_date_blocks() -> None:
    assert evaluate_daily_bar_quality(["missing_field:close"]).status == "block"
    assert evaluate_daily_bar_quality(["missing_field:date"]).status == "block"


def test_estimated_dividend_yield_warns() -> None:
    decision = evaluate_valuation_quality(["estimated_value:dividend_yield"])

    assert decision.status == "warn"
    assert "dividend_yield" in decision.warning_fields


def test_missing_fcf_yield_warns_without_blocking() -> None:
    decision = evaluate_valuation_quality(["missing_field:fcf_yield"])

    assert decision.status == "warn"
    assert decision.blocked_fields == []
    assert "fcf_yield" in decision.warning_fields


def test_pending_credentials_is_not_code_failure() -> None:
    decision = evaluate_cross_source_comparison({"status": "pending_credentials"})

    assert decision.status == "pending_credentials"
    assert decision.blocked_fields == []


def test_cross_source_price_difference_blocks() -> None:
    decision = evaluate_cross_source_comparison(
        {
            "price_diff_pct": {"close": 2.5},
            "price_diff_threshold_pct": 1.0,
        }
    )

    assert decision.status == "block"
    assert "price" in decision.blocked_fields
