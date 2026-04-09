"""Tests for the subtitle parser module."""

import pytest
from pathlib import Path

from src.subtitle_parser import SubtitleParser, SubtitleEntry

SAMPLE_DIR = Path(__file__).parent / "sample_files"


class TestSubtitleParserSRT:
    def test_parse_srt_file(self) -> None:
        parser = SubtitleParser(str(SAMPLE_DIR / "sample.srt"))
        entries = parser.parse()
        assert len(entries) == 3
        assert entries[0].text == "Hello world"
        assert entries[1].text == "This is a test"
        assert entries[2].text == "Numbers 123"

    def test_srt_timing(self) -> None:
        parser = SubtitleParser(str(SAMPLE_DIR / "sample.srt"))
        entries = parser.parse()
        assert entries[0].start_time == pytest.approx(1.0)
        assert entries[0].end_time == pytest.approx(3.0)
        assert entries[1].start_time == pytest.approx(4.0)
        assert entries[1].end_time == pytest.approx(6.5)

    def test_srt_indices(self) -> None:
        parser = SubtitleParser(str(SAMPLE_DIR / "sample.srt"))
        entries = parser.parse()
        assert entries[0].index == 1
        assert entries[1].index == 2
        assert entries[2].index == 3


class TestSubtitleParserVTT:
    def test_parse_vtt_file(self) -> None:
        parser = SubtitleParser(str(SAMPLE_DIR / "sample.vtt"))
        entries = parser.parse()
        assert len(entries) == 3
        assert entries[0].text == "Hello world"

    def test_vtt_timing(self) -> None:
        parser = SubtitleParser(str(SAMPLE_DIR / "sample.vtt"))
        entries = parser.parse()
        assert entries[0].start_time == pytest.approx(1.0)
        assert entries[0].end_time == pytest.approx(3.0)


class TestSubtitleParserEdgeCases:
    def test_get_entry_at_time(self) -> None:
        parser = SubtitleParser(str(SAMPLE_DIR / "sample.srt"))
        parser.parse()
        entry = parser.get_entry_at_time(2.0)
        assert entry is not None
        assert entry.text == "Hello world"

    def test_get_entry_at_time_between_subtitles(self) -> None:
        parser = SubtitleParser(str(SAMPLE_DIR / "sample.srt"))
        parser.parse()
        entry = parser.get_entry_at_time(3.5)
        assert entry is None

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            SubtitleParser("nonexistent.srt")

    def test_unsupported_format(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "test.txt"
        bad_file.write_text("not a subtitle")
        with pytest.raises(ValueError, match="Unsupported subtitle format"):
            SubtitleParser(str(bad_file))

    def test_strips_html_tags(self, tmp_path: Path) -> None:
        srt_content = (
            "1\n"
            "00:00:01,000 --> 00:00:03,000\n"
            "<b>Bold text</b> and <i>italic</i>\n"
        )
        srt_file = tmp_path / "html.srt"
        srt_file.write_text(srt_content)
        parser = SubtitleParser(str(srt_file))
        entries = parser.parse()
        assert entries[0].text == "Bold text and italic"

    def test_handles_empty_subtitles(self, tmp_path: Path) -> None:
        srt_content = (
            "1\n"
            "00:00:01,000 --> 00:00:02,000\n"
            "\n"
            "\n"
            "2\n"
            "00:00:03,000 --> 00:00:04,000\n"
            "Actual text\n"
        )
        srt_file = tmp_path / "empty.srt"
        srt_file.write_text(srt_content)
        parser = SubtitleParser(str(srt_file))
        entries = parser.parse()
        # Empty subtitle should be filtered out
        assert all(e.text for e in entries)
