"""Tests for the real-time audio module.

Most tests skip if sounddevice is not installed.
"""

from __future__ import annotations

import pytest

from src.realtime_audio import SOUNDDEVICE_AVAILABLE


def _sounddevice_available() -> bool:
    return SOUNDDEVICE_AVAILABLE


class TestRealtimeAudioInit:
    def test_import_check(self) -> None:
        # Should at least import without error
        from src.realtime_audio import RealtimeAudio, AudioDevice
        assert AudioDevice is not None

    @pytest.mark.skipif(not _sounddevice_available(), reason="sounddevice not installed")
    def test_list_devices(self) -> None:
        from src.realtime_audio import RealtimeAudio
        devices = RealtimeAudio.list_devices()
        assert isinstance(devices, list)

    @pytest.mark.skipif(not _sounddevice_available(), reason="sounddevice not installed")
    def test_init(self) -> None:
        from src.realtime_audio import RealtimeAudio
        audio = RealtimeAudio(sample_rate=16000, chunk_duration_ms=100)
        assert audio.is_running() is False
        assert audio.sample_rate == 16000
        assert audio.chunk_samples == 1600

    def test_raises_without_sounddevice(self) -> None:
        if _sounddevice_available():
            pytest.skip("sounddevice is installed")
        from src.realtime_audio import RealtimeAudio
        with pytest.raises(RuntimeError, match="sounddevice not installed"):
            RealtimeAudio()


class TestRealtimeTranscriber:
    def test_import(self) -> None:
        from src.realtime_audio import RealtimeTranscriber
        assert RealtimeTranscriber is not None
