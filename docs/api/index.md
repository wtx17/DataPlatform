# API 参考

稳定公共入口以 `quant_data.__all__` 为准；初始化辅助函数与关键扩展点由同步脚本显式列出，
避免递归暴露私有实现。对象签名、类型和 docstring 由 autodoc/autosummary 直接从当前代码
生成，因此无需手工复制 API。

```{toctree}
:maxdepth: 1

public
```

查询的首选入口是 `quant_data.DataClient`。数据模型从包根导入；统一初始化函数位于
`quant_data.initialize`。后端 source descriptor 和 catalog 对象属于扩展接口，兼容性
级别低于包根公开 API，修改时仍需同步架构与后端文档。
