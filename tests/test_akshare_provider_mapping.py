import os
from datetime import UTC, datetime

import pytest

from orchestrator.data.providers.akshare_provider import (
    AkShareProviderError,
    _call_eastmoney_provider,
    _eastmoney_direct_connection_env,
    _merge_valuation_indicator_rows,
    _to_float,
    _valuation_from_row,
    ensure_eastmoney_no_proxy,
    fetch_cn_daily_bar_sample,
    get_configured_eastmoney_proxy_mode,
    get_eastmoney_call_history,
    get_eastmoney_proxy_bypass_status,
    normalize_cn_ticker_for_akshare,
    normalize_hk_ticker_for_akshare,
    reset_eastmoney_call_history,
)


def test_normalize_cn_ticker_for_akshare() -> None:
    assert normalize_cn_ticker_for_akshare("600519.SH") == "600519"
    assert normalize_cn_ticker_for_akshare("000001.SZ") == "000001"


def test_normalize_hk_ticker_for_akshare() -> None:
    assert normalize_hk_ticker_for_akshare("0700.HK") == "00700"
    assert normalize_hk_ticker_for_akshare("9988.HK") == "09988"


def test_invalid_tickers_raise_clear_error() -> None:
    with pytest.raises(AkShareProviderError):
        normalize_cn_ticker_for_akshare("600519.SS")

    with pytest.raises(AkShareProviderError):
        normalize_hk_ticker_for_akshare("AAPL")


def test_to_float_handles_common_provider_strings() -> None:
    assert _to_float("1,234.56") == 1234.56
    assert _to_float("12.3%") == 12.3
    assert _to_float("--") is None
    assert _to_float("") is None
    assert _to_float("None") is None
    assert _to_float("nan") is None


def test_cn_daily_bar_adjustment_parameter_boundary() -> None:
    with pytest.raises(AkShareProviderError, match="adjust must be one of"):
        fetch_cn_daily_bar_sample("600519.SH", adjust="invalid")


def test_eastmoney_no_proxy_defaults_preserve_existing_env(monkeypatch) -> None:
    monkeypatch.setenv("NO_PROXY", "localhost,127.0.0.1")
    monkeypatch.delenv("no_proxy", raising=False)

    value = ensure_eastmoney_no_proxy()

    assert "localhost" in value
    assert "127.0.0.1" in value
    assert "push2his.eastmoney.com" in value
    assert "33.push2his.eastmoney.com" in value
    assert value == ensure_eastmoney_no_proxy()


def test_eastmoney_proxy_mode_config_parsing(monkeypatch) -> None:
    monkeypatch.delenv("ARS_AKSHARE_EASTMONEY_PROXY_MODE", raising=False)
    assert get_configured_eastmoney_proxy_mode() == "auto"

    monkeypatch.setenv("ARS_AKSHARE_EASTMONEY_PROXY_MODE", "respect_env_proxy")
    assert get_configured_eastmoney_proxy_mode() == "respect_env_proxy"

    monkeypatch.setenv("ARS_AKSHARE_EASTMONEY_PROXY_MODE", "bad-mode")
    with pytest.raises(AkShareProviderError, match="Invalid ARS_AKSHARE_EASTMONEY_PROXY_MODE"):
        get_configured_eastmoney_proxy_mode()


def test_eastmoney_default_mode_is_auto(monkeypatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:4780")
    monkeypatch.setenv("NO_PROXY", "<local>")
    monkeypatch.delenv("ARS_AKSHARE_EASTMONEY_PROXY_MODE", raising=False)

    status = get_eastmoney_proxy_bypass_status()

    assert status["enabled"] is False
    assert status["mode"] == "auto"
    assert status["configured_proxy_mode"] == "auto"
    assert status["no_proxy"] == "<local>"
    assert "HTTP_PROXY" in str(status["proxy_env_vars_present"])


def test_eastmoney_respect_env_proxy_does_not_remove_proxy_env(monkeypatch) -> None:
    reset_eastmoney_call_history()
    monkeypatch.setenv("ARS_AKSHARE_EASTMONEY_PROXY_MODE", "respect_env_proxy")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:4780")

    def call():
        assert os.environ["HTTP_PROXY"] == "http://127.0.0.1:4780"
        return "ok"

    assert _call_eastmoney_provider(call, "unit test") == "ok"
    assert get_eastmoney_call_history()[-1]["attempted_mode"] == "respect_env_proxy"


def test_eastmoney_auto_retries_direct_after_env_proxy_failure(monkeypatch) -> None:
    reset_eastmoney_call_history()
    monkeypatch.setenv("ARS_AKSHARE_EASTMONEY_PROXY_MODE", "auto")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:4780")
    calls = {"count": 0}

    def call():
        calls["count"] += 1
        if calls["count"] == 1:
            assert "HTTP_PROXY" in os.environ
            raise RuntimeError("proxy failed")
        assert "HTTP_PROXY" not in os.environ
        return "ok"

    assert _call_eastmoney_provider(call, "unit test") == "ok"
    history = get_eastmoney_call_history()
    assert [item["attempted_mode"] for item in history[-2:]] == [
        "respect_env_proxy",
        "direct_no_proxy",
    ]
    assert [item["status"] for item in history[-2:]] == ["failed", "success"]


def test_eastmoney_direct_context_temporarily_removes_proxy_env(monkeypatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:4780")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:4780")

    with _eastmoney_direct_connection_env():
        assert "HTTP_PROXY" not in os.environ
        assert "HTTPS_PROXY" not in os.environ

    assert os.environ["HTTP_PROXY"] == "http://127.0.0.1:4780"
    assert os.environ["HTTPS_PROXY"] == "http://127.0.0.1:4780"


def test_valuation_merge_marks_asof_mismatch_without_hiding_partial_coverage() -> None:
    row = _merge_valuation_indicator_rows(
        {
            "market_cap": [{"date": "2026-07-01", "value": "100", "_akshare_indicator": "总市值"}],
            "pe": [{"date": "2026-07-02", "value": "20", "_akshare_indicator": "市盈率(TTM)"}],
            "pb": [{"date": "2026-07-02", "value": "3", "_akshare_indicator": "市净率"}],
        }
    )
    snapshot = _valuation_from_row(
        ticker="600519.SH",
        row=row,
        source_updated_at=datetime(2026, 7, 3, tzinfo=UTC),
    )
    data = snapshot.to_dict()

    assert data["market_cap"] == 100.0
    assert data["pe"] == 20.0
    assert data["pb"] == 3.0
    assert any(flag.startswith("asof_mismatch:") for flag in data["quality_flags"])
    assert "partial_coverage:ps" in data["quality_flags"]
