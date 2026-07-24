from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dataset_catalog_is_current_and_generation_is_offline() -> None:
    environment = os.environ.copy()
    for name in (
        "MINGHU_CLICKHOUSE_PASSWORD",
        "QUANT_DATA_CLICKHOUSE_PASSWORD",
        "TUSHARE_TOKEN",
        "QUANT_DATA_TUSHARE_TOKEN",
    ):
        environment.pop(name, None)

    result = subprocess.run(
        [sys.executable, "tools/generate_dataset_catalog.py", "--check"],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
