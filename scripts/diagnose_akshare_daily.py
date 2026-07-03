#!/usr/bin/env python3
"""Diagnose AkShare daily-bar connectivity and proxy behavior."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.data.providers.akshare_provider import (  # noqa: E402
    AkShareProviderError,
    EASTMONEY_PROXY_MODE_ENV,
    _fetch_cn_daily_bar_raw_via_curl,
    _fetch_hk_daily_bar_raw_via_curl,
    _eastmoney_direct_connection_env,
    normalize_cn_ticker_for_akshare,
    normalize_cn_ticker_for_sina,
    normalize_hk_ticker_for_akshare,
)


REPORT_PATH = ROOT / "outputs" / "reports" / "akshare_daily_diagnostics.md"
PROXY_ENV_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy")
PROXY_MODES = ("respect_env_proxy", "direct_no_proxy")
LOOKBACK_DAYS = 90


@dataclass(slots=True)
class DiagnosticRecord:
    market: str
    ticker: str
    interface: str
    transport: str
    proxy_mode: str
    status: str
    shape: str
    columns: list[str]
    reason: str


def _load_akshare() -> Any:
    try:
        import akshare as ak  # type: ignore[import-not-found]
    except ImportError as exc:
        raise AkShareProviderError("AkShare is not installed.") from exc
    return ak


def _date_window() -> tuple[str, str]:
    end = datetime.now(UTC).date()
    start = end - timedelta(days=LOOKBACK_DAYS)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def _context_for_mode(mode: str):
    if mode == "direct_no_proxy":
        return _eastmoney_direct_connection_env()
    return nullcontext()


@contextmanager
def _configured_proxy_mode(mode: str):
    saved = os.environ.get(EASTMONEY_PROXY_MODE_ENV)
    os.environ[EASTMONEY_PROXY_MODE_ENV] = mode
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop(EASTMONEY_PROXY_MODE_ENV, None)
        else:
            os.environ[EASTMONEY_PROXY_MODE_ENV] = saved


def _summarize_frame(frame: Any) -> tuple[str, list[str]]:
    if isinstance(frame, list):
        if not frame:
            return "(0, 0)", []
        keys = list(frame[0].keys()) if isinstance(frame[0], dict) else []
        return f"({len(frame)}, {len(keys)})", [str(item) for item in keys]
    shape = getattr(frame, "shape", None)
    columns = list(getattr(frame, "columns", []))
    return str(shape) if shape is not None else "unknown", [str(item) for item in columns]


def _run_case(
    *,
    market: str,
    ticker: str,
    interface: str,
    transport: str,
    proxy_mode: str,
    call: Callable[[], Any],
) -> DiagnosticRecord:
    try:
        env_context = _configured_proxy_mode(proxy_mode) if transport == "curl_cli" else nullcontext()
        with env_context, _context_for_mode(proxy_mode):
            frame = call()
        shape, columns = _summarize_frame(frame)
        return DiagnosticRecord(market, ticker, interface, transport, proxy_mode, "success", shape, columns, "")
    except Exception as exc:  # provider/network dependent
        return DiagnosticRecord(market, ticker, interface, transport, proxy_mode, "failed", "-", [], str(exc))


def build_records() -> tuple[list[DiagnosticRecord], dict[str, str | bool | list[str]]]:
    ak = _load_akshare()
    start_date, end_date = _date_window()
    alternative_candidates = [
        name for name in ("stock_zh_a_daily", "stock_hk_daily") if hasattr(ak, name)
    ]
    metadata: dict[str, str | bool | list[str]] = {
        "python_executable": sys.executable,
        "akshare_version": getattr(ak, "__version__", "unknown"),
        "proxy_env_vars_present": ", ".join(key for key in PROXY_ENV_KEYS if os.environ.get(key)) or "-",
        "no_proxy": os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or "-",
        "alternative_daily_functions": alternative_candidates,
    }

    records: list[DiagnosticRecord] = []
    for mode in PROXY_MODES:
        for ticker in ("600519.SH", "000001.SZ"):
            symbol = normalize_cn_ticker_for_akshare(ticker)
            records.append(
                _run_case(
                    market="CN",
                    ticker=ticker,
                    interface="stock_zh_a_hist",
                    transport="akshare_requests",
                    proxy_mode=mode,
                    call=lambda symbol=symbol: ak.stock_zh_a_hist(
                        symbol=symbol,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq",
                        timeout=15,
                    ),
                )
            )
            sina_symbol = normalize_cn_ticker_for_sina(ticker)
            records.append(
                _run_case(
                    market="CN",
                    ticker=ticker,
                    interface="stock_zh_a_daily",
                    transport="akshare_sina",
                    proxy_mode=mode,
                    call=lambda sina_symbol=sina_symbol: ak.stock_zh_a_daily(
                        symbol=sina_symbol,
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq",
                    ),
                )
            )
            records.append(
                _run_case(
                    market="CN",
                    ticker=ticker,
                    interface="eastmoney_kline",
                    transport="curl_cli",
                    proxy_mode=mode,
                    call=lambda ticker=ticker, symbol=symbol, start_date=start_date, end_date=end_date: _fetch_cn_daily_bar_raw_via_curl(
                        ticker=ticker,
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq",
                    ),
                )
            )
        symbol = normalize_hk_ticker_for_akshare("0700.HK")
        records.append(
            _run_case(
                market="HK",
                ticker="0700.HK",
                interface="stock_hk_hist",
                transport="akshare_requests",
                proxy_mode=mode,
                call=lambda symbol=symbol: ak.stock_hk_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="",
                ),
            )
        )
        records.append(
            _run_case(
                market="HK",
                ticker="0700.HK",
                interface="stock_hk_daily",
                transport="akshare_sina",
                proxy_mode=mode,
                call=lambda symbol=symbol: ak.stock_hk_daily(symbol=symbol, adjust=""),
            )
        )
        records.append(
            _run_case(
                market="HK",
                ticker="0700.HK",
                interface="eastmoney_kline",
                transport="curl_cli",
                proxy_mode=mode,
                call=lambda symbol=symbol, start_date=start_date, end_date=end_date: _fetch_hk_daily_bar_raw_via_curl(
                    ticker="0700.HK",
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                ),
            )
        )
    return records, metadata


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "-"


def _recommend_proxy_mode(records: list[DiagnosticRecord]) -> str:
    success_counts = {
        mode: sum(
            1
            for record in records
            if record.proxy_mode == mode
            and record.status == "success"
            and record.transport in {"curl_cli", "akshare_sina"}
        )
        for mode in PROXY_MODES
    }
    if success_counts["respect_env_proxy"] > success_counts["direct_no_proxy"]:
        return "respect_env_proxy"
    if success_counts["direct_no_proxy"] > success_counts["respect_env_proxy"]:
        return "direct_no_proxy"
    if success_counts["respect_env_proxy"] == 0 and success_counts["direct_no_proxy"] == 0:
        return "none: both proxy modes failed in this environment"
    return "auto: both proxy modes had equal success counts"


def write_report(records: list[DiagnosticRecord], metadata: dict[str, str | bool | list[str]]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AkShare Daily Diagnostics",
        "",
        f"- 运行时间: {datetime.now(UTC).isoformat()}",
        f"- Python executable: {metadata['python_executable']}",
        f"- AkShare version: {metadata['akshare_version']}",
        f"- proxy_env_vars_present: {metadata['proxy_env_vars_present']}",
        f"- no_proxy: {metadata['no_proxy']}",
        f"- alternative_daily_functions: {_format_list(metadata['alternative_daily_functions'])}",  # type: ignore[arg-type]
        f"- recommended_proxy_mode: {_recommend_proxy_mode(records)}",
        "- note: This diagnostic only tests data provider connectivity and field coverage. It does not produce signals, scores, backtests, LLM output, reports, or trading instructions.",
        "",
        "## Results",
        "",
        "| market | ticker | interface | transport | proxy_mode | status | shape | columns | reason |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        reason = record.reason.replace("|", "\\|") if record.reason else "-"
        lines.append(
            f"| {record.market} | {record.ticker} | {record.interface} | {record.transport} | {record.proxy_mode} | "
            f"{record.status} | {record.shape} | {_format_list(record.columns)} | {reason} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `akshare_requests` tests AkShare's Eastmoney Python HTTP path; `curl_cli` tests the Eastmoney command-line curl fallback; `akshare_sina` tests AkShare's Sina daily interfaces.",
            "- If both proxy modes fail for both transports, AkShare daily bars should be treated as unavailable for this environment.",
            "- If only one proxy mode succeeds for `curl_cli`, set `ARS_AKSHARE_EASTMONEY_PROXY_MODE` to that mode for provider validation.",
            "- If success varies across tickers or runs, treat Eastmoney daily-bar coverage as unstable and cross-check with another provider before strategy work.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    try:
        records, metadata = build_records()
    except AkShareProviderError as exc:
        metadata = {
            "python_executable": sys.executable,
            "akshare_version": "-",
            "proxy_env_vars_present": ", ".join(key for key in PROXY_ENV_KEYS if os.environ.get(key)) or "-",
            "no_proxy": os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or "-",
            "alternative_daily_functions": [],
        }
        records = [
            DiagnosticRecord("-", "-", "-", "akshare_requests", mode, "failed", "-", [], str(exc))
            for mode in PROXY_MODES
        ]
    write_report(records, metadata)
    success = sum(1 for record in records if record.status == "success")
    failed = sum(1 for record in records if record.status == "failed")
    print(f"success count: {success}")
    print(f"failed count: {failed}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
