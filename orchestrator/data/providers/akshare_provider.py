"""AkShare provider adapter for minimal data coverage probes."""

from __future__ import annotations

import json
import os
import re
import subprocess
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any, Callable, Iterator
from urllib.parse import urlencode

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
EASTMONEY_PROXY_MODE_ENV = "ARS_AKSHARE_EASTMONEY_PROXY_MODE"
EASTMONEY_PROXY_MODES = ("direct_no_proxy", "respect_env_proxy", "auto")
AKSHARE_DAILY_SOURCE_MODE_ENV = "ARS_AKSHARE_DAILY_SOURCE_MODE"
AKSHARE_DAILY_SOURCE_MODES = ("sina_first", "eastmoney_first", "eastmoney_only", "sina_only")
_EASTMONEY_CALL_HISTORY: list[dict[str, str]] = []


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


def normalize_cn_ticker_for_sina(ticker: str) -> str:
    match = CN_TICKER_RE.fullmatch(ticker.upper())
    if not match:
        raise AkShareProviderError(
            f"Invalid CN ticker '{ticker}'. Expected project format like 600519.SH or 000001.SZ."
        )
    prefix = "sh" if match.group("exchange") == "SH" else "sz"
    return f"{prefix}{match.group('code')}"


def normalize_cn_ticker_for_eastmoney_symbol(ticker: str) -> str:
    match = CN_TICKER_RE.fullmatch(ticker.upper())
    if not match:
        raise AkShareProviderError(
            f"Invalid CN ticker '{ticker}'. Expected project format like 600519.SH or 000001.SZ."
        )
    return f"{match.group('exchange')}{match.group('code')}"


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


def get_configured_eastmoney_proxy_mode() -> str:
    mode = os.environ.get(EASTMONEY_PROXY_MODE_ENV, "auto").strip().lower()
    if mode not in EASTMONEY_PROXY_MODES:
        allowed = ", ".join(EASTMONEY_PROXY_MODES)
        raise AkShareProviderError(
            f"Invalid {EASTMONEY_PROXY_MODE_ENV}='{mode}'. Expected one of: {allowed}."
        )
    return mode


def get_configured_akshare_daily_source_mode() -> str:
    mode = os.environ.get(AKSHARE_DAILY_SOURCE_MODE_ENV, "sina_first").strip().lower()
    if mode not in AKSHARE_DAILY_SOURCE_MODES:
        allowed = ", ".join(AKSHARE_DAILY_SOURCE_MODES)
        raise AkShareProviderError(
            f"Invalid {AKSHARE_DAILY_SOURCE_MODE_ENV}='{mode}'. Expected one of: {allowed}."
        )
    return mode


def reset_eastmoney_call_history() -> None:
    _EASTMONEY_CALL_HISTORY.clear()


def get_eastmoney_call_history() -> list[dict[str, str]]:
    return [item.copy() for item in _EASTMONEY_CALL_HISTORY]


def _summarize_error(exc: Exception) -> str:
    text = str(exc).replace("\n", " ").strip()
    return text[:500] if len(text) > 500 else text


def _record_eastmoney_call(
    *,
    context: str,
    configured_mode: str,
    attempted_mode: str,
    transport: str,
    status: str,
    error: str = "",
) -> None:
    _EASTMONEY_CALL_HISTORY.append(
        {
            "context": context,
            "configured_mode": configured_mode,
            "attempted_mode": attempted_mode,
            "transport": transport,
            "status": status,
            "error": error,
        }
    )


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
    configured_mode = get_configured_eastmoney_proxy_mode()
    return {
        "enabled": configured_mode == "direct_no_proxy",
        "mode": configured_mode,
        "configured_proxy_mode": configured_mode,
        "daily_source_mode": get_configured_akshare_daily_source_mode(),
        "no_proxy": os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or "-",
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


def _call_eastmoney_once(
    call: Callable[[], Any],
    context: str,
    *,
    configured_mode: str,
    attempted_mode: str,
    transport: str,
) -> Any:
    try:
        if attempted_mode == "direct_no_proxy":
            with _eastmoney_direct_connection_env():
                result = _call_provider(call, context)
        elif attempted_mode == "respect_env_proxy":
            result = _call_provider(call, context)
        else:
            raise AkShareProviderError(f"Unsupported Eastmoney proxy attempt mode: {attempted_mode}")
    except AkShareProviderError as exc:
        _record_eastmoney_call(
            context=context,
            configured_mode=configured_mode,
            attempted_mode=attempted_mode,
            transport=transport,
            status="failed",
            error=_summarize_error(exc),
        )
        raise

    _record_eastmoney_call(
        context=context,
        configured_mode=configured_mode,
        attempted_mode=attempted_mode,
        transport=transport,
        status="success",
    )
    return result


def _call_eastmoney_provider(
    call: Callable[[], Any],
    context: str,
    *,
    transport: str = "akshare_requests",
) -> Any:
    configured_mode = get_configured_eastmoney_proxy_mode()
    if configured_mode in {"direct_no_proxy", "respect_env_proxy"}:
        return _call_eastmoney_once(
            call,
            context,
            configured_mode=configured_mode,
            attempted_mode=configured_mode,
            transport=transport,
        )

    errors: dict[str, str] = {}
    for attempted_mode in ("respect_env_proxy", "direct_no_proxy"):
        try:
            return _call_eastmoney_once(
                call,
                context,
                configured_mode=configured_mode,
                attempted_mode=attempted_mode,
                transport=transport,
            )
        except AkShareProviderError as exc:
            errors[attempted_mode] = _summarize_error(exc)
    raise AkShareProviderError(
        f"Eastmoney provider call failed for {context}; "
        f"respect_env_proxy failed: {errors.get('respect_env_proxy', '-')}; "
        f"direct_no_proxy failed: {errors.get('direct_no_proxy', '-')}"
    )


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


def _records(frame: Any) -> list[dict[str, Any]]:
    try:
        records = frame.to_dict("records")
    except Exception as exc:  # pragma: no cover - provider object dependent
        raise AkShareProviderError(f"AkShare returned an unsupported table object: {exc}") from exc
    if not isinstance(records, list):
        raise AkShareProviderError("AkShare returned an unsupported table format.")
    return records


def _tail_raw_records(rows: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    return rows[-limit:] if rows else []


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
    if str(value).strip().lower() in {"nat", "nan", "none", "null", "--"}:
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
    "ev_ebitda": ["ev_ebitda", "EV/EBITDA-24A"],
    "dividend_yield": ["dividend_yield", "dv_ttm", "dv_ratio", "股息率"],
    "fcf_yield": ["fcf_yield"],
}
VALUATION_INDICATOR_MAP = {
    "market_cap": "总市值",
    "pe": "市盈率(TTM)",
    "pb": "市净率",
}
VALUATION_SOURCE_DATE_UNVERIFIED_FIELDS = ("ps", "ev_ebitda")

EASTMONEY_A_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
EASTMONEY_HK_KLINE_URL = "https://33.push2his.eastmoney.com/api/qt/stock/kline/get"
EASTMONEY_A_KLINE_URLS = (
    EASTMONEY_A_KLINE_URL,
    "https://33.push2his.eastmoney.com/api/qt/stock/kline/get",
    "https://80.push2his.eastmoney.com/api/qt/stock/kline/get",
)
EASTMONEY_HK_KLINE_URLS = (
    EASTMONEY_HK_KLINE_URL,
    "https://push2his.eastmoney.com/api/qt/stock/kline/get",
    "https://80.push2his.eastmoney.com/api/qt/stock/kline/get",
)
EASTMONEY_KLINE_FIELDS = [
    "日期",
    "开盘",
    "收盘",
    "最高",
    "最低",
    "成交量",
    "成交额",
    "振幅",
    "涨跌幅",
    "涨跌额",
    "换手率",
]


def _eastmoney_cn_market_code(symbol: str) -> str:
    return "1" if symbol.startswith("6") else "0"


def _eastmoney_adjust_code(adjust: str) -> str:
    adjust_map = {"qfq": "1", "hfq": "2", "none": "0", "": "0"}
    try:
        return adjust_map[adjust]
    except KeyError as exc:
        raise AkShareProviderError("adjust must be one of: qfq, hfq, none") from exc


def _build_eastmoney_cn_kline_url(
    *,
    base_url: str = EASTMONEY_A_KLINE_URL,
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str,
) -> str:
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": "101",
        "fqt": _eastmoney_adjust_code(adjust),
        "secid": f"{_eastmoney_cn_market_code(symbol)}.{symbol}",
        "beg": start_date,
        "end": end_date,
    }
    return f"{base_url}?{urlencode(params)}"


def _build_eastmoney_hk_kline_url(
    *,
    base_url: str = EASTMONEY_HK_KLINE_URL,
    symbol: str,
    start_date: str,
    end_date: str,
) -> str:
    params = {
        "secid": f"116.{symbol}",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "0",
        "end": "20500000",
        "lmt": "1000000",
    }
    return f"{base_url}?{urlencode(params)}"


def _run_curl_json(url: str, attempted_mode: str, context: str) -> dict[str, Any]:
    command = [
        "curl",
        "-L",
        "-sS",
        "--fail",
        "--max-time",
        "20",
    ]
    if attempted_mode == "direct_no_proxy":
        command.extend(["--noproxy", "*"])
    command.append(url)

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=25,
        )
    except FileNotFoundError as exc:
        raise AkShareProviderError("curl executable is required for Eastmoney fallback but was not found.") from exc
    except subprocess.TimeoutExpired as exc:
        raise AkShareProviderError(f"curl Eastmoney fallback timed out for {context}.") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise AkShareProviderError(
            f"curl Eastmoney fallback failed for {context}: exit={completed.returncode}; {stderr[:500]}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AkShareProviderError(f"curl Eastmoney fallback returned invalid JSON for {context}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AkShareProviderError(f"curl Eastmoney fallback returned unsupported JSON for {context}.")
    return payload


def _parse_eastmoney_kline_payload(
    payload: dict[str, Any],
    *,
    context: str,
    symbol: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise AkShareProviderError(f"Eastmoney kline payload missing data for {context}.")
    klines = data.get("klines")
    if not isinstance(klines, list):
        raise AkShareProviderError(f"Eastmoney kline payload missing klines for {context}.")

    rows: list[dict[str, Any]] = []
    start_iso = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}" if start_date else None
    end_iso = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}" if end_date else None
    for item in klines:
        parts = str(item).split(",")
        if len(parts) < len(EASTMONEY_KLINE_FIELDS):
            continue
        row = dict(zip(EASTMONEY_KLINE_FIELDS, parts[: len(EASTMONEY_KLINE_FIELDS)], strict=False))
        if symbol is not None:
            row["股票代码"] = symbol
        row["_transport"] = "curl_cli"
        row_date = str(row["日期"])
        if start_iso and row_date < start_iso:
            continue
        if end_iso and row_date > end_iso:
            continue
        rows.append(row)
    return rows


def _call_eastmoney_curl_json(url: str, context: str) -> dict[str, Any]:
    configured_mode = get_configured_eastmoney_proxy_mode()

    def make_call(attempted_mode: str) -> Callable[[], dict[str, Any]]:
        return lambda attempted_mode=attempted_mode: _run_curl_json(url, attempted_mode, context)

    if configured_mode in {"direct_no_proxy", "respect_env_proxy"}:
        return _call_eastmoney_once(
            make_call(configured_mode),
            context,
            configured_mode=configured_mode,
            attempted_mode=configured_mode,
            transport="curl_cli",
        )

    errors: dict[str, str] = {}
    for attempted_mode in ("respect_env_proxy", "direct_no_proxy"):
        try:
            return _call_eastmoney_once(
                make_call(attempted_mode),
                context,
                configured_mode=configured_mode,
                attempted_mode=attempted_mode,
                transport="curl_cli",
            )
        except AkShareProviderError as exc:
            errors[attempted_mode] = _summarize_error(exc)
    raise AkShareProviderError(
        f"Eastmoney curl fallback failed for {context}; "
        f"respect_env_proxy failed: {errors.get('respect_env_proxy', '-')}; "
        f"direct_no_proxy failed: {errors.get('direct_no_proxy', '-')}"
    )


def _fetch_cn_daily_bar_raw_via_curl(
    *,
    ticker: str,
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str,
) -> list[dict[str, Any]]:
    errors: list[str] = []
    for base_url in EASTMONEY_A_KLINE_URLS:
        url = _build_eastmoney_cn_kline_url(
            base_url=base_url,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        context = f"CN daily_bar {ticker} curl_fallback {base_url}"
        try:
            payload = _call_eastmoney_curl_json(url, context)
            return _tail_raw_records(
                _parse_eastmoney_kline_payload(
                    payload,
                    context=context,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        except AkShareProviderError as exc:
            errors.append(f"{base_url}: {_summarize_error(exc)}")
    raise AkShareProviderError("; ".join(errors))


def _fetch_hk_daily_bar_raw_via_curl(
    *,
    ticker: str,
    symbol: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    errors: list[str] = []
    for base_url in EASTMONEY_HK_KLINE_URLS:
        url = _build_eastmoney_hk_kline_url(
            base_url=base_url,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
        context = f"HK daily_bar {ticker} curl_fallback {base_url}"
        try:
            payload = _call_eastmoney_curl_json(url, context)
            return _tail_raw_records(
                _parse_eastmoney_kline_payload(
                    payload,
                    context=context,
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        except AkShareProviderError as exc:
            errors.append(f"{base_url}: {_summarize_error(exc)}")
    raise AkShareProviderError("; ".join(errors))


def _fetch_cn_daily_bar_raw_via_sina(
    *,
    ak: Any,
    ticker: str,
    start_date: str,
    end_date: str,
    adjust: str,
) -> list[dict[str, Any]]:
    symbol = normalize_cn_ticker_for_sina(ticker)
    provider_adjust = "" if adjust == "none" else adjust
    frame = _call_provider(
        lambda: ak.stock_zh_a_daily(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=provider_adjust,
        ),
        f"CN daily_bar {ticker} sina",
    )
    rows = _tail_records(frame)
    for row in rows:
        row["_transport"] = "akshare_sina"
    return rows


def _fetch_hk_daily_bar_raw_via_sina(
    *,
    ak: Any,
    ticker: str,
) -> list[dict[str, Any]]:
    symbol = normalize_hk_ticker_for_akshare(ticker)
    frame = _call_provider(
        lambda: ak.stock_hk_daily(symbol=symbol, adjust=""),
        f"HK daily_bar {ticker} sina",
    )
    rows = _tail_records(frame)
    for row in rows:
        row["_transport"] = "akshare_sina"
    return rows


def _fetch_cn_daily_bar_raw_via_eastmoney(
    *,
    ak: Any,
    ticker: str,
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str,
) -> list[dict[str, Any]]:
    provider_adjust = "" if adjust == "none" else adjust
    try:
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
    except AkShareProviderError as akshare_exc:
        try:
            return _fetch_cn_daily_bar_raw_via_curl(
                ticker=ticker,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
        except AkShareProviderError as curl_exc:
            raise AkShareProviderError(
                f"CN daily_bar {ticker} failed through Eastmoney requests and curl fallback; "
                f"akshare_requests: {_summarize_error(akshare_exc)}; "
                f"curl_cli: {_summarize_error(curl_exc)}"
            ) from curl_exc


def _fetch_hk_daily_bar_raw_via_eastmoney(
    *,
    ak: Any,
    ticker: str,
    symbol: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
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

    try:
        frame = _call_eastmoney_provider(call, f"HK daily_bar {ticker}")
        return _tail_records(frame)
    except AkShareProviderError as akshare_exc:
        try:
            return _fetch_hk_daily_bar_raw_via_curl(
                ticker=ticker,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            )
        except AkShareProviderError as curl_exc:
            raise AkShareProviderError(
                f"HK daily_bar {ticker} failed through Eastmoney requests and curl fallback; "
                f"akshare_requests: {_summarize_error(akshare_exc)}; "
                f"curl_cli: {_summarize_error(curl_exc)}"
            ) from curl_exc


def _fetch_cn_daily_bar_raw(ticker: str, adjust: str = "qfq") -> list[dict[str, Any]]:
    if adjust not in {"qfq", "hfq", "none"}:
        raise AkShareProviderError("adjust must be one of: qfq, hfq, none")
    ak = _load_akshare()
    symbol = normalize_cn_ticker_for_akshare(ticker)
    start_date, end_date = _sample_date_window()
    mode = get_configured_akshare_daily_source_mode()
    if mode == "sina_only":
        return _fetch_cn_daily_bar_raw_via_sina(
            ak=ak,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
    if mode == "eastmoney_only":
        return _fetch_cn_daily_bar_raw_via_eastmoney(
            ak=ak,
            ticker=ticker,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
    first, second = (
        ("sina", "eastmoney") if mode == "sina_first" else ("eastmoney", "sina")
    )
    errors: list[str] = []
    for source in (first, second):
        try:
            if source == "sina":
                return _fetch_cn_daily_bar_raw_via_sina(
                    ak=ak,
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )
            return _fetch_cn_daily_bar_raw_via_eastmoney(
                ak=ak,
                symbol=symbol,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
        except AkShareProviderError as exc:
            errors.append(f"{source}: {_summarize_error(exc)}")
    raise AkShareProviderError(f"CN daily_bar {ticker} failed through AkShare daily sources; " + "; ".join(errors))


def _fetch_hk_daily_bar_raw(ticker: str) -> list[dict[str, Any]]:
    ak = _load_akshare()
    symbol = normalize_hk_ticker_for_akshare(ticker)
    start_date, end_date = _sample_date_window()
    mode = get_configured_akshare_daily_source_mode()
    if mode == "sina_only":
        return _fetch_hk_daily_bar_raw_via_sina(ak=ak, ticker=ticker)
    if mode == "eastmoney_only":
        return _fetch_hk_daily_bar_raw_via_eastmoney(
            ak=ak,
            ticker=ticker,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
    first, second = (
        ("sina", "eastmoney") if mode == "sina_first" else ("eastmoney", "sina")
    )
    errors: list[str] = []
    for source in (first, second):
        try:
            if source == "sina":
                return _fetch_hk_daily_bar_raw_via_sina(ak=ak, ticker=ticker)
            return _fetch_hk_daily_bar_raw_via_eastmoney(
                ak=ak,
                ticker=ticker,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            )
        except AkShareProviderError as exc:
            errors.append(f"{source}: {_summarize_error(exc)}")
    raise AkShareProviderError(f"HK daily_bar {ticker} failed through AkShare daily sources; " + "; ".join(errors))


def _latest_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return rows[-1] if rows else None


def _row_by_date(rows: list[dict[str, Any]], target_date: date) -> dict[str, Any] | None:
    for row in rows:
        if _to_date(row.get("date")) == target_date:
            return row
    return None


def _merge_valuation_indicator_rows(
    indicator_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    indicator_dates: dict[str, str] = {}
    indicator_names: dict[str, str] = {}
    date_sets: list[set[date]] = []
    for rows in indicator_rows.values():
        parsed_dates = {_to_date(row.get("date")) for row in rows}
        parsed_dates = {item for item in parsed_dates if item is not None}
        if parsed_dates:
            date_sets.append(parsed_dates)

    common_dates = set.intersection(*date_sets) if date_sets else set()
    aligned_date = max(common_dates) if common_dates else None
    for contract_field, rows in indicator_rows.items():
        latest = _row_by_date(rows, aligned_date) if aligned_date else _latest_row(rows)
        if not latest:
            continue
        row_date = latest.get("date")
        if row_date is not None:
            indicator_dates[contract_field] = str(row_date)
        indicator_names[contract_field] = str(latest.get("_akshare_indicator", ""))
        merged[contract_field] = latest.get("value")

    parsed_dates = [_to_date(value) for value in indicator_dates.values()]
    parsed_dates = [item for item in parsed_dates if item is not None]
    if aligned_date:
        merged["date"] = aligned_date
        merged["_akshare_valuation_alignment"] = "latest_common_date"
    elif parsed_dates:
        merged["date"] = max(parsed_dates)
        merged["_akshare_valuation_alignment"] = "fallback_latest_per_indicator"
    merged["_akshare_indicator_dates"] = indicator_dates
    merged["_akshare_indicator_names"] = indicator_names
    return merged


def _fetch_eastmoney_valuation_comparison_rows(symbol: str) -> list[dict[str, Any]]:
    try:
        import requests  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - AkShare installs requests
        raise AkShareProviderError("requests is required for Eastmoney valuation comparison.") from exc
    url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    params = {
        "reportName": "RPT_PCF10_INDUSTRY_CVALUE",
        "columns": "ALL",
        "quoteColumns": "",
        "filter": f'(SECUCODE="{symbol[2:]}.{symbol[:2]}")',
        "pageNumber": "",
        "pageSize": "",
        "sortTypes": "1",
        "sortColumns": "PAIMING",
        "source": "HSF10",
        "client": "PC",
    }
    response = requests.get(url, params=params, timeout=15)
    data_json = response.json()
    data = data_json.get("result", {}).get("data", [])
    if not isinstance(data, list):
        raise AkShareProviderError("Eastmoney valuation comparison returned unsupported JSON.")
    return [item for item in data if isinstance(item, dict)]


def _merge_valuation_comparison_row(ak: Any, ticker: str, merged: dict[str, Any]) -> None:
    symbol = normalize_cn_ticker_for_eastmoney_symbol(ticker)
    rows = _call_provider(
        lambda: _fetch_eastmoney_valuation_comparison_rows(symbol),
        f"CN valuation comparison {ticker}",
    )
    target_code = normalize_cn_ticker_for_akshare(ticker)
    row = next(
        (item for item in rows if str(item.get("CORRE_SECURITY_CODE") or item.get("SECURITY_CODE")) == target_code),
        rows[0] if rows else None,
    )
    if not row:
        return
    if row.get("PS_TTM") not in (None, ""):
        merged["ps"] = row.get("PS_TTM")
    if row.get("QYBS") not in (None, ""):
        merged["ev_ebitda"] = row.get("QYBS")
    indicator_dates = merged.setdefault("_akshare_indicator_dates", {})
    indicator_names = merged.setdefault("_akshare_indicator_names", {})
    if isinstance(indicator_dates, dict):
        for field in VALUATION_SOURCE_DATE_UNVERIFIED_FIELDS:
            if field in merged:
                indicator_dates[field] = "unverified_current"
    if isinstance(indicator_names, dict):
        if "ps" in merged:
            indicator_names["ps"] = "stock_zh_valuation_comparison_em:市销率-TTM"
        if "ev_ebitda" in merged:
            indicator_names["ev_ebitda"] = "stock_zh_valuation_comparison_em:EV/EBITDA-24A"


def _merge_estimated_dividend_yield(ak: Any, ticker: str, merged: dict[str, Any]) -> None:
    symbol = normalize_cn_ticker_for_akshare(ticker)
    dividend_frame = _call_provider(
        lambda: ak.stock_history_dividend_detail(symbol=symbol, indicator="分红"),
        f"CN dividend detail {ticker}",
    )
    dividend_rows = _records(dividend_frame)
    daily_rows = _fetch_cn_daily_bar_raw(ticker, adjust="none")
    latest_bar = _latest_row(daily_rows)
    if not latest_bar:
        return
    close = _to_float(_first_present(latest_bar, DAILY_BAR_FIELD_MAP["close"]))
    latest_date = _to_date(_first_present(latest_bar, DAILY_BAR_FIELD_MAP["date"]))
    if close is None or close == 0 or latest_date is None:
        return

    trailing_start = latest_date - timedelta(days=365)
    cash_dividend_total = 0.0
    used_dates: list[str] = []
    for row in dividend_rows:
        ex_date = _to_date(row.get("除权除息日"))
        cash_per_10 = _to_float(row.get("派息"))
        if ex_date is None or cash_per_10 is None:
            continue
        if trailing_start <= ex_date <= latest_date:
            cash_dividend_total += cash_per_10 / 10.0
            used_dates.append(ex_date.isoformat())
    if cash_dividend_total <= 0:
        return

    merged["dividend_yield"] = (cash_dividend_total / close) * 100.0
    merged["_akshare_dividend_yield_method"] = "estimated_ttm_cash_dividend_per_share_over_latest_close"
    merged["_akshare_dividend_yield_ex_dates"] = used_dates
    indicator_dates = merged.setdefault("_akshare_indicator_dates", {})
    indicator_names = merged.setdefault("_akshare_indicator_names", {})
    if isinstance(indicator_dates, dict):
        indicator_dates["dividend_yield"] = latest_date.isoformat()
    if isinstance(indicator_names, dict):
        indicator_names["dividend_yield"] = "stock_history_dividend_detail + stock_zh_a_daily close"


def _fetch_cn_valuation_raw(ticker: str) -> list[dict[str, Any]]:
    ak = _load_akshare()
    symbol = normalize_cn_ticker_for_akshare(ticker)
    indicator_rows: dict[str, list[dict[str, Any]]] = {}
    for contract_field, indicator in VALUATION_INDICATOR_MAP.items():
        frame = _call_provider(
            lambda indicator=indicator: ak.stock_zh_valuation_baidu(
                symbol=symbol, indicator=indicator, period="近一年"
            ),
            f"CN valuation {ticker} {indicator}",
        )
        rows = _tail_records(frame)
        for row in rows:
            row["_akshare_indicator"] = indicator
        indicator_rows[contract_field] = rows
    merged = _merge_valuation_indicator_rows(indicator_rows)
    try:
        _merge_valuation_comparison_row(ak, ticker, merged)
    except AkShareProviderError as exc:
        merged.setdefault("_akshare_optional_errors", []).append(f"valuation_comparison:{_summarize_error(exc)}")
    try:
        _merge_estimated_dividend_yield(ak, ticker, merged)
    except AkShareProviderError as exc:
        merged.setdefault("_akshare_optional_errors", []).append(f"dividend_yield:{_summarize_error(exc)}")
    return [merged]


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
    for flag in list(flags):
        if flag.startswith(f"{QualityFlag.MISSING_FIELD.value}:"):
            field = flag.split(":", 1)[1]
            flags.append(f"{QualityFlag.PARTIAL_COVERAGE.value}:{field}")
    flags.append(f"{QualityFlag.UNIT_UNVERIFIED.value}:market_cap")
    for field in ("ps", "ev_ebitda"):
        if row.get(field) is not None:
            flags.append(f"source_date_unverified:{field}")
    if row.get("dividend_yield") is not None:
        flags.append(f"{QualityFlag.ESTIMATED_VALUE.value}:dividend_yield")
        flags.append(f"{QualityFlag.UNIT_UNVERIFIED.value}:dividend_yield")
    if row.get("_akshare_optional_errors"):
        flags.append("optional_provider_error:" + ";".join(str(item) for item in row["_akshare_optional_errors"]))
    if row.get("_akshare_valuation_alignment") == "fallback_latest_per_indicator":
        flags.append(f"{QualityFlag.ASOF_MISMATCH.value}:fallback_latest_per_indicator")

    snapshot_date = _to_date(_first_present(row, VALUATION_FIELD_MAP["date"]))
    if snapshot_date is None:
        flags.append(f"{QualityFlag.MISSING_FIELD.value}:date_parse")
        snapshot_date = source_updated_at.date()
    indicator_dates = row.get("_akshare_indicator_dates")
    if isinstance(indicator_dates, dict):
        comparable_dates = {
            str(value)
            for value in indicator_dates.values()
            if value and str(value) != "unverified_current"
        }
        unique_dates = sorted(comparable_dates)
        if len(unique_dates) > 1:
            flags.append(
                f"{QualityFlag.ASOF_MISMATCH.value}:"
                + ",".join(f"{key}={value}" for key, value in sorted(indicator_dates.items()))
            )

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
