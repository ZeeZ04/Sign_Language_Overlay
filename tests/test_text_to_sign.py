"""Tests for the text to sign converter module."""

import pytest

from src.text_to_sign import TextToSignConverter, SignToken


class TestTextToSignConverter:
    def setup_method(self) -> None:
        self.converter = TextToSignConverter(language="asl")

    def test_convert_simple_word(self) -> None:
        tokens = self.converter.convert("hello")
        assert len(tokens) == 5
        assert [t.sign_id for t in tokens] == ["h", "e", "l", "l", "o"]
        assert all(t.duration_ms == 300 for t in tokens)

    def test_convert_with_spaces(self) -> None:
        tokens = self.converter.convert("hi there")
        assert len(tokens) == 8  # h, i, space, t, h, e, r, e
        assert tokens[2].sign_id == "space"
        assert tokens[2].duration_ms == 150

    def test_convert_with_numbers(self) -> None:
        tokens = self.converter.convert("abc123")
        assert len(tokens) == 6
        assert tokens[3].sign_id == "1"
        assert tokens[3].duration_ms == 350
        assert tokens[4].sign_id == "2"
        assert tokens[5].sign_id == "3"

    def test_handles_uppercase(self) -> None:
        tokens = self.converter.convert("Hello")
        assert tokens[0].sign_id == "h"
        assert tokens[0].character == "H"

    def test_handles_punctuation(self) -> None:
        tokens = self.converter.convert("hi!")
        assert len(tokens) == 3
        assert tokens[2].sign_id == "unknown"
        assert tokens[2].duration_ms == 200

    def test_empty_string(self) -> None:
        tokens = self.converter.convert("")
        assert tokens == []

    def test_all_spaces(self) -> None:
        tokens = self.converter.convert("   ")
        assert len(tokens) == 3
        assert all(t.sign_id == "space" for t in tokens)

    def test_preserves_original_character(self) -> None:
        tokens = self.converter.convert("A1!")
        assert tokens[0].character == "A"
        assert tokens[1].character == "1"
        assert tokens[2].character == "!"

    def test_full_alphabet(self) -> None:
        tokens = self.converter.convert("abcdefghijklmnopqrstuvwxyz")
        assert len(tokens) == 26
        for i, t in enumerate(tokens):
            assert t.sign_id == chr(ord("a") + i)
