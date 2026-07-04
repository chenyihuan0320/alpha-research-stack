"""Daily bar panel dataset builder.

ProviderEvidence is an admission and traceability ledger. This module builds a
small reusable daily_bar panel only when real daily bars are available from the
ledger payload or provider fetchers; it never expands summary evidence into
synthetic time series.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Iterable


PANEL_ALLOWED_DOWNSTREAM = {"vectorbt", "alphasift", "alphasift_exploratory", "qlib_candidate"}
REQUIRED_PANEL_FIELDS = ["date", "ticker", "open", "high", "low", "close", "volume"]
PANEL_FIELDNAMES = [
    "run_id",
    "market",
    "ticker",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "provider",
    "provider_evidence_id",
    "cross_source_status",
    "quality_flags",
    "adjustment",
    "source_updated_at",
]


@dataclass(slots=True)
class DailyBarPanelRow:
    run_id: str
    market: str
    ticker: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float | None
    provider: str
    provider_evidence_id: str
    cross_source_status: str
    quality_flags: list[str] = field(default_factory=list)
    adjustment: str = "unknown"
    source_updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DailyBarPanelBuildResult:
    status: str
    market: str
    tickers: list[str]
    start_date: str | None
    end_date: str | None
    row_count: int
    missing_tickers: list[str]
    warnings: list[str]
    output_path: str
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _payload(value: Any) -> dict[str, Any]:
    payload = _field(value, "normalized_payload", {})
    return payload if isinstance(payload, dict) else {}


def _allowed_downstream(value: Any) -> set[str]:
    return {str(item) for item in (_field(value, "allowed_downstream", []) or [])}


def _is_eligible_evidence(value: Any) -> bool:
    return (
        _field(value, "market") == "CN"
        and _field(value, "data_domain") == "daily_bar"
        and bool(_allowed_downstream(value) & PANEL_ALLOWED_DOWNSTREAM)
    )


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    text = str(value).strip().replace(",", "")
    if text.lower() in {"", "--", "none", "nan", "null"}:
        return None
    if text.endswith("%"):
        text = text[:-1].strip()
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _normalize_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if text.lower() in {"", "--", "none", "nan", "nat", "null"}:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return None


def _bar_to_payload(bar: Any) -> dict[str, Any]:
    if isinstance(bar, dict):
        return dict(bar)
    if hasattr(bar, "to_dict"):
        return dict(bar.to_dict())
    return dict(asdict(bar))


def _row_from_bar(bar: Any, evidence: Any, *, provider: str | None = None) -> DailyBarPanelRow | None:
    payload = _bar_to_payload(bar)
    row_date = _normalize_date(payload.get("date"))
    open_value = _to_float(payload.get("open"))
    high_value = _to_float(payload.get("high"))
    low_value = _to_float(payload.get("low"))
    close_value = _to_float(payload.get("close"))
    volume_value = _to_float(payload.get("volume"))
    if any(item is None for item in (row_date, open_value, high_value, low_value, close_value, volume_value)):
        return None
    quality_flags = list(_field(evidence, "quality_flags", []) or [])
    quality_flags.extend(str(item) for item in payload.get("quality_flags", []) or [])
    return DailyBarPanelRow(
        run_id=str(_field(evidence, "run_id", "")),
        market=str(_field(evidence, "market", "CN")),
        ticker=str(_field(evidence, "ticker", payload.get("ticker", ""))),
        date=str(row_date),
        open=float(open_value),
        high=float(high_value),
        low=float(low_value),
        close=float(close_value),
        volume=float(volume_value),
        amount=_to_float(payload.get("amount")),
        provider=provider or str(payload.get("source") or _field(evidence, "provider", "")),
        provider_evidence_id=str(_field(evidence, "evidence_id", "")),
        cross_source_status=str(_field(evidence, "cross_source_status", "unchecked")),
        quality_flags=sorted(set(quality_flags)),
        adjustment=str(payload.get("adjustment") or "unknown"),
        source_updated_at=str(payload.get("source_updated_at") or _field(evidence, "source_updated_at", "")),
    )


def _rows_from_evidence_payload(evidence: Any) -> list[DailyBarPanelRow]:
    bars = _payload(evidence).get("daily_bars", [])
    if not isinstance(bars, list):
        return []
    rows: list[DailyBarPanelRow] = []
    for bar in bars:
        if not isinstance(bar, dict):
            continue
        row = _row_from_bar(bar, evidence)
        if row is not None:
            rows.append(row)
    return sorted(rows, key=lambda item: (item.ticker, item.date))


def _bars_by_date(rows: list[Any]) -> dict[str, dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for bar in rows:
        payload = _bar_to_payload(bar)
        row_date = _normalize_date(payload.get("date"))
        if row_date:
            by_date[row_date] = payload
    return by_date


def _diff_pct(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    denominator = abs(right) if right != 0 else 1.0
    return abs(left - right) / denominator * 100.0


def _mark_cross_source_quality(
    rows: list[DailyBarPanelRow],
    *,
    akshare_rows: list[Any],
    tushare_rows: list[Any],
    warnings: list[str],
) -> None:
    if not akshare_rows or not tushare_rows:
        for row in rows:
            row.cross_source_status = "unavailable"
            if "cross_source_panel_unavailable" not in row.quality_flags:
                row.quality_flags.append("cross_source_panel_unavailable")
        warnings.append("cross_source_panel_unavailable")
        return

    ak_by_date = _bars_by_date(akshare_rows)
    ts_by_date = _bars_by_date(tushare_rows)
    common_dates = sorted(set(ak_by_date) & set(ts_by_date))
    if not common_dates:
        warnings.append("cross_source_panel_no_common_dates")
        for row in rows:
            row.cross_source_status = "unavailable"
            row.quality_flags.append("cross_source_panel_no_common_dates")
        return

    mismatch_dates: set[str] = set()
    for row_date in common_dates:
        ak_row = ak_by_date[row_date]
        ts_row = ts_by_date[row_date]
        for field_name in ("open", "high", "low", "close", "volume", "amount"):
            diff = _diff_pct(_to_float(ak_row.get(field_name)), _to_float(ts_row.get(field_name)))
            if diff is not None and diff > 0.01:
                mismatch_dates.add(row_date)
                break

    for row in rows:
        if row.date in common_dates and row.date not in mismatch_dates:
            row.cross_source_status = "matched"
        elif row.date in mismatch_dates:
            row.cross_source_status = "mismatch"
            row.quality_flags.append("cross_source_panel_mismatch")
        else:
            row.cross_source_status = "unavailable"
            row.quality_flags.append("cross_source_panel_unchecked_date")
    if mismatch_dates:
        warnings.append("cross_source_panel_mismatch")


def fetch_provider_daily_bars_for_evidence(evidence: Any) -> tuple[list[DailyBarPanelRow], list[str]]:
    """Fetch a small CN daily_bar sample through existing providers.

    This function imports providers lazily and tolerates missing optional
    dependencies or credentials. It returns rows plus warning strings; callers
    decide whether partial output is acceptable.
    """

    warnings: list[str] = []
    ticker = str(_field(evidence, "ticker", ""))
    akshare_bars: list[Any] = []
    tushare_bars: list[Any] = []
    try:
        from orchestrator.data.providers.akshare_provider import (
            AkShareProviderError,
            fetch_cn_daily_bar_sample as fetch_akshare_daily,
        )

        try:
            akshare_bars = fetch_akshare_daily(ticker, adjust="none")
        except AkShareProviderError as exc:
            warnings.append(f"akshare_provider_error:{str(exc)[:240]}")
    except ImportError as exc:  # pragma: no cover - local module should import
        warnings.append(f"akshare_import_error:{exc}")

    try:
        from orchestrator.data.providers.tushare_provider import (
            TushareProviderError,
            fetch_cn_daily_bar_sample as fetch_tushare_daily,
            get_tushare_token,
        )

        if get_tushare_token() is None:
            warnings.append("tushare_needs_credentials")
        else:
            try:
                tushare_bars = fetch_tushare_daily(ticker)
            except TushareProviderError as exc:
                warnings.append(f"tushare_provider_error:{str(exc)[:240]}")
    except ImportError as exc:  # pragma: no cover - local module should import
        warnings.append(f"tushare_import_error:{exc}")

    source_bars = akshare_bars or tushare_bars
    source_name = "akshare" if akshare_bars else "tushare"
    rows = [
        row
        for bar in source_bars
        if (row := _row_from_bar(bar, evidence, provider=source_name)) is not None
    ]
    _mark_cross_source_quality(rows, akshare_rows=akshare_bars, tushare_rows=tushare_bars, warnings=warnings)
    return rows, warnings


def _build_result(
    *,
    status: str,
    market: str,
    eligible: list[Any],
    rows: list[DailyBarPanelRow],
    missing_tickers: list[str],
    warnings: list[str],
    output_path: str,
    next_action: str,
) -> DailyBarPanelBuildResult:
    dates = sorted({row.date for row in rows})
    return DailyBarPanelBuildResult(
        status=status,
        market=market,
        tickers=sorted({str(_field(row, "ticker", "")) for row in eligible} or {row.ticker for row in rows}),
        start_date=dates[0] if dates else None,
        end_date=dates[-1] if dates else None,
        row_count=len(rows),
        missing_tickers=sorted(set(missing_tickers)),
        warnings=sorted(set(warnings)),
        output_path=output_path,
        next_action=next_action,
    )


def build_daily_bar_panel_from_provider_evidence(
    evidence_rows: Iterable[Any],
    *,
    output_path: str | Path = "outputs/panels/cn_daily_bar_panel.csv",
    fetch_missing_time_series: bool = False,
) -> tuple[DailyBarPanelBuildResult, list[DailyBarPanelRow]]:
    eligible = [row for row in evidence_rows if _is_eligible_evidence(row)]
    if not eligible:
        return (
            _build_result(
                status="blocked",
                market="CN",
                eligible=[],
                rows=[],
                missing_tickers=[],
                warnings=["no_eligible_daily_bar_evidence"],
                output_path=str(output_path),
                next_action="create allowed CN daily_bar ProviderEvidence before building panel.",
            ),
            [],
        )

    rows: list[DailyBarPanelRow] = []
    warnings: list[str] = []
    missing_tickers: list[str] = []
    for evidence in eligible:
        ticker = str(_field(evidence, "ticker", ""))
        evidence_rows_from_payload = _rows_from_evidence_payload(evidence)
        if not evidence_rows_from_payload and fetch_missing_time_series:
            evidence_rows_from_payload, provider_warnings = fetch_provider_daily_bars_for_evidence(evidence)
            warnings.extend(provider_warnings)
        if not evidence_rows_from_payload:
            missing_tickers.append(ticker)
            warnings.append("blocked_by_missing_time_series")
            continue
        rows.extend(evidence_rows_from_payload)

    rows = sorted(rows, key=lambda item: (item.ticker, item.date, item.provider))
    if rows and missing_tickers:
        status = "partial"
        next_action = "resolve missing ticker time series before treating panel as complete."
    elif rows and any(warning.startswith("tushare_") or warning.startswith("cross_source_") for warning in warnings):
        status = "partial"
        next_action = "use panel for format/runtime validation only; complete row-level cross-source checks before strategy use."
    elif rows:
        status = "success"
        next_action = "use panel for Qlib/vectorbt runtime validation only; do not train or generate signals yet."
    else:
        status = "blocked"
        next_action = "fetch real daily_bar time series from AkShare/Tushare; do not synthesize panel from summary evidence."

    return (
        _build_result(
            status=status,
            market="CN",
            eligible=eligible,
            rows=rows,
            missing_tickers=missing_tickers,
            warnings=warnings,
            output_path=str(output_path),
            next_action=next_action,
        ),
        rows,
    )


def validate_daily_bar_panel(rows: Iterable[DailyBarPanelRow]) -> list[DailyBarPanelRow]:
    validated: list[DailyBarPanelRow] = []
    for row in rows:
        payload = row.to_dict()
        for field_name in REQUIRED_PANEL_FIELDS:
            if payload.get(field_name) in (None, ""):
                raise ValueError(f"daily_bar panel row missing required field: {field_name}")
        if row.market != "CN":
            raise ValueError("daily_bar panel currently only accepts CN market rows.")
        if not row.provider_evidence_id:
            raise ValueError("daily_bar panel row missing provider_evidence_id.")
        validated.append(row)
    return validated


def write_daily_bar_panel_csv(rows: Iterable[DailyBarPanelRow], path: str | Path) -> None:
    panel_path = Path(path)
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    validated = validate_daily_bar_panel(rows)
    with panel_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PANEL_FIELDNAMES)
        writer.writeheader()
        for row in validated:
            payload = row.to_dict()
            payload["quality_flags"] = ";".join(row.quality_flags)
            writer.writerow(payload)


def load_daily_bar_panel_csv(path: str | Path) -> list[DailyBarPanelRow]:
    panel_path = Path(path)
    if not panel_path.exists():
        return []
    rows: list[DailyBarPanelRow] = []
    with panel_path.open(encoding="utf-8", newline="") as handle:
        for payload in csv.DictReader(handle):
            quality_flags = payload.get("quality_flags", "")
            row_payload: dict[str, Any] = dict(payload)
            row_payload["open"] = _to_float(payload.get("open"))
            row_payload["high"] = _to_float(payload.get("high"))
            row_payload["low"] = _to_float(payload.get("low"))
            row_payload["close"] = _to_float(payload.get("close"))
            row_payload["volume"] = _to_float(payload.get("volume"))
            row_payload["amount"] = _to_float(payload.get("amount"))
            row_payload["quality_flags"] = [item for item in quality_flags.split(";") if item]
            rows.append(DailyBarPanelRow(**row_payload))
    return rows


def summarize_daily_bar_panel(rows_or_path: Iterable[DailyBarPanelRow] | str | Path) -> dict[str, Any]:
    rows = load_daily_bar_panel_csv(rows_or_path) if isinstance(rows_or_path, (str, Path)) else list(rows_or_path)
    dates = sorted({row.date for row in rows})
    return {
        "row_count": len(rows),
        "ticker_count": len({row.ticker for row in rows}),
        "tickers": sorted({row.ticker for row in rows}),
        "start_date": dates[0] if dates else None,
        "end_date": dates[-1] if dates else None,
        "providers": sorted({row.provider for row in rows}),
        "cross_source_status": sorted({row.cross_source_status for row in rows}),
    }


def build_empty_report_result(output_path: str | Path) -> DailyBarPanelBuildResult:
    now = datetime.now(UTC).isoformat()
    return DailyBarPanelBuildResult(
        status="blocked",
        market="CN",
        tickers=[],
        start_date=None,
        end_date=None,
        row_count=0,
        missing_tickers=[],
        warnings=[f"not_built:{now}"],
        output_path=str(output_path),
        next_action="run scripts/build_verified_daily_bar_panel.py after provider evidence exists.",
    )
