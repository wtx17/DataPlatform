# 开始使用

本节给出最短可运行路径。先完成[安装与构建](installation.md)，再根据数据来源选择
[手工注册](quickstart.md)或[统一初始化](initialization.md)。

```{toctree}
:maxdepth: 1

installation
quickstart
initialization
```

核心对象的职责很简单：`DataClient` 持有已注册数据集和后端连接；三类 `DatasetSpec`
只描述数据来源与语义；`get_panel()` 和 `get_table()` 决定结果形态。

```{doctest}
>>> from quant_data.initialize import clickhouse_dataset_specs
>>> [spec.name for spec in clickhouse_dataset_specs()]
['minghu_daily', 'minghu_index_daily', 'minghu_m1', 'minghu_tk', 'minghu_zb']
```

这个示例只构造不可变规格，不读取密码，也不连接 ClickHouse。
