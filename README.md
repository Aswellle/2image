<div align="center">

<h1>
  <img src="https://raw.githubusercontent.com.com/Aswellle/2image/main/assets/banner.png" alt="2image" width="48" align="bottom" />
  &nbsp;2image
</h1>

<p><strong>Desktop AI Image Generator · 22 Built-in Free, Paid & Commercial Image Generation Services</strong></p>

<p>
  One tool, all the major free and paid image generation APIs — minimal barrier to creation.<br/>
  Describe in Chinese, generate with one click — no coding, no server setup, all data stays local.
</p>

[![CI](https://github.com/Aswellle/2image/actions/workflows/ci.yml/badge.svg)](https://github.com/Aswellle/2image/actions)
[![Release](https://img.shields.io/github/v/release/Aswellle/2image)](https://github.com/Aswellle/2image/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4)](https://github.com/Aswellle/2image/releases/latest)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

<p>
  <a href="https://github.com/Aswellle/2image/releases/latest"><b>📥 Download</b></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/Aswellle/2image/issues">🐛 Report Issue</a>
  &nbsp;·&nbsp;
  <a href="#quick-start">📖 Documentation</a>
</p>

<p>
  <b>Language:</b>
  <a href="#english">English</a>
  &nbsp;|&nbsp;
  <a href="https://github.com/Aswellle/2image/blob/main/README.zh-CN.md">中文</a>
</p>

</div>

---

<a id="english"></a>
## 🐇 What is 2image?

**2image** is a Windows desktop AI image generation tool.

Just describe the scene you want, and 2image automatically calls the most suitable image generation API — no coding required, no server setup, no data leaks. Everything stays on your own machine.

> "One tool, all the major free and paid image generation APIs — minimal barrier to creation."

---

## ✨ Key Features

### 🎯 One Interface, 19 Selectable APIs
Directly select from 19 free and paid image generation services on the main interface, covering Pollinations, SiliconFlow, Gemini, Qwen-Image, Bria AI, OpenAI GPT-Image, Black Forest Labs FLUX, and more. **Start with services that require no API key, then optionally configure free or paid APIs** — generation tries available services in priority order. 3 additional commercial services are also implemented (see below).

### 🆓 Zero-Cost Start
**Pollinations.AI works without registration** — ready out of the box. Anonymous calls are subject to rate limits. After registering a few services with free tiers, you can unlock more high-quality models to cover everyday creative needs.

### 🧠 Smart Routing, One-Click Optimal
Once services are configured, entering "banner design" prioritizes Ideogram (excellent for text-in-image); entering "e-commerce product photo" prioritizes fal.ai FLUX Ultra (photorealistic HD). Different scenes try suitable models in priority order, or you can manually specify an API.

### 🖼 Image-to-Image (img2img)
After uploading a reference image, the program shows only the img2img-capable APIs that have configuration entries. Use Stability AI's "strength" slider to control modification intensity; other supported models also receive the reference image. Currently supports Stability AI, Google Gemini Nano Banana, Nano Banana Pro, OpenAI GPT-Image, MiniMax image-01, and Black Forest Labs FLUX. Batch variant and queue modes automatically lock to img2img to prevent the reference image from being ignored.

### 🎲 Batch Variants — 6 Images at Once
Automatically generates multiple seed variants from the same prompt, compare and pick the best one — greatly improves creative efficiency. Supports standard mode and higher-quality mode (more steps / better models).

### 📋 Sequential Queue — Runs While You're Away
Add multiple tasks to a queue and let the program generate them sequentially. Pause, resume, or stop at any time; newly added tasks are automatically included in the current round.

### 🔧 AI Prompt Optimization
Built-in prompt optimization wizard turns vague ideas into high-quality English prompts. With a SiliconFlow key configured, it tries DeepSeek V3, Qwen, and GLM in order; you can also enter a DeepSeek official API key and manually choose quality-first Pro or speed-first Flash presets. Without SiliconFlow, the HuggingFace channel is available as fallback.

### 🀄 Native Chinese Support
Enter Chinese descriptions directly — the program automatically calls MyMemory to translate to English before sending to image APIs. No manual translation, no extra configuration.

### 🔒 Fully Local Data
All images, history, and configuration are saved on your machine (`~/.text_to_image_app/`). No user data is uploaded. Installers distributed to others contain no personal information or API keys.

---

## 🚀 Quick Start

### Option A: Download Installer (Recommended)

1. Go to the [Releases page](https://github.com/Aswellle/2image/releases/latest)
2. Download `text2image_pro_v*.exe` (installer) or `text2image_pro.exe` (portable)
3. Run — a configuration wizard appears on first launch
4. No API key required to start generating (Pollinations.AI is free and unlimited)

### Option B: Run from Source

```bash
git clone https://github.com/Aswellle/2image.git
cd 2image
pip install -r requirements.txt
python main.py
```

---

## 🌐 Supported Image Generation APIs

### Free APIs (Recommended to Configure First)

| API | Model | Free Tier | API Key Required |
|---|---|---|---|
| **Pollinations.AI** | FLUX Schnell | No fixed daily quota; anonymous calls rate-limited | ❌ No registration needed |
| **SiliconFlow** ⭐ | FLUX.1-dev/schnell · SDXL | Free credits on signup | ✅ Free registration |
| **Google Gemini** | Gemini 2.5 Flash Image (Nano Banana) | Per Google AI Studio current free tier | ✅ Free registration |
| **Qwen-Image (Dashscope)** | wanx2.1-t2i-turbo | Free tier for new Alibaba Cloud users | ✅ Free registration |
| **Bria AI Fibo** | Fibo | 1000 free calls on signup | ✅ Free registration |
| **Cloudflare Workers AI** | FLUX.1-schnell | 10k Neurons/day (~10–20 high-res images) | ✅ Free registration |
| **HuggingFace** | FLUX · Stable Diffusion 3 Medium | Free inference API | ✅ Free registration |
| **StableHorde** | SD series | Anonymous available | ❌ Optional registration |
| **ModelsLab** | FLUX · SDXL | 100/day | ✅ Free registration |
| **Together AI** | FLUX.1-schnell | Free availability per Together console | ✅ Free registration |
| **OpenRouter** | Unified Image API | Per-model billing; see model page for free availability | ✅ Free registration |
| **Segmind** | FLUX · SDXL | $5 free credits on signup | ✅ Free registration |

### Paid APIs

| API | Features | Pricing |
|---|---|---|
| **💎 OpenAI GPT-Image** | Text-to-image & reference image editing, supports gpt-image-1 / mini | Per-request |
| **💎 Nano Banana Pro** | Gemini 3 Pro Image, high-quality img2img, reuses Gemini key | Pay-per-use |
| **💎 MiniMax image-01** | Text-to-image & subject reference image creation | Pay-per-use |
| **💎 Black Forest Labs FLUX** | Official FLUX text-to-image & Kontext img2img | Pay-per-use |
| **💎 Stability AI** | Supports img2img, original Stable Diffusion | Per-request |
| **💎 Replicate FLUX** | FLUX.1.1 Pro high resolution | Per-request |
| **💎 xAI Grok Imagine** | Grok Imagine Image Quality model | Per-request |

### Commercial APIs

These services are auto-discovered by the registry but are not yet integrated into the main UI dropdown or key configuration wizards — suitable for commercial use cases where you can add your own configuration entry points.

| API | Features |
|---|---|
| **Ideogram v3** | Best for text-in-image: banners, logos, posters with readable text |
| **fal.ai FLUX Ultra** | Up to 4MP ultra-HD photorealistic, best for product photos / portraits |
| **Recraft v3** | Design / illustration / vector style, ideal for brand VI |

---

## 🏗 Architecture Overview

```
main.py
  └─ config/          Configuration layer: paths · themes · i18n · fonts
  └─ data/            Data layer: SQLite history (WAL mode, thread-safe)
  └─ services/        Service layer: dispatch · routing · translation · prompt optimization
  │   └─ providers/   22 API implementations (auto-discovered via pkgutil, no manual registration)
  └─ ui/              Presentation layer: Tkinter dark theme, decoupled via Protocol interfaces
```

**4-layer strict unidirectional dependency**: `ui` → `services` → `data` → `config`. No reverse references between layers.

---

## 🔌 Adding a New API

Just create a new file — the framework discovers it automatically:

```python
# services/providers/my_api.py
PROVIDER_INFO = {
    "id":         "my_api",
    "name":       "My API",
    "category":   "free",   # free | paid | commercial
    "config_key": "my_api_key",
}

def try_my_api(prompt, w, h, seed, cfg, log):
    key = cfg.get("my_api_key", "").strip()
    if not key:
        raise ValueError("API key required")
    # ... call the API ...
    return image_bytes, "My API"
```

Free and paid APIs automatically appear in the UI dropdown and smart routing. Commercial APIs are also auto-registered — extend using the project's commercial API integration pattern.

---

## 📦 Building a Release

```bash
# One-command build (requires PyInstaller + Inno Setup)
pip install pyinstaller
python auto_build.py
# → dist/text2image_pro.exe         Portable version
# → installer/Output/*.exe          Installer
```

CI/CD is configured via GitHub Actions — pushing a `v*` tag automatically triggers test → build → release.

---

## 🗂 Local Data Directory

| Path | Content |
|---|---|
| `~/.text_to_image_app/config.json` | API keys & preferences |
| `~/.text_to_image_app/history.db` | Generation history (SQLite) |
| `~/.text_to_image_app/images/` | Generated image files |
| `~/.text_to_image_app/debug.log` | Debug log (rotating, max 5 MB) |

All data stays local. Delete this directory after uninstalling for complete removal.

---

## 🤝 Contributing

File an Issue to report problems, or submit a Pull Request to contribute code.

Before submitting a PR, make sure tests pass:

```bash
pytest tests/ -v
```

---

## 📄 License

This project is open-sourced under the [MIT License](LICENSE).
