# Repository Guidelines

## Project Overview

Desktop text-to-image generation tool (文字生图工具) — a Python + Tkinter application that aggregates 17+ AI image generation APIs (free, paid, and commercial tiers) into a unified local GUI. Supports batch variants, AI prompt optimization via LLM (DeepSeek V3), phrase snippet library, translation (zh→en), and full history management with SQLite backend. Runs entirely locally with no server dependencies.

- **Language**: Python 3.11+
- **GUI**: tkinter + ttk (stdlib, no external GUI framework)
- **Packaging**: PyInstaller → Inno Setup → Windows `.exe` installer
- **Version**: 2.5.0 (managed via `version.json`)
- **Platform**: Windows-only (uses `ctypes.windll` for DPI awareness)
- **Dependencies**: `pillow`, `requests` (plus stdlib: `tkinter`, `sqlite3`, `threading`, `json`, `ctypes`, `pathlib`, `base64`, `io`, `os`, `re`, `time`, `datetime`, `random`, `hashlib`, `collections`, `concurrent.futures`, `functools`, `webbrowser`, `shutil`, `html`, `queue`, `urllib`, `ipaddress`, `subprocess`, `argparse`, `tempfile`)
- **No package management files exist**: no `requirements.txt`, `pyproject.toml`, `setup.py`, or `setup.cfg`
- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`) — quality gates + pytest matrix (3.11/3.12) + tag-driven build & release

---

## Architecture & Data Flow

```
main.py  (entry: DPI → fonts → DB init → tk.Tk → App)
   │
   └── ui/app.py  (App class — owns tk.Tk root, self.cfg dict, panel lifecycle)
          │
          ├── config/settings.py    ← load/save JSON config
          ├── config/fonts.py       ← font loading, F dict
          ├── config/theme.py       ← DARK_THEME (single dark theme), tag_color()
          ├── config/i18n.py        ← _(key) translation function, 2 locales
          ├── data/repository.py    ← SQLite CRUD (thread-local connections)
          ├── services/
          │   ├── image_service.py  ← dispatch to providers
          │   ├── smart_router.py   ← scene-aware provider selection
          │   ├── providers/*.py    ← individual API clients (auto-discovered)
          │   ├── generation/       ← orchestrator, router, budget, cancellation, downloader
          │   ├── prompt_assistant.py ← AI prompt generation (DeepSeek V3)
          │   ├── phrase_library.py ← built-in + custom phrase snippets
          │   ├── translation.py    ← zh→en via MyMemory API
          │   └── logger.py         ← file + UI callback logger
          └── ui/
              ├── sidebar.py         ← left panel: history list, search, tags
              ├── main_content.py    ← right panel: prompt input, preview, variants
              ├── app_protocol.py    ← SidebarProtocol, MainContentProtocol
              ├── batch_panel.py     ← 6-cell variant grid
              ├── queue_panel.py     ← sequential generation queue
              ├── viewer.py          ← zoom/pan/crop image viewer
              ├── prompt_wizard.py   ← AI prompt engineering UI
              ├── phrase_panel.py    ← phrase snippet browser
              ├── wizard_free.py     ← free API key config
              ├── wizard_paid.py     ← paid API key config
              └── stats_dashboard.py ← yearly heatmap and statistics
```

**Data flow**: Config loaded once at startup (`App.cfg` dict), passed through every call chain. Services never read config from disk — they receive `cfg` as a parameter. UI panels access `parent_app.cfg` directly. All disk writes go through `save_config()` or `repository.py`.

**Four-layer separation**: Config (settings.py, fonts.py, theme.py, i18n.py) → Data (repository.py) → Services (image_service, providers, assistants) → UI (app.py, panels). Each layer depends only on the layer below it.

**v5.2 Architecture**: App class has been split into modular panels:
- `SidebarProtocol` / `MainContentProtocol` (`ui/app_protocol.py`) define the interfaces panels depend on — decoupling `ui/sidebar.py` and `ui/main_content.py` from `App`'s full surface
- `App` implements both protocols via method forwarding

**End-to-end generation flow**:
1. Read prompt from `self.pt` Text widget, provider from dropdown, size from controls
2. Spawn daemon thread: `has_chinese(prompt)?` → `translate_zh_to_en()` → `generate_image()` → `save_image_file()` → `add_entry()` → `root.after(0, _ok(data, path, used))`
3. `_ok()`: stop progress bar, set preview image, push to viewer if open, refresh history sidebar

---

## Key Directories

|Directory|Purpose|
|---|---|
|`config/`|Path constants, default config dict, font management, theme colors, i18n translations|
|`data/`|SQLite repository — history CRUD, migration from JSON, stats, heatmap|
|`services/`|Business logic — image generation dispatch, AI assistants, translation|
|`services/providers/`|One file per API provider, each exporting a `try_xxx()` function; auto-discovered at import|
|`ui/`|All Tkinter UI — App controller + 10 panel/window modules + Protocol interfaces|
|`tools/`|Build/installer CLI scripts (standalone, not imported by app)|
|`installer/`|Inno Setup template + rendered ISS files + output `.exe`|
|`tests/`|pytest test suite with fixtures for in-memory DB, mock app, and tk root|
|`docs/`|Architecture analysis and code review documentation|
|`开发日志/`|Development logs — refactoring phases, security audits, code review reports|

---

## Development Commands

```bash
# Install dependencies (Python 3.11+)
pip install pillow requests

# Run the application
cd text_to_image
python main.py

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_repository.py -v

# Build Windows installer (requires Inno Setup ISCC on PATH)
python auto_build.py

# Or build installer with custom parameters
python tools/build_inno_installer.py \
  --app-name "Text2Image" --version 2.5.0 \
  --src-dir . --out-dir dist --iscc-path ISCC

# Run pip check (no requirements.txt — list what you have)
pip list
```

**Note**: No `requirements.txt` or `pyproject.toml`. Dependencies are `pillow` (PIL) and `requests`. `tkinter` is stdlib.

---

## Code Conventions & Common Patterns

### Provider Function Contract

Every file in `services/providers/` MUST export exactly one function following the standard contract. Providers are auto-discovered by `services/providers/__init__.py` via `pkgutil.iter_modules` — no manual registration needed.

Each provider module MUST define a `PROVIDER_INFO` dict at module level:

```python
PROVIDER_INFO = {
    "name": "Display Name",
    "category": "free",       # one of: free, paid, commercial
    "config_key": "sf_key",   # config key for API credentials (NOT key_name)
    "description": "Brief description"
}
```

The exported function signature:

```python
def try_<name>(
    prompt: str,       # English prompt
    w: int,            # target width
    h: int,            # target height
    seed: int,         # guaranteed non-None by image_service
    cfg: dict,         # global config (read API keys from cfg["config_key"])
    log: Callable[[str], None]  # logging callback
) -> Tuple[bytes, str]:
    # Returns: (image_bytes, provider_display_name)
    # Raises: ValueError  (missing key / config error — try next provider)
    #         RuntimeError (fatal after retries — try next provider)
    #         TimeoutError (request timed out — try next provider)
```

**Rules**:
- Raise `ValueError` for missing API key or configuration issues
- `image_service.py` catches `(ValueError, RuntimeError, TimeoutError)` — all fall through to next provider
- Import shared HTTP utilities from `services/providers/_net.py` (do NOT duplicate):

```python
from services.providers._net import (
    SESSION as _session,                          # shared requests.Session with connection pooling
    validate_image_url as _validate_image_url,   # SSRF guard — call before downloading any URL from API
    safe_error_text as _safe_error_text,          # extract safe error text from API responses
)
```

### Retry Policy (orchestrator-level)

Provider-level retries are owned by `services/generation/orchestrator.py` +
`services/generation/retry_policy.py` (attempt loop, backoff, cancellation-aware
sleep). Providers themselves only implement inline rate limiting via the
serial-lock pattern below — the former `services/providers/retry.py`
`@with_retries` decorator was removed (zero adopters).

- `max_retries`: maximum retry attempts (default 3)
- `base_delay`: initial wait in seconds (default 3.0)
- `rate_limit_wait`: wait on HTTP 429 (default 30.0)
- `min_interval`: minimum seconds between calls (default 2.0)

### Threading Pattern

All image generation runs in daemon threads. All UI updates **MUST** be dispatched via `root.after(0, callback)` — never mutate tkinter widgets from worker threads.

```python
# Standard pattern
threading.Thread(target=self._gen_worker, daemon=True).start()

# Inside worker: schedule UI updates on main thread
self.root.after(0, lambda: self._status_label.config(text="Done"))
```

### Thread-Local SQLite Connections

`data/repository.py` uses `threading.local()` for per-thread connections to avoid cross-thread sharing:

```python
_thread_local = threading.local()

def _conn() -> sqlite3.Connection:
    if not hasattr(_thread_local, "conn"):
        _thread_local.conn = sqlite3.connect(DB_FILE)
        _thread_local.conn.row_factory = sqlite3.Row
        _thread_local.conn.execute("PRAGMA journal_mode=WAL")
    return _thread_local.conn
```

### Generation Counter (Anti-Race-Condition)

`App._hist_gen` (int) increments on every history refresh. Background thumbnail threads capture `gen` at spawn time and discard results if `gen != self._hist_gen` — prevents stale threads writing to destroyed/recycled tkinter widgets.

### Serial Lock Pattern (Rate Limiting)

Free-tier providers that enforce rate limits use a module-level lock:

```python
_LOCK = threading.Lock()
_LAST_DONE = [0.0]          # mutable list for closure mutation
_MIN_INTV = 2.0             # seconds between calls

with _LOCK:
    gap = time.time() - _LAST_DONE[0]
    if gap < _MIN_INTV:
        time.sleep(_MIN_INTV - gap)
    # ... HTTP request ...
    _LAST_DONE[0] = time.time()
```

Each provider and `translation.py` has its own lock — calls to different providers do not block each other.

### Config Flow

```
load_config() → merges DEFAULT_CONFIG + ~/2image/config.json
   │
   └── App.__init__: self.cfg = load_config()
          │
          └── All panels access parent_app.cfg directly
          └── Wizards: receive cfg.copy() + on_save callback → save_config(cfg)
```

Never read config from disk mid-session — always read from the `cfg` dict in memory. Write through `config.settings.save_config(cfg)`.

Config supports migration via `_migrate_config_v1_to_v2()` called automatically during `load_config()`.

### Logging Pattern

```python
from services.logger import log_to_file, make_log_callback

# File-only logging (default in image_service)
log_cb = log_to_file

# File + UI logging (used in UI code)
log_cb = make_log_callback(lambda msg: self._log_text.insert(tk.END, msg))
```

The `log` callback is a `Callable[[str], None]` threaded through every function in the call chain.

### Naming Conventions

- Provider files: lowercase `snake_case` (`siliconflow.py`, `xai_grok.py`)
- Provider functions: `try_<lowercase_name>` (`try_gemini`, `try_openrouter`)
- UI classes: `PascalCase` (`BatchPanel`, `QueuePanel`, `ConfigWizard`)
- Private helpers: `_underscore_prefixed` (`_gen`, `_refresh_hist`, `_Cell`)
- Config keys: `snake_case` (`sf_key`, `together_key`, `variant_quality`)
- Module-level constants: `UPPER_SNAKE` (`DEFAULT_CONFIG`, `FREE_PROVIDERS`, `_MIN_INTV`)

### Font System

Centralized in `config/fonts.py`. Access via `F` dict after `init_fonts()` is called:

```python
from config.fonts import F
label.config(font=F['body'])       # 13pt sans
title.config(font=F['title'])      # 28pt bold
code.config(font=F['mono'])        # 11pt monospace
```

Font keys: `_sans`, `disp`, `title`, `h1`, `h2`, `btn`, `body`, `body_b`, `body_i`, `small`, `small_b`, `mono`, `mono_tiny`, `mono_sm_b`, `label`, `input`, `tiny`, `tiny_b`, `badge`, `display`.

### Theme / Color System

`config/theme.py` defines a single dark palette (`DARK_THEME`) plus helper utilities. The palette keys:

- `bg` — `#0a0f1a` (background)
- `panel` — `#0d1b2a` (surface)
- `acc` — `#1e3a6a` (accent)
- `hl` — `#e94560` (highlight)
- `text` — `#eaeaea` (primary text)
- `sub` — `#7a8aaa` (subdued)
- `ok` — `#4ecca3` (success)
- `warn` — `#f0a500` (warning)

**Dual theme access pattern** (known inconsistency):
- Most UI files import `DARK_THEME` as a local `C` dict at module level (`from config.theme import DARK_THEME; C = DARK_THEME`)
- `config/theme.py` also exports a global `C` (module-level alias of `DARK_THEME`) for semantic-token access; `config/design_tokens.py` derives `TOKENS` from the theme dict
- `tag_color(tag)` — deterministic hash-based color for tag labels

### i18n System

`config/i18n.py` provides a `_(key, **kwargs)` function with 154 translation keys across 2 locales (`zh-CN`, `en`). Initialize at startup with `init_language(cfg)`. Usage:

```python
from config.i18n import _
label.config(text=_("generate_btn"))
# With formatting: _("gen_count", count=5)
```

Current language is module-global (`_current_lang`). Log messages and provider names are not yet internationalized (known gap).

### Smart Router Pattern

`get_provider_order(prompt, cfg, template_id, fallback_order)` (`services/smart_router.py`) returns a priority-ordered provider list based on:
1. Template ID → scene mapping (`_TEMPLATE_SCENE`)
2. Keyword detection → scene mapping (`_KEYWORD_RULES`)
3. Scene → provider priority list (`_ROUTES`)
4. Filter unavailable paid providers via `_filter_available()`

Fallback order is `DEFAULT_ORDER` (all free providers). Always guarantees at least `Pollinations.AI` is available.

### UI Panel Communication

- All panels store `self.app` (reference to `App` controller) accessed through typed protocols
- `SidebarProtocol` for `ui/sidebar.py`, `MainContentProtocol` for `ui/main_content.py`
- Toplevel windows (ImageViewerWindow, PromptWizard, PhrasePanel) use lazy singleton pattern: `if self._viewer_win is None: create; else: lift()`
- Config wizards receive `(parent, cfg, on_save)` — edit a copy, call `on_save(new_cfg)` on commit
- Panels write to `self.app.pt` (main Text widget) for prompt insertion
- Panels read from `self.app.cfg` for API keys and settings

---

## Important Files

|File|Role|
|---|---|
|`main.py`|Entry point: DPI → fonts → DB init → `tk.Tk` → `App`|
|`config/settings.py`|Path constants (`APP_DIR`, `IMAGES_DIR`, `DB_FILE`), `DEFAULT_CONFIG` dict (all API keys + defaults), `load_config()`/`save_config()`, config v1→v2 migration|
|`config/fonts.py`|Font loading/caching, `F` dict, `init_fonts()`|
|`config/theme.py`|`DARK_THEME` (single dark theme), `tag_color()`, global `C`|
|`config/i18n.py`|`_(key)` translation function, `STRINGS` dict (154 keys, 2 locales), `init_language()`|
|`data/repository.py`|SQLite schema (`history` table: id, timestamp, prompt, translated, image_path, provider, nickname, favorited), tags via junction table (`entry_tags`), full CRUD API, stats, heatmap, JSON→SQLite migration, `_set_test_db()` for in-memory testing|
|`services/image_service.py`|`generate_image()` — iterates providers in order, catches `ValueError`, falls back; `save_image_file()` — saves bytes to disk|
|`services/smart_router.py`|`get_provider_order()` — scene-aware routing: template→scene→providers, keyword detection, filters unavailable paid providers|
|`services/providers/__init__.py`|Auto-discovers all `try_*` functions via `pkgutil.iter_modules`, populates `FREE_PROVIDERS`, `PAID_PROVIDERS`, `COMMERCIAL_PROVIDERS`, `ALL_PROVIDERS`, `DEFAULT_ORDER`|
|`services/generation/orchestrator.py`|Task-level generation orchestration — cancellation/deadline/health/retry/fallback|
|`services/prompt_assistant.py`|`generate_prompt()` — calls DeepSeek V3 via SiliconFlow API; `apply_template()` — template-based prompt; `TEMPLATES` dict (~600 lines)|
|`services/phrase_library.py`|Built-in + custom phrase management, `BUILTIN_PHRASES` (45 phrases, 7 categories)|
|`services/translation.py`|`has_chinese()`, `translate_zh_to_en()` via MyMemory API|
|`services/logger.py`|`log_to_file()`, `make_log_callback()`|
|`ui/app.py`|`App` class — main window controller, owns tk.Tk root, sidebar history, generation orchestration, tag/favorite management|
|`ui/app_protocol.py`|`SidebarProtocol`, `MainContentProtocol` (ABC-like via `typing.Protocol`)|
|`ui/sidebar.py`|`HistorySidebar` — left panel: search, history list with thumbnails, tag editor, favorite toggle|
|`ui/main_content.py`|`MainContent` — right panel: prompt input, preview pane, variant grid container, queue panel, log output, status bar|
|`ui/batch_panel.py`|6-cell variant grid for multi-parameter exploration|
|`ui/queue_panel.py`|Sequential job queue for batch generation|
|`ui/viewer.py`|`ImageViewerWindow` — zoom, pan, crop, save, copy image|
|`main.spec`|PyInstaller spec (console=False, icon set, upx enabled, hiddenimports via `collect_submodules`)|
|`auto_build.py`|Build orchestrator: version read → PyInstaller → Inno Setup → .exe installer|
|`version.json`|`{"version": "2.5.0"}`|
|`tests/conftest.py`|pytest fixtures: `tk_root` (real Tk), `in_memory_db` (SQLite :memory:), `mock_app` (hand-rolled AppProtocol mock)|

---

## Runtime/Tooling Preferences

- **Python**: 3.11+ (uses `ctypes.windll` for DPI awareness — Windows-only)
- **Package manager**: pip (no poetry/pipenv/uv)
- **GUI**: tkinter + ttk (stdlib) — no Qt, wx, or web-based UI
- **Database**: SQLite via stdlib `sqlite3` (no ORM, raw SQL, WAL mode)
- **Packaging**: PyInstaller → single `.exe` → Inno Setup → Windows installer (`text2image_pro_v<ver>.exe`, ~37 MB)
- **Configuration**: JSON file at `~/2image/config.json`
- **Image storage**: `~/2image/images/` (generated images saved as PNG files)
- **Logs**: `~/2image/debug.log`
- **Version**: Managed via `version.json` — read by `auto_build.py` and `tools/build_inno_installer.py`; not auto-incremented; no VCS integration
- **Theme**: Dark by default; `DARK_THEME` is the primary color set; runtime switching supported but requires app restart for full effect

---

## Testing & QA

- **Framework**: pytest（CI 矩阵 3.11/3.12 双版本 + coverage 上报）
- **Test count**: ~514 items across 36 test files（`pytest tests/` 全量约 3 分钟）
- **GUI**: 真实 Tk 会话级共享 root（`tk_session_root`），App 以 Toplevel 承载——规避 Windows 下反复创建/销毁解释器的 Tcl 崩溃

### Test Layout

|Area|Files|What it covers|
|---|---|---|
|Data|`test_repository.py`, `test_search.py`, `test_file_ownership.py`|CRUD、FTS5 搜索、标签、路径穿越防护|
|Generation|`test_orchestrator.py`, `test_router.py`, `test_budget.py`, `test_job_queue.py`, `test_metrics.py`, `test_integration_orchestrator_e2e.py`|编排状态机、场景路由、预算、取消/超时/重试|
|Providers|`test_providers.py`, `test_provider_contract.py`, `test_provider_contract2.py`, `test_new_providers.py`, `test_adapter.py`|契约签名、Key 守卫、SSRF、错误映射|
|UI|`test_protocol_compliance.py`, `test_sidebar_ux.py`, `test_app_layout.py`, `test_language.py`, `test_thumbnail.py`, `test_toast.py` 等|协议一致性 AST 护栏、交互回归、缩略图管线、i18n|
|Infra|`test_config.py`, `test_design_tokens.py`, `test_gap_fixes.py`, `test_fault_injection.py`, `test_performance.py`|配置、令牌、故障注入、性能门槛|

### Fixtures (`tests/conftest.py`)

|Fixture|Scope|Provides|
|---|---|---|
|`isolate_real_config`|**autouse**|所有磁盘写入重定向到 tmp_path（config/db/log/images/词库/spend 台账六处模块全局绑定）|
|`tk_session_root` / `tk_root`|session / alias|会话级共享真实 Tk root|
|`app`|function|Toplevel 承载的完整 App（内存库 + mock 配置读写）|
|`mock_app`|function|手写 AppProtocol mock（`_log_calls`/`_st_calls` 记录）|
|`in_memory_db`|autouse per module|repository 切换 `:memory:` SQLite|

### Testing Patterns

- **隔离硬规则**：测试绝不读写真实用户配置/数据库（见 autouse `isolate_real_config`；2026-10-04 覆写事故的永久加固）
- **unittest.mock 广泛使用**（`@patch` 网络/session）；provider 测试同时用空 `cfg={}` 触发 Key 守卫 `ValueError`
- **协议护栏**：`test_protocol_compliance.py` 以 AST 校验 Protocol 声明、面板 `self.app.*` 引用与 `services/application/` 控制器引用都真实存在于 App
- **UI 测试**：会话级 Tk root + Toplevel 承载 App，组件/布局断言基于真实控件
- 命名：`test_<function_name>_<scenario>`

### Running Tests

```bash
# All tests
pytest tests/ -v

# Single file
pytest tests/test_repository.py -v

# With coverage
pytest tests/ -v --cov=services --cov=config --cov=data --cov-report=term-missing
```

---

## Provider Quick Reference

Registry auto-discovers 23 active providers（`services/providers/__init__.py`）。
可用性判断由 `PROVIDER_KEYS` / `OPTIONAL_KEY_PROVIDERS` / `MULTI_KEY_PROVIDERS` 驱动；
manifest 一致性由 `tests/test_registry_consistency.py` 护栏锁定。

|Tier|Provider|Key in cfg|File|
|---|---|---|---|
|Free|SiliconFlow (★推荐)|`sf_key`|`siliconflow.py`|
|Free|Google Gemini Nano Banana|`gemini_key`|`gemini.py`|
|Free|Pollinations.AI|无（`pollinations_enabled` 开关）|`pollinations.py`|
|Free|Cloudflare AI|`cf_account_id` + `cf_api_token`（双凭证）|`cloudflare_ai.py`|
|Free|ModelsLab|`modelslab_key`|`modelslab.py`|
|Free|Segmind|`segmind_key`|`segmind.py`|
|Free|OpenRouter|`openrouter_key` + `openrouter_model`|`openrouter.py`|
|Free|HuggingFace|`hf_token`|`huggingface.py`|
|Free|StableHorde|`stablehorde_key`（可选，匿名可用）|`stablehorde.py`|
|Free|Together AI|`together_key`|`together_ai.py`|
|Free|阿里云百炼 通义万相|`dashscope_key`|`dashscope_qwen.py`|
|Free|Bria AI|`bria_key`|`bria_ai.py`|
|Paid|OpenAI GPT-Image|`openai_key` + `gpt_image_model`|`openai_image.py`|
|Paid|Stability AI|`stability_key` + `stability_model`|`stability_ai.py`|
|Paid|Replicate FLUX|`replicate_key` + `replicate_model`|`replicate_flux.py`|
|Paid|xAI Grok|`xai_key`|`xai_grok.py`|
|Paid|BFL（FLUX 官方）|`bfl_key` + `bfl_model`|`bfl_flux.py`|
|Paid|Gemini Nano Banana Pro|`gemini_key`（与 gemini 共用）|`gemini_nano_banana_pro.py`|
|Commercial|Ideogram|`ideogram_key`|`ideogram.py`|
|Commercial|fal.ai FLUX Ultra|`fal_key`|`fal_flux.py`|
|Commercial|Recraft|`recraft_key` + `recraft_style` + `recraft_model`|`recraft.py`|
|Commercial|MiniMax Image|`minimax_key`|`minimax_image.py`|
|Commercial|火山引擎 豆包 Seedream|`volcengine_key` + `ark_model`|`volcengine_ark.py`|

---

## Adding a New Provider

1. Create `services/providers/<name>.py` with:
   - `PROVIDER_INFO` dict (`name`, `category`, `config_key`, `description`)
   - Import from `services/providers/_net.py`: `SESSION`, `validate_image_url`, `safe_error_text`
   - `try_<name>(prompt, w, h, seed, cfg, log) -> (bytes, str)` function
   - Raise `ValueError` on missing key; call `validate_image_url()` before downloading any URL from the API response
2. No manual registration needed — `services/providers/__init__.py` auto-discovers via `pkgutil.iter_modules`
3. Add config key to `DEFAULT_CONFIG` in `config/settings.py`
4. Add wizard UI card in `ui/wizard_free.py` or `ui/wizard_paid.py`
5. If commercial tier: use `try/except ImportError` wrapper in `__init__.py` (see `ideogram.py` pattern) so app starts even if import fails
6. Add entry to `_KEY_MAP` in `services/smart_router.py` if paid/commercial, and to `_ROUTES` for scene-based routing

---

## Build Process

```bash
# Manual build
python auto_build.py

# Under the hood:
# Step 1: get_version() reads version.json
# Step 2: pyinstaller_build() runs PyInstaller --onefile --icon=ICON_256x256.ico
# Step 3: inno_setup_build() renders template.iss → writes auto_<ver>.iss → runs ISCC
# Step 4: update_version() writes version.json

# Custom build
python tools/build_inno_installer.py \
  --app-name "Text2Image" --version 2.5.0 \
  --src-dir . --out-dir dist --iscc-path "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

### Build Outputs

|Artifact|Location|
|---|---|
|PyInstaller .exe|`dist/main.exe`|
|Inno Setup .iss|`installer/auto_<version>.iss`|
|Windows installer|`installer/Output/text2image_pro_v<version>.exe` (~37 MB)|

### Known Build Gaps

- `main.spec` has empty `hiddenimports` — may miss `PIL._imagingtk` on some systems

- `main.spec` has empty `datas` — no non-Python assets bundled

- `console=False` — release builds are windowed; `print()` output in `main.py` is invisible in packaged builds (write to LOG_FILE instead)

### Git 提交规则

  - commit message 中禁止包含任何 `Co-Authored-By` 署名（包括但不限于 Claude、Anthropic、noreply@anthropic.com 等任何 AI 相关署名）

  - 所有提交仅保留用户本人的 git 作者信息（`用户名 <邮箱>`）

  - 创建 PR 时同样不添加任何 AI 合作者信息

### 仓库管理硬性规则（永远不可违反）

  - **禁止修改公共仓库的可见性**：不得将任何公开（public）仓库切换为私有（private）或内部（internal），即使是为了清除 contributor 缓存、刷新索引或其他任何原因。此操作会导致 star 和 fork 数据永久丢失。

  - **禁止通过 `gh repo edit --visibility` 切换任何仓库的可见性**：除非用户明确要求且已书面确认接受丢失 star/fork 的后果。

  - **禁止通过其他任何手段（API、浏览器设置等）修改仓库可见性**：本规则覆盖所有可能的可见性修改方式。
