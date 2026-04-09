"""Convert text strings into sequences of ASL fingerspelling sign identifiers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MAPPING_PATH = Path(__file__).parent.parent / "assets" / "signs" / "asl" / "mapping.json"


@dataclass
class SignToken:
    character: str  # original character
    sign_id: str  # identifier for the sign asset (e.g., "a", "1", "space")
    duration_ms: int  # suggested display duration


class TextToSignConverter:
    def __init__(self, language: str = "asl") -> None:
        self.language = language
        self._alphabet: dict[str, dict] = {}
        self._numbers: dict[str, dict] = {}
        self._special: dict[str, dict] = {}
        self.load_mapping(str(DEFAULT_MAPPING_PATH))

    def load_mapping(self, mapping_path: str) -> None:
        path = Path(mapping_path)
        if not path.exists():
            raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

        with open(path, "r") as f:
            data = json.load(f)

        self._alphabet = data.get("alphabet", {})
        self._numbers = data.get("numbers", {})
        self._special = data.get("special", {})
        logger.info(
            "Loaded mapping: %d letters, %d numbers",
            len(self._alphabet),
            len(self._numbers),
        )

    def convert(self, text: str) -> list[SignToken]:
        tokens: list[SignToken] = []
        for char in text:
            lower = char.lower()

            if char == " ":
                info = self._special.get("space", {"duration_ms": 150})
                tokens.append(SignToken(character=char, sign_id="space", duration_ms=info["duration_ms"]))
            elif lower in self._alphabet:
                info = self._alphabet[lower]
                tokens.append(SignToken(character=char, sign_id=lower, duration_ms=info["duration_ms"]))
            elif char in self._numbers:
                info = self._numbers[char]
                tokens.append(SignToken(character=char, sign_id=char, duration_ms=info["duration_ms"]))
            else:
                info = self._special.get("unknown", {"duration_ms": 200})
                tokens.append(SignToken(character=char, sign_id="unknown", duration_ms=info["duration_ms"]))

        return tokens
