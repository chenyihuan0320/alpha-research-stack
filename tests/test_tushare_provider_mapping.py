import pytest

from orchestrator.data.providers.tushare_provider import (
    TushareProviderError,
    _get_pro_client,
    get_tushare_token,
    normalize_cn_ticker_for_tushare,
)


def test_normalize_cn_ticker_for_tushare() -> None:
    assert normalize_cn_ticker_for_tushare("600519.SH") == "600519.SH"
    assert normalize_cn_ticker_for_tushare("000001.SZ") == "000001.SZ"
    assert normalize_cn_ticker_for_tushare("300750.SZ") == "300750.SZ"


def test_tushare_rejects_non_cn_tickers() -> None:
    with pytest.raises(TushareProviderError):
        normalize_cn_ticker_for_tushare("0700.HK")
    with pytest.raises(TushareProviderError):
        normalize_cn_ticker_for_tushare("AAPL")


def test_get_tushare_token_reads_environment_only(monkeypatch) -> None:
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    assert get_tushare_token() is None

    monkeypatch.setenv("TUSHARE_TOKEN", " test-token ")
    assert get_tushare_token() == "test-token"


def test_get_pro_client_does_not_call_set_token(monkeypatch) -> None:
    monkeypatch.setenv("TUSHARE_TOKEN", "test-token")

    class FakeTushare:
        @staticmethod
        def set_token(_token: str) -> None:
            raise AssertionError("set_token writes token files and should not be called")

        @staticmethod
        def pro_api(token: str) -> str:
            assert token == "test-token"
            return "client"

    monkeypatch.setattr("orchestrator.data.providers.tushare_provider._load_tushare", lambda: FakeTushare())

    assert _get_pro_client() == "client"
