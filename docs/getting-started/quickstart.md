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

Tushare schema 与查询语义由本地逻辑 catalog 提供。添加连接和注册都不会读取 token 或
初始化远程客户端：

```python
from quant_data import DataClient, TushareConfig, TushareDatasetSpec

data = DataClient()
data.add_tushare_connection(
    "tushare",
    TushareConfig(token_env="TUSHARE_TOKEN"),
)
data.register(
    TushareDatasetSpec(
        name="income",
        connection="tushare",
    )
)

raw = data.get_table(
    "income",
    ["total_revenue"],
    start="2025-03-31",
    end="2025-12-31",
    instruments=["600000.SH"],
)

pit = data.get_panel(
    "income",
    ["total_revenue"],
    start="2026-01-01",
    end="2026-03-31",
    instruments=None,
)
```

`get_table()` 保留公告和修订长表；`get_panel()` 自动按公告与交易日历构造 PIT 日频宽表。
显式股票池走普通 API，`instruments=None` 自动走同一逻辑数据集的 VIP 全市场路由。
详细规则见 [Tushare 后端](../backends/tushare.md)。

### 本地 Tushare 归档

同步目录包含每个逻辑数据集的 `_manifest.json` 时，可以用同一套查询 API 读取本地
Parquet，仅把交易日历留给远程连接：

```python
from quant_data import DataClient, TushareConfig, TushareParquetDatasetSpec

data = DataClient()
data.add_tushare_connection("calendar", TushareConfig(token_env="TUSHARE_TOKEN"))
data.register(
    TushareParquetDatasetSpec(
        name="income",
        data_dir="/Users/wtx/Sync/Quant/quant_data_infra/tushare/data",
        calendar_connection="calendar",
    )
)
```

`get_table()` 不读取 token；`get_panel()` 只调用 `trade_cal`，不会调用 `income` 或
`income_vip`。显式日期越过 manifest 范围会报错，财报表缺失的边界使用 manifest 边界。
PIT 的 `start - fetch_buffer_days` 也必须位于归档内，以保证左边界 carry-in 完整。
`income`、`balancesheet`、`cashflow` 在未指定固定参数时与 Tushare API 一样默认使用
`report_type=1`；需要单季报表时显式注册 `fixed_params={"report_type": "2"}`。

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
