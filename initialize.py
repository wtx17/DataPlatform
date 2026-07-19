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
        name="minghu_index_daily",
        table="index_base.daily",
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
        name="minghu_tk",
        table="stock_base.tk",
        time_column="date_time",
        partition_column="date",
        order_columns=("date_time", "code", "time_int"),
        panel_compatible=False,
    ),
    _ClickHouseRegistration(
        name="minghu_zb",
        table="stock_base.zb",
        time_column="date_time",
        partition_column="date",
        order_columns=("date_time", "code", "seqno"),
        panel_compatible=False,
    ),
)

_TUSHARE_DATASETS = (
    "income",
    "balancesheet",
    "cashflow",
    "fina_indicator",
    "express",
    "forecast",
    "stk_holdernumber",
    "ci_index_member",
    "index_member_all",
    "stk_holdertrade",
)


def clickhouse_dataset_specs(
    connection: str = DEFAULT_CLICKHOUSE_CONNECTION,
) -> tuple[ClickHouseDatasetSpec, ...]:
    """Return the project-standard ClickHouse dataset specifications.

    Parameters
    ----------
    connection
        Connection profile referenced by every returned specification.

    Returns
    -------
    tuple[ClickHouseDatasetSpec, ...]
        Specifications for the built-in Minghu daily, index daily, minute,
        snapshot, and transaction tables.

    Notes
    -----
    This function only creates immutable specifications. It does not create a
    ClickHouse client, read credentials, or access a remote table.
    """
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
) -> tuple[TushareDatasetSpec, ...]:
    """Return the project-standard Tushare dataset specifications.

    Parameters
    ----------
    connection
        Connection profile referenced by every returned specification.
    Returns
    -------
    tuple[TushareDatasetSpec, ...]
        One immutable specification per supported logical Tushare dataset.

    Notes
    -----
    This function does not initialize a Tushare client or read a token. The
    backend chooses ordinary or VIP transport routes from each query's universe;
    disclosed datasets acquire PIT semantics automatically in ``get_panel``.
    """
    return tuple(
        TushareDatasetSpec(name=name, connection=connection)
        for name in _TUSHARE_DATASETS
    )


def registered_dataset_names() -> tuple[str, ...]:
    """Return dataset names registered by
    :func:`quant_data.initialize.initialize_data_client`.

    Parameters
    ----------
    Returns
    -------
    tuple[str, ...]
        ClickHouse names followed by Tushare names in registration order.

    Notes
    -----
    The result is derived from local specifications and requires no credentials
    or remote service access.
    """
    names = [spec.name for spec in clickhouse_dataset_specs()]
    names.extend(spec.name for spec in tushare_dataset_specs())
    return tuple(names)


def initialize_data_client(
    *,
    audit_dir: str | Path | None = None,
    register_clickhouse: bool = True,
    register_tushare: bool = True,
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
    """Create a client and register the project-supported remote datasets.

    Parameters
    ----------
    audit_dir
        Audit output directory. When omitted,
        ``QUANT_DATA_AUDIT_DIR`` or ``.quant_data/audit`` is used.
    register_clickhouse
        Configure ClickHouse and register the built-in Minghu datasets.
    register_tushare
        Configure Tushare and register its catalog-backed datasets.
    clickhouse_connection
        ClickHouse profile name referenced by generated specifications.
    clickhouse_host
        Server hostname. Environment variables and the project default are
        consulted when omitted.
    clickhouse_port
        Server port. Environment variables and port 8123 are used when omitted.
    clickhouse_username
        Optional login name, with project environment-variable fallbacks.
    clickhouse_password
        Optional direct password value.
    clickhouse_password_env
        Environment variable from which the password is read on first access.
    clickhouse_secure
        Whether to enable TLS. Environment variables are used when omitted.
    tushare_connection
        Tushare profile name referenced by generated specifications.
    tushare_token
        Optional direct Tushare token.
    tushare_token_env
        Environment variable from which the token is read.

    Returns
    -------
    DataClient
        Configured client with the requested default datasets registered.

    Raises
    ------
    DatasetRegistrationError
        If a connection or generated dataset specification is invalid.

    Notes
    -----
    Built-in registrations use local catalogs. Neither ClickHouse nor Tushare
    opens a remote connection or resolves credentials until a query needs it.
    Importing this module and calling the specification helpers are side-effect
    free.
    """
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
        for tushare_spec in tushare_dataset_specs(tushare_connection):
            client.register(tushare_spec)

    return client


def initialize(**kwargs: Any) -> DataClient:
    """Call :func:`quant_data.initialize.initialize_data_client` with
    the same keyword arguments.

    Parameters
    ----------
    **kwargs
        Keyword arguments accepted by
        :func:`quant_data.initialize.initialize_data_client`.

    Returns
    -------
    DataClient
        Configured data client.
    """
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
    """Initialize the default client and print registered dataset names."""

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
