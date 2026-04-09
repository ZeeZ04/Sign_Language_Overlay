"""Tests for the 3D hand model module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import pygame

from src.hand_model_3d import HandModel3D, HandPose


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
