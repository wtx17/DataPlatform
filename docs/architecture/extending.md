# 扩展机制

## 新增后端

实现 `DataBackend` 的四个方法：

1. `prepare(spec)`：验证规格，构造完整 Arrow schema、私有 source descriptor 与
   `DatasetContract`；
2. `scan(dataset, query)`：返回至少包含时间键、证券键和请求字段的 Arrow table；
3. `fingerprint(dataset)`：返回可 JSON 序列化、无凭证的来源信息；
4. `close()`：释放缓存资源，并允许重复调用。

然后在 `DataClient.__init__` 的 backend registry 中加入实现，并为规格提供稳定的
`backend` 值。实现时必须保持以下不变量：

- 不把调用者值拼接成查询语言；
- typed empty result 与注册 schema 一致；
- 不在 fingerprint 中写密码、token 或不必要的身份信息；
- `scan()` 不负责 pivot 或审计；
- 导入模块不得连接远程服务。

若后端的内置数据源可以维护本地 catalog，`prepare()` 应优先使用 catalog，避免文档构建、
静态分析和普通注册依赖远程服务。自定义来源需要远程 schema discovery 时，应在文档中明确
其副作用。

## 新增默认数据集

### ClickHouse

1. 在 `clickhouse_catalog.py` 增加准确的列名/类型 tuple；
2. 在 `initialize.py` 的 panel 或 long spec 集合中增加注册；
3. 正确配置 time、partition、order、frequency 和 panel compatibility；
4. 在 `field_notes.toml` 增加 schema 家族、数据集名与关键字段类型说明；
5. 运行同步脚本和 catalog 集成测试。

### Tushare

1. 定义字段 tuple 与 Arrow schema；
2. 在 `tushare_catalog.py` 增加一个 `TushareDatasetCatalog` 逻辑实体；
3. 分别声明普通/VIP 等 `TushareApiRoute`，以及 period/date/membership 查询形状；
4. 选择 disclosure、membership 或 event 语义，声明表身份列、排序、宽表键和修订优先级；
5. 在初始化集合与 `field_notes.toml` 加入数据集；
6. 用 fake client 覆盖普通/VIP 自动路由、无 fallback、无损修订、错误字段、PIT 状态机和
   行业区间边界。

同步脚本会因未知 family、数据集名变化、字段删除或类型漂移而失败。这使 catalog 变化必须
显式更新字段语义，而不是静默改变站点。

## 新增查询模式

新增模式前先判断它是否能表达为现有两种结果：

- 唯一键长表 → 普通 panel transform；
- 多事件 → Arrow table；
- 公告可用性 → PIT transform。

确需新模式时，在客户端集中处理 orchestration，不要把结果元数据和审计散落到后端。
建议步骤：

1. 扩展内部 `QueryMode`，不改变已有公开签名；
2. 在 `_execute()` 中复用数据集查找、query validation 和 audit lifecycle；
3. 让后端仍返回 Arrow；
4. 用独立纯函数完成转换；
5. 明确定义 duplicate、null key、empty result 和 metadata 语义；
6. 为成功和每类失败验证审计。

如果新模式需要公共参数，属于 API 变更，应先设计兼容策略、类型签名、docstring、迁移文档
与版本策略，不能只在私有实现中接受未声明参数。

## 审阅清单

- 新公开对象是否加入包 `__all__` 或显式扩展点清单；
- 所有公开类、方法和函数是否有英文 NumPy 风格 docstring；
- autodoc 导入是否在无凭证环境中安全；
- 是否有本地可复现的单元测试与文档示例；
- 能力矩阵、字段表、后端专题和维护清单是否同步；
- `sphinx-build -W -n`、doctest、Ruff、mypy 和非集成测试是否通过。
