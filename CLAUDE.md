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

# Build Windows installer (update hardcoded PROJECT_DIR in auto_build.py first)
python auto_build.py
```

Dependencies: `pip install pillow requests pytest`

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

### Provider system

Providers live in `services/providers/`. Each file exports a `PROVIDER_INFO` dict and a `try_<name>()` function — `__init__.py` auto-discovers them via `pkgutil`, no manual registration needed.

```python
PROVIDER_INFO = {
    "name": "Display Name",
    "category": "free",   # free | paid | commercial
    "config_key": "sf_key",
}

def try_xxx(prompt: str, w: int, h: int, seed: int, cfg: dict, log: Callable) -> Tuple[bytes, str]:
    # Returns (image_bytes, provider_display_name)
    # Raises ValueError on failure (scheduler falls through to next provider)
```

Every provider must implement a module-level rate-limit lock (`_last_call` + `_lock = threading.Lock()`).

`image_service.generate_image()` iterates `DEFAULT_ORDER` (all free providers), catches `ValueError` and falls through. Pass `provider_order=` to override.

`services/smart_router.py` maps intent keywords / template IDs to optimized provider sequences — use `get_provider_order(prompt, cfg, template_id=...)` before calling `generate_image`.

### Config and theming

- All UI modules import colors from `config/theme.py` as `DARK_THEME as C` — never hardcode hex values.
- All user-visible strings go through `config/i18n.py` as `_("key")`.
- New provider config keys must be added to `DEFAULT_CONFIG` in `config/settings.py` so `load_config()` backfills them on upgrade.

### Database

Thread-local SQLite connections via `_conn()` in `data/repository.py`. Schema upgrades use `ALTER TABLE` in `init_db()` (no migration files). PNG metadata (prompt, seed, provider) is embedded in image files at save time.

### Prompt optimization

`services/prompt_assistant.py` calls DeepSeek V3 through SiliconFlow's LLM endpoint — requires only `sf_key`, no separate DeepSeek key. Fallback: HuggingFace `hf_token`. Translation uses MyMemory public API (no key).

## Key invariants

- Providers raise `ValueError` on failure, never return `None`.
- `image_service.generate_image()` raises `RuntimeError` only when all providers fail.
- Internal/reserved IPs are blocked in providers that fetch remote URLs (SSRF guard — see `_validate_image_url` in `siliconflow.py` as the reference pattern).
- `auto_build.py` has a hardcoded `PROJECT_DIR` — update before running on a new machine.
