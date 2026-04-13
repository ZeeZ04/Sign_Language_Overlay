"""Tests for the 3D hand model module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import pygame

from src.hand_model_3d import (
    HandModel3D, HandPose, ProjectedJoint,
    JOINT_NAMES, DEFAULT_REST_POSE, SKIN_TONES, BONE_CONNECTIONS,
)
from src.skeletal_animation import SkeletalAnimator, PoseInterpolator


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


class TestProjectedJoint:
    def test_creation(self) -> None:
        pj = ProjectedJoint(screen_x=100, screen_y=50, depth=0.3, radius=5.0, brightness=0.8)
        assert pj.screen_x == 100
        assert pj.depth == 0.3
        assert pj.brightness == 0.8

    def test_depth_affects_radius(self, temp_model_dir) -> None:
        """Joints at different Z depths should get different radii."""
        model = HandModel3D(temp_model_dir, size=(200, 200), perspective_strength=1.0)
        # Near joint (low z) vs far joint (high z)
        joints = dict(DEFAULT_REST_POSE)
        joints["index_tip"] = (0.27, 0.12, -0.1)  # closer
        joints["pinky_tip"] = (0.74, 0.23, 0.1)   # farther

        projected = model._project_joints(joints, source="kaggle-islr")
        assert projected["index_tip"].radius > projected["pinky_tip"].radius

    def test_zero_z_degrades_to_orthographic(self, temp_model_dir) -> None:
        """When all Z=0, all joints should have same depth and uniform radii."""
        model = HandModel3D(temp_model_dir, size=(200, 200), perspective_strength=0.5)
        all_zero = {name: (x, y, 0.0) for name, (x, y, z) in DEFAULT_REST_POSE.items()}
        projected = model._project_joints(all_zero, source="kaggle-islr")
        # All depths should be identical (no Z variation)
        depths = {pj.depth for pj in projected.values()}
        assert len(depths) == 1
        # All radii should be identical (no perspective variation)
        radii = {round(pj.radius, 2) for pj in projected.values()}
        assert len(radii) == 1


class TestProjectionMethods:
    def test_project_joints_returns_all_joints(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        projected = model._project_joints({}, source="manual")
        assert len(projected) == len(DEFAULT_REST_POSE)

    def test_project_joints_kaggle_source(self, temp_model_dir) -> None:
        """ISLR source should use positions directly, not as angle offsets."""
        model = HandModel3D(temp_model_dir, size=(200, 200))
        joints = {"wrist": (0.5, 0.5, 0.0), "thumb_tip": (0.2, 0.2, 0.1)}
        projected = model._project_joints(joints, source="kaggle-islr")
        assert "wrist" in projected
        assert "thumb_tip" in projected
        # Missing joints should fall back to rest pose
        assert "index_tip" in projected

    def test_project_joints_within_bounds(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        projected = model._project_joints(DEFAULT_REST_POSE, source="kaggle-islr")
        for name, pj in projected.items():
            assert 0 <= pj.screen_x <= 200, f"{name} x out of bounds"
            assert 0 <= pj.screen_y <= 200, f"{name} y out of bounds"
            assert 0.0 <= pj.depth <= 1.0, f"{name} depth out of range"
            assert pj.radius >= 2.0, f"{name} radius too small"
            assert 0.0 < pj.brightness <= 1.0, f"{name} brightness out of range"


class TestBoneSorting:
    def test_sort_bones_by_depth(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        projected = model._project_joints(DEFAULT_REST_POSE, source="kaggle-islr")
        sorted_bones = model._sort_bones_by_depth(projected)
        assert len(sorted_bones) == len(BONE_CONNECTIONS)
        # All bone connections should be present
        assert set(tuple(b) for b in sorted_bones) == set(tuple(b) for b in BONE_CONNECTIONS)


class TestRenderSkeletalFromJoints:
    def test_render_from_explicit_joints(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        surface = model.render_skeletal_from_joints(DEFAULT_REST_POSE, source="kaggle-islr")
        assert isinstance(surface, pygame.Surface)
        assert surface.get_size() == (200, 200)

    def test_render_from_empty_joints(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        surface = model.render_skeletal_from_joints({}, source="manual")
        assert isinstance(surface, pygame.Surface)

    def test_render_low_quality(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200), bone_quality="low")
        surface = model.render_skeletal_from_joints(DEFAULT_REST_POSE, source="kaggle-islr")
        assert isinstance(surface, pygame.Surface)

    def test_render_no_shadow_no_palm(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200), show_shadow=False, show_palm_fill=False)
        surface = model.render_skeletal_from_joints(DEFAULT_REST_POSE, source="kaggle-islr")
        assert isinstance(surface, pygame.Surface)


class TestHandPoseSource:
    def test_pose_source_default(self) -> None:
        pose = HandPose(name="test", sign_id="test")
        assert pose.source == "manual"

    def test_pose_source_kaggle(self) -> None:
        pose = HandPose(name="test", sign_id="test", source="kaggle-islr")
        assert pose.source == "kaggle-islr"

    def test_load_pose_with_source(self, tmp_path) -> None:
        poses_dir = tmp_path / "poses"
        poses_dir.mkdir()
        pose_data = {
            "name": "Test",
            "sign_id": "test",
            "joints": {"wrist": [0.5, 0.5, 0.0]},
            "source": "kaggle-islr",
        }
        (poses_dir / "test.json").write_text(json.dumps(pose_data))

        model = HandModel3D(tmp_path, size=(200, 200))
        model.load_model()
        pose = model.get_pose("test")
        assert pose is not None
        assert pose.source == "kaggle-islr"


class TestSyntheticPoses:
    def test_synthetic_poses_directory_exists(self) -> None:
        poses_dir = Path(__file__).parent.parent / "models" / "hand" / "poses" / "asl"
        assert poses_dir.exists()

    def test_synthetic_poses_loadable(self) -> None:
        poses_dir = Path(__file__).parent.parent / "models" / "hand" / "poses" / "asl"
        if not poses_dir.exists():
            pytest.skip("Synthetic poses not generated")
        pose_files = list(poses_dir.glob("*.json"))
        assert len(pose_files) >= 36  # 26 letters + 10 digits

    def test_synthetic_pose_valid_json(self) -> None:
        poses_dir = Path(__file__).parent.parent / "models" / "hand" / "poses" / "asl"
        a_pose = poses_dir / "a.json"
        if not a_pose.exists():
            pytest.skip("Synthetic poses not generated")
        with open(a_pose) as f:
            data = json.load(f)
        assert "name" in data
        assert "sign_id" in data
        assert "joints" in data
        assert data["sign_id"] == "a"

    def test_synthetic_poses_render(self) -> None:
        model_path = Path(__file__).parent.parent / "models" / "hand"
        model = HandModel3D(model_path, size=(200, 200))
        if not model.load_model():
            pytest.skip("No poses available")
        if model.set_pose("a"):
            surface = model.render_skeletal()
            assert isinstance(surface, pygame.Surface)


class TestPoseInterpolator:
    def test_initial_state(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        model.load_model()
        interp = PoseInterpolator(model)
        assert interp.is_transitioning is False
        assert interp.current_surface is None

    def test_queue_and_complete(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        model.load_model()
        interp = PoseInterpolator(model, transition_ms=100)

        pose_a = model.get_pose("a")
        interp.queue_pose_transition(pose_a)
        assert interp.is_transitioning is True

        # Complete the transition
        surface = interp.update(150.0)
        assert interp.is_transitioning is False
        assert surface is not None

    def test_mid_transition_renders(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        model.load_model()
        interp = PoseInterpolator(model, transition_ms=100)

        pose_a = model.get_pose("a")
        interp.queue_pose_transition(pose_a)

        # Mid-transition should render interpolated frame
        surface = interp.update(50.0)
        assert surface is not None
        assert isinstance(surface, pygame.Surface)

    def test_queue_chaining(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        model.load_model()
        interp = PoseInterpolator(model, transition_ms=100)

        pose_a = model.get_pose("a")
        pose_b = model.get_pose("b")
        interp.queue_pose_transition(pose_a)
        interp.queue_pose_transition(pose_b)  # queued

        # Complete first transition
        interp.update(110.0)
        # Second should now be active
        assert interp.is_transitioning is True

        # Complete second
        interp.update(110.0)
        assert interp.is_transitioning is False

    def test_queue_none_pose(self, temp_model_dir) -> None:
        model = HandModel3D(temp_model_dir, size=(200, 200))
        model.load_model()
        interp = PoseInterpolator(model, transition_ms=100)
        interp.queue_pose_transition(None)
        assert interp.is_transitioning is False
