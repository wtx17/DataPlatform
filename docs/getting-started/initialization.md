# 统一初始化

`quant_data.initialize.initialize_data_client()` 集中配置项目默认连接，并按固定顺序注册
五张明湖表，以及十个 Tushare 逻辑数据集。普通/VIP 路由和 PIT 宽表语义不再占用额外
注册名。

```python
from quant_data.initialize import initialize_data_client

data = initialize_data_client()
```

## 环境变量

| 用途 | 首选变量 | 兼容变量 | 默认值 |
| --- | --- | --- | --- |
| 审计目录 | `QUANT_DATA_AUDIT_DIR` | — | `.quant_data/audit` |
| ClickHouse host | `QUANT_DATA_CLICKHOUSE_HOST` | `MINGHU_CLICKHOUSE_HOST` | `chdb.tradegdb.com` |
| ClickHouse port | `QUANT_DATA_CLICKHOUSE_PORT` | `MINGHU_CLICKHOUSE_PORT` | `8123` |
| ClickHouse username | `QUANT_DATA_CLICKHOUSE_USERNAME` | `MINGHU_CLICKHOUSE_USERNAME` | 无 |
| ClickHouse password | `QUANT_DATA_CLICKHOUSE_PASSWORD` | `MINGHU_CLICKHOUSE_PASSWORD` | 无 |
| Tushare token | `QUANT_DATA_TUSHARE_TOKEN` | `TUSHARE_TOKEN` | 无 |

函数参数优先于环境变量。密码和 token 字段不会进入对象 `repr`，审计 fingerprint 也不会
保存凭证或 ClickHouse username。

## 只初始化需要的后端

没有远程凭证时，可以关闭对应注册：

```python
local_plus_catalog = initialize_data_client(
    register_clickhouse=True,
    register_tushare=False,
)

tushare_only = initialize_data_client(
    register_clickhouse=False,
    register_tushare=True,
)
```

只想查看默认规格或数据集名称时，不要调用统一初始化；以下辅助函数完全离线：

```python
from quant_data.initialize import (
    clickhouse_dataset_specs,
    registered_dataset_names,
    tushare_dataset_specs,
)

clickhouse_specs = clickhouse_dataset_specs("research")
tushare_specs = tushare_dataset_specs("ts")
names = registered_dataset_names()
```

这些规格的生成与注册均为离线操作；凭证到第一次查询才解析。

完整默认集合及能力由[自动能力矩阵](../datasets/capabilities.md)列出。
