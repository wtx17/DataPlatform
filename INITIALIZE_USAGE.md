# 初始化与默认数据集文档已迁移

原字段手册已迁入 Sphinx 站点，并改为由初始化规格和后端 catalog 自动同步：

- [统一初始化](docs/getting-started/initialization.md)
- [默认数据集能力矩阵](docs/datasets/capabilities.md)
- [共享字段手册](docs/datasets/fields.md)

请勿在本文件继续维护字段副本。更新默认规格或 catalog 后运行：

```bash
python docs/_scripts/sync_reference.py
```
