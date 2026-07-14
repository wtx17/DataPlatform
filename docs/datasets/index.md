# 数据集与字段手册

默认数据集文档由代码 catalog 生成，分为两层：

- [能力矩阵](capabilities.md)：每个注册名称的来源、频率、键、范围、股票池、宽表能力和
  特殊语义；
- [字段手册](fields.md)：按 schema 家族复用的字段名、类型、键角色和人工说明。

```{toctree}
:maxdepth: 1

capabilities
fields
```

普通、VIP 和 PIT 变体共享字段表，但查询能力不同。例如 `income`、`income_vip`、
`income_pit`、`income_vip_pit` 使用同一 Arrow schema；股票池要求、频率和面板语义集中
在能力矩阵中。

```{admonition} 生成来源
:class: note

`docs/_scripts/sync_reference.py` 只读取 `quant_data.__all__`、初始化规格、ClickHouse catalog、
Tushare catalog 和 `field_notes.toml`。它不会调用 `initialize_data_client()`、创建 backend
client、读取密码/token 或执行远程查询。
```
