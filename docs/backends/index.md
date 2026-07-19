# 后端与特殊数据语义

三个后端都实现 `DataBackend` 协议：`prepare()` 产生 Arrow schema、方法级 contract 和 source descriptor，
`scan()` 接受规范化 `DataQuery`，`fingerprint()` 提供脱敏审计来源，`close()` 释放资源。

```{toctree}
:maxdepth: 1

parquet
clickhouse
tushare
```

| 后端 | 注册阶段 | 查询下推 | 主要特殊语义 |
| --- | --- | --- | --- |
| Parquet | 路径解析、逐文件键检查、schema 合并 | 字段、闭区间、股票池、排序、limit | 本地文件 fingerprint、严格唯一键 pivot |
| ClickHouse | catalog 或远程 `DESCRIBE TABLE` | 字段、时间、分区、股票池、排序、limit | 懒连接、代码后缀、明湖日线复权 |
| Tushare | 离线逻辑 catalog；查询时懒连接 | API fields/period/date/ts_code | 普通/VIP 自动路由、无损修订表、行业区间、PIT 状态机 |
