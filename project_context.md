# project_context.md
> 文字生图工具 · 项目上下文文档  
> 最后更新：2026-03-01

---

## 1. 项目目标

本项目是一个**本地运行的桌面文字生图工具**，基于 Python + Tkinter 构建，
核心目标是：

- 聚合多家免费/付费图像生成 API，提供统一调用界面
- 支持批量变体生成（同一提示词生成多张风格变体）
- 提供短语词库、AI 提示词优化等辅助创作功能
- 配置向导低门槛引导用户快速接入可用的 API 供应商
- 全本地运行，无服务端依赖，历史记录存储于本地 SQLite

---

## 2. 当前进度

| 模块 | 状态 |
|---|---|
| 主窗口 UI | ✅ 完成 |
| 生图调度核心 | ✅ 完成 |
| 历史记录（SQLite） | ✅ 完成 |
| 免费接口（7个） | ✅ 完成并修复批量变体并发问题 |
| 付费接口（3个） | ✅ 完成 |
| 批量变体面板 | ✅ 完成（串行锁修复后稳定） |
| 短语词库面板 | ✅ 完成 |
| 提示词向导（AI优化） | ✅ 完成（DeepSeek V3） |
| 免费配置向导 UI | ✅ 完成（v4，7个接口） |
| 付费配置向导 UI | ✅ 完成 |
| Together AI provider | 🔧 文件已创建，未集成进注册表 |
| Gemini API provider | ❌ 未实现 |
| OpenRouter provider | ❌ 未实现 |
| xAI Grok provider | ❌ 未实现 |
| Groq 提示词加速 | ❌ 未实现（Groq 无图像生成，定位为提示词优化加速） |
| 新供应商配置向导UI | ❌ 未适配 |

---

## 3. 架构图（文本形式）

```
┌─────────────────────────────────────────────────────┐
│                   main.py  入口                      │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │        ui/app.py          │  主窗口（Tkinter）
         │  ┌──────────────────────┐ │
         │  │  batch_panel.py      │ │  批量变体面板
         │  │  phrase_panel.py     │ │  短语词库
         │  │  queue_panel.py      │ │  生成队列
         │  │  viewer.py           │ │  图片查看器
         │  │  wizard_free.py      │ │  免费接口向导
         │  │  wizard_paid.py      │ │  付费接口向导
         │  └──────────────────────┘ │
         └─────────────┬─────────────┘
                       │ 调用
         ┌─────────────▼─────────────┐
         │   services/image_service  │  调度核心
         │   · provider 选择         │
         │   · 自动重试/降级          │
         └──────┬────────────────────┘
                │ 分发
    ┌───────────▼────────────────────────────────┐
    │        services/providers/                  │
    │  FREE:                                      │
    │    siliconflow  pollinations  cloudflare_ai │
    │    modelslab    segmind       huggingface   │
    │    stablehorde                              │
    │  PAID:                                      │
    │    openai_dalle  stability_ai  replicate    │
    │  PENDING:                                   │
    │    together_ai   gemini   openrouter  xai   │
    └─────────────────────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │   services/               │
         │   · prompt_assistant.py   │  DeepSeek V3 提示词优化
         │   · phrase_library.py     │  词库管理
         │   · translation.py        │  翻译
         │   · logger.py             │  日志
         └─────────────┬─────────────┘
                       │
         ┌─────────────▼─────────────┐
         │   config/settings.py      │  配置读写（~/.text_to_image_app/）
         │   data/repository.py      │  SQLite 历史记录
         └───────────────────────────┘
```

---

## 4. 目录结构

```
text_to_image/
├── main.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── data/
│   ├── __init__.py
│   └── repository.py
├── services/
│   ├── __init__.py
│   ├── image_service.py
│   ├── logger.py
│   ├── phrase_library.py
│   ├── prompt_assistant.py
│   ├── translation.py
│   └── providers/
│       ├── __init__.py              ← 注册表（需更新）
│       ├── siliconflow.py
│       ├── pollinations.py
│       ├── cloudflare_ai.py
│       ├── modelslab.py
│       ├── segmind.py
│       ├── huggingface.py
│       ├── stablehorde.py
│       ├── together_ai.py           ← 新建，待集成
│       ├── openai_dalle.py
│       ├── stability_ai.py
│       └── replicate_flux.py
└── ui/
    ├── __init__.py
    ├── app.py
    ├── batch_panel.py
    ├── phrase_panel.py
    ├── prompt_wizard.py
    ├── queue_panel.py
    ├── viewer.py
    ├── wizard_free.py               ← 需扩展新接口
    └── wizard_paid.py               ← 需扩展新接口
```

---

## 5. 核心模块说明

### config/settings.py
- 路径常量：`APP_DIR`, `IMAGES_DIR`, `DB_FILE`, `CONFIG_FILE`, `LOG_FILE`
- `DEFAULT_CONFIG`：所有接口 Key 的默认值字典
- `load_config()` / `save_config(cfg)`：JSON 持久化
- **需新增字段**：`together_key`, `gemini_key`, `openrouter_key`, `xai_key`, `groq_key`, `openrouter_model`

### services/providers/\_\_init\_\_.py
- `FREE_PROVIDERS` dict：供应商名称 → 函数引用
- `PAID_PROVIDERS` dict：同上
- `ALL_PROVIDERS` = FREE + PAID
- `DEFAULT_ORDER`：自动模式的尝试顺序
- **需新增**：together_ai / gemini / openrouter / xai 注册

### services/image_service.py
- 核心调度：接收 prompt/size/seed/cfg，按 DEFAULT_ORDER 逐一尝试
- 每个 provider 函数签名：`(prompt, w, h, seed, cfg, log) → (bytes, source_name)`
- 失败自动降级到下一个 provider

### services/providers/[provider].py（每个文件结构）
```
· 模块级串行锁 + 时间戳（防止批量并发触发速率限制）
· try_xxx(prompt, w, h, seed, cfg, log) → (bytes, str)
· 内部：构建请求 → 重试3次 → 解析 URL/base64 → 下载 → 返回 bytes
· 失败 raise ValueError（调度层捕获后降级）
```

### ui/wizard_free.py / wizard_paid.py
- 继承 `tk.Toplevel`，`grab_set()` 模态
- `_build()` 构建可滚动内容区（Canvas + Scrollbar）
- `_save()` 写入 cfg dict → `save_config()` → 回调 `on_save(cfg)`
- 每个供应商：说明卡片 + API Key 输入框 + 注册链接按钮

---

## 6. API 设计

### Provider 函数接口（统一签名）
```python
def try_xxx(
    prompt: str,          # 英文提示词
    w: int,               # 目标宽度（像素）
    h: int,               # 目标高度（像素）
    seed: int,            # 随机种子
    cfg: dict,            # 全局配置字典（含 API Key 等）
    log: Callable         # 日志回调 log(str)
) -> Tuple[bytes, str]:   # (图片二进制, 来源标识)
```

### 配置字典 cfg 中各供应商字段（现有 + 待新增）
```python
# 现有免费
"sf_key"               # 硅基流动
"hf_token"             # HuggingFace
"stablehorde_key"      # StableHorde
"segmind_key"          # Segmind
"pollinations_enabled" # bool
"cf_account_id"        # Cloudflare
"cf_api_token"         # Cloudflare
"modelslab_key"        # ModelsLab

# 现有付费
"openai_key"           # OpenAI
"stability_key"        # Stability AI
"replicate_key"        # Replicate

# 待新增
"together_key"         # Together AI（FLUX Free免费端点）
"gemini_key"           # Google Gemini API（500次/天免费）
"openrouter_key"       # OpenRouter（部分模型免费）
"openrouter_model"     # OpenRouter 选用模型
"xai_key"              # xAI Grok（注册送$25额度）

# 通用
"variant_quality"      # "high" | "standard"
"default_provider"     # 接口选择
"default_size"         # 默认尺寸
```

### 各新供应商 API 端点
| 供应商 | 端点 | 认证 | 响应格式 |
|---|---|---|---|
| Together AI | `POST https://api.together.xyz/v1/images/generations` | Bearer Token | `{data:[{url}]}` |
| Gemini API | `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent` | x-goog-api-key | `{candidates[0].content.parts[].inlineData.data}` base64 |
| OpenRouter | `POST https://openrouter.ai/api/v1/chat/completions` | Bearer Token | `{choices[0].message.content[].image_url.url}` |
| xAI Grok | `POST https://api.x.ai/v1/images/generations` | Bearer Token | `{data:[{url}]}` OpenAI 兼容 |
| Groq | `POST https://api.groq.com/openai/v1/chat/completions` | Bearer Token | 仅文本，用于提示词优化 |

---

## 7. 未完成任务

### 高优先级
- [ ] **Together AI provider 集成**：`together_ai.py` 已写好，需注册到 `__init__.py`，settings 新增 `together_key`，向导 UI 添加配置卡片
- [ ] **Gemini API provider**：新建 `gemini.py`，HTTP REST 调用，解析 `inlineData.data` base64，免费500次/天
- [ ] **OpenRouter provider**：新建 `openrouter.py`，`/chat/completions` + `modalities:["image"]`，解析 content 中的 image_url
- [ ] **xAI Grok provider**：新建 `xai_grok.py`，OpenAI 兼容格式，`grok-imagine-image` 模型，注册送$25

### 中优先级
- [ ] **wizard_free.py 扩展**：新增 Together AI + Gemini API 两个配置卡片（均有免费额度）
- [ ] **wizard_paid.py 扩展**：新增 OpenRouter + xAI Grok 两个配置卡片（付费但送初始额度）
- [ ] **settings.py 更新**：`DEFAULT_CONFIG` 补全 5 个新字段
- [ ] **providers/\_\_init\_\_.py 更新**：注册 4 个新供应商到对应 dict

### 低优先级
- [ ] **Groq 提示词加速**：Groq 无文生图能力，考虑替换 `prompt_assistant.py` 中的 DeepSeek 调用，用 Groq LLaMA 加速提示词扩写（速度从 2~5s 降至 <0.5s）
- [ ] **OpenRouter 免费模型列表**：在向导中展示当前可用的零成本图像模型（模型列表动态变化）

---

## 8. 后续计划

### 阶段 A — 完成新供应商集成（当前任务）
1. 写 `gemini.py`、`openrouter.py`、`xai_grok.py`
2. 更新 `settings.py`（5个新 key）
3. 更新 `providers/__init__.py`（注册）
4. 更新 `wizard_free.py`（Gemini + Together 卡片）
5. 更新 `wizard_paid.py`（OpenRouter + xAI 卡片）

### 阶段 B — 稳定性与体验
- 为新 provider 补充串行锁（防批量并发）
- 统一错误信息中文化，提升用户友好度
- Groq 接入提示词优化加速路径

### 阶段 C — 扩展功能
- 图生图（img2img）支持（xAI Grok/Gemini 均支持）
- 多语言提示词自动翻译到英文后再生图
- 收藏夹与标签系统

---

*文档由 Claude 自动生成，反映截至 2026-03-01 的项目状态。*
