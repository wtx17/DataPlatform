# Parquet 与 DuckDB

## 注册与 schema 合并

`DatasetSpec.paths` 支持文件、递归目录和 glob。`DuckDBParquetBackend.prepare()` 将匹配项
展开为绝对路径、去重并按字符串排序；没有 `.parquet` 文件会立即失败。

后端只读取每个文件的 Parquet footer：

1. 确认每个文件都存在 `time_column` 与 `instrument_column`；
2. 用 `pyarrow.unify_schemas(..., promote_options="permissive")` 合并字段；
3. 把统一 schema 和已解析 `Path` 元组写入 `RegisteredDataset`。

同名字段仍必须可以安全提升。无法合并时抛出 `SchemaMismatchError`，不会等到研究查询时才
暴露 schema 漂移。

## Tushare manifest 归档

`TushareParquetDatasetSpec` 让同一后端读取按逻辑数据集同步的 Tushare 归档。注册时只读取
各数据集自己的 `_manifest.json` 和 Parquet footer，不依赖归档根目录的 `_catalog.json`：

1. 校验 manifest 版本、数据集名、归档范围和 schema hash；
2. 只接受 manifest 声明且未逃逸归档根目录的分区路径；
3. 比对文件大小、footer 行数和当前 Tushare catalog 的必需字段/类型；
4. 使用当前 catalog 作为公开 schema，忽略归档里额外的字段。

本地扫描保留 Tushare 的报告期过滤、身份列、修订排序、成员区间和事件流语义。可映射的
`fixed_params` 作为参数化等值条件下推；`trade_type` 映射到 `in_de`，`enddate` 映射到
`end_date`。无法从归档列重建的参数（例如 `cashflow.is_calc`）在注册时失败，不会静默忽略。

归档为完整保存源数据，包含 `income`、`balancesheet`、`cashflow` 的全部 12 种
`report_type`；Tushare API 在省略该参数时默认返回 `report_type=1`（最新合并报表）。本地
后端会显式应用同一默认值，避免累计报表、单季报表和母公司报表进入同一个 PIT 状态。
调用者仍可通过 `fixed_params={"report_type": "2"}` 等显式值覆盖默认口径。

显式查询边界必须落在每个 manifest 的闭区间内。财报表省略的边界补为归档边界；PIT 查询
还要求向前回看的 `fetch_buffer_days` 全部位于归档内。行业成员与事件表继续要求双边范围。

## DuckDB 扫描

每次 `scan()` 打开独立的 `:memory:` DuckDB 连接，通过
`read_parquet(?, union_by_name=true)` 把所有文件作为一个长表。以下操作下推到 SQL：

- 只投影两个键与请求字段；
- 将时间键显式 `CAST(... AS TIMESTAMP)`；
- 对 `start`、`end` 使用参数化闭区间；
- 把股票池注册为 Arrow 临时关系并 inner join；
- 按时间、证券稳定排序；
- 最后应用参数化 `LIMIT`。

标识符用双引号转义，值始终作为参数或 Arrow relation 传入，因此字段名中的双引号和证券
代码中的 SQL 特殊字符不会进入可执行 SQL 结构。

## 宽表约束

DuckDB 返回 Arrow 后，客户端先检查两个键没有 null，再由 Polars 检查重复键并 pivot。
后端不做 `fillna`、`ffill` 或 `bfill`。只有调用者明确请求但没有数据的证券，才在结果中
补一个全缺失列；原始字段缺失值原样保留。

## 来源审计

每次查询重新读取每个源文件的：

- 绝对路径；
- 文件大小；
- 纳秒级修改时间。

这些值用于审计 fingerprint，不是内容哈希。需要更强内容寻址时，可以在自定义后端的
`fingerprint()` 中加入校验和，但应评估大文件的额外 I/O。

Tushare 归档的 fingerprint 还保存 manifest schema hash、更新时间、归档范围和每个分区
声明的 SHA256/行数，并重新读取当前文件大小与 `mtime_ns`。注册不会为整份归档重算哈希；
内容校验应由同步流程的 verify 命令完成。
