"""Data models shared by the client and backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

import pyarrow as pa


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    name: str
    paths: Sequence[str | Path]
    time_column: str = "time"
    instrument_column: str = "ts_code"
    frequency: str | None = None
    timezone: str | None = None
    version: str | None = None
    backend: str = "parquet"


@dataclass(frozen=True, slots=True)
class ClickHouseConfig:
    host: str
    port: int = 8123
    username: str | None = None
    password: str | None = field(default=None, repr=False)
    password_env: str | None = None
    secure: bool = False
    connect_timeout: int = 10
    query_timeout: int = 300


@dataclass(frozen=True, slots=True)
class ClickHouseDatasetSpec:
    name: str
    connection: str
    table: str
    time_column: str
    instrument_column: str = "code"
    partition_column: str | None = None
    order_columns: tuple[str, ...] = ()
    frequency: str | None = None
    timezone: str | None = "Asia/Shanghai"
    version: str | None = None
    panel_compatible: bool = True
    require_time_range: bool | None = None
    backend: str = field(default="clickhouse", init=False)


@dataclass(frozen=True, slots=True)
class TushareConfig:
    token: str | None = field(default=None, repr=False)
    token_env: str | None = "TUSHARE_TOKEN"


@dataclass(frozen=True, slots=True)
class TushareDatasetSpec:
    name: str
    connection: str
    api_name: str = "income"
    time_column: str = "end_date"
    instrument_column: str = "ts_code"
    fixed_params: Mapping[str, object] = field(default_factory=dict)
    order_columns: tuple[str, ...] = ()
    frequency: str | None = None
    timezone: str | None = "Asia/Shanghai"
    version: str | None = None
    panel_compatible: bool = True
    require_time_range: bool | None = False
    panel_mode: Literal["period", "pit_daily"] = "period"
    point_in_time: bool = False
    disclosure_lag: int = 0
    calendar_exchange: str = "SSE"
    fetch_buffer_days: int = 365
    fetch_margin_days: int = 31
    backend: str = field(default="tushare", init=False)


DatasetDefinition = DatasetSpec | ClickHouseDatasetSpec | TushareDatasetSpec


@dataclass(frozen=True, slots=True)
class RegisteredDataset:
    spec: DatasetDefinition
    schema: pa.Schema
    source: Any
    adjustment: PriceAdjustment | None = None


@dataclass(frozen=True, slots=True)
class PriceAdjustment:
    factor_column: str
    fields: tuple[str, ...]
    default: bool = True


@dataclass(frozen=True, slots=True)
class DataQuery:
    fields: tuple[str, ...]
    start: datetime | None = None
    end: datetime | None = None
    instruments: tuple[str, ...] | None = None
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    path: str
    size: int
    mtime_ns: int


@dataclass(slots=True)
class QueryAudit:
    query_id: str
    dataset: str
    fields: list[str]
    parameters: dict[str, Any]
    started_at: str
    framework_version: str
    operation: str = "panel"
    source: dict[str, Any] = field(default_factory=dict)
    frequency: str | None = None
    dataset_version: str | None = None
    adjusted: bool = False
    calendar_aligned: bool = False
    status: str = "running"
    duration_ms: float | None = None
    result_shapes: dict[str, list[int]] = field(default_factory=dict)
    error: dict[str, str] | None = None
