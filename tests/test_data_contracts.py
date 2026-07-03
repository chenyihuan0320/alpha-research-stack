from datetime import date, datetime, timezone

from orchestrator.data.contracts import DailyBar, Market, SecurityMaster


def test_security_master_to_dict_converts_enum_and_datetime() -> None:
    item = SecurityMaster(
        market=Market.CN,
        ticker="600519.SH",
        name="Kweichow Moutai",
        exchange="SSE",
        currency="CNY",
        sector=None,
        industry=None,
        source="akshare",
        source_updated_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
        is_active=True,
    )

    data = item.to_dict()

    assert data["market"] == "CN"
    assert data["source_updated_at"] == "2026-07-03T00:00:00+00:00"
    assert data["is_active"] is True


def test_daily_bar_to_dict_supports_optional_fields_and_quality_flags() -> None:
    item = DailyBar(
        market=Market.US,
        ticker="AAPL",
        date=date(2026, 7, 2),
        open=1.0,
        high=2.0,
        low=0.5,
        close=1.5,
        adj_close=None,
        volume=1000.0,
        amount=None,
        turnover=None,
        source="openbb",
        source_updated_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
        adjustment="unknown",
        quality_flags=["unknown_adjustment"],
    )

    data = item.to_dict()

    assert data["market"] == "US"
    assert data["date"] == "2026-07-02"
    assert data["adj_close"] is None
    assert data["quality_flags"] == ["unknown_adjustment"]
