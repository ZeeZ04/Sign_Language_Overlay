"""Map common words to sign assets instead of fingerspelling every letter."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from .text_to_sign import SignToken, TextToSignConverter

logger = logging.getLogger(__name__)

DEFAULT_MAPPING_PATH = Path(__file__).parent.parent / "assets" / "signs" / "asl" / "mapping.json"
PUNCTUATION_RE = re.compile(r"[^\w\s']", re.UNICODE)


@dataclass
class SignSequence:
    tokens: list[SignToken]
    method: str  # "word_sign" or "fingerspell"


class WordSignMapper:
    def __init__(self, assets_path: str, language: str = "asl") -> None:
        self.assets_path = Path(assets_path)
        self.language = language
        self._word_signs: dict[str, dict] = {}
        self._variants: dict[str, str] = {}  # variant -> canonical form
        self._fingerspeller = TextToSignConverter(language=language)

    def load_word_signs(self) -> None:
        mapping_path = self.assets_path / "mapping.json"
        if not mapping_path.exists():
            raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

        with open(mapping_path, "r") as f:
            data = json.load(f)

        self._word_signs = data.get("words", {})

        # Build variant lookup
        for canonical, info in self._word_signs.items():
            # Map the canonical key itself (underscores to spaces)
            normalized = canonical.replace("_", " ").lower()
            self._variants[normalized] = canonical

            # Map explicit variants
            for variant in info.get("variants", []):
                self._variants[variant.lower()] = canonical

        logger.info("Loaded %d word signs with %d variants", len(self._word_signs), len(self._variants))

    def map_text(self, text: str) -> list[SignSequence]:
        words = self._tokenize(text)
        sequences: list[SignSequence] = []

        i = 0
        while i < len(words):
            word = words[i]

            # Check for multi-word signs (e.g., "thank you")
            matched = False
            for lookahead in range(min(3, len(words) - i), 0, -1):
                phrase = " ".join(words[i:i + lookahead]).lower()
                phrase_clean = PUNCTUATION_RE.sub("", phrase).strip()
                if phrase_clean in self._variants:
                    canonical = self._variants[phrase_clean]
                    info = self._word_signs[canonical]
                    token = SignToken(
                        character=phrase,
                        sign_id=f"word:{canonical}",
                        duration_ms=info.get("duration_ms", 600),
                    )
                    sequences.append(SignSequence(tokens=[token], method="word_sign"))
                    i += lookahead
                    matched = True
                    break

            if not matched:
                # Fingerspell the word
                tokens = self._fingerspeller.convert(word)
                if tokens:
                    sequences.append(SignSequence(tokens=tokens, method="fingerspell"))
                i += 1

            # Add space between words (unless last word)
            if i < len(words):
                space_token = SignToken(character=" ", sign_id="space", duration_ms=150)
                sequences.append(SignSequence(tokens=[space_token], method="fingerspell"))

        return sequences

    def get_available_words(self) -> list[str]:
        return list(self._word_signs.keys())

    def has_word_sign(self, word: str) -> bool:
        clean = PUNCTUATION_RE.sub("", word.lower()).strip()
        return clean in self._variants

    def _tokenize(self, text: str) -> list[str]:
        return text.split()
