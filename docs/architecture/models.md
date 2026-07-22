# 数据模型与边界

## Dataset definition

四类公开规格都是冻结、带 slots 的 dataclass。它们只描述来源和语义，不持有查询状态：

- `DatasetSpec`：路径、键、频率、时区、版本；
- `ClickHouseDatasetSpec`：连接、表、分区、排序、面板能力；
- `TushareDatasetSpec`：连接、可选逻辑数据集、固定参数、版本/时区与 PIT 日历参数；键、
  频率、远程路由和表/宽表语义不在公开规格中重复配置。
- `TushareParquetDatasetSpec`：本地归档根目录、逻辑数据集、可重建固定参数，以及仅供
  `trade_cal` 使用的 Tushare 连接；表/宽表仍复用同一 catalog。

`backend` 是选择实现的判别字段：普通 Parquet 与 Tushare Parquet 都固定选择
`"parquet"`，ClickHouse/Tushare 选择各自后端，调用者不能把规格伪装成其他来源。

## RegisteredDataset

后端 `prepare()` 返回 `RegisteredDataset`：

| 字段 | 所有权 | 用途 |
| --- | --- | --- |
| `spec` | 公共模型 | 规范化后的键、范围、频率和行为。 |
| `schema` | 后端构造 | 在扫描前验证请求字段，并为 typed empty result 提供类型。 |
| `source` | 后端私有 | 已解析文件、ClickHouse 表元数据或 Tushare API 元数据。 |
| `contract` | 后端构造 | 表/宽表各自的键、频率、范围要求、身份列与宽表能力。 |
| `adjustment` | 可选公共策略 | 因子列、受影响字段与默认开关。 |

客户端不会解释 `source`，只把它传回创建该对象的后端。新后端可以使用自己的冻结
dataclass，但必须让 `scan()` 和 `fingerprint()` 验证 source 类型，防止跨后端状态混用。

## DataQuery

公共 API 接受宽松的时间输入和任意 `Sequence[str]`，私有 `_prepare_query()` 将其规范化为：

- 不重复的字段 tuple；
- 已解析、按远程规格时区处理的 `datetime` 边界；
- 保留调用者顺序的证券 tuple、`None` 或空 tuple；
- 已验证的正整数 limit。

后端只接收 `DataQuery`，不用重复公共校验。价格因子如果需要但未由调用者请求，客户端会
创建替换后的 scan query；最终投影仍使用原始 query 字段。

## QueryAudit

`QueryAudit` 在调用开始时创建，状态从 `running` 转为 `success` 或 `failed`。来源
fingerprint、实际复权状态、日历对齐标记、结果尺寸和错误信息都在同一个对象累积，最后由
`AuditWriter` 序列化。

审计 writer 不吞掉异常。临时文件名包含 query ID，写入、flush、`fsync`、replace 后才
返回最终路径；失败时尽力删除临时文件并抛出 `AuditWriteError`。

## 转换边界

普通 `build_panels()` 接收 Arrow，使用 Polars 做 null/duplicate 检查与 pivot，再转换到
Pandas。PIT `build_daily_panels()` 接收公告 Arrow 与显式交易日列表，使用 Pandas 做日期
吸附、修订冲突处理、逐报告期状态维护和整行状态携带。它不会逐字段 forward fill。

两个函数都不访问后端、不读取配置、不写审计，因此可以独立测试，也可被新查询模式复用。
