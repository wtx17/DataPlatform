from __future__ import annotations

import inspect
import os
import subprocess
import sys
from pathlib import Path

import quant_data
from quant_data.audit import AuditWriter
from quant_data.backends import ClickHouseBackend, DuckDBParquetBackend, TushareBackend
from quant_data.backends.base import DataBackend
from quant_data.initialize import (
    clickhouse_dataset_specs,
    initialize,
    initialize_data_client,
    registered_dataset_names,
    tushare_parquet_dataset_specs,
    tushare_dataset_specs,
)
from quant_data.transforms import build_daily_panels, build_panels


ROOT = Path(__file__).resolve().parents[1]


def test_root_exports_and_public_methods_have_docstrings() -> None:
    assert isinstance(quant_data.__version__, str) and quant_data.__version__
    for name in quant_data.__all__:
        if name == "__version__":
            continue
        assert inspect.getdoc(getattr(quant_data, name)), name

    for name, member in inspect.getmembers(quant_data.DataClient, inspect.isfunction):
        if not name.startswith("_"):
            assert inspect.getdoc(member), f"DataClient.{name}"


def test_core_extension_points_have_docstrings() -> None:
    objects = (
        DataBackend,
        DuckDBParquetBackend,
        ClickHouseBackend,
        TushareBackend,
        AuditWriter,
        build_panels,
        build_daily_panels,
        clickhouse_dataset_specs,
        tushare_dataset_specs,
        tushare_parquet_dataset_specs,
        registered_dataset_names,
        initialize_data_client,
        initialize,
    )
    for item in objects:
        assert inspect.getdoc(item), item

    for backend in (DuckDBParquetBackend, ClickHouseBackend, TushareBackend):
        for name in ("prepare", "scan", "fingerprint", "close"):
            assert inspect.getdoc(getattr(backend, name)), f"{backend.__name__}.{name}"


def test_documentation_sync_is_current() -> None:
    result = subprocess.run(
        [sys.executable, "docs/_scripts/sync_reference.py", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_package_import_and_spec_generation_need_no_credentials() -> None:
    environment = os.environ.copy()
    for name in (
        "MINGHU_CLICKHOUSE_PASSWORD",
        "QUANT_DATA_CLICKHOUSE_PASSWORD",
        "TUSHARE_TOKEN",
        "QUANT_DATA_TUSHARE_TOKEN",
    ):
        environment.pop(name, None)
    code = (
        "import quant_data; "
        "from quant_data.initialize import clickhouse_dataset_specs, tushare_dataset_specs; "
        "assert clickhouse_dataset_specs(); assert tushare_dataset_specs()"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
