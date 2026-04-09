"""3D hand model renderer (simplified 2.5D approach for Phase 3 MVP).

Uses pre-rendered pose images with blending instead of full 3D rendering.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pygame

logger = logging.getLogger(__name__)


@dataclass
class HandPose:
    """Represents a hand pose configuration."""
    name: str
    sign_id: str
    joint_angles: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    image_file: str | None = None


class HandModel3D:
    """3D hand model renderer using pre-rendered pose images with blending."""

    def __init__(self, model_path: str | Path, size: tuple[int, int] = (200, 200)) -> None:
        self.model_path = Path(model_path)
        self.size = size
        self.poses: dict[str, HandPose] = {}
        self.pose_images: dict[str, pygame.Surface] = {}
        self.current_pose: HandPose | None = None
        self.current_surface: pygame.Surface | None = None
        self.skin_tone = "medium"
        self._initialized = False

    def load_model(self) -> bool:
        poses_dir = self.model_path / "poses"
        if not poses_dir.exists():
            logger.warning("Poses directory not found: %s", poses_dir)
            return False

        for pose_file in poses_dir.glob("**/*.json"):
            try:
                with open(pose_file) as f:
                    data = json.load(f)
                pose = HandPose(
                    name=data.get("name", pose_file.stem),
                    sign_id=data.get("sign_id", pose_file.stem),
                    joint_angles=data.get("joints", {}),
                    image_file=data.get("image_file"),
                )
                self.poses[pose.sign_id] = pose

                if pose.image_file:
                    img_path = self.model_path / "images" / pose.image_file
                    if img_path.exists():
                        img = pygame.image.load(str(img_path))
                        img = pygame.transform.smoothscale(img, self.size)
                        self.pose_images[pose.sign_id] = img
            except Exception as e:
                logger.error("Failed to load pose %s: %s", pose_file, e)

        self._initialized = True
        logger.info("Loaded %d poses, %d images", len(self.poses), len(self.pose_images))
        return True

    def set_pose(self, sign_id: str) -> bool:
        if sign_id in self.poses:
            self.current_pose = self.poses[sign_id]
            if sign_id in self.pose_images:
                self.current_surface = self.pose_images[sign_id]
            return True
        return False

    def get_pose(self, sign_id: str) -> HandPose | None:
        return self.poses.get(sign_id)

    def render(self) -> pygame.Surface | None:
        return self.current_surface

    def set_skin_tone(self, tone: str) -> None:
        self.skin_tone = tone

    def is_initialized(self) -> bool:
        return self._initialized

    def get_available_poses(self) -> list[str]:
        return list(self.poses.keys())
