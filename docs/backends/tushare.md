# Tushare

## Catalog 驱动

每个支持的 API 对应一个 `TushareTableCatalog`，集中定义：

- 完整 Arrow schema 和字段类型；
- `period_range`、`date_range` 或 `membership_interval` 查询风格；
- period/start/end/ts_code 参数名；
- 普通接口是否强制股票池；
- 去重键、修订优先级和排序列；
- 默认时间列、频率、时间范围要求和宽表兼容性；
- PIT disclosure/period 列及公告日期参数；
- 行业成员区间的起止列。

`fixed_params` 可以固定行业、交易或持有人类型等业务条件，但不能覆盖后端管理的
`fields`、日期、period 或证券参数。

## 普通与 VIP 财报

利润表、资产负债表、现金流量表、财务指标、业绩快报和业绩预告是季度报告期查询。
给出双边时间后，后端枚举闭区间内的季度末，再按 API 约束调用：

- 普通接口：`period × ts_code`，必须提供股票池；
- `_vip` 接口：股票池为 `None` 时每个 period 做一次全市场调用；
- `_vip` 也可以给股票池，此时仍逐只调用。

后端只请求结果所需字段，同时自动补去重键、修订排序列和最终排序列。不同家族的披露
字段并不相同：财务指标、快报和预告没有 `f_ann_date`，不会向远程 API 发送该字段。

## 类型规范化与去重

Tushare 返回 Pandas DataFrame。后端严格检查列集合，再按 catalog 转换：

- `YYYYMMDD` 字符串转 `date32`，无效日期报错；
- 文本转 Pandas string；
- 整数转 nullable `Int64`；
- 数值转 numeric；
- 最终按选择后的 Arrow schema 构造 table。

同一证券同一报告期的修订按家族选择最新记录：

| 家族 | 降序优先级 |
| --- | --- |
| 利润表、资产负债表、现金流量表 | `f_ann_date`, `ann_date`, `update_flag` |
| 财务指标 | `ann_date`, `update_flag` |
| 业绩快报 | `ann_date` |
| 业绩预告 | `ann_date`, `first_ann_date` |
| 股东人数 | `ann_date` |

`stk_holdertrade` 没有去重键，保留全部股东事件并禁止宽表。

## 行业成员区间

`ci_index_member` 与 `index_member_all` 返回 `in_date`/`out_date` 区间，不直接返回每日
观测。后端默认分别请求 `is_new=Y` 与 `is_new=N`，合并历史与当前成分；若
`fixed_params` 已固定 `is_new`，只调用一次。

每个区间与查询闭区间相交后，在 Tushare 交易日历上展开为 `date × ts_code`。重叠区间按
纳入日与 `is_new` 稳定排序后保留最新记录。`date` 是本地生成的 schema 字段，不发送给
远程 API。

## PIT 防前视

PIT 调用按公告日期范围而非报告期拉取事件，并向左增加 `fetch_buffer_days`。普通 API
仍要求股票池，VIP API 可请求全市场。后端先按 `(instrument, period, disclosure)` 去掉
同一公告事件的修订，再把 Arrow 事件与交易日历交给 `build_daily_panels()`。

转换层负责非交易日向后吸附、交易日 disclosure lag、同日最新报告期、前向填充和最终
闭区间裁剪。完整顺序见[特殊语义与审计](../guides/semantics.md#point-in-time-日频面板)
和[架构时序图](../architecture/index.md#pit-查询时序)。

日历按 `(connection, exchange, year, month)` 缓存。查询的右侧
`fetch_margin_days` 用于保证靠近结束日的 disclosure lag 有足够日历，但结果最终不会
越过 `end`。

## 连接生命周期

注册 Tushare 数据集会初始化并缓存客户端，因而必须有直接 token 或可解析的
`token_env`。数据 API 直到第一次扫描才调用。审计只记录 connection、API、schema hash
和字符串化 `fixed_params`；token 不会持久化。`close()` 关闭可关闭的客户端并清空日历缓存。
