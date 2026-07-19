"""Point-in-time daily panel construction for disclosed fundamentals."""

from __future__ import annotations

from datetime import date
from typing import Sequence

import pandas as pd
import pyarrow as pa

from ..exceptions import InvalidQueryError, SchemaMismatchError


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
    revision_order: Sequence[str] = (),
    index_name: str = "trade_date",
) -> dict[str, pd.DataFrame]:
    """Build trading-day-aligned point-in-time panels from disclosure events.

    Parameters
    ----------
    table
        Disclosure-event table containing disclosure, instrument, period, and
        requested field columns.
    dataset_name
        Name included in validation error messages.
    disclosure_column
        Date on which an event was disclosed.
    instrument_column
        Security identifier used for panel columns.
    period_column
        Reporting period used to resolve same-day competing events.
    fields
        Value columns to build in caller order.
    instruments
        Requested output-column order, or ``None`` to sort observed identifiers.
    calendar
        Ordered or unordered open trading dates covering buffering and lag.
    panel_start, panel_end
        Inclusive requested output boundaries.
    disclosure_lag
        Number of trading sessions after the snapped disclosure session before
        a value becomes available.
    revision_order
        Catalog precedence columns used as a lexicographic tuple. The greatest
        tuple wins when multiple revisions of one report period become
        available together.
    index_name
        Name assigned to the output trading-date index.

    Returns
    -------
    dict[str, pandas.DataFrame]
        Daily panels restricted to the requested interval.

    Raises
    ------
    InvalidQueryError
        If lag or bounds are invalid, the calendar is empty, or required event
        columns are absent.
    SchemaMismatchError
        If equally ranked revisions contain conflicting requested values.

    Notes
    -----
    Non-trading disclosure dates snap to the next session before lag is added.
    State is maintained per instrument and report period; the greatest known
    report period is active. A late revision to an older period therefore does
    not displace a newer report. The active row is carried as one unit, so an
    explicit null in a new report remains null rather than inheriting the prior
    report's value.
    """

    if disclosure_lag < 0:
        raise InvalidQueryError("disclosure_lag must be non-negative")
    if not isinstance(panel_start, pd.Timestamp) or not isinstance(panel_end, pd.Timestamp):
        raise InvalidQueryError("panel_start and panel_end must be pandas Timestamps")
    if panel_start > panel_end:
        raise InvalidQueryError("panel_start must be earlier than or equal to panel_end")

    cal = pd.DatetimeIndex(sorted(set(pd.to_datetime(list(calendar)))))
    if len(cal) == 0:
        raise InvalidQueryError(
            f"Dataset {dataset_name!r} has an empty trading calendar for the requested range"
        )

    out_index = cal[(cal >= panel_start) & (cal <= panel_end)]

    if table.num_rows == 0:
        return _empty_panels(fields, instruments, out_index, index_name, instrument_column)

    frame = table.to_pandas()
    required_columns = {
        disclosure_column,
        instrument_column,
        period_column,
        *revision_order,
        *fields,
    }
    for column in required_columns:
        if column not in frame.columns:
            raise InvalidQueryError(
                f"Dataset {dataset_name!r} PIT transform requires column {column!r}"
            )
    frame[disclosure_column] = pd.to_datetime(frame[disclosure_column])
    frame[period_column] = pd.to_datetime(frame[period_column])
    null_keys = frame[[disclosure_column, instrument_column, period_column]].isna()
    if null_keys.any(axis=None):
        bad_columns = null_keys.columns[null_keys.any()].tolist()
        raise SchemaMismatchError(
            f"Dataset {dataset_name!r} PIT events contain null state keys: {bad_columns}"
        )

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

    frame = _resolve_revisions(
        frame,
        dataset_name=dataset_name,
        instrument_column=instrument_column,
        period_column=period_column,
        fields=tuple(fields),
        revision_order=tuple(revision_order),
    )
    frame = frame.reset_index(drop=True)
    frame["_row_id"] = frame.index.astype("int64")

    column_order = (
        list(instruments)
        if instruments is not None
        else sorted(frame[instrument_column].unique().tolist())
    )

    state_events = _active_state_events(
        frame,
        instrument_column=instrument_column,
        period_column=period_column,
    )
    earliest = state_events["_available_day"].min()
    fill_index = cal[(cal >= earliest) & (cal <= panel_end)]
    row_ids = state_events.pivot(
        index="_available_day",
        columns=instrument_column,
        values="_row_id",
    )
    row_ids = row_ids.reindex(columns=column_order).reindex(fill_index).ffill()
    row_ids = row_ids.reindex(out_index)
    row_lookup = frame.set_index("_row_id")

    panels: dict[str, pd.DataFrame] = {}
    for field in fields:
        panel = row_ids.apply(
            lambda column: column.map(
                lambda row_id: (
                    float("nan")
                    if pd.isna(row_id)
                    else row_lookup.at[int(row_id), field]
                )
            )
        )
        panel.index = panel.index.rename(index_name)
        panel.columns.name = instrument_column
        panels[field] = panel
    return panels


def _resolve_revisions(
    frame: pd.DataFrame,
    *,
    dataset_name: str,
    instrument_column: str,
    period_column: str,
    fields: tuple[str, ...],
    revision_order: tuple[str, ...],
) -> pd.DataFrame:
    """Choose one row for each simultaneous instrument/period revision."""

    keys = ["_available_day", instrument_column, period_column]
    sort_columns = [*keys, *revision_order]
    ordered = frame.sort_values(
        sort_columns,
        kind="mergesort",
        na_position="first",
    )
    winners: list[pd.Series] = []
    for key, group in ordered.groupby(keys, sort=False, dropna=False):
        winner = group.iloc[-1]
        tied = group
        for column in revision_order:
            value = winner[column]
            tied = tied.loc[
                tied[column].isna() if pd.isna(value) else tied[column].eq(value)
            ]
        if len(tied.loc[:, list(fields)].drop_duplicates()) > 1:
            available_day, instrument, period = key
            raise SchemaMismatchError(
                f"Dataset {dataset_name!r} has conflicting equally ranked PIT "
                f"revisions for {instrument!r}, period {period!s}, available "
                f"{available_day!s}"
            )
        winners.append(tied.iloc[-1])
    return pd.DataFrame(winners).sort_values(
        ["_available_day", instrument_column, period_column],
        kind="mergesort",
    )


def _active_state_events(
    frame: pd.DataFrame,
    *,
    instrument_column: str,
    period_column: str,
) -> pd.DataFrame:
    """Emit the active whole-row identifier after every availability event."""

    records: list[dict[str, object]] = []
    for instrument, instrument_frame in frame.groupby(
        instrument_column, sort=False, dropna=False
    ):
        latest_by_period: dict[pd.Timestamp, int] = {}
        for available_day, events in instrument_frame.groupby(
            "_available_day", sort=True, dropna=False
        ):
            for _, event in events.iterrows():
                latest_by_period[event[period_column]] = int(event["_row_id"])
            active_period = max(latest_by_period)
            records.append(
                {
                    "_available_day": available_day,
                    instrument_column: instrument,
                    "_row_id": latest_by_period[active_period],
                }
            )
    return pd.DataFrame(records)


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
