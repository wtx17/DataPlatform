"""Point-in-time daily panel tests for the Tushare backend.

Uses an injected fake Tushare client (mirrors the ClickHouse FakeFactory pattern)
so no network or tushare install is required. Verifies daily trading-calendar
alignment, forward-fill, T+1 availability, weekend snapping, carry-in, the
balancesheet path (no f_ann_date input), same-day multi-period aggregation, and
the period-range guard. Also covers fina_indicator, whose disclosure date is
ann_date rather than f_ann_date, plus express and forecast registrations.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from quant_data import (
    DataClient,
    InvalidQueryError,
    TushareConfig,
    TushareDatasetSpec,
)


def weekdays(start: date, end: date) -> list[date]:
    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # Mon-Fri
            days.append(current)
        current += timedelta(days=1)
    return days


# Fixed trading calendar covering the fetch window. Excludes weekends (and would
# naturally exclude holidays if they were dropped); days the test cares about:
# 2024-04-25 (Thu), 2024-04-26 (Fri), 2024-04-27/28 (weekend),
# 2024-04-29 (Mon), 2024-04-30 (Tue), 2024-05-02 (Thu), ...
CALENDAR = weekdays(date(2024, 3, 1), date(2024, 5, 31))


class FakeTushareClient:
    def __init__(self, data: dict[str, pd.DataFrame], calendar: list[date]) -> None:
        self.data = data
        self.calendar = calendar
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def query(self, api_name: str, **params: Any) -> pd.DataFrame:
        self.calls.append((api_name, dict(params)))
        if api_name == "trade_cal":
            start = datetime_strptime(params["start_date"])
            end = datetime_strptime(params["end_date"])
            days = [d for d in self.calendar if start <= d <= end]
            return pd.DataFrame(
                {"cal_date": [d.strftime("%Y%m%d") for d in days], "is_open": ["1"] * len(days)}
            )
        frame = self.data[api_name]
        fields = params.get("fields")
        if fields:
            cols = [c for c in fields.split(",") if c in frame.columns]
            frame = frame.loc[:, cols]
        ts_code = params.get("ts_code")
        if ts_code is not None and "ts_code" in frame.columns:
            frame = frame[frame["ts_code"] == ts_code]
        period = params.get("period")
        if period is not None and "end_date" in frame.columns:
            frame = frame[frame["end_date"].astype(str) == str(period)]
        if "ann_date" in frame.columns:
            start = params.get("start_date")
            end = params.get("end_date")
            if start is not None:
                frame = frame[frame["ann_date"].astype(str) >= str(start)]
            if end is not None:
                frame = frame[frame["ann_date"].astype(str) <= str(end)]
        return frame.reset_index(drop=True)


def datetime_strptime(value: str) -> date:
    return datetime.strptime(str(value), "%Y%m%d").date()


class FakeFactory:
    def __init__(self, client: FakeTushareClient) -> None:
        self.client = client

    def __call__(self, **kwargs: Any) -> FakeTushareClient:
        return self.client


def income_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=["ts_code", "ann_date", "f_ann_date", "end_date", "update_flag"]
        )
    base = pd.DataFrame(rows)
    for col in ("ann_date", "f_ann_date", "end_date"):
        base[col] = base[col].astype(str)
    return base


def fina_indicator_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["ts_code", "ann_date", "end_date", "update_flag"])
    base = pd.DataFrame(rows)
    for col in ("ann_date", "end_date"):
        base[col] = base[col].astype(str)
    return base


def express_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["ts_code", "ann_date", "end_date", "is_audit"])
    base = pd.DataFrame(rows)
    for col in ("ann_date", "end_date"):
        base[col] = base[col].astype(str)
    return base


def forecast_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["ts_code", "ann_date", "end_date", "first_ann_date"])
    base = pd.DataFrame(rows)
    for col in ("ann_date", "end_date", "first_ann_date"):
        if col in base.columns:
            base[col] = base[col].astype(str)
    return base


def make_client(
    tmp_path: Path, data: dict[str, pd.DataFrame]
) -> tuple[DataClient, FakeTushareClient]:
    fake = FakeTushareClient(data, CALENDAR)
    client = DataClient(tmp_path / "audit", tushare_client_factory=FakeFactory(fake))
    client.add_tushare_connection("ts", TushareConfig(token="x"))
    return client, fake


def register_pit(
    client: DataClient,
    *,
    name: str = "income_pit",
    api_name: str = "income",
    **spec_kwargs: Any,
) -> TushareDatasetSpec:
    time_column = spec_kwargs.pop("time_column", "f_ann_date")
    disclosure_lag = spec_kwargs.pop("disclosure_lag", 1)
    spec = TushareDatasetSpec(
        name=name,
        connection="ts",
        api_name=api_name,
        time_column=time_column,
        point_in_time=True,
        disclosure_lag=disclosure_lag,
        fetch_buffer_days=60,
        fetch_margin_days=15,
        **spec_kwargs,
    )
    client.register(spec)
    return spec


def test_daily_index_and_forward_fill(tmp_path: Path) -> None:
    data = {
        "income": income_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240426",
                    "f_ann_date": "20240426",
                    "end_date": "20240331",
                    "update_flag": 0,
                    "total_revenue": 1.0e10,
                }
            ]
        )
    }
    client, _ = make_client(tmp_path, data)
    register_pit(client)
    panels = client.get_panel(
        "income_pit",
        fields=["total_revenue"],
        start="2024-04-25",
        end="2024-05-10",
        instruments=["600000.SH"],
    )
    panel = panels["total_revenue"]
    # Index is the trading days within [start, end].
    expected_index = [d for d in CALENDAR if date(2024, 4, 25) <= d <= date(2024, 5, 10)]
    assert list(panel.index) == [pd.Timestamp(d) for d in expected_index]
    # Disclosed Fri 2024-04-26 -> available from Mon 2024-04-29 (T+1); persists to end.
    assert pd.isna(panel.loc[pd.Timestamp("2024-04-25"), "600000.SH"])
    assert pd.isna(panel.loc[pd.Timestamp("2024-04-26"), "600000.SH"])
    value = panel.loc[pd.Timestamp("2024-04-29"), "600000.SH"]
    assert value == pytest.approx(1.0e10)
    assert panel.iloc[-1]["600000.SH"] == pytest.approx(1.0e10)


def test_no_look_ahead_t_plus_one(tmp_path: Path) -> None:
    data = {
        "income": income_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240426",
                    "f_ann_date": "20240426",
                    "end_date": "20240331",
                    "update_flag": 0,
                    "total_revenue": 7.0,
                }
            ]
        )
    }
    client, _ = make_client(tmp_path, data)
    register_pit(client, disclosure_lag=1)
    panel = client.get_panel(
        "income_pit",
        fields=["total_revenue"],
        start="2024-04-25",
        end="2024-04-30",
        instruments=["600000.SH"],
    )["total_revenue"]
    # On the disclosure day itself the value is NOT yet available.
    assert pd.isna(panel.loc[pd.Timestamp("2024-04-26"), "600000.SH"])
    # First available the next trading day (Mon 2024-04-29).
    assert panel.loc[pd.Timestamp("2024-04-29"), "600000.SH"] == pytest.approx(7.0)


def test_non_trading_day_disclosure_snaps_forward(tmp_path: Path) -> None:
    # Disclosed on Saturday 2024-04-27 -> snaps to Mon 2024-04-29, +lag -> Tue 2024-04-30.
    data = {
        "income": income_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240427",
                    "f_ann_date": "20240427",
                    "end_date": "20240331",
                    "update_flag": 0,
                    "total_revenue": 9.0,
                }
            ]
        )
    }
    client, _ = make_client(tmp_path, data)
    register_pit(client)
    panel = client.get_panel(
        "income_pit",
        fields=["total_revenue"],
        start="2024-04-25",
        end="2024-05-03",
        instruments=["600000.SH"],
    )["total_revenue"]
    assert pd.isna(panel.loc[pd.Timestamp("2024-04-29"), "600000.SH"])
    assert panel.loc[pd.Timestamp("2024-04-30"), "600000.SH"] == pytest.approx(9.0)


def test_carry_in_from_pre_start_disclosure(tmp_path: Path) -> None:
    # A disclosure before the panel start should carry into the first panel day.
    data = {
        "income": income_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240410",
                    "f_ann_date": "20240410",
                    "end_date": "20231231",
                    "update_flag": 0,
                    "total_revenue": 3.0,
                }
            ]
        )
    }
    client, _ = make_client(tmp_path, data)
    register_pit(client)
    panel = client.get_panel(
        "income_pit",
        fields=["total_revenue"],
        start="2024-04-25",
        end="2024-04-30",
        instruments=["600000.SH"],
    )["total_revenue"]
    assert panel.loc[pd.Timestamp("2024-04-25"), "600000.SH"] == pytest.approx(3.0)


def test_balancesheet_path_never_sends_f_ann_date(tmp_path: Path) -> None:
    data = {
        "balancesheet": income_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240426",
                    "f_ann_date": "20240426",
                    "end_date": "20240331",
                    "update_flag": 0,
                    "total_assets": 5.0e10,
                }
            ]
        )
    }
    client, fake = make_client(tmp_path, data)
    register_pit(client, name="bs_pit", api_name="balancesheet")
    panel = client.get_panel(
        "bs_pit",
        fields=["total_assets"],
        start="2024-04-25",
        end="2024-05-10",
        instruments=["600000.SH"],
    )["total_assets"]
    # Same PIT behaviour as income.
    assert pd.isna(panel.loc[pd.Timestamp("2024-04-26"), "600000.SH"])
    assert panel.loc[pd.Timestamp("2024-04-29"), "600000.SH"] == pytest.approx(5.0e10)
    # balancesheet has no f_ann_date input -> the backend must never send it.
    for api_name, params in fake.calls:
        if api_name == "balancesheet":
            assert "f_ann_date" not in params


def test_fina_indicator_period_query_uses_ann_date_catalog(tmp_path: Path) -> None:
    data = {
        "fina_indicator": fina_indicator_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240426",
                    "end_date": "20240331",
                    "update_flag": 0,
                    "roe": 10.5,
                    "eps": 0.42,
                },
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20231028",
                    "end_date": "20230930",
                    "update_flag": 0,
                    "roe": 9.5,
                    "eps": 0.36,
                },
            ]
        )
    }
    client, fake = make_client(tmp_path, data)
    client.register(
        TushareDatasetSpec(
            name="indicator",
            connection="ts",
            api_name="fina_indicator",
            frequency="q",
        )
    )

    table = client.get_table(
        "indicator",
        fields=["roe", "eps"],
        start="2024-03-31",
        end="2024-03-31",
        instruments=["600000.SH"],
    )

    frame = table.to_pandas()
    assert frame["roe"].tolist() == pytest.approx([10.5])
    assert frame["eps"].tolist() == pytest.approx([0.42])
    indicator_calls = [params for api_name, params in fake.calls if api_name == "fina_indicator"]
    assert len(indicator_calls) == 1
    assert indicator_calls[0]["period"] == "20240331"
    assert indicator_calls[0]["ts_code"] == "600000.SH"
    assert "f_ann_date" not in str(indicator_calls[0]["fields"]).split(",")
    assert "ann_date" in str(indicator_calls[0]["fields"]).split(",")


def test_fina_indicator_vip_period_query_supports_whole_market(tmp_path: Path) -> None:
    data = {
        "fina_indicator_vip": fina_indicator_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240426",
                    "end_date": "20240331",
                    "update_flag": 0,
                    "roe": 10.5,
                },
                {
                    "ts_code": "000004.SZ",
                    "ann_date": "20240425",
                    "end_date": "20240331",
                    "update_flag": 0,
                    "roe": 8.25,
                },
            ]
        )
    }
    client, fake = make_client(tmp_path, data)
    client.register(
        TushareDatasetSpec(
            name="indicator_vip",
            connection="ts",
            api_name="fina_indicator_vip",
            frequency="q",
        )
    )

    panel = client.get_panel(
        "indicator_vip",
        fields=["roe"],
        start="2024-03-31",
        end="2024-03-31",
        instruments=None,
    )["roe"]

    assert list(panel.columns) == ["000004.SZ", "600000.SH"]
    assert panel.loc[date(2024, 3, 31), "600000.SH"] == pytest.approx(10.5)
    assert panel.loc[date(2024, 3, 31), "000004.SZ"] == pytest.approx(8.25)
    indicator_calls = [
        params for api_name, params in fake.calls if api_name == "fina_indicator_vip"
    ]
    assert len(indicator_calls) == 1
    assert "ts_code" not in indicator_calls[0]
    assert "f_ann_date" not in str(indicator_calls[0]["fields"]).split(",")


def test_fina_indicator_pit_uses_ann_date_without_f_ann_date(tmp_path: Path) -> None:
    data = {
        "fina_indicator": fina_indicator_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240426",
                    "end_date": "20240331",
                    "update_flag": 0,
                    "roe": 10.5,
                }
            ]
        )
    }
    client, fake = make_client(tmp_path, data)
    register_pit(
        client,
        name="indicator_pit",
        api_name="fina_indicator",
        time_column="end_date",
        disclosure_lag=1,
    )

    panel = client.get_panel(
        "indicator_pit",
        fields=["roe"],
        start="2024-04-25",
        end="2024-05-03",
        instruments=["600000.SH"],
    )["roe"]

    assert pd.isna(panel.loc[pd.Timestamp("2024-04-26"), "600000.SH"])
    assert panel.loc[pd.Timestamp("2024-04-29"), "600000.SH"] == pytest.approx(10.5)
    assert panel.iloc[-1]["600000.SH"] == pytest.approx(10.5)
    indicator_calls = [params for api_name, params in fake.calls if api_name == "fina_indicator"]
    assert len(indicator_calls) == 1
    fields = str(indicator_calls[0]["fields"]).split(",")
    assert "ann_date" in fields
    assert "f_ann_date" not in fields
    assert indicator_calls[0]["start_date"] == "20240225"
    assert indicator_calls[0]["end_date"] == "20240503"


def test_express_period_query_supports_text_and_integer_fields(tmp_path: Path) -> None:
    data = {
        "express": express_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240208",
                    "end_date": "20231231",
                    "revenue": 100.0,
                    "n_income": 12.0,
                    "perf_summary": "solid",
                    "is_audit": 1,
                }
            ]
        )
    }
    client, fake = make_client(tmp_path, data)
    client.register(
        TushareDatasetSpec(
            name="express",
            connection="ts",
            api_name="express",
            frequency="q",
        )
    )

    table = client.get_table(
        "express",
        fields=["revenue", "perf_summary", "is_audit"],
        start="2023-12-31",
        end="2023-12-31",
        instruments=["600000.SH"],
    )

    frame = table.to_pandas()
    assert frame["revenue"].tolist() == pytest.approx([100.0])
    assert frame["perf_summary"].tolist() == ["solid"]
    assert frame["is_audit"].tolist() == [1]
    express_calls = [params for api_name, params in fake.calls if api_name == "express"]
    assert len(express_calls) == 1
    assert express_calls[0]["period"] == "20231231"
    assert express_calls[0]["ts_code"] == "600000.SH"
    assert "ann_date" in str(express_calls[0]["fields"]).split(",")
    assert "f_ann_date" not in str(express_calls[0]["fields"]).split(",")


def test_express_vip_period_query_supports_whole_market(tmp_path: Path) -> None:
    data = {
        "express_vip": express_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240208",
                    "end_date": "20231231",
                    "revenue": 100.0,
                },
                {
                    "ts_code": "000004.SZ",
                    "ann_date": "20240209",
                    "end_date": "20231231",
                    "revenue": 80.0,
                },
            ]
        )
    }
    client, fake = make_client(tmp_path, data)
    client.register(
        TushareDatasetSpec(
            name="express_vip",
            connection="ts",
            api_name="express_vip",
            frequency="q",
        )
    )

    panel = client.get_panel(
        "express_vip",
        fields=["revenue"],
        start="2023-12-31",
        end="2023-12-31",
        instruments=None,
    )["revenue"]

    assert list(panel.columns) == ["000004.SZ", "600000.SH"]
    assert panel.loc[date(2023, 12, 31), "600000.SH"] == pytest.approx(100.0)
    assert panel.loc[date(2023, 12, 31), "000004.SZ"] == pytest.approx(80.0)
    express_calls = [params for api_name, params in fake.calls if api_name == "express_vip"]
    assert len(express_calls) == 1
    assert "ts_code" not in express_calls[0]
    assert "f_ann_date" not in str(express_calls[0]["fields"]).split(",")


def test_forecast_period_query_supports_first_ann_date_and_text(tmp_path: Path) -> None:
    data = {
        "forecast": forecast_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240131",
                    "end_date": "20231231",
                    "type": "increase",
                    "p_change_min": 10.0,
                    "p_change_max": 20.0,
                    "first_ann_date": "20240115",
                    "summary": "range raised",
                }
            ]
        )
    }
    client, fake = make_client(tmp_path, data)
    client.register(
        TushareDatasetSpec(
            name="forecast",
            connection="ts",
            api_name="forecast",
            frequency="q",
        )
    )

    table = client.get_table(
        "forecast",
        fields=["type", "p_change_min", "first_ann_date", "summary"],
        start="2023-12-31",
        end="2023-12-31",
        instruments=["600000.SH"],
    )

    frame = table.to_pandas()
    assert frame["type"].tolist() == ["increase"]
    assert frame["p_change_min"].tolist() == pytest.approx([10.0])
    assert str(frame["first_ann_date"].iloc[0]) == "2024-01-15"
    assert frame["summary"].tolist() == ["range raised"]
    forecast_calls = [params for api_name, params in fake.calls if api_name == "forecast"]
    assert len(forecast_calls) == 1
    assert forecast_calls[0]["period"] == "20231231"
    assert forecast_calls[0]["ts_code"] == "600000.SH"
    fields = str(forecast_calls[0]["fields"]).split(",")
    assert "ann_date" in fields
    assert "first_ann_date" in fields
    assert "f_ann_date" not in fields


def test_forecast_vip_period_query_supports_whole_market(tmp_path: Path) -> None:
    data = {
        "forecast_vip": forecast_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240131",
                    "end_date": "20231231",
                    "type": "increase",
                    "p_change_min": 10.0,
                    "first_ann_date": "20240115",
                },
                {
                    "ts_code": "000004.SZ",
                    "ann_date": "20240131",
                    "end_date": "20231231",
                    "type": "loss",
                    "p_change_min": -20.0,
                    "first_ann_date": "20240118",
                },
            ]
        )
    }
    client, fake = make_client(tmp_path, data)
    client.register(
        TushareDatasetSpec(
            name="forecast_vip",
            connection="ts",
            api_name="forecast_vip",
            frequency="q",
        )
    )

    panel = client.get_panel(
        "forecast_vip",
        fields=["p_change_min"],
        start="2023-12-31",
        end="2023-12-31",
        instruments=None,
    )["p_change_min"]

    assert list(panel.columns) == ["000004.SZ", "600000.SH"]
    assert panel.loc[date(2023, 12, 31), "600000.SH"] == pytest.approx(10.0)
    assert panel.loc[date(2023, 12, 31), "000004.SZ"] == pytest.approx(-20.0)
    forecast_calls = [params for api_name, params in fake.calls if api_name == "forecast_vip"]
    assert len(forecast_calls) == 1
    assert "ts_code" not in forecast_calls[0]
    assert "f_ann_date" not in str(forecast_calls[0]["fields"]).split(",")


def test_forecast_pit_uses_ann_date_without_f_ann_date(tmp_path: Path) -> None:
    data = {
        "forecast": forecast_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240426",
                    "end_date": "20240331",
                    "type": "increase",
                    "p_change_min": 10.0,
                    "first_ann_date": "20240420",
                }
            ]
        )
    }
    client, fake = make_client(tmp_path, data)
    register_pit(
        client,
        name="forecast_pit",
        api_name="forecast",
        time_column="end_date",
        disclosure_lag=1,
    )

    panel = client.get_panel(
        "forecast_pit",
        fields=["p_change_min"],
        start="2024-04-25",
        end="2024-05-03",
        instruments=["600000.SH"],
    )["p_change_min"]

    assert pd.isna(panel.loc[pd.Timestamp("2024-04-26"), "600000.SH"])
    assert panel.loc[pd.Timestamp("2024-04-29"), "600000.SH"] == pytest.approx(10.0)
    forecast_calls = [params for api_name, params in fake.calls if api_name == "forecast"]
    assert len(forecast_calls) == 1
    fields = str(forecast_calls[0]["fields"]).split(",")
    assert "ann_date" in fields
    assert "first_ann_date" in fields
    assert "f_ann_date" not in fields
    assert forecast_calls[0]["start_date"] == "20240225"
    assert forecast_calls[0]["end_date"] == "20240503"


def test_same_day_multi_period_keeps_latest_period(tmp_path: Path) -> None:
    data = {
        "income": income_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240426",
                    "f_ann_date": "20240426",
                    "end_date": "20231231",  # prior year annual
                    "update_flag": 0,
                    "total_revenue": 1.0,
                },
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240426",
                    "f_ann_date": "20240426",
                    "end_date": "20240331",  # Q1, later period
                    "update_flag": 0,
                    "total_revenue": 2.0,
                },
            ]
        )
    }
    client, _ = make_client(tmp_path, data)
    register_pit(client)
    panel = client.get_panel(
        "income_pit",
        fields=["total_revenue"],
        start="2024-04-25",
        end="2024-05-03",
        instruments=["600000.SH"],
    )["total_revenue"]
    # Both disclosed the same day; the latest report period (Q1) wins.
    assert panel.loc[pd.Timestamp("2024-04-29"), "600000.SH"] == pytest.approx(2.0)


def test_vip_point_in_time_supports_whole_market(tmp_path: Path) -> None:
    data = {
        "income_vip": income_rows(
            [
                {
                    "ts_code": "600000.SH",
                    "ann_date": "20240426",
                    "f_ann_date": "20240426",
                    "end_date": "20240331",
                    "update_flag": 0,
                    "total_revenue": 5.0,
                },
                {
                    "ts_code": "000004.SZ",
                    "ann_date": "20240426",
                    "f_ann_date": "20240426",
                    "end_date": "20240331",
                    "update_flag": 0,
                    "total_revenue": 8.0,
                },
            ]
        )
    }
    client, fake = make_client(tmp_path, data)
    register_pit(client, name="vip_pit", api_name="income_vip")
    panel = client.get_panel(
        "vip_pit",
        fields=["total_revenue"],
        start="2024-04-25",
        end="2024-05-10",
        instruments=None,
    )["total_revenue"]
    assert list(panel.columns) == ["000004.SZ", "600000.SH"]
    assert panel.loc[pd.Timestamp("2024-04-29"), "600000.SH"] == pytest.approx(5.0)
    assert panel.loc[pd.Timestamp("2024-04-29"), "000004.SZ"] == pytest.approx(8.0)
    income_calls = [params for api_name, params in fake.calls if api_name == "income_vip"]
    assert len(income_calls) == 1
    assert "ts_code" not in income_calls[0]


def test_non_vip_point_in_time_requires_instruments(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path, {"income": income_rows([])})
    register_pit(client)
    with pytest.raises(InvalidQueryError, match="requires instruments"):
        client.get_panel(
            "income_pit",
            fields=["total_revenue"],
            start="2024-04-25",
            end="2024-05-10",
            instruments=None,
        )


def test_point_in_time_requires_both_start_and_end(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path, {"income": income_rows([])})
    register_pit(client)
    with pytest.raises(InvalidQueryError):
        client.get_panel(
            "income_pit",
            fields=["total_revenue"],
            start="2024-04-25",
            instruments=["600000.SH"],
        )
