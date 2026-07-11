from __future__ import annotations

from quant_data.initialize import clickhouse_dataset_specs, registered_dataset_names


def test_clickhouse_dataset_specs_include_index_daily_and_tk() -> None:
    specs = clickhouse_dataset_specs("research")
    assert [spec.name for spec in specs] == [
        "minghu_daily",
        "minghu_index_daily",
        "minghu_m1",
        "minghu_tk",
        "minghu_zb",
    ]

    by_name = {spec.name: spec for spec in specs}
    index_daily = by_name["minghu_index_daily"]
    assert index_daily.connection == "research"
    assert index_daily.table == "index_base.daily"
    assert index_daily.time_column == "date"
    assert index_daily.frequency == "1d"
    assert index_daily.partition_column is None
    assert index_daily.panel_compatible is True

    tk = by_name["minghu_tk"]
    assert tk.connection == "research"
    assert tk.table == "stock_base.tk"
    assert tk.time_column == "date_time"
    assert tk.partition_column == "date"
    assert tk.order_columns == ("date_time", "code", "time_int")
    assert tk.panel_compatible is False


def test_registered_dataset_names_include_new_minghu_tables() -> None:
    names = registered_dataset_names()
    assert "minghu_index_daily" in names
    assert "minghu_tk" in names
