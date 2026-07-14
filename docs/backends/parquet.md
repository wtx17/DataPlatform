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
