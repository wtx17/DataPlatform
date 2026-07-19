"""Domain exceptions raised by quant_data."""


class QuantDataError(Exception):
    """Base class for package errors."""


class DatasetNotFoundError(QuantDataError):
    """The requested dataset is not registered."""


class DatasetRegistrationError(QuantDataError):
    """A dataset cannot be registered."""


class FieldNotFoundError(QuantDataError):
    """A requested field is not present in the dataset."""


class InvalidQueryError(QuantDataError):
    """Query parameters are invalid."""


class SchemaMismatchError(QuantDataError):
    """Storage schemas or query result schemas cannot be reconciled."""


class DuplicateObservationError(QuantDataError):
    """More than one row exists for a time/instrument pair."""


class AuditWriteError(QuantDataError):
    """The query audit record could not be persisted."""


class BackendConnectionError(QuantDataError):
    """A storage backend connection could not be established."""


class RemoteQueryError(QuantDataError):
    """A remote storage query failed."""
