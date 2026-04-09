"""Tests for the language manager module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.language_manager import LanguageManager, LanguageConfig


@pytest.fixture
def temp_assets_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        asl_dir = Path(tmpdir) / "asl"
        asl_dir.mkdir()
        (asl_dir / "alphabet").mkdir()
        (asl_dir / "mapping.json").write_text(json.dumps({
            "alphabet": {"a": {"file": "a.png"}},
            "numbers": {},
            "words": {"hello": {"file": "hello.png"}},
            "special": {},
        }))
        yield tmpdir


class TestLanguageManager:
    def test_get_available_languages(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        languages = manager.get_available_languages()
        assert len(languages) >= 2
        codes = [lang.code for lang in languages]
        assert "asl" in codes
        assert "bsl" in codes

    def test_load_language(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        config = manager.load_language("asl")
        assert config.code == "asl"
        assert config.name == "American Sign Language"
        assert config.has_two_handed_alphabet is False

    def test_load_invalid_language(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        with pytest.raises(ValueError):
            manager.load_language("invalid")

    def test_get_mapping(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        manager.load_language("asl")
        mapping = manager.get_mapping()
        assert "alphabet" in mapping
        assert "words" in mapping

    def test_get_mapping_without_load_raises(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        with pytest.raises(RuntimeError):
            manager.get_mapping()

    def test_switch_language(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        manager.load_language("asl")
        assert manager.get_current_language().code == "asl"
        manager.switch_language("bsl")
        assert manager.get_current_language().code == "bsl"

    def test_is_two_handed(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        manager.load_language("asl")
        assert manager.is_two_handed() is False
        manager.load_language("bsl")
        assert manager.is_two_handed() is True

    def test_is_two_handed_no_language(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        assert manager.is_two_handed() is False

    def test_get_current_language_none(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        assert manager.get_current_language() is None

    def test_word_sign_count(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        config = manager.load_language("asl")
        assert config.word_sign_count == 1  # "hello" in fixture

    def test_creates_missing_directory(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        config = manager.load_language("bsl")
        assert Path(temp_assets_dir, "bsl").exists()

    def test_empty_mapping_for_missing_file(self, temp_assets_dir) -> None:
        manager = LanguageManager(temp_assets_dir)
        manager.load_language("bsl")  # No mapping.json in fixture
        mapping = manager.get_mapping()
        assert mapping == {"alphabet": {}, "numbers": {}, "words": {}, "special": {}}
