"""Manage multiple sign language configurations."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LanguageConfig:
    """Configuration for a sign language."""
    code: str
    name: str
    alphabet_count: int
    has_two_handed_alphabet: bool
    has_numbers: bool
    word_sign_count: int
    assets_path: Path
    notes: str = ""


class LanguageManager:
    """Manage multiple sign language configurations."""

    SUPPORTED_LANGUAGES = {
        "asl": {
            "name": "American Sign Language",
            "alphabet_count": 26,
            "has_two_handed_alphabet": False,
            "has_numbers": True,
            "notes": "One-handed fingerspelling alphabet",
        },
        "bsl": {
            "name": "British Sign Language",
            "alphabet_count": 26,
            "has_two_handed_alphabet": True,
            "has_numbers": True,
            "notes": "Two-handed fingerspelling alphabet",
        },
        "isl": {
            "name": "Irish Sign Language",
            "alphabet_count": 26,
            "has_two_handed_alphabet": True,
            "has_numbers": True,
            "notes": "Related to French Sign Language",
        },
        "auslan": {
            "name": "Australian Sign Language",
            "alphabet_count": 26,
            "has_two_handed_alphabet": True,
            "has_numbers": True,
            "notes": "Related to BSL",
        },
    }

    def __init__(self, base_assets_path: str | Path) -> None:
        self.base_assets_path = Path(base_assets_path)
        self.current_language: LanguageConfig | None = None
        self._mapping_cache: dict[str, dict] = {}

    def get_available_languages(self) -> list[LanguageConfig]:
        languages = []
        for code, info in self.SUPPORTED_LANGUAGES.items():
            assets_path = self.base_assets_path / code
            word_count = self._count_word_signs(assets_path)
            languages.append(LanguageConfig(
                code=code,
                name=info["name"],
                alphabet_count=info["alphabet_count"],
                has_two_handed_alphabet=info["has_two_handed_alphabet"],
                has_numbers=info["has_numbers"],
                word_sign_count=word_count,
                assets_path=assets_path,
                notes=info["notes"],
            ))
        return languages

    def load_language(self, language_code: str) -> LanguageConfig:
        if language_code not in self.SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language: {language_code}. "
                f"Available: {list(self.SUPPORTED_LANGUAGES.keys())}"
            )

        info = self.SUPPORTED_LANGUAGES[language_code]
        assets_path = self.base_assets_path / language_code
        assets_path.mkdir(parents=True, exist_ok=True)

        self.current_language = LanguageConfig(
            code=language_code,
            name=info["name"],
            alphabet_count=info["alphabet_count"],
            has_two_handed_alphabet=info["has_two_handed_alphabet"],
            has_numbers=info["has_numbers"],
            word_sign_count=self._count_word_signs(assets_path),
            assets_path=assets_path,
            notes=info["notes"],
        )

        logger.info("Loaded language: %s", self.current_language.name)
        return self.current_language

    def get_current_language(self) -> LanguageConfig | None:
        return self.current_language

    def get_mapping(self) -> dict[str, Any]:
        if not self.current_language:
            raise RuntimeError("No language loaded. Call load_language() first.")

        code = self.current_language.code
        if code in self._mapping_cache:
            return self._mapping_cache[code]

        mapping_file = self.current_language.assets_path / "mapping.json"
        if not mapping_file.exists():
            logger.warning("No mapping.json found for %s, returning empty mapping", code)
            return {"alphabet": {}, "numbers": {}, "words": {}, "special": {}}

        with open(mapping_file) as f:
            mapping = json.load(f)

        self._mapping_cache[code] = mapping
        return mapping

    def switch_language(self, language_code: str) -> LanguageConfig:
        return self.load_language(language_code)

    def is_two_handed(self) -> bool:
        if not self.current_language:
            return False
        return self.current_language.has_two_handed_alphabet

    def _count_word_signs(self, assets_path: Path) -> int:
        mapping_file = assets_path / "mapping.json"
        if not mapping_file.exists():
            return 0
        try:
            with open(mapping_file) as f:
                mapping = json.load(f)
            return len(mapping.get("words", {}))
        except Exception:
            return 0
