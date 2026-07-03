"""Tushare backend implemented with the Tushare Pro API."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Mapping, cast

import pandas as pd
import pyarrow as pa

from ..exceptions import (
    BackendConnectionError,
    DatasetRegistrationError,
    RemoteQueryError,
    SchemaMismatchError,
)
from ..models import (
    DataQuery,
    DatasetDefinition,
    RegisteredDataset,
    TushareConfig,
    TushareDatasetSpec,
)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_QUARTER_ENDS = ((3, 31), (6, 30), (9, 30), (12, 31))

_INCOME_DEFAULT_FIELDS = (
    "ts_code",
    "ann_date",
    "f_ann_date",
    "end_date",
    "report_type",
    "comp_type",
    "end_type",
    "basic_eps",
    "diluted_eps",
    "total_revenue",
    "revenue",
    "int_income",
    "prem_earned",
    "comm_income",
    "n_commis_income",
    "n_oth_income",
    "n_oth_b_income",
    "prem_income",
    "out_prem",
    "une_prem_reser",
    "reins_income",
    "n_sec_tb_income",
    "n_sec_uw_income",
    "n_asset_mg_income",
    "oth_b_income",
    "fv_value_chg_gain",
    "invest_income",
    "ass_invest_income",
    "forex_gain",
    "total_cogs",
    "oper_cost",
    "int_exp",
    "comm_exp",
    "biz_tax_surchg",
    "sell_exp",
    "admin_exp",
    "fin_exp",
    "assets_impair_loss",
    "prem_refund",
    "compens_payout",
    "reser_insur_liab",
    "div_payt",
    "reins_exp",
    "oper_exp",
    "compens_payout_refu",
    "insur_reser_refu",
    "reins_cost_refund",
    "other_bus_cost",
    "operate_profit",
    "non_oper_income",
    "non_oper_exp",
    "nca_disploss",
    "total_profit",
    "income_tax",
    "n_income",
    "n_income_attr_p",
    "minority_gain",
    "oth_compr_income",
    "t_compr_income",
    "compr_inc_attr_p",
    "compr_inc_attr_m_s",
    "ebit",
    "ebitda",
    "insurance_exp",
    "undist_profit",
    "distable_profit",
    "rd_exp",
    "fin_exp_int_exp",
    "fin_exp_int_inc",
    "transfer_surplus_rese",
    "transfer_housing_imprest",
    "transfer_oth",
    "adj_lossgain",
    "withdra_legal_surplus",
    "withdra_legal_pubfund",
    "withdra_biz_devfund",
    "withdra_rese_fund",
    "withdra_oth_ersu",
    "workers_welfare",
    "distr_profit_shrhder",
    "prfshare_payable_dvd",
    "comshare_payable_dvd",
    "capit_comstock_div",
    "continued_net_profit",
    "update_flag",
)
_INCOME_DATE_FIELDS = frozenset({"ann_date", "f_ann_date", "end_date"})
_INCOME_STRING_FIELDS = frozenset(
    {"ts_code", "report_type", "comp_type", "end_type", "update_flag"}
)


@dataclass(frozen=True, slots=True)
class TushareTableCatalog:
    api_name: str
    schema: pa.Schema
    query_style: str
    period_param: str | None
    start_param: str | None
    end_param: str | None
    instrument_param: str
    dedupe_keys: tuple[str, str]
    dedupe_sort: tuple[str, ...]
    order_columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TushareSource:
    connection: str
    api_name: str
    schema_hash: str
    fixed_params: Mapping[str, object]


def _income_schema() -> pa.Schema:
    fields: list[pa.Field] = []
    for name in _INCOME_DEFAULT_FIELDS:
        if name in _INCOME_DATE_FIELDS:
            data_type = pa.date32()
        elif name in _INCOME_STRING_FIELDS:
            data_type = pa.string()
        else:
            data_type = pa.float64()
        fields.append(pa.field(name, data_type))
    return pa.schema(fields)


_INCOME_SCHEMA = _income_schema()
_TUSHARE_TABLES = {
    "income": TushareTableCatalog(
        api_name="income",
        schema=_INCOME_SCHEMA,
        query_style="date_range",
        period_param=None,
        start_param="start_date",
        end_param="end_date",
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("f_ann_date", "ann_date", "update_flag"),
        order_columns=("end_date", "ts_code"),
    ),
    "income_vip": TushareTableCatalog(
        api_name="income_vip",
        schema=_INCOME_SCHEMA,
        query_style="period_range",
        period_param="period",
        start_param=None,
        end_param=None,
        instrument_param="ts_code",
        dedupe_keys=("ts_code", "end_date"),
        dedupe_sort=("f_ann_date", "ann_date", "update_flag"),
        order_columns=("end_date", "ts_code"),
    ),
}


class TushareBackend:
    def __init__(self, client_factory: Callable[..., Any] | None = None) -> None:
        self._configs: dict[str, TushareConfig] = {}
        self._clients: dict[str, Any] = {}
        self._client_factory = client_factory

    def add_connection(self, name: str, config: TushareConfig) -> None:
        if not name or not _IDENTIFIER.fullmatch(name):
            raise DatasetRegistrationError(f"Invalid Tushare connection name: {name!r}")
        if config.token is not None and not config.token:
            raise DatasetRegistrationError("Tushare token cannot be empty")
        if config.token_env is not None and not config.token_env:
            raise DatasetRegistrationError("Tushare token environment variable cannot be empty")
        if config.token is None and config.token_env is None:
            raise DatasetRegistrationError("Tushare token or token_env must be configured")
        existing = self._clients.pop(name, None)
        if existing is not None:
            self._close_client(existing)
        self._configs[name] = config

    def prepare(self, definition: DatasetDefinition) -> RegisteredDataset:
        if not isinstance(definition, TushareDatasetSpec):
            raise DatasetRegistrationError("Tushare backend requires TushareDatasetSpec")
        catalog = self._catalog(definition.api_name)
        self._validate_definition(definition, catalog)
        self._client(definition.connection)
        normalized = json.dumps(
            [(field.name, str(field.type)) for field in catalog.schema],
            separators=(",", ":"),
        )
        source = TushareSource(
            definition.connection,
            catalog.api_name,
            hashlib.sha256(normalized.encode()).hexdigest(),
            dict(definition.fixed_params),
        )
        return RegisteredDataset(definition, catalog.schema, source)

    def scan(self, dataset: RegisteredDataset, query: DataQuery) -> pa.Table:
        spec = dataset.spec
        source = dataset.source
        if not isinstance(spec, TushareDatasetSpec) or not isinstance(source, TushareSource):
            raise SchemaMismatchError("Invalid Tushare registered dataset")
        catalog = self._catalog(source.api_name)
        client = self._client(source.connection)
        selected = self._selected_columns(spec, query.fields)
        remote_fields = self._remote_columns(selected, spec, catalog)
        frames = self._fetch_frames(client, spec, catalog, query, remote_fields)
        frame = self._normalize_frames(frames, spec, catalog, query, remote_fields)
        frame = self._project_frame(frame, spec, catalog, query, selected)
        return self._to_arrow(frame, catalog.schema, selected)

    def fingerprint(self, dataset: RegisteredDataset) -> dict[str, object]:
        spec = dataset.spec
        source = dataset.source
        if not isinstance(spec, TushareDatasetSpec) or not isinstance(source, TushareSource):
            raise SchemaMismatchError("Invalid Tushare registered dataset")
        return {
            "backend": "tushare",
            "connection": source.connection,
            "api_name": source.api_name,
            "schema_hash": source.schema_hash,
            "fixed_params": {str(key): str(value) for key, value in source.fixed_params.items()},
        }

    def close(self) -> None:
        for client in self._clients.values():
            self._close_client(client)
        self._clients.clear()

    def _client(self, name: str) -> Any:
        existing = self._clients.get(name)
        if existing is not None:
            return existing
        config = self._configs.get(name)
        if config is None:
            raise DatasetRegistrationError(f"Tushare connection {name!r} is not configured")
        token = config.token
        if token is None and config.token_env:
            token = os.environ.get(config.token_env)
            if token is None:
                raise BackendConnectionError(
                    f"Tushare token environment variable {config.token_env!r} is not set"
                )
        if token is None:
            raise BackendConnectionError("Tushare token is not configured")
        factory = self._client_factory
        if factory is None:
            try:
                import tushare as ts
            except ImportError as exc:
                raise BackendConnectionError(
                    "Tushare support is not installed; install the tushare package"
                ) from exc
            try:
                ts_module = cast(Any, ts)
                ts_module.set_token(token)
                client = ts_module.pro_api()
            except Exception as exc:
                raise BackendConnectionError(f"Unable to initialize Tushare client: {exc}") from exc
        else:
            try:
                client = factory(token=token)
            except Exception as exc:
                raise BackendConnectionError(f"Unable to initialize Tushare client: {exc}") from exc
        self._clients[name] = client
        return client

    @staticmethod
    def _catalog(api_name: str) -> TushareTableCatalog:
        catalog = _TUSHARE_TABLES.get(api_name)
        if catalog is None:
            supported = ", ".join(sorted(_TUSHARE_TABLES))
            raise DatasetRegistrationError(
                f"Unsupported Tushare api {api_name!r}; supported APIs: {supported}"
            )
        return catalog

    @staticmethod
    def _validate_definition(
        definition: TushareDatasetSpec, catalog: TushareTableCatalog
    ) -> None:
        schema_names = set(catalog.schema.names)
        required = {definition.time_column, definition.instrument_column}
        required.update(catalog.dedupe_keys)
        required.update(catalog.dedupe_sort)
        required.update(definition.order_columns)
        missing = required.difference(schema_names)
        if missing:
            raise DatasetRegistrationError(
                f"Tushare api {definition.api_name!r} is missing configured columns: "
                f"{sorted(missing)}"
            )
        reserved = {"fields"}
        if catalog.period_param:
            reserved.add(catalog.period_param)
        if catalog.start_param:
            reserved.add(catalog.start_param)
        if catalog.end_param:
            reserved.add(catalog.end_param)
        reserved.add(catalog.instrument_param)
        conflicts = reserved.intersection(definition.fixed_params)
        if conflicts:
            raise DatasetRegistrationError(
                f"Tushare fixed_params cannot define backend-managed parameters: "
                f"{sorted(conflicts)}"
            )

    @staticmethod
    def _selected_columns(spec: TushareDatasetSpec, fields: tuple[str, ...]) -> tuple[str, ...]:
        columns: list[str] = []
        for column in (spec.time_column, spec.instrument_column, *fields):
            if column not in columns:
                columns.append(column)
        return tuple(columns)

    @staticmethod
    def _remote_columns(
        selected: tuple[str, ...],
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
    ) -> tuple[str, ...]:
        columns = list(selected)
        for column in (*catalog.dedupe_sort, *spec.order_columns):
            if column not in columns:
                columns.append(column)
        return tuple(columns)

    def _fetch_frames(
        self,
        client: Any,
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        fields: tuple[str, ...],
    ) -> list[pd.DataFrame]:
        periods = (
            self._periods(query.start, query.end)
            if catalog.query_style == "period_range"
            else None
        )
        if periods == ():
            return []
        instruments = query.instruments
        if instruments == ():
            return []
        period_values: tuple[str | None, ...] = periods if periods is not None else (None,)
        instrument_values: tuple[str | None, ...]
        instrument_values = instruments if instruments is not None else (None,)
        frames: list[pd.DataFrame] = []
        for period in period_values:
            for instrument in instrument_values:
                params = self._call_params(spec, catalog, query, fields, period, instrument)
                frames.append(self._call_api(client, catalog.api_name, params))
        return frames

    @staticmethod
    def _call_params(
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        fields: tuple[str, ...],
        period: str | None,
        instrument: str | None,
    ) -> dict[str, object]:
        params = dict(spec.fixed_params)
        params["fields"] = ",".join(fields)
        if catalog.query_style == "period_range":
            if period is not None and catalog.period_param is not None:
                params[catalog.period_param] = period
        else:
            if query.start is not None and catalog.start_param is not None:
                params[catalog.start_param] = query.start.strftime("%Y%m%d")
            if query.end is not None and catalog.end_param is not None:
                params[catalog.end_param] = query.end.strftime("%Y%m%d")
        if instrument is not None:
            params[catalog.instrument_param] = instrument
        return params

    @staticmethod
    def _call_api(client: Any, api_name: str, params: dict[str, object]) -> pd.DataFrame:
        try:
            method = getattr(client, api_name, None)
            if callable(method):
                result = method(**params)
            elif callable(getattr(client, "query", None)):
                result = client.query(api_name, **params)
            else:
                raise AttributeError(f"Tushare client does not expose {api_name!r}")
        except Exception as exc:
            raise RemoteQueryError(f"Tushare query failed for api {api_name!r}: {exc}") from exc
        if not isinstance(result, pd.DataFrame):
            raise RemoteQueryError(
                f"Tushare api {api_name!r} returned {type(result).__name__}, expected DataFrame"
            )
        return result

    def _normalize_frames(
        self,
        frames: list[pd.DataFrame],
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        columns: tuple[str, ...],
    ) -> pd.DataFrame:
        if frames:
            frame = pd.concat(frames, ignore_index=True)
        else:
            frame = pd.DataFrame(columns=columns)
        missing = set(columns).difference(frame.columns)
        if missing:
            raise SchemaMismatchError(
                f"Tushare api {catalog.api_name!r} result is missing columns: {sorted(missing)}"
            )
        frame = frame.loc[:, list(columns)].copy()
        frame = self._coerce_frame(frame, catalog.schema)
        frame = self._filter_time(frame, spec.time_column, query)
        frame = self._dedupe(frame, catalog)
        return self._sort_frame(frame, spec, catalog)

    @staticmethod
    def _project_frame(
        frame: pd.DataFrame,
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
        query: DataQuery,
        selected: tuple[str, ...],
    ) -> pd.DataFrame:
        if query.limit is not None:
            frame = frame.head(query.limit)
        missing = set(selected).difference(frame.columns)
        if missing:
            raise SchemaMismatchError(
                f"Tushare api {catalog.api_name!r} normalized result is missing columns: "
                f"{sorted(missing)}"
            )
        return frame.loc[:, list(selected)]

    @staticmethod
    def _coerce_frame(frame: pd.DataFrame, schema: pa.Schema) -> pd.DataFrame:
        for field in schema:
            if field.name not in frame.columns:
                continue
            if pa.types.is_date32(field.type):
                frame[field.name] = TushareBackend._coerce_yyyymmdd(
                    frame[field.name], field.name
                )
            elif pa.types.is_string(field.type):
                frame[field.name] = frame[field.name].astype("string")
            elif pa.types.is_floating(field.type):
                frame[field.name] = pd.to_numeric(frame[field.name], errors="coerce")
        return frame

    @staticmethod
    def _coerce_yyyymmdd(series: pd.Series, name: str) -> pd.Series:
        result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
        mask = series.notna() & (series.astype("string") != "")
        if mask.any():
            parsed = pd.to_datetime(
                series.loc[mask].astype("string"), format="%Y%m%d", errors="coerce"
            )
            if parsed.isna().any():
                bad = series.loc[mask][parsed.isna()].head(5).to_list()
                raise SchemaMismatchError(
                    f"Tushare column {name!r} contains invalid YYYYMMDD values: {bad}"
                )
            result.loc[mask] = parsed
        return result.dt.date

    @staticmethod
    def _filter_time(
        frame: pd.DataFrame,
        time_column: str,
        query: DataQuery,
    ) -> pd.DataFrame:
        if frame.empty:
            return frame
        if query.start is not None:
            frame = frame.loc[
                frame[time_column].notna() & (frame[time_column] >= query.start.date())
            ]
        if query.end is not None:
            frame = frame.loc[
                frame[time_column].notna() & (frame[time_column] <= query.end.date())
            ]
        return frame

    @staticmethod
    def _dedupe(frame: pd.DataFrame, catalog: TushareTableCatalog) -> pd.DataFrame:
        if frame.empty:
            return frame
        sort_columns = [column for column in catalog.dedupe_sort if column in frame.columns]
        if sort_columns:
            frame = frame.sort_values(
                sort_columns,
                ascending=[False] * len(sort_columns),
                kind="mergesort",
                na_position="last",
            )
        return frame.drop_duplicates(list(catalog.dedupe_keys), keep="first")

    @staticmethod
    def _sort_frame(
        frame: pd.DataFrame,
        spec: TushareDatasetSpec,
        catalog: TushareTableCatalog,
    ) -> pd.DataFrame:
        if frame.empty:
            return frame
        order_columns = spec.order_columns or catalog.order_columns
        available = [column for column in order_columns if column in frame.columns]
        if not available:
            return frame
        return frame.sort_values(available, kind="mergesort", na_position="last")

    @staticmethod
    def _to_arrow(
        frame: pd.DataFrame,
        schema: pa.Schema,
        selected: tuple[str, ...],
    ) -> pa.Table:
        selected_schema = pa.schema([schema.field(column) for column in selected])
        if frame.empty:
            return pa.table(
                {field.name: pa.array([], type=field.type) for field in selected_schema}
            )
        try:
            return pa.Table.from_pandas(frame, schema=selected_schema, preserve_index=False)
        except (pa.ArrowException, ValueError, TypeError) as exc:
            raise SchemaMismatchError(f"Unable to convert Tushare result to Arrow: {exc}") from exc

    @staticmethod
    def _periods(start: datetime | None, end: datetime | None) -> tuple[str, ...] | None:
        if start is None or end is None:
            return None
        start_date = start.date()
        end_date = end.date()
        periods: list[str] = []
        for year in range(start_date.year, end_date.year + 1):
            for month, day in _QUARTER_ENDS:
                current = date(year, month, day)
                if start_date <= current <= end_date:
                    periods.append(current.strftime("%Y%m%d"))
        return tuple(periods)

    @staticmethod
    def _close_client(client: Any) -> None:
        close = getattr(client, "close", None)
        if callable(close):
            close()
