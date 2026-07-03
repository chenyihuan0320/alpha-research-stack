import os
from types import SimpleNamespace
from datetime import UTC, datetime

import pytest

import orchestrator.data.providers.akshare_provider as ak_provider
from orchestrator.data.providers.akshare_provider import (
    AkShareProviderError,
    _fetch_cn_daily_bar_raw_via_curl,
    _call_eastmoney_provider,
    _eastmoney_direct_connection_env,
    _merge_valuation_indicator_rows,
    _to_float,
    _valuation_from_row,
    ensure_eastmoney_no_proxy,
    fetch_cn_daily_bar_sample,
    get_configured_akshare_daily_source_mode,
    get_configured_eastmoney_proxy_mode,
    get_eastmoney_call_history,
    get_eastmoney_proxy_bypass_status,
    normalize_cn_ticker_for_akshare,
    normalize_cn_ticker_for_sina,
    normalize_hk_ticker_for_akshare,
    reset_eastmoney_call_history,
)


def test_normalize_cn_ticker_for_akshare() -> None:
    assert normalize_cn_ticker_for_akshare("600519.SH") == "600519"
    assert normalize_cn_ticker_for_akshare("000001.SZ") == "000001"


def test_normalize_cn_ticker_for_sina() -> None:
    assert normalize_cn_ticker_for_sina("600519.SH") == "sh600519"
    assert normalize_cn_ticker_for_sina("000001.SZ") == "sz000001"


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


def test_akshare_daily_source_mode_default_and_config(monkeypatch) -> None:
    monkeypatch.delenv("ARS_AKSHARE_DAILY_SOURCE_MODE", raising=False)
    assert get_configured_akshare_daily_source_mode() == "sina_first"

    monkeypatch.setenv("ARS_AKSHARE_DAILY_SOURCE_MODE", "eastmoney_first")
    assert get_configured_akshare_daily_source_mode() == "eastmoney_first"

    monkeypatch.setenv("ARS_AKSHARE_DAILY_SOURCE_MODE", "bad-mode")
    with pytest.raises(AkShareProviderError, match="Invalid ARS_AKSHARE_DAILY_SOURCE_MODE"):
        get_configured_akshare_daily_source_mode()


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


def test_cn_daily_bar_default_uses_sina_first(monkeypatch) -> None:
    reset_eastmoney_call_history()
    monkeypatch.delenv("ARS_AKSHARE_DAILY_SOURCE_MODE", raising=False)

    class FakeFrame:
        def tail(self, _limit):
            return self

        def to_dict(self, _orient):
            return [
                {
                    "date": "2026-07-02",
                    "open": "11",
                    "high": "13",
                    "low": "10",
                    "close": "12",
                    "volume": "1100",
                    "amount": "2100",
                    "turnover": "0.6",
                }
            ]

    class FakeAkShare:
        @staticmethod
        def stock_zh_a_daily(**kwargs):
            assert kwargs["symbol"] == "sh600519"
            return FakeFrame()

        @staticmethod
        def stock_zh_a_hist(**_kwargs):
            raise AssertionError("Eastmoney should not be called in default sina_first mode")

    monkeypatch.setattr(ak_provider, "_load_akshare", lambda: FakeAkShare())

    data = fetch_cn_daily_bar_sample("600519.SH")[0].to_dict()

    assert data["close"] == 12.0
    assert data["volume"] == 1100.0
    assert get_eastmoney_call_history() == []


def test_cn_daily_bar_falls_back_to_curl_cli_after_akshare_failure(monkeypatch) -> None:
    reset_eastmoney_call_history()
    monkeypatch.setenv("ARS_AKSHARE_DAILY_SOURCE_MODE", "eastmoney_only")
    monkeypatch.setenv("ARS_AKSHARE_EASTMONEY_PROXY_MODE", "respect_env_proxy")

    class FakeAkShare:
        @staticmethod
        def stock_zh_a_hist(**_kwargs):
            raise RuntimeError("requests path failed")

    def fake_run(command, **_kwargs):
        assert "--noproxy" not in command
        return SimpleNamespace(
            returncode=0,
            stdout=(
                '{"data":{"klines":['
                '"2026-07-01,10,11,12,9,1000,2000,1.0,2.0,0.2,0.5",'
                '"2026-07-02,11,12,13,10,1100,2100,1.1,2.1,0.3,0.6"'
                ']}}'
            ),
            stderr="",
        )

    monkeypatch.setattr(ak_provider, "_load_akshare", lambda: FakeAkShare())
    monkeypatch.setattr(ak_provider.subprocess, "run", fake_run)

    rows = fetch_cn_daily_bar_sample("600519.SH")
    data = [row.to_dict() for row in rows]
    history = get_eastmoney_call_history()

    assert len(data) == 2
    assert data[-1]["date"] == "2026-07-02"
    assert data[-1]["close"] == 12.0
    assert data[-1]["volume"] == 1100.0
    assert [item["transport"] for item in history] == ["akshare_requests", "curl_cli"]
    assert [item["status"] for item in history] == ["failed", "success"]


def test_curl_cli_auto_retries_direct_no_proxy_after_env_proxy_failure(monkeypatch) -> None:
    reset_eastmoney_call_history()
    monkeypatch.setenv("ARS_AKSHARE_EASTMONEY_PROXY_MODE", "auto")
    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(list(command))
        if len(commands) == 1:
            return SimpleNamespace(returncode=52, stdout="", stderr="Empty reply from server")
        return SimpleNamespace(
            returncode=0,
            stdout='{"data":{"klines":["2026-07-02,11,12,13,10,1100,2100,1.1,2.1,0.3,0.6"]}}',
            stderr="",
        )

    monkeypatch.setattr(ak_provider.subprocess, "run", fake_run)

    rows = _fetch_cn_daily_bar_raw_via_curl(
        ticker="600519.SH",
        symbol="600519",
        start_date="20260701",
        end_date="20260703",
        adjust="qfq",
    )
    history = get_eastmoney_call_history()

    assert rows[-1]["收盘"] == "12"
    assert "--noproxy" not in commands[0]
    assert "--noproxy" in commands[1]
    assert [item["attempted_mode"] for item in history] == ["respect_env_proxy", "direct_no_proxy"]
    assert [item["transport"] for item in history] == ["curl_cli", "curl_cli"]
    assert [item["status"] for item in history] == ["failed", "success"]


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
