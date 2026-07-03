from pathlib import Path

import pytest

from orchestrator.data.sample_universe import load_sample_universe


SAMPLE_PATH = Path("orchestrator/sample_data/universe_sample.csv")


def test_sample_universe_loads_nine_tickers() -> None:
    rows = load_sample_universe(SAMPLE_PATH)

    assert len(rows) == 9
    assert rows[0] == {
        "market": "CN",
        "ticker": "600519.SH",
        "name": "Kweichow Moutai",
    }
    assert rows[-1]["ticker"] == "MSFT"


def test_sample_universe_rejects_invalid_market(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid_universe.csv"
    invalid.write_text("market,ticker,name\nEU,SAP,SAP\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid market"):
        load_sample_universe(invalid)


def test_sample_universe_requires_core_columns(tmp_path: Path) -> None:
    invalid = tmp_path / "missing_columns.csv"
    invalid.write_text("market,ticker\nUS,AAPL\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        load_sample_universe(invalid)
