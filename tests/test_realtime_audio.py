"""Tests for the real-time audio module.

Most tests skip if sounddevice is not installed.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.realtime_audio import SOUNDDEVICE_AVAILABLE, HealthStatus, RealtimeAudio


def _sounddevice_available() -> bool:
    return SOUNDDEVICE_AVAILABLE


class TestRealtimeAudioInit:
    def test_import_check(self) -> None:
        from src.realtime_audio import RealtimeAudio, AudioDevice
        assert AudioDevice is not None

    @pytest.mark.skipif(not _sounddevice_available(), reason="sounddevice not installed")
    def test_list_devices(self) -> None:
        devices = RealtimeAudio.list_devices()
        assert isinstance(devices, list)

    @pytest.mark.skipif(not _sounddevice_available(), reason="sounddevice not installed")
    def test_init(self) -> None:
        audio = RealtimeAudio(sample_rate=16000, chunk_duration_ms=100)
        assert audio.is_running() is False
        assert audio.sample_rate == 16000
        assert audio.chunk_samples == 1600

    def test_raises_without_sounddevice(self) -> None:
        if _sounddevice_available():
            pytest.skip("sounddevice is installed")
        with pytest.raises(RuntimeError, match="sounddevice not installed"):
            RealtimeAudio()


class TestRealtimeTranscriber:
    def test_import(self) -> None:
        from src.realtime_audio import RealtimeTranscriber
        assert RealtimeTranscriber is not None


class TestSilenceDetection:
    def test_zero_array_is_silence(self) -> None:
        audio = np.zeros(1600, dtype=np.float32)
        assert RealtimeAudio.is_silence(audio) is True

    def test_loud_array_is_not_silence(self) -> None:
        audio = np.ones(1600, dtype=np.float32) * 0.5
        assert RealtimeAudio.is_silence(audio) is False

    def test_quiet_array_is_silence(self) -> None:
        audio = np.ones(1600, dtype=np.float32) * 0.005
        assert RealtimeAudio.is_silence(audio) is True

    def test_empty_array_is_silence(self) -> None:
        audio = np.array([], dtype=np.float32)
        assert RealtimeAudio.is_silence(audio) is True

    def test_custom_threshold(self) -> None:
        audio = np.ones(1600, dtype=np.float32) * 0.05
        assert RealtimeAudio.is_silence(audio, threshold=0.1) is True
        assert RealtimeAudio.is_silence(audio, threshold=0.01) is False


class TestHealthStatus:
    def test_health_status_fields(self) -> None:
        status = HealthStatus()
        assert status.stream_active is False
        assert status.queue_size == 0
        assert status.consecutive_failures == 0
        assert status.last_transcription_time is None
        assert status.status == "idle"

    def test_health_status_custom(self) -> None:
        status = HealthStatus(
            stream_active=True,
            queue_size=50,
            consecutive_failures=2,
            last_transcription_time=1234567890.0,
            status="degraded",
        )
        assert status.stream_active is True
        assert status.queue_size == 50
        assert status.consecutive_failures == 2

    @pytest.mark.skipif(not _sounddevice_available(), reason="sounddevice not installed")
    def test_audio_health_status(self) -> None:
        audio = RealtimeAudio(sample_rate=16000, chunk_duration_ms=100)
        status = audio.get_health_status()
        assert isinstance(status, HealthStatus)
        assert status.status == "idle"

    def test_transcriber_health_status(self) -> None:
        from src.realtime_audio import RealtimeTranscriber
        transcriber = RealtimeTranscriber(speech_to_text=None)
        status = transcriber.get_health_status()
        assert isinstance(status, HealthStatus)
        assert status.status == "idle"


class TestQueueBackpressure:
    @pytest.mark.skipif(not _sounddevice_available(), reason="sounddevice not installed")
    def test_max_queue_size_parameter(self) -> None:
        audio = RealtimeAudio(sample_rate=16000, chunk_duration_ms=100, max_queue_size=10)
        assert audio.max_queue_size == 10

    @pytest.mark.skipif(not _sounddevice_available(), reason="sounddevice not installed")
    def test_queue_overflow_drops_oldest(self) -> None:
        audio = RealtimeAudio(sample_rate=16000, chunk_duration_ms=100, max_queue_size=3)
        # Manually fill queue past capacity
        for i in range(5):
            chunk = np.ones(100, dtype=np.float32) * i
            audio._audio_callback(chunk.reshape(-1, 1), 100, None, None)
        # Queue should have at most max_queue_size items
        assert audio._audio_queue.qsize() <= audio.max_queue_size


class TestCallbackProtection:
    @pytest.mark.skipif(not _sounddevice_available(), reason="sounddevice not installed")
    def test_callback_exception_does_not_propagate(self) -> None:
        audio = RealtimeAudio(sample_rate=16000, chunk_duration_ms=100)

        def bad_callback(data: np.ndarray) -> None:
            raise ValueError("callback error")

        audio.set_callback(bad_callback)
        chunk = np.zeros((100, 1), dtype=np.float32)
        # Should not raise
        audio._audio_callback(chunk, 100, None, None)
        # Queue should still have the data
        assert audio._audio_queue.qsize() == 1
