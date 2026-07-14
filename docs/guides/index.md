# 核心方法和查询指南

统一查询层先把调用参数规范化为 `DataQuery`，再交给后端扫描。无论数据来自哪里，字段、
闭区间、股票池、结果元数据和审计规则保持一致。

```{toctree}
:maxdepth: 1

queries
semantics
```

先阅读[注册与查询](queries.md)理解两个结果 API，再阅读[特殊语义与审计](semantics.md)
处理复权、事件表、PIT 和复现信息。
