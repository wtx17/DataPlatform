# Tushare

## 逻辑数据集与远程路由

Tushare 后端按业务实体注册数据集，而不是按远程 API 名注册。例如 `income` 是一个逻辑
数据集，`income` 与 `income_vip` 只是它的两条传输路由。`TushareDatasetCatalog` 集中拥有：

- 完整 Arrow schema；
- 表查询键、自动身份列、排序与频率；
- 宽表时间键、频率和是否支持宽表；
- 披露数据、有效区间或事件流语义；
- 普通/VIP API、参数名和可服务的股票池类型；
- 公告列、报告期列、修订优先级和交易日历要求。

公开的 `TushareDatasetSpec` 只描述注册名、连接、可选逻辑数据集名、固定业务参数、版本、
时区与 PIT 日历参数。省略 `dataset` 时从 `name` 推断：

```python
from quant_data import TushareDatasetSpec

data.register(TushareDatasetSpec(name="income", connection="tushare"))

# 固定参数视图或别名才需要 dataset
data.register(
    TushareDatasetSpec(
        name="income_bank",
        dataset="income",
        connection="tushare",
        fixed_params={"report_type": "1"},
    )
)
```

`fixed_params` 不能覆盖后端管理的 `fields`、日期、报告期和证券参数。成员数据的 `is_new`
例外：可以固定为 `Y` 或 `N`；未固定时后端会同时请求当前与历史区间。

## 确定性路由

利润表、资产负债表、现金流量表、财务指标、业绩快报和业绩预告按股票池选择路由：

| `instruments` | 远程路由 | 调用形状 |
| --- | --- | --- |
| 显式股票序列 | 普通 API | `period × ts_code` |
| `None` | VIP API | 每个 period 一次全市场调用 |
| 空序列 | 不调用数据 API | 返回类型正确的空结果 |

路由在请求前唯一确定。普通 API 失败时不会自动改走 VIP，VIP 失败时也不会缩小为逐股请求；
这样权限、配额、耗时和审计来源都保持可预测。实际选中的数据 API 会写入查询审计。

给出双边时间时，报告期表枚举闭区间内的季度末；表结果随后再次按 `end_date` 做本地闭区间
过滤。只给单边范围或不设范围时只发起一次未指定 period 的请求，再在本地过滤。

## `get_table()`：无损原始长表

`get_table()` 返回源 API 的公告和修订记录，不按 `(ts_code, end_date)` 去重。除了报告期与
证券键，还会自动带回足以区分源记录的身份/版本列。例如 `income` 自动返回：

```text
end_date, ts_code, ann_date, f_ann_date,
report_type, comp_type, end_type, update_flag, <requested fields...>
```

因此同一证券、同一报告期的多次公告和修订会保留为多行。查询时间范围对披露数据表示
报告期范围，而不是公告日期范围。需要构造因子时使用 `get_panel()`；需要审计、研究修订
轨迹或自行定义筛选规则时使用 `get_table()`。

Tushare DataFrame 会严格按 catalog 做类型规范化：`YYYYMMDD` 转 `date32`，文本转 string，
整数转 nullable `Int64`，数值转 numeric。非空响应缺少请求列、日期格式无效或 Arrow 转换
失败都会报错，不会静默补列。

## `get_panel()`：自动 PIT

披露型数据集的 `get_panel()` 固定产生交易日对齐的日频 PIT 面板，无需注册 `_pit` 数据集
或配置 panel mode。流程如下：

1. 从 `start - fetch_buffer_days` 起按公告日期拉取全部公告和修订；
2. 拉取并按月缓存 `trade_cal`；
3. 非交易日公告向后吸附到下一开市日；
4. 再增加 `disclosure_lag` 个交易日，默认值为 `0`；
5. 同一证券、报告期和可用日的候选记录按 catalog 修订优先级选择；优先级完全相同但请求
   字段冲突时直接报错；
6. 每只证券分别保存“每个报告期的最新已知记录”，并以最大的已知报告期作为当前状态；
7. 在交易日上携带当前整行状态并裁剪到请求闭区间。

第 6 步意味着晚到的旧报告期修订会更新旧期历史状态，但不会覆盖已经可见的新报告期。
第 7 步携带的是整行标识，不是逐字段 `ffill`：如果新报告明确返回 null，该字段会继续为
null，不会从上一报告期借值。

完整语义见[特殊语义与审计](../guides/semantics.md#point-in-time-日频面板)。

## 成员区间与事件表

`ci_index_member` 与 `index_member_all` 的 `get_table()` 返回原始 `in_date`/`out_date` 有效
区间，只保留与请求闭区间相交的记录，不生成 `date` 列。只有 `get_panel()` 才会把区间按
Tushare 交易日历展开成 `date × ts_code`。重叠区间按纳入日和 `is_new` 选择；相同优先级
却有冲突值时会报错。

`stk_holdertrade` 是一对多事件流。表查询保留全部事件并自动带回持有人、方向与事件日期等
身份列；该数据集不支持 `get_panel()`。

## 连接生命周期

添加连接和注册数据集都不会读取 token、导入 Tushare SDK 或创建远程客户端。第一次实际
查询才从直接 token 或 `token_env` 解析凭证并缓存客户端。因此默认初始化与文档生成可以在
无凭证环境中完成。

审计 fingerprint 保存逻辑数据集、可用 API、实际选中 API、schema hash、连接名和字符串化
固定参数；使用交易日历时还记录 `trade_cal`。token 永远不会持久化。`close()` 会关闭可
关闭的客户端并清空日历缓存。

## 从旧注册方式迁移

本次接口迁移不保留 `_vip`/`_pit` 注册别名，也不接受旧的 `api_name`、`panel_mode`、
`point_in_time`、键、频率或 panel capability 参数：

| 旧用法 | 新用法 |
| --- | --- |
| 注册 `income` 与 `income_vip` | 只注册 `income`；由 `instruments` 选择路由 |
| 注册 `income_pit` | 调用 `get_panel("income", ...)` |
| `get_panel("income", ...)` 按报告期直接 pivot | 自动返回交易日日频 PIT 面板 |
| `get_table("income_pit", ...)` | `get_table("income", ...)`，保留全部公告/修订 |
| `include_pit` / `register_tushare_pit` | 删除；默认集合始终只有逻辑数据集 |

自定义别名仍受支持，但要显式写 `dataset="income"`；别名不会改变 catalog 语义。
