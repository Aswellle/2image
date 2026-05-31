# Changelog

## [1.3.0] — 2026-05-31

### Security
- Remove two committed OpenRouter API keys from README.md (revoke at openrouter.ai/keys)
- Fix SSRF guard: centralize `validate_image_url()` in `_net.py` using DNS resolver (was failing open for hostname-based URLs)
- Fix SSRF via HTTP redirect: add `safe_get_image()` that validates every redirect target before following
- Fix scheduler to catch `(ValueError, RuntimeError, TimeoutError)` so SSRF blocks degrade gracefully instead of aborting generation

### Architecture
- Create `services/providers/_net.py`: shared `SESSION`, `validate_image_url()`, `safe_get_image()`, `safe_error_text()`
- Migrate all 17 providers to import from `_net.py` (eliminated ~400 LOC of duplicated HTTP boilerplate)
- Build `PROVIDER_KEYS` dict in registry during auto-discovery; `smart_router.py` derives `_KEY_MAP` and `_FREE_PROVIDERS` from it (no more hardcoded maps)

### Performance
- `sidebar.py`: push `LIMIT/OFFSET` into SQL query (fetch 101 rows max instead of all rows Python-side)
- `pollinations.py`: release lock before HTTP call — batch N-thread generation now truly concurrent
- `config/theme.py`: `C = DARK_THEME` (same object, not `.copy()`) — theme switching works correctly

### Fixes
- `update_tags()`: add `c.commit()` (data was silently discarded on cross-thread reads)
- `save_config()`: atomic write via temp file + `os.replace()` (prevents data loss on power failure)
- `auto_build.py`: replace hardcoded `PROJECT_DIR` with `Path(__file__).resolve().parent`
- Fix 8 `open()` without context manager (file handle leaks on Windows)
- Fix `os.system(f"xdg-open '{path}'")` → `subprocess.Popen(["xdg-open", path])` (shell injection)
- Fix `config/settings.py`: surface corrupt config warning instead of silent fallback
- Fix 6 bare `except:` → `except Exception:` in `stats_dashboard.py` and `prompt_wizard.py`
- Fix `tag_color()`: use `hashlib.md5` instead of `sum(ord())` (eliminates anagram collisions)

### Testing
- 40 tests (was 19): add parametrized missing-key tests for 12 providers, scheduler fallback tests (RuntimeError/TimeoutError), IPv6 SSRF tests (IPv4-mapped), config corruption tests
- Add `pyproject.toml` with pytest + coverage config

### Docs
- Fix `AGENTS.md`: `config_key` (not `key_name`), correct `with_retries` params, add `_net.py` import step
- Add `requirements.txt` (Pillow>=10.3.0, requests>=2.32.3)

## [1.2.1] — 2026-03 (pre-refactor baseline)

- Initial multi-provider text-to-image desktop app
- 17 AI image generation provider integrations
- SQLite history, batch variant generation, AI prompt optimization
- Phrase library, smart routing, Windows installer build tooling
