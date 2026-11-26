<div align="center">

<img src="https://raw.githubusercontent.com/Aswellle/2image/main/assets/logo.png" alt="2image" width="200" />

<h1>2image</h1>
<p><strong>桌面 AI 图片生成器 · 内置 23 个免费、付费及商用生图服务</strong></p>

<p>
  一个工具，接入市面上主流的免费、付费与商业生图 API，让创作门槛降到最低。<br/>
  输入图像描述，一键生成 —— 无需编程，无需搭建，数据完全本地。
</p>

[![CI](https://github.com/Aswellle/2image/actions/workflows/ci.yml/badge.svg)](https://github.com/Aswellle/2image/actions)
[![下载量](https://img.shields.io/github/downloads/Aswellle/2image/total)](https://github.com/Aswellle/2image/releases)
[![Release](https://img.shields.io/github/v/release/Aswellle/2image)](https://github.com/Aswellle/2image/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4)](https://github.com/Aswellle/2image/releases/latest)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

<p>
  <a href="https://github.com/Aswellle/2image/releases/latest"><b>📥 立即下载</b></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/Aswellle/2image/issues">🐛 反馈问题</a>
  &nbsp;·&nbsp;
  <a href="#-快速上手">📖 使用文档</a>
</p>

<p>
  <a href="https://github.com/Aswellle/2image/blob/main/README.en.md">English</a>
  &nbsp;|&nbsp;
  <a href="#中文">中文</a>
</p>

</div>

---

<a id="中文"></a>
## 🎨 什么是 2image？

**2image** 是一款运行在 Windows 桌面的 AI 图片生成工具。

只需描述你想要的画面，2image 就会自动调用最合适的生图接口为你生成——无需任何编程基础，无需搭建服务，不用担心数据外泄，所有内容都保存在你自己的电脑上。

> "一个工具，接入市面上主流的免费、付费与商业生图 API，让创作门槛降到最低。"

---

## ✨ 核心亮点

### 🎯 一个界面，23 个可选接口
主界面可直接选择全部 23 个生图服务（12 个免费 + 6 个付费 + 5 个商业），覆盖 Pollinations、硅基流动、Gemini Nano Banana、通义万相、Bria AI、OpenAI GPT-Image、Black Forest Labs FLUX、Ideogram、fal.ai FLUX.2、Recraft、MiniMax H3 与豆包 Seedream 等。**可先使用无需 Key 的服务，再按需配置免费、付费或商业 API**；所有接口都能在「🆓 免费配置」或「💎 付费接口配置」向导里填写 Key 与选择模型，无需手改配置文件。生成会按当前优先序列依次尝试可用服务。

### 🆓 零成本起步
**Pollinations.AI 无需注册即可体验**，开箱即用；匿名调用仍受频率限制。注册几个提供免费额度的服务后，还能解锁更多高质量模型，覆盖日常创作需求。

### 🧠 智能路由，一键最优
配置可用服务后，输入「banner 设计」会优先排列 Ideogram（擅长文字入图）；输入「电商产品图」会优先排列 fal.ai FLUX.2 Pro（写实高清）。不同场景按优先序列尝试适合的模型，也可手动指定接口。单图、批量变体与顺序队列的「自动」模式共用同一套路由；提示词助手模板会优先按模板场景排序。付费与商业接口默认不参与「自动」模式，可在「💎 付费接口配置 → 自动路由与付费预算」中开启，并设置每日美元预算上限；开启后，没有匹配场景的提示词也会在免费接口之后尝试付费接口。

### 🖼 图生图（img2img）
上传参考图后，程序会只显示已接入且已有配置入口的图生图接口，当前共 8 个：Stability AI（「变化强度」滑杆控制改动幅度）、Nano Banana Pro、Black Forest Labs FLUX、Gemini Nano Banana 系列、OpenAI GPT-Image、豆包 Seedream、fal.ai FLUX.2 与 MiniMax H3（原生参考图编辑）。批量变体和顺序队列会在图生图模式下自动锁定，避免参考图被忽略。

### 🎲 批量变体，一次生成 6 张
同一提示词自动生成多张不同种子的变体，对比挑选最满意的一张，极大提升创作效率。支持标准模式与高质量模式（更高步数 / 更好模型）。

### 📋 顺序队列，离开也能跑
将多个任务加入队列，让程序按顺序自动生成。可随时暂停、继续或停止，中途新增任务也会自动纳入当前轮次。

### 🔧 AI 提示词优化
内置提示词优化向导，可将模糊想法整理成高质量英文提示词。填写硅基流动 Key 后会按 DeepSeek-V3.2、V3.1-Terminus 与 Qwen3-8B 候选顺序自动降级尝试；也可填写 DeepSeek 官方 API Key，手动选择质量优先的 Pro（deepseek-v4-pro）或速度优先的 Flash（deepseek-flash）预设。
向导支持一次生成 3 个候选并用 ‹ / › 或方向键切换，生成历史跨会话保存；模板卡片支持键盘导航，一键重试沿用上次参数，重新生成前会保护手动编辑过的内容。

### 📚 提示词词库
内置 45 条词条、7 个分类，并支持自定义分类与词条。词条中的 `{{变量}}` 会在追加时弹窗逐项填写；自定义词条可编写说明并随导出迁移；词库支持 JSON 导入 / 导出与跨机器合并。搜索覆盖词条及中英双语说明，结果标注归属分类；词条按使用频次置顶，悬浮说明会展示该词条在历史生成记录中的使用情况。历史卡片还可一键把提示词沉淀为「⭐ 我的词条」。

### 📊 统计看板
提供全年热力图、接口使用分布、标签热度 Top-10，以及收藏率、近 7 天趋势、连续生成天数和成本估算（历史估算 + 今日台账 + 预算进度），并可一键导出多分区 CSV 与 1280×900 分享图。

### 🀄 中文原生支持
直接输入中文描述，程序自动调用 MyMemory 翻译为英文再送入生图接口——无需手动翻译，无需额外配置。

### 🔒 数据完全本地
所有图片、历史记录、配置均保存在你的电脑（`~/2image/`），不上传任何用户数据。

---

## 🚀 快速上手

### 方式一：下载安装包（推荐）

1. 前往 [Releases 页面](https://github.com/Aswellle/2image/releases/latest)
2. 下载 `2image-setup-v*.exe`（安装包）或 `2image-portable-v*.exe`（便携版）
3. 运行，首次启动会弹出配置向导
4. 不配置任何 Key 也可直接生成（Pollinations.AI 免注册，匿名调用受频率限制）

### 方式二：从源码运行

**运行环境**

- **系统**：Windows 10 / 11（64 位）；GUI 基于 Tkinter，依赖桌面环境。
- **Python**：3.11 或 3.12（CI 在 3.11 / 3.12 双版本验证；3.11 为最低支持版本，3.13 尚未验证）。Tkinter 随 Python 官方安装包提供，安装时保持默认的 `tcl/tk` 组件勾选即可。
- **依赖**：仅 `Pillow` 与 `requests`，由 `requirements.txt` 自动安装；无需 Node.js、数据库或浏览器等外部服务。开发/测试额外需要 `pytest`、`pytest-cov`、`ruff`（同样在 `requirements.txt` 中）。
- **磁盘**：源码与依赖约 100 MB；生成的图片保存在 `~/2image/images/`。

```bash
git clone https://github.com/Aswellle/2image.git
cd 2image
py -3.11 -m venv .venv          # 3.12 亦可；也可跳过虚拟环境
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

首次启动会创建 `~/2image/` 数据目录；不配置任何 Key 也可直接生成（Pollinations.AI 免注册，匿名调用受频率限制）。

---

## 🌐 支持的生图接口

### 免费接口（推荐优先配置）

| 接口 | 模型 | 免费额度 | 是否需要 Key |
|---|---|---|---|
| **Pollinations.AI** | FLUX · Turbo · SANA（匿名层实测名单，高质量档含 GPTImage） | 无固定日配额，匿名调用有频率限制 | ❌ 无需注册 |
| **硅基流动 SiliconFlow** ⭐ | FLUX.1 · SDXL · Kolors · SDXL-Lightning / Turbo | 注册送免费额度 | ✅ 免费注册 |
| **Google Gemini** | Nano Banana 系列（2.1 默认，2 / 2 Lite / Pro 可切换） | 以 Google AI Studio 当前免费额度为准 | ✅ 免费注册 |
| **通义万相 Qwen-Image** | wan2.6-t2i（默认，同步协议）· wan2.5-t2i（旧异步协议） | 阿里云新用户免费额度 | ✅ 免费注册 |
| **Bria AI Fibo** | Fibo | 注册送 1000 次调用 | ✅ 免费注册 |
| **Cloudflare Workers AI** | FLUX.1-schnell · FLUX.2-dev（高质量档）· SDXL | 1 万 Neurons/天（约 10–20 张高分辨率图） | ✅ 免费注册 |
| **HuggingFace** | Stable Diffusion 3 Medium | 免费推理 API | ✅ 免费注册 |
| **StableHorde** | DreamShaper XL · Stable Diffusion | 匿名可用 | ❌ 可选注册 |
| **ModelsLab** | FLUX · SDXL · Realistic Vision · SD 1.5 | 100 次/天 | ✅ 免费注册 |
| **Together AI** | FLUX.1-schnell（官方免费端点） | 免费可用性请以 Together 控制台为准 | ✅ 免费注册 |
| **OpenRouter** | 统一 Image API（默认 gemini-3.1-flash-image） | 按所选模型计费，免费可用性请以模型页为准 | ✅ 免费注册 |
| **Segmind** | FLUX Schnell · SDXL · SD3 Medium | 注册送 $5 额度 | ✅ 免费注册 |

### 付费接口

| 接口 | 特点 | 定价参考 |
|---|---|---|
| **💎 OpenAI GPT-Image** | gpt-image-2 默认（2.5 / 2.6 Flare·Sunburst 可选），文生图与参考图编辑 | 按次计费 |
| **💎 Nano Banana Pro** | Gemini 3 Pro Image，高画质文生图与图生图，复用 Gemini Key | 按量计费 |
| **💎 Black Forest Labs FLUX** | 官方 FLUX.2 单端点文生图与图生图（flux-2-pro 默认） | 按量计费 |
| **💎 Stability AI** | SD3.5-large / core，支持图生图与「变化强度」控制 | 按积分计费 |
| **💎 Replicate FLUX** | black-forest-labs/flux-2-pro 官方托管 | 按次计费 |
| **💎 xAI Grok Imagine** | grok-imagine-image-2.0，接入宽高比与分辨率控制 | 按次计费 |

### 商业变现接口

以下服务与免费 / 付费接口同级出现在主界面下拉菜单，并可在「💎 付费接口配置」中填写 Key、选择模型，无需自行补配置入口。

| 接口 | 特点 |
|---|---|
| **Ideogram v4** | 文字入图首选，Banner / LOGO / 海报中文字可读 |
| **fal.ai FLUX.2 Pro** | 文生图 `fal-ai/flux-2-pro` + 指令式编辑 `/edit`，最高 4MP 超清写实，产品图 / 人像首选 |
| **Recraft v4.1** | 设计 / 插画 / 矢量风格，品牌 VI 利器（默认 recraftv4_1，可切回 v3，支持三种风格切换） |
| **MiniMax H3 Image** | H3-Image / H3-Image-Highspeed 文生图 + 参考图编辑（`/v1/images/edits`），最高 20MP |
| **豆包 Seedream（火山引擎）** | Seedream 5.5（默认）/ 5.0 Pro / 5.0 Flash 文生图 + 原生参考图编辑 |

---

## 🏗 架构概览

```
main.py
  └─ config/          配置层：路径 · 主题 · 国际化 · 字体 · 模型目录
  └─ data/            数据层：SQLite 历史 / 标签 / 统计（WAL 模式，线程安全）
  └─ services/        服务层
  │   ├─ application/ App 控制器：生成 · 菜单 · 设置
  │   ├─ generation/  编排 · 重试 · 预算 · 取消 · 下载
  │   ├─ providers/   23 个接口实现（pkgutil 自动发现，无需手动注册）
  │   ├─ updater/     应用内自更新（清单校验 / 完整性门禁 / 回滚）
  │   └─ 提示词助手 · 词库 · 翻译 · 日志
  └─ ui/              表现层：Tkinter 暗色主题，通过 Protocol 接口解耦
      └─ 主界面 · 词库面板 · 统计看板 · 提示词助手 · 配置向导 · 查看器
```

**4 层严格单向依赖**：`ui` → `services` → `data` → `config`，层间不可逆向引用。

---

## 🔌 扩展新接口

只需新建一个免费、付费或商业接口文件，框架自动发现：

```python
# services/providers/my_api.py
from typing import Callable, Tuple

from services.generation.errors import ProviderConfigError
from services.providers._net import (
    get_session,         # 线程独立共享 Session，勿自建 requests.Session
    raise_for_response,  # HTTP 状态码 → 类型化 ProviderError
    validate_image_url,  # 下载 API 返回的 URL 前必调（SSRF 防护）
)

PROVIDER_INFO = {
    "id":         "my_api",     # 稳定 ID，缺省用文件名
    "name":       "我的接口",   # 下拉框显示名
    "category":   "free",       # free | paid | commercial
    "config_key": "my_api_key", # 凭证在 cfg 中的键名
    # "supports_img2img": True, # 支持参考图编辑时声明
}

def try_my_api(prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("my_api_key", "").strip()
    if not key:
        raise ProviderConfigError("需要 MyAPI 的 API Key！注册地址：https://...")
    resp = get_session().post(url, json=payload, timeout=60)
    raise_for_response(resp, "my_api")  # HTTP 错误统一转类型化异常
    # ...解析响应；下载返回的图片 URL 前先 validate_image_url(url)
    return image_bytes, "我的接口"
```

文件保存后即自动出现在主界面下拉菜单；免费接口同时进入自动路由兜底序列，付费与商业接口需在配置向导中开启自动路由后参与。可用性判断由 `config_key` 自动派生，无需手动注册。

接入完整功能还需要：

1. 把 `my_api_key` 加入 `config/settings.py` 的 `DEFAULT_CONFIG`
2. 在 `ui/wizard_free.py`（免费）或 `ui/wizard_paid.py`（付费/商用）添加配置卡片，用户才有填写 Key 的入口
3. 想参与场景智能路由：在 `services/generation/scenes.py` 的 `ROUTES` 中按场景加入稳定 ID
4. 支持图生图的接口：声明 `"supports_img2img": True`，并在 `services/providers/__init__.py` 的 `WIZARD_CONFIGURED` 中登记配置入口，才会出现在图生图下拉框

---

## 📦 构建发行版

```bash
# 一键打包（需要 Python 3.11+、PyInstaller 与 Inno Setup 6）
pip install pyinstaller
python auto_build.py
# → dist/2image.exe               便携版
# → installer/Output/*.exe         安装包
```

CI/CD 已配置 GitHub Actions，推送 `v*` 标签自动触发测试 → 构建 → 发布 Release。

---

## 🗂 本地数据目录

| 路径 | 内容 |
|---|---|
| `~/2image/config.json` | API Key 及偏好设置 |
| `~/2image/history.db` | 生图历史、标签与统计（SQLite） |
| `~/2image/images/` | 已生成的图片文件 |
| `~/2image/phrase_library.json` | 自定义词库（分类与词条） |
| `~/2image/phrase_desc.json` | 自定义词条说明 |
| `~/2image/phrase_usage.json` | 词条使用计数（用于频次排序） |
| `~/2image/prompt_history.json` | 提示词助手历史（最近 8 条） |
| `~/2image/spend.json` | 当日付费接口消耗台账（成本估算用） |
| `~/2image/debug.log` | 调试日志（滚动，最大 5MB） |

所有数据仅存于本机，卸载程序后手动删除该目录即可完全清除。

> **升级说明**：数据目录已从旧版的 `~/.text_to_image_app` 迁移至 `~/2image`。首次启动新版本时，旧目录中的数据会自动复制到新目录，旧目录保留作为备份。
>
> **模型与兼容性**：接口模型随官方目录持续更新；配置中保存的旧模型 ID（如豆包 4.x / SeedEdit、通义万相 2.1 等已下线版本、MiniMax image-01）会自动归一化到当前默认，升级无需手动改配置。MiniMax H3 图生图走 `/v1/images/edits`（参考图以 data URI 提交）；该端点非幂等，超时后不会自动重试以避免重复计费。编辑为同步请求，服务端最长等待约 10 分钟，期间取消需等本次请求返回后生效。

---

## 🤝 参与贡献

欢迎提交 Issue 反馈问题，或 Pull Request 贡献代码。

在提交 PR 前，请确保测试与门禁通过：

```bash
pytest tests/ -q          # 全量 893 项，含 81 项端到端界面旅程
ruff check main.py config/ data/ services/ ui/ tools/ tests/ --select F821,E9
ruff format --check main.py config/ data/ services/ ui/ tools/ tests/
```

---

## 📄 许可证
本项目采用 [MIT License](LICENSE) 开源协议。

---

## ⭐ 支持这个项目

如果 2image 对你有帮助，欢迎给我一个 ⭐️ Star！

你的每一次支持，都是我持续改进的动力。
