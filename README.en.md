<div align="center">

<img src="https://raw.githubusercontent.com/Aswellle/2image/main/assets/logo.png" alt="2image" width="200" />

<h1>2image</h1>
<p><strong>Desktop AI Image Generator · 23 Built-in Free, Paid & Commercial Image Generation Services</strong></p>

<p>
  One tool, all the major free, paid and commercial image generation APIs — minimal barrier to creation.<br/>
  Describe your image, generate with one click — no coding, no server setup, all data stays local.
</p>

[![CI](https://github.com/Aswellle/2image/actions/workflows/ci.yml/badge.svg)](https://github.com/Aswellle/2image/actions)
[![Downloads](https://img.shields.io/github/downloads/Aswellle/2image/total)](https://github.com/Aswellle/2image/releases)
[![Release](https://img.shields.io/github/v/release/Aswellle/2image)](https://github.com/Aswellle/2image/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4)](https://github.com/Aswellle/2image/releases/latest)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

<p>
  <a href="https://github.com/Aswellle/2image/releases/latest"><b>📥 Download</b></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/Aswellle/2image/issues">🐛 Report Issue</a>
  &nbsp;·&nbsp;
  <a href="#-quick-start">📖 Documentation</a>
</p>

<p>
  <b>Language:</b>
  <a href="#english">English</a>
  &nbsp;|&nbsp;
  <a href="https://github.com/Aswellle/2image/blob/main/README.md">中文</a>
</p>

</div>

---

<a id="english"></a>
## 🎨 What is 2image?

**2image** is a Windows desktop AI image generation tool.

Just describe the scene you want, and 2image automatically calls the most suitable image generation API — no coding required, no server setup, no data leaks. Everything stays on your own machine.

> "One tool, all the major free, paid and commercial image generation APIs — minimal barrier to creation."

---

## ✨ Key Features

### 🎯 One Interface, 23 Selectable APIs
Directly select from all 23 image generation services (12 free + 6 paid + 5 commercial) on the main interface, covering Pollinations, SiliconFlow, Gemini Nano Banana, Qwen-Image, Bria AI, OpenAI GPT-Image, Black Forest Labs FLUX, Ideogram, fal.ai FLUX.2, Recraft, MiniMax H3, Doubao Seedream and more. **Start with services that require no API key, then optionally configure free, paid or commercial APIs** — every API has a key entry and model picker in the Free or Paid setup wizard, so no manual config-file editing is needed. Generation tries available services in priority order.

### 🆓 Zero-Cost Start
**Pollinations.AI works without registration** — ready out of the box. Anonymous calls are subject to rate limits. After registering a few services with free tiers, you can unlock more high-quality models to cover everyday creative needs.

### 🧠 Smart Routing, One-Click Optimal
Once services are configured, entering "banner design" prioritizes Ideogram (excellent for text-in-image); entering "e-commerce product photo" prioritizes fal.ai FLUX.2 Pro (photorealistic HD). Different scenes try suitable models in priority order, or you can manually specify an API. Paid and commercial APIs stay out of Auto mode by default; enable them (and set a daily USD budget) under "Paid API Setup → Auto routing & paid budget". Once enabled, prompts without a matched scene also try paid APIs after the free ones.

### 🖼 Image-to-Image (img2img)
After uploading a reference image, the program shows only the img2img-capable APIs that have configuration entries — currently 8: Stability AI (with a "strength" slider to control modification intensity), Nano Banana Pro, Black Forest Labs FLUX, the Gemini Nano Banana family, OpenAI GPT-Image, Doubao Seedream, fal.ai FLUX.2, and MiniMax H3 (native reference editing via `/v1/images/edits`). Batch variant and queue modes automatically lock to img2img to prevent the reference image from being ignored.

### 🎲 Batch Variants — 6 Images at Once
Automatically generates multiple seed variants from the same prompt, compare and pick the best one — greatly improves creative efficiency. Supports standard mode and higher-quality mode (more steps / better models).

### 📋 Sequential Queue — Runs While You're Away
Add multiple tasks to a queue and let the program generate them sequentially. Pause, resume, or stop at any time; newly added tasks are automatically included in the current round.

### 🔧 AI Prompt Optimization
Built-in prompt optimization wizard turns vague ideas into high-quality English prompts. With a SiliconFlow key configured, it tries DeepSeek-V3.2, V3.1-Terminus, and Qwen3-8B in fallback order; you can also enter a DeepSeek official API key and manually choose the quality-first Pro (deepseek-v4-pro) or speed-first Flash (deepseek-flash) preset.
The wizard can generate 3 candidates at once and switch between them with ‹ / › or the arrow keys; history persists across sessions. Template cards support keyboard navigation, one-click retry reuses the previous parameters, and a guard protects manually edited results before regeneration.

### 📚 Prompt Phrase Library
Ships with 45 phrases across 7 categories, plus custom categories and phrases. `{{variable}}` placeholders in a phrase open a fill-in dialog before insertion; custom phrases can carry descriptions that travel with exports; the library supports JSON import/export and cross-machine merging. Search covers phrases and their bilingual descriptions and labels each hit with its category; phrases are sorted by usage frequency, and the hover card shows how often a phrase appears in generation history. History cards can also save a prompt to "⭐ My Phrases" in one click.

### 📊 Statistics Dashboard
Includes a full-year heatmap, provider usage distribution, Top-10 tags, plus favorite rate, 7-day trend, generation streak, and cost estimates (history estimate + today's ledger + budget progress), with one-click export to a multi-section CSV or a 1280×900 share image.

### 🀄 Native Chinese Support
Enter Chinese descriptions directly — the program automatically calls MyMemory to translate to English before sending to image APIs. No manual translation, no extra configuration.

### 🔒 Fully Local Data
All images, history, and configuration are saved on your machine (`~/2image/`). No user data is uploaded.

---

## 🚀 Quick Start

### Option A: Download Installer (Recommended)

1. Go to the [Releases page](https://github.com/Aswellle/2image/releases/latest)
2. Download `2image-setup-v*.exe` (installer) or `2image-portable-v*.exe` (portable)
3. Run — a configuration wizard appears on first launch
4. No API key required to start generating (Pollinations.AI is free without registration; anonymous calls are rate-limited)

### Option B: Run from Source

**Requirements**

- **OS**: Windows 10 / 11 (64-bit); the GUI is built on Tkinter and needs a desktop session.
- **Python**: 3.11 or 3.12 (CI validates both; 3.11 is the minimum supported version, 3.13 is not yet validated). Tkinter ships with the official Python installer — keep the default `tcl/tk` component selected.
- **Dependencies**: only `Pillow` and `requests`, installed from `requirements.txt`; no Node.js, database, or browser is required. Development/testing additionally needs `pytest`, `pytest-cov`, and `ruff` (also in `requirements.txt`).
- **Disk**: about 100 MB for source and dependencies; generated images live in `~/2image/images/`.

```bash
git clone https://github.com/Aswellle/2image.git
cd 2image
py -3.11 -m venv .venv          # 3.12 works too; a venv is optional
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

The first launch creates the `~/2image/` data directory; no API key is required to start generating (Pollinations.AI is free without registration; anonymous calls are rate-limited).

---

## 🌐 Supported Image Generation APIs

### Free APIs (Recommended to Configure First)

| API | Model | Free Tier | API Key Required |
|---|---|---|---|
| **Pollinations.AI** | FLUX · Turbo · SANA (verified anonymous list; GPTImage in HQ mode) | No fixed daily quota; anonymous calls rate-limited | ❌ No registration needed |
| **SiliconFlow** ⭐ | FLUX.1 · SDXL · Kolors · SDXL-Lightning / Turbo | Free credits on signup | ✅ Free registration |
| **Google Gemini** | Nano Banana family (2.1 default; 2 / 2 Lite / Pro switchable) | Per Google AI Studio current free tier | ✅ Free registration |
| **Qwen-Image (Dashscope)** | wan2.6-t2i (default, sync protocol) · wan2.5-t2i (legacy async) | Free tier for new Alibaba Cloud users | ✅ Free registration |
| **Bria AI Fibo** | Fibo | 1000 free calls on signup | ✅ Free registration |
| **Cloudflare Workers AI** | FLUX.1-schnell · FLUX.2-dev (HQ mode) · SDXL | 10k Neurons/day (~10–20 high-res images) | ✅ Free registration |
| **HuggingFace** | Stable Diffusion 3 Medium | Free inference API | ✅ Free registration |
| **StableHorde** | DreamShaper XL · Stable Diffusion | Anonymous available | ❌ Optional registration |
| **ModelsLab** | FLUX · SDXL · Realistic Vision · SD 1.5 | 100/day | ✅ Free registration |
| **Together AI** | FLUX.1-schnell (official free endpoint) | Free availability per Together console | ✅ Free registration |
| **OpenRouter** | Unified Image API (default gemini-3.1-flash-image) | Per-model billing; see model page for free availability | ✅ Free registration |
| **Segmind** | FLUX Schnell · SDXL · SD3 Medium | $5 free credits on signup | ✅ Free registration |

### Paid APIs

| API | Features | Pricing |
|---|---|---|
| **💎 OpenAI GPT-Image** | gpt-image-2 default (2.5 / 2.6 Flare·Sunburst optional), text-to-image & reference image editing | Per-request |
| **💎 Nano Banana Pro** | Gemini 3 Pro Image, high-quality text-to-image and img2img, reuses Gemini key | Pay-per-use |
| **💎 Black Forest Labs FLUX** | Official FLUX.2 single endpoint for text-to-image & img2img (flux-2-pro default) | Pay-per-use |
| **💎 Stability AI** | SD3.5-large / core, supports img2img with a "strength" control | Per-credit |
| **💎 Replicate FLUX** | black-forest-labs/flux-2-pro officially hosted | Per-request |
| **💎 xAI Grok Imagine** | grok-imagine-image-2.0, with aspect-ratio & resolution controls | Per-request |

### Commercial APIs

These services appear in the main UI dropdown at the same level as free / paid APIs, with key entry and model selection in the Paid API setup wizard — no custom configuration entry points required.

| API | Features |
|---|---|
| **Ideogram v4** | Best for text-in-image: banners, logos, posters with readable text |
| **fal.ai FLUX.2 Pro** | Text-to-image `fal-ai/flux-2-pro` + instruction-based `/edit`, up to 4MP ultra-HD photorealistic — best for product photos / portraits |
| **Recraft v4.1** | Design / illustration / vector style, ideal for brand VI (recraftv4_1 default; switchable back to v3, three styles) |
| **MiniMax H3 Image** | H3-Image / H3-Image-Highspeed text-to-image + reference editing (`/v1/images/edits`), up to 20MP |
| **Doubao Seedream (Volcengine)** | Seedream 5.5 (default) / 5.0 Pro / 5.0 Flash text-to-image + native reference-image editing |

---

## 🏗 Architecture Overview

```
main.py
  └─ config/          Configuration layer: paths · themes · i18n · fonts · model catalog
  └─ data/            Data layer: SQLite history / tags / statistics (WAL mode, thread-safe)
  └─ services/        Service layer
  │   ├─ application/ App controllers: generation · menu · settings
  │   ├─ generation/  Orchestration · retry · budget · cancellation · download
  │   ├─ providers/   23 API implementations (auto-discovered via pkgutil, no manual registration)
  │   ├─ updater/     In-app self-update (manifest validation / integrity gates / rollback)
  │   └─ Prompt assistant · phrase library · translation · logging
  └─ ui/              Presentation layer: Tkinter dark theme, decoupled via Protocol interfaces
      └─ Main window · phrase library · statistics dashboard · prompt wizard · config wizards · viewer
```

**4-layer strict unidirectional dependency**: `ui` → `services` → `data` → `config`. No reverse references between layers.

---

## 🔌 Adding a New API

Just create a new free, paid or commercial API file — the framework discovers it automatically:

```python
# services/providers/my_api.py
from typing import Callable, Tuple

from services.generation.errors import ProviderConfigError
from services.providers._net import (
    get_session,         # shared per-thread Session — don't build your own
    raise_for_response,  # HTTP status → typed ProviderError
    validate_image_url,  # call before downloading any API-returned URL (SSRF guard)
)

PROVIDER_INFO = {
    "id":         "my_api",      # stable ID; falls back to the file name
    "name":       "My API",      # dropdown display name
    "category":   "free",        # free | paid | commercial
    "config_key": "my_api_key",  # cfg key for credentials
    # "supports_img2img": True, # declare for reference-image support
}

def try_my_api(prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable) -> Tuple[bytes, str]:
    key = cfg.get("my_api_key", "").strip()
    if not key:
        raise ProviderConfigError("MyAPI API key required. Sign up: https://...")
    resp = get_session().post(url, json=payload, timeout=60)
    raise_for_response(resp, "my_api")  # HTTP failures become typed errors
    # ...parse the response; call validate_image_url(url) before downloading
    return image_bytes, "My API"
```

Once saved, the API appears automatically in the main dropdown; free APIs also join the auto-routing fallback chain, while paid and commercial APIs join after auto-routing is enabled in the setup wizard. Availability is derived from `config_key`, no manual registration needed.

To complete the integration:

1. Add `my_api_key` to `DEFAULT_CONFIG` in `config/settings.py`
2. Add a config card in `ui/wizard_free.py` (free) or `ui/wizard_paid.py` (paid/commercial) so users have an entry point to paste the key
3. For scene-based smart routing, add the stable ID to `ROUTES` in `services/generation/scenes.py`
4. For img2img support: declare `"supports_img2img": True` and register the config entry in `WIZARD_CONFIGURED` in `services/providers/__init__.py` to appear in the img2img dropdown

---

## 📦 Building a Release

```bash
# One-command build (requires Python 3.11+, PyInstaller, and Inno Setup 6)
pip install pyinstaller
python auto_build.py
# → dist/2image.exe                 Portable version
# → installer/Output/*.exe          Installer
```

CI/CD is configured via GitHub Actions — pushing a `v*` tag automatically triggers test → build → release.

---

## 🗂 Local Data Directory

| Path | Content |
|---|---|
| `~/2image/config.json` | API keys & preferences |
| `~/2image/history.db` | Generation history, tags, and statistics (SQLite) |
| `~/2image/images/` | Generated image files |
| `~/2image/phrase_library.json` | Custom phrase library (categories & phrases) |
| `~/2image/phrase_desc.json` | Custom phrase descriptions |
| `~/2image/phrase_usage.json` | Phrase usage counts (frequency sorting) |
| `~/2image/prompt_history.json` | Prompt assistant history (latest 8) |
| `~/2image/spend.json` | Today's paid-API spend ledger (cost estimates) |
| `~/2image/debug.log` | Debug log (rotating, max 5 MB) |

All data stays local. Delete this directory after uninstalling for complete removal.

> **Upgrade note**: The data directory has moved from the legacy `~/.text_to_image_app` to `~/2image`. On first launch, data from the old directory is automatically copied to the new location; the old directory is kept as a backup.
>
> **Models & compatibility**: API models track the official catalogs; legacy model IDs stored in config (e.g. Doubao 4.x / SeedEdit, retired Qwen-Image models such as 2.1, MiniMax image-01) are automatically normalized to current defaults, so no manual edits are needed. MiniMax H3 img2img uses `/v1/images/edits` (the reference image is sent as a data URI); that endpoint is not idempotent, so timeouts are not retried automatically to avoid double billing. Edits are synchronous and can take up to 10 minutes; a cancel takes effect after the request returns.

---

## 🤝 Contributing

File an Issue to report problems, or submit a Pull Request to contribute code.

Before submitting a PR, make sure tests and gates pass:

```bash
pytest tests/ -q          # 876 tests, including 81 end-to-end UI journeys
ruff check main.py config/ data/ services/ ui/ tools/ tests/ --select F821,E9
ruff format --check main.py config/ data/ services/ ui/ tools/ tests/
```

---

## 📄 License

This project is open-sourced under the [MIT License](LICENSE).

---

## ⭐ Support This Project

If 2image is useful to you, a ⭐️ star is greatly appreciated!

Every bit of support keeps the project moving forward.
