"""Convert audio files to timestamped text using OpenAI Whisper."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".wma", ".aac"}
SUPPORTED_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv"}
MODEL_SIZES = ("tiny", "base", "small", "medium", "large")


@dataclass
class TranscriptSegment:
    start_time: float  # seconds
    end_time: float  # seconds
    text: str
    confidence: float  # 0.0 to 1.0


class SpeechToText:
    def __init__(self, model_size: str = "base", device: str = "auto") -> None:
        if model_size not in MODEL_SIZES:
            raise ValueError(f"Invalid model size: {model_size}. Use one of {MODEL_SIZES}")
        self.model_size = model_size
        self.device = device
        self._model = None

    def load_model(self) -> None:
        try:
            import whisper
        except ImportError:
            raise ImportError(
                "openai-whisper is not installed. "
                "Install it with: pip install openai-whisper torch torchaudio"
            )

        device = self._resolve_device()
        logger.info("Loading Whisper '%s' model on %s...", self.model_size, device)
        self._model = whisper.load_model(self.model_size, device=device)
        logger.info("Whisper model loaded successfully.")

    def transcribe_file(self, audio_path: str) -> list[TranscriptSegment]:
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        ext = path.suffix.lower()
        if ext in SUPPORTED_VIDEO:
            logger.info("Video file detected, extracting audio...")
            audio_path = self.extract_audio_from_video(audio_path)
        elif ext not in SUPPORTED_AUDIO:
            raise ValueError(f"Unsupported file format: {ext}")

        if self._model is None:
            self.load_model()

        logger.info("Transcribing: %s", audio_path)
        result = self._model.transcribe(
            audio_path,
            word_timestamps=True,
            verbose=False,
        )

        segments = self._parse_result(result)
        logger.info("Transcribed %d segments from %s", len(segments), Path(audio_path).name)
        return segments

    def transcribe_audio_array(self, audio, sample_rate: int) -> list[TranscriptSegment]:
        if self._model is None:
            self.load_model()

        import whisper
        # Resample to 16kHz if needed (Whisper expects 16kHz)
        if sample_rate != 16000:
            import numpy as np
            from scipy.signal import resample

            duration = len(audio) / sample_rate
            target_samples = int(duration * 16000)
            audio = resample(audio, target_samples).astype(np.float32)

        result = self._model.transcribe(
            audio,
            word_timestamps=True,
            verbose=False,
        )
        return self._parse_result(result)

    def extract_audio_from_video(self, video_path: str) -> str:
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Create temp wav file
        temp_dir = tempfile.gettempdir()
        output_path = str(Path(temp_dir) / f"{path.stem}_audio.wav")

        cmd = [
            "ffmpeg", "-y",
            "-i", str(path),
            "-vn",  # no video
            "-acodec", "pcm_s16le",  # 16-bit PCM
            "-ar", "16000",  # 16kHz sample rate
            "-ac", "1",  # mono
            output_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Install it with: brew install ffmpeg (macOS) "
                "or apt install ffmpeg (Linux)"
            )

        logger.info("Extracted audio to: %s", output_path)
        return output_path

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _resolve_device(self) -> str:
        if self.device != "auto":
            return self.device

        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "cpu"  # MPS has issues with Whisper, fall back to CPU
        except ImportError:
            pass
        return "cpu"

    def _parse_result(self, result: dict) -> list[TranscriptSegment]:
        segments: list[TranscriptSegment] = []

        for seg in result.get("segments", []):
            text = seg.get("text", "").strip()
            if not text:
                continue

            segments.append(TranscriptSegment(
                start_time=seg.get("start", 0.0),
                end_time=seg.get("end", 0.0),
                text=text,
                confidence=seg.get("avg_logprob", 0.0),
            ))

        return segments
