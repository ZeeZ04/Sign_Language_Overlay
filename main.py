"""Sign Language Overlay - CLI entry point.

Displays synchronized sign language for subtitle files, audio, or
live microphone input. Supports multiple sign languages, word signs,
smooth animations, and facial expression hints.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pygame
import yaml

from src.animation_controller import AnimationController
from src.expression_overlay import ExpressionOverlay
from src.grammar_transformer import ASLGrammarTransformer
from src.language_manager import LanguageManager
from src.overlay_window import OverlayWindow
from src.performance_monitor import PerformanceMonitor
from src.sign_renderer import SignRenderer
from src.subtitle_parser import SubtitleEntry, SubtitleParser
from src.text_to_sign import TextToSignConverter
from src.timing_controller import TimingController

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).parent / "config.yaml"


def load_config(config_path: str | None = None) -> dict:
    path = Path(config_path) if config_path else DEFAULT_CONFIG
    if not path.exists():
        logger.warning("Config file not found: %s. Using defaults.", path)
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sign Language Overlay - Display sign language for subtitles, audio, or live input",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Input source
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "-s", "--subtitle",
        help="Path to subtitle file (SRT or VTT)",
    )
    input_group.add_argument(
        "-a", "--audio",
        help="Path to audio file (mp3, wav, etc.) - transcribed via Whisper",
    )
    input_group.add_argument(
        "--video",
        help="Path to video file (extracts and transcribes audio via Whisper)",
    )
    input_group.add_argument(
        "--realtime",
        action="store_true",
        help="Use live microphone input (requires sounddevice + Whisper)",
    )
    input_group.add_argument(
        "--list-languages",
        action="store_true",
        help="List available sign languages and exit",
    )
    input_group.add_argument(
        "--settings",
        action="store_true",
        help="Open settings GUI",
    )

    # Language
    parser.add_argument(
        "-l", "--language",
        default=None,
        help="Sign language code (asl/bsl/isl/auslan)",
    )

    # Whisper options
    parser.add_argument(
        "--whisper-model",
        choices=["tiny", "base", "small", "medium", "large"],
        default=None,
        help="Whisper model size (default: base)",
    )

    # Features
    parser.add_argument(
        "--use-word-signs",
        action="store_true",
        help="Enable word-level signs for common words",
    )
    parser.add_argument(
        "--show-expressions",
        action="store_true",
        help="Show facial expression hints (?, !, negation, etc.)",
    )
    parser.add_argument(
        "--use-3d",
        action="store_true",
        help="Use 3D hand model (if poses available)",
    )

    # Animation
    parser.add_argument(
        "--transition",
        choices=["fade", "cut", "slide"],
        default=None,
        help="Transition type between signs (default: fade)",
    )

    # Display
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "-p", "--position",
        choices=["top-left", "top-right", "bottom-left", "bottom-right"],
        default=None,
        help="Overlay position on screen",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=None,
        help="Hand image size in pixels",
    )
    parser.add_argument(
        "--start",
        type=float,
        default=0.0,
        help="Start time in seconds",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable performance profiling",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def list_languages(base_assets: str) -> None:
    """Print available languages and exit."""
    manager = LanguageManager(base_assets)
    languages = manager.get_available_languages()
    print("\nAvailable sign languages:\n")
    print(f"  {'Code':<8} {'Name':<30} {'Alphabet':<12} {'Words':<8} {'Notes'}")
    print(f"  {'----':<8} {'----':<30} {'--------':<12} {'-----':<8} {'-----'}")
    for lang in languages:
        hand = "two-hand" if lang.has_two_handed_alphabet else "one-hand"
        print(f"  {lang.code:<8} {lang.name:<30} {hand:<12} {lang.word_sign_count:<8} {lang.notes}")
    print()


def get_subtitles_from_audio(audio_path: str, model_size: str) -> list[SubtitleEntry]:
    from src.speech_to_text import SpeechToText

    stt = SpeechToText(model_size=model_size)
    stt.load_model()
    segments = stt.transcribe_file(audio_path)

    entries = []
    for i, seg in enumerate(segments, start=1):
        entries.append(SubtitleEntry(
            index=i,
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=seg.text,
        ))
    return entries


def main() -> None:
    args = parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load config
    config = load_config(args.config)
    display_cfg = config.get("display", {})
    assets_cfg = config.get("assets", {})
    whisper_cfg = config.get("whisper", {})
    expr_cfg = config.get("expressions", {})

    base_assets = assets_cfg.get("base_directory", "assets/signs")

    # Handle --list-languages
    if args.list_languages:
        list_languages(base_assets)
        sys.exit(0)

    # Handle --settings
    if args.settings:
        from src.settings_gui import SettingsGUI
        gui = SettingsGUI(config_path=str(Path(args.config) if args.config else DEFAULT_CONFIG))
        gui.show()
        sys.exit(0)

    # CLI overrides
    language_code = args.language or config.get("language", "asl")
    position = args.position or display_cfg.get("position", "bottom-right")
    size = args.size or display_cfg.get("size", 200)
    opacity = display_cfg.get("background_opacity", 0.8)
    transition_type = args.transition or display_cfg.get("transition", "fade")
    transition_ms = display_cfg.get("transition_ms", 100)
    whisper_model = args.whisper_model or whisper_cfg.get("model_size", "base")
    show_expressions = args.show_expressions or expr_cfg.get("enabled", False)

    # Load language
    lang_manager = LanguageManager(base_assets)
    lang_config = lang_manager.load_language(language_code)
    assets_dir = str(lang_config.assets_path)
    logger.info("Using language: %s (%s)", lang_config.name, lang_config.code)

    # Initialize performance monitor
    perf_monitor = PerformanceMonitor() if args.profile else None

    # Handle --realtime mode
    if args.realtime:
        _run_realtime(
            lang_manager, assets_dir, size, position, opacity,
            transition_type, transition_ms, whisper_model, show_expressions,
            perf_monitor=perf_monitor,
            use_3d=args.use_3d,
            use_word_signs=args.use_word_signs,
        )
        return

    # Determine input source and get subtitles
    if args.subtitle:
        logger.info("Loading subtitles from: %s", args.subtitle)
        parser = SubtitleParser(args.subtitle)
        subtitles = parser.parse()
    elif args.audio:
        logger.info("Transcribing audio: %s (model: %s)", args.audio, whisper_model)
        subtitles = get_subtitles_from_audio(args.audio, whisper_model)
    elif args.video:
        logger.info("Transcribing video: %s (model: %s)", args.video, whisper_model)
        subtitles = get_subtitles_from_audio(args.video, whisper_model)
    else:
        subtitles = []

    if not subtitles:
        logger.error("No subtitles or transcript segments found.")
        sys.exit(1)
    logger.info("Loaded %d entries", len(subtitles))

    # Initialize converter
    converter = TextToSignConverter(language=language_code)

    # Initialize grammar transformer
    grammar = ASLGrammarTransformer(language=language_code)
    logger.info("Grammar transformer enabled for %s", language_code)

    # Initialize word mapper (optional)
    word_mapper = None
    if args.use_word_signs:
        from src.word_sign_mapper import WordSignMapper
        word_mapper = WordSignMapper(assets_path=assets_dir, language=language_code)
        word_mapper.load_word_signs()
        logger.info("Word signs enabled: %d words available", len(word_mapper.get_available_words()))

    # Initialize pygame
    pygame.init()

    # Initialize renderer
    renderer = SignRenderer(assets_path=assets_dir, size=size)
    renderer.load_assets()

    # Initialize 3D hand model (optional)
    hand_model = None
    pose_interpolator = None
    if args.use_3d:
        from src.hand_model_3d import HandModel3D
        from src.skeletal_animation import PoseInterpolator

        model_path = Path(assets_dir).parent.parent.parent / "models" / "hand"
        hand_model = HandModel3D(model_path=model_path, size=(size, size))
        if hand_model.load_model():
            logger.info("3D hand model loaded with %d poses", len(hand_model.get_available_poses()))
        else:
            logger.warning("3D hand model has no poses, will render skeletal fallback")
        pose_interpolator = PoseInterpolator(hand_model, transition_ms=transition_ms)

    # Initialize animation controller
    animator = AnimationController(transition_ms=transition_ms, transition_type=transition_type)

    # Initialize expression overlay
    expr_overlay = None
    if show_expressions:
        expr_overlay = ExpressionOverlay(font_size=expr_cfg.get("font_size", 32))

    # Initialize overlay window
    overlay = OverlayWindow(position=position, size=size, opacity=opacity)
    overlay.show()

    # Initialize timing
    controller = TimingController(
        subtitles=subtitles,
        converter=converter,
        word_mapper=word_mapper,
        grammar_transformer=grammar,
    )
    controller.start(start_time=args.start)

    # Main loop
    _run_playback_loop(overlay, controller, renderer, animator, expr_overlay, subtitles,
                       hand_model=hand_model, pose_interpolator=pose_interpolator,
                       perf_monitor=perf_monitor)


def _run_playback_loop(
    overlay: OverlayWindow,
    controller: TimingController,
    renderer: SignRenderer,
    animator: AnimationController,
    expr_overlay: ExpressionOverlay | None,
    subtitles: list[SubtitleEntry],
    hand_model: object | None = None,
    pose_interpolator: object | None = None,
    perf_monitor: PerformanceMonitor | None = None,
) -> None:
    clock = pygame.time.Clock()
    fps = 60
    last_sign_id = None
    last_subtitle_idx = -1

    import time as _time

    logger.info("Starting playback... Press Q or close window to quit.")
    logger.info("Press SPACE to pause/resume, LEFT/RIGHT arrows to seek.")

    try:
        while overlay.is_running:
            if perf_monitor:
                perf_monitor.start_frame()

            dt = clock.tick(fps) / 1000.0
            dt_ms = dt * 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    overlay.stop()
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        overlay.stop()
                    elif event.key == pygame.K_SPACE:
                        if controller.is_playing:
                            controller.pause()
                        else:
                            controller.resume()
                    elif event.key == pygame.K_RIGHT:
                        controller.seek(controller.current_time + 5.0)
                    elif event.key == pygame.K_LEFT:
                        controller.seek(max(0, controller.current_time - 5.0))

            controller.update(dt)

            # Get current sign and animate
            sign_token = controller.get_current_sign()
            current_sign_id = sign_token.sign_id if sign_token else None

            if current_sign_id != last_sign_id:
                _lookup_start = _time.perf_counter()
                if pose_interpolator is not None and hand_model is not None and sign_token:
                    # Use PoseInterpolator for smooth skeletal transitions
                    pose = hand_model.get_pose(sign_token.sign_id)
                    if pose:
                        pose_interpolator.queue_pose_transition(pose)
                    else:
                        # No 3D pose available, fall back to 2D image
                        surface = renderer.get_sign_surface(sign_token.sign_id)
                        animator.set_sign(surface)
                elif hand_model is not None and sign_token:
                    hand_model.set_pose(sign_token.sign_id)
                    surface = hand_model.render_skeletal() or renderer.get_sign_surface(sign_token.sign_id)
                    animator.set_sign(surface)
                else:
                    surface = renderer.get_sign_surface(sign_token.sign_id) if sign_token else None
                    animator.set_sign(surface)
                if perf_monitor:
                    perf_monitor.record_sign_lookup((_time.perf_counter() - _lookup_start) * 1000)
                last_sign_id = current_sign_id

            _render_start = _time.perf_counter()

            # Update pose interpolator (renders intermediate frames)
            if pose_interpolator is not None:
                interp_frame = pose_interpolator.update(dt_ms)
                if interp_frame is not None:
                    animator.set_sign(interp_frame)

            animator.update(dt_ms)
            frame = animator.get_current_frame()

            # Expression overlay
            if expr_overlay:
                expr_overlay.update(dt_ms)
                # Infer expression when subtitle changes
                for i, sub in enumerate(subtitles):
                    if sub.start_time <= controller.current_time < sub.end_time and i != last_subtitle_idx:
                        hint = expr_overlay.infer_expression(sub.text)
                        if hint:
                            expr_overlay.set_expression(hint)
                        last_subtitle_idx = i
                        break

                expr_surface = expr_overlay.render((overlay.size + 20, overlay.size + 20))
                if expr_surface and frame:
                    frame = frame.copy()
                    frame.blit(expr_surface, (0, 0))

            overlay.update(frame)
            overlay.render_frame()

            if perf_monitor:
                perf_monitor.record_render_time((_time.perf_counter() - _render_start) * 1000)
                perf_monitor.end_frame()
                perf_monitor.update()

            if controller.current_time > controller.total_duration and controller.total_duration > 0:
                logger.info("Playback complete.")
                overlay.stop()

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        if perf_monitor:
            summary = perf_monitor.get_summary()
            logger.info(
                "Final perf: %d frames | p95 %.1f ms | %d over budget",
                summary["frame_count"], summary["p95_frame_ms"], summary["over_budget_count"],
            )
        pygame.quit()
        logger.info("Overlay closed.")


def _run_realtime(
    lang_manager: LanguageManager,
    assets_dir: str,
    size: int,
    position: str,
    opacity: float,
    transition_type: str,
    transition_ms: int,
    whisper_model: str,
    show_expressions: bool,
    perf_monitor: PerformanceMonitor | None = None,
    use_3d: bool = False,
    use_word_signs: bool = False,
) -> None:
    """Run in real-time microphone mode."""
    import time as _time

    from src.realtime_audio import RealtimeAudio, RealtimeTranscriber
    from src.speech_to_text import SpeechToText

    logger.info("Starting real-time mode...")

    # Initialize Whisper
    stt = SpeechToText(model_size=whisper_model)
    stt.load_model()

    # Initialize audio capture
    audio = RealtimeAudio(sample_rate=16000, chunk_duration_ms=100)
    transcriber = RealtimeTranscriber(stt, chunk_duration_ms=3000)

    # Initialize pygame and renderer
    pygame.init()
    language_code = lang_manager.current_language.code
    converter = TextToSignConverter(language=language_code)
    grammar = ASLGrammarTransformer(language=language_code)
    renderer = SignRenderer(assets_path=assets_dir, size=size)
    renderer.load_assets()
    animator = AnimationController(transition_ms=transition_ms, transition_type=transition_type)
    overlay = OverlayWindow(position=position, size=size, opacity=opacity)
    overlay.show()

    expr_overlay = ExpressionOverlay() if show_expressions else None

    # Initialize word mapper (optional)
    word_mapper = None
    if use_word_signs:
        from src.word_sign_mapper import WordSignMapper
        word_mapper = WordSignMapper(assets_path=assets_dir, language=language_code)
        word_mapper.load_word_signs()
        logger.info("Realtime word signs enabled: %d words", len(word_mapper.get_available_words()))

    # Initialize 3D hand model (optional)
    hand_model = None
    pose_interpolator = None
    if use_3d:
        from src.hand_model_3d import HandModel3D
        from src.skeletal_animation import PoseInterpolator

        model_path = Path(assets_dir).parent.parent.parent / "models" / "hand"
        hand_model = HandModel3D(model_path=model_path, size=(size, size))
        if hand_model.load_model():
            logger.info("Realtime 3D hand model: %d poses", len(hand_model.get_available_poses()))
        else:
            logger.warning("Realtime 3D hand model has no poses, skeletal fallback")
        pose_interpolator = PoseInterpolator(hand_model, transition_ms=transition_ms)

    # Start capture and transcription
    audio.start_capture()
    transcriber.start(audio)

    clock = pygame.time.Clock()
    fps = 30
    last_text = None

    # Multi-sign scheduling for real-time mode
    rt_tokens: list = []
    rt_token_idx = 0
    rt_token_elapsed_ms = 0.0

    logger.info("Listening... Press Q or close window to quit.")

    try:
        while overlay.is_running:
            if perf_monitor:
                perf_monitor.start_frame()

            dt_ms = clock.tick(fps)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    overlay.stop()
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        overlay.stop()

            # Check for new transcription
            text = transcriber.get_latest_text()
            if text and text != last_text:
                _transcribe_start = _time.perf_counter()
                last_text = text
                logger.info("Heard: %s", text)

                # Apply grammar transformation
                transformed = grammar.transform(text)

                # Convert to sign tokens (word mapper or fingerspell)
                if word_mapper is not None:
                    sequences = word_mapper.map_text(transformed.text)
                    rt_tokens = []
                    for seq in sequences:
                        rt_tokens.extend(seq.tokens)
                else:
                    rt_tokens = converter.convert(transformed.text)

                rt_token_idx = 0
                rt_token_elapsed_ms = 0.0

                if rt_tokens:
                    _rt_set_sign(
                        rt_tokens[0], renderer, animator,
                        hand_model, pose_interpolator,
                    )

                if expr_overlay:
                    hint = expr_overlay.infer_expression(text)
                    if hint:
                        expr_overlay.set_expression(hint)

                if perf_monitor:
                    perf_monitor.record_transcription(
                        latency_ms=(_time.perf_counter() - _transcribe_start) * 1000,
                        text_length=len(text),
                    )

            # Advance through token sequence based on duration
            if rt_tokens and rt_token_idx < len(rt_tokens):
                rt_token_elapsed_ms += float(dt_ms)
                current_duration = rt_tokens[rt_token_idx].duration_ms
                if rt_token_elapsed_ms >= current_duration:
                    rt_token_elapsed_ms -= current_duration
                    rt_token_idx += 1
                    if rt_token_idx < len(rt_tokens):
                        _rt_set_sign(
                            rt_tokens[rt_token_idx], renderer, animator,
                            hand_model, pose_interpolator,
                        )

            _render_start = _time.perf_counter()

            # Update pose interpolator (renders intermediate frames)
            if pose_interpolator is not None:
                interp_frame = pose_interpolator.update(float(dt_ms))
                if interp_frame is not None:
                    animator.set_sign(interp_frame)

            animator.update(float(dt_ms))
            if expr_overlay:
                expr_overlay.update(float(dt_ms))

            frame = animator.get_current_frame()

            if expr_overlay:
                expr_surface = expr_overlay.render((size + 20, size + 20))
                if expr_surface and frame:
                    frame = frame.copy()
                    frame.blit(expr_surface, (0, 0))

            overlay.update(frame)
            overlay.render_frame()

            if perf_monitor:
                perf_monitor.record_render_time((_time.perf_counter() - _render_start) * 1000)
                perf_monitor.end_frame()
                perf_monitor.update()

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        if perf_monitor:
            summary = perf_monitor.get_summary()
            logger.info(
                "Final perf: %d frames | p95 %.1f ms | %d over budget | %d transcriptions",
                summary["frame_count"], summary["p95_frame_ms"],
                summary["over_budget_count"], summary["transcription_count"],
            )
        transcriber.stop()
        audio.stop_capture()
        pygame.quit()
        logger.info("Real-time mode stopped.")


def _rt_set_sign(
    token: object,
    renderer: SignRenderer,
    animator: AnimationController,
    hand_model: object | None,
    pose_interpolator: object | None,
) -> None:
    """Set the current sign in realtime mode, with 3D support."""
    if pose_interpolator is not None and hand_model is not None:
        pose = hand_model.get_pose(token.sign_id)
        if pose:
            pose_interpolator.queue_pose_transition(pose)
            return
    # Fallback to 2D image
    surface = renderer.get_sign_surface(token.sign_id)
    animator.set_sign(surface)


if __name__ == "__main__":
    main()
