# 2image v2.2.0

这是自 v2.1.0 之后一次跨越多个子系统的全面升级：引入 Provider Reliability Core（编排器 / 健康检查 / 熔断器 / 重试策略 / 错误分类 / 取消机制），新增 Job Queue V2 与 Provider 性能指标体系；界面侧建立设计令牌系统并落地统一组件库（按钮 / 状态药丸 / 供应商卡片 / 错误横幅 / 生成状态标签 / 强度滑块），补全 i18n 覆盖；数据层加入 FTS5 全文搜索、翻译缓存、异步日志；架构侧抽出 Application Controllers 并定义 ImageProvider Protocol，配合 code-quality 审查与 CI 加固，整体可维护性与可观测性显著提升。

## 主要更新

### Provider Reliability Core（Phase 2）

- **编排器（GenerationOrchestrator）**：统一调度多供应商、按错误类别决定是否降级或终止；支持取消令牌（CancellationToken）与截止期限（Deadline），在超时或用户取消时立即停止。
- **健康检查与熔断（ProviderHealth / HealthRegistry）**：持续跟踪每个供应商的延迟（EMA）、成功率与连续失败次数，达到阈值进入 OPEN 状态被跳过；冷却期后转入 HALF_OPEN，单次成功即恢复。
- **重试策略（RetryPolicy）**：指数退避 + 抖动，并尊重上游的 Retry-After 头；可针对不同供应商命名预设（`get_named_policy`）。
- **错误分类（Error Taxonomy）**：将 HTTP 状态码与提供者特定异常映射到 `ProviderAuthError` / `ProviderQuotaError` / `ProviderRateLimitError` / `ProviderTransientError` / `ProviderPolicyError` / `ProviderInvalidRequestError`，为编排器的降级决策提供依据。
- **故障注入框架（Phase 0）**：ScriptedProvider、FakeHTTP、Scenario 让测试不再依赖外部网络；CancellationToken、Deadline、RetryPolicy 均有对应单测。

### Job Queue V2 与性能指标（Phase 4）

- **Job Queue**：任务状态机（queued → running → success / failed / cancelled），支持暂停 / 恢复 / 批量取消；回调在 UI 线程触发，可直接更新界面。
- **Provider Metrics**：每个供应商的请求数、失败数、P95 延迟、连续失败次数；`MetricsCollector` 按供应商 id 自动创建，`all()` 输出汇总字典。
- **Keyset Pagination**：基于游标的分页，避免 OFFSET 在大数据集上的性能抖动；翻译缓存与异步日志配套服务层性能优化。

### 界面组件库与国际化（Phase 6）

- **Design Tokens（`config/design_tokens.py`）**：DARK / LIGHT 双主题色板、间距刻度、按钮状态色、状态药丸色；`config/theme.py` 改为单一来源，避免漂移。
- **统一组件**：Primary / Secondary / Danger / Ghost 按钮、Info / Success 状态药丸、ProviderCard（选中态 + 密钥状态）、ErrorBanner（可清空）、EmptyState、GenerationStateLabel（含进度条）、Compact / Full 强度滑块。
- **i18n 增补**：新增 18 个翻译键，覆盖状态标签、组件文案、错误提示；当前共 114+ 键，3 种 locale（zh-CN / en / ja）。

### 搜索、缓存与日志（Phase 5 / C-F）

- **FTS5 全文搜索（`data/search.py`）**：手动同步 + 失败回退 LIKE，支持 prompt / translated / provider / tags 字段匹配；线程安全的 setup 与表存在性检查。
- **Translation Cache**：单例 LRU 缓存，避免重复调用外部翻译 API；命中率统计与清空接口。
- **AsyncLogger**：独立线程写日志文件，UI 线程不再阻塞。

### 架构与代码质量（Phase B-F）

- **Application Controllers**：从 `App` 抽出 `MenuController`、`SettingsController`、`GenerationController`，`ui/app.py` 从 953 行瘦身至 633 行；通过 Protocol 接口与 UI 层解耦。
- **ImageProvider Protocol**：统一 `provider_id` / `display_name` / `supports_img2img` / `generate` 契约，`map_http_error` 复用错误分类；现有 `try_*` 函数继续工作，新提供者可按 Protocol 直接接入。
- **file_ownership**：路径遍历 / 符号链接 / 越权访问测试覆盖；UUID 文件名防碰撞；事务迁移保证原子性。

### CI 与发布（Phase 7）

- **质量门禁**：ruff 关键错误（F821/E9）阻断，扩展检查与格式检查非阻断；pip-audit 安全扫描接入（非阻断）。
- **覆盖率阈值**：pytest-cov 低于 50% 失败；当前覆盖率 55%+。
- **发布产物**：自动构建 PyInstaller 单文件 + Inno Setup 安装包，生成 SHA256SUMS 校验和与 SPDX SBOM。

## 下载与安装

- **安装包**：下载 `text2image_pro_v2.2.0.exe`，运行后按向导安装。
- **便携版**：下载 `text2image_pro.exe`，无需安装即可直接运行。
- 现有用户的配置、历史记录和生成图片仍保存在 `~/.text_to_image_app/`，升级前可关闭程序后直接覆盖安装。

## 验证

- GitHub Actions：Ubuntu 质量门禁 + Windows 测试 + Windows 构建三阶段均已通过。
- 完整测试套件：306 项通过，1 项在 headless 环境跳过（tkinter 不可用时自动跳过）。
- 安全审计：pip-audit 集成至 CI，依赖供应链风险持续监控。

**完整变更**：https://github.com/Aswellle/2image/compare/v2.1.0...v2.2.0
