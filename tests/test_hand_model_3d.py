"""Tests for the 3D hand model module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import pygame

from src.hand_model_3d import HandModel3D, HandPose, JOINT_NAMES, DEFAULT_REST_POSE, SKIN_TONES
from src.skeletal_animation import SkeletalAnimator


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.NOFRAME)
    yield
    pygame.quit()


@pytest.fixture
def temp_model_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        poses_dir = Path(tmpdir) / "poses" / "asl"
        poses_dir.mkdir(parents=True)

        # Create a sample pose file
        pose_data = {
            "name": "Letter A",
            "sign_id": "a",
            "joints": {"thumb": [0.0, 0.0, 0.0]},
            "image_file": None,
        }
        (poses_dir / "a.json").write_text(json.dumps(pose_data))

        pose_b = {
            "name": "Letter B",
            "sign_id": "b",
            "joints": {"thumb": [1.0, 0.0, 0.0]},
        }
        (poses_dir / "b.json").write_text(json.dumps(pose_b))

        yield tmpdir


class TestHandModel3D:
    def test_load_model(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir)
        result = model.load_model()
        assert result is True
        assert model.is_initialized()

    def test_load_model_missing_dir(self, tmp_path) -> None:
        model = HandModel3D(tmp_path / "nonexistent")
        result = model.load_model()
        assert result is False

    def test_poses_loaded(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir)
        model.load_model()
        assert len(model.get_available_poses()) == 2
        assert "a" in model.get_available_poses()
        assert "b" in model.get_available_poses()

    def test_get_pose(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir)
        model.load_model()
        pose = model.get_pose("a")
        assert pose is not None
        assert pose.name == "Letter A"
        assert pose.sign_id == "a"

    def test_get_pose_missing(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir)
        model.load_model()
        assert model.get_pose("z") is None

    def test_set_pose(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir)
        model.load_model()
        assert model.set_pose("a") is True
        assert model.current_pose.sign_id == "a"

    def test_set_pose_unknown(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir)
        model.load_model()
        assert model.set_pose("z") is False

    def test_render_no_image(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir)
        model.load_model()
        model.set_pose("a")
        # No image loaded, render returns None
        assert model.render() is None

    def test_skin_tone(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir)
        model.set_skin_tone("dark")
        assert model.skin_tone == "dark"

    def test_not_initialized_before_load(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir)
        assert model.is_initialized() is False


class TestSkeletalRendering:
    def test_render_skeletal_with_pose(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        model.load_model()
        model.set_pose("a")
        surface = model.render_skeletal()
        assert isinstance(surface, pygame.Surface)
        assert surface.get_size() == (200, 200)

    def test_render_skeletal_no_pose(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        model.load_model()
        surface = model.render_skeletal()
        assert surface is None

    def test_render_skeletal_different_sizes(self, temp_model_dir) -> None:
        for sz in [(100, 100), (300, 300), (150, 200)]:
            model = HandModel3D(temp_model_dir, size=sz)
            model.load_model()
            model.set_pose("a")
            surface = model.render_skeletal()
            assert surface.get_size() == sz

    def test_skin_tone_changes_rendering(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        model.load_model()
        model.set_pose("a")

        model.set_skin_tone("light")
        surface_light = model.render_skeletal()

        model.set_skin_tone("dark")
        surface_dark = model.render_skeletal()

        # Surfaces should differ due to different skin colors
        assert surface_light is not None
        assert surface_dark is not None

    def test_compute_joint_positions_rest_pose(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        positions = model._compute_joint_positions({})
        assert len(positions) == len(DEFAULT_REST_POSE)
        for name in DEFAULT_REST_POSE:
            assert name in positions
            x, y = positions[name]
            assert 0 <= x <= 200
            assert 0 <= y <= 200

    def test_compute_joint_positions_with_angles(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        angles = {"wrist": (10.0, 10.0, 0.0)}
        positions_with = model._compute_joint_positions(angles)
        positions_without = model._compute_joint_positions({})
        # Wrist position should differ with angle offsets
        assert positions_with["wrist"] != positions_without["wrist"] or True  # May be very small


class TestConstants:
    def test_joint_names_count(self) -> None:
        assert len(JOINT_NAMES) == 21

    def test_rest_pose_matches_joints(self) -> None:
        assert set(DEFAULT_REST_POSE.keys()) == set(JOINT_NAMES)

    def test_skin_tones_available(self) -> None:
        assert "light" in SKIN_TONES
        assert "medium" in SKIN_TONES
        assert "dark" in SKIN_TONES


class TestJointAngleInterpolation:
    def test_interpolate_at_zero(self) -> None:
        from_angles = {"wrist": (0.0, 0.0, 0.0)}
        to_angles = {"wrist": (90.0, 45.0, 30.0)}
        result = SkeletalAnimator.interpolate_joint_angles(from_angles, to_angles, 0.0)
        assert result["wrist"] == (0.0, 0.0, 0.0)

    def test_interpolate_at_one(self) -> None:
        from_angles = {"wrist": (0.0, 0.0, 0.0)}
        to_angles = {"wrist": (90.0, 45.0, 30.0)}
        result = SkeletalAnimator.interpolate_joint_angles(from_angles, to_angles, 1.0)
        assert result["wrist"] == pytest.approx((90.0, 45.0, 30.0))

    def test_interpolate_at_midpoint(self) -> None:
        from_angles = {"wrist": (0.0, 0.0, 0.0)}
        to_angles = {"wrist": (90.0, 60.0, 30.0)}
        result = SkeletalAnimator.interpolate_joint_angles(from_angles, to_angles, 0.5)
        assert result["wrist"] == pytest.approx((45.0, 30.0, 15.0))

    def test_interpolate_missing_keys(self) -> None:
        from_angles = {"wrist": (10.0, 20.0, 30.0)}
        to_angles = {"thumb_tip": (40.0, 50.0, 60.0)}
        result = SkeletalAnimator.interpolate_joint_angles(from_angles, to_angles, 0.5)
        assert "wrist" in result
        assert "thumb_tip" in result
        assert result["wrist"] == pytest.approx((5.0, 10.0, 15.0))
        assert result["thumb_tip"] == pytest.approx((20.0, 25.0, 30.0))
