"""Smooth transitions between hand poses with easing and queuing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

import pygame

logger = logging.getLogger(__name__)


def ease_in_out_quad(t: float) -> float:
    if t < 0.5:
        return 2 * t * t
    return 1 - pow(-2 * t + 2, 2) / 2


def ease_out_cubic(t: float) -> float:
    return 1 - pow(1 - t, 3)


@dataclass
class TransitionState:
    from_surface: pygame.Surface | None
    to_surface: pygame.Surface | None
    duration_ms: int
    elapsed_ms: float = 0
    easing: Callable[[float], float] = ease_in_out_quad


class SkeletalAnimator:
    """Handles smooth transitions between hand poses."""

    def __init__(self, transition_ms: int = 150) -> None:
        self.default_transition_ms = transition_ms
        self.current_surface: pygame.Surface | None = None
        self.transition: TransitionState | None = None
        self.transition_queue: list[tuple[pygame.Surface | None, int]] = []

    def set_current(self, surface: pygame.Surface | None) -> None:
        self.current_surface = surface
        self.transition = None

    def queue_transition(self, target_surface: pygame.Surface | None,
                         duration_ms: int | None = None) -> None:
        duration = duration_ms or self.default_transition_ms

        if self.transition is None:
            self.transition = TransitionState(
                from_surface=self.current_surface,
                to_surface=target_surface,
                duration_ms=duration,
            )
        else:
            self.transition_queue.append((target_surface, duration))

    def update(self, dt_ms: float) -> pygame.Surface | None:
        if self.transition is None:
            return self.current_surface

        self.transition.elapsed_ms += dt_ms

        if self.transition.elapsed_ms >= self.transition.duration_ms:
            self.current_surface = self.transition.to_surface
            self.transition = None

            if self.transition_queue:
                next_surface, next_duration = self.transition_queue.pop(0)
                self.queue_transition(next_surface, next_duration)

            return self.current_surface

        t = self.transition.elapsed_ms / self.transition.duration_ms
        t = self.transition.easing(t)

        return self._blend_surfaces(
            self.transition.from_surface,
            self.transition.to_surface,
            t,
        )

    def is_transitioning(self) -> bool:
        return self.transition is not None

    def clear_queue(self) -> None:
        self.transition_queue.clear()

    @staticmethod
    def interpolate_joint_angles(
        from_angles: dict[str, tuple[float, float, float]],
        to_angles: dict[str, tuple[float, float, float]],
        t: float,
    ) -> dict[str, tuple[float, float, float]]:
        """Linearly interpolate between two sets of joint angles."""
        all_keys = set(from_angles.keys()) | set(to_angles.keys())
        result: dict[str, tuple[float, float, float]] = {}
        zero = (0.0, 0.0, 0.0)
        for key in all_keys:
            fa = from_angles.get(key, zero)
            ta = to_angles.get(key, zero)
            result[key] = (
                fa[0] + (ta[0] - fa[0]) * t,
                fa[1] + (ta[1] - fa[1]) * t,
                fa[2] + (ta[2] - fa[2]) * t,
            )
        return result

    def _blend_surfaces(self, from_surf: pygame.Surface | None,
                        to_surf: pygame.Surface | None,
                        t: float) -> pygame.Surface | None:
        if from_surf is None and to_surf is None:
            return None

        if from_surf is None:
            result = to_surf.copy()
            result.set_alpha(int(255 * t))
            return result

        if to_surf is None:
            result = from_surf.copy()
            result.set_alpha(int(255 * (1 - t)))
            return result

        size = from_surf.get_size()
        result = pygame.Surface(size, pygame.SRCALPHA)

        from_copy = from_surf.copy()
        from_copy.set_alpha(int(255 * (1 - t)))
        result.blit(from_copy, (0, 0))

        to_copy = to_surf.copy()
        to_copy.set_alpha(int(255 * t))
        result.blit(to_copy, (0, 0))

        return result
