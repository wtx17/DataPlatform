# quant_data

`quant_data` 是面向量化研究的统一 Python 数据访问库，支持本地 Parquet、ClickHouse 和
Tushare。它既能把唯一键长表转换为 `time × instrument` Pandas 宽表，也能以
`pyarrow.Table` 保留盘口、逐笔和股东交易等多事件数据，并为每次查询写入可追溯审计。

## 快速安装

项目要求 Python 3.11 或更高版本：

```bash
conda activate quant_data
python -m pip install -e .
```

远程后端按需安装：

```bash
python -m pip install -e ".[clickhouse]"
python -m pip install -e ".[tushare]"
```

最小本地用法：

```python
from quant_data import DataClient, DatasetSpec

with DataClient() as data:
    data.register(DatasetSpec("daily", ["data/*.parquet"]))
    close = data.get_panel("daily", ["close"])["close"]
```

使用本地 Tushare 归档并保留原逻辑数据集名称：

```python
from quant_data.initialize import initialize_data_client

data = initialize_data_client(
    tushare_data_dir="/Users/wtx/Sync/Quant/quant_data_infra/tushare/data",
)
income = data.get_table("income", ["total_revenue"])
```

表数据完全从 Parquet 读取；PIT 和行业成员面板只远程请求 `trade_cal`。

## 完整文档

从 [文档首页](docs/index.md) 开始，或直接查看：

- [安装与快速上手](docs/getting-started/index.md)
- [核心查询指南](docs/guides/index.md)
- [后端语义](docs/backends/index.md)
- [架构与扩展](docs/architecture/index.md)
- [API 参考](docs/api/index.md)
- [数据集能力与字段](docs/datasets/index.md)

构建站点：

```bash
conda activate quant_data
conda install graphviz
python -m pip install -e ".[dev,docs]"
sphinx-build -W -n -b html docs docs/_build/html
```
