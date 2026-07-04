# quant_data

`quant_data` 是一个面向量化研究的统一数据访问框架，支持本地 Parquet、远程 ClickHouse 和 Tushare。它把不同来源的长表数据转换为因子研究常用的 `time × instrument` 宽表，同时也能直接返回适合逐笔数据的 PyArrow 长表。

框架适合以下场景：

- 本地保存了日线、分钟线、行情、基本面或因子 Parquet 文件；
- 需要从 Tushare 拉取财务报表等基础数据；
- 需要按字段、时间区间和股票池批量查询；
- 希望一次读取多个字段，并得到 Pandas 宽表；
- 需要记录数据文件、查询条件和结果尺寸，保证研究过程可追踪。

## 环境安装

项目要求 Python 3.11 或更高版本。仓库当前使用名为 `quant_data` 的 Conda 环境：

在 pyproject.toml 所在目录下运行以下命令
```bash
conda activate quant_data
python -m pip install -e .
```
即可创建软连接。

如需使用远程后端，可以按需安装可选依赖：

```bash
python -m pip install -e ".[clickhouse]"
python -m pip install -e ".[tushare]"
```

可以用
```bash
conda list | grep quant-data
```
检查是否安装成功。

## 数据注册
### 注册本地parquet数据

#### Parquet 数据要求

数据应采用长表结构，每一行代表某个时间点的一只证券：

| time | ts_code | open | close | volume |
| --- | --- | ---: | ---: | ---: |
| 2026-01-05 | 000001.SZ | 10.10 | 10.32 | 1200000 |
| 2026-01-05 | 000002.SZ | 11.20 | 11.18 | 950000 |

基本约束：

- 必须存在时间列和证券代码列，列名可以在注册时配置；
- 同一数据集的每个文件都必须包含这两个主键列；
- `(time, instrument)` 组合必须唯一，重复数据会直接报错；
- 主键不能为 null；
- 时间列必须能被 DuckDB 转换为 timestamp；
- 多个 Parquet 文件的同名字段类型必须能够兼容合并。

字段值允许缺失。框架不会执行 `fillna`、`ffill` 或 `bfill`。

#### 注册示例

```python
data = DataClient(audit_dir=".quant_data/audit") ## 此路径用于储存追溯查询历史的文件，见下面“追溯设计“一节

data.register(
    DatasetSpec(
        name="daily_bar",
        paths=["./data/daily/*.parquet"],
        time_column="date",
        instrument_column="code",
        frequency="1d",
        timezone="Asia/Shanghai",
        version="2026-06",
    )
)
```

#### 数据路径写法

`DatasetSpec.paths` 支持文件、目录和 glob，也可以一次注册多个位置：

```python
# 单个文件
paths=["/data/daily/2026.parquet"]

# 目录：递归查找目录下所有 .parquet 文件
paths=["/data/daily"]

# glob
paths=["/data/daily/2026-*.parquet"]

# 多个文件或目录
paths=["/data/daily/2025.parquet", "/data/daily/2026"]
```

路径会在注册时解析为绝对路径并稳定排序。没有匹配到 Parquet 文件时，注册会失败。


### 注册远程 ClickHouse 数据库

使用前先设置环境变量
```bash
conda env config vars set MINGHU_CLICKHOUSE_PASSWORD='<password>'
```
设置一次即可，以后激活环境会自动设置。可以用
```bash
echo $MINGHU_CLICKHOUSE_PASSWORD
```
检查。


连接并注册明湖汇数据库的三张表：

```python
from quant_data import ClickHouseConfig, ClickHouseDatasetSpec, DataClient

data = DataClient(audit_dir=".quant_data/audit")
data.add_clickhouse_connection(
    "minghu",
    ClickHouseConfig(
        host="chdb.tradegdb.com",
        port=8123,
        username="your-username",
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
data.register(
    ClickHouseDatasetSpec(
        name="minghu_m1",
        connection="minghu",
        table="stock_base.m1",
        time_column="date_time",
        partition_column="date",
        order_columns=("date_time", "code"),
        frequency="1min",
    )
)
data.register(
    ClickHouseDatasetSpec(
        name="minghu_zb",
        connection="minghu",
        table="stock_base.zb",
        time_column="date_time",
        partition_column="date",
        order_columns=("date_time", "code", "seqno"),
        panel_compatible=False,
    )
)
```

日线和分钟线可以直接构建宽表：

```python
panels = data.get_panel(
    "minghu_m1",
    fields=["close", "volume"],
    start="2026-03-02 09:30:00",
    end="2026-03-02 10:00:00",
    instruments=["000001"],
)
close = panels["close"]
```

明湖日线原始价格没有复权。框架识别 `stock_base.daily` 的 `hfq` 后复权因子，默认按以下公式返回复权价格：

```text
复权价格 = 原始价格 × hfq
```

默认复权字段包括 `open`、`high`、`low`、`close`、`pclose`、`ztprice`、`dtprice`、`omax_op` 和 `omin_op`。成交量、成交额、涨跌额和涨跌幅保持数据库原值。

获取原始未复权价格时显式传入 `adjusted=False`：

```python
raw = data.get_panel(
    "minghu_daily",
    fields=["close", "volume"],
    start="2026-03-02",
    end="2026-03-06",
    adjusted=False,
)
```

`get_table` 使用相同参数和默认规则：

```python
adjusted_table = data.get_table(
    "minghu_daily",
    fields=["open", "close", "hfq"],
    start="2026-03-02",
    end="2026-03-06",
)
```

`hfq` 只会在内部按需读取；调用者没有请求该字段时，它不会出现在结果中。因子为 null 时复权价格同样为 null，框架不会把缺失因子隐式填为 1。

分钟和逐笔数据必须同时提供 `start` 和 `end`。框架还会把时间范围转换成 `date` 条件下推，减少 ClickHouse 分区扫描。

逐笔数据可能在相同毫秒内存在多条事件，因此只能通过 `get_table` 查询：

```python
ticks = data.get_table(
    "minghu_zb",
    fields=["price", "volume", "side", "seqno"],
    start="2026-03-02 09:30:00",
    end="2026-03-02 09:30:01",
    instruments=["000001"],
    limit=100_000,
)

print(ticks.schema)
tick_df = ticks.to_pandas()
```

`get_table` 同样支持 Parquet，返回值始终为 `pyarrow.Table`。它自动包含时间列和证券列，不对重复时间事件做聚合。ClickHouse 中的 `code` 保持数据库原值，不自动添加 `.SZ`、`.SH` 或 `.BJ` 后缀。

使用结束后关闭远程连接，也可以直接使用上下文管理器：

```python
with DataClient() as data:
    data.add_clickhouse_connection(...)
    # 注册和查询
```

返回值始终是 `dict[str, pandas.DataFrame]`。即使只查询一个字段，也需要通过字段名获取：

```python
result = data.get_panel("daily_bar", fields=["close"])
close = result["close"]
```

宽表结构如下：

```text
ts_code     000001.SZ  000002.SZ
time
2026-01-05      10.32      11.18
2026-01-06      10.41       <NA>
```


### 注册 Tushare 数据

Tushare 后端用于直接访问 Tushare Pro API。当前内置 `income` /
`income_vip`、`balancesheet` / `balancesheet_vip`、`cashflow` /
`cashflow_vip` 财务报表字段，以及 `fina_indicator` /
`fina_indicator_vip` 财务指标字段、`express` / `express_vip` 业绩快报字段、
`forecast` / `forecast_vip` 业绩预告字段，不要求研究代码手动声明输出 schema。

使用前先设置 Tushare token：

```bash
conda env config vars set TUSHARE_TOKEN='<token>'
```

连接并注册财务数据：

```python
from quant_data import DataClient, TushareConfig, TushareDatasetSpec

data = DataClient(audit_dir=".quant_data/audit")
data.add_tushare_connection(
    "tushare",
    TushareConfig(token_env="TUSHARE_TOKEN"),
)

for name, api_name in {
    "income": "income_vip",
    "balancesheet": "balancesheet_vip",
    "cashflow": "cashflow_vip",
    "fina_indicator": "fina_indicator_vip",
    "express": "express_vip",
    "forecast": "forecast_vip",
}.items():
    data.register(
        TushareDatasetSpec(
            name=name,
            connection="tushare",
            api_name=api_name,
            frequency="q",
        )
    )
```

这些财务数据默认以报告期 `end_date` 作为时间索引，以 `ts_code` 作为证券列。
`start` 和 `end` 会被转换为闭区间内的季度末 `period`，逐期调用 Tushare。
VIP 接口在 `instruments=None` 时不传 `ts_code`，获取全市场数据。

```python
panels = data.get_panel(
    "income",
    fields=["basic_eps", "total_revenue", "n_income_attr_p"],
    start="2018-01-01",
    end="2018-12-31",
)
basic_eps = panels["basic_eps"]
```

资产负债表、现金流量表、财务指标、业绩快报和业绩预告同样可以直接生成宽表：

```python
balance_panels = data.get_panel(
    "balancesheet",
    fields=["total_assets", "total_liab", "total_hldr_eqy_inc_min_int"],
    start="2018-01-01",
    end="2018-12-31",
)

cashflow_panels = data.get_panel(
    "cashflow",
    fields=["n_cashflow_act", "free_cashflow", "n_incr_cash_cash_equ"],
    start="2018-01-01",
    end="2018-12-31",
)

indicator_panels = data.get_panel(
    "fina_indicator",
    fields=["eps", "roe", "debt_to_assets"],
    start="2018-01-01",
    end="2018-12-31",
)

express_panels = data.get_panel(
    "express",
    fields=["revenue", "n_income", "diluted_eps"],
    start="2018-01-01",
    end="2018-12-31",
)

forecast_panels = data.get_panel(
    "forecast",
    fields=["type", "p_change_min", "p_change_max"],
    start="2018-01-01",
    end="2018-12-31",
)
```

如果传入股票池，Tushare 后端会按股票逐只调用：

```python
table = data.get_table(
    "balancesheet",
    fields=["total_assets", "total_liab"],
    start="2018-03-31",
    end="2018-03-31",
    instruments=["600000.SH", "000001.SZ"],
)
```

普通 `income` / `balancesheet` / `cashflow` / `fina_indicator` / `express` /
`forecast` 接口按 Tushare 文档要求必须传入 `instruments`，后端会按
`period × ts_code` 调用；需要按季度全市场获取时，应注册对应的 `_vip` 接口。
VIP 接口也可以传入股票池，此时仍会逐只调用。

财务数据同一只股票同一报告期可能存在多条记录。财务报表后端会按
`f_ann_date`、`ann_date`、`update_flag` 降序保留最新记录；财务指标会按
`ann_date`、`update_flag` 降序保留最新记录；业绩快报和业绩预告会按公告日
保留最新记录，使结果可以直接构建 `end_date × ts_code` 宽表。审计记录只保存
后端名称、连接名、API 名称、schema 哈希和固定参数，不记录 token。

如果要把财务数据用作实盘可得的因子输入，启用
`panel_mode="pit_daily"`。此模式只影响 `get_panel`：后端按公告日期拉取
disclosure events，财务报表内部使用 `f_ann_date`，财务指标、业绩快报和
业绩预告使用 `ann_date`，再结合交易日历和默认 T+1 延迟构造日频宽表；
`get_table` 仍返回普通查询结果。

```python
data.register(
    TushareDatasetSpec(
        name="balancesheet_factor",
        connection="tushare",
        api_name="balancesheet",
        panel_mode="pit_daily",
        frequency="d",
    )
)

factor_panels = data.get_panel(
    "balancesheet_factor",
    fields=["total_assets", "total_liab"],
    start="2018-01-01",
    end="2018-12-31",
    instruments=["600000.SH", "000004.SZ"],
)
```

`pit_daily` 需要传入 `instruments`，并且应使用 `income`、`balancesheet`、
`cashflow`、`fina_indicator`、`express` 或 `forecast` 普通接口；如果要在
`instruments=None` 时生成全市场日频面板，应注册对应的 `_vip` 接口。

```python
data.register(
    TushareDatasetSpec(
        name="balancesheet_factor_all",
        connection="tushare",
        api_name="balancesheet_vip",
        panel_mode="pit_daily",
        frequency="d",
    )
)

all_factor_panels = data.get_panel(
    "balancesheet_factor_all",
    fields=["total_assets", "total_liab"],
    start="2018-01-01",
    end="2018-12-31",
    instruments=None,
)
```

中信行业成分接口 `ci_index_member` 和申万行业成分接口 `index_member_all`
也可以注册成日频面板。后端会拉取 `in_date` / `out_date` 成分区间，
按交易日历展开为内部 `date × ts_code` 长表，再由 `get_panel` 返回宽表；
注册时不需要手动声明 schema 或时间列。

```python
data.register(
    TushareDatasetSpec(
        name="citic_industry",
        connection="tushare",
        api_name="ci_index_member",
    )
)

industry_panels = data.get_panel(
    "citic_industry",
    fields=["l1_name", "l2_name", "l3_name"],
    start="2024-01-01",
    end="2024-12-31",
    instruments=["600000.SH", "000004.SZ"],
)
```

也可以通过 `fixed_params` 固定行业代码，获取某个中信行业的成分宽表；
`instruments=None` 时不会传 `ts_code`。

```python
data.register(
    TushareDatasetSpec(
        name="citic_electronics",
        connection="tushare",
        api_name="ci_index_member",
        fixed_params={"l2_code": "CI005835.CI"},
    )
)

member_panels = data.get_panel(
    "citic_electronics",
    fields=["l3_name"],
    start="2024-01-01",
    end="2024-12-31",
    instruments=None,
)
```

申万行业成分用法相同，只需把 `api_name` 换成 `index_member_all`。

```python
data.register(
    TushareDatasetSpec(
        name="sw_industry",
        connection="tushare",
        api_name="index_member_all",
    )
)

sw_panels = data.get_panel(
    "sw_industry",
    fields=["l1_name", "l2_name", "l3_name"],
    start="2024-01-01",
    end="2024-12-31",
    instruments=["600000.SH", "000004.SZ"],
)

data.register(
    TushareDatasetSpec(
        name="sw_gold_members",
        connection="tushare",
        api_name="index_member_all",
        fixed_params={"l3_code": "850531.SI"},
    )
)

sw_member_panels = data.get_panel(
    "sw_gold_members",
    fields=["l3_name"],
    start="2024-01-01",
    end="2024-12-31",
    instruments=None,
)
```


## 查询规则

### 时间范围

`start` 和 `end` 都是闭区间，可以只提供一端：

```python
data.get_panel("daily_bar", ["close"], start="2026-01-01")
data.get_panel("daily_bar", ["close"], end="2026-03-31")
```

对于包含日内时间的数据，`end="2026-03-31"` 表示 `2026-03-31 00:00:00`。如需包含当天全部分钟数据，应传入明确的结束时间，例如：

```python
end="2026-03-31 23:59:59.999999"
```

### 股票池

```python
# 查询全部证券，列按证券代码升序
data.get_panel("daily_bar", ["close"], instruments=None)

# 按请求顺序返回列
data.get_panel(
    "daily_bar",
    ["close"],
    instruments=["600000.SH", "000001.SZ"],
)

# 空股票池：返回空宽表
data.get_panel("daily_bar", ["close"], instruments=[])
```

请求的证券没有数据时，该证券仍保留在结果列中，值为缺失值。

### 多字段查询

多个字段在一次 DuckDB 扫描中读取，避免逐字段、逐股票访问文件：

```python
panels = data.get_panel(
    "daily_bar",
    fields=["open", "high", "low", "close", "volume"],
)

returns = panels["close"].pct_change()
```

字段不能为空、不能重复，也不能包含配置的时间列或证券代码列。

## 追溯设计

每次 `get_panel` 调用都会生成一个 UUID，并写入：

```text
.quant_data/audit/YYYY-MM-DD/<query_id>.json
```

审计内容包括：

- 数据集名称、频率和版本；
- Parquet 文件路径、大小和 `mtime_ns`，脱敏后的 ClickHouse host、表名与 schema 哈希，或 Tushare API 与 schema 哈希；
- 字段、时间区间和股票池；
- 查询开始时间、耗时、成功或失败状态；
- 每个字段的结果尺寸和失败异常；
- 实际是否复权、未进行交易日历对齐的标记。

返回的每张 DataFrame 也包含查询元数据：

```python
panel = panels["close"]
print(panel.attrs)

# {
#   "query_id": "...",
#   "dataset": "daily_bar",
#   "frequency": "1d",
#   "version": "2026-06",
#   "parameters": {...},
# }
```

审计文件无法写入时查询会失败，因此 `audit_dir` 必须具有写权限。

## 常见异常

```python
from quant_data import (
    DatasetNotFoundError,
    DatasetRegistrationError,
    DuplicateObservationError,
    FieldNotFoundError,
    InvalidQueryError,
    SchemaMismatchError,
)
```

| 异常 | 常见原因 |
| --- | --- |
| `DatasetRegistrationError` | 路径无匹配文件、缺少主键列、Backend 或 Tushare API 不支持 |
| `DatasetNotFoundError` | 查询了尚未注册的数据集名称 |
| `FieldNotFoundError` | 请求字段不在 Parquet schema 中 |
| `InvalidQueryError` | 字段重复、时间倒置、股票代码为空等 |
| `SchemaMismatchError` | 文件 schema 不兼容、时间无法转换、主键为 null |
| `DuplicateObservationError` | 同一时间和证券存在多行 |

真实数据首次接入时，可以先做一个小范围查询并查看字段类型：

```python
try:
    sample = data.get_panel(
        "daily_bar",
        fields=["close"],
        start="2026-01-01",
        end="2026-01-05",
        instruments=["000001.SZ"],
    )
    print(sample["close"].dtypes)
except Exception as exc:
    print(type(exc).__name__, exc)
```
