import pytest

from orchestrator.data.providers.akshare_provider import (
    AkShareProviderError,
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
