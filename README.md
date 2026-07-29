<div align="center">

<h1>
  <img src="https://raw.githubusercontent.com/Aswellle/2image/main/assets/banner.png" alt="2image" width="48" align="bottom" />
  &nbsp;2image · 兔图
</h1>

<p><strong>桌面 AI 图片生成器 · 内置 22 个免费、付费及商用生图服务</strong></p>

<p>
  一个工具，接入市面上主流的免费与付费生图 API，让创作门槛降到最低。<br/>
  输入中文描述，一键生成 —— 无需编程，无需搭建，数据完全本地。
</p>

[![CI](https://github.com/Aswellle/2image/actions/workflows/ci.yml/badge.svg)](https://github.com/Aswellle/2image/actions)
[![Release](https://img.shields.io/github/v/release/Aswellle/2image)](https://github.com/Aswellle/2image/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4)](https://github.com/Aswellle/2image/releases/latest)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

<p>
  <a href="https://github.com/Aswellle/2image/releases/latest"><b>📥 立即下载</b></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/Aswellle/2image/issues">🐛 反馈问题</a>
  &nbsp;·&nbsp;
  <a href="#快速上手">📖 使用文档</a>
</p>

</div>

---

## 🐇 什么是 2image（兔图）？

**2image · 兔图** 是一款运行在 Windows 桌面的 AI 图片生成工具。

只需描述你想要的画面，兔图就会自动调用最合适的生图接口为你生成——无需任何编程基础，无需搭建服务，不用担心数据外泄，所有内容都保存在你自己的电脑上。

> "一个工具，接入市面上主流的免费与付费生图 API，让创作门槛降到最低。"

---

## ✨ 核心亮点

### 🎯 一个界面，19 个可选接口
主界面可直接选择 19 个免费与付费生图服务，覆盖 Pollinations、硅基流动、Gemini、通义万相、Bria AI、OpenAI GPT-Image 与 Black Forest Labs FLUX 等。**可先使用无需 Key 的服务，再按需配置免费或付费 API**；生成会按当前优先序列依次尝试可用服务。另有 3 个商用服务实现，见下方说明。

### 🆓 零成本起步
**Pollinations.AI 无需注册即可体验**，开箱即用；匿名调用仍受频率限制。注册几个提供免费额度的服务后，还能解锁更多高质量模型，覆盖日常创作需求。

### 🧠 智能路由，一键最优
配置可用服务后，输入「banner 设计」会优先排列 Ideogram（擅长文字入图）；输入「电商产品图」会优先排列 fal.ai FLUX Ultra（写实高清）。不同场景按优先序列尝试适合的模型，也可手动指定接口。

### 🖼 图生图（img2img）
上传参考图后，程序会只显示已接入且已有配置入口的图生图接口；可使用 Stability AI 的「变化强度」控制改动幅度，其他支持的模型会一并接收参考图。当前可选 Stability AI、Google Gemini Nano Banana、Nano Banana Pro、OpenAI GPT-Image、MiniMax image-01 与 Black Forest Labs FLUX 等服务；批量变体和顺序队列会在图生图模式下自动锁定，避免参考图被忽略。

### 🎲 批量变体，一次生成 6 张
同一提示词自动生成多张不同种子的变体，对比挑选最满意的一张，极大提升创作效率。支持标准模式与高质量模式（更高步数 / 更好模型）。

### 📋 顺序队列，离开也能跑
将多个任务加入队列，让程序按顺序自动生成。可随时暂停、继续或停止，中途新增任务也会自动纳入当前轮次。

### 🔧 AI 提示词优化
内置提示词优化向导，可将模糊想法整理成高质量英文提示词。填写硅基流动 Key 后会按 DeepSeek V3、Qwen 与 GLM 候选顺序尝试；也可填写 DeepSeek 官方 API Key，手动选择质量优先的 Pro 或速度优先的 Flash 预设。未配置硅基流动时，可改用 HuggingFace 通道。

### 🀄 中文原生支持
直接输入中文描述，程序自动调用 MyMemory 翻译为英文再送入生图接口——无需手动翻译，无需额外配置。

### 🔒 数据完全本地
所有图片、历史记录、配置均保存在你的电脑（`~/.text_to_image_app/`），不上传任何用户数据。分发给他人的安装包内不含任何个人信息和 API 密钥。

---

## 🚀 快速上手

### 方式一：下载安装包（推荐）

1. 前往 [Releases 页面](https://github.com/Aswellle/2image/releases/latest)
2. 下载 `text2image_pro_v*.exe`（安装包）或 `text2image_pro.exe`（便携版）
3. 运行，首次启动会弹出配置向导
4. 不配置任何 Key 也可直接生成（Pollinations.AI 免费无限额）

### 方式二：从源码运行

```bash
git clone https://github.com/Aswellle/2image.git
cd 2image
pip install -r requirements.txt
python main.py
```

---

## 🌐 支持的生图接口

### 免费接口（推荐优先配置）

| 接口 | 模型 | 免费额度 | 是否需要 Key |
|---|---|---|---|
| **Pollinations.AI** | FLUX Schnell | 无固定日配额，匿名调用有频率限制 | ❌ 无需注册 |
| **硅基流动 SiliconFlow** ⭐ | FLUX.1-dev/schnell · SDXL | 注册送免费额度 | ✅ 免费注册 |
| **Google Gemini** | Gemini 2.5 Flash Image（Nano Banana） | 以 Google AI Studio 当前免费额度为准 | ✅ 免费注册 |
| **通义万相 Qwen-Image** | wanx2.1-t2i-turbo | 阿里云新用户免费额度 | ✅ 免费注册 |
| **Bria AI Fibo** | Fibo | 注册送 1000 次调用 | ✅ 免费注册 |
| **Cloudflare Workers AI** | FLUX.1-schnell | 1 万 Neurons/天（约 10–20 张高分辨率图） | ✅ 免费注册 |
| **HuggingFace** | FLUX · Stable Diffusion 3 Medium | 免费推理 API | ✅ 免费注册 |
| **StableHorde** | SD 系列 | 匿名可用 | ❌ 可选注册 |
| **ModelsLab** | FLUX · SDXL | 100 次/天 | ✅ 免费注册 |
| **Together AI** | FLUX.1-schnell | 免费可用性请以 Together 控制台为准 | ✅ 免费注册 |
| **OpenRouter** | 统一 Image API | 按所选模型计费，免费可用性请以模型页为准 | ✅ 免费注册 |
| **Segmind** | FLUX · SDXL | 注册送 $5 额度 | ✅ 免费注册 |

### 付费接口

| 接口 | 特点 | 定价参考 |
|---|---|---|
| **💎 OpenAI GPT-Image** | 文生图与参考图编辑，支持 gpt-image-1 / mini | 按次计费 |
| **💎 Nano Banana Pro** | Gemini 3 Pro Image，高画质图生图，复用 Gemini Key | 按量计费 |
| **💎 MiniMax image-01** | 文生图与主体参考图创作 | 按量计费 |
| **💎 Black Forest Labs FLUX** | 官方 FLUX 文生图与 Kontext 图生图 | 按量计费 |
| **💎 Stability AI** | 支持图生图，Stable Diffusion 原厂 | 按次计费 |
| **💎 Replicate FLUX** | FLUX.1.1 Pro 高分辨率 | 按次计费 |
| **💎 xAI Grok Imagine** | Grok Imagine Image Quality 模型 | 按次计费 |

### 商业变现接口

以下服务已由注册表自动发现；当前尚未接入常规的主界面下拉菜单与密钥配置向导，适合需要自行补充配置入口的商用场景。

| 接口 | 特点 |
|---|---|
| **Ideogram v3** | 文字入图首选，Banner / LOGO / 海报中文字可读 |
| **fal.ai FLUX Ultra** | 最高 4MP 超清写实，产品图 / 人像首选 |
| **Recraft v3** | 设计 / 插画 / 矢量风格，品牌 VI 利器 |

---

## 🏗 架构概览

```
main.py
  └─ config/          配置层：路径 · 主题 · 国际化 · 字体
  └─ data/            数据层：SQLite 历史（WAL 模式，线程安全）
  └─ services/        服务层：调度 · 路由 · 翻译 · 提示词优化
  │   └─ providers/   22 个接口实现（pkgutil 自动发现，无需手动注册）
  └─ ui/              表现层：Tkinter 暗色主题，通过 Protocol 接口解耦
```

**4 层严格单向依赖**：`ui` → `services` → `data` → `config`，层间不可逆向引用。

---

## 🔌 扩展新接口

只需新建一个免费或付费接口文件，框架自动发现：

```python
# services/providers/my_api.py
PROVIDER_INFO = {
    "id":         "my_api",
    "name":       "我的接口",
    "category":   "free",   # free | paid | commercial
    "config_key": "my_api_key",
}

def try_my_api(prompt, w, h, seed, cfg, log):
    key = cfg.get("my_api_key", "").strip()
    if not key:
        raise ValueError("需要 API Key")
    # ... 调用接口 ...
    return image_bytes, "我的接口"
```

免费或付费接口会自动出现在 UI 下拉菜单和智能路由中。商用分类也会被自动注册，可按项目的商用接口接入方式继续扩展。

---

## 📦 构建发行版

```bash
# 一键打包（需要 PyInstaller + Inno Setup）
pip install pyinstaller
python auto_build.py
# → dist/text2image_pro.exe        便携版
# → installer/Output/*.exe         安装包
```

CI/CD 已配置 GitHub Actions，推送 `v*` 标签自动触发测试 → 构建 → 发布 Release。

---

## 🗂 本地数据目录

| 路径 | 内容 |
|---|---|
| `~/.text_to_image_app/config.json` | API Key 及偏好设置 |
| `~/.text_to_image_app/history.db` | 生图历史（SQLite） |
| `~/.text_to_image_app/images/` | 已生成的图片文件 |
| `~/.text_to_image_app/debug.log` | 调试日志（滚动，最大 5MB） |

所有数据仅存于本机，卸载程序后手动删除该目录即可完全清除。

---

## 🤝 参与贡献

欢迎提交 Issue 反馈问题，或 Pull Request 贡献代码。

在提交 PR 前，请确保测试通过：

```bash
pytest tests/ -v
```

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。
