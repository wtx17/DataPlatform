# 特殊语义与审计

## 价格复权

内置 `stock_base.daily` catalog 包含 `hfq`，注册时自动形成 `PriceAdjustment`。默认规则为：

```text
返回价格 = 原始价格 × hfq
```

默认受影响字段为 `open`、`high`、`low`、`close`、`pclose`、`ztprice`、`dtprice`、
`omax_op`、`omin_op`。成交量、成交额、涨跌额和涨跌幅不变。

```python
adjusted = data.get_panel("minghu_daily", ["close"])
raw = data.get_panel("minghu_daily", ["close"], adjusted=False)
forced = data.get_table("minghu_daily", ["close"], adjusted=True)
```

`adjusted=None` 使用数据集默认值。只有请求到受影响价格字段时，后端才额外投影因子；
若调用者没请求 `hfq`，它在复权后从结果中移除。因子为 null 时价格也为 null，不会把
缺失因子当作 1。没有复权配置的数据集传 `adjusted=True` 会报错。

## 事件表与普通面板

`get_panel()` 是严格 pivot，不是聚合器。以下数据天然允许同一键多行：

- `minghu_tk`：同一秒内多张盘口快照；
- `minghu_zb`：同一毫秒内多条委托或成交；
- `stk_holdertrade`：同一公告日同一股票的多个股东事件。

这些规格设置 `panel_compatible=False`，客户端在远程扫描前就拒绝宽表请求。使用
`get_table()` 可保留每一行和稳定排序字段。

## Point-in-time 日频面板

Tushare `panel_mode="pit_daily"` 只改变 `get_panel()`。它不以报告期直接 pivot，而是：

1. 从 `start - fetch_buffer_days` 拉取公告事件，让开始日前已知值能够 carry in；
2. 财报用 `f_ann_date`，财务指标、快报、预告和股东人数用 `ann_date`；
3. 拉取并按月缓存交易日历；
4. 非交易日公告向后吸附到下一开市日；
5. 再增加 `disclosure_lag` 个交易日；
6. 同一可用日同一证券的多个报告期保留最新报告期；
7. 在交易日 index 上前向填充，最后裁剪到请求闭区间。

默认初始化规格的 `disclosure_lag=0`，表示公告吸附后的首个交易日即可用。若研究假设为
T+1，应在自定义 `TushareDatasetSpec` 中显式设置 `disclosure_lag=1`。

```python
from quant_data import TushareDatasetSpec

data.register(
    TushareDatasetSpec(
        name="income_factor_t1",
        connection="tushare",
        api_name="income",
        panel_mode="pit_daily",
        frequency="d",
        disclosure_lag=1,
    )
)
```

普通财报 PIT 仍要求 `instruments`；对应 `_vip` 变体可做全市场。`get_table()` 对同一规格
继续执行普通报告期查询，不进行公告日对齐或前向填充。

## 结果元数据

每张 Pandas panel 的 `attrs` 包含：

```python
{
    "query_id": "...",
    "dataset": "minghu_daily",
    "frequency": "1d",
    "version": None,
    "parameters": {"start": "...", "end": "...", "adjusted": True, ...},
    "adjusted": True,
}
```

PIT 结果额外包含 `panel_mode` 和 `disclosure_lag`。Arrow table 在 schema metadata 中保存
`quant_data.query_id`、`quant_data.dataset`、`quant_data.parameters`、
`quant_data.adjusted`。

## 审计记录

每次查询无论成功或失败，都写入：

```text
<audit_dir>/YYYY-MM-DD/<query_id>.json
```

记录包含请求字段、边界、股票池、实际复权状态、框架版本、来源 fingerprint、耗时、结果
尺寸和错误类型。Parquet fingerprint 保存文件绝对路径、大小和 `mtime_ns`；ClickHouse
保存脱敏 host、port、表、schema hash 与 catalog/remote 来源；Tushare 保存连接名、API、
schema hash 和字符串化固定参数。凭证与 ClickHouse username 不会写入。

写入过程先在目标日期目录创建临时文件，flush、`fsync` 后用 `os.replace` 原子替换。
审计不是 best effort：无法持久化时查询视为失败，从而避免返回无法追溯的研究结果。
