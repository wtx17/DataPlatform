#!/usr/bin/env python3
"""Generate and validate code-derived Sphinx reference pages.

The script deliberately uses only package exports, immutable initialization
specifications, and local backend catalogs. It never constructs ``DataClient``
or a backend client, and therefore never reads credentials or performs network
I/O.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

import quant_data  # noqa: E402
from quant_data.backends.clickhouse_catalog import MINGHU_TABLE_COLUMN_TYPES  # noqa: E402
from quant_data.backends.tushare import _TUSHARE_DATASETS  # noqa: E402
from quant_data.backends.tushare_catalog import (  # noqa: E402
    DisclosureSemantics,
    EventSemantics,
    MembershipSemantics,
)
from quant_data.initialize import (  # noqa: E402
    clickhouse_dataset_specs,
    tushare_dataset_specs,
)


INITIALIZATION_API = (
    "quant_data.initialize.clickhouse_dataset_specs",
    "quant_data.initialize.tushare_dataset_specs",
    "quant_data.initialize.registered_dataset_names",
    "quant_data.initialize.initialize_data_client",
    "quant_data.initialize.initialize",
)

EXTENSION_API = (
    "quant_data.models.RegisteredDataset",
    "quant_data.models.DatasetContract",
    "quant_data.models.PriceAdjustment",
    "quant_data.models.DataQuery",
    "quant_data.models.QueryAudit",
    "quant_data.backends.base.DataBackend",
    "quant_data.backends.DuckDBParquetBackend",
    "quant_data.backends.ClickHouseBackend",
    "quant_data.backends.TushareBackend",
    "quant_data.backends.clickhouse.ClickHouseSource",
    "quant_data.backends.tushare_catalog.TushareDatasetCatalog",
    "quant_data.backends.tushare_catalog.TushareApiRoute",
    "quant_data.backends.tushare_catalog.DisclosureSemantics",
    "quant_data.backends.tushare_catalog.MembershipSemantics",
    "quant_data.backends.tushare_catalog.EventSemantics",
    "quant_data.backends.tushare_catalog.PeriodQuery",
    "quant_data.backends.tushare_catalog.DateRangeQuery",
    "quant_data.backends.tushare_catalog.UnboundedQuery",
    "quant_data.backends.tushare_catalog.MembershipQuery",
    "quant_data.backends.tushare.TushareSource",
    "quant_data.transforms.build_panels",
    "quant_data.transforms.build_daily_panels",
    "quant_data.audit.AuditWriter",
)

FAMILY_LABELS = {
    "minghu_daily": "明湖股票日线",
    "minghu_index_daily": "明湖指数日线",
    "minghu_m1": "明湖一分钟线",
    "minghu_tk": "明湖盘口快照",
    "minghu_zb": "明湖逐笔事件",
    "income": "Tushare 利润表",
    "balancesheet": "Tushare 资产负债表",
    "cashflow": "Tushare 现金流量表",
    "fina_indicator": "Tushare 财务指标",
    "express": "Tushare 业绩快报",
    "forecast": "Tushare 业绩预告",
    "stk_holdernumber": "Tushare 股东人数",
    "industry_member": "Tushare 行业成分",
    "stk_holdertrade": "Tushare 股东增减持",
}

COMMON_FIELD_DESCRIPTIONS = {
    "ts_code": "带交易所后缀的证券代码。",
    "code": "证券代码；内置明湖数据返回时自动补交易所后缀。",
    "date": "交易日期。",
    "date_time": "业务时间戳。",
    "ann_date": "公告日期。",
    "f_ann_date": "实际披露日期。",
    "end_date": "报告期或统计截止日期。",
    "begin_date": "事件开始日期。",
    "close_date": "事件结束日期。",
    "in_date": "成分纳入日期。",
    "out_date": "成分移出日期；空值表示仍然有效。",
    "update_flag": "Tushare 更新或修订标记。",
    "report_type": "报告类型。",
    "comp_type": "公司类型。",
    "end_type": "报告期类型。",
    "is_new": "当前成分与历史成分标记。",
}


class SyncError(RuntimeError):
    """Raised when handwritten metadata disagrees with code catalogs."""


@dataclass
class FieldFamily:
    """Collected schema family used to render the shared field reference."""

    name: str
    backend: str
    fields: tuple[tuple[str, str], ...]
    datasets: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    time_keys: set[str] = field(default_factory=set)
    instrument_keys: set[str] = field(default_factory=set)
    identity_columns: set[str] = field(default_factory=set)


def _tushare_family(dataset_name: str) -> str:
    if dataset_name in {"ci_index_member", "index_member_all"}:
        return "industry_member"
    return dataset_name


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def collect_families() -> dict[str, FieldFamily]:
    """Collect schema families without constructing any remote client."""

    families: dict[str, FieldFamily] = {}
    for clickhouse_spec in clickhouse_dataset_specs():
        columns = MINGHU_TABLE_COLUMN_TYPES.get(clickhouse_spec.table)
        if columns is None:
            raise SyncError(
                f"Default ClickHouse table {clickhouse_spec.table!r} has no local catalog"
            )
        family = FieldFamily(
            name=clickhouse_spec.name,
            backend="ClickHouse",
            fields=columns,
            datasets=[clickhouse_spec.name],
            sources=[clickhouse_spec.table],
            time_keys={clickhouse_spec.time_column},
            instrument_keys={clickhouse_spec.instrument_column},
        )
        families[family.name] = family

    for tushare_spec in tushare_dataset_specs():
        dataset_name = tushare_spec.dataset or tushare_spec.name
        catalog = _TUSHARE_DATASETS.get(dataset_name)
        if catalog is None:
            raise SyncError(
                f"Default Tushare dataset {dataset_name!r} has no local catalog"
            )
        family_name = _tushare_family(dataset_name)
        fields = tuple((item.name, str(item.type)) for item in catalog.schema)
        semantics = catalog.semantics
        if isinstance(semantics, DisclosureSemantics):
            time_column = semantics.period_column
        else:
            time_column = semantics.table_time_column
        existing = families.get(family_name)
        if existing is None:
            existing = FieldFamily(family_name, "Tushare", fields)
            families[family_name] = existing
        elif existing.fields != fields:
            raise SyncError(
                f"Tushare schema family {family_name!r} has inconsistent field definitions"
            )
        _append_unique(existing.datasets, tushare_spec.name)
        for route in catalog.routes:
            _append_unique(existing.sources, route.api_name)
        existing.time_keys.add(time_column)
        existing.instrument_keys.add(catalog.instrument_column)
        existing.identity_columns.update(semantics.identity_columns)
    return families


def load_and_validate_notes(
    families: dict[str, FieldFamily],
) -> dict[str, dict[str, Any]]:
    """Validate handwritten dataset names, field names, and field types."""

    path = DOCS / "datasets" / "field_notes.toml"
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    notes = raw.get("families")
    if not isinstance(notes, dict):
        raise SyncError("field_notes.toml must define a [families] table")

    missing_families = set(families).difference(notes)
    unknown_families = set(notes).difference(families)
    if missing_families or unknown_families:
        raise SyncError(
            "field_notes.toml family mismatch: "
            f"missing={sorted(missing_families)}, unknown={sorted(unknown_families)}"
        )

    for name, family in families.items():
        note = notes[name]
        if not isinstance(note, dict):
            raise SyncError(f"Handwritten family {name!r} must be a table")
        declared_datasets = note.get("datasets")
        if not isinstance(declared_datasets, list) or not all(
            isinstance(item, str) for item in declared_datasets
        ):
            raise SyncError(f"Handwritten family {name!r} must list dataset names")
        if set(declared_datasets) != set(family.datasets):
            raise SyncError(
                f"Dataset names for family {name!r} are stale: "
                f"documented={sorted(declared_datasets)}, "
                f"catalog={sorted(family.datasets)}"
            )

        catalog_types = dict(family.fields)
        field_notes = note.get("fields", {})
        if not isinstance(field_notes, dict):
            raise SyncError(f"Handwritten fields for family {name!r} must be a table")
        for field_name, field_note in field_notes.items():
            if field_name not in catalog_types:
                raise SyncError(
                    f"Unknown handwritten field {field_name!r} in family {name!r}"
                )
            if not isinstance(field_note, dict):
                raise SyncError(f"Handwritten field {name}.{field_name} must be a table")
            documented_type = field_note.get("type")
            if documented_type != catalog_types[field_name]:
                raise SyncError(
                    f"Type drift for {name}.{field_name}: documented={documented_type!r}, "
                    f"catalog={catalog_types[field_name]!r}"
                )
            description = field_note.get("description")
            if not isinstance(description, str) or not description.strip():
                raise SyncError(
                    f"Handwritten field {name}.{field_name} needs a description"
                )
    return notes


def _autosummary(objects: tuple[str, ...] | list[str]) -> list[str]:
    return [
        ".. autosummary::",
        "   :toctree: generated",
        "",
        *(f"   {item}" for item in objects),
    ]


def render_api_index() -> str:
    public_objects = [f"quant_data.{name}" for name in quant_data.__all__]
    lines = [
        ".. Generated by docs/_scripts/sync_reference.py; do not edit.",
        "",
        "自动 API 清单",
        "=============",
        "",
        "本页从 ``quant_data.__all__``、显式初始化辅助函数和稳定扩展点生成。",
        "对象页由 Sphinx ``autosummary`` 在构建时生成。",
        "",
        "包根公开 API",
        "-------------",
        "",
        *_autosummary(public_objects),
        "",
        "初始化辅助函数",
        "--------------",
        "",
        *_autosummary(INITIALIZATION_API),
        "",
        "核心扩展点",
        "----------",
        "",
        *_autosummary(EXTENSION_API),
        "",
    ]
    return "\n".join(lines)


def _escape_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_capability_matrix() -> str:
    rows: list[list[object]] = []
    for clickhouse_spec in clickhouse_dataset_specs():
        columns = dict(MINGHU_TABLE_COLUMN_TYPES[clickhouse_spec.table])
        requires_range = bool(
            clickhouse_spec.require_time_range is True
            or (
                clickhouse_spec.require_time_range is None
                and clickhouse_spec.partition_column is not None
            )
        )
        universe = "可选"
        if clickhouse_spec.instrument_column == "code" and "exg" in columns:
            universe = "可选；须带交易所后缀"
        if clickhouse_spec.name == "minghu_daily":
            semantics = "普通行情；价格默认后复权"
        elif clickhouse_spec.panel_compatible:
            semantics = "普通行情"
        else:
            semantics = "事件长表"
        rows.append(
            [
                clickhouse_spec.name,
                f"ClickHouse `{clickhouse_spec.table}`",
                clickhouse_spec.time_column,
                clickhouse_spec.instrument_column,
                "必须" if requires_range else "可选",
                universe,
                "是" if clickhouse_spec.panel_compatible else "否",
                semantics,
            ]
        )

    for tushare_spec in tushare_dataset_specs():
        dataset_name = tushare_spec.dataset or tushare_spec.name
        catalog = _TUSHARE_DATASETS[dataset_name]
        catalog_semantics = catalog.semantics
        has_split_routes = {route.universe for route in catalog.routes} == {
            "instrument_only",
            "whole_market",
        }
        universe = (
            "可选；列表走普通 API，`None` 走 VIP"
            if has_split_routes
            else "可选；`None` 为全市场"
        )
        if isinstance(catalog_semantics, DisclosureSemantics):
            time_column = (
                f"表 `{catalog_semantics.period_column}`；"
                f"宽表 `{catalog_semantics.panel_time_column}`"
            )
            range_label = "表可选；宽表必须"
            panel_compatible = True
            semantics = "原始修订长表；宽表自动按交易日构建 PIT 状态"
        elif isinstance(catalog_semantics, MembershipSemantics):
            time_column = (
                f"表 `{catalog_semantics.table_time_column}`；"
                f"宽表 `{catalog_semantics.panel_time_column}`"
            )
            range_label = "必须"
            panel_compatible = True
            semantics = "表返回成员区间；宽表才按交易日展开"
        elif isinstance(catalog_semantics, EventSemantics):
            time_column = catalog_semantics.table_time_column
            range_label = "必须"
            panel_compatible = False
            semantics = "事件长表"
        else:  # pragma: no cover - exhaustive catalog guard
            raise SyncError(f"Unknown Tushare semantics for {dataset_name!r}")
        rows.append(
            [
                tushare_spec.name,
                "Tushare " + ", ".join(
                    f"`{route.api_name}`" for route in catalog.routes
                ),
                time_column,
                catalog.instrument_column,
                range_label,
                universe,
                "是" if panel_compatible else "否",
                semantics,
            ]
        )

    lines = [
        "<!-- Generated by docs/_scripts/sync_reference.py; do not edit. -->",
        "",
        "# 默认数据集能力矩阵",
        "",
        "本页直接读取初始化规格和本地后端 catalog；生成过程不会创建远程客户端或读取凭证。",
        "时间范围均为闭区间。披露数据的 `get_panel()` 自动执行 PIT；`get_table()` 保留公告和修订记录。",
        "",
        "| 数据集 | 来源 | 时间键 | 证券键 | 时间范围 | 股票池 | 宽表 | 语义 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend("| " + " | ".join(_escape_cell(item) for item in row) + " |" for row in rows)
    lines.append("")
    return "\n".join(lines)


def _description_for(
    family_name: str,
    field_name: str,
    notes: dict[str, dict[str, Any]],
) -> str:
    field_note = notes[family_name].get("fields", {}).get(field_name)
    if isinstance(field_note, dict):
        return str(field_note["description"])
    if field_name in COMMON_FIELD_DESCRIPTIONS:
        return COMMON_FIELD_DESCRIPTIONS[field_name]
    if field_name.startswith("bidv") and field_name[4:].isdigit():
        return f"买 {field_name[4:]} 档委托量。"
    if field_name.startswith("askv") and field_name[4:].isdigit():
        return f"卖 {field_name[4:]} 档委托量。"
    if field_name.startswith("bid") and field_name[3:].isdigit():
        return f"买 {field_name[3:]} 档价格。"
    if field_name.startswith("ask") and field_name[3:].isdigit():
        return f"卖 {field_name[3:]} 档价格。"
    return "—"


def render_field_reference(
    families: dict[str, FieldFamily], notes: dict[str, dict[str, Any]]
) -> str:
    lines = [
        "<!-- Generated by docs/_scripts/sync_reference.py; do not edit. -->",
        "",
        "# 字段手册",
        "",
        "字段名和类型来自 ClickHouse/Tushare 本地 catalog；说明来自经同步脚本校验的",
        "`field_notes.toml`。普通与 VIP 只是同一逻辑数据集的远程路由，共用字段表。",
        "表键与表身份列由 `get_table()` 自动返回；身份列仍可作为 `get_panel()` 的值字段。",
        "",
    ]
    for name, family in families.items():
        note = notes[name]
        label = FAMILY_LABELS.get(name, name)
        lines.extend(
            [
                f"## `{name}`：{label}",
                "",
                str(note.get("summary", "")),
                "",
                f"- 数据集：{', '.join(f'`{item}`' for item in family.datasets)}",
                f"- 来源：{family.backend} {', '.join(f'`{item}`' for item in family.sources)}",
                "",
                "| 字段 | 类型 | 角色 | 说明 |",
                "| --- | --- | --- | --- |",
            ]
        )
        keys = family.time_keys | family.instrument_keys
        for field_name, field_type in family.fields:
            if field_name in keys:
                role = "自动键列"
            elif field_name in family.identity_columns:
                role = "表自动身份列"
            else:
                role = "可请求字段"
            description = _description_for(name, field_name, notes)
            lines.append(
                "| "
                + " | ".join(
                    _escape_cell(item)
                    for item in (
                        f"`{field_name}`",
                        f"`{field_type}`",
                        role,
                        description,
                    )
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def expected_outputs() -> dict[Path, str]:
    families = collect_families()
    notes = load_and_validate_notes(families)
    return {
        DOCS / "api" / "public.rst": render_api_index(),
        DOCS / "datasets" / "capabilities.md": render_capability_matrix(),
        DOCS / "datasets" / "fields.md": render_field_reference(families, notes),
    }


def sync(*, check: bool) -> int:
    outputs = expected_outputs()
    stale: list[Path] = []
    for path, content in outputs.items():
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        stale.append(path)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale and check:
        for path in stale:
            print(f"stale generated documentation: {path.relative_to(ROOT)}", file=sys.stderr)
        print(
            "run: python docs/_scripts/sync_reference.py",
            file=sys.stderr,
        )
        return 1
    action = "checked" if check else "updated"
    print(f"{action} {len(outputs)} generated documentation files")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when generated pages differ instead of writing them",
    )
    args = parser.parse_args()
    try:
        return sync(check=args.check)
    except (OSError, SyncError, tomllib.TOMLDecodeError) as exc:
        print(f"documentation synchronization failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
