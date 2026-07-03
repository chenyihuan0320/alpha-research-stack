"""Tushare provider adapter for A-share data validation probes."""

from __future__ import annotations

import os
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any, Callable

from orchestrator.data.contracts import (
    DailyBar,
    FundamentalsSnapshot,
    Market,
    QualityFlag,
    ValuationSnapshot,
)


class TushareProviderError(Exception):
    """Raised when Tushare is unavailable, uncredentialed, or a provider call fails."""


CN_TICKER_RE = re.compile(r"^(?P<code>\d{6})\.(?P<exchange>SH|SZ)$")
SAMPLE_LOOKBACK_DAYS = 180
_DAILY_BASIC_BY_DATE_CACHE: dict[str, list[dict[str, Any]]] = {}


def normalize_cn_ticker_for_tushare(ticker: str) -> str:
    normalized = ticker.upper()
    if not CN_TICKER_RE.fullmatch(normalized):
        raise TushareProviderError(
            f"Invalid CN ticker '{ticker}'. Expected project format like 600519.SH or 000001.SZ."
        )
    return normalized


def get_tushare_token() -> str | None:
    token = os.environ.get("TUSHARE_TOKEN")
    if token is None or not token.strip():
        return None
    return token.strip()


def _load_tushare() -> Any:
    try:
        import tushare as ts  # type: ignore[import-not-found]
    except ImportError as exc:
        raise TushareProviderError(
            "Tushare is not installed. Install it only when running provider probes, for example: "
            'python -m pip install -e ".[tushare]"'
        ) from exc
    return ts


def get_tushare_import_status() -> dict[str, str | bool | None]:
    try:
        ts = _load_tushare()
    except TushareProviderError as exc:
        return {"installed": False, "version": None, "error": str(exc)}
    return {"installed": True, "version": getattr(ts, "__version__", "unknown"), "error": None}


def _get_pro_client() -> Any:
    token = get_tushare_token()
    if token is None:
        raise TushareProviderError("needs_credentials: TUSHARE_TOKEN is not set.")
    ts = _load_tushare()
    try:
        # Avoid ts.set_token(token): it writes tk.csv under HOME in current Tushare,
        # which both violates the no-credential-file rule and can fail in read-only sandboxes.
        return ts.pro_api(token)
    except Exception as exc:  # pragma: no cover - provider dependent
        raise TushareProviderError(f"Tushare pro client initialization failed: {exc}") from exc


def _sample_date_window() -> tuple[str, str]:
    end = datetime.now(UTC).date()
    start = end - timedelta(days=SAMPLE_LOOKBACK_DAYS)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def _records(frame: Any, limit: int = 5) -> list[dict[str, Any]]:
    try:
        records = frame.to_dict("records")
    except Exception as exc:  # pragma: no cover - provider object dependent
        raise TushareProviderError(f"Tushare returned an unsupported table object: {exc}") from exc
    if not isinstance(records, list):
        raise TushareProviderError("Tushare returned an unsupported table format.")
    date_fields = ("trade_date", "end_date", "cal_date", "date")
    for field in date_fields:
        if any(isinstance(row, dict) and row.get(field) for row in records):
            records = sorted(records, key=lambda row, field=field: str(row.get(field) or ""))
            break
    return records[-limit:] if len(records) > limit else records


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
    if value != value:
        return None
    text = str(value).strip()
    if text.lower() in {"nat", "nan", "none", "null", "--"}:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text).date()
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
    except TushareProviderError:
        raise
    except Exception as exc:  # pragma: no cover - provider/network dependent
        raise TushareProviderError(f"Tushare provider call failed for {context}: {exc}") from exc


DAILY_BAR_FIELD_MAP = {
    "date": ["trade_date", "date"],
    "open": ["open"],
    "high": ["high"],
    "low": ["low"],
    "close": ["close"],
    "volume": ["vol", "volume"],
    "amount": ["amount"],
}

VALUATION_FIELD_MAP = {
    "date": ["trade_date", "date"],
    "market_cap": ["total_mv", "market_cap"],
    "pe": ["pe_ttm", "pe"],
    "pb": ["pb"],
    "ps": ["ps_ttm", "ps"],
    "dividend_yield": ["dv_ttm", "dv_ratio", "dividend_yield"],
    "ev_ebitda": ["ev_ebitda"],
    "fcf_yield": ["fcf_yield"],
}

FUNDAMENTALS_FIELD_MAP = {
    "period_end": ["end_date", "period_end"],
    "report_date": ["ann_date", "report_date"],
    "revenue": ["revenue", "total_revenue"],
    "gross_profit": [],
    "operating_income": ["operate_profit"],
    "net_income": ["n_income_attr_p", "n_income"],
    "operating_cash_flow": ["n_cashflow_act"],
    "free_cash_flow": [],
    "total_assets": ["total_assets"],
    "total_liabilities": ["total_liab"],
    "total_equity": ["total_hldr_eqy_exc_min_int", "total_hldr_eqy_inc_min_int"],
    "debt": [],
    "shares_outstanding": ["total_share"],
}


def _fetch_cn_daily_bar_raw(ticker: str) -> list[dict[str, Any]]:
    ts_code = normalize_cn_ticker_for_tushare(ticker)
    pro = _get_pro_client()
    start_date, end_date = _sample_date_window()
    frame = _call_provider(
        lambda: pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date),
        f"CN daily_bar {ticker}",
    )
    return _records(frame)


def _fetch_cn_valuation_raw(ticker: str) -> list[dict[str, Any]]:
    ts_code = normalize_cn_ticker_for_tushare(ticker)
    pro = _get_pro_client()
    start_date, end_date = _sample_date_window()
    daily_rows = _records(
        _call_provider(
            lambda: pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date),
            f"CN valuation trade_date seed {ticker}",
        ),
        limit=20,
    )
    trade_dates = sorted(
        str(row.get("trade_date"))
        for row in daily_rows
        if row.get("trade_date") not in (None, "")
    )
    if not trade_dates:
        return []
    latest_trade_date = trade_dates[-1]
    if latest_trade_date not in _DAILY_BASIC_BY_DATE_CACHE:
        fields = "ts_code,trade_date,total_mv,pe_ttm,pe,pb,ps_ttm,dv_ttm,dv_ratio"
        frame = _call_provider(
            lambda: pro.daily_basic(ts_code="", trade_date=latest_trade_date, fields=fields),
            f"CN valuation_snapshot all-sample trade_date {latest_trade_date}",
        )
        _DAILY_BASIC_BY_DATE_CACHE[latest_trade_date] = _records(frame, limit=10000)
    rows = [
        row
        for row in _DAILY_BASIC_BY_DATE_CACHE[latest_trade_date]
        if str(row.get("ts_code")) == ts_code
    ]
    return rows[-5:]


def _fetch_cn_financial_raw(ticker: str) -> list[dict[str, Any]]:
    ts_code = normalize_cn_ticker_for_tushare(ticker)
    pro = _get_pro_client()
    income_rows = _records(
        _call_provider(lambda: pro.income(ts_code=ts_code), f"CN income statement {ticker}"),
        limit=20,
    )
    cashflow_rows = _records(
        _call_provider(lambda: pro.cashflow(ts_code=ts_code), f"CN cashflow statement {ticker}"),
        limit=20,
    )
    balance_rows = _records(
        _call_provider(lambda: pro.balancesheet(ts_code=ts_code), f"CN balance sheet {ticker}"),
        limit=20,
    )
    latest_dates = [
        _to_date(row.get("end_date"))
        for rows in (income_rows, cashflow_rows, balance_rows)
        for row in rows
    ]
    latest_dates = [item for item in latest_dates if item is not None]
    if not latest_dates:
        return []
    target = max(latest_dates)

    def row_for_date(rows: list[dict[str, Any]]) -> dict[str, Any]:
        for row in rows:
            if _to_date(row.get("end_date")) == target:
                return row
        return {}

    merged: dict[str, Any] = {"end_date": target.strftime("%Y%m%d")}
    for row in (row_for_date(income_rows), row_for_date(cashflow_rows), row_for_date(balance_rows)):
        merged.update(row)
    return [merged]


def fetch_trade_calendar_sample() -> list[dict[str, Any]]:
    pro = _get_pro_client()
    start_date, end_date = _sample_date_window()
    frame = _call_provider(
        lambda: pro.trade_cal(exchange="", start_date=start_date, end_date=end_date),
        "CN trade_calendar",
    )
    return _records(frame)


def _daily_bar_from_row(
    *, ticker: str, row: dict[str, Any], source_updated_at: datetime
) -> DailyBar:
    flags = _missing_flags(row, DAILY_BAR_FIELD_MAP)
    bar_date = _to_date(_first_present(row, DAILY_BAR_FIELD_MAP["date"]))
    if bar_date is None:
        flags.append(f"{QualityFlag.MISSING_FIELD.value}:date_parse")
        bar_date = source_updated_at.date()
    flags.append(f"{QualityFlag.UNIT_UNVERIFIED.value}:volume")
    flags.append(f"{QualityFlag.UNIT_UNVERIFIED.value}:amount")
    flags.append(f"{QualityFlag.ADJUSTMENT_UNVERIFIED.value}:none")
    volume = _parse_float_field(row, DAILY_BAR_FIELD_MAP, "volume", flags)
    amount = _parse_float_field(row, DAILY_BAR_FIELD_MAP, "amount", flags)
    if volume is not None:
        volume *= 100.0
        flags.append("unit_normalized:volume_hands_to_shares")
    if amount is not None:
        amount *= 1000.0
        flags.append("unit_normalized:amount_thousand_yuan_to_yuan")

    return DailyBar(
        market=Market.CN,
        ticker=ticker,
        date=bar_date,
        open=_parse_float_field(row, DAILY_BAR_FIELD_MAP, "open", flags),
        high=_parse_float_field(row, DAILY_BAR_FIELD_MAP, "high", flags),
        low=_parse_float_field(row, DAILY_BAR_FIELD_MAP, "low", flags),
        close=_parse_float_field(row, DAILY_BAR_FIELD_MAP, "close", flags),
        adj_close=None,
        volume=volume,
        amount=amount,
        turnover=None,
        source="tushare",
        source_updated_at=source_updated_at,
        adjustment="none",
        quality_flags=flags,
    )


def _valuation_from_row(
    *, ticker: str, row: dict[str, Any], source_updated_at: datetime
) -> ValuationSnapshot:
    flags = _missing_flags(row, VALUATION_FIELD_MAP)
    for field in ("market_cap", "dividend_yield"):
        if row.get(field) is not None or _first_present(row, VALUATION_FIELD_MAP[field]) is not None:
            flags.append(f"{QualityFlag.UNIT_UNVERIFIED.value}:{field}")
    if _first_present(row, VALUATION_FIELD_MAP["ev_ebitda"]) is None:
        flags.append(f"{QualityFlag.PARTIAL_COVERAGE.value}:ev_ebitda")
    if _first_present(row, VALUATION_FIELD_MAP["fcf_yield"]) is None:
        flags.append(f"{QualityFlag.PARTIAL_COVERAGE.value}:fcf_yield")
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
        ev_ebitda=_parse_float_field(row, VALUATION_FIELD_MAP, "ev_ebitda", flags),
        dividend_yield=_parse_float_field(row, VALUATION_FIELD_MAP, "dividend_yield", flags),
        fcf_yield=_parse_float_field(row, VALUATION_FIELD_MAP, "fcf_yield", flags),
        source="tushare",
        source_updated_at=source_updated_at,
        quality_flags=flags,
    )


def _fundamentals_from_row(
    *, ticker: str, row: dict[str, Any], source_updated_at: datetime
) -> FundamentalsSnapshot:
    flags = _missing_flags(row, FUNDAMENTALS_FIELD_MAP)
    flags.append(f"{QualityFlag.UNIT_UNVERIFIED.value}:financial_fields")
    flags.append("source_date_unverified:financial_fields")
    period_end = _to_date(_first_present(row, FUNDAMENTALS_FIELD_MAP["period_end"]))
    if period_end is None:
        flags.append(f"{QualityFlag.MISSING_FIELD.value}:period_end_parse")
        period_end = source_updated_at.date()
    return FundamentalsSnapshot(
        market=Market.CN,
        ticker=ticker,
        period_end=period_end,
        fiscal_period=None,
        report_date=_to_date(_first_present(row, FUNDAMENTALS_FIELD_MAP["report_date"])),
        revenue=_parse_float_field(row, FUNDAMENTALS_FIELD_MAP, "revenue", flags),
        gross_profit=_parse_float_field(row, FUNDAMENTALS_FIELD_MAP, "gross_profit", flags),
        operating_income=_parse_float_field(row, FUNDAMENTALS_FIELD_MAP, "operating_income", flags),
        net_income=_parse_float_field(row, FUNDAMENTALS_FIELD_MAP, "net_income", flags),
        operating_cash_flow=_parse_float_field(row, FUNDAMENTALS_FIELD_MAP, "operating_cash_flow", flags),
        free_cash_flow=_parse_float_field(row, FUNDAMENTALS_FIELD_MAP, "free_cash_flow", flags),
        total_assets=_parse_float_field(row, FUNDAMENTALS_FIELD_MAP, "total_assets", flags),
        total_liabilities=_parse_float_field(row, FUNDAMENTALS_FIELD_MAP, "total_liabilities", flags),
        total_equity=_parse_float_field(row, FUNDAMENTALS_FIELD_MAP, "total_equity", flags),
        debt=_parse_float_field(row, FUNDAMENTALS_FIELD_MAP, "debt", flags),
        shares_outstanding=_parse_float_field(row, FUNDAMENTALS_FIELD_MAP, "shares_outstanding", flags),
        source="tushare",
        source_updated_at=source_updated_at,
        quality_flags=flags,
    )


def fetch_cn_daily_bar_sample(ticker: str) -> list[DailyBar]:
    source_updated_at = datetime.now(UTC)
    return [
        _daily_bar_from_row(ticker=ticker, row=row, source_updated_at=source_updated_at)
        for row in _fetch_cn_daily_bar_raw(ticker)
    ]


def fetch_cn_valuation_sample(ticker: str) -> list[ValuationSnapshot]:
    source_updated_at = datetime.now(UTC)
    return [
        _valuation_from_row(ticker=ticker, row=row, source_updated_at=source_updated_at)
        for row in _fetch_cn_valuation_raw(ticker)
    ]


def fetch_cn_financial_snapshot_sample(ticker: str) -> list[FundamentalsSnapshot]:
    source_updated_at = datetime.now(UTC)
    return [
        _fundamentals_from_row(ticker=ticker, row=row, source_updated_at=source_updated_at)
        for row in _fetch_cn_financial_raw(ticker)
    ]
