"""Generate placeholder images for BSL (British Sign Language) signs."""

from __future__ import annotations

import json
import string
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent.parent / "assets" / "signs" / "bsl"
SIZE = 200
BG_COLOR = (40, 60, 80)
TEXT_COLOR = (255, 200, 100)
ACCENT_COLOR = (100, 160, 220)


def _get_fonts() -> tuple:
    for path in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            big = ImageFont.truetype(path, 80)
            small = ImageFont.truetype(path, 16)
            return big, small
        except (OSError, IOError):
            continue
    fallback = ImageFont.load_default()
    return fallback, fallback


def generate_image(label: str, output_path: Path, tag: str = "BSL") -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    big_font, small_font = _get_fonts()

    # Rounded rect background
    draw.rounded_rectangle(
        [(10, 10), (SIZE - 10, SIZE - 10)],
        radius=20,
        fill=BG_COLOR + (230,),
        outline=ACCENT_COLOR + (255,),
        width=3,
    )

    # Main label
    bbox = draw.textbbox((0, 0), label, font=big_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (SIZE - text_w) / 2
    y = (SIZE - text_h) / 2 - bbox[1]
    draw.text((x, y), label, fill=TEXT_COLOR, font=big_font)

    # Tag label
    draw.text((SIZE / 2 - 12, SIZE - 35), tag, fill=ACCENT_COLOR + (180,), font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def main() -> None:
    # Alphabet
    for letter in string.ascii_lowercase:
        generate_image(letter.upper(), ASSETS_DIR / "alphabet" / f"{letter}.png")
        print(f"  Created alphabet/{letter}.png")

    # Numbers
    for digit in range(10):
        generate_image(str(digit), ASSETS_DIR / "numbers" / f"{digit}.png")
        print(f"  Created numbers/{digit}.png")

    # Create mapping.json
    mapping = {
        "alphabet": {
            c: {"file": f"alphabet/{c}.png", "duration_ms": 350}
            for c in string.ascii_lowercase
        },
        "numbers": {
            str(n): {"file": f"numbers/{n}.png", "duration_ms": 400}
            for n in range(10)
        },
        "words": {},
        "special": {
            "space": {"file": None, "duration_ms": 200},
            "unknown": {"file": "alphabet/a.png", "duration_ms": 250},
        },
        "meta": {
            "language": "bsl",
            "name": "British Sign Language",
            "two_handed": True,
            "notes": "BSL uses a two-handed alphabet. These are placeholders.",
        },
    }

    with open(ASSETS_DIR / "mapping.json", "w") as f:
        json.dump(mapping, f, indent=2)

    print(f"\nGenerated BSL placeholders: 26 alphabet + 10 numbers + mapping.json")


if __name__ == "__main__":
    main()
