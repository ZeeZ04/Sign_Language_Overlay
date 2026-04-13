"""Smooth transitions between hand poses with easing and queuing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

import pygame

if TYPE_CHECKING:
    from .hand_model_3d import HandModel3D, HandPose

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


class PoseInterpolator:
    """Interpolates between hand poses at the joint level, then renders.

    Instead of blending pre-rendered surfaces, this interpolates the actual
    3D joint positions and renders each intermediate frame from scratch.
    This produces smooth skeletal motion between signs.
    """

    def __init__(self, hand_model: HandModel3D, transition_ms: int = 150) -> None:
        self.hand_model = hand_model
        self.default_transition_ms = transition_ms
        self.easing = ease_in_out_quad

        self._from_joints: dict[str, tuple[float, float, float]] = {}
        self._to_joints: dict[str, tuple[float, float, float]] = {}
        self._from_source: str = "manual"
        self._to_source: str = "manual"
        self._duration_ms: float = 0
        self._elapsed_ms: float = 0
        self._transitioning: bool = False
        self._current_surface: pygame.Surface | None = None
        self._queue: list[tuple[dict, str, int]] = []

    def queue_pose_transition(
        self,
        target_pose: HandPose | None,
        duration_ms: int | None = None,
    ) -> None:
        """Queue a transition to a target pose."""
        if target_pose is None:
            return

        duration = duration_ms or self.default_transition_ms
        target_joints = target_pose.joint_angles
        target_source = target_pose.source

        if self._transitioning:
            self._queue.append((target_joints, target_source, duration))
            return

        self._from_joints = self._to_joints.copy() if self._to_joints else {}
        self._from_source = self._to_source
        self._to_joints = target_joints
        self._to_source = target_source
        self._duration_ms = float(duration)
        self._elapsed_ms = 0.0
        self._transitioning = True

    def update(self, dt_ms: float) -> pygame.Surface | None:
        """Advance the interpolation and render the current frame."""
        if not self._transitioning:
            return self._current_surface

        self._elapsed_ms += dt_ms

        if self._elapsed_ms >= self._duration_ms:
            # Transition complete
            self._transitioning = False
            self._current_surface = self.hand_model.render_skeletal_from_joints(
                self._to_joints, source=self._to_source,
            )

            # Start next queued transition
            if self._queue:
                joints, source, dur = self._queue.pop(0)
                self._from_joints = self._to_joints.copy()
                self._from_source = self._to_source
                self._to_joints = joints
                self._to_source = source
                self._duration_ms = float(dur)
                self._elapsed_ms = 0.0
                self._transitioning = True

            return self._current_surface

        # Interpolate at current progress
        t = self._elapsed_ms / self._duration_ms
        t = self.easing(t)

        interpolated = SkeletalAnimator.interpolate_joint_angles(
            self._from_joints, self._to_joints, t,
        )

        # Use the target source for rendering (positions are blended)
        self._current_surface = self.hand_model.render_skeletal_from_joints(
            interpolated, source=self._to_source,
        )
        return self._current_surface

    @property
    def is_transitioning(self) -> bool:
        return self._transitioning

    @property
    def current_surface(self) -> pygame.Surface | None:
        return self._current_surface
