"""Integration tests for the sign language overlay pipeline.

Tests the full flow from subtitle text through grammar transformation,
sign conversion, timing, rendering, and animation.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pygame

from src.grammar_transformer import ASLGrammarTransformer
from src.subtitle_parser import SubtitleEntry, SubtitleParser
from src.text_to_sign import SignToken, TextToSignConverter
from src.timing_controller import TimingController
from src.sign_renderer import SignRenderer
from src.animation_controller import AnimationController
from src.expression_overlay import ExpressionOverlay


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.NOFRAME)
    yield
    pygame.quit()


@pytest.fixture
def converter() -> TextToSignConverter:
    return TextToSignConverter(language="asl")


@pytest.fixture
def grammar() -> ASLGrammarTransformer:
    return ASLGrammarTransformer(language="asl")


@pytest.fixture
def assets_dir() -> str:
    return str(Path(__file__).parent.parent / "assets" / "signs" / "asl")


@pytest.fixture
def renderer(assets_dir: str) -> SignRenderer:
    r = SignRenderer(assets_path=assets_dir, size=100)
    r.load_assets()
    return r


@pytest.fixture
def sample_subtitles() -> list[SubtitleEntry]:
    return [
        SubtitleEntry(index=1, start_time=0.0, end_time=2.0, text="Hello world"),
        SubtitleEntry(index=2, start_time=2.5, end_time=5.0, text="How are you?"),
        SubtitleEntry(index=3, start_time=5.5, end_time=8.0, text="I went to the store yesterday"),
    ]


# ── Subtitle → Sign Token Pipeline ───────────────────────────────────────────

class TestSubtitleToSignPipeline:
    def test_text_to_tokens_produces_sign_tokens(self, converter: TextToSignConverter) -> None:
        tokens = converter.convert("hello")
        assert len(tokens) == 5
        assert all(isinstance(t, SignToken) for t in tokens)
        assert [t.sign_id for t in tokens] == ["h", "e", "l", "l", "o"]

    def test_text_with_spaces(self, converter: TextToSignConverter) -> None:
        tokens = converter.convert("hi there")
        sign_ids = [t.sign_id for t in tokens]
        assert "space" in sign_ids

    def test_numbers_convert(self, converter: TextToSignConverter) -> None:
        tokens = converter.convert("123")
        assert len(tokens) == 3
        assert [t.sign_id for t in tokens] == ["1", "2", "3"]

    def test_word_mapper_integration(self, assets_dir: str) -> None:
        from src.word_sign_mapper import WordSignMapper
        mapper = WordSignMapper(assets_path=assets_dir, language="asl")
        mapper.load_word_signs()
        sequences = mapper.map_text("hello world")
        # "hello" should be a word sign, "world" fingerspelled
        methods = [s.method for s in sequences]
        assert "word_sign" in methods

    def test_grammar_then_converter(
        self, grammar: ASLGrammarTransformer, converter: TextToSignConverter
    ) -> None:
        result = grammar.transform("I went to the store yesterday")
        tokens = converter.convert(result.text)
        # Should start with YESTERDAY letters
        assert tokens[0].sign_id == "y"
        assert all(isinstance(t, SignToken) for t in tokens)

    def test_grammar_then_word_mapper(self, grammar: ASLGrammarTransformer, assets_dir: str) -> None:
        from src.word_sign_mapper import WordSignMapper
        mapper = WordSignMapper(assets_path=assets_dir, language="asl")
        mapper.load_word_signs()

        result = grammar.transform("I don't like coffee")
        sequences = mapper.map_text(result.text)
        all_tokens = [t for s in sequences for t in s.tokens]
        assert len(all_tokens) > 0


# ── Timing Synchronization ────────────────────────────────────────────────────

class TestTimingSynchronization:
    def test_schedule_built_from_subtitles(
        self, sample_subtitles: list[SubtitleEntry], converter: TextToSignConverter
    ) -> None:
        controller = TimingController(subtitles=sample_subtitles, converter=converter)
        assert len(controller._schedule) > 0

    def test_signs_within_subtitle_windows(
        self, sample_subtitles: list[SubtitleEntry], converter: TextToSignConverter
    ) -> None:
        controller = TimingController(subtitles=sample_subtitles, converter=converter)
        for scheduled in controller._schedule:
            # Each sign should be near some subtitle's time range.
            # When clamped per-sign duration exceeds subtitle duration,
            # signs can overflow slightly, so allow a small tolerance.
            tolerance = 0.5  # seconds
            near_some_subtitle = any(
                sub.start_time <= scheduled.start_time <= sub.end_time + tolerance
                for sub in sample_subtitles
            )
            assert near_some_subtitle, (
                f"Sign at {scheduled.start_time:.2f}s not near any subtitle window"
            )

    def test_seek_returns_sign_at_time(
        self, sample_subtitles: list[SubtitleEntry], converter: TextToSignConverter
    ) -> None:
        controller = TimingController(subtitles=sample_subtitles, converter=converter)
        controller.start()
        controller.seek(1.0)
        sign = controller.get_current_sign()
        assert sign is not None

    def test_pause_stops_time(
        self, sample_subtitles: list[SubtitleEntry], converter: TextToSignConverter
    ) -> None:
        controller = TimingController(subtitles=sample_subtitles, converter=converter)
        controller.start()
        controller.update(1.0)
        time_before = controller.current_time
        controller.pause()
        controller.update(1.0)
        assert controller.current_time == time_before

    def test_resume_continues_time(
        self, sample_subtitles: list[SubtitleEntry], converter: TextToSignConverter
    ) -> None:
        controller = TimingController(subtitles=sample_subtitles, converter=converter)
        controller.start()
        controller.pause()
        controller.resume()
        controller.update(0.5)
        assert controller.current_time > 0

    def test_grammar_transformer_integration(
        self, sample_subtitles: list[SubtitleEntry], converter: TextToSignConverter,
        grammar: ASLGrammarTransformer
    ) -> None:
        controller = TimingController(
            subtitles=sample_subtitles, converter=converter,
            grammar_transformer=grammar,
        )
        assert len(controller._schedule) > 0
        controller.start()
        sign = controller.get_current_sign()
        assert sign is not None

    def test_total_duration_covers_subtitles(
        self, sample_subtitles: list[SubtitleEntry], converter: TextToSignConverter
    ) -> None:
        controller = TimingController(subtitles=sample_subtitles, converter=converter)
        assert controller.total_duration > 0


# ── Rendering Pipeline ────────────────────────────────────────────────────────

class TestRenderingPipeline:
    def test_renderer_loads_assets(self, renderer: SignRenderer) -> None:
        assert len(renderer._cache) > 0

    def test_renderer_returns_surface_for_letter(self, renderer: SignRenderer) -> None:
        surface = renderer.get_sign_surface("a")
        assert isinstance(surface, pygame.Surface)

    def test_renderer_returns_none_for_space(self, renderer: SignRenderer) -> None:
        assert renderer.get_sign_surface("space") is None

    def test_renderer_returns_placeholder_for_unknown(self, renderer: SignRenderer) -> None:
        surface = renderer.get_sign_surface("zzz_nonexistent")
        assert isinstance(surface, pygame.Surface)

    def test_animation_fade_produces_surface(self, renderer: SignRenderer) -> None:
        animator = AnimationController(transition_ms=100, transition_type="fade")
        s1 = renderer.get_sign_surface("a")
        s2 = renderer.get_sign_surface("b")
        animator.set_sign(s1)
        animator.update(200)
        animator.set_sign(s2)
        animator.update(50)  # mid-transition
        frame = animator.get_current_frame()
        assert isinstance(frame, pygame.Surface)

    def test_animation_slide_produces_surface(self, renderer: SignRenderer) -> None:
        animator = AnimationController(transition_ms=100, transition_type="slide")
        s1 = renderer.get_sign_surface("a")
        animator.set_sign(s1)
        animator.update(200)
        s2 = renderer.get_sign_surface("b")
        animator.set_sign(s2)
        animator.update(50)
        frame = animator.get_current_frame()
        assert isinstance(frame, pygame.Surface)

    def test_animation_cut_immediate(self, renderer: SignRenderer) -> None:
        animator = AnimationController(transition_ms=100, transition_type="cut")
        s1 = renderer.get_sign_surface("a")
        animator.set_sign(s1)
        assert not animator.is_transitioning

    def test_expression_overlay_renders(self) -> None:
        expr = ExpressionOverlay(font_size=24)
        hint = expr.infer_expression("Are you okay?")
        assert hint is not None
        expr.set_expression(hint)
        surface = expr.render((120, 120))
        assert isinstance(surface, pygame.Surface)


# ── Real-time Pipeline (Mocked) ──────────────────────────────────────────────

class TestRealtimePipeline:
    def test_mock_transcription_to_signs(self, converter: TextToSignConverter) -> None:
        """Simulate what _run_realtime does: transcribed text → signs."""
        transcribed_text = "Hello how are you"
        grammar = ASLGrammarTransformer(language="asl")
        result = grammar.transform(transcribed_text)
        tokens = converter.convert(result.text)
        assert len(tokens) > 0

    def test_mock_realtime_loop(
        self, converter: TextToSignConverter, renderer: SignRenderer
    ) -> None:
        """Simulate the core of the real-time loop."""
        animator = AnimationController(transition_ms=50, transition_type="fade")

        texts = ["Hello", "How are you", "Goodbye"]
        for text in texts:
            tokens = converter.convert(text)
            if tokens:
                surface = renderer.get_sign_surface(tokens[0].sign_id)
                animator.set_sign(surface)
                animator.update(100)
                frame = animator.get_current_frame()
                # Should always get some frame
                assert frame is None or isinstance(frame, pygame.Surface)


# ── CLI Argument Parsing ──────────────────────────────────────────────────────

class TestCLIArgParsing:
    def test_subtitle_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from main import parse_args
        monkeypatch.setattr(sys, "argv", ["main.py", "-s", "test.srt"])
        args = parse_args()
        assert args.subtitle == "test.srt"

    def test_audio_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from main import parse_args
        monkeypatch.setattr(sys, "argv", ["main.py", "-a", "audio.mp3"])
        args = parse_args()
        assert args.audio == "audio.mp3"

    def test_realtime_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from main import parse_args
        monkeypatch.setattr(sys, "argv", ["main.py", "--realtime"])
        args = parse_args()
        assert args.realtime is True

    def test_language_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from main import parse_args
        monkeypatch.setattr(sys, "argv", ["main.py", "-s", "test.srt", "-l", "bsl"])
        args = parse_args()
        assert args.language == "bsl"

    def test_mutually_exclusive_inputs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from main import parse_args
        monkeypatch.setattr(sys, "argv", ["main.py", "-s", "test.srt", "-a", "audio.mp3"])
        with pytest.raises(SystemExit):
            parse_args()

    def test_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from main import parse_args
        monkeypatch.setattr(sys, "argv", ["main.py", "-s", "test.srt"])
        args = parse_args()
        assert args.language is None
        assert args.position is None
        assert args.size is None
        assert args.verbose is False
        assert args.use_word_signs is False
        assert args.show_expressions is False

    def test_all_feature_flags(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from main import parse_args
        monkeypatch.setattr(sys, "argv", [
            "main.py", "-s", "test.srt",
            "--use-word-signs", "--show-expressions", "--use-3d",
            "--transition", "slide", "-p", "top-left", "--size", "300",
        ])
        args = parse_args()
        assert args.use_word_signs is True
        assert args.show_expressions is True
        assert args.use_3d is True
        assert args.transition == "slide"
        assert args.position == "top-left"
        assert args.size == 300


# ── Error Scenarios ───────────────────────────────────────────────────────────

class TestErrorScenarios:
    def test_missing_subtitle_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            parser = SubtitleParser("/nonexistent/file.srt")
            parser.parse()

    def test_unsupported_subtitle_format(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"not a subtitle")
            f.flush()
            with pytest.raises(ValueError):
                parser = SubtitleParser(f.name)
                parser.parse()

    def test_missing_assets_directory(self) -> None:
        renderer = SignRenderer(assets_path="/nonexistent/path", size=100)
        with pytest.raises(FileNotFoundError):
            renderer.load_assets()

    def test_invalid_transition_type(self) -> None:
        with pytest.raises(ValueError):
            AnimationController(transition_type="invalid")

    def test_empty_subtitles_zero_duration(self, converter: TextToSignConverter) -> None:
        controller = TimingController(subtitles=[], converter=converter)
        assert controller.total_duration == 0.0
        assert controller.get_current_sign() is None

    def test_zero_duration_subtitle_skipped(self, converter: TextToSignConverter) -> None:
        subs = [SubtitleEntry(index=1, start_time=1.0, end_time=1.0, text="skip me")]
        controller = TimingController(subtitles=subs, converter=converter)
        assert len(controller._schedule) == 0

    def test_config_load_missing_file(self) -> None:
        from main import load_config
        config = load_config("/nonexistent/config.yaml")
        assert config == {}
