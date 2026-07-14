"""Storage backend protocol."""

from typing import Protocol

import pyarrow as pa

from ..models import DataQuery, DatasetDefinition, RegisteredDataset


class DataBackend(Protocol):
    """Protocol implemented by storage backends.

    Notes
    -----
    A backend validates definitions in :meth:`prepare`, executes normalized
    scans in :meth:`scan`, provides sanitized provenance in
    :meth:`fingerprint`, and releases resources in :meth:`close`.
    """

    def prepare(self, spec: DatasetDefinition) -> RegisteredDataset:
        """Validate a definition and create backend-owned prepared state.

        Parameters
        ----------
        spec
            Dataset definition assigned to this backend.

        Returns
        -------
        RegisteredDataset
            Normalized specification, Arrow schema, source descriptor, and
            optional adjustment policy.
        """

        ...

    def scan(self, dataset: RegisteredDataset, query: DataQuery) -> pa.Table:
        """Execute a normalized query and return an Arrow long table.

        Parameters
        ----------
        dataset
            Prepared dataset returned by :meth:`prepare`.
        query
            Validated field, time, instrument, and limit request.

        Returns
        -------
        pyarrow.Table
            Projected long table containing both key columns.
        """

        ...

    def fingerprint(self, dataset: RegisteredDataset) -> dict[str, object]:
        """Return sanitized source provenance for a query audit.

        Parameters
        ----------
        dataset
            Prepared dataset returned by :meth:`prepare`.

        Returns
        -------
        dict[str, object]
            JSON-serializable source metadata without credentials.
        """

        ...

    def close(self) -> None:
        """Release cached clients or other persistent resources."""

        ...
