# Docstring 规范

## 范围与语言

以下对象必须有非空 docstring：

- `quant_data.__all__` 中的类和异常；
- `DataClient` 的全部公开方法；
- 三类 dataset spec 与两类 connection config；
- `initialize_data_client()` 及离线规格辅助函数；
- `DataBackend` 协议和三个内置后端的公开方法；
- `RegisteredDataset`、`DataQuery`、转换函数和审计 writer 等扩展点。

docstring 采用英文 NumPy 风格，使签名、类型检查和对象级交叉引用保持一致。教程正文使用
中文。私有辅助函数不因文档而批量公开；影响下推、复权、PIT、去重或扩展不变量的行为在
架构文章中解释。

## 章节顺序

按需要使用以下标准章节：

1. 单行摘要；
2. 补充说明；
3. `Parameters`；
4. `Returns` 或 `Yields`；
5. `Raises`；
6. `Notes`；
7. `Examples`。

不要重复签名中的默认值和类型；Sphinx 从注解自动取得类型。参数名必须与签名完全一致，
多个参数只有共享语义时才写成 `start, end`。

## 示例

```python
def scan(self, dataset: RegisteredDataset, query: DataQuery) -> pa.Table:
    """Execute a normalized query against the prepared source.

    Parameters
    ----------
    dataset
        Dataset returned by ``prepare``.
    query
        Validated projection and filter request.

    Returns
    -------
    pyarrow.Table
        Long table containing both configured key columns.

    Raises
    ------
    RemoteQueryError
        If the remote service rejects the query.

    Notes
    -----
    Values are bound parameters and never interpolated into query text.
    """
```

类 docstring 说明构造参数和跨方法不变量；方法 docstring 只描述该调用。异常类若没有新增
参数或行为，一行摘要即可。

## 示例执行规则

doctest 只包含本地、确定、无凭证的行为，例如检查离线规格名称。以下内容不要作为可执行
doctest：

- ClickHouse/Tushare 网络调用；
- 依赖用户目录或真实 Parquet 文件的代码；
- 当前日期、随机 UUID、耗时或环境特定路径；
- 需要秘密或付费数据权限的示例。

这类示例使用普通 `python` code fence，并给出预期语义而非伪造输出。
