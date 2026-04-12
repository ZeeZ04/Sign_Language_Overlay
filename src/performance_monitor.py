"""Performance monitoring for frame timing and transcription latency."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FrameStats:
    """Statistics for a single frame."""
    frame_time_ms: float
    render_time_ms: float = 0.0
    sign_lookup_time_ms: float = 0.0
    timestamp: float = 0.0


@dataclass
class TranscriptionStats:
    """Statistics for a single transcription."""
    latency_ms: float
    audio_duration_ms: float = 0.0
    text_length: int = 0
    timestamp: float = 0.0


class PerformanceMonitor:
    """Track frame times, render times, and transcription latency.

    Call start_frame()/end_frame() around each main loop iteration.
    Call record_transcription() when a transcription completes.
    Call update() each frame to periodically log stats.
    """

    def __init__(self, frame_budget_ms: float = 16.67, log_interval_s: float = 10.0) -> None:
        self.frame_budget_ms = frame_budget_ms
        self.log_interval_s = log_interval_s

        self._frame_stats: list[FrameStats] = []
        self._transcription_stats: list[TranscriptionStats] = []
        self._frame_start: float = 0.0
        self._render_start: float = 0.0
        self._last_log_time: float = time.time()
        self._warn_count: int = 0
        self._enabled: bool = True

    def start_frame(self) -> None:
        self._frame_start = time.perf_counter()

    def end_frame(self) -> None:
        elapsed_ms = (time.perf_counter() - self._frame_start) * 1000
        stats = FrameStats(
            frame_time_ms=elapsed_ms,
            timestamp=time.time(),
        )
        self._frame_stats.append(stats)

        if elapsed_ms > self.frame_budget_ms:
            self._warn_count += 1

    def record_render_time(self, ms: float) -> None:
        if self._frame_stats:
            self._frame_stats[-1].render_time_ms = ms

    def record_sign_lookup(self, ms: float) -> None:
        if self._frame_stats:
            self._frame_stats[-1].sign_lookup_time_ms = ms

    def record_transcription(self, latency_ms: float,
                             audio_duration_ms: float = 0.0,
                             text_length: int = 0) -> None:
        self._transcription_stats.append(TranscriptionStats(
            latency_ms=latency_ms,
            audio_duration_ms=audio_duration_ms,
            text_length=text_length,
            timestamp=time.time(),
        ))

    def update(self) -> None:
        """Log performance stats periodically."""
        now = time.time()
        if now - self._last_log_time < self.log_interval_s:
            return

        self._last_log_time = now
        summary = self.get_summary()

        if summary["frame_count"] > 0:
            logger.info(
                "Perf: %.1f avg fps | frame %.1f/%.1f/%.1f ms (avg/min/max) | %d over budget",
                summary["avg_fps"],
                summary["avg_frame_ms"],
                summary["min_frame_ms"],
                summary["max_frame_ms"],
                summary["over_budget_count"],
            )

        if summary["transcription_count"] > 0:
            logger.info(
                "Transcription: %.0f/%.0f/%.0f ms (avg/min/max) over %d calls",
                summary["avg_transcription_ms"],
                summary["min_transcription_ms"],
                summary["max_transcription_ms"],
                summary["transcription_count"],
            )

    def get_summary(self) -> dict:
        """Return summary statistics."""
        result: dict = {
            "frame_count": 0,
            "avg_frame_ms": 0.0,
            "min_frame_ms": 0.0,
            "max_frame_ms": 0.0,
            "p95_frame_ms": 0.0,
            "avg_fps": 0.0,
            "over_budget_count": self._warn_count,
            "transcription_count": 0,
            "avg_transcription_ms": 0.0,
            "min_transcription_ms": 0.0,
            "max_transcription_ms": 0.0,
        }

        if self._frame_stats:
            times = [s.frame_time_ms for s in self._frame_stats]
            times_sorted = sorted(times)
            result["frame_count"] = len(times)
            result["avg_frame_ms"] = sum(times) / len(times)
            result["min_frame_ms"] = times_sorted[0]
            result["max_frame_ms"] = times_sorted[-1]
            p95_idx = int(len(times_sorted) * 0.95)
            result["p95_frame_ms"] = times_sorted[min(p95_idx, len(times_sorted) - 1)]
            avg_ms = result["avg_frame_ms"]
            result["avg_fps"] = 1000.0 / avg_ms if avg_ms > 0 else 0.0

        if self._transcription_stats:
            latencies = [s.latency_ms for s in self._transcription_stats]
            result["transcription_count"] = len(latencies)
            result["avg_transcription_ms"] = sum(latencies) / len(latencies)
            result["min_transcription_ms"] = min(latencies)
            result["max_transcription_ms"] = max(latencies)

        return result

    def reset(self) -> None:
        self._frame_stats.clear()
        self._transcription_stats.clear()
        self._warn_count = 0
        self._last_log_time = time.time()
