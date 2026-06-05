# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
python main.py

# Run tests
pytest tests/
pytest tests/test_providers.py          # single file
pytest tests/ -k "siliconflow"          # filter by name

# Lint (catches undefined names + syntax errors — run alongside tests)
ruff check services/ ui/ config/ data/ tests/ --select F821,E9

# Build Windows installer
python auto_build.py
```

Dependencies: `pip install -r requirements.txt`

## Architecture

4-layer separation: `config/` → `data/` → `services/` → `ui/`. Layers only import downward.

```
main.py
  → config/fonts.py          # font init + background download
  → data/repository.py       # SQLite (thread-local connections, WAL mode)
  → ui/app.py (App)          # coordinator; delegates rendering to:
        ui/sidebar.py        # HistorySidebar (history list, filters)
        ui/main_content.py   # MainContent (prompt input, generation controls)
        ui/viewer.py         # standalone image viewer (zoom/pan)
        ui/batch_panel.py    # batch variant generation
        ui/phrase_panel.py   # phrase library
        ui/prompt_wizard.py  # AI prompt optimization (DeepSeek V3 via sf_key)
        ui/wizard_free.py    # free provider key config UI
        ui/wizard_paid.py    # paid provider key config UI
        ui/stats_dashboard.py
```

UI panels interact with `App` only through the `SidebarProtocol` / `MainContentProtocol` interfaces defined in `ui/app_protocol.py` — never importing `App` directly. Tests inject `MockApp` from `tests/conftest.py`.

### Provider system

Providers live in `services/providers/`. Each file exports a `PROVIDER_INFO` dict and a `try_<name>()` function — `__init__.py` auto-discovers them via `pkgutil`, no manual registration needed.

```python
PROVIDER_INFO = {
    "name": "Display Name",
    "category": "free",   # free | paid | commercial
    "config_key": "sf_key",
    # "try_fn": "custom_fn_name",  # optional; defaults to try_<module_name>
}

def try_xxx(prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable) -> Tuple[bytes, str]:
    # Returns (image_bytes, provider_display_name)
    # Raises ValueError on failure (scheduler falls through to next provider)
```

Every provider must:
- Handle rate limiting with a module-level `_last_call = [0.0]` + `_lock = threading.Lock()` pattern. Acquire the lock, sleep if needed, then release before making the HTTP call.
- Use `SESSION` from `services/providers/_net.py` for HTTP requests (shared connection pool).
- Use `safe_get_image(url)` from `_net.py` to download API-returned image URLs — this performs SSRF validation (DNS-resolved IP range checks) and redirect-following checks.
- Use `safe_error_text(resp)` from `_net.py` to extract error messages from API responses.

`PROVIDER_INFO["config_key"]` feeds into `PROVIDER_KEYS` (exported from `services/providers/__init__.py`), which is the single source of truth for which config dict key a provider requires. `smart_router.py` and the status bar derive their key maps from `PROVIDER_KEYS` — don't hardcode a separate copy.

img2img mode: `generate_image()` accepts `ref_image: bytes | None` and `strength: float`. If `ref_image` is set, a copy of `cfg` is passed to providers with `_ref_image` and `_ref_strength` keys; providers that support img2img should read those keys. The original `cfg` is never mutated.

`image_service.generate_image()` iterates `DEFAULT_ORDER` (all free providers), catches `ValueError`/`RuntimeError`/`TimeoutError` and falls through. Pass `provider_order=` to override.

`services/smart_router.py` maps intent keywords / template IDs to optimized provider sequences — use `get_provider_order(prompt, cfg, template_id=...)` before calling `generate_image`. It auto-filters providers whose config keys are missing and always guarantees a non-empty list (falls back to Pollinations.AI).

### Config and theming

- All UI modules import colors from `config/theme.py` as `DARK_THEME as C`. New code that needs runtime theme switching can import the module-level `C` dict and call `apply_theme(name)`.
- All user-visible strings go through `config/i18n.py` as `_("key")`. Supports `zh-CN` (default), `zh-TW`, `en`. Call `init_language(cfg)` on startup; use `_("key", param=val)` for formatted strings.
- New provider config keys must be added to `DEFAULT_CONFIG` in `config/settings.py` so `load_config()` backfills them on upgrade. `load_config()` handles `config_version` migrations internally.

### Database

Thread-local SQLite connections via `_conn()` in `data/repository.py`. Schema upgrades use `ALTER TABLE` in `init_db()` (no migration files). PNG metadata (prompt, seed, provider) is embedded in image files at save time.

Three fixtures in `tests/conftest.py`:
- `in_memory_db` — calls `repository._set_test_db(":memory:")` for repository tests
- `mock_app` — minimal `MockApp` satisfying `SidebarProtocol`/`MainContentProtocol` for panel tests
- `tk_root` — creates and tears down a real `tk.Tk()` instance for widget tests

### Prompt optimization

`services/prompt_assistant.py` calls DeepSeek V3 through SiliconFlow's LLM endpoint — requires only `sf_key`, no separate DeepSeek key. Fallback: HuggingFace `hf_token`. Translation uses MyMemory public API (no key).

## Key invariants

- Providers raise `ValueError` on failure, never return `None`.
- `image_service.generate_image()` raises `RuntimeError` only when all providers fail.
- All providers that download external URLs must use `safe_get_image()` from `services/providers/_net.py` — never call `validate_image_url()` manually followed by a raw `requests.get()`, because that pattern is vulnerable to TOCTOU on redirects.
- `auto_build.py` has a hardcoded `PROJECT_DIR` — update before running on a new machine.
