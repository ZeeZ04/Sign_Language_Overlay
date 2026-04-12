"""Tests for the word sign mapper module."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.word_sign_mapper import WordSignMapper

ASSETS_DIR = str(Path(__file__).parent.parent / "assets" / "signs" / "asl")


class TestWordSignMapper:
    def setup_method(self) -> None:
        self.mapper = WordSignMapper(assets_path=ASSETS_DIR, language="asl")
        self.mapper.load_word_signs()

    def test_map_known_word(self) -> None:
        sequences = self.mapper.map_text("hello")
        assert len(sequences) == 1
        assert sequences[0].method == "word_sign"
        assert sequences[0].tokens[0].sign_id == "word:hello"

    def test_fallback_to_fingerspell(self) -> None:
        sequences = self.mapper.map_text("xylophone")
        assert len(sequences) == 1
        assert sequences[0].method == "fingerspell"
        assert len(sequences[0].tokens) == 9  # x-y-l-o-p-h-o-n-e

    def test_mixed_known_unknown(self) -> None:
        sequences = self.mapper.map_text("hello xylophone")
        # "hello" (word_sign) + space + "xylophone" (fingerspell)
        methods = [s.method for s in sequences]
        assert "word_sign" in methods
        assert "fingerspell" in methods

    def test_case_insensitive(self) -> None:
        sequences = self.mapper.map_text("HELLO")
        assert sequences[0].method == "word_sign"
        assert sequences[0].tokens[0].sign_id == "word:hello"

    def test_handles_punctuation(self) -> None:
        # "hello!" - the word "hello" should still match
        sequences = self.mapper.map_text("hello!")
        # May fingerspell the punctuation or match the word
        sign_ids = []
        for seq in sequences:
            for tok in seq.tokens:
                sign_ids.append(tok.sign_id)
        assert "word:hello" in sign_ids or any(s.method == "word_sign" for s in sequences)

    def test_variant_matching(self) -> None:
        # "hi" is a variant of "hello"
        sequences = self.mapper.map_text("hi")
        assert sequences[0].method == "word_sign"
        assert sequences[0].tokens[0].sign_id == "word:hello"

    def test_multi_word_sign(self) -> None:
        # "thank you" maps to "thank_you"
        sequences = self.mapper.map_text("thank you")
        word_signs = [s for s in sequences if s.method == "word_sign"]
        assert len(word_signs) >= 1
        assert word_signs[0].tokens[0].sign_id == "word:thank_you"

    def test_has_word_sign(self) -> None:
        assert self.mapper.has_word_sign("hello") is True
        assert self.mapper.has_word_sign("xylophone") is False
        assert self.mapper.has_word_sign("hi") is True  # variant

    def test_get_available_words(self) -> None:
        words = self.mapper.get_available_words()
        assert len(words) >= 50  # 50 original + ASL-LEX expansion
        assert "hello" in words
        assert "goodbye" in words

    def test_empty_text(self) -> None:
        sequences = self.mapper.map_text("")
        assert sequences == []
