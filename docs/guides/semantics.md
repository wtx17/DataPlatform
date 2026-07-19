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

这些数据集的运行期 contract 设置 `panel_compatible=False`，客户端在远程扫描前就拒绝宽表请求。使用
`get_table()` 可保留每一行和稳定排序字段。

## Point-in-time 日频面板

披露型 Tushare 数据集的 `get_panel()` 自动执行 PIT，不需要 `_pit` 注册名或 mode 开关。
它不以报告期直接 pivot，而是：

1. 从 `start - fetch_buffer_days` 拉取公告事件，让开始日前已知值能够 carry in；
2. 财报用 `f_ann_date`，财务指标、快报、预告和股东人数用 `ann_date`；
3. 拉取并按月缓存交易日历；
4. 非交易日公告向后吸附到下一开市日；
5. 再增加 `disclosure_lag` 个交易日；
6. 同一报告期的同时可用修订按 catalog 优先级选择；同优先级冲突会报错；
7. 每只证券维护各报告期的最新已知记录，最大已知报告期成为当前状态；
8. 在交易日 index 上携带当前整行状态，最后裁剪到请求闭区间。

晚到的旧报告期修订不会替换已经可见的新报告期。状态携带以整条源记录为单位，因此新报告
中的显式 null 会保持为 null，不会逐字段继承旧报告的值。

默认初始化规格的 `disclosure_lag=0`，表示公告吸附后的首个交易日即可用。若研究假设为
T+1，应在自定义 `TushareDatasetSpec` 中显式设置 `disclosure_lag=1`。

```python
from quant_data import TushareDatasetSpec

data.register(
    TushareDatasetSpec(
        name="income_factor_t1",
        dataset="income",
        connection="tushare",
        disclosure_lag=1,
    )
)
```

给出显式 `instruments` 时走普通 API；`instruments=None` 时同一逻辑数据集自动走 VIP
全市场路由。`get_table()` 返回按报告期筛选的原始公告/修订长表，不做 PIT 对齐或状态携带。

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

日历对齐结果还包含 `calendar_aligned=True`，PIT 的 `disclosure_lag` 位于 `parameters`。
Arrow table 在 schema metadata 中保存
`quant_data.query_id`、`quant_data.dataset`、`quant_data.parameters`、
`quant_data.adjusted`。

## 审计记录

每次查询无论成功或失败，都写入：

```text
<audit_dir>/YYYY-MM-DD/<query_id>.json
```

记录包含请求字段、边界、股票池、实际复权状态、框架版本、来源 fingerprint、耗时、结果
尺寸和错误类型。Parquet fingerprint 保存文件绝对路径、大小和 `mtime_ns`；ClickHouse
保存脱敏 host、port、表、schema hash 与 catalog/remote 来源；Tushare 保存连接名、逻辑
数据集、可用 API、实际选中 API、schema hash、日历 API 和字符串化固定参数。凭证与
ClickHouse username 不会写入。

写入过程先在目标日期目录创建临时文件，flush、`fsync` 后用 `os.replace` 原子替换。
审计不是 best effort：无法持久化时查询视为失败，从而避免返回无法追溯的研究结果。
