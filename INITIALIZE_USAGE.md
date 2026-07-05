# initialize.py 注册数据字段手册

本文档按 `initialize_data_client()` 默认注册的数据集名称分节，列出每个数据集可用于 `get_panel()` 和 `get_table()` 的字段。
字段表中的“自动键列”不应写入 `fields` 参数：宽表会把它们用作索引或列，长表会自动返回它们。

```python
from quant_data.initialize import initialize_data_client

data = initialize_data_client()
```

默认连接环境变量：

| 用途 | 环境变量 | 默认值 |
| --- | --- | --- |
| 审计目录 | `QUANT_DATA_AUDIT_DIR` | `.quant_data/audit` |
| ClickHouse host | `QUANT_DATA_CLICKHOUSE_HOST` / `MINGHU_CLICKHOUSE_HOST` | `chdb.tradegdb.com` |
| ClickHouse port | `QUANT_DATA_CLICKHOUSE_PORT` / `MINGHU_CLICKHOUSE_PORT` | `8123` |
| ClickHouse username | `QUANT_DATA_CLICKHOUSE_USERNAME` / `MINGHU_CLICKHOUSE_USERNAME` | 无 |
| ClickHouse password | `QUANT_DATA_CLICKHOUSE_PASSWORD` 或 `MINGHU_CLICKHOUSE_PASSWORD` | 无 |
| Tushare token | `QUANT_DATA_TUSHARE_TOKEN` 或 `TUSHARE_TOKEN` | 无 |

通用宽表调用：

```python
panels = data.get_panel(
    "dataset_name",
    fields=["field_a", "field_b"],
    start="2024-01-01",
    end="2024-12-31",
    instruments=["600000.SH", "000001.SZ"],
)
field_a_panel = panels["field_a"]
```

通用长表调用：

```python
table = data.get_table(
    "dataset_name",
    fields=["field_a", "field_b"],
    start="2024-01-01",
    end="2024-12-31",
    instruments=["600000.SH"],
)
frame = table.to_pandas()
```

所有能生成宽表的数据集也能用 `get_table()` 返回长表；反过来不一定成立，例如逐笔和股东增减持是多事件长表，不能直接 pivot 成唯一的 `time × instrument` 宽表。

## `minghu_daily`

- 来源：ClickHouse `stock_base.daily` 明湖日线
- 自动键列：`date`、`code`
- 可生成宽表：是
- 可返回长表：是
- 说明：返回的 `code` 会根据 `exg` 自动补 `.SZ`、`.SH` 或 `.BJ` 后缀；`instruments` 必须传带后缀代码。价格字段默认按 `hfq` 后复权；传 `adjusted=False` 可返回原始价格。

宽表 `fields` 可选字段：`exg`, `open`, `high`, `low`, `close`, `pclose`, `change`, `pct_chg`, `volume`, `amount`, `hfq`, `ztprice`, `dtprice`, `omax_op`, `omin_op`。

```python
panels = data.get_panel(
    'minghu_daily',
    fields=['close', 'volume'],
    start='2026-03-02',
    end='2026-03-06',
    instruments=['000001.SZ', '600000.SH'],
)
first_panel = panels['close']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'minghu_daily',
    fields=['close', 'volume'],
    start='2026-03-02',
    end='2026-03-06',
    instruments=['000001.SZ'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `code` | `String` | 自动键列 | 证券代码（返回时自动补 `.SZ`/`.SH`/`.BJ`） |
| `date` | `Date` | 自动键列 | 日期 |
| `exg` | `UInt8` | 可请求字段 | 交易所类型, 1为深市，2为沪市 |
| `open` | `Nullable(Float64)` | 可请求字段 | 开盘价 |
| `high` | `Nullable(Float64)` | 可请求字段 | 最高价 |
| `low` | `Nullable(Float64)` | 可请求字段 | 最低价 |
| `close` | `Nullable(Float64)` | 可请求字段 | 收盘价 |
| `pclose` | `Nullable(Float64)` | 可请求字段 | 昨收价 |
| `change` | `Nullable(Float64)` | 可请求字段 | 涨跌额 |
| `pct_chg` | `Nullable(Float64)` | 可请求字段 | 涨跌幅(未复权) |
| `volume` | `Nullable(Int64)` | 可请求字段 | 成交量(股) |
| `amount` | `Nullable(Float64)` | 可请求字段 | 成交额 |
| `hfq` | `Nullable(Float64)` | 可请求字段 | 复权因子 |
| `ztprice` | `Nullable(Float64)` | 可请求字段 | 涨停价 |
| `dtprice` | `Nullable(Float64)` | 可请求字段 | 跌停价 |
| `omax_op` | `Nullable(Float64)` | 可请求字段 | 集合可申报最大价格 |
| `omin_op` | `Nullable(Float64)` | 可请求字段 | 集合可申报最小价格 |

## `minghu_m1`

- 来源：ClickHouse `stock_base.m1` 明湖 1 分钟线
- 自动键列：`date_time`、`code`
- 可生成宽表：是
- 可返回长表：是
- 说明：返回的 `code` 会根据 `exg` 自动补 `.SZ`、`.SH` 或 `.BJ` 后缀；`instruments` 必须传带后缀代码。分钟数据注册了 `partition_column='date'`，查询需要同时提供 `start` 和 `end`。

宽表 `fields` 可选字段：`exg`, `time_int`, `open`, `close`, `high`, `low`, `volume`, `amount`, `date`。

```python
panels = data.get_panel(
    'minghu_m1',
    fields=['close', 'volume'],
    start='2026-03-02 09:30:00',
    end='2026-03-02 10:00:00',
    instruments=['000001.SZ'],
)
first_panel = panels['close']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'minghu_m1',
    fields=['close', 'volume'],
    start='2026-03-02 09:30:00',
    end='2026-03-02 09:31:00',
    instruments=['000001.SZ'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `code` | `String` | 自动键列 | 证券代码（返回时自动补 `.SZ`/`.SH`/`.BJ`） |
| `date_time` | `DateTime('Asia/Shanghai')` | 自动键列 | 日期详情 |
| `exg` | `UInt8` | 可请求字段 | 交易所的标识，深市是1，沪市是2, 北交所是3 |
| `time_int` | `Int32` | 可请求字段 | 日期详情整形 |
| `open` | `Nullable(Float64)` | 可请求字段 |  |
| `close` | `Nullable(Float64)` | 可请求字段 |  |
| `high` | `Nullable(Float64)` | 可请求字段 |  |
| `low` | `Nullable(Float64)` | 可请求字段 |  |
| `volume` | `Nullable(Float64)` | 可请求字段 |  |
| `amount` | `Nullable(Float64)` | 可请求字段 |  |
| `date` | `Date` | 可请求字段 | 日期 |

## `minghu_zb`

- 来源：ClickHouse `stock_base.zb` 明湖逐笔事件
- 自动键列：`date_time`、`code`
- 可生成宽表：否
- 可返回长表：是
- 说明：返回的 `code` 会根据 `exg` 自动补 `.SZ`、`.SH` 或 `.BJ` 后缀；`instruments` 必须传带后缀代码。逐笔事件同一时间同一股票可能多条，只能用 `get_table()`。

宽表：不支持。

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'minghu_zb',
    fields=['price', 'volume', 'side', 'seqno'],
    start='2026-03-02 09:30:00',
    end='2026-03-02 09:31:00',
    instruments=['000001.SZ'],
    limit=100_000,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `code` | `String` | 自动键列 | 证券代码（返回时自动补 `.SZ`/`.SH`/`.BJ`） |
| `date` | `Date` | 可请求字段 | 日期 |
| `date_time` | `DateTime64(3, 'Asia/Shanghai')` | 自动键列 | 日期详情,业务时间,精确到百分之一秒 |
| `exg` | `UInt8` | 可请求字段 | 交易所的标识,深市是1,沪市是2 |
| `time_int` | `Int32` | 可请求字段 | date_time日期详情整形 |
| `price` | `Nullable(Float64)` | 可请求字段 | 价格（元） |
| `volume` | `Nullable(Int64)` | 可请求字段 | 委托数量 |
| `side` | `FixedString(1)` | 可请求字段 | 买卖标志,B-买单,S-卖单,G-借入,F-借出 |
| `type` | `FixedString(1)` | 可请求字段 | 订单类别,沪市为A-新增委托订单,D-删除委托订单,即撤单,深市为1-市价,2-限价,U - 本方最优 |
| `trade_flag` | `FixedString(1)` | 可请求字段 | 成交单子的内外盘标志:B-沪市外盘,主动买,S-沪市内盘,主动卖,N-沪市未知,F-深市成交,4-深市撤单 |
| `chno` | `UInt64` | 可请求字段 | 频道代码,通道 |
| `bidno` | `Nullable(Int64)` | 可请求字段 | 成交单子的买方委托编号 |
| `askno` | `Nullable(Int64)` | 可请求字段 | 成交单子的卖方委托编号 |
| `ordno` | `Nullable(Int64)` | 可请求字段 | 委托单子的编号,sh的order_no,sz的app_seq_num,sz的成交单子也有,sh的成交单子无,默认为0 |
| `seqno` | `UInt64` | 可请求字段 | 序列号,要求连续递增唯一,sh的业务序列号biz_idx,sz的委托索引app_seq_num |
| `ctype` | `FixedString(1)` | 可请求字段 | type,side,flag的合并, 1是新增限价委托,2是新增市价委托,3是新增本方最优,4是撤单,5是成交 |
| `cbidno` | `Nullable(Int64)` | 可请求字段 | 合并的成交单子的买方委托编号 |
| `caskno` | `Nullable(Int64)` | 可请求字段 | 合并的成交单子的买方委托编号 |

## `income`

- 来源：Tushare `income`（利润表）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：普通接口查询需要传入 `instruments`；对应 `_vip` 数据集支持 `instruments=None` 全市场查询。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `report_type`, `comp_type`, `end_type`, `basic_eps`, `diluted_eps`, `total_revenue`, `revenue`, `int_income`, `prem_earned`, `comm_income`, `n_commis_income`, `n_oth_income`, `n_oth_b_income`, `prem_income`, `out_prem`, `une_prem_reser`, `reins_income`, `n_sec_tb_income`, `n_sec_uw_income`, `n_asset_mg_income`, `oth_b_income`, `fv_value_chg_gain`, `invest_income`, `ass_invest_income`, `forex_gain`, `total_cogs`, `oper_cost`, `int_exp`, `comm_exp`, `biz_tax_surchg`, `sell_exp`, `admin_exp`, `fin_exp`, `assets_impair_loss`, `prem_refund`, `compens_payout`, `reser_insur_liab`, `div_payt`, `reins_exp`, `oper_exp`, `compens_payout_refu`, `insur_reser_refu`, `reins_cost_refund`, `other_bus_cost`, `operate_profit`, `non_oper_income`, `non_oper_exp`, `nca_disploss`, `total_profit`, `income_tax`, `n_income`, `n_income_attr_p`, `minority_gain`, `oth_compr_income`, `t_compr_income`, `compr_inc_attr_p`, `compr_inc_attr_m_s`, `ebit`, `ebitda`, `insurance_exp`, `undist_profit`, `distable_profit`, `rd_exp`, `fin_exp_int_exp`, `fin_exp_int_inc`, `transfer_surplus_rese`, `transfer_housing_imprest`, `transfer_oth`, `adj_lossgain`, `withdra_legal_surplus`, `withdra_legal_pubfund`, `withdra_biz_devfund`, `withdra_rese_fund`, `withdra_oth_ersu`, `workers_welfare`, `distr_profit_shrhder`, `prfshare_payable_dvd`, `comshare_payable_dvd`, `capit_comstock_div`, `continued_net_profit`, `update_flag`。

```python
panels = data.get_panel(
    'income',
    fields=['basic_eps', 'total_revenue', 'n_income_attr_p'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['basic_eps']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'income',
    fields=['basic_eps', 'total_revenue', 'n_income_attr_p'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `report_type` | `string` | 可请求字段 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `basic_eps` | `double` | 可请求字段 |  |
| `diluted_eps` | `double` | 可请求字段 |  |
| `total_revenue` | `double` | 可请求字段 |  |
| `revenue` | `double` | 可请求字段 |  |
| `int_income` | `double` | 可请求字段 |  |
| `prem_earned` | `double` | 可请求字段 |  |
| `comm_income` | `double` | 可请求字段 |  |
| `n_commis_income` | `double` | 可请求字段 |  |
| `n_oth_income` | `double` | 可请求字段 |  |
| `n_oth_b_income` | `double` | 可请求字段 |  |
| `prem_income` | `double` | 可请求字段 |  |
| `out_prem` | `double` | 可请求字段 |  |
| `une_prem_reser` | `double` | 可请求字段 |  |
| `reins_income` | `double` | 可请求字段 |  |
| `n_sec_tb_income` | `double` | 可请求字段 |  |
| `n_sec_uw_income` | `double` | 可请求字段 |  |
| `n_asset_mg_income` | `double` | 可请求字段 |  |
| `oth_b_income` | `double` | 可请求字段 |  |
| `fv_value_chg_gain` | `double` | 可请求字段 |  |
| `invest_income` | `double` | 可请求字段 |  |
| `ass_invest_income` | `double` | 可请求字段 |  |
| `forex_gain` | `double` | 可请求字段 |  |
| `total_cogs` | `double` | 可请求字段 |  |
| `oper_cost` | `double` | 可请求字段 |  |
| `int_exp` | `double` | 可请求字段 |  |
| `comm_exp` | `double` | 可请求字段 |  |
| `biz_tax_surchg` | `double` | 可请求字段 |  |
| `sell_exp` | `double` | 可请求字段 |  |
| `admin_exp` | `double` | 可请求字段 |  |
| `fin_exp` | `double` | 可请求字段 |  |
| `assets_impair_loss` | `double` | 可请求字段 |  |
| `prem_refund` | `double` | 可请求字段 |  |
| `compens_payout` | `double` | 可请求字段 |  |
| `reser_insur_liab` | `double` | 可请求字段 |  |
| `div_payt` | `double` | 可请求字段 |  |
| `reins_exp` | `double` | 可请求字段 |  |
| `oper_exp` | `double` | 可请求字段 |  |
| `compens_payout_refu` | `double` | 可请求字段 |  |
| `insur_reser_refu` | `double` | 可请求字段 |  |
| `reins_cost_refund` | `double` | 可请求字段 |  |
| `other_bus_cost` | `double` | 可请求字段 |  |
| `operate_profit` | `double` | 可请求字段 |  |
| `non_oper_income` | `double` | 可请求字段 |  |
| `non_oper_exp` | `double` | 可请求字段 |  |
| `nca_disploss` | `double` | 可请求字段 |  |
| `total_profit` | `double` | 可请求字段 |  |
| `income_tax` | `double` | 可请求字段 |  |
| `n_income` | `double` | 可请求字段 |  |
| `n_income_attr_p` | `double` | 可请求字段 |  |
| `minority_gain` | `double` | 可请求字段 |  |
| `oth_compr_income` | `double` | 可请求字段 |  |
| `t_compr_income` | `double` | 可请求字段 |  |
| `compr_inc_attr_p` | `double` | 可请求字段 |  |
| `compr_inc_attr_m_s` | `double` | 可请求字段 |  |
| `ebit` | `double` | 可请求字段 |  |
| `ebitda` | `double` | 可请求字段 |  |
| `insurance_exp` | `double` | 可请求字段 |  |
| `undist_profit` | `double` | 可请求字段 |  |
| `distable_profit` | `double` | 可请求字段 |  |
| `rd_exp` | `double` | 可请求字段 |  |
| `fin_exp_int_exp` | `double` | 可请求字段 |  |
| `fin_exp_int_inc` | `double` | 可请求字段 |  |
| `transfer_surplus_rese` | `double` | 可请求字段 |  |
| `transfer_housing_imprest` | `double` | 可请求字段 |  |
| `transfer_oth` | `double` | 可请求字段 |  |
| `adj_lossgain` | `double` | 可请求字段 |  |
| `withdra_legal_surplus` | `double` | 可请求字段 |  |
| `withdra_legal_pubfund` | `double` | 可请求字段 |  |
| `withdra_biz_devfund` | `double` | 可请求字段 |  |
| `withdra_rese_fund` | `double` | 可请求字段 |  |
| `withdra_oth_ersu` | `double` | 可请求字段 |  |
| `workers_welfare` | `double` | 可请求字段 |  |
| `distr_profit_shrhder` | `double` | 可请求字段 |  |
| `prfshare_payable_dvd` | `double` | 可请求字段 |  |
| `comshare_payable_dvd` | `double` | 可请求字段 |  |
| `capit_comstock_div` | `double` | 可请求字段 |  |
| `continued_net_profit` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `income_vip`

- 来源：Tushare `income_vip`（利润表 VIP）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：VIP 接口支持 `instruments=None` 全市场查询，也可以传股票池。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `report_type`, `comp_type`, `end_type`, `basic_eps`, `diluted_eps`, `total_revenue`, `revenue`, `int_income`, `prem_earned`, `comm_income`, `n_commis_income`, `n_oth_income`, `n_oth_b_income`, `prem_income`, `out_prem`, `une_prem_reser`, `reins_income`, `n_sec_tb_income`, `n_sec_uw_income`, `n_asset_mg_income`, `oth_b_income`, `fv_value_chg_gain`, `invest_income`, `ass_invest_income`, `forex_gain`, `total_cogs`, `oper_cost`, `int_exp`, `comm_exp`, `biz_tax_surchg`, `sell_exp`, `admin_exp`, `fin_exp`, `assets_impair_loss`, `prem_refund`, `compens_payout`, `reser_insur_liab`, `div_payt`, `reins_exp`, `oper_exp`, `compens_payout_refu`, `insur_reser_refu`, `reins_cost_refund`, `other_bus_cost`, `operate_profit`, `non_oper_income`, `non_oper_exp`, `nca_disploss`, `total_profit`, `income_tax`, `n_income`, `n_income_attr_p`, `minority_gain`, `oth_compr_income`, `t_compr_income`, `compr_inc_attr_p`, `compr_inc_attr_m_s`, `ebit`, `ebitda`, `insurance_exp`, `undist_profit`, `distable_profit`, `rd_exp`, `fin_exp_int_exp`, `fin_exp_int_inc`, `transfer_surplus_rese`, `transfer_housing_imprest`, `transfer_oth`, `adj_lossgain`, `withdra_legal_surplus`, `withdra_legal_pubfund`, `withdra_biz_devfund`, `withdra_rese_fund`, `withdra_oth_ersu`, `workers_welfare`, `distr_profit_shrhder`, `prfshare_payable_dvd`, `comshare_payable_dvd`, `capit_comstock_div`, `continued_net_profit`, `update_flag`。

```python
panels = data.get_panel(
    'income_vip',
    fields=['basic_eps', 'total_revenue', 'n_income_attr_p'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
first_panel = panels['basic_eps']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'income_vip',
    fields=['basic_eps', 'total_revenue', 'n_income_attr_p'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `report_type` | `string` | 可请求字段 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `basic_eps` | `double` | 可请求字段 |  |
| `diluted_eps` | `double` | 可请求字段 |  |
| `total_revenue` | `double` | 可请求字段 |  |
| `revenue` | `double` | 可请求字段 |  |
| `int_income` | `double` | 可请求字段 |  |
| `prem_earned` | `double` | 可请求字段 |  |
| `comm_income` | `double` | 可请求字段 |  |
| `n_commis_income` | `double` | 可请求字段 |  |
| `n_oth_income` | `double` | 可请求字段 |  |
| `n_oth_b_income` | `double` | 可请求字段 |  |
| `prem_income` | `double` | 可请求字段 |  |
| `out_prem` | `double` | 可请求字段 |  |
| `une_prem_reser` | `double` | 可请求字段 |  |
| `reins_income` | `double` | 可请求字段 |  |
| `n_sec_tb_income` | `double` | 可请求字段 |  |
| `n_sec_uw_income` | `double` | 可请求字段 |  |
| `n_asset_mg_income` | `double` | 可请求字段 |  |
| `oth_b_income` | `double` | 可请求字段 |  |
| `fv_value_chg_gain` | `double` | 可请求字段 |  |
| `invest_income` | `double` | 可请求字段 |  |
| `ass_invest_income` | `double` | 可请求字段 |  |
| `forex_gain` | `double` | 可请求字段 |  |
| `total_cogs` | `double` | 可请求字段 |  |
| `oper_cost` | `double` | 可请求字段 |  |
| `int_exp` | `double` | 可请求字段 |  |
| `comm_exp` | `double` | 可请求字段 |  |
| `biz_tax_surchg` | `double` | 可请求字段 |  |
| `sell_exp` | `double` | 可请求字段 |  |
| `admin_exp` | `double` | 可请求字段 |  |
| `fin_exp` | `double` | 可请求字段 |  |
| `assets_impair_loss` | `double` | 可请求字段 |  |
| `prem_refund` | `double` | 可请求字段 |  |
| `compens_payout` | `double` | 可请求字段 |  |
| `reser_insur_liab` | `double` | 可请求字段 |  |
| `div_payt` | `double` | 可请求字段 |  |
| `reins_exp` | `double` | 可请求字段 |  |
| `oper_exp` | `double` | 可请求字段 |  |
| `compens_payout_refu` | `double` | 可请求字段 |  |
| `insur_reser_refu` | `double` | 可请求字段 |  |
| `reins_cost_refund` | `double` | 可请求字段 |  |
| `other_bus_cost` | `double` | 可请求字段 |  |
| `operate_profit` | `double` | 可请求字段 |  |
| `non_oper_income` | `double` | 可请求字段 |  |
| `non_oper_exp` | `double` | 可请求字段 |  |
| `nca_disploss` | `double` | 可请求字段 |  |
| `total_profit` | `double` | 可请求字段 |  |
| `income_tax` | `double` | 可请求字段 |  |
| `n_income` | `double` | 可请求字段 |  |
| `n_income_attr_p` | `double` | 可请求字段 |  |
| `minority_gain` | `double` | 可请求字段 |  |
| `oth_compr_income` | `double` | 可请求字段 |  |
| `t_compr_income` | `double` | 可请求字段 |  |
| `compr_inc_attr_p` | `double` | 可请求字段 |  |
| `compr_inc_attr_m_s` | `double` | 可请求字段 |  |
| `ebit` | `double` | 可请求字段 |  |
| `ebitda` | `double` | 可请求字段 |  |
| `insurance_exp` | `double` | 可请求字段 |  |
| `undist_profit` | `double` | 可请求字段 |  |
| `distable_profit` | `double` | 可请求字段 |  |
| `rd_exp` | `double` | 可请求字段 |  |
| `fin_exp_int_exp` | `double` | 可请求字段 |  |
| `fin_exp_int_inc` | `double` | 可请求字段 |  |
| `transfer_surplus_rese` | `double` | 可请求字段 |  |
| `transfer_housing_imprest` | `double` | 可请求字段 |  |
| `transfer_oth` | `double` | 可请求字段 |  |
| `adj_lossgain` | `double` | 可请求字段 |  |
| `withdra_legal_surplus` | `double` | 可请求字段 |  |
| `withdra_legal_pubfund` | `double` | 可请求字段 |  |
| `withdra_biz_devfund` | `double` | 可请求字段 |  |
| `withdra_rese_fund` | `double` | 可请求字段 |  |
| `withdra_oth_ersu` | `double` | 可请求字段 |  |
| `workers_welfare` | `double` | 可请求字段 |  |
| `distr_profit_shrhder` | `double` | 可请求字段 |  |
| `prfshare_payable_dvd` | `double` | 可请求字段 |  |
| `comshare_payable_dvd` | `double` | 可请求字段 |  |
| `capit_comstock_div` | `double` | 可请求字段 |  |
| `continued_net_profit` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `balancesheet`

- 来源：Tushare `balancesheet`（资产负债表）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：普通接口查询需要传入 `instruments`；对应 `_vip` 数据集支持 `instruments=None` 全市场查询。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `report_type`, `comp_type`, `end_type`, `total_share`, `cap_rese`, `undistr_porfit`, `surplus_rese`, `special_rese`, `money_cap`, `trad_asset`, `notes_receiv`, `accounts_receiv`, `oth_receiv`, `prepayment`, `div_receiv`, `int_receiv`, `inventories`, `amor_exp`, `nca_within_1y`, `sett_rsrv`, `loanto_oth_bank_fi`, `premium_receiv`, `reinsur_receiv`, `reinsur_res_receiv`, `pur_resale_fa`, `oth_cur_assets`, `total_cur_assets`, `fa_avail_for_sale`, `htm_invest`, `lt_eqt_invest`, `invest_real_estate`, `time_deposits`, `oth_assets`, `lt_rec`, `fix_assets`, `cip`, `const_materials`, `fixed_assets_disp`, `produc_bio_assets`, `oil_and_gas_assets`, `intan_assets`, `r_and_d`, `goodwill`, `lt_amor_exp`, `defer_tax_assets`, `decr_in_disbur`, `oth_nca`, `total_nca`, `cash_reser_cb`, `depos_in_oth_bfi`, `prec_metals`, `deriv_assets`, `rr_reins_une_prem`, `rr_reins_outstd_cla`, `rr_reins_lins_liab`, `rr_reins_lthins_liab`, `refund_depos`, `ph_pledge_loans`, `refund_cap_depos`, `indep_acct_assets`, `client_depos`, `client_prov`, `transac_seat_fee`, `invest_as_receiv`, `total_assets`, `lt_borr`, `st_borr`, `cb_borr`, `depos_ib_deposits`, `loan_oth_bank`, `trading_fl`, `notes_payable`, `acct_payable`, `adv_receipts`, `sold_for_repur_fa`, `comm_payable`, `payroll_payable`, `taxes_payable`, `int_payable`, `div_payable`, `oth_payable`, `acc_exp`, `deferred_inc`, `st_bonds_payable`, `payable_to_reinsurer`, `rsrv_insur_cont`, `acting_trading_sec`, `acting_uw_sec`, `non_cur_liab_due_1y`, `oth_cur_liab`, `total_cur_liab`, `bond_payable`, `lt_payable`, `specific_payables`, `estimated_liab`, `defer_tax_liab`, `defer_inc_non_cur_liab`, `oth_ncl`, `total_ncl`, `depos_oth_bfi`, `deriv_liab`, `depos`, `agency_bus_liab`, `oth_liab`, `prem_receiv_adva`, `depos_received`, `ph_invest`, `reser_une_prem`, `reser_outstd_claims`, `reser_lins_liab`, `reser_lthins_liab`, `indept_acc_liab`, `pledge_borr`, `indem_payable`, `policy_div_payable`, `total_liab`, `treasury_share`, `ordin_risk_reser`, `forex_differ`, `invest_loss_unconf`, `minority_int`, `total_hldr_eqy_exc_min_int`, `total_hldr_eqy_inc_min_int`, `total_liab_hldr_eqy`, `lt_payroll_payable`, `oth_comp_income`, `oth_eqt_tools`, `oth_eqt_tools_p_shr`, `lending_funds`, `acc_receivable`, `st_fin_payable`, `payables`, `hfs_assets`, `hfs_sales`, `cost_fin_assets`, `fair_value_fin_assets`, `cip_total`, `oth_pay_total`, `long_pay_total`, `debt_invest`, `oth_debt_invest`, `contract_assets`, `contract_liab`, `accounts_receiv_bill`, `accounts_pay`, `oth_rcv_total`, `fix_assets_total`, `update_flag`。

```python
panels = data.get_panel(
    'balancesheet',
    fields=['total_assets', 'total_liab'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['total_assets']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'balancesheet',
    fields=['total_assets', 'total_liab'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `report_type` | `string` | 可请求字段 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `total_share` | `double` | 可请求字段 |  |
| `cap_rese` | `double` | 可请求字段 |  |
| `undistr_porfit` | `double` | 可请求字段 |  |
| `surplus_rese` | `double` | 可请求字段 |  |
| `special_rese` | `double` | 可请求字段 |  |
| `money_cap` | `double` | 可请求字段 |  |
| `trad_asset` | `double` | 可请求字段 |  |
| `notes_receiv` | `double` | 可请求字段 |  |
| `accounts_receiv` | `double` | 可请求字段 |  |
| `oth_receiv` | `double` | 可请求字段 |  |
| `prepayment` | `double` | 可请求字段 |  |
| `div_receiv` | `double` | 可请求字段 |  |
| `int_receiv` | `double` | 可请求字段 |  |
| `inventories` | `double` | 可请求字段 |  |
| `amor_exp` | `double` | 可请求字段 |  |
| `nca_within_1y` | `double` | 可请求字段 |  |
| `sett_rsrv` | `double` | 可请求字段 |  |
| `loanto_oth_bank_fi` | `double` | 可请求字段 |  |
| `premium_receiv` | `double` | 可请求字段 |  |
| `reinsur_receiv` | `double` | 可请求字段 |  |
| `reinsur_res_receiv` | `double` | 可请求字段 |  |
| `pur_resale_fa` | `double` | 可请求字段 |  |
| `oth_cur_assets` | `double` | 可请求字段 |  |
| `total_cur_assets` | `double` | 可请求字段 |  |
| `fa_avail_for_sale` | `double` | 可请求字段 |  |
| `htm_invest` | `double` | 可请求字段 |  |
| `lt_eqt_invest` | `double` | 可请求字段 |  |
| `invest_real_estate` | `double` | 可请求字段 |  |
| `time_deposits` | `double` | 可请求字段 |  |
| `oth_assets` | `double` | 可请求字段 |  |
| `lt_rec` | `double` | 可请求字段 |  |
| `fix_assets` | `double` | 可请求字段 |  |
| `cip` | `double` | 可请求字段 |  |
| `const_materials` | `double` | 可请求字段 |  |
| `fixed_assets_disp` | `double` | 可请求字段 |  |
| `produc_bio_assets` | `double` | 可请求字段 |  |
| `oil_and_gas_assets` | `double` | 可请求字段 |  |
| `intan_assets` | `double` | 可请求字段 |  |
| `r_and_d` | `double` | 可请求字段 |  |
| `goodwill` | `double` | 可请求字段 |  |
| `lt_amor_exp` | `double` | 可请求字段 |  |
| `defer_tax_assets` | `double` | 可请求字段 |  |
| `decr_in_disbur` | `double` | 可请求字段 |  |
| `oth_nca` | `double` | 可请求字段 |  |
| `total_nca` | `double` | 可请求字段 |  |
| `cash_reser_cb` | `double` | 可请求字段 |  |
| `depos_in_oth_bfi` | `double` | 可请求字段 |  |
| `prec_metals` | `double` | 可请求字段 |  |
| `deriv_assets` | `double` | 可请求字段 |  |
| `rr_reins_une_prem` | `double` | 可请求字段 |  |
| `rr_reins_outstd_cla` | `double` | 可请求字段 |  |
| `rr_reins_lins_liab` | `double` | 可请求字段 |  |
| `rr_reins_lthins_liab` | `double` | 可请求字段 |  |
| `refund_depos` | `double` | 可请求字段 |  |
| `ph_pledge_loans` | `double` | 可请求字段 |  |
| `refund_cap_depos` | `double` | 可请求字段 |  |
| `indep_acct_assets` | `double` | 可请求字段 |  |
| `client_depos` | `double` | 可请求字段 |  |
| `client_prov` | `double` | 可请求字段 |  |
| `transac_seat_fee` | `double` | 可请求字段 |  |
| `invest_as_receiv` | `double` | 可请求字段 |  |
| `total_assets` | `double` | 可请求字段 |  |
| `lt_borr` | `double` | 可请求字段 |  |
| `st_borr` | `double` | 可请求字段 |  |
| `cb_borr` | `double` | 可请求字段 |  |
| `depos_ib_deposits` | `double` | 可请求字段 |  |
| `loan_oth_bank` | `double` | 可请求字段 |  |
| `trading_fl` | `double` | 可请求字段 |  |
| `notes_payable` | `double` | 可请求字段 |  |
| `acct_payable` | `double` | 可请求字段 |  |
| `adv_receipts` | `double` | 可请求字段 |  |
| `sold_for_repur_fa` | `double` | 可请求字段 |  |
| `comm_payable` | `double` | 可请求字段 |  |
| `payroll_payable` | `double` | 可请求字段 |  |
| `taxes_payable` | `double` | 可请求字段 |  |
| `int_payable` | `double` | 可请求字段 |  |
| `div_payable` | `double` | 可请求字段 |  |
| `oth_payable` | `double` | 可请求字段 |  |
| `acc_exp` | `double` | 可请求字段 |  |
| `deferred_inc` | `double` | 可请求字段 |  |
| `st_bonds_payable` | `double` | 可请求字段 |  |
| `payable_to_reinsurer` | `double` | 可请求字段 |  |
| `rsrv_insur_cont` | `double` | 可请求字段 |  |
| `acting_trading_sec` | `double` | 可请求字段 |  |
| `acting_uw_sec` | `double` | 可请求字段 |  |
| `non_cur_liab_due_1y` | `double` | 可请求字段 |  |
| `oth_cur_liab` | `double` | 可请求字段 |  |
| `total_cur_liab` | `double` | 可请求字段 |  |
| `bond_payable` | `double` | 可请求字段 |  |
| `lt_payable` | `double` | 可请求字段 |  |
| `specific_payables` | `double` | 可请求字段 |  |
| `estimated_liab` | `double` | 可请求字段 |  |
| `defer_tax_liab` | `double` | 可请求字段 |  |
| `defer_inc_non_cur_liab` | `double` | 可请求字段 |  |
| `oth_ncl` | `double` | 可请求字段 |  |
| `total_ncl` | `double` | 可请求字段 |  |
| `depos_oth_bfi` | `double` | 可请求字段 |  |
| `deriv_liab` | `double` | 可请求字段 |  |
| `depos` | `double` | 可请求字段 |  |
| `agency_bus_liab` | `double` | 可请求字段 |  |
| `oth_liab` | `double` | 可请求字段 |  |
| `prem_receiv_adva` | `double` | 可请求字段 |  |
| `depos_received` | `double` | 可请求字段 |  |
| `ph_invest` | `double` | 可请求字段 |  |
| `reser_une_prem` | `double` | 可请求字段 |  |
| `reser_outstd_claims` | `double` | 可请求字段 |  |
| `reser_lins_liab` | `double` | 可请求字段 |  |
| `reser_lthins_liab` | `double` | 可请求字段 |  |
| `indept_acc_liab` | `double` | 可请求字段 |  |
| `pledge_borr` | `double` | 可请求字段 |  |
| `indem_payable` | `double` | 可请求字段 |  |
| `policy_div_payable` | `double` | 可请求字段 |  |
| `total_liab` | `double` | 可请求字段 |  |
| `treasury_share` | `double` | 可请求字段 |  |
| `ordin_risk_reser` | `double` | 可请求字段 |  |
| `forex_differ` | `double` | 可请求字段 |  |
| `invest_loss_unconf` | `double` | 可请求字段 |  |
| `minority_int` | `double` | 可请求字段 |  |
| `total_hldr_eqy_exc_min_int` | `double` | 可请求字段 |  |
| `total_hldr_eqy_inc_min_int` | `double` | 可请求字段 |  |
| `total_liab_hldr_eqy` | `double` | 可请求字段 |  |
| `lt_payroll_payable` | `double` | 可请求字段 |  |
| `oth_comp_income` | `double` | 可请求字段 |  |
| `oth_eqt_tools` | `double` | 可请求字段 |  |
| `oth_eqt_tools_p_shr` | `double` | 可请求字段 |  |
| `lending_funds` | `double` | 可请求字段 |  |
| `acc_receivable` | `double` | 可请求字段 |  |
| `st_fin_payable` | `double` | 可请求字段 |  |
| `payables` | `double` | 可请求字段 |  |
| `hfs_assets` | `double` | 可请求字段 |  |
| `hfs_sales` | `double` | 可请求字段 |  |
| `cost_fin_assets` | `double` | 可请求字段 |  |
| `fair_value_fin_assets` | `double` | 可请求字段 |  |
| `cip_total` | `double` | 可请求字段 |  |
| `oth_pay_total` | `double` | 可请求字段 |  |
| `long_pay_total` | `double` | 可请求字段 |  |
| `debt_invest` | `double` | 可请求字段 |  |
| `oth_debt_invest` | `double` | 可请求字段 |  |
| `contract_assets` | `double` | 可请求字段 |  |
| `contract_liab` | `double` | 可请求字段 |  |
| `accounts_receiv_bill` | `double` | 可请求字段 |  |
| `accounts_pay` | `double` | 可请求字段 |  |
| `oth_rcv_total` | `double` | 可请求字段 |  |
| `fix_assets_total` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `balancesheet_vip`

- 来源：Tushare `balancesheet_vip`（资产负债表 VIP）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：VIP 接口支持 `instruments=None` 全市场查询，也可以传股票池。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `report_type`, `comp_type`, `end_type`, `total_share`, `cap_rese`, `undistr_porfit`, `surplus_rese`, `special_rese`, `money_cap`, `trad_asset`, `notes_receiv`, `accounts_receiv`, `oth_receiv`, `prepayment`, `div_receiv`, `int_receiv`, `inventories`, `amor_exp`, `nca_within_1y`, `sett_rsrv`, `loanto_oth_bank_fi`, `premium_receiv`, `reinsur_receiv`, `reinsur_res_receiv`, `pur_resale_fa`, `oth_cur_assets`, `total_cur_assets`, `fa_avail_for_sale`, `htm_invest`, `lt_eqt_invest`, `invest_real_estate`, `time_deposits`, `oth_assets`, `lt_rec`, `fix_assets`, `cip`, `const_materials`, `fixed_assets_disp`, `produc_bio_assets`, `oil_and_gas_assets`, `intan_assets`, `r_and_d`, `goodwill`, `lt_amor_exp`, `defer_tax_assets`, `decr_in_disbur`, `oth_nca`, `total_nca`, `cash_reser_cb`, `depos_in_oth_bfi`, `prec_metals`, `deriv_assets`, `rr_reins_une_prem`, `rr_reins_outstd_cla`, `rr_reins_lins_liab`, `rr_reins_lthins_liab`, `refund_depos`, `ph_pledge_loans`, `refund_cap_depos`, `indep_acct_assets`, `client_depos`, `client_prov`, `transac_seat_fee`, `invest_as_receiv`, `total_assets`, `lt_borr`, `st_borr`, `cb_borr`, `depos_ib_deposits`, `loan_oth_bank`, `trading_fl`, `notes_payable`, `acct_payable`, `adv_receipts`, `sold_for_repur_fa`, `comm_payable`, `payroll_payable`, `taxes_payable`, `int_payable`, `div_payable`, `oth_payable`, `acc_exp`, `deferred_inc`, `st_bonds_payable`, `payable_to_reinsurer`, `rsrv_insur_cont`, `acting_trading_sec`, `acting_uw_sec`, `non_cur_liab_due_1y`, `oth_cur_liab`, `total_cur_liab`, `bond_payable`, `lt_payable`, `specific_payables`, `estimated_liab`, `defer_tax_liab`, `defer_inc_non_cur_liab`, `oth_ncl`, `total_ncl`, `depos_oth_bfi`, `deriv_liab`, `depos`, `agency_bus_liab`, `oth_liab`, `prem_receiv_adva`, `depos_received`, `ph_invest`, `reser_une_prem`, `reser_outstd_claims`, `reser_lins_liab`, `reser_lthins_liab`, `indept_acc_liab`, `pledge_borr`, `indem_payable`, `policy_div_payable`, `total_liab`, `treasury_share`, `ordin_risk_reser`, `forex_differ`, `invest_loss_unconf`, `minority_int`, `total_hldr_eqy_exc_min_int`, `total_hldr_eqy_inc_min_int`, `total_liab_hldr_eqy`, `lt_payroll_payable`, `oth_comp_income`, `oth_eqt_tools`, `oth_eqt_tools_p_shr`, `lending_funds`, `acc_receivable`, `st_fin_payable`, `payables`, `hfs_assets`, `hfs_sales`, `cost_fin_assets`, `fair_value_fin_assets`, `cip_total`, `oth_pay_total`, `long_pay_total`, `debt_invest`, `oth_debt_invest`, `contract_assets`, `contract_liab`, `accounts_receiv_bill`, `accounts_pay`, `oth_rcv_total`, `fix_assets_total`, `update_flag`。

```python
panels = data.get_panel(
    'balancesheet_vip',
    fields=['total_assets', 'total_liab'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
first_panel = panels['total_assets']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'balancesheet_vip',
    fields=['total_assets', 'total_liab'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `report_type` | `string` | 可请求字段 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `total_share` | `double` | 可请求字段 |  |
| `cap_rese` | `double` | 可请求字段 |  |
| `undistr_porfit` | `double` | 可请求字段 |  |
| `surplus_rese` | `double` | 可请求字段 |  |
| `special_rese` | `double` | 可请求字段 |  |
| `money_cap` | `double` | 可请求字段 |  |
| `trad_asset` | `double` | 可请求字段 |  |
| `notes_receiv` | `double` | 可请求字段 |  |
| `accounts_receiv` | `double` | 可请求字段 |  |
| `oth_receiv` | `double` | 可请求字段 |  |
| `prepayment` | `double` | 可请求字段 |  |
| `div_receiv` | `double` | 可请求字段 |  |
| `int_receiv` | `double` | 可请求字段 |  |
| `inventories` | `double` | 可请求字段 |  |
| `amor_exp` | `double` | 可请求字段 |  |
| `nca_within_1y` | `double` | 可请求字段 |  |
| `sett_rsrv` | `double` | 可请求字段 |  |
| `loanto_oth_bank_fi` | `double` | 可请求字段 |  |
| `premium_receiv` | `double` | 可请求字段 |  |
| `reinsur_receiv` | `double` | 可请求字段 |  |
| `reinsur_res_receiv` | `double` | 可请求字段 |  |
| `pur_resale_fa` | `double` | 可请求字段 |  |
| `oth_cur_assets` | `double` | 可请求字段 |  |
| `total_cur_assets` | `double` | 可请求字段 |  |
| `fa_avail_for_sale` | `double` | 可请求字段 |  |
| `htm_invest` | `double` | 可请求字段 |  |
| `lt_eqt_invest` | `double` | 可请求字段 |  |
| `invest_real_estate` | `double` | 可请求字段 |  |
| `time_deposits` | `double` | 可请求字段 |  |
| `oth_assets` | `double` | 可请求字段 |  |
| `lt_rec` | `double` | 可请求字段 |  |
| `fix_assets` | `double` | 可请求字段 |  |
| `cip` | `double` | 可请求字段 |  |
| `const_materials` | `double` | 可请求字段 |  |
| `fixed_assets_disp` | `double` | 可请求字段 |  |
| `produc_bio_assets` | `double` | 可请求字段 |  |
| `oil_and_gas_assets` | `double` | 可请求字段 |  |
| `intan_assets` | `double` | 可请求字段 |  |
| `r_and_d` | `double` | 可请求字段 |  |
| `goodwill` | `double` | 可请求字段 |  |
| `lt_amor_exp` | `double` | 可请求字段 |  |
| `defer_tax_assets` | `double` | 可请求字段 |  |
| `decr_in_disbur` | `double` | 可请求字段 |  |
| `oth_nca` | `double` | 可请求字段 |  |
| `total_nca` | `double` | 可请求字段 |  |
| `cash_reser_cb` | `double` | 可请求字段 |  |
| `depos_in_oth_bfi` | `double` | 可请求字段 |  |
| `prec_metals` | `double` | 可请求字段 |  |
| `deriv_assets` | `double` | 可请求字段 |  |
| `rr_reins_une_prem` | `double` | 可请求字段 |  |
| `rr_reins_outstd_cla` | `double` | 可请求字段 |  |
| `rr_reins_lins_liab` | `double` | 可请求字段 |  |
| `rr_reins_lthins_liab` | `double` | 可请求字段 |  |
| `refund_depos` | `double` | 可请求字段 |  |
| `ph_pledge_loans` | `double` | 可请求字段 |  |
| `refund_cap_depos` | `double` | 可请求字段 |  |
| `indep_acct_assets` | `double` | 可请求字段 |  |
| `client_depos` | `double` | 可请求字段 |  |
| `client_prov` | `double` | 可请求字段 |  |
| `transac_seat_fee` | `double` | 可请求字段 |  |
| `invest_as_receiv` | `double` | 可请求字段 |  |
| `total_assets` | `double` | 可请求字段 |  |
| `lt_borr` | `double` | 可请求字段 |  |
| `st_borr` | `double` | 可请求字段 |  |
| `cb_borr` | `double` | 可请求字段 |  |
| `depos_ib_deposits` | `double` | 可请求字段 |  |
| `loan_oth_bank` | `double` | 可请求字段 |  |
| `trading_fl` | `double` | 可请求字段 |  |
| `notes_payable` | `double` | 可请求字段 |  |
| `acct_payable` | `double` | 可请求字段 |  |
| `adv_receipts` | `double` | 可请求字段 |  |
| `sold_for_repur_fa` | `double` | 可请求字段 |  |
| `comm_payable` | `double` | 可请求字段 |  |
| `payroll_payable` | `double` | 可请求字段 |  |
| `taxes_payable` | `double` | 可请求字段 |  |
| `int_payable` | `double` | 可请求字段 |  |
| `div_payable` | `double` | 可请求字段 |  |
| `oth_payable` | `double` | 可请求字段 |  |
| `acc_exp` | `double` | 可请求字段 |  |
| `deferred_inc` | `double` | 可请求字段 |  |
| `st_bonds_payable` | `double` | 可请求字段 |  |
| `payable_to_reinsurer` | `double` | 可请求字段 |  |
| `rsrv_insur_cont` | `double` | 可请求字段 |  |
| `acting_trading_sec` | `double` | 可请求字段 |  |
| `acting_uw_sec` | `double` | 可请求字段 |  |
| `non_cur_liab_due_1y` | `double` | 可请求字段 |  |
| `oth_cur_liab` | `double` | 可请求字段 |  |
| `total_cur_liab` | `double` | 可请求字段 |  |
| `bond_payable` | `double` | 可请求字段 |  |
| `lt_payable` | `double` | 可请求字段 |  |
| `specific_payables` | `double` | 可请求字段 |  |
| `estimated_liab` | `double` | 可请求字段 |  |
| `defer_tax_liab` | `double` | 可请求字段 |  |
| `defer_inc_non_cur_liab` | `double` | 可请求字段 |  |
| `oth_ncl` | `double` | 可请求字段 |  |
| `total_ncl` | `double` | 可请求字段 |  |
| `depos_oth_bfi` | `double` | 可请求字段 |  |
| `deriv_liab` | `double` | 可请求字段 |  |
| `depos` | `double` | 可请求字段 |  |
| `agency_bus_liab` | `double` | 可请求字段 |  |
| `oth_liab` | `double` | 可请求字段 |  |
| `prem_receiv_adva` | `double` | 可请求字段 |  |
| `depos_received` | `double` | 可请求字段 |  |
| `ph_invest` | `double` | 可请求字段 |  |
| `reser_une_prem` | `double` | 可请求字段 |  |
| `reser_outstd_claims` | `double` | 可请求字段 |  |
| `reser_lins_liab` | `double` | 可请求字段 |  |
| `reser_lthins_liab` | `double` | 可请求字段 |  |
| `indept_acc_liab` | `double` | 可请求字段 |  |
| `pledge_borr` | `double` | 可请求字段 |  |
| `indem_payable` | `double` | 可请求字段 |  |
| `policy_div_payable` | `double` | 可请求字段 |  |
| `total_liab` | `double` | 可请求字段 |  |
| `treasury_share` | `double` | 可请求字段 |  |
| `ordin_risk_reser` | `double` | 可请求字段 |  |
| `forex_differ` | `double` | 可请求字段 |  |
| `invest_loss_unconf` | `double` | 可请求字段 |  |
| `minority_int` | `double` | 可请求字段 |  |
| `total_hldr_eqy_exc_min_int` | `double` | 可请求字段 |  |
| `total_hldr_eqy_inc_min_int` | `double` | 可请求字段 |  |
| `total_liab_hldr_eqy` | `double` | 可请求字段 |  |
| `lt_payroll_payable` | `double` | 可请求字段 |  |
| `oth_comp_income` | `double` | 可请求字段 |  |
| `oth_eqt_tools` | `double` | 可请求字段 |  |
| `oth_eqt_tools_p_shr` | `double` | 可请求字段 |  |
| `lending_funds` | `double` | 可请求字段 |  |
| `acc_receivable` | `double` | 可请求字段 |  |
| `st_fin_payable` | `double` | 可请求字段 |  |
| `payables` | `double` | 可请求字段 |  |
| `hfs_assets` | `double` | 可请求字段 |  |
| `hfs_sales` | `double` | 可请求字段 |  |
| `cost_fin_assets` | `double` | 可请求字段 |  |
| `fair_value_fin_assets` | `double` | 可请求字段 |  |
| `cip_total` | `double` | 可请求字段 |  |
| `oth_pay_total` | `double` | 可请求字段 |  |
| `long_pay_total` | `double` | 可请求字段 |  |
| `debt_invest` | `double` | 可请求字段 |  |
| `oth_debt_invest` | `double` | 可请求字段 |  |
| `contract_assets` | `double` | 可请求字段 |  |
| `contract_liab` | `double` | 可请求字段 |  |
| `accounts_receiv_bill` | `double` | 可请求字段 |  |
| `accounts_pay` | `double` | 可请求字段 |  |
| `oth_rcv_total` | `double` | 可请求字段 |  |
| `fix_assets_total` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `cashflow`

- 来源：Tushare `cashflow`（现金流量表）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：普通接口查询需要传入 `instruments`；对应 `_vip` 数据集支持 `instruments=None` 全市场查询。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `comp_type`, `report_type`, `end_type`, `net_profit`, `finan_exp`, `c_fr_sale_sg`, `recp_tax_rends`, `n_depos_incr_fi`, `n_incr_loans_cb`, `n_inc_borr_oth_fi`, `prem_fr_orig_contr`, `n_incr_insured_dep`, `n_reinsur_prem`, `n_incr_disp_tfa`, `ifc_cash_incr`, `n_incr_disp_faas`, `n_incr_loans_oth_bank`, `n_cap_incr_repur`, `c_fr_oth_operate_a`, `c_inf_fr_operate_a`, `c_paid_goods_s`, `c_paid_to_for_empl`, `c_paid_for_taxes`, `n_incr_clt_loan_adv`, `n_incr_dep_cbob`, `c_pay_claims_orig_inco`, `pay_handling_chrg`, `pay_comm_insur_plcy`, `oth_cash_pay_oper_act`, `st_cash_out_act`, `n_cashflow_act`, `oth_recp_ral_inv_act`, `c_disp_withdrwl_invest`, `c_recp_return_invest`, `n_recp_disp_fiolta`, `n_recp_disp_sobu`, `stot_inflows_inv_act`, `c_pay_acq_const_fiolta`, `c_paid_invest`, `n_disp_subs_oth_biz`, `oth_pay_ral_inv_act`, `n_incr_pledge_loan`, `stot_out_inv_act`, `n_cashflow_inv_act`, `c_recp_borrow`, `proc_issue_bonds`, `oth_cash_recp_ral_fnc_act`, `stot_cash_in_fnc_act`, `free_cashflow`, `c_prepay_amt_borr`, `c_pay_dist_dpcp_int_exp`, `incl_dvd_profit_paid_sc_ms`, `oth_cashpay_ral_fnc_act`, `stot_cashout_fnc_act`, `n_cash_flows_fnc_act`, `eff_fx_flu_cash`, `n_incr_cash_cash_equ`, `c_cash_equ_beg_period`, `c_cash_equ_end_period`, `c_recp_cap_contrib`, `incl_cash_rec_saims`, `uncon_invest_loss`, `prov_depr_assets`, `depr_fa_coga_dpba`, `amort_intang_assets`, `lt_amort_deferred_exp`, `decr_deferred_exp`, `incr_acc_exp`, `loss_disp_fiolta`, `loss_scr_fa`, `loss_fv_chg`, `invest_loss`, `decr_def_inc_tax_assets`, `incr_def_inc_tax_liab`, `decr_inventories`, `decr_oper_payable`, `incr_oper_payable`, `others`, `im_net_cashflow_oper_act`, `conv_debt_into_cap`, `conv_copbonds_due_within_1y`, `fa_fnc_leases`, `im_n_incr_cash_equ`, `net_dism_capital_add`, `net_cash_rece_sec`, `credit_impa_loss`, `use_right_asset_dep`, `oth_loss_asset`, `end_bal_cash`, `beg_bal_cash`, `end_bal_cash_equ`, `beg_bal_cash_equ`, `update_flag`。

```python
panels = data.get_panel(
    'cashflow',
    fields=['n_cashflow_act', 'free_cashflow'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['n_cashflow_act']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'cashflow',
    fields=['n_cashflow_act', 'free_cashflow'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `report_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `net_profit` | `double` | 可请求字段 |  |
| `finan_exp` | `double` | 可请求字段 |  |
| `c_fr_sale_sg` | `double` | 可请求字段 |  |
| `recp_tax_rends` | `double` | 可请求字段 |  |
| `n_depos_incr_fi` | `double` | 可请求字段 |  |
| `n_incr_loans_cb` | `double` | 可请求字段 |  |
| `n_inc_borr_oth_fi` | `double` | 可请求字段 |  |
| `prem_fr_orig_contr` | `double` | 可请求字段 |  |
| `n_incr_insured_dep` | `double` | 可请求字段 |  |
| `n_reinsur_prem` | `double` | 可请求字段 |  |
| `n_incr_disp_tfa` | `double` | 可请求字段 |  |
| `ifc_cash_incr` | `double` | 可请求字段 |  |
| `n_incr_disp_faas` | `double` | 可请求字段 |  |
| `n_incr_loans_oth_bank` | `double` | 可请求字段 |  |
| `n_cap_incr_repur` | `double` | 可请求字段 |  |
| `c_fr_oth_operate_a` | `double` | 可请求字段 |  |
| `c_inf_fr_operate_a` | `double` | 可请求字段 |  |
| `c_paid_goods_s` | `double` | 可请求字段 |  |
| `c_paid_to_for_empl` | `double` | 可请求字段 |  |
| `c_paid_for_taxes` | `double` | 可请求字段 |  |
| `n_incr_clt_loan_adv` | `double` | 可请求字段 |  |
| `n_incr_dep_cbob` | `double` | 可请求字段 |  |
| `c_pay_claims_orig_inco` | `double` | 可请求字段 |  |
| `pay_handling_chrg` | `double` | 可请求字段 |  |
| `pay_comm_insur_plcy` | `double` | 可请求字段 |  |
| `oth_cash_pay_oper_act` | `double` | 可请求字段 |  |
| `st_cash_out_act` | `double` | 可请求字段 |  |
| `n_cashflow_act` | `double` | 可请求字段 |  |
| `oth_recp_ral_inv_act` | `double` | 可请求字段 |  |
| `c_disp_withdrwl_invest` | `double` | 可请求字段 |  |
| `c_recp_return_invest` | `double` | 可请求字段 |  |
| `n_recp_disp_fiolta` | `double` | 可请求字段 |  |
| `n_recp_disp_sobu` | `double` | 可请求字段 |  |
| `stot_inflows_inv_act` | `double` | 可请求字段 |  |
| `c_pay_acq_const_fiolta` | `double` | 可请求字段 |  |
| `c_paid_invest` | `double` | 可请求字段 |  |
| `n_disp_subs_oth_biz` | `double` | 可请求字段 |  |
| `oth_pay_ral_inv_act` | `double` | 可请求字段 |  |
| `n_incr_pledge_loan` | `double` | 可请求字段 |  |
| `stot_out_inv_act` | `double` | 可请求字段 |  |
| `n_cashflow_inv_act` | `double` | 可请求字段 |  |
| `c_recp_borrow` | `double` | 可请求字段 |  |
| `proc_issue_bonds` | `double` | 可请求字段 |  |
| `oth_cash_recp_ral_fnc_act` | `double` | 可请求字段 |  |
| `stot_cash_in_fnc_act` | `double` | 可请求字段 |  |
| `free_cashflow` | `double` | 可请求字段 |  |
| `c_prepay_amt_borr` | `double` | 可请求字段 |  |
| `c_pay_dist_dpcp_int_exp` | `double` | 可请求字段 |  |
| `incl_dvd_profit_paid_sc_ms` | `double` | 可请求字段 |  |
| `oth_cashpay_ral_fnc_act` | `double` | 可请求字段 |  |
| `stot_cashout_fnc_act` | `double` | 可请求字段 |  |
| `n_cash_flows_fnc_act` | `double` | 可请求字段 |  |
| `eff_fx_flu_cash` | `double` | 可请求字段 |  |
| `n_incr_cash_cash_equ` | `double` | 可请求字段 |  |
| `c_cash_equ_beg_period` | `double` | 可请求字段 |  |
| `c_cash_equ_end_period` | `double` | 可请求字段 |  |
| `c_recp_cap_contrib` | `double` | 可请求字段 |  |
| `incl_cash_rec_saims` | `double` | 可请求字段 |  |
| `uncon_invest_loss` | `double` | 可请求字段 |  |
| `prov_depr_assets` | `double` | 可请求字段 |  |
| `depr_fa_coga_dpba` | `double` | 可请求字段 |  |
| `amort_intang_assets` | `double` | 可请求字段 |  |
| `lt_amort_deferred_exp` | `double` | 可请求字段 |  |
| `decr_deferred_exp` | `double` | 可请求字段 |  |
| `incr_acc_exp` | `double` | 可请求字段 |  |
| `loss_disp_fiolta` | `double` | 可请求字段 |  |
| `loss_scr_fa` | `double` | 可请求字段 |  |
| `loss_fv_chg` | `double` | 可请求字段 |  |
| `invest_loss` | `double` | 可请求字段 |  |
| `decr_def_inc_tax_assets` | `double` | 可请求字段 |  |
| `incr_def_inc_tax_liab` | `double` | 可请求字段 |  |
| `decr_inventories` | `double` | 可请求字段 |  |
| `decr_oper_payable` | `double` | 可请求字段 |  |
| `incr_oper_payable` | `double` | 可请求字段 |  |
| `others` | `double` | 可请求字段 |  |
| `im_net_cashflow_oper_act` | `double` | 可请求字段 |  |
| `conv_debt_into_cap` | `double` | 可请求字段 |  |
| `conv_copbonds_due_within_1y` | `double` | 可请求字段 |  |
| `fa_fnc_leases` | `double` | 可请求字段 |  |
| `im_n_incr_cash_equ` | `double` | 可请求字段 |  |
| `net_dism_capital_add` | `double` | 可请求字段 |  |
| `net_cash_rece_sec` | `double` | 可请求字段 |  |
| `credit_impa_loss` | `double` | 可请求字段 |  |
| `use_right_asset_dep` | `double` | 可请求字段 |  |
| `oth_loss_asset` | `double` | 可请求字段 |  |
| `end_bal_cash` | `double` | 可请求字段 |  |
| `beg_bal_cash` | `double` | 可请求字段 |  |
| `end_bal_cash_equ` | `double` | 可请求字段 |  |
| `beg_bal_cash_equ` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `cashflow_vip`

- 来源：Tushare `cashflow_vip`（现金流量表 VIP）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：VIP 接口支持 `instruments=None` 全市场查询，也可以传股票池。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `comp_type`, `report_type`, `end_type`, `net_profit`, `finan_exp`, `c_fr_sale_sg`, `recp_tax_rends`, `n_depos_incr_fi`, `n_incr_loans_cb`, `n_inc_borr_oth_fi`, `prem_fr_orig_contr`, `n_incr_insured_dep`, `n_reinsur_prem`, `n_incr_disp_tfa`, `ifc_cash_incr`, `n_incr_disp_faas`, `n_incr_loans_oth_bank`, `n_cap_incr_repur`, `c_fr_oth_operate_a`, `c_inf_fr_operate_a`, `c_paid_goods_s`, `c_paid_to_for_empl`, `c_paid_for_taxes`, `n_incr_clt_loan_adv`, `n_incr_dep_cbob`, `c_pay_claims_orig_inco`, `pay_handling_chrg`, `pay_comm_insur_plcy`, `oth_cash_pay_oper_act`, `st_cash_out_act`, `n_cashflow_act`, `oth_recp_ral_inv_act`, `c_disp_withdrwl_invest`, `c_recp_return_invest`, `n_recp_disp_fiolta`, `n_recp_disp_sobu`, `stot_inflows_inv_act`, `c_pay_acq_const_fiolta`, `c_paid_invest`, `n_disp_subs_oth_biz`, `oth_pay_ral_inv_act`, `n_incr_pledge_loan`, `stot_out_inv_act`, `n_cashflow_inv_act`, `c_recp_borrow`, `proc_issue_bonds`, `oth_cash_recp_ral_fnc_act`, `stot_cash_in_fnc_act`, `free_cashflow`, `c_prepay_amt_borr`, `c_pay_dist_dpcp_int_exp`, `incl_dvd_profit_paid_sc_ms`, `oth_cashpay_ral_fnc_act`, `stot_cashout_fnc_act`, `n_cash_flows_fnc_act`, `eff_fx_flu_cash`, `n_incr_cash_cash_equ`, `c_cash_equ_beg_period`, `c_cash_equ_end_period`, `c_recp_cap_contrib`, `incl_cash_rec_saims`, `uncon_invest_loss`, `prov_depr_assets`, `depr_fa_coga_dpba`, `amort_intang_assets`, `lt_amort_deferred_exp`, `decr_deferred_exp`, `incr_acc_exp`, `loss_disp_fiolta`, `loss_scr_fa`, `loss_fv_chg`, `invest_loss`, `decr_def_inc_tax_assets`, `incr_def_inc_tax_liab`, `decr_inventories`, `decr_oper_payable`, `incr_oper_payable`, `others`, `im_net_cashflow_oper_act`, `conv_debt_into_cap`, `conv_copbonds_due_within_1y`, `fa_fnc_leases`, `im_n_incr_cash_equ`, `net_dism_capital_add`, `net_cash_rece_sec`, `credit_impa_loss`, `use_right_asset_dep`, `oth_loss_asset`, `end_bal_cash`, `beg_bal_cash`, `end_bal_cash_equ`, `beg_bal_cash_equ`, `update_flag`。

```python
panels = data.get_panel(
    'cashflow_vip',
    fields=['n_cashflow_act', 'free_cashflow'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
first_panel = panels['n_cashflow_act']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'cashflow_vip',
    fields=['n_cashflow_act', 'free_cashflow'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `report_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `net_profit` | `double` | 可请求字段 |  |
| `finan_exp` | `double` | 可请求字段 |  |
| `c_fr_sale_sg` | `double` | 可请求字段 |  |
| `recp_tax_rends` | `double` | 可请求字段 |  |
| `n_depos_incr_fi` | `double` | 可请求字段 |  |
| `n_incr_loans_cb` | `double` | 可请求字段 |  |
| `n_inc_borr_oth_fi` | `double` | 可请求字段 |  |
| `prem_fr_orig_contr` | `double` | 可请求字段 |  |
| `n_incr_insured_dep` | `double` | 可请求字段 |  |
| `n_reinsur_prem` | `double` | 可请求字段 |  |
| `n_incr_disp_tfa` | `double` | 可请求字段 |  |
| `ifc_cash_incr` | `double` | 可请求字段 |  |
| `n_incr_disp_faas` | `double` | 可请求字段 |  |
| `n_incr_loans_oth_bank` | `double` | 可请求字段 |  |
| `n_cap_incr_repur` | `double` | 可请求字段 |  |
| `c_fr_oth_operate_a` | `double` | 可请求字段 |  |
| `c_inf_fr_operate_a` | `double` | 可请求字段 |  |
| `c_paid_goods_s` | `double` | 可请求字段 |  |
| `c_paid_to_for_empl` | `double` | 可请求字段 |  |
| `c_paid_for_taxes` | `double` | 可请求字段 |  |
| `n_incr_clt_loan_adv` | `double` | 可请求字段 |  |
| `n_incr_dep_cbob` | `double` | 可请求字段 |  |
| `c_pay_claims_orig_inco` | `double` | 可请求字段 |  |
| `pay_handling_chrg` | `double` | 可请求字段 |  |
| `pay_comm_insur_plcy` | `double` | 可请求字段 |  |
| `oth_cash_pay_oper_act` | `double` | 可请求字段 |  |
| `st_cash_out_act` | `double` | 可请求字段 |  |
| `n_cashflow_act` | `double` | 可请求字段 |  |
| `oth_recp_ral_inv_act` | `double` | 可请求字段 |  |
| `c_disp_withdrwl_invest` | `double` | 可请求字段 |  |
| `c_recp_return_invest` | `double` | 可请求字段 |  |
| `n_recp_disp_fiolta` | `double` | 可请求字段 |  |
| `n_recp_disp_sobu` | `double` | 可请求字段 |  |
| `stot_inflows_inv_act` | `double` | 可请求字段 |  |
| `c_pay_acq_const_fiolta` | `double` | 可请求字段 |  |
| `c_paid_invest` | `double` | 可请求字段 |  |
| `n_disp_subs_oth_biz` | `double` | 可请求字段 |  |
| `oth_pay_ral_inv_act` | `double` | 可请求字段 |  |
| `n_incr_pledge_loan` | `double` | 可请求字段 |  |
| `stot_out_inv_act` | `double` | 可请求字段 |  |
| `n_cashflow_inv_act` | `double` | 可请求字段 |  |
| `c_recp_borrow` | `double` | 可请求字段 |  |
| `proc_issue_bonds` | `double` | 可请求字段 |  |
| `oth_cash_recp_ral_fnc_act` | `double` | 可请求字段 |  |
| `stot_cash_in_fnc_act` | `double` | 可请求字段 |  |
| `free_cashflow` | `double` | 可请求字段 |  |
| `c_prepay_amt_borr` | `double` | 可请求字段 |  |
| `c_pay_dist_dpcp_int_exp` | `double` | 可请求字段 |  |
| `incl_dvd_profit_paid_sc_ms` | `double` | 可请求字段 |  |
| `oth_cashpay_ral_fnc_act` | `double` | 可请求字段 |  |
| `stot_cashout_fnc_act` | `double` | 可请求字段 |  |
| `n_cash_flows_fnc_act` | `double` | 可请求字段 |  |
| `eff_fx_flu_cash` | `double` | 可请求字段 |  |
| `n_incr_cash_cash_equ` | `double` | 可请求字段 |  |
| `c_cash_equ_beg_period` | `double` | 可请求字段 |  |
| `c_cash_equ_end_period` | `double` | 可请求字段 |  |
| `c_recp_cap_contrib` | `double` | 可请求字段 |  |
| `incl_cash_rec_saims` | `double` | 可请求字段 |  |
| `uncon_invest_loss` | `double` | 可请求字段 |  |
| `prov_depr_assets` | `double` | 可请求字段 |  |
| `depr_fa_coga_dpba` | `double` | 可请求字段 |  |
| `amort_intang_assets` | `double` | 可请求字段 |  |
| `lt_amort_deferred_exp` | `double` | 可请求字段 |  |
| `decr_deferred_exp` | `double` | 可请求字段 |  |
| `incr_acc_exp` | `double` | 可请求字段 |  |
| `loss_disp_fiolta` | `double` | 可请求字段 |  |
| `loss_scr_fa` | `double` | 可请求字段 |  |
| `loss_fv_chg` | `double` | 可请求字段 |  |
| `invest_loss` | `double` | 可请求字段 |  |
| `decr_def_inc_tax_assets` | `double` | 可请求字段 |  |
| `incr_def_inc_tax_liab` | `double` | 可请求字段 |  |
| `decr_inventories` | `double` | 可请求字段 |  |
| `decr_oper_payable` | `double` | 可请求字段 |  |
| `incr_oper_payable` | `double` | 可请求字段 |  |
| `others` | `double` | 可请求字段 |  |
| `im_net_cashflow_oper_act` | `double` | 可请求字段 |  |
| `conv_debt_into_cap` | `double` | 可请求字段 |  |
| `conv_copbonds_due_within_1y` | `double` | 可请求字段 |  |
| `fa_fnc_leases` | `double` | 可请求字段 |  |
| `im_n_incr_cash_equ` | `double` | 可请求字段 |  |
| `net_dism_capital_add` | `double` | 可请求字段 |  |
| `net_cash_rece_sec` | `double` | 可请求字段 |  |
| `credit_impa_loss` | `double` | 可请求字段 |  |
| `use_right_asset_dep` | `double` | 可请求字段 |  |
| `oth_loss_asset` | `double` | 可请求字段 |  |
| `end_bal_cash` | `double` | 可请求字段 |  |
| `beg_bal_cash` | `double` | 可请求字段 |  |
| `end_bal_cash_equ` | `double` | 可请求字段 |  |
| `beg_bal_cash_equ` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `fina_indicator`

- 来源：Tushare `fina_indicator`（财务指标）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：普通接口查询需要传入 `instruments`；对应 `_vip` 数据集支持 `instruments=None` 全市场查询。

宽表 `fields` 可选字段：`ann_date`, `eps`, `dt_eps`, `total_revenue_ps`, `revenue_ps`, `capital_rese_ps`, `surplus_rese_ps`, `undist_profit_ps`, `extra_item`, `profit_dedt`, `gross_margin`, `current_ratio`, `quick_ratio`, `cash_ratio`, `invturn_days`, `arturn_days`, `inv_turn`, `ar_turn`, `ca_turn`, `fa_turn`, `assets_turn`, `op_income`, `valuechange_income`, `interst_income`, `daa`, `ebit`, `ebitda`, `fcff`, `fcfe`, `current_exint`, `noncurrent_exint`, `interestdebt`, `netdebt`, `tangible_asset`, `working_capital`, `networking_capital`, `invest_capital`, `retained_earnings`, `diluted2_eps`, `bps`, `ocfps`, `retainedps`, `cfps`, `ebit_ps`, `fcff_ps`, `fcfe_ps`, `netprofit_margin`, `grossprofit_margin`, `cogs_of_sales`, `expense_of_sales`, `profit_to_gr`, `saleexp_to_gr`, `adminexp_of_gr`, `finaexp_of_gr`, `impai_ttm`, `gc_of_gr`, `op_of_gr`, `ebit_of_gr`, `roe`, `roe_waa`, `roe_dt`, `roa`, `npta`, `roic`, `roe_yearly`, `roa2_yearly`, `roe_avg`, `opincome_of_ebt`, `investincome_of_ebt`, `n_op_profit_of_ebt`, `tax_to_ebt`, `dtprofit_to_profit`, `salescash_to_or`, `ocf_to_or`, `ocf_to_opincome`, `capitalized_to_da`, `debt_to_assets`, `assets_to_eqt`, `dp_assets_to_eqt`, `ca_to_assets`, `nca_to_assets`, `tbassets_to_totalassets`, `int_to_talcap`, `eqt_to_talcapital`, `currentdebt_to_debt`, `longdeb_to_debt`, `ocf_to_shortdebt`, `debt_to_eqt`, `eqt_to_debt`, `eqt_to_interestdebt`, `tangibleasset_to_debt`, `tangasset_to_intdebt`, `tangibleasset_to_netdebt`, `ocf_to_debt`, `ocf_to_interestdebt`, `ocf_to_netdebt`, `ebit_to_interest`, `longdebt_to_workingcapital`, `ebitda_to_debt`, `turn_days`, `roa_yearly`, `roa_dp`, `fixed_assets`, `profit_prefin_exp`, `non_op_profit`, `op_to_ebt`, `nop_to_ebt`, `ocf_to_profit`, `cash_to_liqdebt`, `cash_to_liqdebt_withinterest`, `op_to_liqdebt`, `op_to_debt`, `roic_yearly`, `total_fa_trun`, `profit_to_op`, `q_opincome`, `q_investincome`, `q_dtprofit`, `q_eps`, `q_netprofit_margin`, `q_gsprofit_margin`, `q_exp_to_sales`, `q_profit_to_gr`, `q_saleexp_to_gr`, `q_adminexp_to_gr`, `q_finaexp_to_gr`, `q_impair_to_gr_ttm`, `q_gc_to_gr`, `q_op_to_gr`, `q_roe`, `q_dt_roe`, `q_npta`, `q_opincome_to_ebt`, `q_investincome_to_ebt`, `q_dtprofit_to_profit`, `q_salescash_to_or`, `q_ocf_to_sales`, `q_ocf_to_or`, `basic_eps_yoy`, `dt_eps_yoy`, `cfps_yoy`, `op_yoy`, `ebt_yoy`, `netprofit_yoy`, `dt_netprofit_yoy`, `ocf_yoy`, `roe_yoy`, `bps_yoy`, `assets_yoy`, `eqt_yoy`, `tr_yoy`, `or_yoy`, `q_gr_yoy`, `q_gr_qoq`, `q_sales_yoy`, `q_sales_qoq`, `q_op_yoy`, `q_op_qoq`, `q_profit_yoy`, `q_profit_qoq`, `q_netprofit_yoy`, `q_netprofit_qoq`, `equity_yoy`, `rd_exp`, `update_flag`。

```python
panels = data.get_panel(
    'fina_indicator',
    fields=['eps', 'roe'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['eps']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'fina_indicator',
    fields=['eps', 'roe'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `eps` | `double` | 可请求字段 |  |
| `dt_eps` | `double` | 可请求字段 |  |
| `total_revenue_ps` | `double` | 可请求字段 |  |
| `revenue_ps` | `double` | 可请求字段 |  |
| `capital_rese_ps` | `double` | 可请求字段 |  |
| `surplus_rese_ps` | `double` | 可请求字段 |  |
| `undist_profit_ps` | `double` | 可请求字段 |  |
| `extra_item` | `double` | 可请求字段 |  |
| `profit_dedt` | `double` | 可请求字段 |  |
| `gross_margin` | `double` | 可请求字段 |  |
| `current_ratio` | `double` | 可请求字段 |  |
| `quick_ratio` | `double` | 可请求字段 |  |
| `cash_ratio` | `double` | 可请求字段 |  |
| `invturn_days` | `double` | 可请求字段 |  |
| `arturn_days` | `double` | 可请求字段 |  |
| `inv_turn` | `double` | 可请求字段 |  |
| `ar_turn` | `double` | 可请求字段 |  |
| `ca_turn` | `double` | 可请求字段 |  |
| `fa_turn` | `double` | 可请求字段 |  |
| `assets_turn` | `double` | 可请求字段 |  |
| `op_income` | `double` | 可请求字段 |  |
| `valuechange_income` | `double` | 可请求字段 |  |
| `interst_income` | `double` | 可请求字段 |  |
| `daa` | `double` | 可请求字段 |  |
| `ebit` | `double` | 可请求字段 |  |
| `ebitda` | `double` | 可请求字段 |  |
| `fcff` | `double` | 可请求字段 |  |
| `fcfe` | `double` | 可请求字段 |  |
| `current_exint` | `double` | 可请求字段 |  |
| `noncurrent_exint` | `double` | 可请求字段 |  |
| `interestdebt` | `double` | 可请求字段 |  |
| `netdebt` | `double` | 可请求字段 |  |
| `tangible_asset` | `double` | 可请求字段 |  |
| `working_capital` | `double` | 可请求字段 |  |
| `networking_capital` | `double` | 可请求字段 |  |
| `invest_capital` | `double` | 可请求字段 |  |
| `retained_earnings` | `double` | 可请求字段 |  |
| `diluted2_eps` | `double` | 可请求字段 |  |
| `bps` | `double` | 可请求字段 |  |
| `ocfps` | `double` | 可请求字段 |  |
| `retainedps` | `double` | 可请求字段 |  |
| `cfps` | `double` | 可请求字段 |  |
| `ebit_ps` | `double` | 可请求字段 |  |
| `fcff_ps` | `double` | 可请求字段 |  |
| `fcfe_ps` | `double` | 可请求字段 |  |
| `netprofit_margin` | `double` | 可请求字段 |  |
| `grossprofit_margin` | `double` | 可请求字段 |  |
| `cogs_of_sales` | `double` | 可请求字段 |  |
| `expense_of_sales` | `double` | 可请求字段 |  |
| `profit_to_gr` | `double` | 可请求字段 |  |
| `saleexp_to_gr` | `double` | 可请求字段 |  |
| `adminexp_of_gr` | `double` | 可请求字段 |  |
| `finaexp_of_gr` | `double` | 可请求字段 |  |
| `impai_ttm` | `double` | 可请求字段 |  |
| `gc_of_gr` | `double` | 可请求字段 |  |
| `op_of_gr` | `double` | 可请求字段 |  |
| `ebit_of_gr` | `double` | 可请求字段 |  |
| `roe` | `double` | 可请求字段 |  |
| `roe_waa` | `double` | 可请求字段 |  |
| `roe_dt` | `double` | 可请求字段 |  |
| `roa` | `double` | 可请求字段 |  |
| `npta` | `double` | 可请求字段 |  |
| `roic` | `double` | 可请求字段 |  |
| `roe_yearly` | `double` | 可请求字段 |  |
| `roa2_yearly` | `double` | 可请求字段 |  |
| `roe_avg` | `double` | 可请求字段 |  |
| `opincome_of_ebt` | `double` | 可请求字段 |  |
| `investincome_of_ebt` | `double` | 可请求字段 |  |
| `n_op_profit_of_ebt` | `double` | 可请求字段 |  |
| `tax_to_ebt` | `double` | 可请求字段 |  |
| `dtprofit_to_profit` | `double` | 可请求字段 |  |
| `salescash_to_or` | `double` | 可请求字段 |  |
| `ocf_to_or` | `double` | 可请求字段 |  |
| `ocf_to_opincome` | `double` | 可请求字段 |  |
| `capitalized_to_da` | `double` | 可请求字段 |  |
| `debt_to_assets` | `double` | 可请求字段 |  |
| `assets_to_eqt` | `double` | 可请求字段 |  |
| `dp_assets_to_eqt` | `double` | 可请求字段 |  |
| `ca_to_assets` | `double` | 可请求字段 |  |
| `nca_to_assets` | `double` | 可请求字段 |  |
| `tbassets_to_totalassets` | `double` | 可请求字段 |  |
| `int_to_talcap` | `double` | 可请求字段 |  |
| `eqt_to_talcapital` | `double` | 可请求字段 |  |
| `currentdebt_to_debt` | `double` | 可请求字段 |  |
| `longdeb_to_debt` | `double` | 可请求字段 |  |
| `ocf_to_shortdebt` | `double` | 可请求字段 |  |
| `debt_to_eqt` | `double` | 可请求字段 |  |
| `eqt_to_debt` | `double` | 可请求字段 |  |
| `eqt_to_interestdebt` | `double` | 可请求字段 |  |
| `tangibleasset_to_debt` | `double` | 可请求字段 |  |
| `tangasset_to_intdebt` | `double` | 可请求字段 |  |
| `tangibleasset_to_netdebt` | `double` | 可请求字段 |  |
| `ocf_to_debt` | `double` | 可请求字段 |  |
| `ocf_to_interestdebt` | `double` | 可请求字段 |  |
| `ocf_to_netdebt` | `double` | 可请求字段 |  |
| `ebit_to_interest` | `double` | 可请求字段 |  |
| `longdebt_to_workingcapital` | `double` | 可请求字段 |  |
| `ebitda_to_debt` | `double` | 可请求字段 |  |
| `turn_days` | `double` | 可请求字段 |  |
| `roa_yearly` | `double` | 可请求字段 |  |
| `roa_dp` | `double` | 可请求字段 |  |
| `fixed_assets` | `double` | 可请求字段 |  |
| `profit_prefin_exp` | `double` | 可请求字段 |  |
| `non_op_profit` | `double` | 可请求字段 |  |
| `op_to_ebt` | `double` | 可请求字段 |  |
| `nop_to_ebt` | `double` | 可请求字段 |  |
| `ocf_to_profit` | `double` | 可请求字段 |  |
| `cash_to_liqdebt` | `double` | 可请求字段 |  |
| `cash_to_liqdebt_withinterest` | `double` | 可请求字段 |  |
| `op_to_liqdebt` | `double` | 可请求字段 |  |
| `op_to_debt` | `double` | 可请求字段 |  |
| `roic_yearly` | `double` | 可请求字段 |  |
| `total_fa_trun` | `double` | 可请求字段 |  |
| `profit_to_op` | `double` | 可请求字段 |  |
| `q_opincome` | `double` | 可请求字段 |  |
| `q_investincome` | `double` | 可请求字段 |  |
| `q_dtprofit` | `double` | 可请求字段 |  |
| `q_eps` | `double` | 可请求字段 |  |
| `q_netprofit_margin` | `double` | 可请求字段 |  |
| `q_gsprofit_margin` | `double` | 可请求字段 |  |
| `q_exp_to_sales` | `double` | 可请求字段 |  |
| `q_profit_to_gr` | `double` | 可请求字段 |  |
| `q_saleexp_to_gr` | `double` | 可请求字段 |  |
| `q_adminexp_to_gr` | `double` | 可请求字段 |  |
| `q_finaexp_to_gr` | `double` | 可请求字段 |  |
| `q_impair_to_gr_ttm` | `double` | 可请求字段 |  |
| `q_gc_to_gr` | `double` | 可请求字段 |  |
| `q_op_to_gr` | `double` | 可请求字段 |  |
| `q_roe` | `double` | 可请求字段 |  |
| `q_dt_roe` | `double` | 可请求字段 |  |
| `q_npta` | `double` | 可请求字段 |  |
| `q_opincome_to_ebt` | `double` | 可请求字段 |  |
| `q_investincome_to_ebt` | `double` | 可请求字段 |  |
| `q_dtprofit_to_profit` | `double` | 可请求字段 |  |
| `q_salescash_to_or` | `double` | 可请求字段 |  |
| `q_ocf_to_sales` | `double` | 可请求字段 |  |
| `q_ocf_to_or` | `double` | 可请求字段 |  |
| `basic_eps_yoy` | `double` | 可请求字段 |  |
| `dt_eps_yoy` | `double` | 可请求字段 |  |
| `cfps_yoy` | `double` | 可请求字段 |  |
| `op_yoy` | `double` | 可请求字段 |  |
| `ebt_yoy` | `double` | 可请求字段 |  |
| `netprofit_yoy` | `double` | 可请求字段 |  |
| `dt_netprofit_yoy` | `double` | 可请求字段 |  |
| `ocf_yoy` | `double` | 可请求字段 |  |
| `roe_yoy` | `double` | 可请求字段 |  |
| `bps_yoy` | `double` | 可请求字段 |  |
| `assets_yoy` | `double` | 可请求字段 |  |
| `eqt_yoy` | `double` | 可请求字段 |  |
| `tr_yoy` | `double` | 可请求字段 |  |
| `or_yoy` | `double` | 可请求字段 |  |
| `q_gr_yoy` | `double` | 可请求字段 |  |
| `q_gr_qoq` | `double` | 可请求字段 |  |
| `q_sales_yoy` | `double` | 可请求字段 |  |
| `q_sales_qoq` | `double` | 可请求字段 |  |
| `q_op_yoy` | `double` | 可请求字段 |  |
| `q_op_qoq` | `double` | 可请求字段 |  |
| `q_profit_yoy` | `double` | 可请求字段 |  |
| `q_profit_qoq` | `double` | 可请求字段 |  |
| `q_netprofit_yoy` | `double` | 可请求字段 |  |
| `q_netprofit_qoq` | `double` | 可请求字段 |  |
| `equity_yoy` | `double` | 可请求字段 |  |
| `rd_exp` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `fina_indicator_vip`

- 来源：Tushare `fina_indicator_vip`（财务指标 VIP）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：VIP 接口支持 `instruments=None` 全市场查询，也可以传股票池。

宽表 `fields` 可选字段：`ann_date`, `eps`, `dt_eps`, `total_revenue_ps`, `revenue_ps`, `capital_rese_ps`, `surplus_rese_ps`, `undist_profit_ps`, `extra_item`, `profit_dedt`, `gross_margin`, `current_ratio`, `quick_ratio`, `cash_ratio`, `invturn_days`, `arturn_days`, `inv_turn`, `ar_turn`, `ca_turn`, `fa_turn`, `assets_turn`, `op_income`, `valuechange_income`, `interst_income`, `daa`, `ebit`, `ebitda`, `fcff`, `fcfe`, `current_exint`, `noncurrent_exint`, `interestdebt`, `netdebt`, `tangible_asset`, `working_capital`, `networking_capital`, `invest_capital`, `retained_earnings`, `diluted2_eps`, `bps`, `ocfps`, `retainedps`, `cfps`, `ebit_ps`, `fcff_ps`, `fcfe_ps`, `netprofit_margin`, `grossprofit_margin`, `cogs_of_sales`, `expense_of_sales`, `profit_to_gr`, `saleexp_to_gr`, `adminexp_of_gr`, `finaexp_of_gr`, `impai_ttm`, `gc_of_gr`, `op_of_gr`, `ebit_of_gr`, `roe`, `roe_waa`, `roe_dt`, `roa`, `npta`, `roic`, `roe_yearly`, `roa2_yearly`, `roe_avg`, `opincome_of_ebt`, `investincome_of_ebt`, `n_op_profit_of_ebt`, `tax_to_ebt`, `dtprofit_to_profit`, `salescash_to_or`, `ocf_to_or`, `ocf_to_opincome`, `capitalized_to_da`, `debt_to_assets`, `assets_to_eqt`, `dp_assets_to_eqt`, `ca_to_assets`, `nca_to_assets`, `tbassets_to_totalassets`, `int_to_talcap`, `eqt_to_talcapital`, `currentdebt_to_debt`, `longdeb_to_debt`, `ocf_to_shortdebt`, `debt_to_eqt`, `eqt_to_debt`, `eqt_to_interestdebt`, `tangibleasset_to_debt`, `tangasset_to_intdebt`, `tangibleasset_to_netdebt`, `ocf_to_debt`, `ocf_to_interestdebt`, `ocf_to_netdebt`, `ebit_to_interest`, `longdebt_to_workingcapital`, `ebitda_to_debt`, `turn_days`, `roa_yearly`, `roa_dp`, `fixed_assets`, `profit_prefin_exp`, `non_op_profit`, `op_to_ebt`, `nop_to_ebt`, `ocf_to_profit`, `cash_to_liqdebt`, `cash_to_liqdebt_withinterest`, `op_to_liqdebt`, `op_to_debt`, `roic_yearly`, `total_fa_trun`, `profit_to_op`, `q_opincome`, `q_investincome`, `q_dtprofit`, `q_eps`, `q_netprofit_margin`, `q_gsprofit_margin`, `q_exp_to_sales`, `q_profit_to_gr`, `q_saleexp_to_gr`, `q_adminexp_to_gr`, `q_finaexp_to_gr`, `q_impair_to_gr_ttm`, `q_gc_to_gr`, `q_op_to_gr`, `q_roe`, `q_dt_roe`, `q_npta`, `q_opincome_to_ebt`, `q_investincome_to_ebt`, `q_dtprofit_to_profit`, `q_salescash_to_or`, `q_ocf_to_sales`, `q_ocf_to_or`, `basic_eps_yoy`, `dt_eps_yoy`, `cfps_yoy`, `op_yoy`, `ebt_yoy`, `netprofit_yoy`, `dt_netprofit_yoy`, `ocf_yoy`, `roe_yoy`, `bps_yoy`, `assets_yoy`, `eqt_yoy`, `tr_yoy`, `or_yoy`, `q_gr_yoy`, `q_gr_qoq`, `q_sales_yoy`, `q_sales_qoq`, `q_op_yoy`, `q_op_qoq`, `q_profit_yoy`, `q_profit_qoq`, `q_netprofit_yoy`, `q_netprofit_qoq`, `equity_yoy`, `rd_exp`, `update_flag`。

```python
panels = data.get_panel(
    'fina_indicator_vip',
    fields=['eps', 'roe'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
first_panel = panels['eps']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'fina_indicator_vip',
    fields=['eps', 'roe'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `eps` | `double` | 可请求字段 |  |
| `dt_eps` | `double` | 可请求字段 |  |
| `total_revenue_ps` | `double` | 可请求字段 |  |
| `revenue_ps` | `double` | 可请求字段 |  |
| `capital_rese_ps` | `double` | 可请求字段 |  |
| `surplus_rese_ps` | `double` | 可请求字段 |  |
| `undist_profit_ps` | `double` | 可请求字段 |  |
| `extra_item` | `double` | 可请求字段 |  |
| `profit_dedt` | `double` | 可请求字段 |  |
| `gross_margin` | `double` | 可请求字段 |  |
| `current_ratio` | `double` | 可请求字段 |  |
| `quick_ratio` | `double` | 可请求字段 |  |
| `cash_ratio` | `double` | 可请求字段 |  |
| `invturn_days` | `double` | 可请求字段 |  |
| `arturn_days` | `double` | 可请求字段 |  |
| `inv_turn` | `double` | 可请求字段 |  |
| `ar_turn` | `double` | 可请求字段 |  |
| `ca_turn` | `double` | 可请求字段 |  |
| `fa_turn` | `double` | 可请求字段 |  |
| `assets_turn` | `double` | 可请求字段 |  |
| `op_income` | `double` | 可请求字段 |  |
| `valuechange_income` | `double` | 可请求字段 |  |
| `interst_income` | `double` | 可请求字段 |  |
| `daa` | `double` | 可请求字段 |  |
| `ebit` | `double` | 可请求字段 |  |
| `ebitda` | `double` | 可请求字段 |  |
| `fcff` | `double` | 可请求字段 |  |
| `fcfe` | `double` | 可请求字段 |  |
| `current_exint` | `double` | 可请求字段 |  |
| `noncurrent_exint` | `double` | 可请求字段 |  |
| `interestdebt` | `double` | 可请求字段 |  |
| `netdebt` | `double` | 可请求字段 |  |
| `tangible_asset` | `double` | 可请求字段 |  |
| `working_capital` | `double` | 可请求字段 |  |
| `networking_capital` | `double` | 可请求字段 |  |
| `invest_capital` | `double` | 可请求字段 |  |
| `retained_earnings` | `double` | 可请求字段 |  |
| `diluted2_eps` | `double` | 可请求字段 |  |
| `bps` | `double` | 可请求字段 |  |
| `ocfps` | `double` | 可请求字段 |  |
| `retainedps` | `double` | 可请求字段 |  |
| `cfps` | `double` | 可请求字段 |  |
| `ebit_ps` | `double` | 可请求字段 |  |
| `fcff_ps` | `double` | 可请求字段 |  |
| `fcfe_ps` | `double` | 可请求字段 |  |
| `netprofit_margin` | `double` | 可请求字段 |  |
| `grossprofit_margin` | `double` | 可请求字段 |  |
| `cogs_of_sales` | `double` | 可请求字段 |  |
| `expense_of_sales` | `double` | 可请求字段 |  |
| `profit_to_gr` | `double` | 可请求字段 |  |
| `saleexp_to_gr` | `double` | 可请求字段 |  |
| `adminexp_of_gr` | `double` | 可请求字段 |  |
| `finaexp_of_gr` | `double` | 可请求字段 |  |
| `impai_ttm` | `double` | 可请求字段 |  |
| `gc_of_gr` | `double` | 可请求字段 |  |
| `op_of_gr` | `double` | 可请求字段 |  |
| `ebit_of_gr` | `double` | 可请求字段 |  |
| `roe` | `double` | 可请求字段 |  |
| `roe_waa` | `double` | 可请求字段 |  |
| `roe_dt` | `double` | 可请求字段 |  |
| `roa` | `double` | 可请求字段 |  |
| `npta` | `double` | 可请求字段 |  |
| `roic` | `double` | 可请求字段 |  |
| `roe_yearly` | `double` | 可请求字段 |  |
| `roa2_yearly` | `double` | 可请求字段 |  |
| `roe_avg` | `double` | 可请求字段 |  |
| `opincome_of_ebt` | `double` | 可请求字段 |  |
| `investincome_of_ebt` | `double` | 可请求字段 |  |
| `n_op_profit_of_ebt` | `double` | 可请求字段 |  |
| `tax_to_ebt` | `double` | 可请求字段 |  |
| `dtprofit_to_profit` | `double` | 可请求字段 |  |
| `salescash_to_or` | `double` | 可请求字段 |  |
| `ocf_to_or` | `double` | 可请求字段 |  |
| `ocf_to_opincome` | `double` | 可请求字段 |  |
| `capitalized_to_da` | `double` | 可请求字段 |  |
| `debt_to_assets` | `double` | 可请求字段 |  |
| `assets_to_eqt` | `double` | 可请求字段 |  |
| `dp_assets_to_eqt` | `double` | 可请求字段 |  |
| `ca_to_assets` | `double` | 可请求字段 |  |
| `nca_to_assets` | `double` | 可请求字段 |  |
| `tbassets_to_totalassets` | `double` | 可请求字段 |  |
| `int_to_talcap` | `double` | 可请求字段 |  |
| `eqt_to_talcapital` | `double` | 可请求字段 |  |
| `currentdebt_to_debt` | `double` | 可请求字段 |  |
| `longdeb_to_debt` | `double` | 可请求字段 |  |
| `ocf_to_shortdebt` | `double` | 可请求字段 |  |
| `debt_to_eqt` | `double` | 可请求字段 |  |
| `eqt_to_debt` | `double` | 可请求字段 |  |
| `eqt_to_interestdebt` | `double` | 可请求字段 |  |
| `tangibleasset_to_debt` | `double` | 可请求字段 |  |
| `tangasset_to_intdebt` | `double` | 可请求字段 |  |
| `tangibleasset_to_netdebt` | `double` | 可请求字段 |  |
| `ocf_to_debt` | `double` | 可请求字段 |  |
| `ocf_to_interestdebt` | `double` | 可请求字段 |  |
| `ocf_to_netdebt` | `double` | 可请求字段 |  |
| `ebit_to_interest` | `double` | 可请求字段 |  |
| `longdebt_to_workingcapital` | `double` | 可请求字段 |  |
| `ebitda_to_debt` | `double` | 可请求字段 |  |
| `turn_days` | `double` | 可请求字段 |  |
| `roa_yearly` | `double` | 可请求字段 |  |
| `roa_dp` | `double` | 可请求字段 |  |
| `fixed_assets` | `double` | 可请求字段 |  |
| `profit_prefin_exp` | `double` | 可请求字段 |  |
| `non_op_profit` | `double` | 可请求字段 |  |
| `op_to_ebt` | `double` | 可请求字段 |  |
| `nop_to_ebt` | `double` | 可请求字段 |  |
| `ocf_to_profit` | `double` | 可请求字段 |  |
| `cash_to_liqdebt` | `double` | 可请求字段 |  |
| `cash_to_liqdebt_withinterest` | `double` | 可请求字段 |  |
| `op_to_liqdebt` | `double` | 可请求字段 |  |
| `op_to_debt` | `double` | 可请求字段 |  |
| `roic_yearly` | `double` | 可请求字段 |  |
| `total_fa_trun` | `double` | 可请求字段 |  |
| `profit_to_op` | `double` | 可请求字段 |  |
| `q_opincome` | `double` | 可请求字段 |  |
| `q_investincome` | `double` | 可请求字段 |  |
| `q_dtprofit` | `double` | 可请求字段 |  |
| `q_eps` | `double` | 可请求字段 |  |
| `q_netprofit_margin` | `double` | 可请求字段 |  |
| `q_gsprofit_margin` | `double` | 可请求字段 |  |
| `q_exp_to_sales` | `double` | 可请求字段 |  |
| `q_profit_to_gr` | `double` | 可请求字段 |  |
| `q_saleexp_to_gr` | `double` | 可请求字段 |  |
| `q_adminexp_to_gr` | `double` | 可请求字段 |  |
| `q_finaexp_to_gr` | `double` | 可请求字段 |  |
| `q_impair_to_gr_ttm` | `double` | 可请求字段 |  |
| `q_gc_to_gr` | `double` | 可请求字段 |  |
| `q_op_to_gr` | `double` | 可请求字段 |  |
| `q_roe` | `double` | 可请求字段 |  |
| `q_dt_roe` | `double` | 可请求字段 |  |
| `q_npta` | `double` | 可请求字段 |  |
| `q_opincome_to_ebt` | `double` | 可请求字段 |  |
| `q_investincome_to_ebt` | `double` | 可请求字段 |  |
| `q_dtprofit_to_profit` | `double` | 可请求字段 |  |
| `q_salescash_to_or` | `double` | 可请求字段 |  |
| `q_ocf_to_sales` | `double` | 可请求字段 |  |
| `q_ocf_to_or` | `double` | 可请求字段 |  |
| `basic_eps_yoy` | `double` | 可请求字段 |  |
| `dt_eps_yoy` | `double` | 可请求字段 |  |
| `cfps_yoy` | `double` | 可请求字段 |  |
| `op_yoy` | `double` | 可请求字段 |  |
| `ebt_yoy` | `double` | 可请求字段 |  |
| `netprofit_yoy` | `double` | 可请求字段 |  |
| `dt_netprofit_yoy` | `double` | 可请求字段 |  |
| `ocf_yoy` | `double` | 可请求字段 |  |
| `roe_yoy` | `double` | 可请求字段 |  |
| `bps_yoy` | `double` | 可请求字段 |  |
| `assets_yoy` | `double` | 可请求字段 |  |
| `eqt_yoy` | `double` | 可请求字段 |  |
| `tr_yoy` | `double` | 可请求字段 |  |
| `or_yoy` | `double` | 可请求字段 |  |
| `q_gr_yoy` | `double` | 可请求字段 |  |
| `q_gr_qoq` | `double` | 可请求字段 |  |
| `q_sales_yoy` | `double` | 可请求字段 |  |
| `q_sales_qoq` | `double` | 可请求字段 |  |
| `q_op_yoy` | `double` | 可请求字段 |  |
| `q_op_qoq` | `double` | 可请求字段 |  |
| `q_profit_yoy` | `double` | 可请求字段 |  |
| `q_profit_qoq` | `double` | 可请求字段 |  |
| `q_netprofit_yoy` | `double` | 可请求字段 |  |
| `q_netprofit_qoq` | `double` | 可请求字段 |  |
| `equity_yoy` | `double` | 可请求字段 |  |
| `rd_exp` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `express`

- 来源：Tushare `express`（业绩快报）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：普通接口查询需要传入 `instruments`；对应 `_vip` 数据集支持 `instruments=None` 全市场查询。

宽表 `fields` 可选字段：`ann_date`, `revenue`, `operate_profit`, `total_profit`, `n_income`, `total_assets`, `total_hldr_eqy_exc_min_int`, `diluted_eps`, `diluted_roe`, `yoy_net_profit`, `bps`, `yoy_sales`, `yoy_op`, `yoy_tp`, `yoy_dedu_np`, `yoy_eps`, `yoy_roe`, `growth_assets`, `yoy_equity`, `growth_bps`, `or_last_year`, `op_last_year`, `tp_last_year`, `np_last_year`, `eps_last_year`, `open_net_assets`, `open_bps`, `perf_summary`, `is_audit`, `remark`。

```python
panels = data.get_panel(
    'express',
    fields=['revenue', 'n_income'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['revenue']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'express',
    fields=['revenue', 'n_income'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `revenue` | `double` | 可请求字段 |  |
| `operate_profit` | `double` | 可请求字段 |  |
| `total_profit` | `double` | 可请求字段 |  |
| `n_income` | `double` | 可请求字段 |  |
| `total_assets` | `double` | 可请求字段 |  |
| `total_hldr_eqy_exc_min_int` | `double` | 可请求字段 |  |
| `diluted_eps` | `double` | 可请求字段 |  |
| `diluted_roe` | `double` | 可请求字段 |  |
| `yoy_net_profit` | `double` | 可请求字段 |  |
| `bps` | `double` | 可请求字段 |  |
| `yoy_sales` | `double` | 可请求字段 |  |
| `yoy_op` | `double` | 可请求字段 |  |
| `yoy_tp` | `double` | 可请求字段 |  |
| `yoy_dedu_np` | `double` | 可请求字段 |  |
| `yoy_eps` | `double` | 可请求字段 |  |
| `yoy_roe` | `double` | 可请求字段 |  |
| `growth_assets` | `double` | 可请求字段 |  |
| `yoy_equity` | `double` | 可请求字段 |  |
| `growth_bps` | `double` | 可请求字段 |  |
| `or_last_year` | `double` | 可请求字段 |  |
| `op_last_year` | `double` | 可请求字段 |  |
| `tp_last_year` | `double` | 可请求字段 |  |
| `np_last_year` | `double` | 可请求字段 |  |
| `eps_last_year` | `double` | 可请求字段 |  |
| `open_net_assets` | `double` | 可请求字段 |  |
| `open_bps` | `double` | 可请求字段 |  |
| `perf_summary` | `string` | 可请求字段 |  |
| `is_audit` | `int64` | 可请求字段 |  |
| `remark` | `string` | 可请求字段 |  |

## `express_vip`

- 来源：Tushare `express_vip`（业绩快报 VIP）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：VIP 接口支持 `instruments=None` 全市场查询，也可以传股票池。

宽表 `fields` 可选字段：`ann_date`, `revenue`, `operate_profit`, `total_profit`, `n_income`, `total_assets`, `total_hldr_eqy_exc_min_int`, `diluted_eps`, `diluted_roe`, `yoy_net_profit`, `bps`, `yoy_sales`, `yoy_op`, `yoy_tp`, `yoy_dedu_np`, `yoy_eps`, `yoy_roe`, `growth_assets`, `yoy_equity`, `growth_bps`, `or_last_year`, `op_last_year`, `tp_last_year`, `np_last_year`, `eps_last_year`, `open_net_assets`, `open_bps`, `perf_summary`, `is_audit`, `remark`。

```python
panels = data.get_panel(
    'express_vip',
    fields=['revenue', 'n_income'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
first_panel = panels['revenue']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'express_vip',
    fields=['revenue', 'n_income'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `revenue` | `double` | 可请求字段 |  |
| `operate_profit` | `double` | 可请求字段 |  |
| `total_profit` | `double` | 可请求字段 |  |
| `n_income` | `double` | 可请求字段 |  |
| `total_assets` | `double` | 可请求字段 |  |
| `total_hldr_eqy_exc_min_int` | `double` | 可请求字段 |  |
| `diluted_eps` | `double` | 可请求字段 |  |
| `diluted_roe` | `double` | 可请求字段 |  |
| `yoy_net_profit` | `double` | 可请求字段 |  |
| `bps` | `double` | 可请求字段 |  |
| `yoy_sales` | `double` | 可请求字段 |  |
| `yoy_op` | `double` | 可请求字段 |  |
| `yoy_tp` | `double` | 可请求字段 |  |
| `yoy_dedu_np` | `double` | 可请求字段 |  |
| `yoy_eps` | `double` | 可请求字段 |  |
| `yoy_roe` | `double` | 可请求字段 |  |
| `growth_assets` | `double` | 可请求字段 |  |
| `yoy_equity` | `double` | 可请求字段 |  |
| `growth_bps` | `double` | 可请求字段 |  |
| `or_last_year` | `double` | 可请求字段 |  |
| `op_last_year` | `double` | 可请求字段 |  |
| `tp_last_year` | `double` | 可请求字段 |  |
| `np_last_year` | `double` | 可请求字段 |  |
| `eps_last_year` | `double` | 可请求字段 |  |
| `open_net_assets` | `double` | 可请求字段 |  |
| `open_bps` | `double` | 可请求字段 |  |
| `perf_summary` | `string` | 可请求字段 |  |
| `is_audit` | `int64` | 可请求字段 |  |
| `remark` | `string` | 可请求字段 |  |

## `forecast`

- 来源：Tushare `forecast`（业绩预告）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：普通接口查询需要传入 `instruments`；对应 `_vip` 数据集支持 `instruments=None` 全市场查询。

宽表 `fields` 可选字段：`ann_date`, `type`, `p_change_min`, `p_change_max`, `net_profit_min`, `net_profit_max`, `last_parent_net`, `first_ann_date`, `summary`, `change_reason`。

```python
panels = data.get_panel(
    'forecast',
    fields=['type', 'p_change_min', 'p_change_max'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['type']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'forecast',
    fields=['type', 'p_change_min', 'p_change_max'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `type` | `string` | 可请求字段 |  |
| `p_change_min` | `double` | 可请求字段 |  |
| `p_change_max` | `double` | 可请求字段 |  |
| `net_profit_min` | `double` | 可请求字段 |  |
| `net_profit_max` | `double` | 可请求字段 |  |
| `last_parent_net` | `double` | 可请求字段 |  |
| `first_ann_date` | `date32[day]` | 可请求字段 |  |
| `summary` | `string` | 可请求字段 |  |
| `change_reason` | `string` | 可请求字段 |  |

## `forecast_vip`

- 来源：Tushare `forecast_vip`（业绩预告 VIP）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：VIP 接口支持 `instruments=None` 全市场查询，也可以传股票池。

宽表 `fields` 可选字段：`ann_date`, `type`, `p_change_min`, `p_change_max`, `net_profit_min`, `net_profit_max`, `last_parent_net`, `first_ann_date`, `summary`, `change_reason`。

```python
panels = data.get_panel(
    'forecast_vip',
    fields=['type', 'p_change_min', 'p_change_max'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
first_panel = panels['type']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'forecast_vip',
    fields=['type', 'p_change_min', 'p_change_max'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `type` | `string` | 可请求字段 |  |
| `p_change_min` | `double` | 可请求字段 |  |
| `p_change_max` | `double` | 可请求字段 |  |
| `net_profit_min` | `double` | 可请求字段 |  |
| `net_profit_max` | `double` | 可请求字段 |  |
| `last_parent_net` | `double` | 可请求字段 |  |
| `first_ann_date` | `date32[day]` | 可请求字段 |  |
| `summary` | `string` | 可请求字段 |  |
| `change_reason` | `string` | 可请求字段 |  |

## `stk_holdernumber`

- 来源：Tushare `stk_holdernumber`（股东人数）
- 自动键列：`end_date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：`instruments=None` 时不传 `ts_code`，可读取全市场股东人数。

宽表 `fields` 可选字段：`ann_date`, `holder_num`。

```python
panels = data.get_panel(
    'stk_holdernumber',
    fields=['holder_num'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
first_panel = panels['holder_num']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'stk_holdernumber',
    fields=['holder_num'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `holder_num` | `int64` | 可请求字段 |  |

## `ci_index_member`

- 来源：Tushare `ci_index_member`（中信行业成分）
- 自动键列：`date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：后端会把 `in_date` / `out_date` 成分区间按交易日历展开为日频。

宽表 `fields` 可选字段：`l1_code`, `l1_name`, `l2_code`, `l2_name`, `l3_code`, `l3_name`, `name`, `in_date`, `out_date`, `is_new`。

```python
panels = data.get_panel(
    'ci_index_member',
    fields=['l1_name', 'l2_name', 'l3_name'],
    start='2024-01-01',
    end='2024-12-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['l1_name']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'ci_index_member',
    fields=['l1_name', 'l2_name', 'l3_name'],
    start='2024-01-01',
    end='2024-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `date` | `date32[day]` | 自动键列 |  |
| `l1_code` | `string` | 可请求字段 |  |
| `l1_name` | `string` | 可请求字段 |  |
| `l2_code` | `string` | 可请求字段 |  |
| `l2_name` | `string` | 可请求字段 |  |
| `l3_code` | `string` | 可请求字段 |  |
| `l3_name` | `string` | 可请求字段 |  |
| `ts_code` | `string` | 自动键列 |  |
| `name` | `string` | 可请求字段 |  |
| `in_date` | `date32[day]` | 可请求字段 |  |
| `out_date` | `date32[day]` | 可请求字段 |  |
| `is_new` | `string` | 可请求字段 |  |

## `index_member_all`

- 来源：Tushare `index_member_all`（申万行业成分）
- 自动键列：`date`、`ts_code`
- 可生成宽表：是
- 可返回长表：是
- 说明：后端会把 `in_date` / `out_date` 成分区间按交易日历展开为日频。

宽表 `fields` 可选字段：`l1_code`, `l1_name`, `l2_code`, `l2_name`, `l3_code`, `l3_name`, `name`, `in_date`, `out_date`, `is_new`。

```python
panels = data.get_panel(
    'index_member_all',
    fields=['l1_name', 'l2_name', 'l3_name'],
    start='2024-01-01',
    end='2024-12-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['l1_name']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'index_member_all',
    fields=['l1_name', 'l2_name', 'l3_name'],
    start='2024-01-01',
    end='2024-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `date` | `date32[day]` | 自动键列 |  |
| `l1_code` | `string` | 可请求字段 |  |
| `l1_name` | `string` | 可请求字段 |  |
| `l2_code` | `string` | 可请求字段 |  |
| `l2_name` | `string` | 可请求字段 |  |
| `l3_code` | `string` | 可请求字段 |  |
| `l3_name` | `string` | 可请求字段 |  |
| `ts_code` | `string` | 自动键列 |  |
| `name` | `string` | 可请求字段 |  |
| `in_date` | `date32[day]` | 可请求字段 |  |
| `out_date` | `date32[day]` | 可请求字段 |  |
| `is_new` | `string` | 可请求字段 |  |

## `stk_holdertrade`

- 来源：Tushare `stk_holdertrade`（股东增减持事件）
- 自动键列：`ann_date`、`ts_code`
- 可生成宽表：否
- 可返回长表：是
- 说明：同一公告日同一股票可能有多名股东多笔增减持，只能用 `get_table()` 保留事件明细。

宽表：不支持。

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'stk_holdertrade',
    fields=['holder_name', 'in_de', 'change_vol'],
    start='2019-04-01',
    end='2019-04-30',
    instruments=['300216.SZ'],
    limit=100_000,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 自动键列 |  |
| `holder_name` | `string` | 可请求字段 |  |
| `holder_type` | `string` | 可请求字段 |  |
| `in_de` | `string` | 可请求字段 |  |
| `change_vol` | `double` | 可请求字段 |  |
| `change_ratio` | `double` | 可请求字段 |  |
| `after_share` | `double` | 可请求字段 |  |
| `after_ratio` | `double` | 可请求字段 |  |
| `avg_price` | `double` | 可请求字段 |  |
| `total_share` | `double` | 可请求字段 |  |
| `begin_date` | `date32[day]` | 可请求字段 |  |
| `close_date` | `date32[day]` | 可请求字段 |  |

## `income_pit`

- 来源：Tushare `income`（利润表 PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`f_ann_date`；默认 `disclosure_lag=1`。
- 说明：普通 PIT 数据集需要传入 `instruments`；对应 `_vip_pit` 数据集支持 `instruments=None`。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `report_type`, `comp_type`, `end_type`, `basic_eps`, `diluted_eps`, `total_revenue`, `revenue`, `int_income`, `prem_earned`, `comm_income`, `n_commis_income`, `n_oth_income`, `n_oth_b_income`, `prem_income`, `out_prem`, `une_prem_reser`, `reins_income`, `n_sec_tb_income`, `n_sec_uw_income`, `n_asset_mg_income`, `oth_b_income`, `fv_value_chg_gain`, `invest_income`, `ass_invest_income`, `forex_gain`, `total_cogs`, `oper_cost`, `int_exp`, `comm_exp`, `biz_tax_surchg`, `sell_exp`, `admin_exp`, `fin_exp`, `assets_impair_loss`, `prem_refund`, `compens_payout`, `reser_insur_liab`, `div_payt`, `reins_exp`, `oper_exp`, `compens_payout_refu`, `insur_reser_refu`, `reins_cost_refund`, `other_bus_cost`, `operate_profit`, `non_oper_income`, `non_oper_exp`, `nca_disploss`, `total_profit`, `income_tax`, `n_income`, `n_income_attr_p`, `minority_gain`, `oth_compr_income`, `t_compr_income`, `compr_inc_attr_p`, `compr_inc_attr_m_s`, `ebit`, `ebitda`, `insurance_exp`, `undist_profit`, `distable_profit`, `rd_exp`, `fin_exp_int_exp`, `fin_exp_int_inc`, `transfer_surplus_rese`, `transfer_housing_imprest`, `transfer_oth`, `adj_lossgain`, `withdra_legal_surplus`, `withdra_legal_pubfund`, `withdra_biz_devfund`, `withdra_rese_fund`, `withdra_oth_ersu`, `workers_welfare`, `distr_profit_shrhder`, `prfshare_payable_dvd`, `comshare_payable_dvd`, `capit_comstock_div`, `continued_net_profit`, `update_flag`。

```python
panels = data.get_panel(
    'income_pit',
    fields=['basic_eps', 'total_revenue', 'n_income_attr_p'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['basic_eps']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'income_pit',
    fields=['basic_eps', 'total_revenue', 'n_income_attr_p'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `report_type` | `string` | 可请求字段 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `basic_eps` | `double` | 可请求字段 |  |
| `diluted_eps` | `double` | 可请求字段 |  |
| `total_revenue` | `double` | 可请求字段 |  |
| `revenue` | `double` | 可请求字段 |  |
| `int_income` | `double` | 可请求字段 |  |
| `prem_earned` | `double` | 可请求字段 |  |
| `comm_income` | `double` | 可请求字段 |  |
| `n_commis_income` | `double` | 可请求字段 |  |
| `n_oth_income` | `double` | 可请求字段 |  |
| `n_oth_b_income` | `double` | 可请求字段 |  |
| `prem_income` | `double` | 可请求字段 |  |
| `out_prem` | `double` | 可请求字段 |  |
| `une_prem_reser` | `double` | 可请求字段 |  |
| `reins_income` | `double` | 可请求字段 |  |
| `n_sec_tb_income` | `double` | 可请求字段 |  |
| `n_sec_uw_income` | `double` | 可请求字段 |  |
| `n_asset_mg_income` | `double` | 可请求字段 |  |
| `oth_b_income` | `double` | 可请求字段 |  |
| `fv_value_chg_gain` | `double` | 可请求字段 |  |
| `invest_income` | `double` | 可请求字段 |  |
| `ass_invest_income` | `double` | 可请求字段 |  |
| `forex_gain` | `double` | 可请求字段 |  |
| `total_cogs` | `double` | 可请求字段 |  |
| `oper_cost` | `double` | 可请求字段 |  |
| `int_exp` | `double` | 可请求字段 |  |
| `comm_exp` | `double` | 可请求字段 |  |
| `biz_tax_surchg` | `double` | 可请求字段 |  |
| `sell_exp` | `double` | 可请求字段 |  |
| `admin_exp` | `double` | 可请求字段 |  |
| `fin_exp` | `double` | 可请求字段 |  |
| `assets_impair_loss` | `double` | 可请求字段 |  |
| `prem_refund` | `double` | 可请求字段 |  |
| `compens_payout` | `double` | 可请求字段 |  |
| `reser_insur_liab` | `double` | 可请求字段 |  |
| `div_payt` | `double` | 可请求字段 |  |
| `reins_exp` | `double` | 可请求字段 |  |
| `oper_exp` | `double` | 可请求字段 |  |
| `compens_payout_refu` | `double` | 可请求字段 |  |
| `insur_reser_refu` | `double` | 可请求字段 |  |
| `reins_cost_refund` | `double` | 可请求字段 |  |
| `other_bus_cost` | `double` | 可请求字段 |  |
| `operate_profit` | `double` | 可请求字段 |  |
| `non_oper_income` | `double` | 可请求字段 |  |
| `non_oper_exp` | `double` | 可请求字段 |  |
| `nca_disploss` | `double` | 可请求字段 |  |
| `total_profit` | `double` | 可请求字段 |  |
| `income_tax` | `double` | 可请求字段 |  |
| `n_income` | `double` | 可请求字段 |  |
| `n_income_attr_p` | `double` | 可请求字段 |  |
| `minority_gain` | `double` | 可请求字段 |  |
| `oth_compr_income` | `double` | 可请求字段 |  |
| `t_compr_income` | `double` | 可请求字段 |  |
| `compr_inc_attr_p` | `double` | 可请求字段 |  |
| `compr_inc_attr_m_s` | `double` | 可请求字段 |  |
| `ebit` | `double` | 可请求字段 |  |
| `ebitda` | `double` | 可请求字段 |  |
| `insurance_exp` | `double` | 可请求字段 |  |
| `undist_profit` | `double` | 可请求字段 |  |
| `distable_profit` | `double` | 可请求字段 |  |
| `rd_exp` | `double` | 可请求字段 |  |
| `fin_exp_int_exp` | `double` | 可请求字段 |  |
| `fin_exp_int_inc` | `double` | 可请求字段 |  |
| `transfer_surplus_rese` | `double` | 可请求字段 |  |
| `transfer_housing_imprest` | `double` | 可请求字段 |  |
| `transfer_oth` | `double` | 可请求字段 |  |
| `adj_lossgain` | `double` | 可请求字段 |  |
| `withdra_legal_surplus` | `double` | 可请求字段 |  |
| `withdra_legal_pubfund` | `double` | 可请求字段 |  |
| `withdra_biz_devfund` | `double` | 可请求字段 |  |
| `withdra_rese_fund` | `double` | 可请求字段 |  |
| `withdra_oth_ersu` | `double` | 可请求字段 |  |
| `workers_welfare` | `double` | 可请求字段 |  |
| `distr_profit_shrhder` | `double` | 可请求字段 |  |
| `prfshare_payable_dvd` | `double` | 可请求字段 |  |
| `comshare_payable_dvd` | `double` | 可请求字段 |  |
| `capit_comstock_div` | `double` | 可请求字段 |  |
| `continued_net_profit` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `income_vip_pit`

- 来源：Tushare `income_vip`（利润表 VIP PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`f_ann_date`；默认 `disclosure_lag=1`。
- 说明：支持 `instruments=None` 全市场 PIT 面板。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `report_type`, `comp_type`, `end_type`, `basic_eps`, `diluted_eps`, `total_revenue`, `revenue`, `int_income`, `prem_earned`, `comm_income`, `n_commis_income`, `n_oth_income`, `n_oth_b_income`, `prem_income`, `out_prem`, `une_prem_reser`, `reins_income`, `n_sec_tb_income`, `n_sec_uw_income`, `n_asset_mg_income`, `oth_b_income`, `fv_value_chg_gain`, `invest_income`, `ass_invest_income`, `forex_gain`, `total_cogs`, `oper_cost`, `int_exp`, `comm_exp`, `biz_tax_surchg`, `sell_exp`, `admin_exp`, `fin_exp`, `assets_impair_loss`, `prem_refund`, `compens_payout`, `reser_insur_liab`, `div_payt`, `reins_exp`, `oper_exp`, `compens_payout_refu`, `insur_reser_refu`, `reins_cost_refund`, `other_bus_cost`, `operate_profit`, `non_oper_income`, `non_oper_exp`, `nca_disploss`, `total_profit`, `income_tax`, `n_income`, `n_income_attr_p`, `minority_gain`, `oth_compr_income`, `t_compr_income`, `compr_inc_attr_p`, `compr_inc_attr_m_s`, `ebit`, `ebitda`, `insurance_exp`, `undist_profit`, `distable_profit`, `rd_exp`, `fin_exp_int_exp`, `fin_exp_int_inc`, `transfer_surplus_rese`, `transfer_housing_imprest`, `transfer_oth`, `adj_lossgain`, `withdra_legal_surplus`, `withdra_legal_pubfund`, `withdra_biz_devfund`, `withdra_rese_fund`, `withdra_oth_ersu`, `workers_welfare`, `distr_profit_shrhder`, `prfshare_payable_dvd`, `comshare_payable_dvd`, `capit_comstock_div`, `continued_net_profit`, `update_flag`。

```python
panels = data.get_panel(
    'income_vip_pit',
    fields=['basic_eps', 'total_revenue', 'n_income_attr_p'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=None,
)
first_panel = panels['basic_eps']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'income_vip_pit',
    fields=['basic_eps', 'total_revenue', 'n_income_attr_p'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `report_type` | `string` | 可请求字段 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `basic_eps` | `double` | 可请求字段 |  |
| `diluted_eps` | `double` | 可请求字段 |  |
| `total_revenue` | `double` | 可请求字段 |  |
| `revenue` | `double` | 可请求字段 |  |
| `int_income` | `double` | 可请求字段 |  |
| `prem_earned` | `double` | 可请求字段 |  |
| `comm_income` | `double` | 可请求字段 |  |
| `n_commis_income` | `double` | 可请求字段 |  |
| `n_oth_income` | `double` | 可请求字段 |  |
| `n_oth_b_income` | `double` | 可请求字段 |  |
| `prem_income` | `double` | 可请求字段 |  |
| `out_prem` | `double` | 可请求字段 |  |
| `une_prem_reser` | `double` | 可请求字段 |  |
| `reins_income` | `double` | 可请求字段 |  |
| `n_sec_tb_income` | `double` | 可请求字段 |  |
| `n_sec_uw_income` | `double` | 可请求字段 |  |
| `n_asset_mg_income` | `double` | 可请求字段 |  |
| `oth_b_income` | `double` | 可请求字段 |  |
| `fv_value_chg_gain` | `double` | 可请求字段 |  |
| `invest_income` | `double` | 可请求字段 |  |
| `ass_invest_income` | `double` | 可请求字段 |  |
| `forex_gain` | `double` | 可请求字段 |  |
| `total_cogs` | `double` | 可请求字段 |  |
| `oper_cost` | `double` | 可请求字段 |  |
| `int_exp` | `double` | 可请求字段 |  |
| `comm_exp` | `double` | 可请求字段 |  |
| `biz_tax_surchg` | `double` | 可请求字段 |  |
| `sell_exp` | `double` | 可请求字段 |  |
| `admin_exp` | `double` | 可请求字段 |  |
| `fin_exp` | `double` | 可请求字段 |  |
| `assets_impair_loss` | `double` | 可请求字段 |  |
| `prem_refund` | `double` | 可请求字段 |  |
| `compens_payout` | `double` | 可请求字段 |  |
| `reser_insur_liab` | `double` | 可请求字段 |  |
| `div_payt` | `double` | 可请求字段 |  |
| `reins_exp` | `double` | 可请求字段 |  |
| `oper_exp` | `double` | 可请求字段 |  |
| `compens_payout_refu` | `double` | 可请求字段 |  |
| `insur_reser_refu` | `double` | 可请求字段 |  |
| `reins_cost_refund` | `double` | 可请求字段 |  |
| `other_bus_cost` | `double` | 可请求字段 |  |
| `operate_profit` | `double` | 可请求字段 |  |
| `non_oper_income` | `double` | 可请求字段 |  |
| `non_oper_exp` | `double` | 可请求字段 |  |
| `nca_disploss` | `double` | 可请求字段 |  |
| `total_profit` | `double` | 可请求字段 |  |
| `income_tax` | `double` | 可请求字段 |  |
| `n_income` | `double` | 可请求字段 |  |
| `n_income_attr_p` | `double` | 可请求字段 |  |
| `minority_gain` | `double` | 可请求字段 |  |
| `oth_compr_income` | `double` | 可请求字段 |  |
| `t_compr_income` | `double` | 可请求字段 |  |
| `compr_inc_attr_p` | `double` | 可请求字段 |  |
| `compr_inc_attr_m_s` | `double` | 可请求字段 |  |
| `ebit` | `double` | 可请求字段 |  |
| `ebitda` | `double` | 可请求字段 |  |
| `insurance_exp` | `double` | 可请求字段 |  |
| `undist_profit` | `double` | 可请求字段 |  |
| `distable_profit` | `double` | 可请求字段 |  |
| `rd_exp` | `double` | 可请求字段 |  |
| `fin_exp_int_exp` | `double` | 可请求字段 |  |
| `fin_exp_int_inc` | `double` | 可请求字段 |  |
| `transfer_surplus_rese` | `double` | 可请求字段 |  |
| `transfer_housing_imprest` | `double` | 可请求字段 |  |
| `transfer_oth` | `double` | 可请求字段 |  |
| `adj_lossgain` | `double` | 可请求字段 |  |
| `withdra_legal_surplus` | `double` | 可请求字段 |  |
| `withdra_legal_pubfund` | `double` | 可请求字段 |  |
| `withdra_biz_devfund` | `double` | 可请求字段 |  |
| `withdra_rese_fund` | `double` | 可请求字段 |  |
| `withdra_oth_ersu` | `double` | 可请求字段 |  |
| `workers_welfare` | `double` | 可请求字段 |  |
| `distr_profit_shrhder` | `double` | 可请求字段 |  |
| `prfshare_payable_dvd` | `double` | 可请求字段 |  |
| `comshare_payable_dvd` | `double` | 可请求字段 |  |
| `capit_comstock_div` | `double` | 可请求字段 |  |
| `continued_net_profit` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `balancesheet_pit`

- 来源：Tushare `balancesheet`（资产负债表 PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`f_ann_date`；默认 `disclosure_lag=1`。
- 说明：普通 PIT 数据集需要传入 `instruments`；对应 `_vip_pit` 数据集支持 `instruments=None`。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `report_type`, `comp_type`, `end_type`, `total_share`, `cap_rese`, `undistr_porfit`, `surplus_rese`, `special_rese`, `money_cap`, `trad_asset`, `notes_receiv`, `accounts_receiv`, `oth_receiv`, `prepayment`, `div_receiv`, `int_receiv`, `inventories`, `amor_exp`, `nca_within_1y`, `sett_rsrv`, `loanto_oth_bank_fi`, `premium_receiv`, `reinsur_receiv`, `reinsur_res_receiv`, `pur_resale_fa`, `oth_cur_assets`, `total_cur_assets`, `fa_avail_for_sale`, `htm_invest`, `lt_eqt_invest`, `invest_real_estate`, `time_deposits`, `oth_assets`, `lt_rec`, `fix_assets`, `cip`, `const_materials`, `fixed_assets_disp`, `produc_bio_assets`, `oil_and_gas_assets`, `intan_assets`, `r_and_d`, `goodwill`, `lt_amor_exp`, `defer_tax_assets`, `decr_in_disbur`, `oth_nca`, `total_nca`, `cash_reser_cb`, `depos_in_oth_bfi`, `prec_metals`, `deriv_assets`, `rr_reins_une_prem`, `rr_reins_outstd_cla`, `rr_reins_lins_liab`, `rr_reins_lthins_liab`, `refund_depos`, `ph_pledge_loans`, `refund_cap_depos`, `indep_acct_assets`, `client_depos`, `client_prov`, `transac_seat_fee`, `invest_as_receiv`, `total_assets`, `lt_borr`, `st_borr`, `cb_borr`, `depos_ib_deposits`, `loan_oth_bank`, `trading_fl`, `notes_payable`, `acct_payable`, `adv_receipts`, `sold_for_repur_fa`, `comm_payable`, `payroll_payable`, `taxes_payable`, `int_payable`, `div_payable`, `oth_payable`, `acc_exp`, `deferred_inc`, `st_bonds_payable`, `payable_to_reinsurer`, `rsrv_insur_cont`, `acting_trading_sec`, `acting_uw_sec`, `non_cur_liab_due_1y`, `oth_cur_liab`, `total_cur_liab`, `bond_payable`, `lt_payable`, `specific_payables`, `estimated_liab`, `defer_tax_liab`, `defer_inc_non_cur_liab`, `oth_ncl`, `total_ncl`, `depos_oth_bfi`, `deriv_liab`, `depos`, `agency_bus_liab`, `oth_liab`, `prem_receiv_adva`, `depos_received`, `ph_invest`, `reser_une_prem`, `reser_outstd_claims`, `reser_lins_liab`, `reser_lthins_liab`, `indept_acc_liab`, `pledge_borr`, `indem_payable`, `policy_div_payable`, `total_liab`, `treasury_share`, `ordin_risk_reser`, `forex_differ`, `invest_loss_unconf`, `minority_int`, `total_hldr_eqy_exc_min_int`, `total_hldr_eqy_inc_min_int`, `total_liab_hldr_eqy`, `lt_payroll_payable`, `oth_comp_income`, `oth_eqt_tools`, `oth_eqt_tools_p_shr`, `lending_funds`, `acc_receivable`, `st_fin_payable`, `payables`, `hfs_assets`, `hfs_sales`, `cost_fin_assets`, `fair_value_fin_assets`, `cip_total`, `oth_pay_total`, `long_pay_total`, `debt_invest`, `oth_debt_invest`, `contract_assets`, `contract_liab`, `accounts_receiv_bill`, `accounts_pay`, `oth_rcv_total`, `fix_assets_total`, `update_flag`。

```python
panels = data.get_panel(
    'balancesheet_pit',
    fields=['total_assets', 'total_liab'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['total_assets']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'balancesheet_pit',
    fields=['total_assets', 'total_liab'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `report_type` | `string` | 可请求字段 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `total_share` | `double` | 可请求字段 |  |
| `cap_rese` | `double` | 可请求字段 |  |
| `undistr_porfit` | `double` | 可请求字段 |  |
| `surplus_rese` | `double` | 可请求字段 |  |
| `special_rese` | `double` | 可请求字段 |  |
| `money_cap` | `double` | 可请求字段 |  |
| `trad_asset` | `double` | 可请求字段 |  |
| `notes_receiv` | `double` | 可请求字段 |  |
| `accounts_receiv` | `double` | 可请求字段 |  |
| `oth_receiv` | `double` | 可请求字段 |  |
| `prepayment` | `double` | 可请求字段 |  |
| `div_receiv` | `double` | 可请求字段 |  |
| `int_receiv` | `double` | 可请求字段 |  |
| `inventories` | `double` | 可请求字段 |  |
| `amor_exp` | `double` | 可请求字段 |  |
| `nca_within_1y` | `double` | 可请求字段 |  |
| `sett_rsrv` | `double` | 可请求字段 |  |
| `loanto_oth_bank_fi` | `double` | 可请求字段 |  |
| `premium_receiv` | `double` | 可请求字段 |  |
| `reinsur_receiv` | `double` | 可请求字段 |  |
| `reinsur_res_receiv` | `double` | 可请求字段 |  |
| `pur_resale_fa` | `double` | 可请求字段 |  |
| `oth_cur_assets` | `double` | 可请求字段 |  |
| `total_cur_assets` | `double` | 可请求字段 |  |
| `fa_avail_for_sale` | `double` | 可请求字段 |  |
| `htm_invest` | `double` | 可请求字段 |  |
| `lt_eqt_invest` | `double` | 可请求字段 |  |
| `invest_real_estate` | `double` | 可请求字段 |  |
| `time_deposits` | `double` | 可请求字段 |  |
| `oth_assets` | `double` | 可请求字段 |  |
| `lt_rec` | `double` | 可请求字段 |  |
| `fix_assets` | `double` | 可请求字段 |  |
| `cip` | `double` | 可请求字段 |  |
| `const_materials` | `double` | 可请求字段 |  |
| `fixed_assets_disp` | `double` | 可请求字段 |  |
| `produc_bio_assets` | `double` | 可请求字段 |  |
| `oil_and_gas_assets` | `double` | 可请求字段 |  |
| `intan_assets` | `double` | 可请求字段 |  |
| `r_and_d` | `double` | 可请求字段 |  |
| `goodwill` | `double` | 可请求字段 |  |
| `lt_amor_exp` | `double` | 可请求字段 |  |
| `defer_tax_assets` | `double` | 可请求字段 |  |
| `decr_in_disbur` | `double` | 可请求字段 |  |
| `oth_nca` | `double` | 可请求字段 |  |
| `total_nca` | `double` | 可请求字段 |  |
| `cash_reser_cb` | `double` | 可请求字段 |  |
| `depos_in_oth_bfi` | `double` | 可请求字段 |  |
| `prec_metals` | `double` | 可请求字段 |  |
| `deriv_assets` | `double` | 可请求字段 |  |
| `rr_reins_une_prem` | `double` | 可请求字段 |  |
| `rr_reins_outstd_cla` | `double` | 可请求字段 |  |
| `rr_reins_lins_liab` | `double` | 可请求字段 |  |
| `rr_reins_lthins_liab` | `double` | 可请求字段 |  |
| `refund_depos` | `double` | 可请求字段 |  |
| `ph_pledge_loans` | `double` | 可请求字段 |  |
| `refund_cap_depos` | `double` | 可请求字段 |  |
| `indep_acct_assets` | `double` | 可请求字段 |  |
| `client_depos` | `double` | 可请求字段 |  |
| `client_prov` | `double` | 可请求字段 |  |
| `transac_seat_fee` | `double` | 可请求字段 |  |
| `invest_as_receiv` | `double` | 可请求字段 |  |
| `total_assets` | `double` | 可请求字段 |  |
| `lt_borr` | `double` | 可请求字段 |  |
| `st_borr` | `double` | 可请求字段 |  |
| `cb_borr` | `double` | 可请求字段 |  |
| `depos_ib_deposits` | `double` | 可请求字段 |  |
| `loan_oth_bank` | `double` | 可请求字段 |  |
| `trading_fl` | `double` | 可请求字段 |  |
| `notes_payable` | `double` | 可请求字段 |  |
| `acct_payable` | `double` | 可请求字段 |  |
| `adv_receipts` | `double` | 可请求字段 |  |
| `sold_for_repur_fa` | `double` | 可请求字段 |  |
| `comm_payable` | `double` | 可请求字段 |  |
| `payroll_payable` | `double` | 可请求字段 |  |
| `taxes_payable` | `double` | 可请求字段 |  |
| `int_payable` | `double` | 可请求字段 |  |
| `div_payable` | `double` | 可请求字段 |  |
| `oth_payable` | `double` | 可请求字段 |  |
| `acc_exp` | `double` | 可请求字段 |  |
| `deferred_inc` | `double` | 可请求字段 |  |
| `st_bonds_payable` | `double` | 可请求字段 |  |
| `payable_to_reinsurer` | `double` | 可请求字段 |  |
| `rsrv_insur_cont` | `double` | 可请求字段 |  |
| `acting_trading_sec` | `double` | 可请求字段 |  |
| `acting_uw_sec` | `double` | 可请求字段 |  |
| `non_cur_liab_due_1y` | `double` | 可请求字段 |  |
| `oth_cur_liab` | `double` | 可请求字段 |  |
| `total_cur_liab` | `double` | 可请求字段 |  |
| `bond_payable` | `double` | 可请求字段 |  |
| `lt_payable` | `double` | 可请求字段 |  |
| `specific_payables` | `double` | 可请求字段 |  |
| `estimated_liab` | `double` | 可请求字段 |  |
| `defer_tax_liab` | `double` | 可请求字段 |  |
| `defer_inc_non_cur_liab` | `double` | 可请求字段 |  |
| `oth_ncl` | `double` | 可请求字段 |  |
| `total_ncl` | `double` | 可请求字段 |  |
| `depos_oth_bfi` | `double` | 可请求字段 |  |
| `deriv_liab` | `double` | 可请求字段 |  |
| `depos` | `double` | 可请求字段 |  |
| `agency_bus_liab` | `double` | 可请求字段 |  |
| `oth_liab` | `double` | 可请求字段 |  |
| `prem_receiv_adva` | `double` | 可请求字段 |  |
| `depos_received` | `double` | 可请求字段 |  |
| `ph_invest` | `double` | 可请求字段 |  |
| `reser_une_prem` | `double` | 可请求字段 |  |
| `reser_outstd_claims` | `double` | 可请求字段 |  |
| `reser_lins_liab` | `double` | 可请求字段 |  |
| `reser_lthins_liab` | `double` | 可请求字段 |  |
| `indept_acc_liab` | `double` | 可请求字段 |  |
| `pledge_borr` | `double` | 可请求字段 |  |
| `indem_payable` | `double` | 可请求字段 |  |
| `policy_div_payable` | `double` | 可请求字段 |  |
| `total_liab` | `double` | 可请求字段 |  |
| `treasury_share` | `double` | 可请求字段 |  |
| `ordin_risk_reser` | `double` | 可请求字段 |  |
| `forex_differ` | `double` | 可请求字段 |  |
| `invest_loss_unconf` | `double` | 可请求字段 |  |
| `minority_int` | `double` | 可请求字段 |  |
| `total_hldr_eqy_exc_min_int` | `double` | 可请求字段 |  |
| `total_hldr_eqy_inc_min_int` | `double` | 可请求字段 |  |
| `total_liab_hldr_eqy` | `double` | 可请求字段 |  |
| `lt_payroll_payable` | `double` | 可请求字段 |  |
| `oth_comp_income` | `double` | 可请求字段 |  |
| `oth_eqt_tools` | `double` | 可请求字段 |  |
| `oth_eqt_tools_p_shr` | `double` | 可请求字段 |  |
| `lending_funds` | `double` | 可请求字段 |  |
| `acc_receivable` | `double` | 可请求字段 |  |
| `st_fin_payable` | `double` | 可请求字段 |  |
| `payables` | `double` | 可请求字段 |  |
| `hfs_assets` | `double` | 可请求字段 |  |
| `hfs_sales` | `double` | 可请求字段 |  |
| `cost_fin_assets` | `double` | 可请求字段 |  |
| `fair_value_fin_assets` | `double` | 可请求字段 |  |
| `cip_total` | `double` | 可请求字段 |  |
| `oth_pay_total` | `double` | 可请求字段 |  |
| `long_pay_total` | `double` | 可请求字段 |  |
| `debt_invest` | `double` | 可请求字段 |  |
| `oth_debt_invest` | `double` | 可请求字段 |  |
| `contract_assets` | `double` | 可请求字段 |  |
| `contract_liab` | `double` | 可请求字段 |  |
| `accounts_receiv_bill` | `double` | 可请求字段 |  |
| `accounts_pay` | `double` | 可请求字段 |  |
| `oth_rcv_total` | `double` | 可请求字段 |  |
| `fix_assets_total` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `balancesheet_vip_pit`

- 来源：Tushare `balancesheet_vip`（资产负债表 VIP PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`f_ann_date`；默认 `disclosure_lag=1`。
- 说明：支持 `instruments=None` 全市场 PIT 面板。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `report_type`, `comp_type`, `end_type`, `total_share`, `cap_rese`, `undistr_porfit`, `surplus_rese`, `special_rese`, `money_cap`, `trad_asset`, `notes_receiv`, `accounts_receiv`, `oth_receiv`, `prepayment`, `div_receiv`, `int_receiv`, `inventories`, `amor_exp`, `nca_within_1y`, `sett_rsrv`, `loanto_oth_bank_fi`, `premium_receiv`, `reinsur_receiv`, `reinsur_res_receiv`, `pur_resale_fa`, `oth_cur_assets`, `total_cur_assets`, `fa_avail_for_sale`, `htm_invest`, `lt_eqt_invest`, `invest_real_estate`, `time_deposits`, `oth_assets`, `lt_rec`, `fix_assets`, `cip`, `const_materials`, `fixed_assets_disp`, `produc_bio_assets`, `oil_and_gas_assets`, `intan_assets`, `r_and_d`, `goodwill`, `lt_amor_exp`, `defer_tax_assets`, `decr_in_disbur`, `oth_nca`, `total_nca`, `cash_reser_cb`, `depos_in_oth_bfi`, `prec_metals`, `deriv_assets`, `rr_reins_une_prem`, `rr_reins_outstd_cla`, `rr_reins_lins_liab`, `rr_reins_lthins_liab`, `refund_depos`, `ph_pledge_loans`, `refund_cap_depos`, `indep_acct_assets`, `client_depos`, `client_prov`, `transac_seat_fee`, `invest_as_receiv`, `total_assets`, `lt_borr`, `st_borr`, `cb_borr`, `depos_ib_deposits`, `loan_oth_bank`, `trading_fl`, `notes_payable`, `acct_payable`, `adv_receipts`, `sold_for_repur_fa`, `comm_payable`, `payroll_payable`, `taxes_payable`, `int_payable`, `div_payable`, `oth_payable`, `acc_exp`, `deferred_inc`, `st_bonds_payable`, `payable_to_reinsurer`, `rsrv_insur_cont`, `acting_trading_sec`, `acting_uw_sec`, `non_cur_liab_due_1y`, `oth_cur_liab`, `total_cur_liab`, `bond_payable`, `lt_payable`, `specific_payables`, `estimated_liab`, `defer_tax_liab`, `defer_inc_non_cur_liab`, `oth_ncl`, `total_ncl`, `depos_oth_bfi`, `deriv_liab`, `depos`, `agency_bus_liab`, `oth_liab`, `prem_receiv_adva`, `depos_received`, `ph_invest`, `reser_une_prem`, `reser_outstd_claims`, `reser_lins_liab`, `reser_lthins_liab`, `indept_acc_liab`, `pledge_borr`, `indem_payable`, `policy_div_payable`, `total_liab`, `treasury_share`, `ordin_risk_reser`, `forex_differ`, `invest_loss_unconf`, `minority_int`, `total_hldr_eqy_exc_min_int`, `total_hldr_eqy_inc_min_int`, `total_liab_hldr_eqy`, `lt_payroll_payable`, `oth_comp_income`, `oth_eqt_tools`, `oth_eqt_tools_p_shr`, `lending_funds`, `acc_receivable`, `st_fin_payable`, `payables`, `hfs_assets`, `hfs_sales`, `cost_fin_assets`, `fair_value_fin_assets`, `cip_total`, `oth_pay_total`, `long_pay_total`, `debt_invest`, `oth_debt_invest`, `contract_assets`, `contract_liab`, `accounts_receiv_bill`, `accounts_pay`, `oth_rcv_total`, `fix_assets_total`, `update_flag`。

```python
panels = data.get_panel(
    'balancesheet_vip_pit',
    fields=['total_assets', 'total_liab'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=None,
)
first_panel = panels['total_assets']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'balancesheet_vip_pit',
    fields=['total_assets', 'total_liab'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `report_type` | `string` | 可请求字段 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `total_share` | `double` | 可请求字段 |  |
| `cap_rese` | `double` | 可请求字段 |  |
| `undistr_porfit` | `double` | 可请求字段 |  |
| `surplus_rese` | `double` | 可请求字段 |  |
| `special_rese` | `double` | 可请求字段 |  |
| `money_cap` | `double` | 可请求字段 |  |
| `trad_asset` | `double` | 可请求字段 |  |
| `notes_receiv` | `double` | 可请求字段 |  |
| `accounts_receiv` | `double` | 可请求字段 |  |
| `oth_receiv` | `double` | 可请求字段 |  |
| `prepayment` | `double` | 可请求字段 |  |
| `div_receiv` | `double` | 可请求字段 |  |
| `int_receiv` | `double` | 可请求字段 |  |
| `inventories` | `double` | 可请求字段 |  |
| `amor_exp` | `double` | 可请求字段 |  |
| `nca_within_1y` | `double` | 可请求字段 |  |
| `sett_rsrv` | `double` | 可请求字段 |  |
| `loanto_oth_bank_fi` | `double` | 可请求字段 |  |
| `premium_receiv` | `double` | 可请求字段 |  |
| `reinsur_receiv` | `double` | 可请求字段 |  |
| `reinsur_res_receiv` | `double` | 可请求字段 |  |
| `pur_resale_fa` | `double` | 可请求字段 |  |
| `oth_cur_assets` | `double` | 可请求字段 |  |
| `total_cur_assets` | `double` | 可请求字段 |  |
| `fa_avail_for_sale` | `double` | 可请求字段 |  |
| `htm_invest` | `double` | 可请求字段 |  |
| `lt_eqt_invest` | `double` | 可请求字段 |  |
| `invest_real_estate` | `double` | 可请求字段 |  |
| `time_deposits` | `double` | 可请求字段 |  |
| `oth_assets` | `double` | 可请求字段 |  |
| `lt_rec` | `double` | 可请求字段 |  |
| `fix_assets` | `double` | 可请求字段 |  |
| `cip` | `double` | 可请求字段 |  |
| `const_materials` | `double` | 可请求字段 |  |
| `fixed_assets_disp` | `double` | 可请求字段 |  |
| `produc_bio_assets` | `double` | 可请求字段 |  |
| `oil_and_gas_assets` | `double` | 可请求字段 |  |
| `intan_assets` | `double` | 可请求字段 |  |
| `r_and_d` | `double` | 可请求字段 |  |
| `goodwill` | `double` | 可请求字段 |  |
| `lt_amor_exp` | `double` | 可请求字段 |  |
| `defer_tax_assets` | `double` | 可请求字段 |  |
| `decr_in_disbur` | `double` | 可请求字段 |  |
| `oth_nca` | `double` | 可请求字段 |  |
| `total_nca` | `double` | 可请求字段 |  |
| `cash_reser_cb` | `double` | 可请求字段 |  |
| `depos_in_oth_bfi` | `double` | 可请求字段 |  |
| `prec_metals` | `double` | 可请求字段 |  |
| `deriv_assets` | `double` | 可请求字段 |  |
| `rr_reins_une_prem` | `double` | 可请求字段 |  |
| `rr_reins_outstd_cla` | `double` | 可请求字段 |  |
| `rr_reins_lins_liab` | `double` | 可请求字段 |  |
| `rr_reins_lthins_liab` | `double` | 可请求字段 |  |
| `refund_depos` | `double` | 可请求字段 |  |
| `ph_pledge_loans` | `double` | 可请求字段 |  |
| `refund_cap_depos` | `double` | 可请求字段 |  |
| `indep_acct_assets` | `double` | 可请求字段 |  |
| `client_depos` | `double` | 可请求字段 |  |
| `client_prov` | `double` | 可请求字段 |  |
| `transac_seat_fee` | `double` | 可请求字段 |  |
| `invest_as_receiv` | `double` | 可请求字段 |  |
| `total_assets` | `double` | 可请求字段 |  |
| `lt_borr` | `double` | 可请求字段 |  |
| `st_borr` | `double` | 可请求字段 |  |
| `cb_borr` | `double` | 可请求字段 |  |
| `depos_ib_deposits` | `double` | 可请求字段 |  |
| `loan_oth_bank` | `double` | 可请求字段 |  |
| `trading_fl` | `double` | 可请求字段 |  |
| `notes_payable` | `double` | 可请求字段 |  |
| `acct_payable` | `double` | 可请求字段 |  |
| `adv_receipts` | `double` | 可请求字段 |  |
| `sold_for_repur_fa` | `double` | 可请求字段 |  |
| `comm_payable` | `double` | 可请求字段 |  |
| `payroll_payable` | `double` | 可请求字段 |  |
| `taxes_payable` | `double` | 可请求字段 |  |
| `int_payable` | `double` | 可请求字段 |  |
| `div_payable` | `double` | 可请求字段 |  |
| `oth_payable` | `double` | 可请求字段 |  |
| `acc_exp` | `double` | 可请求字段 |  |
| `deferred_inc` | `double` | 可请求字段 |  |
| `st_bonds_payable` | `double` | 可请求字段 |  |
| `payable_to_reinsurer` | `double` | 可请求字段 |  |
| `rsrv_insur_cont` | `double` | 可请求字段 |  |
| `acting_trading_sec` | `double` | 可请求字段 |  |
| `acting_uw_sec` | `double` | 可请求字段 |  |
| `non_cur_liab_due_1y` | `double` | 可请求字段 |  |
| `oth_cur_liab` | `double` | 可请求字段 |  |
| `total_cur_liab` | `double` | 可请求字段 |  |
| `bond_payable` | `double` | 可请求字段 |  |
| `lt_payable` | `double` | 可请求字段 |  |
| `specific_payables` | `double` | 可请求字段 |  |
| `estimated_liab` | `double` | 可请求字段 |  |
| `defer_tax_liab` | `double` | 可请求字段 |  |
| `defer_inc_non_cur_liab` | `double` | 可请求字段 |  |
| `oth_ncl` | `double` | 可请求字段 |  |
| `total_ncl` | `double` | 可请求字段 |  |
| `depos_oth_bfi` | `double` | 可请求字段 |  |
| `deriv_liab` | `double` | 可请求字段 |  |
| `depos` | `double` | 可请求字段 |  |
| `agency_bus_liab` | `double` | 可请求字段 |  |
| `oth_liab` | `double` | 可请求字段 |  |
| `prem_receiv_adva` | `double` | 可请求字段 |  |
| `depos_received` | `double` | 可请求字段 |  |
| `ph_invest` | `double` | 可请求字段 |  |
| `reser_une_prem` | `double` | 可请求字段 |  |
| `reser_outstd_claims` | `double` | 可请求字段 |  |
| `reser_lins_liab` | `double` | 可请求字段 |  |
| `reser_lthins_liab` | `double` | 可请求字段 |  |
| `indept_acc_liab` | `double` | 可请求字段 |  |
| `pledge_borr` | `double` | 可请求字段 |  |
| `indem_payable` | `double` | 可请求字段 |  |
| `policy_div_payable` | `double` | 可请求字段 |  |
| `total_liab` | `double` | 可请求字段 |  |
| `treasury_share` | `double` | 可请求字段 |  |
| `ordin_risk_reser` | `double` | 可请求字段 |  |
| `forex_differ` | `double` | 可请求字段 |  |
| `invest_loss_unconf` | `double` | 可请求字段 |  |
| `minority_int` | `double` | 可请求字段 |  |
| `total_hldr_eqy_exc_min_int` | `double` | 可请求字段 |  |
| `total_hldr_eqy_inc_min_int` | `double` | 可请求字段 |  |
| `total_liab_hldr_eqy` | `double` | 可请求字段 |  |
| `lt_payroll_payable` | `double` | 可请求字段 |  |
| `oth_comp_income` | `double` | 可请求字段 |  |
| `oth_eqt_tools` | `double` | 可请求字段 |  |
| `oth_eqt_tools_p_shr` | `double` | 可请求字段 |  |
| `lending_funds` | `double` | 可请求字段 |  |
| `acc_receivable` | `double` | 可请求字段 |  |
| `st_fin_payable` | `double` | 可请求字段 |  |
| `payables` | `double` | 可请求字段 |  |
| `hfs_assets` | `double` | 可请求字段 |  |
| `hfs_sales` | `double` | 可请求字段 |  |
| `cost_fin_assets` | `double` | 可请求字段 |  |
| `fair_value_fin_assets` | `double` | 可请求字段 |  |
| `cip_total` | `double` | 可请求字段 |  |
| `oth_pay_total` | `double` | 可请求字段 |  |
| `long_pay_total` | `double` | 可请求字段 |  |
| `debt_invest` | `double` | 可请求字段 |  |
| `oth_debt_invest` | `double` | 可请求字段 |  |
| `contract_assets` | `double` | 可请求字段 |  |
| `contract_liab` | `double` | 可请求字段 |  |
| `accounts_receiv_bill` | `double` | 可请求字段 |  |
| `accounts_pay` | `double` | 可请求字段 |  |
| `oth_rcv_total` | `double` | 可请求字段 |  |
| `fix_assets_total` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `cashflow_pit`

- 来源：Tushare `cashflow`（现金流量表 PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`f_ann_date`；默认 `disclosure_lag=1`。
- 说明：普通 PIT 数据集需要传入 `instruments`；对应 `_vip_pit` 数据集支持 `instruments=None`。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `comp_type`, `report_type`, `end_type`, `net_profit`, `finan_exp`, `c_fr_sale_sg`, `recp_tax_rends`, `n_depos_incr_fi`, `n_incr_loans_cb`, `n_inc_borr_oth_fi`, `prem_fr_orig_contr`, `n_incr_insured_dep`, `n_reinsur_prem`, `n_incr_disp_tfa`, `ifc_cash_incr`, `n_incr_disp_faas`, `n_incr_loans_oth_bank`, `n_cap_incr_repur`, `c_fr_oth_operate_a`, `c_inf_fr_operate_a`, `c_paid_goods_s`, `c_paid_to_for_empl`, `c_paid_for_taxes`, `n_incr_clt_loan_adv`, `n_incr_dep_cbob`, `c_pay_claims_orig_inco`, `pay_handling_chrg`, `pay_comm_insur_plcy`, `oth_cash_pay_oper_act`, `st_cash_out_act`, `n_cashflow_act`, `oth_recp_ral_inv_act`, `c_disp_withdrwl_invest`, `c_recp_return_invest`, `n_recp_disp_fiolta`, `n_recp_disp_sobu`, `stot_inflows_inv_act`, `c_pay_acq_const_fiolta`, `c_paid_invest`, `n_disp_subs_oth_biz`, `oth_pay_ral_inv_act`, `n_incr_pledge_loan`, `stot_out_inv_act`, `n_cashflow_inv_act`, `c_recp_borrow`, `proc_issue_bonds`, `oth_cash_recp_ral_fnc_act`, `stot_cash_in_fnc_act`, `free_cashflow`, `c_prepay_amt_borr`, `c_pay_dist_dpcp_int_exp`, `incl_dvd_profit_paid_sc_ms`, `oth_cashpay_ral_fnc_act`, `stot_cashout_fnc_act`, `n_cash_flows_fnc_act`, `eff_fx_flu_cash`, `n_incr_cash_cash_equ`, `c_cash_equ_beg_period`, `c_cash_equ_end_period`, `c_recp_cap_contrib`, `incl_cash_rec_saims`, `uncon_invest_loss`, `prov_depr_assets`, `depr_fa_coga_dpba`, `amort_intang_assets`, `lt_amort_deferred_exp`, `decr_deferred_exp`, `incr_acc_exp`, `loss_disp_fiolta`, `loss_scr_fa`, `loss_fv_chg`, `invest_loss`, `decr_def_inc_tax_assets`, `incr_def_inc_tax_liab`, `decr_inventories`, `decr_oper_payable`, `incr_oper_payable`, `others`, `im_net_cashflow_oper_act`, `conv_debt_into_cap`, `conv_copbonds_due_within_1y`, `fa_fnc_leases`, `im_n_incr_cash_equ`, `net_dism_capital_add`, `net_cash_rece_sec`, `credit_impa_loss`, `use_right_asset_dep`, `oth_loss_asset`, `end_bal_cash`, `beg_bal_cash`, `end_bal_cash_equ`, `beg_bal_cash_equ`, `update_flag`。

```python
panels = data.get_panel(
    'cashflow_pit',
    fields=['n_cashflow_act', 'free_cashflow'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['n_cashflow_act']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'cashflow_pit',
    fields=['n_cashflow_act', 'free_cashflow'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `report_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `net_profit` | `double` | 可请求字段 |  |
| `finan_exp` | `double` | 可请求字段 |  |
| `c_fr_sale_sg` | `double` | 可请求字段 |  |
| `recp_tax_rends` | `double` | 可请求字段 |  |
| `n_depos_incr_fi` | `double` | 可请求字段 |  |
| `n_incr_loans_cb` | `double` | 可请求字段 |  |
| `n_inc_borr_oth_fi` | `double` | 可请求字段 |  |
| `prem_fr_orig_contr` | `double` | 可请求字段 |  |
| `n_incr_insured_dep` | `double` | 可请求字段 |  |
| `n_reinsur_prem` | `double` | 可请求字段 |  |
| `n_incr_disp_tfa` | `double` | 可请求字段 |  |
| `ifc_cash_incr` | `double` | 可请求字段 |  |
| `n_incr_disp_faas` | `double` | 可请求字段 |  |
| `n_incr_loans_oth_bank` | `double` | 可请求字段 |  |
| `n_cap_incr_repur` | `double` | 可请求字段 |  |
| `c_fr_oth_operate_a` | `double` | 可请求字段 |  |
| `c_inf_fr_operate_a` | `double` | 可请求字段 |  |
| `c_paid_goods_s` | `double` | 可请求字段 |  |
| `c_paid_to_for_empl` | `double` | 可请求字段 |  |
| `c_paid_for_taxes` | `double` | 可请求字段 |  |
| `n_incr_clt_loan_adv` | `double` | 可请求字段 |  |
| `n_incr_dep_cbob` | `double` | 可请求字段 |  |
| `c_pay_claims_orig_inco` | `double` | 可请求字段 |  |
| `pay_handling_chrg` | `double` | 可请求字段 |  |
| `pay_comm_insur_plcy` | `double` | 可请求字段 |  |
| `oth_cash_pay_oper_act` | `double` | 可请求字段 |  |
| `st_cash_out_act` | `double` | 可请求字段 |  |
| `n_cashflow_act` | `double` | 可请求字段 |  |
| `oth_recp_ral_inv_act` | `double` | 可请求字段 |  |
| `c_disp_withdrwl_invest` | `double` | 可请求字段 |  |
| `c_recp_return_invest` | `double` | 可请求字段 |  |
| `n_recp_disp_fiolta` | `double` | 可请求字段 |  |
| `n_recp_disp_sobu` | `double` | 可请求字段 |  |
| `stot_inflows_inv_act` | `double` | 可请求字段 |  |
| `c_pay_acq_const_fiolta` | `double` | 可请求字段 |  |
| `c_paid_invest` | `double` | 可请求字段 |  |
| `n_disp_subs_oth_biz` | `double` | 可请求字段 |  |
| `oth_pay_ral_inv_act` | `double` | 可请求字段 |  |
| `n_incr_pledge_loan` | `double` | 可请求字段 |  |
| `stot_out_inv_act` | `double` | 可请求字段 |  |
| `n_cashflow_inv_act` | `double` | 可请求字段 |  |
| `c_recp_borrow` | `double` | 可请求字段 |  |
| `proc_issue_bonds` | `double` | 可请求字段 |  |
| `oth_cash_recp_ral_fnc_act` | `double` | 可请求字段 |  |
| `stot_cash_in_fnc_act` | `double` | 可请求字段 |  |
| `free_cashflow` | `double` | 可请求字段 |  |
| `c_prepay_amt_borr` | `double` | 可请求字段 |  |
| `c_pay_dist_dpcp_int_exp` | `double` | 可请求字段 |  |
| `incl_dvd_profit_paid_sc_ms` | `double` | 可请求字段 |  |
| `oth_cashpay_ral_fnc_act` | `double` | 可请求字段 |  |
| `stot_cashout_fnc_act` | `double` | 可请求字段 |  |
| `n_cash_flows_fnc_act` | `double` | 可请求字段 |  |
| `eff_fx_flu_cash` | `double` | 可请求字段 |  |
| `n_incr_cash_cash_equ` | `double` | 可请求字段 |  |
| `c_cash_equ_beg_period` | `double` | 可请求字段 |  |
| `c_cash_equ_end_period` | `double` | 可请求字段 |  |
| `c_recp_cap_contrib` | `double` | 可请求字段 |  |
| `incl_cash_rec_saims` | `double` | 可请求字段 |  |
| `uncon_invest_loss` | `double` | 可请求字段 |  |
| `prov_depr_assets` | `double` | 可请求字段 |  |
| `depr_fa_coga_dpba` | `double` | 可请求字段 |  |
| `amort_intang_assets` | `double` | 可请求字段 |  |
| `lt_amort_deferred_exp` | `double` | 可请求字段 |  |
| `decr_deferred_exp` | `double` | 可请求字段 |  |
| `incr_acc_exp` | `double` | 可请求字段 |  |
| `loss_disp_fiolta` | `double` | 可请求字段 |  |
| `loss_scr_fa` | `double` | 可请求字段 |  |
| `loss_fv_chg` | `double` | 可请求字段 |  |
| `invest_loss` | `double` | 可请求字段 |  |
| `decr_def_inc_tax_assets` | `double` | 可请求字段 |  |
| `incr_def_inc_tax_liab` | `double` | 可请求字段 |  |
| `decr_inventories` | `double` | 可请求字段 |  |
| `decr_oper_payable` | `double` | 可请求字段 |  |
| `incr_oper_payable` | `double` | 可请求字段 |  |
| `others` | `double` | 可请求字段 |  |
| `im_net_cashflow_oper_act` | `double` | 可请求字段 |  |
| `conv_debt_into_cap` | `double` | 可请求字段 |  |
| `conv_copbonds_due_within_1y` | `double` | 可请求字段 |  |
| `fa_fnc_leases` | `double` | 可请求字段 |  |
| `im_n_incr_cash_equ` | `double` | 可请求字段 |  |
| `net_dism_capital_add` | `double` | 可请求字段 |  |
| `net_cash_rece_sec` | `double` | 可请求字段 |  |
| `credit_impa_loss` | `double` | 可请求字段 |  |
| `use_right_asset_dep` | `double` | 可请求字段 |  |
| `oth_loss_asset` | `double` | 可请求字段 |  |
| `end_bal_cash` | `double` | 可请求字段 |  |
| `beg_bal_cash` | `double` | 可请求字段 |  |
| `end_bal_cash_equ` | `double` | 可请求字段 |  |
| `beg_bal_cash_equ` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `cashflow_vip_pit`

- 来源：Tushare `cashflow_vip`（现金流量表 VIP PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`f_ann_date`；默认 `disclosure_lag=1`。
- 说明：支持 `instruments=None` 全市场 PIT 面板。

宽表 `fields` 可选字段：`ann_date`, `f_ann_date`, `comp_type`, `report_type`, `end_type`, `net_profit`, `finan_exp`, `c_fr_sale_sg`, `recp_tax_rends`, `n_depos_incr_fi`, `n_incr_loans_cb`, `n_inc_borr_oth_fi`, `prem_fr_orig_contr`, `n_incr_insured_dep`, `n_reinsur_prem`, `n_incr_disp_tfa`, `ifc_cash_incr`, `n_incr_disp_faas`, `n_incr_loans_oth_bank`, `n_cap_incr_repur`, `c_fr_oth_operate_a`, `c_inf_fr_operate_a`, `c_paid_goods_s`, `c_paid_to_for_empl`, `c_paid_for_taxes`, `n_incr_clt_loan_adv`, `n_incr_dep_cbob`, `c_pay_claims_orig_inco`, `pay_handling_chrg`, `pay_comm_insur_plcy`, `oth_cash_pay_oper_act`, `st_cash_out_act`, `n_cashflow_act`, `oth_recp_ral_inv_act`, `c_disp_withdrwl_invest`, `c_recp_return_invest`, `n_recp_disp_fiolta`, `n_recp_disp_sobu`, `stot_inflows_inv_act`, `c_pay_acq_const_fiolta`, `c_paid_invest`, `n_disp_subs_oth_biz`, `oth_pay_ral_inv_act`, `n_incr_pledge_loan`, `stot_out_inv_act`, `n_cashflow_inv_act`, `c_recp_borrow`, `proc_issue_bonds`, `oth_cash_recp_ral_fnc_act`, `stot_cash_in_fnc_act`, `free_cashflow`, `c_prepay_amt_borr`, `c_pay_dist_dpcp_int_exp`, `incl_dvd_profit_paid_sc_ms`, `oth_cashpay_ral_fnc_act`, `stot_cashout_fnc_act`, `n_cash_flows_fnc_act`, `eff_fx_flu_cash`, `n_incr_cash_cash_equ`, `c_cash_equ_beg_period`, `c_cash_equ_end_period`, `c_recp_cap_contrib`, `incl_cash_rec_saims`, `uncon_invest_loss`, `prov_depr_assets`, `depr_fa_coga_dpba`, `amort_intang_assets`, `lt_amort_deferred_exp`, `decr_deferred_exp`, `incr_acc_exp`, `loss_disp_fiolta`, `loss_scr_fa`, `loss_fv_chg`, `invest_loss`, `decr_def_inc_tax_assets`, `incr_def_inc_tax_liab`, `decr_inventories`, `decr_oper_payable`, `incr_oper_payable`, `others`, `im_net_cashflow_oper_act`, `conv_debt_into_cap`, `conv_copbonds_due_within_1y`, `fa_fnc_leases`, `im_n_incr_cash_equ`, `net_dism_capital_add`, `net_cash_rece_sec`, `credit_impa_loss`, `use_right_asset_dep`, `oth_loss_asset`, `end_bal_cash`, `beg_bal_cash`, `end_bal_cash_equ`, `beg_bal_cash_equ`, `update_flag`。

```python
panels = data.get_panel(
    'cashflow_vip_pit',
    fields=['n_cashflow_act', 'free_cashflow'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=None,
)
first_panel = panels['n_cashflow_act']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'cashflow_vip_pit',
    fields=['n_cashflow_act', 'free_cashflow'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `f_ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `comp_type` | `string` | 可请求字段 |  |
| `report_type` | `string` | 可请求字段 |  |
| `end_type` | `string` | 可请求字段 |  |
| `net_profit` | `double` | 可请求字段 |  |
| `finan_exp` | `double` | 可请求字段 |  |
| `c_fr_sale_sg` | `double` | 可请求字段 |  |
| `recp_tax_rends` | `double` | 可请求字段 |  |
| `n_depos_incr_fi` | `double` | 可请求字段 |  |
| `n_incr_loans_cb` | `double` | 可请求字段 |  |
| `n_inc_borr_oth_fi` | `double` | 可请求字段 |  |
| `prem_fr_orig_contr` | `double` | 可请求字段 |  |
| `n_incr_insured_dep` | `double` | 可请求字段 |  |
| `n_reinsur_prem` | `double` | 可请求字段 |  |
| `n_incr_disp_tfa` | `double` | 可请求字段 |  |
| `ifc_cash_incr` | `double` | 可请求字段 |  |
| `n_incr_disp_faas` | `double` | 可请求字段 |  |
| `n_incr_loans_oth_bank` | `double` | 可请求字段 |  |
| `n_cap_incr_repur` | `double` | 可请求字段 |  |
| `c_fr_oth_operate_a` | `double` | 可请求字段 |  |
| `c_inf_fr_operate_a` | `double` | 可请求字段 |  |
| `c_paid_goods_s` | `double` | 可请求字段 |  |
| `c_paid_to_for_empl` | `double` | 可请求字段 |  |
| `c_paid_for_taxes` | `double` | 可请求字段 |  |
| `n_incr_clt_loan_adv` | `double` | 可请求字段 |  |
| `n_incr_dep_cbob` | `double` | 可请求字段 |  |
| `c_pay_claims_orig_inco` | `double` | 可请求字段 |  |
| `pay_handling_chrg` | `double` | 可请求字段 |  |
| `pay_comm_insur_plcy` | `double` | 可请求字段 |  |
| `oth_cash_pay_oper_act` | `double` | 可请求字段 |  |
| `st_cash_out_act` | `double` | 可请求字段 |  |
| `n_cashflow_act` | `double` | 可请求字段 |  |
| `oth_recp_ral_inv_act` | `double` | 可请求字段 |  |
| `c_disp_withdrwl_invest` | `double` | 可请求字段 |  |
| `c_recp_return_invest` | `double` | 可请求字段 |  |
| `n_recp_disp_fiolta` | `double` | 可请求字段 |  |
| `n_recp_disp_sobu` | `double` | 可请求字段 |  |
| `stot_inflows_inv_act` | `double` | 可请求字段 |  |
| `c_pay_acq_const_fiolta` | `double` | 可请求字段 |  |
| `c_paid_invest` | `double` | 可请求字段 |  |
| `n_disp_subs_oth_biz` | `double` | 可请求字段 |  |
| `oth_pay_ral_inv_act` | `double` | 可请求字段 |  |
| `n_incr_pledge_loan` | `double` | 可请求字段 |  |
| `stot_out_inv_act` | `double` | 可请求字段 |  |
| `n_cashflow_inv_act` | `double` | 可请求字段 |  |
| `c_recp_borrow` | `double` | 可请求字段 |  |
| `proc_issue_bonds` | `double` | 可请求字段 |  |
| `oth_cash_recp_ral_fnc_act` | `double` | 可请求字段 |  |
| `stot_cash_in_fnc_act` | `double` | 可请求字段 |  |
| `free_cashflow` | `double` | 可请求字段 |  |
| `c_prepay_amt_borr` | `double` | 可请求字段 |  |
| `c_pay_dist_dpcp_int_exp` | `double` | 可请求字段 |  |
| `incl_dvd_profit_paid_sc_ms` | `double` | 可请求字段 |  |
| `oth_cashpay_ral_fnc_act` | `double` | 可请求字段 |  |
| `stot_cashout_fnc_act` | `double` | 可请求字段 |  |
| `n_cash_flows_fnc_act` | `double` | 可请求字段 |  |
| `eff_fx_flu_cash` | `double` | 可请求字段 |  |
| `n_incr_cash_cash_equ` | `double` | 可请求字段 |  |
| `c_cash_equ_beg_period` | `double` | 可请求字段 |  |
| `c_cash_equ_end_period` | `double` | 可请求字段 |  |
| `c_recp_cap_contrib` | `double` | 可请求字段 |  |
| `incl_cash_rec_saims` | `double` | 可请求字段 |  |
| `uncon_invest_loss` | `double` | 可请求字段 |  |
| `prov_depr_assets` | `double` | 可请求字段 |  |
| `depr_fa_coga_dpba` | `double` | 可请求字段 |  |
| `amort_intang_assets` | `double` | 可请求字段 |  |
| `lt_amort_deferred_exp` | `double` | 可请求字段 |  |
| `decr_deferred_exp` | `double` | 可请求字段 |  |
| `incr_acc_exp` | `double` | 可请求字段 |  |
| `loss_disp_fiolta` | `double` | 可请求字段 |  |
| `loss_scr_fa` | `double` | 可请求字段 |  |
| `loss_fv_chg` | `double` | 可请求字段 |  |
| `invest_loss` | `double` | 可请求字段 |  |
| `decr_def_inc_tax_assets` | `double` | 可请求字段 |  |
| `incr_def_inc_tax_liab` | `double` | 可请求字段 |  |
| `decr_inventories` | `double` | 可请求字段 |  |
| `decr_oper_payable` | `double` | 可请求字段 |  |
| `incr_oper_payable` | `double` | 可请求字段 |  |
| `others` | `double` | 可请求字段 |  |
| `im_net_cashflow_oper_act` | `double` | 可请求字段 |  |
| `conv_debt_into_cap` | `double` | 可请求字段 |  |
| `conv_copbonds_due_within_1y` | `double` | 可请求字段 |  |
| `fa_fnc_leases` | `double` | 可请求字段 |  |
| `im_n_incr_cash_equ` | `double` | 可请求字段 |  |
| `net_dism_capital_add` | `double` | 可请求字段 |  |
| `net_cash_rece_sec` | `double` | 可请求字段 |  |
| `credit_impa_loss` | `double` | 可请求字段 |  |
| `use_right_asset_dep` | `double` | 可请求字段 |  |
| `oth_loss_asset` | `double` | 可请求字段 |  |
| `end_bal_cash` | `double` | 可请求字段 |  |
| `beg_bal_cash` | `double` | 可请求字段 |  |
| `end_bal_cash_equ` | `double` | 可请求字段 |  |
| `beg_bal_cash_equ` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `fina_indicator_pit`

- 来源：Tushare `fina_indicator`（财务指标 PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`ann_date`；默认 `disclosure_lag=1`。
- 说明：普通 PIT 数据集需要传入 `instruments`；对应 `_vip_pit` 数据集支持 `instruments=None`。

宽表 `fields` 可选字段：`ann_date`, `eps`, `dt_eps`, `total_revenue_ps`, `revenue_ps`, `capital_rese_ps`, `surplus_rese_ps`, `undist_profit_ps`, `extra_item`, `profit_dedt`, `gross_margin`, `current_ratio`, `quick_ratio`, `cash_ratio`, `invturn_days`, `arturn_days`, `inv_turn`, `ar_turn`, `ca_turn`, `fa_turn`, `assets_turn`, `op_income`, `valuechange_income`, `interst_income`, `daa`, `ebit`, `ebitda`, `fcff`, `fcfe`, `current_exint`, `noncurrent_exint`, `interestdebt`, `netdebt`, `tangible_asset`, `working_capital`, `networking_capital`, `invest_capital`, `retained_earnings`, `diluted2_eps`, `bps`, `ocfps`, `retainedps`, `cfps`, `ebit_ps`, `fcff_ps`, `fcfe_ps`, `netprofit_margin`, `grossprofit_margin`, `cogs_of_sales`, `expense_of_sales`, `profit_to_gr`, `saleexp_to_gr`, `adminexp_of_gr`, `finaexp_of_gr`, `impai_ttm`, `gc_of_gr`, `op_of_gr`, `ebit_of_gr`, `roe`, `roe_waa`, `roe_dt`, `roa`, `npta`, `roic`, `roe_yearly`, `roa2_yearly`, `roe_avg`, `opincome_of_ebt`, `investincome_of_ebt`, `n_op_profit_of_ebt`, `tax_to_ebt`, `dtprofit_to_profit`, `salescash_to_or`, `ocf_to_or`, `ocf_to_opincome`, `capitalized_to_da`, `debt_to_assets`, `assets_to_eqt`, `dp_assets_to_eqt`, `ca_to_assets`, `nca_to_assets`, `tbassets_to_totalassets`, `int_to_talcap`, `eqt_to_talcapital`, `currentdebt_to_debt`, `longdeb_to_debt`, `ocf_to_shortdebt`, `debt_to_eqt`, `eqt_to_debt`, `eqt_to_interestdebt`, `tangibleasset_to_debt`, `tangasset_to_intdebt`, `tangibleasset_to_netdebt`, `ocf_to_debt`, `ocf_to_interestdebt`, `ocf_to_netdebt`, `ebit_to_interest`, `longdebt_to_workingcapital`, `ebitda_to_debt`, `turn_days`, `roa_yearly`, `roa_dp`, `fixed_assets`, `profit_prefin_exp`, `non_op_profit`, `op_to_ebt`, `nop_to_ebt`, `ocf_to_profit`, `cash_to_liqdebt`, `cash_to_liqdebt_withinterest`, `op_to_liqdebt`, `op_to_debt`, `roic_yearly`, `total_fa_trun`, `profit_to_op`, `q_opincome`, `q_investincome`, `q_dtprofit`, `q_eps`, `q_netprofit_margin`, `q_gsprofit_margin`, `q_exp_to_sales`, `q_profit_to_gr`, `q_saleexp_to_gr`, `q_adminexp_to_gr`, `q_finaexp_to_gr`, `q_impair_to_gr_ttm`, `q_gc_to_gr`, `q_op_to_gr`, `q_roe`, `q_dt_roe`, `q_npta`, `q_opincome_to_ebt`, `q_investincome_to_ebt`, `q_dtprofit_to_profit`, `q_salescash_to_or`, `q_ocf_to_sales`, `q_ocf_to_or`, `basic_eps_yoy`, `dt_eps_yoy`, `cfps_yoy`, `op_yoy`, `ebt_yoy`, `netprofit_yoy`, `dt_netprofit_yoy`, `ocf_yoy`, `roe_yoy`, `bps_yoy`, `assets_yoy`, `eqt_yoy`, `tr_yoy`, `or_yoy`, `q_gr_yoy`, `q_gr_qoq`, `q_sales_yoy`, `q_sales_qoq`, `q_op_yoy`, `q_op_qoq`, `q_profit_yoy`, `q_profit_qoq`, `q_netprofit_yoy`, `q_netprofit_qoq`, `equity_yoy`, `rd_exp`, `update_flag`。

```python
panels = data.get_panel(
    'fina_indicator_pit',
    fields=['eps', 'roe'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['eps']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'fina_indicator_pit',
    fields=['eps', 'roe'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `eps` | `double` | 可请求字段 |  |
| `dt_eps` | `double` | 可请求字段 |  |
| `total_revenue_ps` | `double` | 可请求字段 |  |
| `revenue_ps` | `double` | 可请求字段 |  |
| `capital_rese_ps` | `double` | 可请求字段 |  |
| `surplus_rese_ps` | `double` | 可请求字段 |  |
| `undist_profit_ps` | `double` | 可请求字段 |  |
| `extra_item` | `double` | 可请求字段 |  |
| `profit_dedt` | `double` | 可请求字段 |  |
| `gross_margin` | `double` | 可请求字段 |  |
| `current_ratio` | `double` | 可请求字段 |  |
| `quick_ratio` | `double` | 可请求字段 |  |
| `cash_ratio` | `double` | 可请求字段 |  |
| `invturn_days` | `double` | 可请求字段 |  |
| `arturn_days` | `double` | 可请求字段 |  |
| `inv_turn` | `double` | 可请求字段 |  |
| `ar_turn` | `double` | 可请求字段 |  |
| `ca_turn` | `double` | 可请求字段 |  |
| `fa_turn` | `double` | 可请求字段 |  |
| `assets_turn` | `double` | 可请求字段 |  |
| `op_income` | `double` | 可请求字段 |  |
| `valuechange_income` | `double` | 可请求字段 |  |
| `interst_income` | `double` | 可请求字段 |  |
| `daa` | `double` | 可请求字段 |  |
| `ebit` | `double` | 可请求字段 |  |
| `ebitda` | `double` | 可请求字段 |  |
| `fcff` | `double` | 可请求字段 |  |
| `fcfe` | `double` | 可请求字段 |  |
| `current_exint` | `double` | 可请求字段 |  |
| `noncurrent_exint` | `double` | 可请求字段 |  |
| `interestdebt` | `double` | 可请求字段 |  |
| `netdebt` | `double` | 可请求字段 |  |
| `tangible_asset` | `double` | 可请求字段 |  |
| `working_capital` | `double` | 可请求字段 |  |
| `networking_capital` | `double` | 可请求字段 |  |
| `invest_capital` | `double` | 可请求字段 |  |
| `retained_earnings` | `double` | 可请求字段 |  |
| `diluted2_eps` | `double` | 可请求字段 |  |
| `bps` | `double` | 可请求字段 |  |
| `ocfps` | `double` | 可请求字段 |  |
| `retainedps` | `double` | 可请求字段 |  |
| `cfps` | `double` | 可请求字段 |  |
| `ebit_ps` | `double` | 可请求字段 |  |
| `fcff_ps` | `double` | 可请求字段 |  |
| `fcfe_ps` | `double` | 可请求字段 |  |
| `netprofit_margin` | `double` | 可请求字段 |  |
| `grossprofit_margin` | `double` | 可请求字段 |  |
| `cogs_of_sales` | `double` | 可请求字段 |  |
| `expense_of_sales` | `double` | 可请求字段 |  |
| `profit_to_gr` | `double` | 可请求字段 |  |
| `saleexp_to_gr` | `double` | 可请求字段 |  |
| `adminexp_of_gr` | `double` | 可请求字段 |  |
| `finaexp_of_gr` | `double` | 可请求字段 |  |
| `impai_ttm` | `double` | 可请求字段 |  |
| `gc_of_gr` | `double` | 可请求字段 |  |
| `op_of_gr` | `double` | 可请求字段 |  |
| `ebit_of_gr` | `double` | 可请求字段 |  |
| `roe` | `double` | 可请求字段 |  |
| `roe_waa` | `double` | 可请求字段 |  |
| `roe_dt` | `double` | 可请求字段 |  |
| `roa` | `double` | 可请求字段 |  |
| `npta` | `double` | 可请求字段 |  |
| `roic` | `double` | 可请求字段 |  |
| `roe_yearly` | `double` | 可请求字段 |  |
| `roa2_yearly` | `double` | 可请求字段 |  |
| `roe_avg` | `double` | 可请求字段 |  |
| `opincome_of_ebt` | `double` | 可请求字段 |  |
| `investincome_of_ebt` | `double` | 可请求字段 |  |
| `n_op_profit_of_ebt` | `double` | 可请求字段 |  |
| `tax_to_ebt` | `double` | 可请求字段 |  |
| `dtprofit_to_profit` | `double` | 可请求字段 |  |
| `salescash_to_or` | `double` | 可请求字段 |  |
| `ocf_to_or` | `double` | 可请求字段 |  |
| `ocf_to_opincome` | `double` | 可请求字段 |  |
| `capitalized_to_da` | `double` | 可请求字段 |  |
| `debt_to_assets` | `double` | 可请求字段 |  |
| `assets_to_eqt` | `double` | 可请求字段 |  |
| `dp_assets_to_eqt` | `double` | 可请求字段 |  |
| `ca_to_assets` | `double` | 可请求字段 |  |
| `nca_to_assets` | `double` | 可请求字段 |  |
| `tbassets_to_totalassets` | `double` | 可请求字段 |  |
| `int_to_talcap` | `double` | 可请求字段 |  |
| `eqt_to_talcapital` | `double` | 可请求字段 |  |
| `currentdebt_to_debt` | `double` | 可请求字段 |  |
| `longdeb_to_debt` | `double` | 可请求字段 |  |
| `ocf_to_shortdebt` | `double` | 可请求字段 |  |
| `debt_to_eqt` | `double` | 可请求字段 |  |
| `eqt_to_debt` | `double` | 可请求字段 |  |
| `eqt_to_interestdebt` | `double` | 可请求字段 |  |
| `tangibleasset_to_debt` | `double` | 可请求字段 |  |
| `tangasset_to_intdebt` | `double` | 可请求字段 |  |
| `tangibleasset_to_netdebt` | `double` | 可请求字段 |  |
| `ocf_to_debt` | `double` | 可请求字段 |  |
| `ocf_to_interestdebt` | `double` | 可请求字段 |  |
| `ocf_to_netdebt` | `double` | 可请求字段 |  |
| `ebit_to_interest` | `double` | 可请求字段 |  |
| `longdebt_to_workingcapital` | `double` | 可请求字段 |  |
| `ebitda_to_debt` | `double` | 可请求字段 |  |
| `turn_days` | `double` | 可请求字段 |  |
| `roa_yearly` | `double` | 可请求字段 |  |
| `roa_dp` | `double` | 可请求字段 |  |
| `fixed_assets` | `double` | 可请求字段 |  |
| `profit_prefin_exp` | `double` | 可请求字段 |  |
| `non_op_profit` | `double` | 可请求字段 |  |
| `op_to_ebt` | `double` | 可请求字段 |  |
| `nop_to_ebt` | `double` | 可请求字段 |  |
| `ocf_to_profit` | `double` | 可请求字段 |  |
| `cash_to_liqdebt` | `double` | 可请求字段 |  |
| `cash_to_liqdebt_withinterest` | `double` | 可请求字段 |  |
| `op_to_liqdebt` | `double` | 可请求字段 |  |
| `op_to_debt` | `double` | 可请求字段 |  |
| `roic_yearly` | `double` | 可请求字段 |  |
| `total_fa_trun` | `double` | 可请求字段 |  |
| `profit_to_op` | `double` | 可请求字段 |  |
| `q_opincome` | `double` | 可请求字段 |  |
| `q_investincome` | `double` | 可请求字段 |  |
| `q_dtprofit` | `double` | 可请求字段 |  |
| `q_eps` | `double` | 可请求字段 |  |
| `q_netprofit_margin` | `double` | 可请求字段 |  |
| `q_gsprofit_margin` | `double` | 可请求字段 |  |
| `q_exp_to_sales` | `double` | 可请求字段 |  |
| `q_profit_to_gr` | `double` | 可请求字段 |  |
| `q_saleexp_to_gr` | `double` | 可请求字段 |  |
| `q_adminexp_to_gr` | `double` | 可请求字段 |  |
| `q_finaexp_to_gr` | `double` | 可请求字段 |  |
| `q_impair_to_gr_ttm` | `double` | 可请求字段 |  |
| `q_gc_to_gr` | `double` | 可请求字段 |  |
| `q_op_to_gr` | `double` | 可请求字段 |  |
| `q_roe` | `double` | 可请求字段 |  |
| `q_dt_roe` | `double` | 可请求字段 |  |
| `q_npta` | `double` | 可请求字段 |  |
| `q_opincome_to_ebt` | `double` | 可请求字段 |  |
| `q_investincome_to_ebt` | `double` | 可请求字段 |  |
| `q_dtprofit_to_profit` | `double` | 可请求字段 |  |
| `q_salescash_to_or` | `double` | 可请求字段 |  |
| `q_ocf_to_sales` | `double` | 可请求字段 |  |
| `q_ocf_to_or` | `double` | 可请求字段 |  |
| `basic_eps_yoy` | `double` | 可请求字段 |  |
| `dt_eps_yoy` | `double` | 可请求字段 |  |
| `cfps_yoy` | `double` | 可请求字段 |  |
| `op_yoy` | `double` | 可请求字段 |  |
| `ebt_yoy` | `double` | 可请求字段 |  |
| `netprofit_yoy` | `double` | 可请求字段 |  |
| `dt_netprofit_yoy` | `double` | 可请求字段 |  |
| `ocf_yoy` | `double` | 可请求字段 |  |
| `roe_yoy` | `double` | 可请求字段 |  |
| `bps_yoy` | `double` | 可请求字段 |  |
| `assets_yoy` | `double` | 可请求字段 |  |
| `eqt_yoy` | `double` | 可请求字段 |  |
| `tr_yoy` | `double` | 可请求字段 |  |
| `or_yoy` | `double` | 可请求字段 |  |
| `q_gr_yoy` | `double` | 可请求字段 |  |
| `q_gr_qoq` | `double` | 可请求字段 |  |
| `q_sales_yoy` | `double` | 可请求字段 |  |
| `q_sales_qoq` | `double` | 可请求字段 |  |
| `q_op_yoy` | `double` | 可请求字段 |  |
| `q_op_qoq` | `double` | 可请求字段 |  |
| `q_profit_yoy` | `double` | 可请求字段 |  |
| `q_profit_qoq` | `double` | 可请求字段 |  |
| `q_netprofit_yoy` | `double` | 可请求字段 |  |
| `q_netprofit_qoq` | `double` | 可请求字段 |  |
| `equity_yoy` | `double` | 可请求字段 |  |
| `rd_exp` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `fina_indicator_vip_pit`

- 来源：Tushare `fina_indicator_vip`（财务指标 VIP PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`ann_date`；默认 `disclosure_lag=1`。
- 说明：支持 `instruments=None` 全市场 PIT 面板。

宽表 `fields` 可选字段：`ann_date`, `eps`, `dt_eps`, `total_revenue_ps`, `revenue_ps`, `capital_rese_ps`, `surplus_rese_ps`, `undist_profit_ps`, `extra_item`, `profit_dedt`, `gross_margin`, `current_ratio`, `quick_ratio`, `cash_ratio`, `invturn_days`, `arturn_days`, `inv_turn`, `ar_turn`, `ca_turn`, `fa_turn`, `assets_turn`, `op_income`, `valuechange_income`, `interst_income`, `daa`, `ebit`, `ebitda`, `fcff`, `fcfe`, `current_exint`, `noncurrent_exint`, `interestdebt`, `netdebt`, `tangible_asset`, `working_capital`, `networking_capital`, `invest_capital`, `retained_earnings`, `diluted2_eps`, `bps`, `ocfps`, `retainedps`, `cfps`, `ebit_ps`, `fcff_ps`, `fcfe_ps`, `netprofit_margin`, `grossprofit_margin`, `cogs_of_sales`, `expense_of_sales`, `profit_to_gr`, `saleexp_to_gr`, `adminexp_of_gr`, `finaexp_of_gr`, `impai_ttm`, `gc_of_gr`, `op_of_gr`, `ebit_of_gr`, `roe`, `roe_waa`, `roe_dt`, `roa`, `npta`, `roic`, `roe_yearly`, `roa2_yearly`, `roe_avg`, `opincome_of_ebt`, `investincome_of_ebt`, `n_op_profit_of_ebt`, `tax_to_ebt`, `dtprofit_to_profit`, `salescash_to_or`, `ocf_to_or`, `ocf_to_opincome`, `capitalized_to_da`, `debt_to_assets`, `assets_to_eqt`, `dp_assets_to_eqt`, `ca_to_assets`, `nca_to_assets`, `tbassets_to_totalassets`, `int_to_talcap`, `eqt_to_talcapital`, `currentdebt_to_debt`, `longdeb_to_debt`, `ocf_to_shortdebt`, `debt_to_eqt`, `eqt_to_debt`, `eqt_to_interestdebt`, `tangibleasset_to_debt`, `tangasset_to_intdebt`, `tangibleasset_to_netdebt`, `ocf_to_debt`, `ocf_to_interestdebt`, `ocf_to_netdebt`, `ebit_to_interest`, `longdebt_to_workingcapital`, `ebitda_to_debt`, `turn_days`, `roa_yearly`, `roa_dp`, `fixed_assets`, `profit_prefin_exp`, `non_op_profit`, `op_to_ebt`, `nop_to_ebt`, `ocf_to_profit`, `cash_to_liqdebt`, `cash_to_liqdebt_withinterest`, `op_to_liqdebt`, `op_to_debt`, `roic_yearly`, `total_fa_trun`, `profit_to_op`, `q_opincome`, `q_investincome`, `q_dtprofit`, `q_eps`, `q_netprofit_margin`, `q_gsprofit_margin`, `q_exp_to_sales`, `q_profit_to_gr`, `q_saleexp_to_gr`, `q_adminexp_to_gr`, `q_finaexp_to_gr`, `q_impair_to_gr_ttm`, `q_gc_to_gr`, `q_op_to_gr`, `q_roe`, `q_dt_roe`, `q_npta`, `q_opincome_to_ebt`, `q_investincome_to_ebt`, `q_dtprofit_to_profit`, `q_salescash_to_or`, `q_ocf_to_sales`, `q_ocf_to_or`, `basic_eps_yoy`, `dt_eps_yoy`, `cfps_yoy`, `op_yoy`, `ebt_yoy`, `netprofit_yoy`, `dt_netprofit_yoy`, `ocf_yoy`, `roe_yoy`, `bps_yoy`, `assets_yoy`, `eqt_yoy`, `tr_yoy`, `or_yoy`, `q_gr_yoy`, `q_gr_qoq`, `q_sales_yoy`, `q_sales_qoq`, `q_op_yoy`, `q_op_qoq`, `q_profit_yoy`, `q_profit_qoq`, `q_netprofit_yoy`, `q_netprofit_qoq`, `equity_yoy`, `rd_exp`, `update_flag`。

```python
panels = data.get_panel(
    'fina_indicator_vip_pit',
    fields=['eps', 'roe'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=None,
)
first_panel = panels['eps']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'fina_indicator_vip_pit',
    fields=['eps', 'roe'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `eps` | `double` | 可请求字段 |  |
| `dt_eps` | `double` | 可请求字段 |  |
| `total_revenue_ps` | `double` | 可请求字段 |  |
| `revenue_ps` | `double` | 可请求字段 |  |
| `capital_rese_ps` | `double` | 可请求字段 |  |
| `surplus_rese_ps` | `double` | 可请求字段 |  |
| `undist_profit_ps` | `double` | 可请求字段 |  |
| `extra_item` | `double` | 可请求字段 |  |
| `profit_dedt` | `double` | 可请求字段 |  |
| `gross_margin` | `double` | 可请求字段 |  |
| `current_ratio` | `double` | 可请求字段 |  |
| `quick_ratio` | `double` | 可请求字段 |  |
| `cash_ratio` | `double` | 可请求字段 |  |
| `invturn_days` | `double` | 可请求字段 |  |
| `arturn_days` | `double` | 可请求字段 |  |
| `inv_turn` | `double` | 可请求字段 |  |
| `ar_turn` | `double` | 可请求字段 |  |
| `ca_turn` | `double` | 可请求字段 |  |
| `fa_turn` | `double` | 可请求字段 |  |
| `assets_turn` | `double` | 可请求字段 |  |
| `op_income` | `double` | 可请求字段 |  |
| `valuechange_income` | `double` | 可请求字段 |  |
| `interst_income` | `double` | 可请求字段 |  |
| `daa` | `double` | 可请求字段 |  |
| `ebit` | `double` | 可请求字段 |  |
| `ebitda` | `double` | 可请求字段 |  |
| `fcff` | `double` | 可请求字段 |  |
| `fcfe` | `double` | 可请求字段 |  |
| `current_exint` | `double` | 可请求字段 |  |
| `noncurrent_exint` | `double` | 可请求字段 |  |
| `interestdebt` | `double` | 可请求字段 |  |
| `netdebt` | `double` | 可请求字段 |  |
| `tangible_asset` | `double` | 可请求字段 |  |
| `working_capital` | `double` | 可请求字段 |  |
| `networking_capital` | `double` | 可请求字段 |  |
| `invest_capital` | `double` | 可请求字段 |  |
| `retained_earnings` | `double` | 可请求字段 |  |
| `diluted2_eps` | `double` | 可请求字段 |  |
| `bps` | `double` | 可请求字段 |  |
| `ocfps` | `double` | 可请求字段 |  |
| `retainedps` | `double` | 可请求字段 |  |
| `cfps` | `double` | 可请求字段 |  |
| `ebit_ps` | `double` | 可请求字段 |  |
| `fcff_ps` | `double` | 可请求字段 |  |
| `fcfe_ps` | `double` | 可请求字段 |  |
| `netprofit_margin` | `double` | 可请求字段 |  |
| `grossprofit_margin` | `double` | 可请求字段 |  |
| `cogs_of_sales` | `double` | 可请求字段 |  |
| `expense_of_sales` | `double` | 可请求字段 |  |
| `profit_to_gr` | `double` | 可请求字段 |  |
| `saleexp_to_gr` | `double` | 可请求字段 |  |
| `adminexp_of_gr` | `double` | 可请求字段 |  |
| `finaexp_of_gr` | `double` | 可请求字段 |  |
| `impai_ttm` | `double` | 可请求字段 |  |
| `gc_of_gr` | `double` | 可请求字段 |  |
| `op_of_gr` | `double` | 可请求字段 |  |
| `ebit_of_gr` | `double` | 可请求字段 |  |
| `roe` | `double` | 可请求字段 |  |
| `roe_waa` | `double` | 可请求字段 |  |
| `roe_dt` | `double` | 可请求字段 |  |
| `roa` | `double` | 可请求字段 |  |
| `npta` | `double` | 可请求字段 |  |
| `roic` | `double` | 可请求字段 |  |
| `roe_yearly` | `double` | 可请求字段 |  |
| `roa2_yearly` | `double` | 可请求字段 |  |
| `roe_avg` | `double` | 可请求字段 |  |
| `opincome_of_ebt` | `double` | 可请求字段 |  |
| `investincome_of_ebt` | `double` | 可请求字段 |  |
| `n_op_profit_of_ebt` | `double` | 可请求字段 |  |
| `tax_to_ebt` | `double` | 可请求字段 |  |
| `dtprofit_to_profit` | `double` | 可请求字段 |  |
| `salescash_to_or` | `double` | 可请求字段 |  |
| `ocf_to_or` | `double` | 可请求字段 |  |
| `ocf_to_opincome` | `double` | 可请求字段 |  |
| `capitalized_to_da` | `double` | 可请求字段 |  |
| `debt_to_assets` | `double` | 可请求字段 |  |
| `assets_to_eqt` | `double` | 可请求字段 |  |
| `dp_assets_to_eqt` | `double` | 可请求字段 |  |
| `ca_to_assets` | `double` | 可请求字段 |  |
| `nca_to_assets` | `double` | 可请求字段 |  |
| `tbassets_to_totalassets` | `double` | 可请求字段 |  |
| `int_to_talcap` | `double` | 可请求字段 |  |
| `eqt_to_talcapital` | `double` | 可请求字段 |  |
| `currentdebt_to_debt` | `double` | 可请求字段 |  |
| `longdeb_to_debt` | `double` | 可请求字段 |  |
| `ocf_to_shortdebt` | `double` | 可请求字段 |  |
| `debt_to_eqt` | `double` | 可请求字段 |  |
| `eqt_to_debt` | `double` | 可请求字段 |  |
| `eqt_to_interestdebt` | `double` | 可请求字段 |  |
| `tangibleasset_to_debt` | `double` | 可请求字段 |  |
| `tangasset_to_intdebt` | `double` | 可请求字段 |  |
| `tangibleasset_to_netdebt` | `double` | 可请求字段 |  |
| `ocf_to_debt` | `double` | 可请求字段 |  |
| `ocf_to_interestdebt` | `double` | 可请求字段 |  |
| `ocf_to_netdebt` | `double` | 可请求字段 |  |
| `ebit_to_interest` | `double` | 可请求字段 |  |
| `longdebt_to_workingcapital` | `double` | 可请求字段 |  |
| `ebitda_to_debt` | `double` | 可请求字段 |  |
| `turn_days` | `double` | 可请求字段 |  |
| `roa_yearly` | `double` | 可请求字段 |  |
| `roa_dp` | `double` | 可请求字段 |  |
| `fixed_assets` | `double` | 可请求字段 |  |
| `profit_prefin_exp` | `double` | 可请求字段 |  |
| `non_op_profit` | `double` | 可请求字段 |  |
| `op_to_ebt` | `double` | 可请求字段 |  |
| `nop_to_ebt` | `double` | 可请求字段 |  |
| `ocf_to_profit` | `double` | 可请求字段 |  |
| `cash_to_liqdebt` | `double` | 可请求字段 |  |
| `cash_to_liqdebt_withinterest` | `double` | 可请求字段 |  |
| `op_to_liqdebt` | `double` | 可请求字段 |  |
| `op_to_debt` | `double` | 可请求字段 |  |
| `roic_yearly` | `double` | 可请求字段 |  |
| `total_fa_trun` | `double` | 可请求字段 |  |
| `profit_to_op` | `double` | 可请求字段 |  |
| `q_opincome` | `double` | 可请求字段 |  |
| `q_investincome` | `double` | 可请求字段 |  |
| `q_dtprofit` | `double` | 可请求字段 |  |
| `q_eps` | `double` | 可请求字段 |  |
| `q_netprofit_margin` | `double` | 可请求字段 |  |
| `q_gsprofit_margin` | `double` | 可请求字段 |  |
| `q_exp_to_sales` | `double` | 可请求字段 |  |
| `q_profit_to_gr` | `double` | 可请求字段 |  |
| `q_saleexp_to_gr` | `double` | 可请求字段 |  |
| `q_adminexp_to_gr` | `double` | 可请求字段 |  |
| `q_finaexp_to_gr` | `double` | 可请求字段 |  |
| `q_impair_to_gr_ttm` | `double` | 可请求字段 |  |
| `q_gc_to_gr` | `double` | 可请求字段 |  |
| `q_op_to_gr` | `double` | 可请求字段 |  |
| `q_roe` | `double` | 可请求字段 |  |
| `q_dt_roe` | `double` | 可请求字段 |  |
| `q_npta` | `double` | 可请求字段 |  |
| `q_opincome_to_ebt` | `double` | 可请求字段 |  |
| `q_investincome_to_ebt` | `double` | 可请求字段 |  |
| `q_dtprofit_to_profit` | `double` | 可请求字段 |  |
| `q_salescash_to_or` | `double` | 可请求字段 |  |
| `q_ocf_to_sales` | `double` | 可请求字段 |  |
| `q_ocf_to_or` | `double` | 可请求字段 |  |
| `basic_eps_yoy` | `double` | 可请求字段 |  |
| `dt_eps_yoy` | `double` | 可请求字段 |  |
| `cfps_yoy` | `double` | 可请求字段 |  |
| `op_yoy` | `double` | 可请求字段 |  |
| `ebt_yoy` | `double` | 可请求字段 |  |
| `netprofit_yoy` | `double` | 可请求字段 |  |
| `dt_netprofit_yoy` | `double` | 可请求字段 |  |
| `ocf_yoy` | `double` | 可请求字段 |  |
| `roe_yoy` | `double` | 可请求字段 |  |
| `bps_yoy` | `double` | 可请求字段 |  |
| `assets_yoy` | `double` | 可请求字段 |  |
| `eqt_yoy` | `double` | 可请求字段 |  |
| `tr_yoy` | `double` | 可请求字段 |  |
| `or_yoy` | `double` | 可请求字段 |  |
| `q_gr_yoy` | `double` | 可请求字段 |  |
| `q_gr_qoq` | `double` | 可请求字段 |  |
| `q_sales_yoy` | `double` | 可请求字段 |  |
| `q_sales_qoq` | `double` | 可请求字段 |  |
| `q_op_yoy` | `double` | 可请求字段 |  |
| `q_op_qoq` | `double` | 可请求字段 |  |
| `q_profit_yoy` | `double` | 可请求字段 |  |
| `q_profit_qoq` | `double` | 可请求字段 |  |
| `q_netprofit_yoy` | `double` | 可请求字段 |  |
| `q_netprofit_qoq` | `double` | 可请求字段 |  |
| `equity_yoy` | `double` | 可请求字段 |  |
| `rd_exp` | `double` | 可请求字段 |  |
| `update_flag` | `string` | 可请求字段 |  |

## `express_pit`

- 来源：Tushare `express`（业绩快报 PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`ann_date`；默认 `disclosure_lag=1`。
- 说明：普通 PIT 数据集需要传入 `instruments`；对应 `_vip_pit` 数据集支持 `instruments=None`。

宽表 `fields` 可选字段：`ann_date`, `revenue`, `operate_profit`, `total_profit`, `n_income`, `total_assets`, `total_hldr_eqy_exc_min_int`, `diluted_eps`, `diluted_roe`, `yoy_net_profit`, `bps`, `yoy_sales`, `yoy_op`, `yoy_tp`, `yoy_dedu_np`, `yoy_eps`, `yoy_roe`, `growth_assets`, `yoy_equity`, `growth_bps`, `or_last_year`, `op_last_year`, `tp_last_year`, `np_last_year`, `eps_last_year`, `open_net_assets`, `open_bps`, `perf_summary`, `is_audit`, `remark`。

```python
panels = data.get_panel(
    'express_pit',
    fields=['revenue', 'n_income'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['revenue']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'express_pit',
    fields=['revenue', 'n_income'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `revenue` | `double` | 可请求字段 |  |
| `operate_profit` | `double` | 可请求字段 |  |
| `total_profit` | `double` | 可请求字段 |  |
| `n_income` | `double` | 可请求字段 |  |
| `total_assets` | `double` | 可请求字段 |  |
| `total_hldr_eqy_exc_min_int` | `double` | 可请求字段 |  |
| `diluted_eps` | `double` | 可请求字段 |  |
| `diluted_roe` | `double` | 可请求字段 |  |
| `yoy_net_profit` | `double` | 可请求字段 |  |
| `bps` | `double` | 可请求字段 |  |
| `yoy_sales` | `double` | 可请求字段 |  |
| `yoy_op` | `double` | 可请求字段 |  |
| `yoy_tp` | `double` | 可请求字段 |  |
| `yoy_dedu_np` | `double` | 可请求字段 |  |
| `yoy_eps` | `double` | 可请求字段 |  |
| `yoy_roe` | `double` | 可请求字段 |  |
| `growth_assets` | `double` | 可请求字段 |  |
| `yoy_equity` | `double` | 可请求字段 |  |
| `growth_bps` | `double` | 可请求字段 |  |
| `or_last_year` | `double` | 可请求字段 |  |
| `op_last_year` | `double` | 可请求字段 |  |
| `tp_last_year` | `double` | 可请求字段 |  |
| `np_last_year` | `double` | 可请求字段 |  |
| `eps_last_year` | `double` | 可请求字段 |  |
| `open_net_assets` | `double` | 可请求字段 |  |
| `open_bps` | `double` | 可请求字段 |  |
| `perf_summary` | `string` | 可请求字段 |  |
| `is_audit` | `int64` | 可请求字段 |  |
| `remark` | `string` | 可请求字段 |  |

## `express_vip_pit`

- 来源：Tushare `express_vip`（业绩快报 VIP PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`ann_date`；默认 `disclosure_lag=1`。
- 说明：支持 `instruments=None` 全市场 PIT 面板。

宽表 `fields` 可选字段：`ann_date`, `revenue`, `operate_profit`, `total_profit`, `n_income`, `total_assets`, `total_hldr_eqy_exc_min_int`, `diluted_eps`, `diluted_roe`, `yoy_net_profit`, `bps`, `yoy_sales`, `yoy_op`, `yoy_tp`, `yoy_dedu_np`, `yoy_eps`, `yoy_roe`, `growth_assets`, `yoy_equity`, `growth_bps`, `or_last_year`, `op_last_year`, `tp_last_year`, `np_last_year`, `eps_last_year`, `open_net_assets`, `open_bps`, `perf_summary`, `is_audit`, `remark`。

```python
panels = data.get_panel(
    'express_vip_pit',
    fields=['revenue', 'n_income'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=None,
)
first_panel = panels['revenue']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'express_vip_pit',
    fields=['revenue', 'n_income'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `revenue` | `double` | 可请求字段 |  |
| `operate_profit` | `double` | 可请求字段 |  |
| `total_profit` | `double` | 可请求字段 |  |
| `n_income` | `double` | 可请求字段 |  |
| `total_assets` | `double` | 可请求字段 |  |
| `total_hldr_eqy_exc_min_int` | `double` | 可请求字段 |  |
| `diluted_eps` | `double` | 可请求字段 |  |
| `diluted_roe` | `double` | 可请求字段 |  |
| `yoy_net_profit` | `double` | 可请求字段 |  |
| `bps` | `double` | 可请求字段 |  |
| `yoy_sales` | `double` | 可请求字段 |  |
| `yoy_op` | `double` | 可请求字段 |  |
| `yoy_tp` | `double` | 可请求字段 |  |
| `yoy_dedu_np` | `double` | 可请求字段 |  |
| `yoy_eps` | `double` | 可请求字段 |  |
| `yoy_roe` | `double` | 可请求字段 |  |
| `growth_assets` | `double` | 可请求字段 |  |
| `yoy_equity` | `double` | 可请求字段 |  |
| `growth_bps` | `double` | 可请求字段 |  |
| `or_last_year` | `double` | 可请求字段 |  |
| `op_last_year` | `double` | 可请求字段 |  |
| `tp_last_year` | `double` | 可请求字段 |  |
| `np_last_year` | `double` | 可请求字段 |  |
| `eps_last_year` | `double` | 可请求字段 |  |
| `open_net_assets` | `double` | 可请求字段 |  |
| `open_bps` | `double` | 可请求字段 |  |
| `perf_summary` | `string` | 可请求字段 |  |
| `is_audit` | `int64` | 可请求字段 |  |
| `remark` | `string` | 可请求字段 |  |

## `forecast_pit`

- 来源：Tushare `forecast`（业绩预告 PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`ann_date`；默认 `disclosure_lag=1`。
- 说明：普通 PIT 数据集需要传入 `instruments`；对应 `_vip_pit` 数据集支持 `instruments=None`。

宽表 `fields` 可选字段：`ann_date`, `type`, `p_change_min`, `p_change_max`, `net_profit_min`, `net_profit_max`, `last_parent_net`, `first_ann_date`, `summary`, `change_reason`。

```python
panels = data.get_panel(
    'forecast_pit',
    fields=['type', 'p_change_min', 'p_change_max'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=['600000.SH', '000001.SZ'],
)
first_panel = panels['type']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'forecast_pit',
    fields=['type', 'p_change_min', 'p_change_max'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=['600000.SH'],
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `type` | `string` | 可请求字段 |  |
| `p_change_min` | `double` | 可请求字段 |  |
| `p_change_max` | `double` | 可请求字段 |  |
| `net_profit_min` | `double` | 可请求字段 |  |
| `net_profit_max` | `double` | 可请求字段 |  |
| `last_parent_net` | `double` | 可请求字段 |  |
| `first_ann_date` | `date32[day]` | 可请求字段 |  |
| `summary` | `string` | 可请求字段 |  |
| `change_reason` | `string` | 可请求字段 |  |

## `forecast_vip_pit`

- 来源：Tushare `forecast_vip`（业绩预告 VIP PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`ann_date`；默认 `disclosure_lag=1`。
- 说明：支持 `instruments=None` 全市场 PIT 面板。

宽表 `fields` 可选字段：`ann_date`, `type`, `p_change_min`, `p_change_max`, `net_profit_min`, `net_profit_max`, `last_parent_net`, `first_ann_date`, `summary`, `change_reason`。

```python
panels = data.get_panel(
    'forecast_vip_pit',
    fields=['type', 'p_change_min', 'p_change_max'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=None,
)
first_panel = panels['type']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'forecast_vip_pit',
    fields=['type', 'p_change_min', 'p_change_max'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `type` | `string` | 可请求字段 |  |
| `p_change_min` | `double` | 可请求字段 |  |
| `p_change_max` | `double` | 可请求字段 |  |
| `net_profit_min` | `double` | 可请求字段 |  |
| `net_profit_max` | `double` | 可请求字段 |  |
| `last_parent_net` | `double` | 可请求字段 |  |
| `first_ann_date` | `date32[day]` | 可请求字段 |  |
| `summary` | `string` | 可请求字段 |  |
| `change_reason` | `string` | 可请求字段 |  |

## `stk_holdernumber_pit`

- 来源：Tushare `stk_holdernumber`（股东人数 PIT 日频面板）
- 自动键列：宽表输出为 `trade_date × ts_code`；原始报告期列为 `end_date`。
- 可生成宽表：是，使用公告日和交易日历构造 PIT 日频可得数据。
- 可返回长表：是，但 `get_table()` 返回普通 Tushare 长表，不构造 PIT 日频面板。
- disclosure date：`ann_date`；默认 `disclosure_lag=1`。
- 说明：支持 `instruments=None` 全市场 PIT 面板。

宽表 `fields` 可选字段：`ann_date`, `holder_num`。

```python
panels = data.get_panel(
    'stk_holdernumber_pit',
    fields=['holder_num'],
    start='2024-04-01',
    end='2024-05-31',
    instruments=None,
)
first_panel = panels['holder_num']
```

长表自动返回键列，`fields` 可选字段同下表中的“可请求字段”。

```python
table = data.get_table(
    'stk_holdernumber_pit',
    fields=['holder_num'],
    start='2023-01-01',
    end='2023-12-31',
    instruments=None,
)
frame = table.to_pandas()
```

| 字段 | 类型 | 角色 | 说明 |
| --- | --- | --- | --- |
| `ts_code` | `string` | 自动键列 |  |
| `ann_date` | `date32[day]` | 可请求字段 |  |
| `end_date` | `date32[day]` | 自动键列 |  |
| `holder_num` | `int64` | 可请求字段 |  |
