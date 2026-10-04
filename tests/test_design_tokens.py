"""
tests/test_design_tokens.py — Design tokens and SBOM tests
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from config.design_tokens import (
    TOKENS,
    DesignTokens,
    button_colors,
    derive_tokens_from_theme,
    status_pill_colors,
    sync_tokens_from_theme,
)
from config.theme import DARK_THEME, init_theme

import re

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class TestDesignTokens:
    def test_tokens_derive_from_dark_theme(self):
        assert TOKENS.surface_app == DARK_THEME["bg"]
        assert TOKENS.text_primary == DARK_THEME["text"]
        assert TOKENS.accent == DARK_THEME["acc"]

    def test_semantic_alias_keys_exist(self):
        """语义令牌别名键必须齐全（暗色单主题）。"""
        for key in ("surface", "surface_raised", "surface_hover",
                    "surface_selected", "accent", "accent_hover",
                    "success", "danger", "warning", "divider",
                    "text_primary", "text_secondary", "text_muted",
                    "text_inverse", "surface_disabled", "text_disabled"):
            assert key in DARK_THEME, f"DARK_THEME 缺少语义键 {key}"

    def test_all_colors_valid_hex(self):
        for key, val in DARK_THEME.items():
            assert _HEX_RE.match(val), f"DARK_THEME.{key} = {val!r} 不是 #rrggbb"

    def test_init_theme_resyncs_tokens(self):
        TOKENS.accent = "#000000"   # 模拟外部篡改
        init_theme({})
        assert TOKENS.accent == DARK_THEME["acc"]

    def test_derive_tokens_from_theme(self):
        t = derive_tokens_from_theme(DARK_THEME)
        assert t.accent == DARK_THEME["acc"]
        assert t.success == DARK_THEME["ok"]

    def test_sync_in_place_keeps_identity(self):
        t = DesignTokens()
        before = id(t)
        sync_tokens_from_theme(t, DARK_THEME)
        assert id(t) == before
        assert t.surface_app == DARK_THEME["bg"]

    def test_spacing_scale(self):
        assert TOKENS.space_xs < TOKENS.space_sm < TOKENS.space_md

    def test_get_method(self):
        assert TOKENS.get("accent") == TOKENS.accent
        assert TOKENS.get("nonexistent", "default") == "default"


class TestButtonColors:
    def test_primary_normal(self):
        colors = button_colors("normal", "primary")
        assert "bg" in colors
        assert "fg" in colors

    def test_danger_variant(self):
        colors = button_colors("normal", "danger")
        assert colors["bg"] == TOKENS.danger

    def test_disabled_state(self):
        colors = button_colors("disabled", "primary")
        assert colors["fg"] == TOKENS.text_muted

    def test_unknown_state_defaults(self):
        colors = button_colors("unknown", "primary")
        assert colors["bg"] == TOKENS.accent


class TestStatusPillColors:
    def test_info(self):
        colors = status_pill_colors("info")
        assert colors["bg"] == TOKENS.info

    def test_success(self):
        colors = status_pill_colors("success")
        assert colors["bg"] == TOKENS.success

    def test_unknown_defaults_to_info(self):
        colors = status_pill_colors("unknown")
        assert colors["bg"] == TOKENS.info


class TestSBOMGeneration:
    def test_sbom_generates_files(self):
        from tools.generate_sbom import generate_sbom

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake version.json
            version_file = os.path.join(tmpdir, "version.json")
            with open(version_file, "w") as f:
                json.dump({"version": "9.9.9"}, f)

            out_dir = os.path.join(tmpdir, "dist")
            os.makedirs(out_dir, exist_ok=True)

            # Change to temp dir for git commands
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # Init a git repo so get_git_sha works
                os.system("git init -q")
                os.system("git config user.email test@test.com")
                os.system("git config user.name test")
                os.system("git add .")
                os.system("git commit -q -m init")

                meta = generate_sbom(tmpdir, out_dir)
                assert meta["version"] == "9.9.9"
                assert os.path.exists(os.path.join(out_dir, "build-metadata.json"))
                assert os.path.exists(os.path.join(out_dir, "SBOM.spdx.json"))

                # Verify SBOM structure
                with open(os.path.join(out_dir, "SBOM.spdx.json")) as f:
                    sbom = json.load(f)
                assert sbom["spdxVersion"] == "SPDX-2.3"
                assert len(sbom["packages"]) > 0
            finally:
                os.chdir(old_cwd)
