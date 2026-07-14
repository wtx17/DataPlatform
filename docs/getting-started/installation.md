# 安装与文档构建

## 运行环境

项目要求 Python 3.11 或更高版本。仓库约定使用 `quant_data` Conda 环境；Graphviz
由 Conda 提供，Python 文档工具由 `docs` extra 提供。

```bash
conda activate quant_data
conda install graphviz
python -m pip install -e ".[dev,docs]"
```

远程查询依赖按需安装：

```bash
python -m pip install -e ".[clickhouse]"
python -m pip install -e ".[tushare]"
```

`clickhouse-connect` 与 `tushare` 都不是导入 `quant_data` 的前置条件；后端只在实际创建
远程客户端时导入它们。

## 构建命令

本地热更新预览：

```bash
sphinx-autobuild docs docs/_build/html
```

合并前执行严格 HTML 构建：

```bash
sphinx-build -W -n -b html docs docs/_build/html
```

离线可复现示例使用 doctest builder：

```bash
sphinx-build -W -b doctest docs docs/_build/doctest
```

HTML、搜索索引、主题资源和 Graphviz SVG 都写入 `docs/_build/`，不会提交 Git。
`docs/_build/html/index.html` 可以直接打开；只有热更新和自动刷新需要
`sphinx-autobuild` 的本地服务。

Sphinx 9.1 要求 Python 3.12。项目仍支持 Python 3.11，因此 `docs` extra 在 Python
3.12+ 安装计划版本 `9.1.x`，在 Python 3.11 安装兼容的 `9.0.x`；两条分支都使用同一套
严格构建配置。

## 可选的在线交叉引用

严格构建默认不访问网络。需要为 Python、Pandas 或 Arrow 对象解析外部链接时，可显式
启用 intersphinx：

```bash
QUANT_DATA_DOCS_ONLINE=1 sphinx-build -W -n -b html docs docs/_build/html
```

站点本身不引用外部字体或脚本；在线开关只影响构建阶段下载对象清单。
