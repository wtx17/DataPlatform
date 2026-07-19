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

每个业务实体只有一个注册名。例如 `income` 的普通与 VIP API 是按股票池自动选择的路由，
而 PIT 是 `get_panel()` 的固有语义；`get_table()` 则保留原始公告和修订长表。键、频率与
方法语义集中在能力矩阵中。

```{admonition} 生成来源
:class: note

`docs/_scripts/sync_reference.py` 只读取 `quant_data.__all__`、初始化规格、ClickHouse catalog、
Tushare catalog 和 `field_notes.toml`。它不会调用 `initialize_data_client()`、创建 backend
client、读取密码/token 或执行远程查询。
```
