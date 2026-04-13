"""3D hand model renderer with skeletal visualization.

Supports two rendering modes:
1. Pre-rendered pose images (original 2.5D approach)
2. Skeletal rendering: perspective projection of 3D joint positions with
   anti-aliased drawing, depth shading, and palm silhouette
"""

from __future__ import annotations

import json
import logging
import math
import time as _time
from dataclasses import dataclass, field
from pathlib import Path

import pygame
import pygame.gfxdraw

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

# Palm polygon: wrist + MCP joints of each finger
PALM_JOINT_INDICES = [0, 5, 9, 13, 17]

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
class ProjectedJoint:
    """A 3D joint projected onto screen coordinates with depth info."""
    screen_x: int
    screen_y: int
    depth: float  # normalized 0.0 (nearest) to 1.0 (farthest)
    radius: float  # perspective-scaled joint radius
    brightness: float  # 0.0-1.0, closer = brighter


@dataclass
class HandPose:
    """Represents a hand pose configuration."""
    name: str
    sign_id: str
    joint_angles: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    image_file: str | None = None
    source: str = "manual"  # "manual" or "kaggle-islr"


class HandModel3D:
    """3D hand model renderer with skeletal visualization."""

    def __init__(
        self,
        model_path: str | Path,
        size: tuple[int, int] = (200, 200),
        perspective_strength: float = 0.5,
        show_shadow: bool = True,
        show_palm_fill: bool = True,
        bone_quality: str = "high",
    ) -> None:
        self.model_path = Path(model_path)
        self.size = size
        self.poses: dict[str, HandPose] = {}
        self.pose_images: dict[str, pygame.Surface] = {}
        self.current_pose: HandPose | None = None
        self.current_surface: pygame.Surface | None = None
        self.skin_tone = "medium"
        self._initialized = False

        # Rendering settings
        self.perspective_strength = max(0.0, min(1.0, perspective_strength))
        self.show_shadow = show_shadow
        self.show_palm_fill = show_palm_fill
        self.bone_quality = bone_quality  # "high" or "low"
        self._auto_downgraded = False

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
                    source=data.get("source", "manual"),
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
        """Render the current pose as a skeleton with perspective and shading."""
        if self.current_pose is None:
            return None
        return self.render_skeletal_from_joints(
            self.current_pose.joint_angles,
            source=self.current_pose.source,
        )

    def render_skeletal_from_joints(
        self,
        joint_positions: dict[str, tuple[float, float, float]],
        source: str = "manual",
    ) -> pygame.Surface | None:
        """Render a skeleton from explicit joint positions.

        Args:
            joint_positions: Joint name -> (x, y, z) mapping.
            source: "kaggle-islr" for raw positions, "manual" for angle offsets.
        """
        start = _time.perf_counter()

        w, h = self.size
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        surface.fill((40, 40, 50, 200))

        # Project 3D joints to screen
        projected = self._project_joints(joint_positions, source)
        if not projected:
            return surface

        skin_color = SKIN_TONES.get(self.skin_tone, SKIN_TONES["medium"])
        use_high_quality = self.bone_quality == "high" and not self._auto_downgraded

        # Shadow pass (draw offset skeleton in transparent black)
        if self.show_shadow and use_high_quality:
            self._draw_shadow(surface, projected)

        # Palm silhouette
        if self.show_palm_fill and use_high_quality:
            self._draw_palm_fill(surface, projected, skin_color)

        # Sort bones by average depth (farthest first = painter's algorithm)
        sorted_bones = self._sort_bones_by_depth(projected)

        # Draw bones
        for idx_i, idx_j in sorted_bones:
            name_i = JOINT_NAMES[idx_i]
            name_j = JOINT_NAMES[idx_j]
            if name_i in projected and name_j in projected:
                pi, pj = projected[name_i], projected[name_j]
                if use_high_quality:
                    self._draw_bone_aa(surface, pi, pj, skin_color)
                else:
                    self._draw_bone_basic(surface, pi, pj, skin_color)

        # Draw joints (nearer joints on top = draw nearest last)
        joints_sorted = sorted(projected.items(), key=lambda kv: -kv[1].depth)
        for name, pj in joints_sorted:
            if use_high_quality:
                self._draw_joint_aa(surface, pj, skin_color, is_tip=name.endswith("_tip"))
            else:
                self._draw_joint_basic(surface, pj, skin_color, is_tip=name.endswith("_tip"))

        # Performance guard: auto-downgrade if render exceeds budget
        elapsed_ms = (_time.perf_counter() - start) * 1000
        if elapsed_ms > 10.0 and not self._auto_downgraded and use_high_quality:
            self._auto_downgraded = True
            logger.warning("3D render took %.1f ms, auto-downgrading to low quality", elapsed_ms)

        return surface

    # --- Projection ---

    def _project_joints(
        self,
        joint_data: dict[str, tuple[float, float, float]],
        source: str = "manual",
    ) -> dict[str, ProjectedJoint]:
        """Project 3D joint positions to screen coordinates with depth info."""
        w, h = self.size
        padding = 10
        draw_w = w - 2 * padding
        draw_h = h - 2 * padding

        # Resolve joint 3D positions based on data source
        positions_3d: dict[str, tuple[float, float, float]] = {}
        if source == "kaggle-islr":
            # ISLR data: values are raw (x, y, z) positions in [0,1] range
            for name in JOINT_NAMES:
                if name in joint_data:
                    positions_3d[name] = joint_data[name]
                elif name in DEFAULT_REST_POSE:
                    positions_3d[name] = DEFAULT_REST_POSE[name]
        else:
            # Manual data: values are angle offsets from rest pose
            for name, rest_pos in DEFAULT_REST_POSE.items():
                rx, ry, rz = rest_pos
                if name in joint_data:
                    ax, ay, az = joint_data[name]
                    scale = 0.003
                    rx += math.sin(math.radians(ax)) * scale * abs(ax)
                    ry += math.sin(math.radians(ay)) * scale * abs(ay)
                    rz += math.sin(math.radians(az)) * scale * abs(az)
                positions_3d[name] = (rx, ry, rz)

        if not positions_3d:
            return {}

        # Compute Z range for normalization
        z_values = [p[2] for p in positions_3d.values()]
        z_min, z_max = min(z_values), max(z_values)
        z_range = z_max - z_min if z_max != z_min else 1.0

        base_radius = max(3, min(w, h) // 35)

        result: dict[str, ProjectedJoint] = {}
        for name, (px, py, pz) in positions_3d.items():
            # Normalize depth: 0.0 = nearest, 1.0 = farthest
            depth = (pz - z_min) / z_range if z_range > 0 else 0.5

            # Weak perspective: scale by depth
            # perspective_strength controls how much Z affects size
            ps = self.perspective_strength
            scale_factor = 1.0 + ps * (0.3 - depth * 0.6)  # nearer=bigger
            radius = base_radius * scale_factor
            brightness = 1.0 - depth * 0.4 * ps  # nearer=brighter

            # Screen projection (x, y mapped to drawing area)
            sx = int(padding + px * draw_w)
            sy = int(padding + py * draw_h)
            sx = max(padding, min(w - padding, sx))
            sy = max(padding, min(h - padding, sy))

            result[name] = ProjectedJoint(
                screen_x=sx,
                screen_y=sy,
                depth=depth,
                radius=max(2.0, radius),
                brightness=max(0.3, min(1.0, brightness)),
            )

        return result

    # --- Bone sorting ---

    def _sort_bones_by_depth(
        self, projected: dict[str, ProjectedJoint],
    ) -> list[tuple[int, int]]:
        """Sort bones by average depth, farthest first (painter's algorithm)."""
        def bone_depth(pair: tuple[int, int]) -> float:
            name_i = JOINT_NAMES[pair[0]]
            name_j = JOINT_NAMES[pair[1]]
            di = projected[name_i].depth if name_i in projected else 0.5
            dj = projected[name_j].depth if name_j in projected else 0.5
            return -(di + dj) / 2  # negative for farthest-first sort

        return sorted(BONE_CONNECTIONS, key=bone_depth)

    # --- High quality drawing ---

    def _draw_bone_aa(
        self,
        surface: pygame.Surface,
        p1: ProjectedJoint,
        p2: ProjectedJoint,
        skin_color: tuple[int, int, int],
    ) -> None:
        """Draw a tapered, depth-shaded bone with anti-aliasing."""
        avg_brightness = (p1.brightness + p2.brightness) / 2
        color = self._shade_color(skin_color, avg_brightness * 0.8)

        # Compute perpendicular direction for width
        dx = p2.screen_x - p1.screen_x
        dy = p2.screen_y - p1.screen_y
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            return

        # Perpendicular unit vector
        nx, ny = -dy / length, dx / length

        # Tapered widths from joint radii
        w1 = max(1.5, p1.radius * 0.5)
        w2 = max(1.5, p2.radius * 0.5)

        # Quad vertices for tapered bone
        points = [
            (int(p1.screen_x + nx * w1), int(p1.screen_y + ny * w1)),
            (int(p2.screen_x + nx * w2), int(p2.screen_y + ny * w2)),
            (int(p2.screen_x - nx * w2), int(p2.screen_y - ny * w2)),
            (int(p1.screen_x - nx * w1), int(p1.screen_y - ny * w1)),
        ]

        # Clamp points to surface bounds
        w, h = surface.get_size()
        points = [(max(0, min(w - 1, x)), max(0, min(h - 1, y))) for x, y in points]

        try:
            pygame.gfxdraw.filled_polygon(surface, points, color + (220,))
            pygame.gfxdraw.aapolygon(surface, points, color + (255,))
        except (ValueError, OverflowError):
            # Fallback for degenerate polygons
            pygame.draw.line(
                surface, color,
                (p1.screen_x, p1.screen_y), (p2.screen_x, p2.screen_y), 3,
            )

    def _draw_joint_aa(
        self,
        surface: pygame.Surface,
        pj: ProjectedJoint,
        skin_color: tuple[int, int, int],
        is_tip: bool = False,
    ) -> None:
        """Draw an anti-aliased joint circle with highlight."""
        r = int(pj.radius + (1 if is_tip else 0))
        color = self._shade_color(skin_color, pj.brightness)
        x, y = pj.screen_x, pj.screen_y
        w, h = surface.get_size()

        # Clamp to valid drawing area
        if r < 1 or x - r < 0 or y - r < 0 or x + r >= w or y + r >= h:
            # Fallback: basic circle if near edges
            pygame.draw.circle(surface, color, (x, y), max(1, r))
            return

        try:
            pygame.gfxdraw.aacircle(surface, x, y, r, color)
            pygame.gfxdraw.filled_circle(surface, x, y, r, color)

            # Highlight dot on fingertips (small bright spot for 3D effect)
            if is_tip and r > 3:
                highlight = self._shade_color(skin_color, min(1.0, pj.brightness + 0.3))
                hr = max(1, r // 3)
                hx, hy = x - r // 4, y - r // 4
                if 0 <= hx - hr and hx + hr < w and 0 <= hy - hr and hy + hr < h:
                    pygame.gfxdraw.filled_circle(surface, hx, hy, hr, highlight + (160,))
        except (ValueError, OverflowError):
            pygame.draw.circle(surface, color, (x, y), max(1, r))

    def _draw_shadow(
        self, surface: pygame.Surface, projected: dict[str, ProjectedJoint],
    ) -> None:
        """Draw a drop shadow by rendering offset skeleton in semi-transparent black."""
        shadow_color = (0, 0, 0, 35)
        offset = 2
        for idx_i, idx_j in BONE_CONNECTIONS:
            name_i = JOINT_NAMES[idx_i]
            name_j = JOINT_NAMES[idx_j]
            if name_i in projected and name_j in projected:
                pi, pj = projected[name_i], projected[name_j]
                pygame.draw.line(
                    surface, shadow_color,
                    (pi.screen_x + offset, pi.screen_y + offset),
                    (pj.screen_x + offset, pj.screen_y + offset),
                    3,
                )

    def _draw_palm_fill(
        self,
        surface: pygame.Surface,
        projected: dict[str, ProjectedJoint],
        skin_color: tuple[int, int, int],
    ) -> None:
        """Draw a semi-transparent palm silhouette."""
        palm_names = [JOINT_NAMES[i] for i in PALM_JOINT_INDICES]
        points = []
        for name in palm_names:
            if name in projected:
                pj = projected[name]
                points.append((pj.screen_x, pj.screen_y))

        if len(points) >= 3:
            fill_color = skin_color + (35,)
            w, h = surface.get_size()
            points = [(max(0, min(w - 1, x)), max(0, min(h - 1, y))) for x, y in points]
            try:
                pygame.gfxdraw.filled_polygon(surface, points, fill_color)
            except (ValueError, OverflowError):
                pass

    # --- Low quality fallbacks ---

    def _draw_bone_basic(
        self,
        surface: pygame.Surface,
        p1: ProjectedJoint,
        p2: ProjectedJoint,
        skin_color: tuple[int, int, int],
    ) -> None:
        """Draw a basic bone line (fast fallback)."""
        avg_brightness = (p1.brightness + p2.brightness) / 2
        color = self._shade_color(skin_color, avg_brightness * 0.8)
        pygame.draw.line(
            surface, color,
            (p1.screen_x, p1.screen_y), (p2.screen_x, p2.screen_y), 3,
        )

    def _draw_joint_basic(
        self,
        surface: pygame.Surface,
        pj: ProjectedJoint,
        skin_color: tuple[int, int, int],
        is_tip: bool = False,
    ) -> None:
        """Draw a basic joint circle (fast fallback)."""
        r = int(pj.radius + (1 if is_tip else 0))
        color = self._shade_color(skin_color, pj.brightness)
        pygame.draw.circle(surface, color, (pj.screen_x, pj.screen_y), max(1, r))

    # --- Utilities ---

    @staticmethod
    def _shade_color(
        base: tuple[int, int, int], brightness: float,
    ) -> tuple[int, int, int]:
        """Scale a color by brightness factor."""
        return (
            max(0, min(255, int(base[0] * brightness))),
            max(0, min(255, int(base[1] * brightness))),
            max(0, min(255, int(base[2] * brightness))),
        )

    # --- Legacy compatibility ---

    def _compute_joint_positions(
        self, joint_angles: dict[str, tuple[float, float, float]],
    ) -> dict[str, tuple[int, int]]:
        """Legacy method: compute 2D positions (no depth info).

        Kept for backward compatibility with existing tests.
        """
        projected = self._project_joints(joint_angles, source="manual")
        return {name: (pj.screen_x, pj.screen_y) for name, pj in projected.items()}

    def set_skin_tone(self, tone: str) -> None:
        self.skin_tone = tone

    def is_initialized(self) -> bool:
        return self._initialized

    def get_available_poses(self) -> list[str]:
        return list(self.poses.keys())
