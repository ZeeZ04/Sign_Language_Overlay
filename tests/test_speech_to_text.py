"""Tests for the speech-to-text module.

Note: Most tests are skipped if Whisper is not installed,
since it requires large dependencies (torch, etc.).
"""

from __future__ import annotations

import pytest

from src.speech_to_text import SpeechToText, SUPPORTED_AUDIO, SUPPORTED_VIDEO, MODEL_SIZES


def _whisper_available() -> bool:
    try:
        import whisper
        return True
    except ImportError:
        return False


class TestSpeechToTextInit:
    def test_valid_model_sizes(self) -> None:
        for size in MODEL_SIZES:
            stt = SpeechToText(model_size=size)
            assert stt.model_size == size

    def test_invalid_model_size(self) -> None:
        with pytest.raises(ValueError, match="Invalid model size"):
            SpeechToText(model_size="gigantic")

    def test_not_loaded_initially(self) -> None:
        stt = SpeechToText()
        assert stt.is_loaded is False

    def test_supported_formats(self) -> None:
        assert ".mp3" in SUPPORTED_AUDIO
        assert ".wav" in SUPPORTED_AUDIO
        assert ".mp4" in SUPPORTED_VIDEO
        assert ".mkv" in SUPPORTED_VIDEO


class TestSpeechToTextFile:
    def test_file_not_found(self) -> None:
        stt = SpeechToText()
        with pytest.raises(FileNotFoundError):
            stt.transcribe_file("nonexistent.wav")

    def test_unsupported_format(self, tmp_path) -> None:
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("not audio")
        stt = SpeechToText()
        with pytest.raises(ValueError, match="Unsupported file format"):
            stt.transcribe_file(str(bad_file))


@pytest.mark.skipif(not _whisper_available(), reason="Whisper not installed")
class TestSpeechToTextTranscribe:
    def test_load_model(self) -> None:
        stt = SpeechToText(model_size="tiny")
        stt.load_model()
        assert stt.is_loaded is True

    def test_transcribe_returns_segments(self, tmp_path) -> None:
        """Create a minimal WAV file and transcribe it."""
        import numpy as np
        from scipy.io import wavfile

        # Generate 2 seconds of silence
        sample_rate = 16000
        audio = np.zeros(sample_rate * 2, dtype=np.float32)
        wav_path = str(tmp_path / "silence.wav")
        wavfile.write(wav_path, sample_rate, audio)

        stt = SpeechToText(model_size="tiny")
        stt.load_model()
        segments = stt.transcribe_file(wav_path)
        # Silence may or may not produce segments, but should not crash
        assert isinstance(segments, list)


class TestSpeechToTextExtract:
    def test_extract_nonexistent_video(self) -> None:
        stt = SpeechToText()
        with pytest.raises(FileNotFoundError):
            stt.extract_audio_from_video("nonexistent.mp4")
