"""Capture audio from microphone in real-time and transcribe."""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from typing import Callable, Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    sd = None  # type: ignore[assignment]
    SOUNDDEVICE_AVAILABLE = False
    logger.debug("sounddevice not installed. Real-time audio disabled.")


@dataclass
class AudioDevice:
    """Audio input device info."""
    id: int
    name: str
    channels: int
    sample_rate: float
    is_default: bool = False


class RealtimeAudio:
    """Capture audio from microphone in real-time."""

    def __init__(self, device_id: int | None = None, sample_rate: int = 16000,
                 chunk_duration_ms: int = 100) -> None:
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice not installed. Run: pip install sounddevice")

        self.device_id = device_id
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_samples = int(sample_rate * chunk_duration_ms / 1000)

        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: Any = None
        self._running = False
        self._callback: Callable[[np.ndarray], None] | None = None

    @staticmethod
    def list_devices() -> list[AudioDevice]:
        if not SOUNDDEVICE_AVAILABLE:
            return []

        devices = []
        default_input = sd.default.device[0]

        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                devices.append(AudioDevice(
                    id=i,
                    name=dev["name"],
                    channels=dev["max_input_channels"],
                    sample_rate=dev["default_samplerate"],
                    is_default=(i == default_input),
                ))
        return devices

    def _audio_callback(self, indata: np.ndarray, frames: int,
                        time_info: Any, status: Any) -> None:
        if status:
            logger.warning("Audio status: %s", status)

        audio_data = indata[:, 0].copy()
        self._audio_queue.put(audio_data)

        if self._callback:
            self._callback(audio_data)

    def start_capture(self) -> None:
        if self._running:
            return

        self._stream = sd.InputStream(
            device=self.device_id,
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.chunk_samples,
            callback=self._audio_callback,
        )
        self._stream.start()
        self._running = True
        logger.info("Audio capture started")

    def stop_capture(self) -> None:
        if not self._running:
            return

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._running = False
        logger.info("Audio capture stopped")

    def get_audio_chunk(self, timeout_ms: int = 1000) -> np.ndarray | None:
        try:
            return self._audio_queue.get(timeout=timeout_ms / 1000)
        except queue.Empty:
            return None

    def get_accumulated_audio(self, duration_ms: int) -> np.ndarray | None:
        chunks = []
        target_samples = int(self.sample_rate * duration_ms / 1000)
        collected_samples = 0

        while collected_samples < target_samples:
            chunk = self.get_audio_chunk(timeout_ms=100)
            if chunk is None:
                break
            chunks.append(chunk)
            collected_samples += len(chunk)

        if not chunks:
            return None

        return np.concatenate(chunks)

    def set_callback(self, callback: Callable[[np.ndarray], None] | None) -> None:
        self._callback = callback

    def is_running(self) -> bool:
        return self._running

    def clear_queue(self) -> None:
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break


class RealtimeTranscriber:
    """Transcribe audio in real-time using Whisper.

    Accumulates audio chunks and sends to Whisper periodically.
    """

    def __init__(self, speech_to_text: Any, chunk_duration_ms: int = 3000) -> None:
        self.stt = speech_to_text
        self.chunk_duration_ms = chunk_duration_ms

        self._audio_source: RealtimeAudio | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._text_callback: Callable[[str, float], None] | None = None
        self._latest_text: str | None = None
        self._lock = threading.Lock()

    def start(self, audio_source: RealtimeAudio) -> None:
        if self._running:
            return

        self._audio_source = audio_source
        self._running = True
        self._thread = threading.Thread(target=self._transcription_loop, daemon=True)
        self._thread.start()
        logger.info("Real-time transcription started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        logger.info("Real-time transcription stopped")

    def get_latest_text(self) -> str | None:
        with self._lock:
            return self._latest_text

    def set_text_callback(self, callback: Callable[[str, float], None] | None) -> None:
        self._text_callback = callback

    def _transcription_loop(self) -> None:
        import time

        while self._running:
            if not self._audio_source:
                time.sleep(0.1)
                continue

            audio = self._audio_source.get_accumulated_audio(self.chunk_duration_ms)
            if audio is None or len(audio) < 1000:
                continue

            try:
                segments = self.stt.transcribe_audio_array(
                    audio,
                    self._audio_source.sample_rate,
                )

                if segments:
                    text = " ".join(seg.text for seg in segments)
                    timestamp = time.time()

                    with self._lock:
                        self._latest_text = text

                    if self._text_callback:
                        self._text_callback(text, timestamp)

            except Exception as e:
                logger.error("Transcription error: %s", e)
