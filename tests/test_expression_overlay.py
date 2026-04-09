"""Tests for the expression overlay module."""

from __future__ import annotations

import pytest
import pygame

from src.expression_overlay import (
    ExpressionOverlay,
    ExpressionHint,
    ExpressionType,
)


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.NOFRAME)
    yield
    pygame.quit()


class TestExpressionOverlay:
    def test_initial_state(self) -> None:
        overlay = ExpressionOverlay()
        assert overlay.current_hint is None
        assert overlay.render((200, 200)) is None

    def test_set_expression(self) -> None:
        overlay = ExpressionOverlay()
        hint = ExpressionHint(ExpressionType.QUESTION, duration_ms=1000)
        overlay.set_expression(hint)
        assert overlay.current_hint is not None
        assert overlay.current_hint.type == ExpressionType.QUESTION

    def test_clear_expression(self) -> None:
        overlay = ExpressionOverlay()
        overlay.set_expression(ExpressionHint(ExpressionType.QUESTION))
        overlay.clear_expression()
        assert overlay.current_hint is None

    def test_render_question(self) -> None:
        overlay = ExpressionOverlay()
        overlay.set_expression(ExpressionHint(ExpressionType.QUESTION))
        surface = overlay.render((200, 200))
        assert surface is not None
        assert surface.get_size() == (200, 200)

    def test_render_none_type(self) -> None:
        overlay = ExpressionOverlay()
        overlay.set_expression(ExpressionHint(ExpressionType.NONE))
        assert overlay.render((200, 200)) is None

    def test_update_expires_hint(self) -> None:
        overlay = ExpressionOverlay()
        overlay.set_expression(ExpressionHint(ExpressionType.EMPHASIS, duration_ms=100))
        overlay.update(150.0)
        assert overlay.current_hint is None

    def test_update_keeps_active(self) -> None:
        overlay = ExpressionOverlay()
        overlay.set_expression(ExpressionHint(ExpressionType.EMPHASIS, duration_ms=1000))
        overlay.update(50.0)
        assert overlay.current_hint is not None


class TestInferExpression:
    def setup_method(self) -> None:
        self.overlay = ExpressionOverlay()

    def test_infer_question(self) -> None:
        hint = self.overlay.infer_expression("What is your name?")
        assert hint is not None
        assert hint.type == ExpressionType.QUESTION

    def test_infer_question_mark(self) -> None:
        hint = self.overlay.infer_expression("Really?")
        assert hint is not None
        assert hint.type == ExpressionType.QUESTION

    def test_infer_negation(self) -> None:
        hint = self.overlay.infer_expression("I don't know")
        assert hint is not None
        assert hint.type == ExpressionType.NEGATION

    def test_infer_emphasis(self) -> None:
        hint = self.overlay.infer_expression("Watch out!")
        assert hint is not None
        assert hint.type == ExpressionType.EMPHASIS

    def test_infer_positive(self) -> None:
        hint = self.overlay.infer_expression("That is great")
        assert hint is not None
        assert hint.type == ExpressionType.POSITIVE

    def test_infer_neutral(self) -> None:
        hint = self.overlay.infer_expression("The cat sat on the mat")
        assert hint is None

    def test_infer_empty(self) -> None:
        hint = self.overlay.infer_expression("")
        assert hint is None
