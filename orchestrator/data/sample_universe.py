"""Sample universe loader for provider probe dry runs."""

from __future__ import annotations

import csv
from pathlib import Path

from orchestrator.data.contracts import Market


REQUIRED_COLUMNS = {"market", "ticker", "name"}


def load_sample_universe(path: str | Path) -> list[dict[str, str]]:
    sample_path = Path(path)
    if not sample_path.exists():
        raise ValueError(f"Sample universe file does not exist: {sample_path}")

    with sample_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            missing_cols = ", ".join(sorted(missing))
            raise ValueError(f"Sample universe is missing required columns: {missing_cols}")

        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            market = (row.get("market") or "").strip()
            ticker = (row.get("ticker") or "").strip()
            name = (row.get("name") or "").strip()

            if market not in Market._value2member_map_:
                allowed = ", ".join(market.value for market in Market)
                raise ValueError(
                    f"Invalid market '{market}' at line {line_number}; expected one of: {allowed}"
                )
            if not ticker:
                raise ValueError(f"Missing ticker at line {line_number}")
            if not name:
                raise ValueError(f"Missing name at line {line_number}")

            normalized = dict(row)
            normalized["market"] = market
            normalized["ticker"] = ticker
            normalized["name"] = name
            rows.append(normalized)

    return rows
