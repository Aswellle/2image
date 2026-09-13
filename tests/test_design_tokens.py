"""
tests/test_design_tokens.py — Design tokens and SBOM tests
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from config.design_tokens import (
    LIGHT_TOKENS,
    TOKENS,
    DesignTokens,
    button_colors,
    status_pill_colors,
)


class TestDesignTokens:
    def test_dark_theme_colors(self):
        assert TOKENS.surface_app == "#0a0f1a"
        assert TOKENS.text_primary == "#eaeaea"
        assert TOKENS.accent == "#1e3a6a"

    def test_light_theme_colors(self):
        assert LIGHT_TOKENS.surface_app == "#f5f7fa"
        assert LIGHT_TOKENS.text_primary == "#1a1a2e"

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
