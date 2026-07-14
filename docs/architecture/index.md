# 架构总览

系统把“来源如何读取”和“结果如何表达”分离。后端只需返回 Arrow 长表；客户端统一处理
校验、复权、转换、元数据与审计。

```{toctree}
:maxdepth: 1

models
extending
```

## 组件关系

```{graphviz} ../_static/diagrams/components.dot
:align: center
:alt: DataClient 经 DataBackend 读取 Arrow，转换为面板或长表并写入审计
```

`DataClient` 根据规格中的 `backend` 选择实现。`RegisteredDataset` 是准备阶段和查询阶段的
边界：它同时保存规范化规格、完整 Arrow schema、后端私有 source descriptor，以及可选
复权策略。

## 普通查询时序

```{graphviz} ../_static/diagrams/query-sequence.dot
:align: center
:alt: 普通查询从注册、参数校验、后端扫描、复权、转换到审计的顺序
```

注册只做一次，后续查询重用 prepared state。每次查询在验证前就创建 `QueryAudit`，所以
字段错误、范围错误和远程失败也能留下失败记录。成功结果写入尺寸和元数据后再原子落盘。

## PIT 查询时序

```{graphviz} ../_static/diagrams/pit-sequence.dot
:align: center
:alt: PIT 查询从公告缓冲、交易日历、披露延迟、去重、前向填充到审计的顺序
```

PIT 的核心不变量是“值只能在可用日及之后出现”。公告日先向后吸附到开市日，再增加
`disclosure_lag`，绝不向前吸附。左侧缓冲只用于找历史已知值；右侧 margin 只用于完成
日历定位；最后输出仍严格裁剪到用户闭区间。

三张图的 DOT 源码位于 `docs/_static/diagrams/`，Sphinx 构建时由 Graphviz 生成静态 SVG。
SVG 使用透明背景和固定高对比色，在亮色与暗色主题中均无需外部资源。
