import os

import pytest

from orchestrator.data.providers.akshare_provider import (
    AkShareProviderError,
    _eastmoney_direct_connection_env,
    _to_float,
    ensure_eastmoney_no_proxy,
    fetch_cn_daily_bar_sample,
    normalize_cn_ticker_for_akshare,
    normalize_hk_ticker_for_akshare,
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


def test_eastmoney_direct_context_temporarily_removes_proxy_env(monkeypatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:4780")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:4780")

    with _eastmoney_direct_connection_env():
        assert "HTTP_PROXY" not in os.environ
        assert "HTTPS_PROXY" not in os.environ

    assert os.environ["HTTP_PROXY"] == "http://127.0.0.1:4780"
    assert os.environ["HTTPS_PROXY"] == "http://127.0.0.1:4780"
