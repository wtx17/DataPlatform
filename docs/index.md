# quant_data 文档

`quant_data` 为量化研究提供统一的数据访问接口：同一套注册和查询方法可以读取本地
Parquet、ClickHouse 与 Tushare，将唯一的长表观测转换成 `time × instrument`
Pandas 宽表，也能保留盘口、逐笔和股东交易等多事件 Arrow 长表。

| 路径 | 内容 |
| --- | --- |
| [快速开始](getting-started/index.md) | 安装依赖，注册第一个数据集，并理解统一初始化与上下文管理器。 |
| [查询指南](guides/index.md) | 掌握 `register()`、`get_panel()`、`get_table()`、闭区间、股票池、复权与元数据。 |
| [架构与扩展](architecture/index.md) | 理解 Backend → Arrow → Transform → Result/Audit 数据流以及新增后端和数据集的方法。 |
| [数据集与字段](datasets/index.md) | 查看从初始化规格和 catalog 自动生成的能力矩阵与字段手册。 |

```{admonition} 两种结果形态
:class: tip

唯一的 `(time, instrument)` 数据适合 `get_panel()`；同一键允许多条事件的数据必须用
`get_table()`。两种查询都会写入审计记录。
```

```{toctree}
:maxdepth: 2
:caption: 开始使用与快速上手

getting-started/index
```

```{toctree}
:maxdepth: 2
:caption: 核心方法和查询指南

guides/index
```

```{toctree}
:maxdepth: 2
:caption: 后端与特殊数据语义

backends/index
```

```{toctree}
:maxdepth: 2
:caption: 架构设计和扩展机制

architecture/index
```

```{toctree}
:maxdepth: 2
:caption: API 参考

api/index
```

```{toctree}
:maxdepth: 2
:caption: 数据集与字段手册

datasets/index
```

```{toctree}
:maxdepth: 2
:caption: 文档维护规范

contributing/index
```
