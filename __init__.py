"""Public API for the quant data access package."""

from .client import DataClient
from ._version import __version__ as __version__
from .exceptions import (
    AuditWriteError,
    BackendConnectionError,
    DatasetNotFoundError,
    DatasetRegistrationError,
    DuplicateObservationError,
    FieldNotFoundError,
    InvalidQueryError,
    QuantDataError,
    RemoteQueryError,
    SchemaMismatchError,
)
from .models import ClickHouseConfig, ClickHouseDatasetSpec, DatasetSpec

__all__ = [
    "AuditWriteError",
    "BackendConnectionError",
    "ClickHouseConfig",
    "ClickHouseDatasetSpec",
    "DataClient",
    "DatasetNotFoundError",
    "DatasetRegistrationError",
    "DatasetSpec",
    "DuplicateObservationError",
    "FieldNotFoundError",
    "InvalidQueryError",
    "QuantDataError",
    "RemoteQueryError",
    "SchemaMismatchError",
    "__version__",
]
