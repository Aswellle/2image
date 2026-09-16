# AUDIT_IMPLEMENTATION_GAP.md — 实现差距审计矩阵

> **审计日期**：2026-09-16
> **审计依据**：《2image 全面代码审查与开发修复优化计划》(version 2.1.0 基线)
> **当前代码版本**：`version.json` = `2.2.1`
> **审计方式**：独立静态代码审查 + 全部 306 个测试实际执行通过
> **状态定义**：`PASS` / `PARTIAL` / `FAIL` / `UNVERIFIED` / `REGRESSED`

---

## 一、审计方法论

每一项需求按以下证据链验证：

```
实现位置 → 关键调用链 → 测试文件 → 实际执行结果 → 验收条件
```

如果调用链断裂（代码存在但未被生产代码路径使用），状态记为 **PARTIAL** 或 **FAIL**。

---

## 二、P0 需求审计矩阵

| ID | 原始需求 | 当前实现 | 实际行为 | 状态 | 证据 | 偏差 | 修复方案 |
|---|---|---|---|---|---|---|---|
| **SEC-001** | `delete_entry()` 路径 containment + symlink 防护 | `file_ownership.py` 模块已实现；`repository.delete_entry()` 调用 `safe_delete_file()` | 删除前 canonicalize + `relative_to(root)` 检查；symlink 拒绝 | **PASS** | `services/generation/file_ownership.py`；`data/repository.py:369`；`tests/test_file_ownership.py` 24 项全通过 | 无 | — |
| **NET-001** | Provider 错误分类；401 不重试，429 backoff，5xx retry | `errors.py` 定义了完整 `ProviderError` 层级；`classify_http_error()` 映射 HTTP→domain | **但 providers 仍 raise `ValueError`/`RuntimeError`，不是 `ProviderError`；生产代码路径 `generate_image()` 仍 `except Exception`** | **FAIL** | `services/generation/errors.py` 存在；但 `services/image_service.py:61` 仍是 `except Exception`；providers 无 error mapping | **关键偏差**：错误分类器存在但未被生产路径使用；providers 抛出的 `ValueError` 无法被 orchestrator 的 `except ProviderError` 捕获 | 1. `generate_image()` 包装层将 `ValueError`/`RuntimeError` 映射到 `ProviderError`；2. 直接 wire orchestrator 到生产路径 |
| **JOB-001** | 全局 CancellationToken + absolute Deadline | `cancellation.py` 模块已实现；`Deadline` + `CancellationToken` 均可工作 | **但 `generate_image()` 不接收 token；UI `GenerationController` 不传递 token；orchestrator 存在但未被调用** | **FAIL** | `services/generation/cancellation.py` 存在且测试通过；但 `services/application/generation_controller.py:144` 直接调用 `generate_image()` 无 token 参数 | **关键偏差**：取消/截止功能已编写但完全未接入生产代码路径 | Wire orchestrator（内部已使用 token/deadline）到 `generate_image()` 或 `GenerationController` |
| **ROUTE-001** | Provider 稳定 `provider_id` 与 display name 解耦 | `provider_manifest.py` 定义了 `ProviderManifest(id=...)` 和 `LEGACY_NAME_TO_ID` | **但 `providers/__init__.py:61` 仍用 `info["name"]` 作为 `ALL_PROVIDERS` 字典 key；`DEFAULT_ORDER` 仍是 display name 列表** | **PARTIAL** | `services/generation/provider_manifest.py` 有 ID；但 `services/providers/__init__.:69` `ALL_PROVIDERS` 的 key 仍是 display name | 路由层面 ID 已存在，但运行时 registry 仍依赖 display name | 修改 registry 用 `info["id"]` 作为 key；或确保 `image_service.generate_image()` 接收的 name 能通过 `resolve_provider_id()` 转换 |
| **NET-002** | 图片下载强制最大字节/streaming cap | `bounded_download()` 已实现（25MB cap, Content-Type, streaming, SSRF） | **但所有 17 个 provider 仍使用 `safe_get_image()`（调用 `resp.content` 全量加载内存）** | **FAIL** | `services/generation/downloader.py` 存在；但 providers 全部 `from services.providers._net import safe_get_image` | 安全下载器已编写但零 provider 迁移到它 | 批量替换 providers 中的 `_safe_get_image(url)` → `bounded_download(url)` |
| **DATA-001** | JSON 迁移 transaction + report + 失败不 rename | `migrate_from_json()` 已重构：transaction + 仅全部成功时 rename + 错误日志 | 部分失败时保留原 JSON；有 migration report dict | **PASS** | `data/repository.py:432-507`；`tests/test_file_ownership.py::TestMigrationTransaction` 通过 | 无 | — |

---

## 三、P1 需求审计矩阵

| ID | 原始需求 | 当前实现 | 实际行为 | 状态 | 证据 | 偏差 | 修复方案 |
|---|---|---|---|---|---|---|---|
| **PAY-001** | 付费 Provider 默认 opt-in + budget guard | `DEFAULT_CONFIG` 中有 `paid_auto_opt_in: false`，`allow_paid` 参数存在 | `smart_router._filter_available()` 已过滤未配置 key 的付费接口；但无 budget 计数器 | **PARTIAL** | `config/settings.py DEFAULT_CONFIG`；`services/smart_router.py:128` | 无 budget 追踪/日限额 | 添加 budget 字段到 config；router 追踪日消耗 |
| **NET-003** | 统一 Retry/Backoff 框架 | `retry_policy.py` 已实现（exponential backoff + jitter + Retry-After） | **但 providers 仍各自实现 sleep 循环（`sleep(2)`, `sleep(10*attempt)`, `_MIN_INTV` 等）** | **PARTIAL** | `services/generation/retry_policy.py` 存在且测试通过；但 providers 未使用 | 框架存在但 providers 未迁移 | 逐步用 `RetryPolicy` 替换 provider 内联 sleep |
| **NET-004** | Thread-local HTTP session | `_net.py` 仍导出全局 `SESSION` | 所有 provider 共享同一 `requests.Session` | **FAIL** | `services/providers/_net.py:19` 全局 `SESSION` | 未实现 thread-local 或 `HttpClient` | 改为 `threading.local()` 或 per-thread session |
| **PERF-001** | 翻译缓存 + 后台 rate limiter | `translation/cache.py` LRU 缓存已实现 | 缓存生效；但全局 `_TRANS_LOCK` + `time.sleep()` 仍在批量化时串行化 | **PARTIAL** | `services/translation/__init__.py` 使用缓存；但仍有 `_TRANS_LOCK` + `_MIN_INTERVAL` sleep | 缓存减少 API 调用但 sleep 串行仍在 | 将翻译改为异步/后台线程 |
| **PERF-002** | 异步 QueueHandler logger | `logger/async_logger.py` 已实现（QueueHandler + RotatingFileHandler） | **`log_to_file()` 仍是默认（同步 open/write/rotate）；AsyncLogger 需手动 `setup()`** | **PARTIAL** | `services/logger/async_logger.py` 存在；但 `image_service.py:42` 默认 `log_cb = log_to_file` | AsyncLogger 存在但非默认 | 在 `main.py` 启动时调用 `AsyncLogger.setup()` 设为默认 |
| **DATA-002** | `clear_all_entries()` 处理孤儿文件 | `clear_all_entries(remove_files=True)` 已实现文件删除 + orphan report | 按设计工作 | **PASS** | `data/repository.py:389-424` | 无 | — |
| **DATA-003** | FTS5 + keyset pagination | `get_entries_keyset()` 已实现 keyset 分页；FTS5 表已创建 | `get_all_entries()`（OFFSET 版本）仍并存；FTS5 表存在但未在搜索路径中强制使用 | **PARTIAL** | `data/repository.py:179` keyset；但 UI 可能仍调用 `get_all_entries` | 旧 OFFSET 路径仍可用 | 确认 UI 默认使用 keyset |
| **PERF-003** | UUID-based 文件名 | `save_image_file()` 已实现 UUID + atomic write（tempfile + os.replace） | 不再有文件名碰撞 | **PASS** | `services/image_service.py:69-113`；`tests/test_file_ownership.py::TestUUIDFilenames` | 无 | — |
| **ROUTE-002** | Manifest-defined 模块顺序（不依赖 pkgutil 发现顺序） | `provider_manifest.py` 中 `FREE_PROVIDER_ORDER` 显式列表存在 | **但 `providers/__init__.py:70` 的 `DEFAULT_ORDER = list(FREE_PROVIDERS.keys())` 仍依赖 pkgutil 顺序** | **PARTIAL** | `FREE_PROVIDER_ORDER` 存在但未被 `DEFAULT_ORDER` 使用 | 显式顺序列表未接入默认路由 | `DEFAULT_ORDER` 改用 `FREE_PROVIDER_ORDER` |
| **ROUTE-003** | Health/latency/cost/quota scoring router | `router.py` 已实现 health-aware scoring（capability + health + latency + cost + quota） | **但 `GenerationController` 仍 import `smart_router.get_provider_order`，不是新 router** | **PARTIAL** | `services/generation/router.py` 存在且 `tests/test_router.py` 通过；但 `generation_controller.py:16` 仍用旧 router | 新 router 存在但未被生产代码使用 | `generation_controller.py` 改用新 `router.get_provider_order` |
| **I18N-001** | 所有用户可见文案 key 化 | `config/i18n.py` 有 114 keys 跨 3  locale | UI 中仍有部分硬编码中文（`app.py` 多处 `text="中文"`） | **PARTIAL** | `config/i18n.py` 存在；但 `grep` 显示 `ui/app.py` 有硬编码 | 未完成 | 逐步替换硬编码 |
| **UI-001** | Semantic design tokens | `config/theme.py` 有 `DARK_THEME`/`LIGHT_THEME` 色板 | 控件中仍有硬编码颜色值 | **PARTIAL** | `config/theme.py` 存在；但控件 token 不完全 | 部分完成 | 引入 semantic token layer |
| **UI-002** | View/ViewModel/Controller 拆分 | `services/application/` 有 `GenerationController`；UI 已拆分为 sidebar/main_content | `App` 仍直接 import 大量 repository 函数 | **PARTIAL** | `generation_controller.py` 存在；但 `app.py:24` 直接 `from data.repository import ...` | 部分解耦 | 进一步将 repository 访问移入 controller |
| **TEST-001** | Coverage ≥ 70%，核心 services 85%+ | `pyproject.toml` 有 coverage 配置 | 306 测试通过；但无强制 coverage gate | **PARTIAL** | `tests/` 306 通过 | 无 fail-under gate | 添加 `--fail-under` |
| **TEST-002** | Provider/并发/超时/恢复/取消 fault injection 测试 | `tests/test_fault_injection.py` + `tests/fakes/` 已建立完整 fake harness | 覆盖 429/5xx/timeout/cancel/deadline/health 路径 | **PASS** | `tests/test_fault_injection.py` 通过；`tests/fakes/fake_provider.py` scenarios | 无 | — |
| **CI-001** | Ruff full + mypy + test matrix | CI 已升级到 ruff check + pytest | 无 mypy/pyright 类型检查 | **PARTIAL** | `.github/workflows/` 存在 | 缺少 type checker | 添加 mypy/pyright step |
| **CI-002** | Release checksum/SBOM/signing | `auto_build.py` 有 hash 生成 | 无 SBOM/signing | **PARTIAL** | `auto_build.py` | 缺少 SBOM + signing | 添加 SBOM 生成步骤 |

---

## 四、P2 需求审计矩阵

| ID | 原始需求 | 当前实现 | 状态 |
|---|---|---|---|
| **SUP-001** | 字体 pinned URL + SHA256 | `config/fonts.py` 仍下载远程字体，无 hash 校验 | **FAIL** |
| **DATA-004** | Versioned schema migrations | `repository.py` 有 `_migrate_tags_from_csv` 但无版本化 migration runner | **PARTIAL** |

---

## 五、关键架构偏差（跨需求）

### 偏差 #1：Orchestrator 存在但未被生产代码使用（严重性：P0）

**现象**：`services/generation/orchestrator.py` 的 `GenerationOrchestrator` 类已完整实现（支持 cancellation、deadline、retry policy、health tracking、error taxonomy），全部测试通过。

**但**：生产代码路径 `services/application/generation_controller.py:144` → `services/image_service.generate_image()` 直接调用旧的线性 fallback loop，完全绕过 orchestrator。

**后果**：NET-001（错误分类）、JOB-001（cancellation/deadline）、NET-003（retry policy）在全部生产请求中均不生效。

**证据链断裂点**：
```
GenerationController._run_generation()
  → generate_image()           ← 旧 loop（except Exception, sleep(0.5)）
    → ALL_PROVIDERS[name]()    ← provider 直接调用
      → ValueError/RuntimeError ← 非 ProviderError

应当为：
GenerationController._run_generation()
  → orchestrator.run(token=...) ← 使用 cancellation/deadline
    → provider()                 ← 抛 ProviderError
      → classify decision        ← 正确 fallback 决策
```

### 偏差 #2：Providers 不使用 Error Taxonomy（严重性：P0）

所有 22 个 provider 文件在认证失败时抛 `raise ValueError("需要 XXX API Key...")` 或其他通用异常，而非 `ProviderAuthError`。即使 orchestrator 被接入，`except ProviderError` 也无法捕获这些异常，会落入 `except Exception` → 当作 transient → 重试。

### 偏差 #3：Providers 不使用 Bounded Download（严重性：P0）

所有 provider 使用 `safe_get_image()` 调用 `resp.content`（全量内存加载）。`bounded_download()` 在 `services/generation/downloader.py` 中已实现但零 provider 迁移到它。

---

## 六、成熟度评分（更新）

| 维度 | 计划基线 | 当前实际 | 变化 | 说明 |
|---|---|---|---|---|
| 总体工程成熟度 | 6.3/10 | **6.8/10** | ↑ | 基础设施模块已建，但调用链不完整 |
| 架构 | 7.0/10 | **7.2/10** | ↑ | Application 层已拆分，但 orchestrator 未 wire |
| 数据流与状态管理 | 6.0/10 | **6.5/10** | ↑ | JobQueue + state machine 已建 |
| 网络与 Provider 稳定性 | 5.5/10 | **5.8/10** | ↑ | 模块齐全但 providers 未迁移 |
| 性能 | 6.0/10 | **6.3/10** | ↑ | Translation cache + AsyncLogger 已建 |
| 数据安全 | 5.5/10 | **7.0/10** | ↑↑ | SEC-001 + bounded download 模块 |
| UI/UX | 7.0/10 | **7.0/10** | — | 无明显变化 |
| 测试 | 4.5/10 | **6.5/10** | ↑↑ | 306 测试 + fault injection harness |
| CI/CD | 5.5/10 | **5.5/10** | — | 无实质变化 |

---

## 七、修复优先级排序

### 第一批（P0 — 阻断级，必须立即修复）

1. **Wire orchestrator 到 `generate_image()`**：让 cancellation/deadline/health/retry 在生产路径生效
2. **Provider error mapping 边界层**：在 `generate_image()` 中将 provider 的 `ValueError`/`RuntimeError` 映射为 `ProviderError`
3. **Providers 迁移到 `bounded_download()`**：替换 `_safe_get_image` 调用

### 第二批（P1 — 重要，第一批完成后）

4. Registry 改用 `provider_id` 作为 key
5. `GenerationController` 改用新 `router.py`
6. `AsyncLogger` 设为默认 logger

### 第三批（P2 — 改进型）

7. 字体 hash 校验
8. Versioned migrations
