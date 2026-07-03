"""DuckDB-backed local Parquet scanner."""

from __future__ import annotations

import glob
import os
from collections.abc import Iterable, Sequence
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from ..exceptions import DatasetRegistrationError, SchemaMismatchError
from ..models import DataQuery, DatasetDefinition, DatasetSpec, RegisteredDataset


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


class DuckDBParquetBackend:
    """Read all matching Parquet files as one logical long table."""

    def prepare(self, definition: DatasetDefinition) -> RegisteredDataset:
        if not isinstance(definition, DatasetSpec):
            raise DatasetRegistrationError("Parquet backend requires DatasetSpec")
        files = self._resolve_paths(definition.paths)
        schema = self._inspect_schema(tuple(str(path) for path in files))
        for path in files:
            file_schema = pq.read_schema(path)
            missing_keys = {
                definition.time_column,
                definition.instrument_column,
            }.difference(file_schema.names)
            if missing_keys:
                raise DatasetRegistrationError(
                    f"Parquet file {path} is missing key columns: {sorted(missing_keys)}"
                )
        return RegisteredDataset(definition, schema, tuple(files))

    def _inspect_schema(self, files: tuple[str, ...]) -> pa.Schema:
        schemas: list[pa.Schema] = []
        try:
            for path in files:
                schemas.append(pq.read_schema(path))
            return pa.unify_schemas(schemas, promote_options="permissive")
        except (pa.ArrowException, OSError) as exc:
            raise SchemaMismatchError(f"Unable to unify Parquet schemas: {exc}") from exc

    def fingerprint(self, dataset: RegisteredDataset) -> dict[str, object]:
        fingerprints: list[dict[str, object]] = []
        for path in self._files(dataset):
            stat = os.stat(path)
            fingerprints.append(
                {"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
            )
        return {"backend": "parquet", "files": fingerprints}

    def scan(self, dataset: RegisteredDataset, query: DataQuery) -> pa.Table:
        spec = dataset.spec
        time_col = _quote_identifier(spec.time_column)
        instrument_col = _quote_identifier(spec.instrument_column)
        projected = [
            f"CAST({time_col} AS TIMESTAMP) AS {time_col}",
            instrument_col,
            *[_quote_identifier(field) for field in query.fields],
        ]
        sql = (
            f"SELECT {', '.join(projected)} "
            "FROM read_parquet(?, union_by_name = true) AS source"
        )
        params: list[object] = [[str(path) for path in self._files(dataset)]]
        clauses: list[str] = []

        if query.start is not None:
            clauses.append(f"CAST({time_col} AS TIMESTAMP) >= ?")
            params.append(query.start)
        if query.end is not None:
            clauses.append(f"CAST({time_col} AS TIMESTAMP) <= ?")
            params.append(query.end)

        connection = duckdb.connect(database=":memory:")
        try:
            if query.instruments is not None:
                requested = pa.table({spec.instrument_column: list(query.instruments)})
                connection.register("requested_instruments", requested)
                sql += (
                    f" INNER JOIN requested_instruments AS requested USING ({instrument_col})"
                )
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += f" ORDER BY {time_col}, {instrument_col}"
            if query.limit is not None:
                sql += " LIMIT ?"
                params.append(query.limit)
            return connection.execute(sql, params).to_arrow_table()
        except (duckdb.Error, pa.ArrowException) as exc:
            raise SchemaMismatchError(f"Parquet query failed for dataset {spec.name!r}: {exc}") from exc
        finally:
            connection.close()

    def close(self) -> None:
        return None

    @staticmethod
    def _files(dataset: RegisteredDataset) -> tuple[Path, ...]:
        source = dataset.source
        if not isinstance(source, tuple) or not all(isinstance(path, Path) for path in source):
            raise SchemaMismatchError("Invalid Parquet dataset source")
        return source

    @staticmethod
    def _resolve_paths(paths: Sequence[str | Path]) -> list[Path]:
        resolved: set[Path] = set()
        for raw in paths:
            value = Path(raw).expanduser()
            matches: Iterable[Path]
            if value.is_dir():
                matches = value.rglob("*.parquet")
            elif glob.has_magic(str(value)):
                matches = (Path(item) for item in glob.glob(str(value), recursive=True))
            else:
                matches = (value,)
            for match in matches:
                if match.is_file() and match.suffix.lower() == ".parquet":
                    resolved.add(match.resolve())
        if not resolved:
            raise DatasetRegistrationError("No Parquet files matched the supplied paths")
        return sorted(resolved, key=str)
