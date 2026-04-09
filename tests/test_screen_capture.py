"""Tests for the screen capture module."""

from __future__ import annotations

import pytest
import numpy as np

from src.screen_capture import MSS_AVAILABLE, CV2_AVAILABLE


class TestScreenCapture:
    @pytest.mark.skipif(not MSS_AVAILABLE, reason="mss not installed")
    def test_init(self) -> None:
        from src.screen_capture import ScreenCapture
        sc = ScreenCapture()
        assert sc.monitor_id == 1

    @pytest.mark.skipif(not MSS_AVAILABLE, reason="mss not installed")
    def test_list_monitors(self) -> None:
        from src.screen_capture import ScreenCapture
        sc = ScreenCapture()
        monitors = sc.list_monitors()
        assert isinstance(monitors, list)
        # May be empty in headless/CI environments
        if monitors:
            assert monitors[0].width > 0
            assert monitors[0].height > 0

    @pytest.mark.skipif(not MSS_AVAILABLE, reason="mss not installed")
    def test_capture_frame(self) -> None:
        from src.screen_capture import ScreenCapture
        sc = ScreenCapture()
        monitors = sc.list_monitors()
        if not monitors:
            pytest.skip("No monitors detected (headless environment)")
        frame = sc.capture_frame()
        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert len(frame.shape) == 3

    @pytest.mark.skipif(not MSS_AVAILABLE, reason="mss not installed")
    def test_set_region(self) -> None:
        from src.screen_capture import ScreenCapture, CaptureRegion
        sc = ScreenCapture()
        sc.set_region(0, 0, 100, 100)
        assert sc.region is not None
        assert sc.region.width == 100
        frame = sc.capture_frame()
        assert frame is not None
        assert frame.shape[0] == 100
        assert frame.shape[1] == 100

    @pytest.mark.skipif(not MSS_AVAILABLE, reason="mss not installed")
    def test_clear_region(self) -> None:
        from src.screen_capture import ScreenCapture
        sc = ScreenCapture()
        sc.set_region(0, 0, 100, 100)
        sc.clear_region()
        assert sc.region is None

    @pytest.mark.skipif(not MSS_AVAILABLE, reason="mss not installed")
    def test_get_monitor_info(self) -> None:
        from src.screen_capture import ScreenCapture
        sc = ScreenCapture(monitor=1)
        monitors = sc.list_monitors()
        if not monitors:
            pytest.skip("No monitors detected (headless environment)")
        info = sc.get_monitor_info()
        assert info is not None
        assert info.id == 1

    def test_raises_without_mss(self) -> None:
        if MSS_AVAILABLE:
            pytest.skip("mss is installed")
        from src.screen_capture import ScreenCapture
        with pytest.raises(RuntimeError, match="mss not installed"):
            ScreenCapture()


class TestVideoOverlayCompositor:
    @pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv not installed")
    def test_init(self) -> None:
        from src.screen_capture import VideoOverlayCompositor
        comp = VideoOverlayCompositor(overlay_size=100)
        assert comp.overlay_size == 100

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv not installed")
    def test_composite_none_overlay(self) -> None:
        from src.screen_capture import VideoOverlayCompositor
        comp = VideoOverlayCompositor()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = comp.composite(frame, None)
        assert np.array_equal(result, frame)

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv not installed")
    def test_composite_with_overlay(self) -> None:
        from src.screen_capture import VideoOverlayCompositor
        comp = VideoOverlayCompositor(overlay_size=50, position="bottom-right")
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        overlay = np.ones((50, 50, 3), dtype=np.uint8) * 255
        result = comp.composite(frame, overlay)
        assert result.shape == frame.shape
        # Bottom-right should have some non-zero values
        assert result[-30, -30].sum() > 0

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv not installed")
    def test_set_position(self) -> None:
        from src.screen_capture import VideoOverlayCompositor
        comp = VideoOverlayCompositor()
        comp.set_overlay_position("top-left")
        assert comp.position == "top-left"

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv not installed")
    def test_invalid_position(self) -> None:
        from src.screen_capture import VideoOverlayCompositor
        comp = VideoOverlayCompositor()
        with pytest.raises(ValueError):
            comp.set_overlay_position("center")

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="opencv not installed")
    def test_set_opacity(self) -> None:
        from src.screen_capture import VideoOverlayCompositor
        comp = VideoOverlayCompositor()
        comp.set_opacity(0.5)
        assert comp.opacity == 0.5
        comp.set_opacity(1.5)  # Clamped
        assert comp.opacity == 1.0
        comp.set_opacity(-0.5)
        assert comp.opacity == 0.0

    def test_raises_without_cv2(self) -> None:
        if CV2_AVAILABLE:
            pytest.skip("opencv is installed")
        from src.screen_capture import VideoOverlayCompositor
        with pytest.raises(RuntimeError, match="opencv-python not installed"):
            VideoOverlayCompositor()
