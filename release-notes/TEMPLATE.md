# Release Notes 撰写规范

> 本文件描述 2image 项目的发行版描述（Release Notes）撰写规范。
> 所有发行版描述统一存放于 `release-notes/` 目录，命名为 `v<version>.md`。

---

## 文件存放规则

- 路径：`release-notes/v<version>.md`（例如 `release-notes/v2.3.0.md`）
- 一个版本对应一个文件，与 `version.json` 中的版本号一一对应
- CI/CD 流程（`.github/workflows/ci.yml`）在打 `v*` 标签时自动读取对应文件作为 Release 描述

## 版本号规则

遵循 [Semantic Versioning](https://semver.org/)：

| 变更类型 | 版本号变化 | 示例 |
|---|---|---|
| 破坏性变更（需用户手动迁移） | MAJOR（x.0.0） | v2.0.0 |
| 新功能、子系统升级 | MINOR（x.y.0） | v2.3.0 |
| Bug 修复、小优化、内部重构 | PATCH（x.y.z） | v2.2.2 |

## 文档结构模板

```markdown
# 2image v<version>

<一句话概述本次更新的核心内容，概括用户可见的最大变化。>

## 主要更新

### <子系统 / 模块名>

- **<功能点名称>**：<具体描述，说明"做了什么"和"用户/开发者感知到什么">。
- **<功能点名称>**：<描述>。

### <子系统 / 模块名>

- ...

## 下载与安装

- **安装包**：下载 `text2image_pro_v<version>.exe`，运行后按向导安装。
- **便携版**：下载 `text2image_pro.exe`，无需安装即可直接运行。
- <升级注意事项，如有。旧版配置/数据兼容性说明。>

## 验证

- GitHub Actions：<各阶段通过情况>。
- 完整测试套件：<数量> 项通过，<X> 失败/跳过。
- <其他质量指标：覆盖率、安全审计等>。

**完整变更**：https://github.com/Aswellle/2image/compare/<previous_tag>...<current_tag>
```

## 写作风格要求

1. **语气**：客观、简洁，使用中文（与项目 i18n 主语言一致）
2. **时态**：使用完成时或现在时，描述"已做了什么"而非"将要做"
3. **用户视角**：首段概述应让用户一眼看懂"这次更新对我有什么用"
4. **技术细节**：放在具体条目中，用粗体标注关键术语或模块名
5. **兼容性**：明确标注是否向后兼容，升级是否需要用户操作
6. **避免**：不要提及内部重构过程、审计行为、开发阶段前置工作；只描述结果

## 撰写流程

1. 确定版本号，更新 `version.json`
2. 在 `release-notes/` 目录下创建 `v<version>.md`
3. 自上次发布以来的 commit 日志作为素材，提炼用户可见变更
4. 编写完成后本地预览，检查格式与链接
5. 提交至主干，打 `v<version>` 标签，推送触发 CD

## 示例参考

- `release-notes/v2.2.0.md` — 多子系统全面升级（MINOR）
- `release-notes/v2.2.1.md` — 单一功能点小版本（PATCH）
- `release-notes/v2.3.0.md` — 可靠性基础设施接入（MINOR）
