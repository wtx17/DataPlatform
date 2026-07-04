"""Point-in-time daily panel construction for disclosed fundamentals."""

from __future__ import annotations

from datetime import date
from typing import Sequence

import pandas as pd
import pyarrow as pa

from ..exceptions import InvalidQueryError


def build_daily_panels(
    table: pa.Table,
    *,
    dataset_name: str,
    disclosure_column: str,
    instrument_column: str,
    period_column: str,
    fields: Sequence[str],
    instruments: Sequence[str] | None,
    calendar: Sequence[date],
    panel_start: pd.Timestamp,
    panel_end: pd.Timestamp,
    disclosure_lag: int,
    index_name: str = "trade_date",
) -> dict[str, pd.DataFrame]:
    """Build daily, calendar-aligned, forward-filled PIT panels."""
    if disclosure_lag < 0:
        raise InvalidQueryError("disclosure_lag must be non-negative")
    if not isinstance(panel_start, pd.Timestamp) or not isinstance(panel_end, pd.Timestamp):
        raise InvalidQueryError("panel_start and panel_end must be pandas Timestamps")
    if panel_start > panel_end:
        raise InvalidQueryError("panel_start must be earlier than or equal to panel_end")

    cal = pd.DatetimeIndex(sorted(pd.to_datetime(list(calendar))))
    if len(cal) == 0:
        raise InvalidQueryError(
            f"Dataset {dataset_name!r} has an empty trading calendar for the requested range"
        )

    out_index = cal[(cal >= panel_start) & (cal <= panel_end)]

    if table.num_rows == 0:
        return _empty_panels(fields, instruments, out_index, index_name, instrument_column)

    frame = table.to_pandas()
    required_columns = {disclosure_column, instrument_column, period_column, *fields}
    for column in required_columns:
        if column not in frame.columns:
            raise InvalidQueryError(
                f"Dataset {dataset_name!r} PIT transform requires column {column!r}"
            )
    frame[disclosure_column] = pd.to_datetime(frame[disclosure_column])
    frame[period_column] = pd.to_datetime(frame[period_column])

    positions = cal.searchsorted(frame[disclosure_column].values, side="left")
    available_pos = positions + disclosure_lag
    in_calendar = available_pos < len(cal)
    frame = frame.loc[in_calendar].copy()
    if frame.empty:
        return _empty_panels(fields, instruments, out_index, index_name, instrument_column)
    frame["_available_day"] = cal.values[available_pos[in_calendar]]

    frame = frame.loc[frame["_available_day"] <= panel_end]
    if frame.empty:
        return _empty_panels(fields, instruments, out_index, index_name, instrument_column)

    frame = frame.sort_values(period_column, kind="mergesort", na_position="last")
    frame = frame.drop_duplicates(subset=["_available_day", instrument_column], keep="last")

    column_order = (
        list(instruments)
        if instruments is not None
        else sorted(frame[instrument_column].unique().tolist())
    )

    earliest = frame["_available_day"].min()
    fill_index = cal[(cal >= earliest) & (cal <= panel_end)]

    panels: dict[str, pd.DataFrame] = {}
    for field in fields:
        wide = frame.pivot(
            index="_available_day", columns=instrument_column, values=field
        )
        wide = wide.reindex(columns=column_order).reindex(fill_index).ffill()
        wide = wide.reindex(out_index)
        wide.index = wide.index.rename(index_name)
        wide.columns.name = instrument_column
        panels[field] = wide
    return panels


def _empty_panels(
    fields: Sequence[str],
    instruments: Sequence[str] | None,
    index: pd.DatetimeIndex,
    time_column: str,
    instrument_column: str,
) -> dict[str, pd.DataFrame]:
    column_order = list(instruments) if instruments is not None else []
    panels: dict[str, pd.DataFrame] = {}
    for field in fields:
        panel = pd.DataFrame(
            data=float("nan"),
            index=index.rename(time_column),
            columns=column_order,
        )
        panel.columns.name = instrument_column
        panels[field] = panel
    return panels
