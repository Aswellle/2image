# BEHAVIOR_DEVIATION_REPORT.md — 行为偏差检测报告

> **审计日期**：2026-09-16
> **检测重点**：需求与代码语义不一致、看起来实现了但实际未生效、控制流偏差

---

## 一、偏差分级定义

| 级别 | 含义 |
|---|---|
| **CRITICAL** | 功能模块已编写但完全未接入生产代码路径；用户可见行为无任何变化 |
| **MAJOR** | 功能部分生效但关键分支有错误；特定场景下行为与需求相反 |
| **MINOR** | 功能基本生效但边缘情况不符；性能或次要行为偏差 |

---

## 二、CRITICAL 级偏差

### B-001：Orchestrator 完全未接入生产路径

| 项 | 内容 |
|---|---|
| **需求** | NET-001/JOB-001：Provider 错误分类、任务 deadline、cancellation |
| **代码存在** | `services/generation/orchestrator.py` — `GenerationOrchestrator` 类，100% 功能完整，测试通过 |
| **实际行为** | 生产请求走 `image_service.generate_image()` → 旧线性 loop，orchestrator 从未被调用 |
| **偏差类型** | **看起来实现了，但实际没有生效** |
| **证据** | `services/application/generation_controller.py:144` 直接调用 `generate_image(prompt, ...)` 无 token 参数；`generate_image()` 内部 `for name in order` + `except Exception` 旧逻辑 |
| **影响范围** | 所有生成请求均受影响 |
| **修复方案** | 将 `generate_image()` 重构为 orchestrator 的 façade，或让 `GenerationController` 直接调用 orchestrator |

**控制流对比**：
```
【当前实际】
用户点击生成
  → App._gen() → GenerationController.generate()
    → _run_generation() [daemon thread]
      → generate_image(prompt, w, h, seed, cfg, provider_order)
        → for name in order:
            try: fn(prompt, w, h, seed, cfg, log_cb)
            except Exception:  ← 捕获所有错误
              errors.append(...)
              time.sleep(0.5)  ← 固定 0.5s 延迟
        → raise RuntimeError

【期望行为】
用户点击生成
  → App._gen() → GenerationController.generate()
    → _run_generation() [daemon thread, 持有 CancellationToken]
      → orchestrator.run(prompt, ..., token=token, deadline=...)
        → for provider_id in order:
            token.throw_if_cancelled()     ← 立即响应取消
            health.is_available            ← 跳过不健康 provider
            for attempt in range(max):
              try: fn(...)
              except ProviderAuthError:    ← 认证失败，不重试，跳下一个
              except ProviderRateLimitError: ← backoff + retry
              except ProviderTransientError: ← retry with backoff
              except Exception:            ← 未知 → 映射为 transient
```

---

### B-002：Providers 抛非 ProviderError 异常，error taxonomy 形同虚设

| 项 | 内容 |
|---|---|
| **需求** | NET-001：401 → `ProviderAuthError`（不重试）；402 → `ProviderQuotaError` |
| **代码存在** | `services/generation/errors.py` 定义了完整 taxonomy；`adapter.py` 有 `map_http_error()` |
| **实际行为** | 所有 provider 在认证失败时抛 `raise ValueError("需要 OpenAI API Key...")` 或 `RuntimeError` |
| **偏差类型** | **需求与代码语义不一致** |
| **证据** | `services/providers/openai_image.py:89` → `raise ValueError("需要 OpenAI API Key...")`；`services/providers/siliconflow.py:140` → `raise ValueError("所有硅基流动免费模型均失败")` |
| **影响** | 即使 orchestrator 被接入，401 错误也会落入 `except Exception`（被当作 transient 重试），而不是 `except ProviderAuthError`（立即停止该 provider） |

**偏差示例**：
```python
# 需求：401 → 不重试当前 Provider，立即 fallback
# 实际：
#   provider 抛 ValueError("需要 OpenAI API Key")
#   orchestrator 的 except ProviderError 不捕获
#   落入 except Exception → mapped = ProviderTransientError(...)
#   → retry with backoff  ← 错误行为！浪费时间和请求
```

**修复方案**：在 `generate_image()` 中添加异常映射边界层（wrapper），将常见 `ValueError`/`RuntimeError` 按消息关键词/上下文映射为对应的 `ProviderError`。

---

### B-003：图片下载无内存上限（全量加载）

| 项 | 内容 |
|---|---|
| **需求** | NET-002：bounded streaming download，25MB 上限，Content-Type 校验 |
| **代码存在** | `services/generation/downloader.py` — `bounded_download()` 完整实现 |
| **实际行为** | 所有 17 个 provider 调用 `safe_get_image(url)` → `resp.content`（全量加载内存，无大小限制） |
| **偏差类型** | **看起来实现了，但实际没有生效** |
| **证据** | `services/providers/siliconflow.py:137` → `data = _safe_get_image(img_url, timeout=60)`；`services/providers/_net.py:94` → `return resp.content` |
| **影响** | 大图片/异常响应可耗尽内存；Download 路径不受 deadline/cancellation 约束 |

---

### B-004：Cancellation Token 在 UI 层不可用

| 项 | 内容 |
|---|---|
| **需求** | JOB-001：点击停止后 500ms 内任务状态变为"正在停止" |
| **代码存在** | `cancellation.py` — `CancellationToken` 完整实现；`tests/test_fault_injection.py` 验证通过 |
| **实际行为** | `GenerationController._run_generation()` 不创建也不传递 token；无机制可中断 `generate_image()` 中的 HTTP 请求或 sleep |
| **偏差类型** | **看起来实现了，但实际没有生效** |
| **证据** | `generation_controller.py:119-159` 整个函数无 `CancellationToken` 引用 |
| **影响** | 用户点击停止无效；只能等待所有 provider 全部失败或成功 |

---

## 三、MAJOR 级偏差

### B-005：Provider Registry 仍用 display name 作 key

| 项 | 内容 |
|---|---|
| **需求** | ROUTE-001：stable `provider_id` 用于路由，display name 仅用于 UI |
| **代码存在** | `provider_manifest.py` 有 `ProviderManifest(id="siliconflow")` + `LEGACY_NAME_TO_ID` |
| **实际行为** | `ALL_PROVIDERS` 字典 key 是 `info["name"]`（如 `"硅基流动 SiliconFlow (★推荐)"`），不是 `info["id"]` |
| **偏差类型** | 需求与代码语义不一致 |
| **证据** | `services/providers/__init__.py:61` → `_for_loop_registry[category][info["name"]] = try_fn` |
| **影响** | 改名/多语言会导致路由失效；配置迁移复杂 |

---

### B-006：Router 健康感知版本未接入

| 项 | 内容 |
|---|---|
| **需求** | ROUTE-003：health/latency/cost/quota scoring router |
| **代码存在** | `services/generation/router.py` — `Router` 类有 health-aware scoring |
| **实际行为** | `generation_controller.py:16` → `from services.smart_router import get_provider_order`（旧 router） |
| **偏差类型** | 看起来实现了，但实际没有生效 |
| **影响** | 路由决策不使用 health 数据，可能持续撞击已失效 provider |

---

### B-007：DEFAULT_ORDER 依赖 pkgutil 发现顺序

| 项 | 内容 |
|---|---|
| **需求** | ROUTE-002：manifest-defined order，不依赖发现顺序 |
| **代码存在** | `provider_manifest.py` 有显式 `FREE_PROVIDER_ORDER` 列表 |
| **实际行为** | `providers/__init__.py:70` → `DEFAULT_ORDER = list(FREE_PROVIDERS.keys())`（依赖 dict 插入顺序 = pkgutil 发现顺序） |
| **偏差类型** | 需求与代码语义不一致 |

---

## 四、MINOR 级偏差

### B-008：Translation 全局锁强制串行化

| 项 | 内容 |
|---|---|
| **需求** | PERF-001：translation cache + background worker，不阻塞批量 |
| **实际行为** | `_TRANS_LOCK` + `time.sleep(_MIN_INTERVAL)` 强制每 1.5s 一次翻译 |
| **影响** | 批量中文 prompt 被强制串行节流 |

---

### B-009：Logger 默认为同步 I/O

| 项 | 内容 |
|---|---|
| **需求** | PERF-002：QueueHandler + RotatingFileHandler |
| **实际行为** | `log_to_file()` 仍是默认（同步 open/write/rotate）；`AsyncLogger` 存在但需手动 setup |
| **影响** | 高频生成时同步 I/O 仍是瓶颈 |

---

### B-010：FTS5 表存在但默认搜索可能不走 FTS

| 项 | 内容 |
|---|---|
| **需求** | DATA-003：FTS5 全文搜索 + keyset pagination |
| **实际行为** | `get_all_entries()`（OFFSET + LIKE）与 `get_entries_keyset()` 并存 |
| **影响** | 如 UI 默认调用旧接口，性能随历史增长退化 |

---

## 五、无偏差确认（PASS 项确认）

| ID | 需求 | 验证结果 |
|---|---|---|
| SEC-001 | 安全文件删除 | `delete_entry()` → `safe_delete_file()` 路径 containment + symlink 拒绝 ✓ |
| DATA-001 | JSON 迁移事务 | `migrate_from_json()` transaction + 失败保留原文件 ✓ |
| DATA-002 | clear_all_entries 文件处理 | `remove_files=True` 参数 + orphan report ✓ |
| PERF-003 | UUID 文件名 | `save_image_file()` UUID + atomic rename ✓ |
| TEST-002 | Fault injection harness | `tests/fakes/` + `test_fault_injection.py` 完整 ✓ |
| — | `bounded_download()` 模块 | 功能完整，有 redirect SSRF 验证 ✓ |
| — | `AsyncLogger` 模块 | QueueHandler + RotatingFileHandler 完整 ✓ |
| — | `JobQueue` state machine | `JobState` 枚举 + 合法转换表 ✓ |
| — | `ProviderHealth` 熔断 | HEALTHY→DEGRADED→OPEN→HALF_OPEN 状态机 ✓ |

---

## 六、偏差根因分析

### 核心问题：基础设施已建，调用链未通

本次审计最突出的模式是：**所有计划中的基础设施模块（orchestrator、errors、cancellation、retry_policy、health、downloader、router）均已在 `services/generation/` 下实现，但 providers 层和 service 入口层未迁移到新接口**。

根因是开发代理按"添加新模块"模式工作，而未重构旧的集成点。结果是：
- 新模块有完整的独立测试（306 测试全通过）
- 旧生产代码路径不受影响
- 用户可见行为无任何变化

### 必要的集成重构

需要修改的关键集成点只有 4 个：

1. **`services/image_service.py:generate_image()`** — 改为使用 orchestrator + provider error mapping
2. **`services/providers/__init__.py:61`** — registry 用 `info["id"]` 作 key
3. **`services/application/generation_controller.py:144`** — 传递 CancellationToken 给 generate_image
4. **Provider 文件中的 `_safe_get_image()` 调用** — 改为 `bounded_download()`

完成这些集成后，全部 P0 功能将在生产路径生效。
