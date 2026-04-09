"""Parse SRT and VTT subtitle files into a unified format."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import pysrt
import webvtt

logger = logging.getLogger(__name__)

HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class SubtitleEntry:
    index: int
    start_time: float  # seconds
    end_time: float  # seconds
    text: str


class SubtitleParser:
    def __init__(self, filepath: str) -> None:
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"Subtitle file not found: {filepath}")

        ext = self.filepath.suffix.lower()
        if ext not in (".srt", ".vtt"):
            raise ValueError(f"Unsupported subtitle format: {ext}. Use .srt or .vtt")

        self._entries: list[SubtitleEntry] = []

    def parse(self) -> list[SubtitleEntry]:
        ext = self.filepath.suffix.lower()
        if ext == ".srt":
            self._entries = self._parse_srt()
        elif ext == ".vtt":
            self._entries = self._parse_vtt()

        logger.info("Parsed %d subtitle entries from %s", len(self._entries), self.filepath.name)
        return self._entries

    def get_entry_at_time(self, time_seconds: float) -> SubtitleEntry | None:
        for entry in self._entries:
            if entry.start_time <= time_seconds < entry.end_time:
                return entry
        return None

    def _parse_srt(self) -> list[SubtitleEntry]:
        subs = pysrt.open(str(self.filepath), encoding="utf-8-sig")
        entries: list[SubtitleEntry] = []
        for sub in subs:
            text = self._clean_text(sub.text)
            if not text:
                continue
            entries.append(SubtitleEntry(
                index=sub.index,
                start_time=self._srt_time_to_seconds(sub.start),
                end_time=self._srt_time_to_seconds(sub.end),
                text=text,
            ))
        return entries

    def _parse_vtt(self) -> list[SubtitleEntry]:
        captions = webvtt.read(str(self.filepath))
        entries: list[SubtitleEntry] = []
        for i, caption in enumerate(captions, start=1):
            text = self._clean_text(caption.text)
            if not text:
                continue
            entries.append(SubtitleEntry(
                index=i,
                start_time=self._vtt_timestamp_to_seconds(caption.start),
                end_time=self._vtt_timestamp_to_seconds(caption.end),
                text=text,
            ))
        return entries

    @staticmethod
    def _clean_text(text: str) -> str:
        text = HTML_TAG_RE.sub("", text)
        text = " ".join(text.split())
        return text.strip()

    @staticmethod
    def _srt_time_to_seconds(t: pysrt.SubRipTime) -> float:
        return t.hours * 3600 + t.minutes * 60 + t.seconds + t.milliseconds / 1000.0

    @staticmethod
    def _vtt_timestamp_to_seconds(timestamp: str) -> float:
        parts = timestamp.split(":")
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        return float(timestamp)
