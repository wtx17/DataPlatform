# 注册与查询

## `register()`

`register(spec)` 完成三件事：验证公共键配置、根据 `spec.backend` 选择后端、调用后端
`prepare()` 生成 `RegisteredDataset`。再次注册同名数据集会替换客户端内的旧定义。

三种规格分别用于：

- `DatasetSpec`：本地 Parquet 文件、目录或 glob；
- `ClickHouseDatasetSpec`：连接名与远程表；
- `TushareDatasetSpec`：连接名、catalog API 与查询语义。

数据集名称、键列不能为空，时间键与证券键不能相同，时区必须是有效 IANA 名称。
后端还会检查路径、连接名、远程标识符、catalog 字段和保留参数。

## `get_panel()`

```python
panels = data.get_panel(
    dataset="daily_bar",
    fields=["open", "close", "volume"],
    start="2026-07-01",
    end="2026-07-10",
    instruments=["600000.SH", "000001.SZ"],
    adjusted=None,
)
```

返回值始终是 `dict[str, pandas.DataFrame]`，字段顺序与请求一致。即使只请求一个字段，
也要用字段名取出：

```python
close = data.get_panel("daily_bar", ["close"])["close"]
```

每张宽表以时间为 index、证券为 columns。普通面板要求每个 `(time, instrument)` 只有
一行；重复键抛出 `DuplicateObservationError`，不会隐式聚合。

## `get_table()`

```python
table = data.get_table(
    dataset="minghu_zb",
    fields=["price", "volume", "side", "seqno"],
    start="2026-07-01 09:30:00",
    end="2026-07-01 09:31:00",
    instruments=["600000.SH"],
    limit=100_000,
)
```

返回 `pyarrow.Table`。时间键和证券键总是排在请求字段之前，调用者不能把键列再写进
`fields`。长表允许同一时间与证券有多条事件；因此盘口、逐笔、股东增减持必须使用
这个 API。

`limit` 只能是正整数且只出现在 `get_table()`。后端在排序后应用 limit：Parquet 用
DuckDB 参数，ClickHouse 用 `UInt64` 参数，Tushare 在规范化、去重和排序后截取。

## 时间范围是闭区间

`start` 与 `end` 都包含边界值，可以只传一端；分区表、行业成员、事件表和 PIT 等特定
数据集会要求两端齐全。

```python
data.get_panel("daily_bar", ["close"], start="2026-07-01")
data.get_panel("daily_bar", ["close"], end="2026-07-31")
```

远程规格会用自身时区本地化无时区时间，或把已有时区转换到配置时区。本地 Parquet
查询不执行本地化，只让 DuckDB 将存储列转换成 timestamp。

对于日内数据，`end="2026-07-31"` 表示当天 `00:00:00`。要包含整天，应给出明确的
右边界：

```python
end = "2026-07-31 23:59:59.999999"
```

## 股票池的三种状态

| `instruments` | 行为 |
| --- | --- |
| `None` | 请求后端允许的全部证券；普通非 VIP 财报接口不允许此值。 |
| 非空序列 | 过滤数据，并按调用者给出的顺序排列宽表列。 |
| `[]` | 不扫描后端，返回保留 schema、字段和列语义的空结果。 |

请求中没有观测的证券仍保留为全缺失列。没有显式股票池时，普通宽表按观察到的证券代码
升序排列。证券标识不能为空或重复。

明湖 ClickHouse 数据的原始 `code` 不带后缀。后端根据 `exg` 投影出 `.SZ`、`.SH`、
`.BJ`，所以查询这些表时股票池也必须带后缀。

## 字段与空结果

`fields` 至少包含一个非空、唯一字段，并且不能包含配置的两个键列。未知字段在扫描前
抛出 `FieldNotFoundError`。空查询结果仍具有：

- 请求字段对应的字典键；
- 请求股票池对应的列和顺序；
- 正确命名的时间 index 与证券 columns；
- Arrow 长表中与 catalog 一致的列类型。

## 常见异常

| 异常 | 典型原因 |
| --- | --- |
| `DatasetRegistrationError` | 路径无匹配、键列缺失、连接或 API 未配置、保留参数冲突。 |
| `DatasetNotFoundError` | 查询尚未注册的数据集名称。 |
| `FieldNotFoundError` | 字段不在注册 schema 中。 |
| `InvalidQueryError` | 字段重复、边界倒置、缺少必需范围、股票代码不合法、事件表请求宽表。 |
| `SchemaMismatchError` | schema 无法合并、远端类型不支持、结果缺键或键为 null。 |
| `DuplicateObservationError` | 普通宽表中同一时间和证券出现多行。 |
| `BackendConnectionError` | 依赖、凭证或连接创建失败。 |
| `RemoteQueryError` | ClickHouse/Tushare 请求失败或远程返回结构不合法。 |
| `AuditWriteError` | 审计目录或原子写入失败。 |

查询失败也会先写入失败审计；如果审计本身无法持久化，`AuditWriteError` 会成为最终错误。
