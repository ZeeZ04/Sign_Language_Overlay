"""Capture screen regions and composite sign overlay onto video frames."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    mss = None  # type: ignore[assignment]
    MSS_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None  # type: ignore[assignment]
    CV2_AVAILABLE = False


@dataclass
class Monitor:
    """Display monitor info."""
    id: int
    x: int
    y: int
    width: int
    height: int
    name: str = ""


@dataclass
class CaptureRegion:
    """Screen region to capture."""
    x: int
    y: int
    width: int
    height: int


class ScreenCapture:
    """Capture screen regions for overlay compositing."""

    def __init__(self, monitor: int = 1, region: CaptureRegion | None = None) -> None:
        if not MSS_AVAILABLE:
            raise RuntimeError("mss not installed. Run: pip install mss")

        self._sct = mss.mss()
        self.monitor_id = monitor
        self.region = region
        self._monitors: list[Monitor] = []
        self._refresh_monitors()

    def list_monitors(self) -> list[Monitor]:
        return list(self._monitors)

    def set_region(self, x: int, y: int, width: int, height: int) -> None:
        self.region = CaptureRegion(x, y, width, height)

    def clear_region(self) -> None:
        self.region = None

    def capture_frame(self) -> np.ndarray | None:
        try:
            if self.region:
                monitor_dict = {
                    "left": self.region.x,
                    "top": self.region.y,
                    "width": self.region.width,
                    "height": self.region.height,
                }
            else:
                monitor_dict = self._sct.monitors[self.monitor_id]

            screenshot = self._sct.grab(monitor_dict)
            frame = np.array(screenshot)

            # Convert BGRA to BGR
            if frame.shape[2] == 4:
                frame = frame[:, :, :3]

            return frame
        except Exception as e:
            logger.error("Screen capture failed: %s", e)
            return None

    def get_monitor_info(self) -> Monitor | None:
        idx = self.monitor_id - 1
        if 0 <= idx < len(self._monitors):
            return self._monitors[idx]
        return None

    def _refresh_monitors(self) -> None:
        self._monitors = []
        for i, mon in enumerate(self._sct.monitors):
            if i == 0:
                continue
            self._monitors.append(Monitor(
                id=i,
                x=mon["left"],
                y=mon["top"],
                width=mon["width"],
                height=mon["height"],
                name=f"Monitor {i}",
            ))


class VideoOverlayCompositor:
    """Composite sign overlay onto video frames."""

    def __init__(self, overlay_size: int = 200, position: str = "bottom-right",
                 opacity: float = 0.9) -> None:
        if not CV2_AVAILABLE:
            raise RuntimeError("opencv-python not installed. Run: pip install opencv-python")

        self.overlay_size = overlay_size
        self.position = position
        self.opacity = opacity
        self.padding = 20

    def set_overlay_position(self, position: str) -> None:
        valid = ["top-left", "top-right", "bottom-left", "bottom-right"]
        if position not in valid:
            raise ValueError(f"Position must be one of: {valid}")
        self.position = position

    def set_overlay_size(self, size: int) -> None:
        self.overlay_size = size

    def set_opacity(self, opacity: float) -> None:
        self.opacity = max(0.0, min(1.0, opacity))

    def composite(self, video_frame: np.ndarray,
                  overlay_frame: np.ndarray | None) -> np.ndarray:
        if overlay_frame is None:
            return video_frame

        result = video_frame.copy()

        if overlay_frame.shape[0] != self.overlay_size:
            overlay_frame = cv2.resize(overlay_frame, (self.overlay_size, self.overlay_size))

        x, y = self._get_overlay_position(result.shape, overlay_frame.shape)
        oh, ow = overlay_frame.shape[:2]

        x = max(0, min(x, result.shape[1] - ow))
        y = max(0, min(y, result.shape[0] - oh))

        if overlay_frame.shape[2] == 4:
            alpha = overlay_frame[:, :, 3:4] / 255.0 * self.opacity
            overlay_rgb = overlay_frame[:, :, :3]
            roi = result[y:y + oh, x:x + ow]
            blended = (overlay_rgb * alpha + roi * (1 - alpha)).astype(np.uint8)
            result[y:y + oh, x:x + ow] = blended
        else:
            roi = result[y:y + oh, x:x + ow]
            blended = cv2.addWeighted(overlay_frame, self.opacity, roi, 1 - self.opacity, 0)
            result[y:y + oh, x:x + ow] = blended

        return result

    def _get_overlay_position(self, frame_shape: tuple, overlay_shape: tuple) -> tuple[int, int]:
        fh, fw = frame_shape[:2]
        oh, ow = overlay_shape[:2]

        positions = {
            "top-left": (self.padding, self.padding),
            "top-right": (fw - ow - self.padding, self.padding),
            "bottom-left": (self.padding, fh - oh - self.padding),
            "bottom-right": (fw - ow - self.padding, fh - oh - self.padding),
        }
        return positions.get(self.position, positions["bottom-right"])
