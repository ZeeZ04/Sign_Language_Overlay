"""Capture audio from microphone in real-time and transcribe."""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
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


@dataclass
class HealthStatus:
    """Health status for audio and transcription components."""
    stream_active: bool = False
    queue_size: int = 0
    consecutive_failures: int = 0
    last_transcription_time: float | None = None
    status: str = "idle"  # "ok", "idle", "reconnecting", "failed"


class RealtimeAudio:
    """Capture audio from microphone in real-time."""

    def __init__(self, device_id: int | None = None, sample_rate: int = 16000,
                 chunk_duration_ms: int = 100, max_queue_size: int = 100) -> None:
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice not installed. Run: pip install sounddevice")

        self.device_id = device_id
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.chunk_samples = int(sample_rate * chunk_duration_ms / 1000)
        self.max_queue_size = max_queue_size

        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=max_queue_size)
        self._stream: Any = None
        self._running = False
        self._callback: Callable[[np.ndarray], None] | None = None

        # Health monitoring
        self._health_thread: threading.Thread | None = None
        self._health_status = HealthStatus()
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5

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

    @staticmethod
    def is_silence(audio: np.ndarray, threshold: float = 0.01) -> bool:
        """Return True if RMS amplitude is below threshold."""
        if len(audio) == 0:
            return True
        rms = float(np.sqrt(np.mean(audio ** 2)))
        return rms < threshold

    def _audio_callback(self, indata: np.ndarray, frames: int,
                        time_info: Any, status: Any) -> None:
        if status:
            logger.warning("Audio status: %s", status)

        audio_data = indata[:, 0].copy()

        # Backpressure: drop oldest chunk if queue is full
        if self._audio_queue.full():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                pass
            logger.debug("Audio queue full, dropped oldest chunk")

        try:
            self._audio_queue.put_nowait(audio_data)
        except queue.Full:
            pass

        if self._callback:
            try:
                self._callback(audio_data)
            except Exception as e:
                logger.error("Audio callback error: %s", e)

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
        self._reconnect_attempts = 0
        self._health_status.status = "ok"
        self._health_status.stream_active = True

        # Start health monitoring thread
        self._health_thread = threading.Thread(
            target=self._monitor_stream_health, daemon=True
        )
        self._health_thread.start()

        logger.info("Audio capture started")

    def stop_capture(self) -> None:
        if not self._running:
            return

        self._running = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._health_status.status = "idle"
        self._health_status.stream_active = False
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

    def get_health_status(self) -> HealthStatus:
        self._health_status.queue_size = self._audio_queue.qsize()
        return self._health_status

    def _monitor_stream_health(self) -> None:
        """Background thread that checks stream status periodically."""
        while self._running:
            time.sleep(2.0)
            if not self._running:
                break

            if self._stream is None:
                continue

            # Check if stream is still active
            try:
                stream_active = self._stream.active
            except Exception:
                stream_active = False

            self._health_status.stream_active = stream_active

            if not stream_active and self._running:
                logger.warning("Audio stream became inactive, attempting reconnection...")
                self._health_status.status = "reconnecting"
                self._attempt_reconnect()

    def _attempt_reconnect(self) -> None:
        """Attempt to reconnect to the audio stream with exponential backoff."""
        for attempt in range(self._max_reconnect_attempts):
            if not self._running:
                return

            delay = min(2 ** attempt, 16)
            logger.info("Reconnect attempt %d/%d (delay: %ds)",
                        attempt + 1, self._max_reconnect_attempts, delay)
            time.sleep(delay)

            try:
                if self._stream:
                    try:
                        self._stream.stop()
                        self._stream.close()
                    except Exception:
                        pass

                self._stream = sd.InputStream(
                    device=self.device_id,
                    channels=1,
                    samplerate=self.sample_rate,
                    blocksize=self.chunk_samples,
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._health_status.status = "ok"
                self._health_status.stream_active = True
                self._reconnect_attempts = 0
                logger.info("Audio stream reconnected successfully")
                return
            except Exception as e:
                logger.error("Reconnection attempt %d failed: %s", attempt + 1, e)

        self._health_status.status = "failed"
        logger.error("Failed to reconnect audio stream after %d attempts",
                      self._max_reconnect_attempts)


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

        # Error recovery
        self._consecutive_failures: int = 0
        self._max_backoff_s: float = 30.0
        self._last_transcription_time: float | None = None

    def start(self, audio_source: RealtimeAudio) -> None:
        if self._running:
            return

        self._audio_source = audio_source
        self._running = True
        self._consecutive_failures = 0
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

    def get_health_status(self) -> HealthStatus:
        return HealthStatus(
            consecutive_failures=self._consecutive_failures,
            last_transcription_time=self._last_transcription_time,
            status="ok" if self._running and self._consecutive_failures == 0 else
                   "degraded" if self._running and self._consecutive_failures > 0 else "idle",
        )

    def _transcription_loop(self) -> None:
        while self._running:
            if not self._audio_source:
                time.sleep(0.1)
                continue

            audio = self._audio_source.get_accumulated_audio(self.chunk_duration_ms)
            if audio is None or len(audio) < 1000:
                continue

            # Skip silent audio to save processing
            if RealtimeAudio.is_silence(audio):
                logger.debug("Skipping silent audio chunk")
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

                    self._last_transcription_time = timestamp
                    self._consecutive_failures = 0

                    if self._text_callback:
                        try:
                            self._text_callback(text, timestamp)
                        except Exception as e:
                            logger.error("Text callback error: %s", e)

            except Exception as e:
                self._consecutive_failures += 1
                backoff = min(2 ** self._consecutive_failures, self._max_backoff_s)
                logger.error("Transcription error (attempt %d, backoff %.1fs): %s",
                             self._consecutive_failures, backoff, e)
                time.sleep(backoff)
