# 文档维护规范

文档与代码使用同一仓库、同一评审和同一严格构建。公开 API 说明写在代码 docstring；教程、
架构、后端语义和数据集手册写在 `docs/`。

```{toctree}
:maxdepth: 1

docstrings
maintenance
```

修改前先阅读[docstring 规范](docstrings.md)，提交前按[同步与验收](maintenance.md)执行完整
检查。生成页带有 “do not edit” 注释，不应直接修改。
