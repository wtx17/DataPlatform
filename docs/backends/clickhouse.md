# ClickHouse

## 本地 catalog 与远程 schema

`MINGHU_TABLE_COLUMN_TYPES` 固化五张项目表的列名和 ClickHouse 类型：

- `stock_base.daily`；
- `index_base.daily`；
- `stock_base.m1`；
- `stock_base.tk`；
- `stock_base.zb`。

这些表注册时从本地 catalog 构造 Arrow schema，既不创建客户端，也不执行
`DESCRIBE TABLE`。source fingerprint 的 `schema_source` 为 `catalog`。自定义表会在注册时
连接并执行 `DESCRIBE TABLE`，`schema_source` 为 `remote`。

支持的类型转换包括整数、浮点、字符串/FixedString/Enum、Date、带时区 DateTime、
DateTime64、Decimal 和 Array；Nullable、LowCardinality 会递归解包。未知类型产生
`SchemaMismatchError`，避免静默降级。

真实服务的可选集成测试会逐列比较 catalog 与 `DESCRIBE TABLE`，用于发现 schema drift。

## 惰性连接与凭证

`add_clickhouse_connection()` 只验证名称、host、port 和 timeout。首次扫描或自定义表注册
才创建 `clickhouse-connect` client。密码优先使用 `ClickHouseConfig.password`，否则在
连接时读取 `password_env`；两者都不出现在审计中。

同一 profile 的客户端会缓存复用。替换已经打开的 profile 会先关闭旧 client，
`DataClient.close()` 会关闭所有缓存。

## 查询下推与参数安全

数据库、表、列和别名只接受 ClickHouse 标识符语法并用反引号引用。查询值使用带类型的
server parameters：

- `{start:<ClickHouseType>}` 与 `{end:<ClickHouseType>}`；
- `{partition_start:<Type>}` 与 `{partition_end:<Type>}`；
- `{instruments:Array(String)}`；
- `{limit:UInt64}`。

Date 列接收 Python `date`，DateTime 列接收按规格时区规范化的 `datetime`。`order_columns`
为空时按时间键、证券键排序；事件表显式加入 `time_int` 或 `seqno` 保持同一时间内顺序。

## 分区过滤与范围要求

带 `partition_column` 的规格默认必须同时提供 `start` 和 `end`。扫描既保留业务时间列的
精确闭区间，又把日期范围下推到分区列，避免扫描无关分区。默认分钟、盘口快照和逐笔表
都使用 `date` 分区。

可以用 `require_time_range=True` 在无分区列时也强制双边范围；显式 `False` 只在没有
catalog/分区强制规则时有效。

## 明湖代码后缀

内置表的 `code` 不含交易所后缀，`exg` 表示市场。若 schema 同时有 `code` 和 `exg`，
后端在 SELECT 和股票池过滤中都使用同一表达式：

```text
1 -> .SZ
2 -> .SH
3 -> .BJ
```

因此结果统一为 `000001.SZ` 形式，`instruments` 也必须带后缀。过滤值仍通过
`Array(String)` 参数传入，不拼接到 SQL。

## 日线复权

只有 `stock_base.daily` 且包含 `hfq` 时注册 `PriceAdjustment`。客户端在扫描字段与
`hfq` 后，用 Arrow compute 逐行相乘，再移除未被调用者请求的因子列。默认与可选行为见
[价格复权](../guides/semantics.md#价格复权)。指数日线没有该策略。

## 事件表

`minghu_tk` 和 `minghu_zb` 的 `panel_compatible=False`。同一时间同一证券多行是业务事实，
不会被合并；调用 `get_panel()` 在发出 SQL 前失败。使用 `get_table()` 并请求稳定序列字段。
