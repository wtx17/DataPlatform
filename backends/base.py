"""Storage backend protocol."""

from typing import Protocol

import pyarrow as pa

from ..models import DataQuery, DatasetDefinition, RegisteredDataset


class DataBackend(Protocol):
    def prepare(self, spec: DatasetDefinition) -> RegisteredDataset: ...

    def scan(self, dataset: RegisteredDataset, query: DataQuery) -> pa.Table: ...

    def fingerprint(self, dataset: RegisteredDataset) -> dict[str, object]: ...

    def close(self) -> None: ...
