<div align="center">

```
╔══════════════════════════════════════════════════════╗
║   ___  _                                             ║
║  |__ \(_)_ __ ___   __ _  __ _  ___                 ║
║    / /| | '_ ` _ \ / _` |/ _` |/ _ \                ║
║   / /_| | | | | | | (_| | (_| |  __/                ║
║  |____|_|_| |_| |_|\__,_|\__, |\___|  兔 图          ║
║                           |___/                      ║
╚══════════════════════════════════════════════════════╝
```

**桌面 AI 图片生成器 · 聚合 17 个免费与付费生图接口**

[![CI](https://github.com/Aswellle/2image/actions/workflows/ci.yml/badge.svg)](https://github.com/Aswellle/2image/actions)
[![Release](https://img.shields.io/github/v/release/Aswellle/2image)](https://github.com/Aswellle/2image/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4)](https://github.com/Aswellle/2image/releases/latest)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

[📥 立即下载](https://github.com/Aswellle/2image/releases/latest) · [🐛 反馈问题](https://github.com/Aswellle/2image/issues) · [📖 使用文档](#快速上手)

</div>

---

## 🐇 什么是 2image（兔图）？

**2image · 兔图** 是一款运行在 Windows 桌面的 AI 图片生成工具。

只需描述你想要的画面，兔图就会自动调用最合适的生图接口为你生成——无需任何编程基础，无需搭建服务，不用担心数据外泄，所有内容都保存在你自己的电脑上。

> "一个工具，接入市面上主流的免费与付费生图 API，让创作门槛降到最低。"

---

## ✨ 核心亮点

### 🎯 一个界面，17 个接口
同时接入 Pollinations、硅基流动、Gemini、Cloudflare、fal.ai、DALL-E 3 等 17 个主流生图服务。**免费的先用，付费的按需开通**，接口故障自动切换，生成从不中断。

### 🆓 零成本起步
**Pollinations.AI 完全免费、无需注册**，开箱即用。注册几个免费账号后还能解锁更多高质量模型，日均数百张的创作需求无需花一分钱。

### 🧠 智能路由，一键最优
输入「banner 设计」自动优先 Ideogram（擅长文字入图）；输入「电商产品图」自动优先 fal.ai FLUX Ultra（写实高清）。不同场景用最合适的模型，无需手动切换。

### 🖼 图生图（img2img）
上传参考图，调整「变化强度」，让 AI 在保留原图风格的基础上进行创作。支持 Stability AI 和 fal.ai 等主流图生图接口。

### 🎲 批量变体，一次生成 6 张
同一提示词自动生成多张不同种子的变体，对比挑选最满意的一张，极大提升创作效率。支持标准模式与高质量模式（更高步数 / 更好模型）。

### 📋 顺序队列，离开也能跑
将多个任务加入队列，让程序按顺序自动生成。可随时暂停、继续或停止，中途新增任务也会自动纳入当前轮次。

### 🔧 AI 提示词优化
内置 DeepSeek V3 提示词优化向导（通过硅基流动 LLM 接口调用），帮助你把模糊想法转化为高质量的英文提示词，无需 DeepSeek 独立账号。

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
| **Pollinations.AI** | FLUX Schnell | 无限制 | ❌ 无需注册 |
| **硅基流动 SiliconFlow** ⭐ | FLUX.1-dev/schnell · SDXL | 注册送免费额度 | ✅ 免费注册 |
| **Google Gemini** | Gemini 2.5 Flash Image | 500 次/天 | ✅ 免费注册 |
| **Cloudflare Workers AI** | FLUX.1-schnell | 1 万次/天 | ✅ 免费注册 |
| **HuggingFace** | FLUX · SDXL | 免费推理 API | ✅ 免费注册 |
| **StableHorde** | SD 系列 | 匿名可用 | ❌ 可选注册 |
| **ModelsLab** | FLUX · SDXL | 100 次/天 | ✅ 免费注册 |
| **Together AI** | FLUX.1-schnell-Free | 免费端点 | ✅ 免费注册 |
| **OpenRouter** | 多种免费模型 | 部分模型免费 | ✅ 免费注册 |
| **Segmind** | FLUX · SDXL | 注册送 $5 额度 | ✅ 免费注册 |

### 付费接口

| 接口 | 特点 | 定价参考 |
|---|---|---|
| **💎 OpenAI DALL-E 3** | 高质量写实 / 插画，提示词服从度极高 | 按次计费 |
| **💎 Stability AI** | 支持图生图，Stable Diffusion 原厂 | 按次计费 |
| **💎 Replicate FLUX** | FLUX.1-pro 高分辨率 | 按次计费 |
| **💎 xAI Grok Imagine** | Aurora 模型，注册送 $25 免费额度 | 按次计费 |

### 商业变现接口

| 接口 | 特点 |
|---|---|
| **Ideogram v2** | 文字入图首选，Banner / LOGO / 海报中文字可读 |
| **fal.ai FLUX Ultra** | 最高 4MP 超清写实，产品图 / 人像首选 |
| **Recraft v3** | 设计 / 插画 / 矢量风格，品牌 VI 利器 |

---

## 🏗 架构概览

```
main.py
  └─ config/          配置层：路径 · 主题 · 国际化 · 字体
  └─ data/            数据层：SQLite 历史（WAL 模式，线程安全）
  └─ services/        服务层：调度 · 路由 · 翻译 · 提示词优化
  │   └─ providers/   17 个接口实现（pkgutil 自动发现，无需手动注册）
  └─ ui/              表现层：Tkinter 暗色主题，通过 Protocol 接口解耦
```

**4 层严格单向依赖**：`ui` → `services` → `data` → `config`，层间不可逆向引用。

---

## 🔌 扩展新接口

只需新建一个文件，框架自动发现：

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

无需修改任何其他文件，接口自动出现在 UI 下拉菜单和智能路由中。

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
