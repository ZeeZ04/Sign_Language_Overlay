"""Tests for the performance monitor module."""

from __future__ import annotations

import time

from src.performance_monitor import PerformanceMonitor


class TestFrameTiming:
    def test_frame_stats_recorded(self) -> None:
        monitor = PerformanceMonitor()
        monitor.start_frame()
        monitor.end_frame()
        assert len(monitor._frame_stats) == 1
        assert monitor._frame_stats[0].frame_time_ms >= 0

    def test_multiple_frames(self) -> None:
        monitor = PerformanceMonitor()
        for _ in range(10):
            monitor.start_frame()
            monitor.end_frame()
        assert len(monitor._frame_stats) == 10

    def test_over_budget_warning(self) -> None:
        monitor = PerformanceMonitor(frame_budget_ms=0.001)  # impossibly small
        monitor.start_frame()
        time.sleep(0.001)
        monitor.end_frame()
        assert monitor._warn_count >= 1

    def test_under_budget_no_warning(self) -> None:
        monitor = PerformanceMonitor(frame_budget_ms=10000)  # very generous
        monitor.start_frame()
        monitor.end_frame()
        assert monitor._warn_count == 0


class TestTranscriptionStats:
    def test_transcription_recorded(self) -> None:
        monitor = PerformanceMonitor()
        monitor.record_transcription(latency_ms=150.0, audio_duration_ms=3000.0, text_length=50)
        assert len(monitor._transcription_stats) == 1
        assert monitor._transcription_stats[0].latency_ms == 150.0

    def test_multiple_transcriptions(self) -> None:
        monitor = PerformanceMonitor()
        for i in range(5):
            monitor.record_transcription(latency_ms=float(100 + i * 50))
        assert len(monitor._transcription_stats) == 5


class TestSummary:
    def test_summary_with_frames(self) -> None:
        monitor = PerformanceMonitor()
        for _ in range(5):
            monitor.start_frame()
            monitor.end_frame()
        summary = monitor.get_summary()
        assert summary["frame_count"] == 5
        assert summary["avg_frame_ms"] >= 0
        assert summary["min_frame_ms"] >= 0
        assert summary["max_frame_ms"] >= summary["min_frame_ms"]
        assert summary["avg_fps"] >= 0

    def test_summary_empty(self) -> None:
        monitor = PerformanceMonitor()
        summary = monitor.get_summary()
        assert summary["frame_count"] == 0
        assert summary["transcription_count"] == 0

    def test_summary_with_transcriptions(self) -> None:
        monitor = PerformanceMonitor()
        monitor.record_transcription(latency_ms=100.0)
        monitor.record_transcription(latency_ms=200.0)
        monitor.record_transcription(latency_ms=300.0)
        summary = monitor.get_summary()
        assert summary["transcription_count"] == 3
        assert summary["avg_transcription_ms"] == 200.0
        assert summary["min_transcription_ms"] == 100.0
        assert summary["max_transcription_ms"] == 300.0

    def test_p95_calculation(self) -> None:
        monitor = PerformanceMonitor(frame_budget_ms=1000)
        # Add 100 frames with known times
        for i in range(100):
            monitor.start_frame()
            monitor.end_frame()
        summary = monitor.get_summary()
        assert summary["p95_frame_ms"] >= 0


class TestReset:
    def test_reset_clears_data(self) -> None:
        monitor = PerformanceMonitor()
        for _ in range(5):
            monitor.start_frame()
            monitor.end_frame()
        monitor.record_transcription(latency_ms=100.0)
        monitor.reset()
        assert len(monitor._frame_stats) == 0
        assert len(monitor._transcription_stats) == 0
        assert monitor._warn_count == 0

    def test_reset_allows_new_recording(self) -> None:
        monitor = PerformanceMonitor()
        monitor.start_frame()
        monitor.end_frame()
        monitor.reset()
        monitor.start_frame()
        monitor.end_frame()
        assert len(monitor._frame_stats) == 1
