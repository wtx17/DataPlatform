# 同步与验收

## 代码变化对应的文档变化

| 代码变化 | 必须同步 |
| --- | --- |
| 包根公开对象或异常 | `__all__`、NumPy docstring、API 同步页、使用/迁移说明。 |
| `DataClient` 参数或返回语义 | 方法 docstring、查询指南、架构时序、测试。 |
| DatasetSpec/Config 字段 | 类 docstring、快速开始、能力矩阵生成逻辑。 |
| 默认初始化规格 | `field_notes.toml` 数据集列表、能力矩阵、初始化说明。 |
| ClickHouse catalog 列或类型 | `field_notes.toml`、字段手册、远程 catalog drift 测试。 |
| Tushare catalog/schema/query style | `field_notes.toml`、字段手册、Tushare 专题、fake-client 测试。 |
| 复权字段或默认值 | 查询语义、ClickHouse 专题、审计说明、测试。 |
| PIT disclosure/lag/buffer/dedupe | PIT 时序图、Tushare 专题、能力矩阵、无前视边界测试。 |
| 后端协议或新后端 | 架构模型、扩展指南、API 扩展点、导入安全测试。 |
| 审计 schema 或持久化 | 查询语义、架构、示例 metadata、成功/失败测试。 |

## 生成文档

更新 API、初始化规格或 catalog 后运行：

```bash
python docs/_scripts/sync_reference.py
```

CI/验收只检查，不允许静默重写：

```bash
python docs/_scripts/sync_reference.py --check
```

脚本会检查：

- API 清单与 `quant_data.__all__`；
- 默认规格引用的表/API 都存在本地 catalog；
- 普通、VIP、PIT 共享家族的 schema 完全一致；
- `field_notes.toml` 的家族、数据集名、字段名和声明类型没有漂移；
- 三个生成 Markdown 文件与当前代码一致。

## 导入安全

autodoc 会真实导入包，因此以下命令必须在没有 ClickHouse/Tushare 凭证时成功：

```bash
env -u MINGHU_CLICKHOUSE_PASSWORD -u TUSHARE_TOKEN \
  python -c "import quant_data; import quant_data.initialize"
```

模块顶层不得调用 `initialize_data_client()`、实例化 backend client、读取环境凭证或探测
远程 schema。同步脚本只能使用离线规格 helper 和本地 catalog。

## 完整验收

在 `quant_data` Conda 环境中依次执行：

```bash
python docs/_scripts/sync_reference.py --check
sphinx-build -W -n -b html docs docs/_build/html
sphinx-build -W -b doctest docs docs/_build/doctest
pytest -m "not clickhouse"
ruff check .
mypy .
```

HTML 构建还应人工检查：

- 首页与七组导航在宽屏、窄屏可用；
- 亮色、暗色模式下三张 SVG 的文字和连线可读；
- 中文搜索能找到类名、数据集名与正文术语；
- API 签名、参数章节和源码链接正确；
- 字段大表可横向滚动且不会撑破正文；
- 页面源代码中没有外部字体或脚本 URL；
- `docs/_build/html/index.html` 可直接打开。

真实 ClickHouse catalog 比对属于可选集成测试，需要显式凭证和 `clickhouse` marker；它不属于
默认离线验收。
