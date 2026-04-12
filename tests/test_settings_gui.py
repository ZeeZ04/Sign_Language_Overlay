"""Tests for the settings GUI module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from src.settings_gui import SettingsGUI


class TestSettingsConfig:
    def test_load_config_from_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump({"language": "bsl", "display": {"size": 300}}, f)
            f.flush()
            gui = SettingsGUI(config_path=f.name)
            config = gui.load_config()
            assert config["language"] == "bsl"
            assert config["display"]["size"] == 300

    def test_load_config_missing_file(self) -> None:
        gui = SettingsGUI(config_path="/nonexistent/config.yaml")
        config = gui.load_config()
        assert config == {}

    def test_save_config(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            path = f.name

        gui = SettingsGUI(config_path=path)
        gui.config = {
            "language": "asl",
            "display": {"position": "top-left", "size": 250},
        }
        gui.save_config()

        with open(path) as f:
            saved = yaml.safe_load(f)
        assert saved["language"] == "asl"
        assert saved["display"]["position"] == "top-left"
        assert saved["display"]["size"] == 250

    def test_roundtrip(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            original = {
                "language": "isl",
                "display": {"size": 150, "transition": "slide"},
                "whisper": {"model_size": "small"},
            }
            yaml.safe_dump(original, f)
            path = f.name

        gui = SettingsGUI(config_path=path)
        gui.load_config()
        gui.save_config()

        gui2 = SettingsGUI(config_path=path)
        config = gui2.load_config()
        assert config["language"] == "isl"
        assert config["display"]["transition"] == "slide"
        assert config["whisper"]["model_size"] == "small"
