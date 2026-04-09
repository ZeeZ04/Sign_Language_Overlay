"""Smooth transitions between signs instead of hard cuts."""

from __future__ import annotations

import logging
import math

import pygame

logger = logging.getLogger(__name__)


def _ease_in_out(t: float) -> float:
    """Smooth step easing function (ease-in-out)."""
    return t * t * (3.0 - 2.0 * t)


class AnimationController:
    def __init__(self, transition_ms: int = 100, transition_type: str = "fade") -> None:
        if transition_type not in ("fade", "cut", "slide"):
            raise ValueError(f"Invalid transition type: {transition_type}. Use fade, cut, or slide")
        self.transition_ms = transition_ms
        self.transition_type = transition_type
        self._current: pygame.Surface | None = None
        self._previous: pygame.Surface | None = None
        self._transition_progress: float = 1.0  # 0.0 = showing previous, 1.0 = showing current
        self._transitioning: bool = False
        self._size: tuple[int, int] = (200, 200)

    def set_sign(self, surface: pygame.Surface | None) -> None:
        if self.transition_type == "cut" or self.transition_ms <= 0:
            self._current = surface
            self._previous = None
            self._transitioning = False
            self._transition_progress = 1.0
            return

        # Only trigger transition if the sign actually changed
        if surface is self._current:
            return

        self._previous = self._current
        self._current = surface
        self._transition_progress = 0.0
        self._transitioning = True

        if surface is not None:
            self._size = surface.get_size()

    def update(self, dt_ms: float) -> None:
        if not self._transitioning:
            return

        if self.transition_ms <= 0:
            self._transition_progress = 1.0
            self._transitioning = False
            return

        self._transition_progress += dt_ms / self.transition_ms
        if self._transition_progress >= 1.0:
            self._transition_progress = 1.0
            self._transitioning = False
            self._previous = None

    def get_current_frame(self) -> pygame.Surface | None:
        if not self._transitioning or self._previous is None:
            return self._current

        t = _ease_in_out(self._transition_progress)

        if self.transition_type == "fade":
            return self._blend_fade(t)
        elif self.transition_type == "slide":
            return self._blend_slide(t)

        return self._current

    @property
    def is_transitioning(self) -> bool:
        return self._transitioning

    def _blend_fade(self, t: float) -> pygame.Surface:
        result = pygame.Surface(self._size, pygame.SRCALPHA)

        # Draw previous with fading alpha
        if self._previous is not None:
            prev_copy = self._previous.copy()
            prev_copy.set_alpha(int(255 * (1.0 - t)))
            result.blit(prev_copy, (0, 0))

        # Draw current with increasing alpha
        if self._current is not None:
            curr_copy = self._current.copy()
            curr_copy.set_alpha(int(255 * t))
            result.blit(curr_copy, (0, 0))

        return result

    def _blend_slide(self, t: float) -> pygame.Surface:
        w, h = self._size
        result = pygame.Surface(self._size, pygame.SRCALPHA)

        offset = int(w * t)

        # Previous slides out to the left
        if self._previous is not None:
            result.blit(self._previous, (-offset, 0))

        # Current slides in from the right
        if self._current is not None:
            result.blit(self._current, (w - offset, 0))

        return result
