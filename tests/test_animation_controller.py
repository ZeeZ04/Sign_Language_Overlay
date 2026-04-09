"""Tests for the animation controller module."""

from __future__ import annotations

import pytest
import pygame

from src.animation_controller import AnimationController


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.NOFRAME)
    yield
    pygame.quit()


def _make_surface(color: tuple[int, int, int, int] = (255, 0, 0, 255)) -> pygame.Surface:
    surface = pygame.Surface((100, 100), pygame.SRCALPHA)
    surface.fill(color)
    return surface


class TestAnimationControllerFade:
    def test_initial_state(self) -> None:
        ac = AnimationController(transition_ms=100, transition_type="fade")
        assert ac.get_current_frame() is None
        assert ac.is_transitioning is False

    def test_set_first_sign(self) -> None:
        ac = AnimationController(transition_ms=100, transition_type="fade")
        s = _make_surface()
        ac.set_sign(s)
        # Transition starts from None to surface
        assert ac.is_transitioning is True

    def test_transition_completes(self) -> None:
        ac = AnimationController(transition_ms=100, transition_type="fade")
        s = _make_surface()
        ac.set_sign(s)
        # Advance past the transition
        ac.update(150.0)
        assert ac.is_transitioning is False
        frame = ac.get_current_frame()
        assert frame is not None

    def test_mid_transition_returns_blended(self) -> None:
        ac = AnimationController(transition_ms=200, transition_type="fade")
        s1 = _make_surface((255, 0, 0, 255))
        ac.set_sign(s1)
        ac.update(250.0)  # complete first

        s2 = _make_surface((0, 0, 255, 255))
        ac.set_sign(s2)
        ac.update(100.0)  # half way
        frame = ac.get_current_frame()
        assert frame is not None
        assert frame.get_size() == (100, 100)

    def test_handles_none_surface(self) -> None:
        ac = AnimationController(transition_ms=100, transition_type="fade")
        s = _make_surface()
        ac.set_sign(s)
        ac.update(150.0)

        ac.set_sign(None)
        ac.update(150.0)
        assert ac.get_current_frame() is None


class TestAnimationControllerCut:
    def test_cut_no_transition(self) -> None:
        ac = AnimationController(transition_ms=100, transition_type="cut")
        s = _make_surface()
        ac.set_sign(s)
        assert ac.is_transitioning is False
        assert ac.get_current_frame() is s


class TestAnimationControllerSlide:
    def test_slide_transition(self) -> None:
        ac = AnimationController(transition_ms=200, transition_type="slide")
        s1 = _make_surface((255, 0, 0, 255))
        ac.set_sign(s1)
        ac.update(250.0)

        s2 = _make_surface((0, 0, 255, 255))
        ac.set_sign(s2)
        assert ac.is_transitioning is True
        ac.update(100.0)
        frame = ac.get_current_frame()
        assert frame is not None

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid transition type"):
            AnimationController(transition_type="wipe")
