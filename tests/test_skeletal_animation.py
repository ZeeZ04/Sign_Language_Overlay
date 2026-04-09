"""Tests for the skeletal animation module."""

from __future__ import annotations

import pytest
import pygame

from src.skeletal_animation import SkeletalAnimator, ease_in_out_quad, ease_out_cubic


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.NOFRAME)
    yield
    pygame.quit()


def _surface(color: tuple[int, int, int, int] = (255, 0, 0, 255)) -> pygame.Surface:
    s = pygame.Surface((100, 100), pygame.SRCALPHA)
    s.fill(color)
    return s


class TestEasingFunctions:
    def test_ease_in_out_quad_boundaries(self) -> None:
        assert ease_in_out_quad(0.0) == pytest.approx(0.0)
        assert ease_in_out_quad(1.0) == pytest.approx(1.0)
        assert ease_in_out_quad(0.5) == pytest.approx(0.5)

    def test_ease_out_cubic_boundaries(self) -> None:
        assert ease_out_cubic(0.0) == pytest.approx(0.0)
        assert ease_out_cubic(1.0) == pytest.approx(1.0)


class TestSkeletalAnimator:
    def test_initial_state(self) -> None:
        anim = SkeletalAnimator()
        assert anim.current_surface is None
        assert anim.is_transitioning() is False

    def test_set_current(self) -> None:
        anim = SkeletalAnimator()
        s = _surface()
        anim.set_current(s)
        assert anim.current_surface is s
        assert anim.is_transitioning() is False

    def test_queue_transition(self) -> None:
        anim = SkeletalAnimator(transition_ms=100)
        s1 = _surface((255, 0, 0, 255))
        s2 = _surface((0, 0, 255, 255))
        anim.set_current(s1)
        anim.queue_transition(s2)
        assert anim.is_transitioning() is True

    def test_transition_completes(self) -> None:
        anim = SkeletalAnimator(transition_ms=100)
        s1 = _surface((255, 0, 0, 255))
        s2 = _surface((0, 0, 255, 255))
        anim.set_current(s1)
        anim.queue_transition(s2)
        result = anim.update(150.0)
        assert anim.is_transitioning() is False
        assert anim.current_surface is s2

    def test_mid_transition_returns_blend(self) -> None:
        anim = SkeletalAnimator(transition_ms=200)
        s1 = _surface((255, 0, 0, 255))
        s2 = _surface((0, 0, 255, 255))
        anim.set_current(s1)
        anim.queue_transition(s2)
        result = anim.update(100.0)
        assert result is not None
        assert result.get_size() == (100, 100)

    def test_queue_multiple(self) -> None:
        anim = SkeletalAnimator(transition_ms=50)
        s1 = _surface((255, 0, 0, 255))
        s2 = _surface((0, 255, 0, 255))
        s3 = _surface((0, 0, 255, 255))
        anim.set_current(s1)
        anim.queue_transition(s2)
        anim.queue_transition(s3)  # Queued
        assert len(anim.transition_queue) == 1

        anim.update(100.0)  # Complete first transition
        assert anim.is_transitioning() is True  # Second starts
        anim.update(100.0)
        assert anim.current_surface is s3

    def test_clear_queue(self) -> None:
        anim = SkeletalAnimator(transition_ms=50)
        s1 = _surface()
        s2 = _surface()
        anim.set_current(s1)
        anim.queue_transition(s1)
        anim.queue_transition(s2)
        anim.clear_queue()
        assert len(anim.transition_queue) == 0

    def test_blend_none_to_surface(self) -> None:
        anim = SkeletalAnimator(transition_ms=100)
        s = _surface()
        anim.queue_transition(s)
        result = anim.update(50.0)
        assert result is not None

    def test_blend_surface_to_none(self) -> None:
        anim = SkeletalAnimator(transition_ms=100)
        s = _surface()
        anim.set_current(s)
        anim.queue_transition(None)
        result = anim.update(50.0)
        assert result is not None

    def test_blend_none_to_none(self) -> None:
        anim = SkeletalAnimator(transition_ms=100)
        anim.queue_transition(None)
        result = anim.update(50.0)
        assert result is None
