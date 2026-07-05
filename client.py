"""High-level data registration and query API."""

from __future__ import annotations

import time
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Sequence, cast
from zoneinfo import ZoneInfo

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from ._version import __version__
from .audit import AuditWriter
from .backends.base import DataBackend
from .backends.clickhouse import ClickHouseBackend
from .backends.parquet import DuckDBParquetBackend
from .backends.tushare import TushareBackend
from .exceptions import (
    DatasetNotFoundError,
    DatasetRegistrationError,
    FieldNotFoundError,
    InvalidQueryError,
    SchemaMismatchError,
)
from .models import (
    ClickHouseConfig,
    ClickHouseDatasetSpec,
    DataQuery,
    DatasetDefinition,
    DatasetSpec,
    QueryAudit,
    RegisteredDataset,
    TushareConfig,
    TushareDatasetSpec,
)
from .transforms import build_daily_panels, build_panels

QueryMode = Literal["panel", "table"]
_MINGHU_CODE_SUFFIXES = (".SZ", ".SH", ".BJ")


class DataClient:
    def __init__(
        self,
        audit_dir: str | Path = ".quant_data/audit",
        *,
        clickhouse_client_factory: Callable[..., Any] | None = None,
        tushare_client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._datasets: dict[str, RegisteredDataset] = {}
        self._clickhouse = ClickHouseBackend(clickhouse_client_factory)
        self._tushare = TushareBackend(tushare_client_factory)
        self._backends: dict[str, DataBackend] = {
            "parquet": DuckDBParquetBackend(),
            "clickhouse": self._clickhouse,
            "tushare": self._tushare,
        }
        self._audit = AuditWriter(audit_dir)

    def add_clickhouse_connection(self, name: str, config: ClickHouseConfig) -> None:
        self._clickhouse.add_connection(name, config)

    def add_tushare_connection(self, name: str, config: TushareConfig) -> None:
        self._tushare.add_connection(name, config)

    def register(self, spec: DatasetDefinition) -> None:
        self._validate_spec(spec)
        backend = self._backends.get(spec.backend)
        if backend is None:
            raise DatasetRegistrationError(f"Unsupported backend: {spec.backend!r}")
        self._datasets[spec.name] = backend.prepare(spec)

    def get_panel(
        self,
        dataset: str,
        fields: Sequence[str],
        start: Any | None = None,
        end: Any | None = None,
        instruments: Sequence[str] | None = None,
        adjusted: bool | None = None,
    ) -> dict[str, pd.DataFrame]:
        result = self._execute(
            "panel", dataset, fields, start, end, instruments, limit=None, adjusted=adjusted
        )
        return cast(dict[str, pd.DataFrame], result)

    def get_table(
        self,
        dataset: str,
        fields: Sequence[str],
        start: Any | None = None,
        end: Any | None = None,
        instruments: Sequence[str] | None = None,
        limit: int | None = None,
        adjusted: bool | None = None,
    ) -> pa.Table:
        result = self._execute(
            "table", dataset, fields, start, end, instruments, limit, adjusted
        )
        return cast(pa.Table, result)

    def close(self) -> None:
        for backend in self._backends.values():
            backend.close()

    def __enter__(self) -> DataClient:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def _execute(
        self,
        mode: QueryMode,
        dataset: str,
        fields: Sequence[str],
        start: Any | None,
        end: Any | None,
        instruments: Sequence[str] | None,
        limit: int | None,
        adjusted: bool | None,
    ) -> dict[str, pd.DataFrame] | pa.Table:
        query_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        started_clock = time.perf_counter()
        record = QueryAudit(
            query_id=query_id,
            dataset=dataset,
            fields=list(fields),
            parameters={
                "start": self._audit_value(start),
                "end": self._audit_value(end),
                "instruments": list(instruments) if instruments is not None else None,
                "limit": limit,
                "adjusted": adjusted,
            },
            started_at=started_at.isoformat(),
            framework_version=__version__,
            operation=mode,
        )

        try:
            registered = self._datasets.get(dataset)
            if registered is None:
                raise DatasetNotFoundError(f"Dataset {dataset!r} is not registered")
            spec = registered.spec
            backend = self._backends[spec.backend]
            record.frequency = spec.frequency
            record.dataset_version = spec.version
            record.source = backend.fingerprint(registered)

            if mode == "panel" and isinstance(
                spec, (ClickHouseDatasetSpec, TushareDatasetSpec)
            ):
                if not spec.panel_compatible:
                    raise InvalidQueryError(
                        f"Dataset {dataset!r} is event data and cannot be pivoted; use get_table"
                    )
            query = self._prepare_query(registered, fields, start, end, instruments, limit)
            apply_adjustment = self._resolve_adjustment(registered, adjusted)
            record.adjusted = apply_adjustment
            record.parameters["adjusted"] = apply_adjustment
            scan_query = self._with_adjustment_factor(registered, query, apply_adjustment)
            if mode == "panel" and self._uses_tushare_pit_panel(registered):
                result = self._build_tushare_pit_panels(
                    dataset,
                    registered,
                    scan_query,
                    record,
                    apply_adjustment,
                )
            else:
                if scan_query.instruments == ():
                    table = self._empty_table(registered, scan_query.fields)
                else:
                    table = backend.scan(registered, scan_query)
                self._validate_table_keys(table, registered)
                if apply_adjustment:
                    table = self._adjust_prices(table, registered)
                table = table.select(
                    [spec.time_column, spec.instrument_column, *query.fields]
                )

                if mode == "table":
                    result = self._attach_table_metadata(
                        table, query_id, dataset, record.parameters
                    )
                    record.result_shapes = {"table": [result.num_rows, result.num_columns]}
                else:
                    panel_instruments = self._panel_instruments(
                        table, registered, query.instruments
                    )
                    result = build_panels(
                        table,
                        dataset_name=dataset,
                        time_column=spec.time_column,
                        instrument_column=spec.instrument_column,
                        fields=query.fields,
                        instruments=panel_instruments,
                    )
                    attrs = {
                        "query_id": query_id,
                        "dataset": dataset,
                        "frequency": spec.frequency,
                        "version": spec.version,
                        "parameters": record.parameters,
                        "adjusted": apply_adjustment,
                    }
                    for panel in result.values():
                        panel.attrs.update(attrs)
                    record.result_shapes = {
                        field: [int(panel.shape[0]), int(panel.shape[1])]
                        for field, panel in result.items()
                    }
            record.status = "success"
        except Exception as exc:
            record.status = "failed"
            record.error = {"type": type(exc).__name__, "message": str(exc)}
            record.duration_ms = (time.perf_counter() - started_clock) * 1000
            self._audit.write(record)
            raise

        record.duration_ms = (time.perf_counter() - started_clock) * 1000
        self._audit.write(record)
        return result

    @staticmethod
    def _uses_tushare_pit_panel(dataset: RegisteredDataset) -> bool:
        spec = dataset.spec
        return isinstance(spec, TushareDatasetSpec) and (
            spec.panel_mode == "pit_daily" or spec.point_in_time
        )

    def _build_tushare_pit_panels(
        self,
        dataset_name: str,
        dataset: RegisteredDataset,
        query: DataQuery,
        record: QueryAudit,
        apply_adjustment: bool,
    ) -> dict[str, pd.DataFrame]:
        spec = dataset.spec
        if not isinstance(spec, TushareDatasetSpec):
            raise SchemaMismatchError("PIT panels require a Tushare dataset")
        if query.start is None or query.end is None:
            raise InvalidQueryError(
                f"Dataset {dataset_name!r} pit_daily panel requires both start and end"
            )
        if apply_adjustment:
            raise InvalidQueryError("pit_daily panels do not support price adjustment")

        table = self._tushare.scan_disclosure_events(dataset, query)
        self._validate_table_keys(table, dataset)
        disclosure_column, period_column = self._tushare.pit_panel_columns(dataset)
        calendar = self._tushare.trade_calendar(dataset, query)
        panels = build_daily_panels(
            table,
            dataset_name=dataset_name,
            disclosure_column=disclosure_column,
            instrument_column=spec.instrument_column,
            period_column=period_column,
            fields=query.fields,
            instruments=query.instruments,
            calendar=calendar,
            panel_start=pd.Timestamp(query.start.date()),
            panel_end=pd.Timestamp(query.end.date()),
            disclosure_lag=spec.disclosure_lag,
        )
        record.calendar_aligned = True
        record.parameters["panel_mode"] = "pit_daily"
        record.parameters["disclosure_lag"] = spec.disclosure_lag
        attrs = {
            "query_id": record.query_id,
            "dataset": dataset_name,
            "frequency": spec.frequency,
            "version": spec.version,
            "parameters": record.parameters,
            "adjusted": False,
            "panel_mode": "pit_daily",
            "disclosure_lag": spec.disclosure_lag,
        }
        for panel in panels.values():
            panel.attrs.update(attrs)
        record.result_shapes = {
            field: [int(panel.shape[0]), int(panel.shape[1])]
            for field, panel in panels.items()
        }
        return panels

    @staticmethod
    def _resolve_adjustment(dataset: RegisteredDataset, adjusted: bool | None) -> bool:
        if adjusted is not None and not isinstance(adjusted, bool):
            raise InvalidQueryError("adjusted must be True, False, or None")
        if adjusted is None:
            return dataset.adjustment.default if dataset.adjustment else False
        if adjusted and dataset.adjustment is None:
            raise InvalidQueryError(
                f"Dataset {dataset.spec.name!r} does not define a price adjustment factor"
            )
        return adjusted

    @staticmethod
    def _with_adjustment_factor(
        dataset: RegisteredDataset,
        query: DataQuery,
        apply_adjustment: bool,
    ) -> DataQuery:
        adjustment = dataset.adjustment
        if not apply_adjustment or adjustment is None:
            return query
        if not set(query.fields).intersection(adjustment.fields):
            return query
        if adjustment.factor_column in query.fields:
            return query
        return replace(query, fields=(*query.fields, adjustment.factor_column))

    @staticmethod
    def _adjust_prices(table: pa.Table, dataset: RegisteredDataset) -> pa.Table:
        adjustment = dataset.adjustment
        if adjustment is None or adjustment.factor_column not in table.column_names:
            return table
        factor = table[adjustment.factor_column]
        for field in adjustment.fields:
            if field not in table.column_names:
                continue
            index = table.schema.get_field_index(field)
            adjusted_values = pc.multiply(table[field], factor)
            table = table.set_column(index, field, adjusted_values)
        return table

    @staticmethod
    def _panel_instruments(
        table: pa.Table,
        dataset: RegisteredDataset,
        instruments: tuple[str, ...] | None,
    ) -> tuple[str, ...] | None:
        if instruments is None:
            return None
        if not DataClient._returns_suffixed_clickhouse_codes(dataset):
            return instruments
        if not instruments:
            return instruments

        instrument_column = dataset.spec.instrument_column
        actual: list[str] = []
        if instrument_column in table.column_names:
            for value in table[instrument_column].to_pylist():
                if value is None:
                    continue
                code = str(value)
                if code not in actual:
                    actual.append(code)

        resolved: list[str] = []
        for instrument in instruments:
            if DataClient._is_suffixed_instrument(instrument):
                candidates = (instrument,)
            else:
                prefix = f"{instrument}."
                matches = tuple(
                    code for code in actual if code == instrument or code.startswith(prefix)
                )
                candidates = matches or (instrument,)
            for candidate in candidates:
                if candidate not in resolved:
                    resolved.append(candidate)
        return tuple(resolved)

    @staticmethod
    def _returns_suffixed_clickhouse_codes(dataset: RegisteredDataset) -> bool:
        spec = dataset.spec
        return (
            isinstance(spec, ClickHouseDatasetSpec)
            and spec.instrument_column == "code"
            and "exg" in dataset.schema.names
        )

    @staticmethod
    def _is_suffixed_instrument(value: str) -> bool:
        return value.endswith(_MINGHU_CODE_SUFFIXES)

    @staticmethod
    def _validate_spec(spec: DatasetDefinition) -> None:
        if not spec.name.strip():
            raise DatasetRegistrationError("Dataset name cannot be empty")
        if not spec.time_column or not spec.instrument_column:
            raise DatasetRegistrationError("Key column names cannot be empty")
        if spec.time_column == spec.instrument_column:
            raise DatasetRegistrationError("Time and instrument columns must be different")
        if isinstance(spec, DatasetSpec) and not spec.paths:
            raise DatasetRegistrationError("Dataset paths cannot be empty")
        if isinstance(spec, TushareDatasetSpec):
            if spec.panel_mode not in {"period", "pit_daily"}:
                raise DatasetRegistrationError(
                    f"Unsupported Tushare panel_mode: {spec.panel_mode!r}"
                )
            if spec.disclosure_lag < 0:
                raise DatasetRegistrationError("disclosure_lag must be non-negative")
            if spec.fetch_buffer_days < 0:
                raise DatasetRegistrationError("fetch_buffer_days must be non-negative")
            if spec.fetch_margin_days < 0:
                raise DatasetRegistrationError("fetch_margin_days must be non-negative")
        if spec.timezone:
            try:
                ZoneInfo(spec.timezone)
            except Exception as exc:
                raise DatasetRegistrationError(f"Invalid timezone: {spec.timezone!r}") from exc

    @staticmethod
    def _prepare_query(
        dataset: RegisteredDataset,
        fields: Sequence[str],
        start: Any | None,
        end: Any | None,
        instruments: Sequence[str] | None,
        limit: int | None,
    ) -> DataQuery:
        requested_fields = tuple(fields)
        if not requested_fields:
            raise InvalidQueryError("At least one field is required")
        if not all(isinstance(field, str) and field for field in requested_fields):
            raise InvalidQueryError("Field names must be non-empty strings")
        if len(set(requested_fields)) != len(requested_fields):
            raise InvalidQueryError("Fields cannot contain duplicates")
        keys = {dataset.spec.time_column, dataset.spec.instrument_column}
        invalid_keys = keys.intersection(requested_fields)
        if invalid_keys:
            raise InvalidQueryError(f"Key columns cannot be requested as fields: {invalid_keys}")
        missing = set(requested_fields).difference(dataset.schema.names)
        if missing:
            raise FieldNotFoundError(f"Fields not found in dataset: {sorted(missing)}")

        localize = isinstance(dataset.spec, (ClickHouseDatasetSpec, TushareDatasetSpec))
        parsed_start = DataClient._parse_time(
            start, "start", dataset.spec.timezone if localize else None
        )
        parsed_end = DataClient._parse_time(
            end, "end", dataset.spec.timezone if localize else None
        )
        if parsed_start is not None and parsed_end is not None and parsed_start > parsed_end:
            raise InvalidQueryError("start must be earlier than or equal to end")
        if DataClient._requires_time_range(dataset.spec) and (
            parsed_start is None or parsed_end is None
        ):
            raise InvalidQueryError(
                f"Dataset {dataset.spec.name!r} requires both start and end"
            )

        requested_instruments: tuple[str, ...] | None = None
        if instruments is not None:
            requested_instruments = tuple(instruments)
            if not all(isinstance(item, str) and item for item in requested_instruments):
                raise InvalidQueryError("Instrument identifiers must be non-empty strings")
            if len(set(requested_instruments)) != len(requested_instruments):
                raise InvalidQueryError("Instruments cannot contain duplicates")
        if limit is not None and (
            isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0
        ):
            raise InvalidQueryError("limit must be a positive integer")
        return DataQuery(
            requested_fields, parsed_start, parsed_end, requested_instruments, limit
        )

    @staticmethod
    def _requires_time_range(spec: DatasetDefinition) -> bool:
        if isinstance(spec, ClickHouseDatasetSpec):
            return bool(
                spec.require_time_range is True
                or (spec.require_time_range is None and spec.partition_column is not None)
            )
        if isinstance(spec, TushareDatasetSpec):
            return bool(spec.require_time_range)
        return False

    @staticmethod
    def _parse_time(value: Any | None, name: str, timezone_name: str | None) -> datetime | None:
        if value is None:
            return None
        try:
            parsed = pd.Timestamp(value)
        except (TypeError, ValueError) as exc:
            raise InvalidQueryError(f"Invalid {name} value: {value!r}") from exc
        if pd.isna(parsed):
            raise InvalidQueryError(f"Invalid {name} value: {value!r}")
        result = cast(datetime, parsed.to_pydatetime())
        if timezone_name:
            zone = ZoneInfo(timezone_name)
            if result.tzinfo is None:
                result = result.replace(tzinfo=zone)
            else:
                result = result.astimezone(zone)
        return result

    @staticmethod
    def _empty_table(dataset: RegisteredDataset, fields: tuple[str, ...]) -> pa.Table:
        spec = dataset.spec
        arrays: dict[str, pa.Array] = {
            spec.time_column: pa.array([], type=dataset.schema.field(spec.time_column).type),
            spec.instrument_column: pa.array(
                [], type=dataset.schema.field(spec.instrument_column).type
            ),
        }
        for field in fields:
            arrays[field] = pa.array([], type=dataset.schema.field(field).type)
        return pa.table(arrays)

    @staticmethod
    def _validate_table_keys(table: pa.Table, dataset: RegisteredDataset) -> None:
        for column in (dataset.spec.time_column, dataset.spec.instrument_column):
            if column not in table.column_names:
                raise SchemaMismatchError(f"Query result is missing key column {column!r}")
            if pc.any(pc.is_null(table[column])).as_py():
                raise SchemaMismatchError(
                    f"Dataset {dataset.spec.name!r} contains null values in key column {column!r}"
                )

    @staticmethod
    def _attach_table_metadata(
        table: pa.Table,
        query_id: str,
        dataset: str,
        parameters: dict[str, Any],
    ) -> pa.Table:
        metadata = dict(table.schema.metadata or {})
        metadata.update(
            {
                b"quant_data.query_id": query_id.encode(),
                b"quant_data.dataset": dataset.encode(),
                b"quant_data.parameters": str(parameters).encode(),
                b"quant_data.adjusted": str(bool(parameters.get("adjusted"))).lower().encode(),
            }
        )
        return table.replace_schema_metadata(metadata)

    @staticmethod
    def _audit_value(value: Any | None) -> str | None:
        if value is None:
            return None
        try:
            return str(pd.Timestamp(value).isoformat())
        except (TypeError, ValueError):
            return repr(value)
