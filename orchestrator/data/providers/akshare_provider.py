"""AkShare provider adapter for minimal data coverage probes."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any, Callable

from orchestrator.data.contracts import DailyBar, Market, QualityFlag, ValuationSnapshot


class AkShareProviderError(Exception):
    """Raised when AkShare is unavailable or a provider call fails."""


CN_TICKER_RE = re.compile(r"^(?P<code>\d{6})\.(?P<exchange>SH|SZ)$")
HK_TICKER_RE = re.compile(r"^(?P<code>\d{1,5})\.HK$")


def normalize_cn_ticker_for_akshare(ticker: str) -> str:
    match = CN_TICKER_RE.fullmatch(ticker.upper())
    if not match:
        raise AkShareProviderError(
            f"Invalid CN ticker '{ticker}'. Expected project format like 600519.SH or 000001.SZ."
        )
    return match.group("code")


def normalize_hk_ticker_for_akshare(ticker: str) -> str:
    match = HK_TICKER_RE.fullmatch(ticker.upper())
    if not match:
        raise AkShareProviderError(
            f"Invalid HK ticker '{ticker}'. Expected project format like 0700.HK or 9988.HK."
        )
    return match.group("code").zfill(5)


def _load_akshare() -> Any:
    try:
        import akshare as ak  # type: ignore[import-not-found]
    except ImportError as exc:
        raise AkShareProviderError(
            "AkShare is not installed. Install it only when running provider probes, for example: "
            "python -m pip install akshare"
        ) from exc
    return ak


def _tail_records(frame: Any, limit: int = 5) -> list[dict[str, Any]]:
    try:
        records = frame.tail(limit).to_dict("records")
    except Exception as exc:  # pragma: no cover - provider object dependent
        raise AkShareProviderError(f"AkShare returned an unsupported table object: {exc}") from exc
    if not isinstance(records, list):
        raise AkShareProviderError("AkShare returned an unsupported table format.")
    return records


def _first_present(row: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def _missing_flags(row: dict[str, Any], mapping: dict[str, list[str]]) -> list[str]:
    flags: list[str] = []
    for contract_field, provider_fields in mapping.items():
        if not any(field in row and row[field] not in (None, "") for field in provider_fields):
            flags.append(f"{QualityFlag.MISSING_FIELD.value}:{contract_field}")
    return flags


def _call_provider(call: Callable[[], Any], context: str) -> Any:
    try:
        return call()
    except AkShareProviderError:
        raise
    except Exception as exc:  # pragma: no cover - provider/network dependent
        raise AkShareProviderError(f"AkShare provider call failed for {context}: {exc}") from exc


DAILY_BAR_FIELD_MAP = {
    "date": ["日期", "date", "trade_date"],
    "open": ["开盘", "open"],
    "high": ["最高", "high"],
    "low": ["最低", "low"],
    "close": ["收盘", "close"],
    "volume": ["成交量", "volume"],
    "amount": ["成交额", "amount"],
    "turnover": ["换手率", "turnover"],
}

VALUATION_FIELD_MAP = {
    "date": ["trade_date", "日期", "date"],
    "market_cap": ["total_mv", "总市值", "market_cap"],
    "pe": ["pe_ttm", "pe", "市盈率"],
    "pb": ["pb", "市净率"],
    "ps": ["ps_ttm", "ps", "市销率"],
    "dividend_yield": ["dv_ttm", "dv_ratio", "股息率"],
}


def _daily_bar_from_row(
    *,
    market: Market,
    ticker: str,
    row: dict[str, Any],
    source_updated_at: datetime,
    adjustment: str,
) -> DailyBar:
    flags = _missing_flags(row, DAILY_BAR_FIELD_MAP)
    bar_date = _to_date(_first_present(row, DAILY_BAR_FIELD_MAP["date"]))
    if bar_date is None:
        flags.append(f"{QualityFlag.MISSING_FIELD.value}:date_parse")
        bar_date = source_updated_at.date()

    close = _to_float(_first_present(row, DAILY_BAR_FIELD_MAP["close"]))
    adj_close = close if adjustment in {"qfq", "hfq"} else None
    if adj_close is None and adjustment in {"qfq", "hfq"}:
        flags.append(f"{QualityFlag.MISSING_FIELD.value}:adj_close")

    return DailyBar(
        market=market,
        ticker=ticker,
        date=bar_date,
        open=_to_float(_first_present(row, DAILY_BAR_FIELD_MAP["open"])),
        high=_to_float(_first_present(row, DAILY_BAR_FIELD_MAP["high"])),
        low=_to_float(_first_present(row, DAILY_BAR_FIELD_MAP["low"])),
        close=close,
        adj_close=adj_close,
        volume=_to_float(_first_present(row, DAILY_BAR_FIELD_MAP["volume"])),
        amount=_to_float(_first_present(row, DAILY_BAR_FIELD_MAP["amount"])),
        turnover=_to_float(_first_present(row, DAILY_BAR_FIELD_MAP["turnover"])),
        source="akshare",
        source_updated_at=source_updated_at,
        adjustment=adjustment,
        quality_flags=flags,
    )


def fetch_cn_daily_bar_sample(ticker: str, adjust: str = "qfq") -> list[DailyBar]:
    if adjust not in {"qfq", "hfq", "none"}:
        raise AkShareProviderError("adjust must be one of: qfq, hfq, none")
    ak = _load_akshare()
    symbol = normalize_cn_ticker_for_akshare(ticker)
    provider_adjust = "" if adjust == "none" else adjust
    frame = _call_provider(
        lambda: ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust=provider_adjust),
        f"CN daily_bar {ticker}",
    )
    source_updated_at = datetime.now(UTC)
    return [
        _daily_bar_from_row(
            market=Market.CN,
            ticker=ticker,
            row=row,
            source_updated_at=source_updated_at,
            adjustment=adjust,
        )
        for row in _tail_records(frame)
    ]


def fetch_hk_daily_bar_sample(ticker: str) -> list[DailyBar]:
    ak = _load_akshare()
    symbol = normalize_hk_ticker_for_akshare(ticker)

    def call() -> Any:
        try:
            return ak.stock_hk_hist(symbol=symbol, period="daily", adjust="")
        except TypeError:
            return ak.stock_hk_hist(symbol=symbol, period="daily")

    frame = _call_provider(call, f"HK daily_bar {ticker}")
    source_updated_at = datetime.now(UTC)
    return [
        _daily_bar_from_row(
            market=Market.HK,
            ticker=ticker,
            row=row,
            source_updated_at=source_updated_at,
            adjustment="none",
        )
        for row in _tail_records(frame)
    ]


def _valuation_from_row(
    *, ticker: str, row: dict[str, Any], source_updated_at: datetime
) -> ValuationSnapshot:
    flags = _missing_flags(row, VALUATION_FIELD_MAP)
    for unavailable in ("ev_ebitda", "fcf_yield"):
        flags.append(f"{QualityFlag.MISSING_FIELD.value}:{unavailable}")

    snapshot_date = _to_date(_first_present(row, VALUATION_FIELD_MAP["date"]))
    if snapshot_date is None:
        flags.append(f"{QualityFlag.MISSING_FIELD.value}:date_parse")
        snapshot_date = source_updated_at.date()

    return ValuationSnapshot(
        market=Market.CN,
        ticker=ticker,
        date=snapshot_date,
        market_cap=_to_float(_first_present(row, VALUATION_FIELD_MAP["market_cap"])),
        pe=_to_float(_first_present(row, VALUATION_FIELD_MAP["pe"])),
        pb=_to_float(_first_present(row, VALUATION_FIELD_MAP["pb"])),
        ps=_to_float(_first_present(row, VALUATION_FIELD_MAP["ps"])),
        ev_ebitda=None,
        dividend_yield=_to_float(_first_present(row, VALUATION_FIELD_MAP["dividend_yield"])),
        fcf_yield=None,
        source="akshare",
        source_updated_at=source_updated_at,
        quality_flags=flags,
    )


def fetch_cn_valuation_sample(ticker: str) -> list[ValuationSnapshot]:
    ak = _load_akshare()
    symbol = normalize_cn_ticker_for_akshare(ticker)
    frame = _call_provider(lambda: ak.stock_a_indicator_lg(symbol=symbol), f"CN valuation {ticker}")
    source_updated_at = datetime.now(UTC)
    return [
        _valuation_from_row(ticker=ticker, row=row, source_updated_at=source_updated_at)
        for row in _tail_records(frame)
    ]
