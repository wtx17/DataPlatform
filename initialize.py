"""Initialize a DataClient with the project-supported remote datasets."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__:
    from . import (
        ClickHouseConfig,
        ClickHouseDatasetSpec,
        DataClient,
        TushareConfig,
        TushareDatasetSpec,
    )
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from quant_data import (
        ClickHouseConfig,
        ClickHouseDatasetSpec,
        DataClient,
        TushareConfig,
        TushareDatasetSpec,
    )

DEFAULT_CLICKHOUSE_CONNECTION = "minghu"
DEFAULT_TUSHARE_CONNECTION = "tushare"


@dataclass(frozen=True, slots=True)
class _ClickHouseRegistration:
    name: str
    table: str
    time_column: str
    partition_column: str | None = None
    order_columns: tuple[str, ...] = ()
    frequency: str | None = None
    panel_compatible: bool = True


_CLICKHOUSE_PANEL_SPECS = (
    _ClickHouseRegistration(
        name="minghu_daily",
        table="stock_base.daily",
        time_column="date",
        frequency="1d",
    ),
    _ClickHouseRegistration(
        name="minghu_m1",
        table="stock_base.m1",
        time_column="date_time",
        partition_column="date",
        order_columns=("date_time", "code"),
        frequency="1min",
    ),
)

_CLICKHOUSE_LONG_SPECS = (
    _ClickHouseRegistration(
        name="minghu_zb",
        table="stock_base.zb",
        time_column="date_time",
        partition_column="date",
        order_columns=("date_time", "code", "seqno"),
        panel_compatible=False,
    ),
)

_TUSHARE_QUARTERLY_APIS = (
    "income",
    "income_vip",
    "balancesheet",
    "balancesheet_vip",
    "cashflow",
    "cashflow_vip",
    "fina_indicator",
    "fina_indicator_vip",
    "express",
    "express_vip",
    "forecast",
    "forecast_vip",
)

_TUSHARE_DAILY_PANEL_APIS = (
    "stk_holdernumber",
    "ci_index_member",
    "index_member_all",
)

_TUSHARE_LONG_APIS = ("stk_holdertrade",)

_TUSHARE_PIT_APIS = (
    "income",
    "income_vip",
    "balancesheet",
    "balancesheet_vip",
    "cashflow",
    "cashflow_vip",
    "fina_indicator",
    "fina_indicator_vip",
    "express",
    "express_vip",
    "forecast",
    "forecast_vip",
    "stk_holdernumber",
)


def clickhouse_dataset_specs(
    connection: str = DEFAULT_CLICKHOUSE_CONNECTION,
) -> tuple[ClickHouseDatasetSpec, ...]:
    """Return the project-standard ClickHouse dataset registrations."""
    specs: list[ClickHouseDatasetSpec] = []
    for item in (*_CLICKHOUSE_PANEL_SPECS, *_CLICKHOUSE_LONG_SPECS):
        specs.append(
            ClickHouseDatasetSpec(
                name=item.name,
                connection=connection,
                table=item.table,
                time_column=item.time_column,
                partition_column=item.partition_column,
                order_columns=item.order_columns,
                frequency=item.frequency,
                panel_compatible=item.panel_compatible,
            )
        )
    return tuple(specs)


def tushare_dataset_specs(
    connection: str = DEFAULT_TUSHARE_CONNECTION,
    *,
    include_pit: bool = True,
) -> tuple[TushareDatasetSpec, ...]:
    """Return all Tushare dataset registrations supported by this package."""
    specs: list[TushareDatasetSpec] = []
    for api_name in _TUSHARE_QUARTERLY_APIS:
        specs.append(
            TushareDatasetSpec(
                name=api_name,
                connection=connection,
                api_name=api_name,
                frequency="q",
            )
        )
    for api_name in _TUSHARE_DAILY_PANEL_APIS:
        specs.append(
            TushareDatasetSpec(
                name=api_name,
                connection=connection,
                api_name=api_name,
                frequency="d",
            )
        )
    for api_name in _TUSHARE_LONG_APIS:
        specs.append(
            TushareDatasetSpec(
                name=api_name,
                connection=connection,
                api_name=api_name,
            )
        )
    if include_pit:
        for api_name in _TUSHARE_PIT_APIS:
            specs.append(
                TushareDatasetSpec(
                    name=f"{api_name}_pit",
                    connection=connection,
                    api_name=api_name,
                    panel_mode="pit_daily",
                    frequency="d",
                    disclosure_lag=1,
                )
            )
    return tuple(specs)


def registered_dataset_names(*, include_tushare_pit: bool = True) -> tuple[str, ...]:
    """Return dataset names registered by initialize_data_client."""
    names = [spec.name for spec in clickhouse_dataset_specs()]
    names.extend(
        spec.name for spec in tushare_dataset_specs(include_pit=include_tushare_pit)
    )
    return tuple(names)


def initialize_data_client(
    *,
    audit_dir: str | Path | None = None,
    register_clickhouse: bool = True,
    register_tushare: bool = True,
    register_tushare_pit: bool = True,
    clickhouse_connection: str = DEFAULT_CLICKHOUSE_CONNECTION,
    clickhouse_host: str | None = None,
    clickhouse_port: int | None = None,
    clickhouse_username: str | None = None,
    clickhouse_password: str | None = None,
    clickhouse_password_env: str | None = None,
    clickhouse_secure: bool | None = None,
    tushare_connection: str = DEFAULT_TUSHARE_CONNECTION,
    tushare_token: str | None = None,
    tushare_token_env: str | None = None,
) -> DataClient:
    """Create a DataClient, connect remote backends, and register supported datasets."""
    client = DataClient(
        audit_dir=audit_dir
        if audit_dir is not None
        else _first_env("QUANT_DATA_AUDIT_DIR") or ".quant_data/audit"
    )
    if register_clickhouse:
        client.add_clickhouse_connection(
            clickhouse_connection,
            ClickHouseConfig(
                host=clickhouse_host
                or _first_env("QUANT_DATA_CLICKHOUSE_HOST", "MINGHU_CLICKHOUSE_HOST")
                or "chdb.tradegdb.com",
                port=clickhouse_port
                if clickhouse_port is not None
                else _env_int(("QUANT_DATA_CLICKHOUSE_PORT", "MINGHU_CLICKHOUSE_PORT"), 8123),
                username=clickhouse_username
                or _first_env(
                    "QUANT_DATA_CLICKHOUSE_USERNAME",
                    "MINGHU_CLICKHOUSE_USERNAME",
                ),
                password=clickhouse_password or _first_env("QUANT_DATA_CLICKHOUSE_PASSWORD"),
                password_env=clickhouse_password_env
                or _first_env("QUANT_DATA_CLICKHOUSE_PASSWORD_ENV")
                or "MINGHU_CLICKHOUSE_PASSWORD",
                secure=clickhouse_secure
                if clickhouse_secure is not None
                else _env_bool(("QUANT_DATA_CLICKHOUSE_SECURE", "MINGHU_CLICKHOUSE_SECURE"), False),
            ),
        )
        for clickhouse_spec in clickhouse_dataset_specs(clickhouse_connection):
            client.register(clickhouse_spec)

    if register_tushare:
        client.add_tushare_connection(
            tushare_connection,
            TushareConfig(
                token=tushare_token or _first_env("QUANT_DATA_TUSHARE_TOKEN"),
                token_env=tushare_token_env
                or _first_env("QUANT_DATA_TUSHARE_TOKEN_ENV")
                or "TUSHARE_TOKEN",
            ),
        )
        for tushare_spec in tushare_dataset_specs(
            tushare_connection,
            include_pit=register_tushare_pit,
        ):
            client.register(tushare_spec)

    return client


def initialize(**kwargs: Any) -> DataClient:
    """Compatibility alias for initialize_data_client."""
    return initialize_data_client(**kwargs)


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _env_int(names: tuple[str, ...], default: int) -> int:
    value = _first_env(*names)
    return int(value) if value is not None else default


def _env_bool(names: tuple[str, ...], default: bool) -> bool:
    value = _first_env(*names)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> None:
    client = initialize_data_client()
    try:
        names = registered_dataset_names()
        print(f"Registered {len(names)} datasets:")
        for name in names:
            print(f"- {name}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
