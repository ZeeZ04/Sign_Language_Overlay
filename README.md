# Sign Language Overlay

A real-time sign language overlay system that converts subtitles or audio into visual sign language representations. Supports multiple sign languages (ASL, BSL, ISL, Auslan) with word-level signs and fingerspelling.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python)
![License](https://img.shields.io/badge/License-Custom-yellow)
![Status](https://img.shields.io/badge/Status-Beta-orange)

## Features

- **Multiple Input Sources**: Parse SRT/VTT subtitles, transcribe audio/video files, or use live microphone input
- **Multi-Language Support**: ASL, BSL, ISL, and Auslan with switchable languages
- **Word-Level Signs**: 50+ common words displayed as single signs (not just fingerspelling)
- **Real-Time Transcription**: Powered by OpenAI Whisper for accurate speech-to-text
- **Expression Hints**: Visual indicators for questions (❓), emphasis (❗), and negation (🚫)
- **Smooth Animations**: Fade, slide, and cut transitions between signs
- **Configurable Display**: Adjustable position, size, and overlay settings

## Installation

### Prerequisites
- Python 3.9 or higher
- pip package manager

### Basic Installation
```bash
git clone https://github.com/ZeeZ04/Sign_Language_Overlay.git
cd Sign_Language_Overlay
pip install -r requirements.txt
```

### Optional Dependencies (for full features)
```bash
# For audio/video transcription (Whisper)
pip install openai-whisper torch torchaudio

# For real-time microphone input
pip install sounddevice

# For screen capture compositing
pip install opencv-python
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
| `--transition TYPE` | Transition type: `fade`, `cut`, `slide` |
| `-p, --position POS` | Overlay position: `top-left`, `top-right`, `bottom-left`, `bottom-right` |
| `--size SIZE` | Hand image size in pixels |

### Whisper Options
| Flag | Description |
|------|-------------|
| `--whisper-model SIZE` | Model: `tiny`, `base`, `small`, `medium`, `large` |

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause/Resume |
| `←` / `→` | Seek backward/forward 5 seconds |
| `Q` / `ESC` | Quit |

## Project Structure

```
Sign_Language_Overlay/
├── main.py                 # CLI entry point
├── config.yaml             # Configuration file
├── src/
│   ├── subtitle_parser.py      # SRT/VTT parsing
│   ├── speech_to_text.py       # Whisper integration
│   ├── text_to_sign.py         # Text to sign conversion
│   ├── word_sign_mapper.py     # Word-level sign mapping
│   ├── sign_renderer.py        # Image loading and rendering
│   ├── overlay_window.py       # Pygame overlay display
│   ├── timing_controller.py    # Synchronization logic
│   ├── animation_controller.py # Smooth transitions
│   ├── language_manager.py     # Multi-language support
│   ├── realtime_audio.py       # Microphone capture
│   ├── screen_capture.py       # Screen capture mode
│   └── expression_overlay.py   # Expression hints
├── assets/signs/
│   ├── asl/                    # American Sign Language assets
│   └── bsl/                    # British Sign Language assets
└── tests/                      # Test suite
```

## Current Limitations

- **Placeholder Images**: Currently uses placeholder graphics. Replace with actual hand sign images for real accessibility use.
- **Grammar**: Signs are displayed word-by-word; proper ASL sentence structure/grammar not implemented.
- **Word Coverage**: 50 word signs for ASL; other languages have fingerspelling only.

## Roadmap

- [ ] Real hand sign images/illustrations
- [ ] Expanded word sign vocabulary (500+ words)
- [ ] ASL grammar transformation
- [ ] 3D animated hand model
- [ ] Browser extension version
- [ ] Mobile app

## Running Tests

```bash
pytest tests/ -v
```

## License

**Custom License - Attribution Required, Non-Commercial**

- ✅ Free for personal, educational, and research use
- ✅ Free to modify and learn from
- ✅ Must give credit to Abdul Azeez Aris
- ❌ Commercial use requires written permission

See [LICENSE](LICENSE) for full terms.

For commercial licensing inquiries: azeezaris@outlook.com

## Author

**Abdul Azeez Aris**
- MSc Artificial Intelligence, University of Southampton (2024-2026)
- BEng (Hons) Artificial Intelligence, Ulster University (2020-2024)
- GitHub: [@ZeeZ04](https://github.com/ZeeZ04)

## Acknowledgments

- OpenAI Whisper for speech recognition
- Pygame for overlay rendering
- The deaf and hard-of-hearing community for inspiration

---

*If you use this project, please star ⭐ the repository and provide attribution.*
