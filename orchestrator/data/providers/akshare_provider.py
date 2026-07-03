"""AkShare provider adapter for minimal data coverage probes."""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any, Callable, Iterator

from orchestrator.data.contracts import DailyBar, Market, QualityFlag, ValuationSnapshot


class AkShareProviderError(Exception):
    """Raised when AkShare is unavailable or a provider call fails."""


CN_TICKER_RE = re.compile(r"^(?P<code>\d{6})\.(?P<exchange>SH|SZ)$")
HK_TICKER_RE = re.compile(r"^(?P<code>\d{1,5})\.HK$")
EASTMONEY_NO_PROXY_HOSTS = (
    "eastmoney.com",
    ".eastmoney.com",
    "push2his.eastmoney.com",
    "33.push2his.eastmoney.com",
)
PROXY_ENV_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy")
SAMPLE_LOOKBACK_DAYS = 180


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


def get_akshare_import_status() -> dict[str, str | bool | None]:
    try:
        ak = _load_akshare()
    except AkShareProviderError as exc:
        return {"installed": False, "version": None, "error": str(exc)}
    return {"installed": True, "version": getattr(ak, "__version__", "unknown"), "error": None}


def ensure_eastmoney_no_proxy() -> str:
    hosts = list(EASTMONEY_NO_PROXY_HOSTS)
    merged: list[str] = []
    for key in ("NO_PROXY", "no_proxy"):
        for value in os.environ.get(key, "").split(","):
            value = value.strip()
            if value and value not in merged:
                merged.append(value)
    for host in hosts:
        if host not in merged:
            merged.append(host)
    value = ",".join(merged)
    os.environ["NO_PROXY"] = value
    os.environ["no_proxy"] = value
    return value


def get_eastmoney_proxy_bypass_status() -> dict[str, str | bool]:
    proxy_env_vars = [key for key in PROXY_ENV_KEYS if os.environ.get(key)]
    return {
        "enabled": True,
        "mode": "direct_no_proxy",
        "no_proxy": ensure_eastmoney_no_proxy(),
        "proxy_env_vars_present": ", ".join(proxy_env_vars) if proxy_env_vars else "-",
    }


@contextmanager
def _eastmoney_direct_connection_env() -> Iterator[None]:
    ensure_eastmoney_no_proxy()
    saved = {key: os.environ.get(key) for key in PROXY_ENV_KEYS}
    for key in PROXY_ENV_KEYS:
        os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _call_eastmoney_provider(call: Callable[[], Any], context: str) -> Any:
    with _eastmoney_direct_connection_env():
        return _call_provider(call, context)


def _sample_date_window() -> tuple[str, str]:
    end = datetime.now(UTC).date()
    start = end - timedelta(days=SAMPLE_LOOKBACK_DAYS)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


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
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    text = str(value).strip()
    if text.lower() in {"", "--", "none", "nan", "null"}:
        return None
    text = text.replace(",", "")
    if text.endswith("%"):
        text = text[:-1].strip()
    try:
        return float(text)
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


def _parse_float_field(
    row: dict[str, Any],
    mapping: dict[str, list[str]],
    contract_field: str,
    flags: list[str],
) -> float | None:
    raw = _first_present(row, mapping[contract_field])
    parsed = _to_float(raw)
    if parsed is None and raw not in (None, "", "--", "None", "nan"):
        flags.append(f"{QualityFlag.PARSE_ERROR.value}:{contract_field}")
    return parsed


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
    "date": ["date", "trade_date", "日期"],
    "market_cap": ["market_cap", "total_mv", "总市值"],
    "pe": ["pe", "pe_ttm", "市盈率(TTM)", "市盈率"],
    "pb": ["pb", "市净率"],
    "ps": ["ps", "ps_ttm", "市销率"],
    "dividend_yield": ["dividend_yield", "dv_ttm", "dv_ratio", "股息率"],
}


def _fetch_cn_daily_bar_raw(ticker: str, adjust: str = "qfq") -> list[dict[str, Any]]:
    if adjust not in {"qfq", "hfq", "none"}:
        raise AkShareProviderError("adjust must be one of: qfq, hfq, none")
    ensure_eastmoney_no_proxy()
    ak = _load_akshare()
    symbol = normalize_cn_ticker_for_akshare(ticker)
    provider_adjust = "" if adjust == "none" else adjust
    start_date, end_date = _sample_date_window()
    frame = _call_eastmoney_provider(
        lambda: ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=provider_adjust,
            timeout=15,
        ),
        f"CN daily_bar {ticker}",
    )
    return _tail_records(frame)


def _fetch_hk_daily_bar_raw(ticker: str) -> list[dict[str, Any]]:
    ensure_eastmoney_no_proxy()
    ak = _load_akshare()
    symbol = normalize_hk_ticker_for_akshare(ticker)
    start_date, end_date = _sample_date_window()

    def call() -> Any:
        try:
            return ak.stock_hk_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="",
            )
        except TypeError:
            return ak.stock_hk_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date)

    frame = _call_eastmoney_provider(call, f"HK daily_bar {ticker}")
    return _tail_records(frame)


def _fetch_cn_valuation_raw(ticker: str) -> list[dict[str, Any]]:
    ak = _load_akshare()
    symbol = normalize_cn_ticker_for_akshare(ticker)
    indicator_map = {
        "market_cap": "总市值",
        "pe": "市盈率(TTM)",
        "pb": "市净率",
    }
    by_date: dict[Any, dict[str, Any]] = {}
    for contract_field, indicator in indicator_map.items():
        frame = _call_provider(
            lambda indicator=indicator: ak.stock_zh_valuation_baidu(
                symbol=symbol, indicator=indicator, period="近一年"
            ),
            f"CN valuation {ticker} {indicator}",
        )
        for row in _tail_records(frame):
            row_date = row.get("date")
            if row_date not in by_date:
                by_date[row_date] = {"date": row_date}
            by_date[row_date][contract_field] = row.get("value")
            by_date[row_date][f"akshare_{contract_field}_indicator"] = indicator
    rows = list(by_date.values())
    return rows[-5:]


def fetch_raw_sample_keys(ticker: str, market: Market, capability: str) -> list[str]:
    if market == Market.CN and capability == "daily_bar":
        rows = _fetch_cn_daily_bar_raw(ticker)
    elif market == Market.CN and capability == "valuation_snapshot":
        rows = _fetch_cn_valuation_raw(ticker)
    elif market == Market.HK and capability == "daily_bar":
        rows = _fetch_hk_daily_bar_raw(ticker)
    else:
        raise AkShareProviderError(f"Unsupported AkShare raw sample: {market.value} {capability}")
    return list(rows[0].keys()) if rows else []


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

    close = _parse_float_field(row, DAILY_BAR_FIELD_MAP, "close", flags)
    adj_close = close if adjustment in {"qfq", "hfq"} else None
    if adj_close is None and adjustment in {"qfq", "hfq"}:
        flags.append(f"{QualityFlag.MISSING_FIELD.value}:adj_close")
    flags.append(f"{QualityFlag.UNIT_UNVERIFIED.value}:volume")
    flags.append(f"{QualityFlag.UNIT_UNVERIFIED.value}:amount")
    flags.append(f"{QualityFlag.UNIT_UNVERIFIED.value}:turnover")
    flags.append(f"{QualityFlag.ADJUSTMENT_UNVERIFIED.value}:{adjustment}")

    return DailyBar(
        market=market,
        ticker=ticker,
        date=bar_date,
        open=_parse_float_field(row, DAILY_BAR_FIELD_MAP, "open", flags),
        high=_parse_float_field(row, DAILY_BAR_FIELD_MAP, "high", flags),
        low=_parse_float_field(row, DAILY_BAR_FIELD_MAP, "low", flags),
        close=close,
        adj_close=adj_close,
        volume=_parse_float_field(row, DAILY_BAR_FIELD_MAP, "volume", flags),
        amount=_parse_float_field(row, DAILY_BAR_FIELD_MAP, "amount", flags),
        turnover=_parse_float_field(row, DAILY_BAR_FIELD_MAP, "turnover", flags),
        source="akshare",
        source_updated_at=source_updated_at,
        adjustment=adjustment,
        quality_flags=flags,
    )


def fetch_cn_daily_bar_sample(ticker: str, adjust: str = "qfq") -> list[DailyBar]:
    source_updated_at = datetime.now(UTC)
    return [
        _daily_bar_from_row(
            market=Market.CN,
            ticker=ticker,
            row=row,
            source_updated_at=source_updated_at,
            adjustment=adjust,
        )
        for row in _fetch_cn_daily_bar_raw(ticker, adjust=adjust)
    ]


def fetch_hk_daily_bar_sample(ticker: str) -> list[DailyBar]:
    source_updated_at = datetime.now(UTC)
    return [
        _daily_bar_from_row(
            market=Market.HK,
            ticker=ticker,
            row=row,
            source_updated_at=source_updated_at,
            adjustment="none",
        )
        for row in _fetch_hk_daily_bar_raw(ticker)
    ]


def _valuation_from_row(
    *, ticker: str, row: dict[str, Any], source_updated_at: datetime
) -> ValuationSnapshot:
    flags = _missing_flags(row, VALUATION_FIELD_MAP)
    for unavailable in ("ev_ebitda", "fcf_yield"):
        flags.append(f"{QualityFlag.MISSING_FIELD.value}:{unavailable}")
    flags.append(f"{QualityFlag.UNIT_UNVERIFIED.value}:market_cap")
    flags.append(f"{QualityFlag.UNIT_UNVERIFIED.value}:dividend_yield")

    snapshot_date = _to_date(_first_present(row, VALUATION_FIELD_MAP["date"]))
    if snapshot_date is None:
        flags.append(f"{QualityFlag.MISSING_FIELD.value}:date_parse")
        snapshot_date = source_updated_at.date()

    return ValuationSnapshot(
        market=Market.CN,
        ticker=ticker,
        date=snapshot_date,
        market_cap=_parse_float_field(row, VALUATION_FIELD_MAP, "market_cap", flags),
        pe=_parse_float_field(row, VALUATION_FIELD_MAP, "pe", flags),
        pb=_parse_float_field(row, VALUATION_FIELD_MAP, "pb", flags),
        ps=_parse_float_field(row, VALUATION_FIELD_MAP, "ps", flags),
        ev_ebitda=None,
        dividend_yield=_parse_float_field(row, VALUATION_FIELD_MAP, "dividend_yield", flags),
        fcf_yield=None,
        source="akshare",
        source_updated_at=source_updated_at,
        quality_flags=flags,
    )


def fetch_cn_valuation_sample(ticker: str) -> list[ValuationSnapshot]:
    source_updated_at = datetime.now(UTC)
    return [
        _valuation_from_row(ticker=ticker, row=row, source_updated_at=source_updated_at)
        for row in _fetch_cn_valuation_raw(ticker)
    ]
