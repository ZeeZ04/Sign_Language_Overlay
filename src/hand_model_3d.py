"""3D hand model renderer with skeletal visualization.

Supports two rendering modes:
1. Pre-rendered pose images (original 2.5D approach)
2. Skeletal rendering: 2D projection of 3D joint positions drawn with pygame
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import pygame

logger = logging.getLogger(__name__)

# 21 joints following MediaPipe hand landmark convention
JOINT_NAMES: list[str] = [
    "wrist",
    "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip",
    "index_mcp", "index_pip", "index_dip", "index_tip",
    "middle_mcp", "middle_pip", "middle_dip", "middle_tip",
    "ring_mcp", "ring_pip", "ring_dip", "ring_tip",
    "pinky_mcp", "pinky_pip", "pinky_dip", "pinky_tip",
]

# Bone connections as pairs of joint indices
BONE_CONNECTIONS: list[tuple[int, int]] = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle
    (0, 9), (9, 10), (10, 11), (11, 12),
    # Ring
    (0, 13), (13, 14), (14, 15), (15, 16),
    # Pinky
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm connections
    (5, 9), (9, 13), (13, 17),
]

# Default rest pose: 3D positions (x, y, z) normalized to 0-1 range
DEFAULT_REST_POSE: dict[str, tuple[float, float, float]] = {
    "wrist": (0.5, 0.9, 0.0),
    "thumb_cmc": (0.35, 0.78, 0.02),
    "thumb_mcp": (0.25, 0.65, 0.04),
    "thumb_ip": (0.2, 0.52, 0.05),
    "thumb_tip": (0.17, 0.42, 0.05),
    "index_mcp": (0.3, 0.45, 0.0),
    "index_pip": (0.28, 0.3, 0.0),
    "index_dip": (0.27, 0.2, 0.0),
    "index_tip": (0.27, 0.12, 0.0),
    "middle_mcp": (0.45, 0.42, 0.0),
    "middle_pip": (0.44, 0.26, 0.0),
    "middle_dip": (0.44, 0.16, 0.0),
    "middle_tip": (0.44, 0.08, 0.0),
    "ring_mcp": (0.58, 0.45, 0.0),
    "ring_pip": (0.59, 0.3, 0.0),
    "ring_dip": (0.6, 0.2, 0.0),
    "ring_tip": (0.6, 0.13, 0.0),
    "pinky_mcp": (0.7, 0.5, 0.0),
    "pinky_pip": (0.72, 0.38, 0.0),
    "pinky_dip": (0.73, 0.3, 0.0),
    "pinky_tip": (0.74, 0.23, 0.0),
}

SKIN_TONES: dict[str, tuple[int, int, int]] = {
    "light": (255, 224, 189),
    "medium-light": (241, 194, 151),
    "medium": (227, 161, 115),
    "medium-dark": (188, 120, 75),
    "dark": (141, 85, 52),
}


@dataclass
class HandPose:
    """Represents a hand pose configuration."""
    name: str
    sign_id: str
    joint_angles: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    image_file: str | None = None


class HandModel3D:
    """3D hand model renderer with skeletal visualization."""

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

    def render_skeletal(self) -> pygame.Surface | None:
        """Render the current pose as a 2D-projected skeleton on a pygame Surface.

        Uses joint_angles from the current pose to offset from the rest pose,
        then projects 3D positions onto a 2D surface. Draws joints as circles
        and bones as lines.
        """
        if self.current_pose is None:
            return None

        w, h = self.size
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        surface.fill((40, 40, 50, 200))

        # Compute 2D joint positions
        positions_2d = self._compute_joint_positions(self.current_pose.joint_angles)

        skin_color = SKIN_TONES.get(self.skin_tone, SKIN_TONES["medium"])
        bone_color = (
            max(0, skin_color[0] - 30),
            max(0, skin_color[1] - 30),
            max(0, skin_color[2] - 30),
        )

        # Draw bones
        for i, j in BONE_CONNECTIONS:
            name_i = JOINT_NAMES[i]
            name_j = JOINT_NAMES[j]
            if name_i in positions_2d and name_j in positions_2d:
                pygame.draw.line(surface, bone_color,
                                 positions_2d[name_i], positions_2d[name_j], 3)

        # Draw joints
        joint_radius = max(3, min(w, h) // 40)
        for name, pos in positions_2d.items():
            # Fingertips get a slightly larger radius
            r = joint_radius + 1 if name.endswith("_tip") else joint_radius
            pygame.draw.circle(surface, skin_color, pos, r)

        return surface

    def _compute_joint_positions(
        self, joint_angles: dict[str, tuple[float, float, float]]
    ) -> dict[str, tuple[int, int]]:
        """Compute 2D screen positions from rest pose + joint angle offsets.

        Joint angles are interpreted as rotation offsets (degrees) from the
        rest pose. The offset is applied as a simple positional displacement
        scaled by angle magnitude — not a full FK chain.
        """
        w, h = self.size
        padding = 10
        draw_w = w - 2 * padding
        draw_h = h - 2 * padding

        positions: dict[str, tuple[int, int]] = {}
        for name, rest_pos in DEFAULT_REST_POSE.items():
            rx, ry, rz = rest_pos

            # Apply angle offsets if available
            if name in joint_angles:
                ax, ay, az = joint_angles[name]
                # Convert degrees to small positional offsets
                scale = 0.003
                rx += math.sin(math.radians(ax)) * scale * abs(ax)
                ry += math.sin(math.radians(ay)) * scale * abs(ay)
            # Ignore Z for orthographic projection

            # Map to screen coordinates
            sx = int(padding + rx * draw_w)
            sy = int(padding + ry * draw_h)
            sx = max(padding, min(w - padding, sx))
            sy = max(padding, min(h - padding, sy))
            positions[name] = (sx, sy)

        return positions

    def set_skin_tone(self, tone: str) -> None:
        self.skin_tone = tone

    def is_initialized(self) -> bool:
        return self._initialized

    def get_available_poses(self) -> list[str]:
        return list(self.poses.keys())
