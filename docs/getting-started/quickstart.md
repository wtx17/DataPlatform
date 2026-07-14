# 手工注册快速上手

## 本地 Parquet

Parquet 数据应为长表：每行是一只证券在一个时间点的一条观测。每个文件都必须包含
配置的时间列和证券列，两个键都不能为 null；只有 `(time, instrument)` 唯一的数据
才能生成宽表。

```python
from quant_data import DataClient, DatasetSpec

data = DataClient(audit_dir=".quant_data/audit")
data.register(
    DatasetSpec(
        name="daily_bar",
        paths=["data/daily/*.parquet"],
        time_column="date",
        instrument_column="ts_code",
        frequency="1d",
        timezone="Asia/Shanghai",
        version="2026-07",
    )
)

panels = data.get_panel(
    "daily_bar",
    fields=["close", "volume"],
    start="2026-07-01",
    end="2026-07-10",
    instruments=["600000.SH", "000001.SZ"],
)
close = panels["close"]
```

`paths` 可以是单个文件、目录、glob 或多个位置。目录会递归查找 `.parquet`；解析后的
绝对路径稳定排序。注册阶段会读取 schema，但不会读取完整数据列。

## ClickHouse

先添加连接，再注册表。内置明湖表使用本地 schema catalog，下面的注册不会创建连接：

```python
from quant_data import ClickHouseConfig, ClickHouseDatasetSpec, DataClient

data = DataClient()
data.add_clickhouse_connection(
    "minghu",
    ClickHouseConfig(
        host="chdb.tradegdb.com",
        username="researcher",
        password_env="MINGHU_CLICKHOUSE_PASSWORD",
    ),
)
data.register(
    ClickHouseDatasetSpec(
        name="minghu_daily",
        connection="minghu",
        table="stock_base.daily",
        time_column="date",
        frequency="1d",
    )
)
```

自定义表不在 catalog 中，注册时会执行 `DESCRIBE TABLE`。因此自定义表注册需要可用凭证
和网络，而五张默认明湖表直到首次查询才连接。

## Tushare

Tushare schema 由本地 catalog 提供。当前实现会在注册时初始化 Tushare 客户端，但不会
发起数据 API 查询：

```python
from quant_data import DataClient, TushareConfig, TushareDatasetSpec

data = DataClient()
data.add_tushare_connection(
    "tushare",
    TushareConfig(token_env="TUSHARE_TOKEN"),
)
data.register(
    TushareDatasetSpec(
        name="income_vip",
        connection="tushare",
        api_name="income_vip",
        frequency="q",
    )
)
```

普通财报接口需要股票池；相应的 `_vip` 接口允许 `instruments=None` 获取全市场报告期。
详细调用与去重规则见 [Tushare 后端](../backends/tushare.md)。

## 上下文管理器

远程客户端会缓存复用。推荐用上下文管理器保证所有后端最终关闭：

```python
with DataClient() as data:
    data.add_clickhouse_connection(...)
    data.register(...)
    table = data.get_table(...)
```

也可以显式调用 `data.close()`。Parquet 每次扫描使用短生命周期的内存 DuckDB 连接，
`close()` 对它没有额外动作。
