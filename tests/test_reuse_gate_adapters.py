import pytest

from orchestrator.adapters.alphasift_adapter import (
    build_alphasift_input,
    can_send_to_alphasift,
    parse_alphasift_output,
)
from orchestrator.adapters.vectorbt_adapter import (
    build_vectorbt_input,
    can_send_to_vectorbt,
    parse_vectorbt_result,
)


def test_can_send_to_alphasift_blocks_bad_gate_statuses() -> None:
    assert can_send_to_alphasift({"quality_gate_status": "block", "allowed_downstream": []}) is False
    assert can_send_to_alphasift({"quality_gate_status": "pending_credentials", "allowed_downstream": []}) is False


def test_can_send_to_alphasift_allows_warn_and_pass() -> None:
    assert can_send_to_alphasift({"quality_gate_status": "warn", "allowed_downstream": ["alphasift_exploratory"]}) is True
    assert can_send_to_alphasift({"quality_gate_status": "pass", "allowed_downstream": ["alphasift"]}) is True


def test_build_alphasift_input_rejects_blocked_evidence() -> None:
    with pytest.raises(ValueError):
        build_alphasift_input(
            {
                "run_id": "run-1",
                "market": "CN",
                "ticker": "600519.SH",
                "candidate_date": "2026-07-04",
                "provider_evidence": {},
                "quality_gate_status": "block",
            }
        )


def test_parse_alphasift_output_minimal_payload() -> None:
    output = parse_alphasift_output(
        {
            "run_id": "run-1",
            "market": "CN",
            "ticker": "600519.SH",
            "candidate_date": "2026-07-04",
            "candidate_score": 0.0,
            "reasons": ["adapter contract test"],
            "quality_flags": ["test_flag"],
        }
    )

    assert output.run_id == "run-1"
    assert output.ticker == "600519.SH"
    assert output.candidate_score == 0.0
    assert output.reasons == ["adapter contract test"]
    assert output.quality_flags == ["test_flag"]


def test_can_send_to_vectorbt_blocks_bad_gate_statuses() -> None:
    assert can_send_to_vectorbt({"quality_gate_status": "block", "allowed_downstream": []}) is False
    assert can_send_to_vectorbt({"quality_gate_status": "pending_credentials", "allowed_downstream": []}) is False


def test_can_send_to_vectorbt_allows_warn_and_pass() -> None:
    assert can_send_to_vectorbt({"quality_gate_status": "warn", "allowed_downstream": ["vectorbt"]}) is True
    assert can_send_to_vectorbt({"quality_gate_status": "pass", "allowed_downstream": ["vectorbt"]}) is True


def test_build_vectorbt_input_rejects_blocked_daily_bars() -> None:
    with pytest.raises(ValueError):
        build_vectorbt_input(
            ticker="600519.SH",
            market="CN",
            daily_bars=[],
            event_dates=[],
            holding_period=5,
            quality_gate_status="pending_credentials",
        )


def test_parse_vectorbt_result_minimal_payload() -> None:
    result = parse_vectorbt_result(
        {
            "ticker": "600519.SH",
            "market": "CN",
            "status": "planned",
            "metrics": {"sample_count": 0},
            "warnings": ["adapter skeleton only"],
        }
    )

    assert result.ticker == "600519.SH"
    assert result.status == "planned"
    assert result.metrics == {"sample_count": 0}
    assert result.warnings == ["adapter skeleton only"]
