"""Synchronize sign display with subtitle timing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .subtitle_parser import SubtitleEntry
from .text_to_sign import SignToken, TextToSignConverter

if TYPE_CHECKING:
    from .word_sign_mapper import WordSignMapper

logger = logging.getLogger(__name__)

MIN_SIGN_DURATION_MS = 100
MAX_SIGN_DURATION_MS = 800


@dataclass
class ScheduledSign:
    token: SignToken
    start_time: float  # seconds
    end_time: float  # seconds


class TimingController:
    def __init__(
        self,
        subtitles: list[SubtitleEntry],
        converter: TextToSignConverter,
        word_mapper: WordSignMapper | None = None,
    ) -> None:
        self.subtitles = subtitles
        self.converter = converter
        self.word_mapper = word_mapper
        self._schedule: list[ScheduledSign] = []
        self._current_time: float = 0.0
        self._playing: bool = False
        self._current_index: int = 0

        self._build_schedule()

    def start(self, start_time: float = 0.0) -> None:
        self._current_time = start_time
        self._playing = True
        self._current_index = self._find_index_at_time(start_time)
        logger.info("Playback started at %.2fs", start_time)

    def pause(self) -> None:
        self._playing = False
        logger.info("Playback paused at %.2fs", self._current_time)

    def resume(self) -> None:
        self._playing = True
        logger.info("Playback resumed at %.2fs", self._current_time)

    def seek(self, time_seconds: float) -> None:
        self._current_time = time_seconds
        self._current_index = self._find_index_at_time(time_seconds)
        logger.info("Seeked to %.2fs", time_seconds)

    def get_current_sign(self) -> SignToken | None:
        if not self._schedule:
            return None

        for i in range(self._current_index, len(self._schedule)):
            item = self._schedule[i]
            if item.start_time <= self._current_time < item.end_time:
                self._current_index = i
                return item.token
            if item.start_time > self._current_time:
                break

        return None

    def update(self, dt: float) -> None:
        if self._playing:
            self._current_time += dt

    @property
    def current_time(self) -> float:
        return self._current_time

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def total_duration(self) -> float:
        if not self._schedule:
            return 0.0
        return self._schedule[-1].end_time

    def _build_schedule(self) -> None:
        self._schedule = []

        for entry in self.subtitles:
            total_duration = entry.end_time - entry.start_time
            if total_duration <= 0:
                continue

            tokens = self._convert_entry(entry.text)
            if not tokens:
                continue

            per_sign_ms = (total_duration * 1000) / len(tokens)
            clamped_ms = max(MIN_SIGN_DURATION_MS, min(MAX_SIGN_DURATION_MS, per_sign_ms))

            actual_total_ms = clamped_ms * len(tokens)
            actual_total_s = actual_total_ms / 1000.0

            # Center the sign sequence within the subtitle time window
            offset = entry.start_time + (total_duration - actual_total_s) / 2
            offset = max(offset, entry.start_time)

            for i, token in enumerate(tokens):
                # Use the token's own duration ratio to scale timing
                start = offset + (i * clamped_ms / 1000.0)
                end = start + clamped_ms / 1000.0
                self._schedule.append(ScheduledSign(
                    token=token,
                    start_time=start,
                    end_time=min(end, entry.end_time),
                ))

        logger.info("Built schedule with %d signs from %d subtitles", len(self._schedule), len(self.subtitles))

    def _convert_entry(self, text: str) -> list[SignToken]:
        if self.word_mapper is not None:
            sequences = self.word_mapper.map_text(text)
            tokens: list[SignToken] = []
            for seq in sequences:
                tokens.extend(seq.tokens)
            return tokens
        return self.converter.convert(text)

    def _find_index_at_time(self, time_seconds: float) -> int:
        for i, item in enumerate(self._schedule):
            if item.end_time > time_seconds:
                return i
        return len(self._schedule) - 1 if self._schedule else 0
