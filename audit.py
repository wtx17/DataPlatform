"""Durable JSON audit records for data queries."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from .exceptions import AuditWriteError
from .models import QueryAudit


class AuditWriter:
    """Persist query audit records with an atomic file replacement.

    Parameters
    ----------
    root
        Root directory beneath which records are partitioned by UTC date.

    Notes
    -----
    Each record is written to a temporary file, flushed and synchronized, then
    atomically moved to ``YYYY-MM-DD/<query_id>.json``.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def write(self, record: QueryAudit) -> Path:
        """Write one audit record.

        Parameters
        ----------
        record
            Mutable query audit state to serialize as JSON.

        Returns
        -------
        pathlib.Path
            Final path of the persisted record.

        Raises
        ------
        AuditWriteError
            If directory creation, serialization, synchronization, or atomic
            replacement fails.
        """

        day = record.started_at[:10]
        target_dir = self.root / day
        target = target_dir / f"{record.query_id}.json"
        temporary: str | None = None
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=target_dir,
                prefix=f".{record.query_id}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = handle.name
                json.dump(asdict(record), handle, ensure_ascii=True, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            return target
        except (OSError, TypeError, ValueError) as exc:
            if temporary is not None:
                try:
                    Path(temporary).unlink(missing_ok=True)
                except OSError:
                    pass
            raise AuditWriteError(f"Unable to write query audit record {target}: {exc}") from exc
