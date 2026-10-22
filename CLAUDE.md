# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup and run (Python 3.11+)
pip install -r requirements.txt
python main.py

# Tests (pytest; ~620 tests across 41 modules, ~4 min full run)
pytest tests/ -v --tb=short
pytest tests/test_providers.py -v
pytest tests/test_providers.py::test_gemini_missing_key_raises_valueerror -v
pytest tests/ -v --cov=services --cov=data --cov=config --cov-fail-under=68

# Lint — the CI blocking gate is F821/E9 only
ruff check main.py config/ data/ services/ ui/ tools/ tests/ --select F821,E9
ruff check main.py config/ data/ services/ ui/ tools/ tests/ --select F401,F841,E402   # non-blocking in CI
ruff format --check main.py config/ data/ services/ ui/ tools/ tests/                 # non-blocking

# i18n gates (both blocking in CI)
python tools/check_i18n.py --missing-keys
python tools/check_i18n.py --hardcoded --baseline tools/i18n_baseline.json
python tools/check_i18n.py --update-baseline tools/i18n_baseline.json   # after intentionally adding strings

# Build portable exe + Windows installer (needs PyInstaller + Inno Setup 6's ISCC on PATH)
python auto_build.py

# Verify a release tag is internally consistent (tag ↔ version.json ↔ release notes)
python tools/verify_release_version.py --tag v2.7.2
```

`pyproject.toml` configures only pytest, ruff, and coverage. mypy, pip-audit, and `ruff format` are CI-only steps invoked with CLI flags in `.github/workflows/ci.yml`, and all three are `continue-on-error` — only ruff F821/E9, the two i18n gates, and the coverage floor of 68 actually fail a build.

## Architecture

Windows-only desktop text-to-image app: Python 3.11 + Tkinter, no web layer, no ORM.

```text
main.py  (DPI awareness → fonts → legacy-data migration → SQLite init → App)
  ├─ config/     settings · theme · design_tokens · i18n · fonts · model_catalog
  ├─ data/       repository (SQLite) · search (FTS5) · file_ownership
  ├─ services/   generation/ · providers/ · application/ · updater/ · translation/ · logger/
  └─ ui/         app.py coordinator + panels/dialogs
```

Intended dependency direction is `ui → services → data → config`. One deliberate exception: `services/application/` holds the three UI controllers (`GenerationController`, `MenuController`, `SettingsController`) that were extracted out of `ui/app.py` to slim it down. They import Tkinter and message boxes, so they are UI code living one layer too low. This is a **deliberate, deferred refactor** — the rationale is inlined here because `docs/` is gitignored and therefore absent from a fresh clone: the controllers were extracted to keep `App` navigable, the move back into `ui/` is gated on the functional-stability conditions in `docs/structural-refactor-backlog.md` (local-only), and until that lands, **do not add a fourth controller there** — put new UI code in `ui/`.

### Key modules

| Path | Role |
|---|---|
| `main.py` | Entry point only: DPI, fonts, data migration, DB init, `App(root)` |
| `ui/app.py::App` | Coordinator: layout, sash, hotkeys, viewer/toast wiring, update check |
| `ui/main_content.py` | Prompt box, provider dropdown, size control, preview, tabs |
| `ui/sidebar.py` | History list, tag filters, favorites, thumbnails |
| `ui/app_protocol.py` | `SidebarProtocol` / `MainContentProtocol` — panels depend on these, never on `App` |
| `services/image_service.py` | `generate_image()` — the single generation entry point |
| `services/generation/orchestrator.py` | Provider chain: retry, circuit-breaking, fallback decisions |
| `services/generation/errors.py` | `ProviderError` taxonomy — the only retry/fallback signal |
| `services/generation/router.py` | Health-aware routing (`get_provider_order`) |
| `services/generation/scenes.py` | Scene → provider order, keyword/template → scene (pure data) |
| `services/generation/provider_manifest.py` | Stable-ID provider metadata used by routing |
| `services/providers/__init__.py` | pkgutil auto-discovery, `ALL_PROVIDERS`, `DEFAULT_ORDER` |
| `services/providers/_net.py` | Shared HTTP: thread-local session, SSRF-validated download, error text |
| `services/generation/budget.py` | Paid-spend ledger + daily budget guard |
| `services/updater/` | Self-update: version → manifest → download → verify → install → confirm |
| `services/translation/` | zh→en via MyMemory, rate-limited and cancellable |
| `config/model_catalog.py` | Single source for per-family model lists and defaults |

`services/smart_router.py` is a **backward-compat shim only** — production code imports `services.generation.router`. Likewise `services/generation/job_queue.py` is a state-machine/metrics library whose `_process_job` is a placeholder; the real sequential queue is `ui/queue_panel.py`.

### Generation flow

1. UI (`GenerationController`, `BatchPanel`, `QueuePanel`) translates Chinese prompts, then calls `generate_image(prompt, w, h, seed, cfg, provider_order=..., token=...)`.
2. `generate_image()` builds the provider map: the requested order first, then every other provider as a fallback — **filtered** to those with configured keys, and to free providers unless `paid_auto_opt_in` is set and the daily budget is not exhausted. Each provider is wrapped by `_wrap_provider_fn`, which maps `requests` exceptions and plain-text messages onto the `ProviderError` taxonomy.
3. `GenerationOrchestrator.run()` walks the order: checks `CancellationToken`/`Deadline`, skips providers whose circuit breaker is OPEN, retries `retryable` errors per `RetryPolicy`, and stops the whole chain when a `fallback=False` error appears.
4. On success it records paid spend, then `save_image_file()` writes a UUID-named PNG with metadata, and the caller inserts a history row.

Cancellation is cooperative: `CancellationToken` is checked between providers and inside retry waits, and is injected into `cfg["_cancel_check"]` so polling providers (submit-then-poll, up to 6 minutes) abort immediately instead of timing out.

## Provider system

`services/providers/__init__.py` discovers every module in the package via `pkgutil`. A module must define `PROVIDER_INFO` and a matching `try_<module_name>()` (override with `PROVIDER_INFO["try_fn"]`). Discovery is defensive: a module that fails to import, or lacks its declared function, prints `[warn]` and is skipped — a broken provider degrades the chain, it does not crash startup.

```python
PROVIDER_INFO = {
    "id": "my_provider",          # stable ID — the key in ALL_PROVIDERS and all routing
    "name": "Display name",       # UI only; must equal ProviderManifest.name
    "category": "free",           # free | paid | commercial
    "config_key": "my_key",       # None when no key is required
    "key_optional": False,        # True when an empty key is still usable (StableHorde)
    "extra_config_keys": (),      # additional required credentials (Cloudflare)
    "supports_img2img": False,
    # "try_fn": "try_custom_name",
}

def try_my_provider(prompt, w, h, seed, cfg, log) -> tuple[bytes, str]:
    ...
```

Rules that the tests enforce or rely on:

- **Two registries must stay in lockstep.** `PROVIDER_INFO` feeds runtime dispatch; `services/generation/provider_manifest.py` feeds routing metadata (category, `supports_img2img`, capabilities). `tests/test_registry_consistency.py` asserts IDs, names, categories, config keys, and tier membership match — but **not** `supports_img2img`, which has already drifted: four modules (`gemini`, `openai_image`, `minimax_image`, `volcengine_ark`) read `cfg["_ref_image"]` and are flagged in the manifest, yet omit the key from `PROVIDER_INFO`, so `IMG2IMG_PROVIDERS` (built solely from that key) excludes them and they never reach the img2img UI. Set the flag in both places; the manifest also carries no production reader (`Router` is test-only), so treat `PROVIDER_INFO` as the live source of truth.
- **Raise `ValueError`** for expected failures; the orchestrator classifies them. Never return `None`.
- **Use the shared network layer**: `get_session()` (thread-local), `safe_get_image()` (SSRF + 25 MB cap + redirect validation), `safe_error_text()`, `read_bounded()`, `raise_if_cancelled(cfg)`.
- **Serial lock per module** — one `_LOCK` + `_LAST_DONE` pair, held across the network call, so concurrent batch calls to the same free tier don't trip rate limits. 18 of 23 providers implement it; `siliconflow`, `openai_image`, `stability_ai`, `replicate_flux`, and `cloudflare_ai` do not, and no test enforces it. New providers must copy the pattern.
- New config keys go in `DEFAULT_CONFIG` (`config/settings.py`); discovery then populates `PROVIDER_KEYS`, which routing and the UI treat as the source of truth.

`DEFAULT_ORDER` in `services/providers/__init__.py` is the sole fallback order — an explicit list, deliberately not pkgutil order. `provider_manifest.py` carries identity/routing metadata only; it has no order list.

## Configuration and persistence

All user data lives in `~/2image/` (`config/settings.py::APP_DIR`), not the legacy `~/.text_to_image_app/` — `migrate_legacy_data()` copies the old directory once on first launch and leaves it as a backup.

| File | Contents |
|---|---|
| `config.json` | Flat provider keys + preferences |
| `history.db` | SQLite: `history`, `tag`, `entry_tag` tables + FTS5 index |
| `images/` | PNGs, `YYYY/MM/DD/<uuid>.png` |
| `fonts/` | JetBrains Mono cache (SHA-256-pinned jsDelivr download; system-font fallback) |
| `spend.json` | Daily paid-spend ledger for the budget guard |
| `debug.log` | Rotating app log (5 MB) |

`load_config()` backfills missing keys from `DEFAULT_CONFIG`, migrates old `config_version`s, then applies `TEXTIMG_<CONFIG_KEY>` environment overrides (type-coerced against the default's type). `save_config()` is the only writer and uses atomic replace.

Two config subtleties:

- **`variant_quality` vs `variant_hq`.** `DEFAULT_CONFIG` stores `variant_quality: "high" | "standard"`. Providers read `cfg["variant_hq"]`; `ui/batch_panel.py` injects that transient flag into a copy of the config when quality is `high`. Do not add `variant_hq` to `DEFAULT_CONFIG` — it is a per-request marker, not a setting.
- **Paid safety.** `paid_auto_opt_in` (default `False`) gates whether paid/commercial providers may appear in *automatic* routing at all; `paid_daily_budget_usd` (default 2.0, `0` = unlimited) additionally removes them once estimated spend is reached. Explicit user selection bypasses auto-routing but is still blocked by the budget check in `GenerationController._precheck_provider`.

`data/repository.py` uses a thread-local SQLite connection (WAL, `busy_timeout`), versioned migrations via `_MIGRATIONS`, and `ALTER TABLE` backfills for older schemas. Deleting an image must go through `data/file_ownership.safe_owned_image_path()`.

## UI conventions

- Every user-visible string goes through `_()` from `config/i18n.py`; locales are `zh-CN` and `en` only. `tools/check_i18n.py --hardcoded` scans `ui/` and `services/application/` and fails on any Chinese string not in `tools/i18n_baseline.json` — so new UI text needs a key, not a literal.
- Colors come from `config/theme.py::DARK_THEME` (imported as `C`). `config/design_tokens.py::TOKENS` is derived from it for semantic names; do not introduce a third color map.
- Long-running work runs in daemon threads; every Tk call from a worker must be marshalled with `root.after(0, ...)`.
- Panels receive the coordinator through `SidebarProtocol`/`MainContentProtocol`. `tests/test_protocol_compliance.py` AST-scans every panel's `self.app.X` references and fails if `App` no longer provides them — this exists because a v2.4.0 refactor deleted a method the protocol still promised and the packaged app crashed on launch.

## Testing

- `tests/conftest.py::isolate_real_config` is **autouse**: it redirects config, DB, log, images, phrase-library, and spend-ledger paths into `tmp_path`. Never write to the real `~/2image/` from a test (a 2026-10-04 incident overwrote a user's config).
- `tk_session_root` / `tk_root` share one Tk interpreter for the whole session — destroying it causes Tcl C-level crashes on Windows. The `app` fixture hosts `App` in a `Toplevel` instead.
- Other fixtures: `in_memory_db`, `mock_app`, and `tests/fakes/` (scriptable provider outcomes, fake HTTP) for deterministic orchestrator/fallback tests.
- GUI tests use `skip_if_no_tk`; headless environments skip rather than fail.

## Release process

1. Bump `version.json` (SemVer; MINOR for new subsystems, PATCH for fixes).
2. Write `release-notes/v<version>.md` following `release-notes/TEMPLATE.md` — Chinese, user-facing, ending with the compare link.
3. Commit, tag `v<version>`, push the tag.

CI then runs the quality gates → Windows test matrix (3.11/3.12) → build. The build step calls `tools/verify_release_version.py` (tag ↔ `version.json` ↔ notes must agree), builds with `auto_build.py`, generates `update.json` + `SHA256SUMS.txt` + SBOM from the real artifacts, and only then creates the GitHub Release. `update.json` is the in-app updater's only channel — never hand-edit it.

## Gotchas

- `console=False` in `main.spec`: `print()` is invisible in packaged builds. Log through `services/logger.py` instead.
- `services/logger.log_to_file()` is asynchronous (queue + writer thread). Use `flush_logs()` in tests or on exit.
- Provider display names are UI-only; `resolve_provider_id()` maps legacy display names to stable IDs. The UI dropdown and all routing now use stable IDs.
- `auto_build.py` deletes and recreates `build/` and `dist/`; artifacts are `dist/2image.exe` and `installer/Output/2image-setup-v<ver>.exe`.
- `main.spec` collects provider submodules into `hiddenimports`; a new top-level package needs the same treatment or it will be missing from the packaged exe.
- `AGENTS.md` is a much longer companion reference (provider quick-reference table, build internals, review history). It drifts more slowly than this file — verify specific numbers against the code.

## Git rules

- Commit messages must not contain any `Co-Authored-By` line, including Claude/Anthropic/noreply@anthropic.com or any other AI attribution. Commits carry only the user's own author identity.
- PRs must not list AI collaborators.
- Never change a public repository's visibility (public → private/internal), by `gh repo edit --visibility` or any other means — it permanently destroys stars and forks.
