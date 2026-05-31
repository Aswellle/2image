"""Tests for config loading edge cases."""
import json
import os
import tempfile
import pytest
from unittest.mock import patch


def test_load_config_corrupt_json_falls_back_to_defaults():
    """Corrupt JSON config must fall back to defaults without crashing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json',
                                     delete=False) as f:
        f.write("{invalid json ][")
        tmp = f.name
    try:
        with patch('config.settings.CONFIG_FILE', tmp):
            from config.settings import load_config, DEFAULT_CONFIG
            cfg = load_config()
        assert cfg["config_version"] == DEFAULT_CONFIG["config_version"]
        assert cfg["sf_key"] == ""
    finally:
        os.unlink(tmp)


def test_load_config_empty_file_falls_back_to_defaults():
    """Empty config file must fall back to defaults."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json',
                                     delete=False) as f:
        f.write("")
        tmp = f.name
    try:
        with patch('config.settings.CONFIG_FILE', tmp):
            from config.settings import load_config
            cfg = load_config()
        assert cfg["language"] == "zh-CN"
        assert "sf_key" in cfg
    finally:
        os.unlink(tmp)


def test_load_config_missing_keys_backfilled_from_defaults():
    """Partial config must be backfilled with DEFAULT_CONFIG values."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json',
                                     delete=False) as f:
        json.dump({"sf_key": "abc123", "config_version": 2}, f)
        tmp = f.name
    try:
        with patch('config.settings.CONFIG_FILE', tmp):
            from config.settings import load_config
            cfg = load_config()
        assert cfg["sf_key"] == "abc123"
        assert "gemini_key" in cfg       # backfilled
        assert "openai_key" in cfg       # backfilled
        assert cfg["language"] == "zh-CN"  # backfilled
    finally:
        os.unlink(tmp)


def test_save_config_atomic_write_creates_valid_json():
    """save_config must produce a valid JSON file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_config = os.path.join(tmpdir, "config.json")
        with patch('config.settings.CONFIG_FILE', tmp_config), \
             patch('config.settings.APP_DIR', tmpdir):
            from config.settings import save_config, load_config
            save_config({"sf_key": "test_key", "config_version": 2})
            assert os.path.exists(tmp_config)
            cfg = load_config()
            assert cfg["sf_key"] == "test_key"
