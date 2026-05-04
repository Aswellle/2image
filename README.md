# 2image — 文生图 / 图生图 聚合工具

> 聚合全球最优质的文生图（Text-to-Image）和图生图（Image-to-Image）API，
> 统一调用界面，本地 Tkinter 桌面应用，支持批量变体、提示词优化、历史管理。

**GitHub**: [github.com/Aswellle/2image](https://github.com/Aswellle/2image)

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **多 Provider 聚合** | 9+ 文生图引擎，自动竞速降级，优先级可配置 |
| **图生图（img2img）** | 支持以参考图为基础生成变体（部分 Provider） |
| **批量变体** | 同一提示词并行/串行生成多张风格变体 |
| **提示词助手** | DeepSeek V3 自动扩写优化中英文提示词 |
| **历史管理** | SQLite 本地持久化，支持标签、收藏、搜索 |
| **免费优先** | 默认按免费额度 Provider 顺序尝试，无需 API Key 也能跑 |
| **零依赖发行** | 纯 Python，无须用户安装任何运行时 |

---

## 支持的 Provider

### 免费 / 低成本（推荐优先）

| Provider | 模型 | 费用 | img2img | 特点 |
|----------|------|------|---------|------|
| **Google Gemini 2.5 Flash** | gemini-2.5-flash-preview-04-17 | 免费 500次/天 | 否 | 速度快，质量好，Google AI Studio 注册即用 |
| **Google Gemini 3.1 Flash** | gemini-3.1-flash-image-preview | $0.0000005/M token | 否 | 最新模型，质量更高 |
| **Together AI FLUX.1 Free** | black-forest-labs/FLUX.1-schnell-Free | 免费（限速） | 否 | FLUX 嫡系开源模型，质量出色 |
| **Pollinations.AI** | pollinations/default | 完全免费，无需 Key | **是** | 零配置开箱即用 |
| **Cloudflare Workers AI** | @cf/stable-diffusion-xl-base-1.0 | 免费 10,000 次/天 | 否 | 全球 CDN 加速，无需注册 |
| **SiliconFlow** | FLUX.1-pro 等 | 低价（注册送额度） | 否 | 国内可访问，稳定性好 |
| **ModelsLab** | 模型多样 | 免费 100次/天 | **是** | 支持 img2img |
| **OpenRouter** | 聚合 16+ 图像模型 | 部分免费 | **是** | 统一入口，可选免费模型 |
| **MiniMax M2.5** | minimax-m2.5:free | 免费 | 否 | 超长上下文，OpenRouter 可访问 |
| **Segmind** | 多模型 | 注册送 $5 | **是** | 支持图生图 |

### 付费 / 高质量

| Provider | 模型 | 参考价格 | img2img | 特点 |
|----------|------|---------|---------|------|
| **OpenAI DALL-E 3** | dall-e-3 | $0.04~0.12/张 | 否 | 行业标杆，质量最优 |
| **Stability AI** | core / sd3 | 按张计费 | **是** | SD3 嫡系，画风丰富 |
| **Replicate FLUX.1 Pro** | flux-1.1-pro | 较贵 | 否 | FLUX 最强闭源版本 |
| **xAI Grok Imagine** | grok-2-image-1212 | $0.07/张 | 否 | Aurora 模型，注册送 $25 |

### 计划接入的高质量 Provider

| Provider | 接入状态 | img2img | 备注 |
|----------|----------|---------|------|
| **Ideogram V2** | ✅ 已接入 | ❌ 不支持 | 文字渲染质量最佳，API v2 仅文生图 |
| **Leonardo.ai** | ✅ 已接入 | ✅ **已支持** | 游戏资产风格见长，每日免费 Credits |
| **Recraft V3** | ❌ 已下线 | ❌ | 官方已关闭公共 API（2025年），代码保留占位 |

---

## Provider 对比矩阵（2026-05）

```
质量 ↑                    免费/低价 ◀──────────────▶ 付费
     │
     │  Pollinations.ai    Gemini 2.5 Flash  Together FLUX.Free
     │  Cloudflare AI      Gemini 3.1 Flash   SiliconFlow
     │  ModelsLab          OpenRouter        Segmind
     │                     MiniMax Free
     │
     ▼  (质量边界)
  Ideogram  Leonardo.ai   Stability AI   DALL-E 3  xAI Grok
  Recraft V3              Replicate FLUX  SD3
```

---

## 系统要求

- Python 3.9+
- Windows / macOS / Linux（桌面环境）
- 无须安装任何运行时（已打包版本为单 EXE）

---

## 快速开始

### 方式一：直接运行源码

```bash
# 克隆项目
git clone https://github.com/Aswellle/2image.git
cd 2image

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 方式二：使用打包版本（Windows）

下载最新 Release 中的 `.exe` 安装包，双击安装即可。

---

## 配置 API Key

首次启动会自动弹出配置向导，也可手动配置：

1. 打开菜单 → 🔑 API 配置 → 🆓 免费接口配置（或 💎 付费接口配置）
2. 填入对应 Provider 的 API Key
3. 点击保存

**推荐优先配置（零成本）：**
- [Google AI Studio](https://aistudio.google.com/) → Gemini 2.5 Flash（免费 500次/天）
- [Pollinations.AI](https://pollinations.ai/) → 无需 Key，直接可用
- [Together AI](https://api.together.ai/) → FLUX.1 Free（免费限速）

---

## 项目结构

```
2image/
├── main.py                     # 程序入口（DPI感知 → 建库 → 启动UI）
├── config/
│   └── settings.py             # 路径常量 + DEFAULT_CONFIG（含所有 API Key 字段）
├── data/
│   └── repository.py           # SQLite 历史记录层（增删改查 + 迁移 + 统计）
├── services/
│   ├── image_service.py        # 调度核心：竞速降级循环
│   ├── prompt_assistant.py     # DeepSeek V3 提示词扩写
│   ├── translation.py          # 中译英
│   ├── logger.py               # 调试日志
│   ├── phrase_library.py       # 短语词库管理
│   ├── i18n.py                 # 多语言支持（zh_CN / en_US）
│   ├── locales/               # i18n locale 文件
│   │   ├── zh_CN.json
│   │   └── en_US.json
│   └── providers/             # 各 Provider 实现
│       ├── __init__.py         # 注册表（FREE_PROVIDERS / PAID_PROVIDERS）
│       ├── gemini.py           # Google Gemini 2.5 Flash Image
│       ├── pollinations.py     # Pollinations.AI（支持 img2img）
│       ├── cloudflare_ai.py    # Cloudflare Workers AI
│       ├── modelslab.py        # ModelsLab
│       ├── siliconflow.py      # 硅基流动
│       ├── openrouter.py       # OpenRouter 聚合
│       ├── together_ai.py      # Together AI FLUX Free
│       ├── openai_dalle.py     # OpenAI DALL-E 3
│       ├── stability_ai.py    # Stability AI
│       ├── replicate_flux.py   # Replicate FLUX
│       └── xai_grok.py         # xAI Grok Imagine
└── ui/
    ├── app.py                  # 主窗口（Tkinter）
    ├── wizard_free.py          # 免费接口配置向导
    ├── wizard_paid.py          # 付费接口配置向导
    ├── batch_panel.py          # 批量变体面板
    ├── phrase_panel.py         # 短语词库面板
    ├── queue_panel.py          # 生成队列面板
    ├── prompt_wizard.py        # AI 提示词助手面板
    └── viewer.py               # 图片查看器
```

---

## 核心逻辑

### Provider 调度（竞速降级）

```
用户请求
  │
  ▼
image_service.generate_image()
  │
  ├─▶ 遍历 provider_order（优先级顺序）
  │     ├─ 尝试 Provider A → 成功 → 返回
  │     ├─ 失败（速率限制/网络错误）→ 等待 0.5s → 尝试 Provider B
  │     ├─ Provider B 失败 → 等待 0.5s → 尝试 Provider C
  │     └─ ... 依次类推 ...
  │
  ▼
所有 Provider 均失败 → 抛出 RuntimeError（已收集所有错误信息）
```

### 提示词优化管道

```
用户输入（中文） → DeepSeek V3 扩写 → 英文优化提示词
                      │
                      ▼
              image_service.generate_image()
                      │
                      ▼
               Provider 竞速降级
                      │
                      ▼
                   返回图片
```

### img2img（图生图）流程（支持 Provider）

```
用户上传参考图 + 输入提示词
        │
        ▼
  编码为 base64 → 发送给支持的 Provider
        │
        ├─▶ Pollinations.AI（直接支持，零配置）
        ├─▶ ModelsLab（img2img 模式）
        ├─▶ Leonardo.ai（init_image + prompt，v1.1 新增）
        ├─▶ Stability AI（image-to-image，v1.1 新增）
        └─▶ OpenRouter（部分模型支持）
```

---

## 技术亮点

1. **串行锁机制**：每个 Provider 文件内含 `threading.Lock()` + `_LAST_DONE[0]` 时间戳，防止批量并发触发速率限制
2. **自动重试 + 指数退避**：每个 Provider 失败重试 3 次，等待时间 3×attempt 秒
3. **DPI 感知**：Windows 下调用 `SetProcessDpiAwareness(1)` 避免界面模糊
4. **SQLite 迁移**：从 JSON 历史记录平滑迁移到 SQLite，自动补列兼容旧库
5. **Tkinter 竞态修复**：`_hist_gen` 代号机制防止后台线程在 UI 更新期间错误赋值到已销毁的 widget

---

## 开发路线图

### v1.2（当前版本 — 2026-05-04）
- [x] **Txt2ImgPanel 历史写入**：生成完成后调用 `add_entry()` 写入 SQLite
- [x] **Img2ImgPanel 历史写入**：生成完成后调用 `add_entry(is_img2img=True)` 写入 SQLite，含参考图标记
- [x] **HistoryPanel 删除修复**：`delete_entry()` 实际删除 SQLite 记录（`remove_file=False` 保留图片）
- [x] **HistoryPanel 双击打开**：`image_path` 列名修正 + Windows `os.startfile()` 系统图片查看器
- [x] **repository 线程安全确认**：`sqlite3.connect(..., check_same_thread=False)` 支持多线程安全写入

### v1.1（2026-05-04）
- [x] **Img2ImgPanel._save() 修复**：保存生成结果而非参考图
- [x] **图生图 UI 增强**：strength 强度滑块 + provider 选择下拉框 + 强度预设快捷按钮
- [x] **Leonardo.ai img2img 接入**：完整实现 `try_leonardo_img2img()`
- [x] **Stability AI img2img 接入**：完整实现 `try_stability_img2img()`
- [x] **统一 img2img 抽象层**：`IMG2IMG_PROVIDERS` 注册表 + strength 参数 + 竞速降级
- [x] **Recraft API 探测**：确认官方已下线（2025年），保留占位代码
- [x] **多语言 i18n 架构**：`services/locales/` + zh_CN/en_US + 语言切换选择器
- [x] Ideogram API 接入

### v2.0（中长期）
- [x] **完整 i18n UI 文本外化**（v2.0 P1）：所有中文硬编码 → `get_text()` / `format()`，新增插值 API，zh_CN/en_US 双语言完整覆盖
- [ ] ControlNet / LoRA 风格迁移（仅本地 Provider）

---

## 相关项目

- [claude-code-best-win](https://github.com/Aswellle/claude-code-best-win) — Claude Code CLI Windows 独立打包方案
- [text_to_iamge_app](https://github.com/Aswellle/text_to_image_app) — 本项目的前身，Tkinter 原型版本

---

## 免责声明

本项目仅供个人学习研究使用。Provider 的使用须遵守各平台的服务条款，生成的图片版权归属用户。请勿将本工具用于任何商业或违法用途。

---

*文档更新：2026-05-04*
