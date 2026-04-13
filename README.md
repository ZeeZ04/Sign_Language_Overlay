# Sign Language Overlay

A real-time sign language overlay system that converts subtitles or audio into visual sign language representations. Supports multiple sign languages (ASL, BSL, ISL, Auslan) with word-level signs, fingerspelling, and grammar-aware reordering.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python)
![CI](https://github.com/ZeeZ04/Sign_Language_Overlay/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/License-Custom-yellow)
![Status](https://img.shields.io/badge/Status-Beta-orange)

## Features

- **Multiple Input Sources**: Parse SRT/VTT subtitles, transcribe audio/video files, or use live microphone input
- **Multi-Language Support**: ASL, BSL, ISL, and Auslan with switchable languages
- **Expanded ASL Vocabulary**: 2,725 word-level signs sourced from ASL-LEX
- **ASL Grammar Transformer**: Automatic English-to-ASL reordering (topic-comment structure, time fronting, WH-movement, negation placement)
- **Real-Time Transcription**: Powered by OpenAI Whisper for accurate speech-to-text
- **3D Skeletal Hand Model**: Optional 3D hand rendering with `--use-3d`
- **Expression Hints**: Visual indicators for questions, emphasis, and negation
- **Settings GUI**: Tkinter-based configuration panel with `--settings`
- **Performance Profiling**: Frame timing and latency tracking with `--profile`
- **Smooth Animations**: Fade, slide, and cut transitions between signs
- **Configurable Display**: Adjustable position, size, and overlay settings

## Installation

### Prerequisites
- Python 3.9 or higher
- pip package manager

### Install from source

```bash
git clone https://github.com/ZeeZ04/Sign_Language_Overlay.git
cd Sign_Language_Overlay
pip install -e .
```

### Optional extras

```bash
# Audio/video transcription (Whisper)
pip install -e ".[whisper]"

# Real-time microphone input
pip install -e ".[realtime]"

# Screen capture / video support
pip install -e ".[video]"

# Development tools (pytest, ruff, mypy)
pip install -e ".[dev]"

# Everything
pip install -e ".[all]"
```

## Quick Start

```bash
# Basic subtitle mode
python main.py -s subtitles.srt

# With word signs and expression hints
python main.py -s subtitles.srt --use-word-signs --show-expressions

# Transcribe audio file
python main.py --audio recording.mp3 --whisper-model base

# Real-time microphone mode
python main.py --realtime --whisper-model base

# Use British Sign Language
python main.py -s subtitles.srt -l bsl

# 3D skeletal hand rendering
python main.py -s subtitles.srt --use-3d

# Open settings GUI
python main.py --settings

# Enable performance profiling
python main.py -s subtitles.srt --profile
```

## CLI Reference

### Input Options
| Flag | Description |
|------|-------------|
| `-s, --subtitle PATH` | Path to subtitle file (SRT or VTT) |
| `-a, --audio PATH` | Path to audio file (mp3, wav, etc.) |
| `--video PATH` | Path to video file (extracts audio) |
| `--realtime` | Use live microphone input |

### Language Options
| Flag | Description |
|------|-------------|
| `-l, --language CODE` | Sign language: `asl`, `bsl`, `isl`, `auslan` |
| `--list-languages` | Show available languages and exit |

### Display Options
| Flag | Description |
|------|-------------|
| `--use-word-signs` | Use word-level signs (not just fingerspelling) |
| `--show-expressions` | Show facial expression hints |
| `--use-3d` | Use 3D skeletal hand model rendering |
| `--transition TYPE` | Transition type: `fade`, `cut`, `slide` |
| `-p, --position POS` | Overlay position: `top-left`, `top-right`, `bottom-left`, `bottom-right` |
| `--size SIZE` | Hand image size in pixels |

### Whisper Options
| Flag | Description |
|------|-------------|
| `--whisper-model SIZE` | Model: `tiny`, `base`, `small`, `medium`, `large` |

### Other Options
| Flag | Description |
|------|-------------|
| `--settings` | Open the settings GUI |
| `--profile` | Enable performance profiling (frame times, latency) |
| `-c, --config PATH` | Path to config file (default: config.yaml) |
| `-v, --verbose` | Enable debug logging |

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause/Resume |
| `LEFT` / `RIGHT` | Seek backward/forward 5 seconds |
| `Q` / `ESC` | Quit |

## Project Structure

```
Sign_Language_Overlay/
├── main.py                      # CLI entry point
├── config.yaml                  # Configuration file
├── pyproject.toml               # Package metadata and dependencies
├── Makefile                     # Dev shortcuts (test, lint, typecheck)
├── src/
│   ├── subtitle_parser.py       # SRT/VTT parsing
│   ├── speech_to_text.py        # Whisper integration
│   ├── text_to_sign.py          # Text to sign conversion
│   ├── word_sign_mapper.py      # Word-level sign mapping
│   ├── grammar_transformer.py   # English → ASL grammar reordering
│   ├── sign_renderer.py         # Image loading and rendering
│   ├── hand_model_3d.py         # 3D skeletal hand rendering
│   ├── overlay_window.py        # Pygame overlay display
│   ├── timing_controller.py     # Synchronization logic
│   ├── animation_controller.py  # Smooth transitions
│   ├── language_manager.py      # Multi-language support
│   ├── realtime_audio.py        # Microphone capture + error recovery
│   ├── screen_capture.py        # Screen capture mode
│   ├── expression_overlay.py    # Expression hints
│   ├── performance_monitor.py   # Frame timing and latency tracking
│   └── settings_gui.py          # Tkinter settings panel
├── assets/signs/
│   ├── asl/                     # ASL assets (2,725 word signs)
│   ├── bsl/                     # BSL assets (alphabet + numbers)
│   ├── isl/                     # ISL assets (alphabet + numbers)
│   └── auslan/                  # Auslan assets (alphabet + numbers)
├── scripts/                     # Asset generation and integration scripts
└── tests/                       # Test suite (226+ tests)
```

## Development

```bash
make install    # Install package in editable mode
make dev        # Install with dev dependencies
make test       # Run all tests
make lint       # Run ruff linter
make typecheck  # Run mypy type checker
make format     # Auto-format code with ruff
make clean      # Remove build artifacts
```

### CI/CD

Tests run automatically on push and PR via GitHub Actions across Python 3.9-3.12, including linting (ruff) and type checking (mypy).

## Current Limitations

- **Placeholder Images**: Currently uses generated placeholder graphics. Replace with actual hand sign images for real accessibility use.
- **BSL/ISL/Auslan Vocabulary**: These languages have alphabet and number support only; word-level signs are ASL only for now.

## Roadmap

- [x] ASL grammar transformation
- [x] 3D animated hand model
- [x] Expanded ASL vocabulary (2,725 words via ASL-LEX)
- [x] Settings GUI
- [x] Performance monitoring
- [x] CI/CD pipeline
- [ ] BSL/ISL/Auslan word-level signs
- [ ] Real hand sign images/illustrations
- [ ] Google ISLR hand landmarks for realistic 3D poses
- [ ] Browser extension version
- [ ] Mobile app

## Running Tests

```bash
pytest tests/ -v
```

## License

**Custom License - Attribution Required, Non-Commercial**

- Free for personal, educational, and research use
- Free to modify and learn from
- Must give credit to Abdul Azeez Aris
- Commercial use requires written permission

See [LICENSE](LICENSE) for full terms.

For commercial licensing inquiries: azeezaris@outlook.com

## Author

**Abdul Azeez Aris**
- MSc Artificial Intelligence, University of Southampton (2024-2026)
- BEng (Hons) Artificial Intelligence, Ulster University (2020-2024)
- GitHub: [@ZeeZ04](https://github.com/ZeeZ04)

## Acknowledgments

- OpenAI Whisper for speech recognition
- ASL-LEX for expanded vocabulary data
- Pygame for overlay rendering
- The deaf and hard-of-hearing community for inspiration

---

*If you use this project, please star the repository and provide attribution.*
