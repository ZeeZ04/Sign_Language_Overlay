"""Generate placeholder images for word signs.

Creates colored rounded rectangles with word labels for development.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent.parent / "assets" / "signs" / "asl"
SIZE = 200
BG_COLOR = (35, 50, 60)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (80, 220, 160)  # green accent for word signs

CATEGORY_COLORS = {
    "greeting": (80, 220, 160),
    "basic": (100, 180, 255),
    "pronoun": (255, 160, 80),
    "question": (220, 120, 255),
    "verb": (255, 200, 80),
    "adjective": (255, 120, 120),
    "time": (120, 200, 255),
}


def generate_word_image(word: str, output_path: Path, accent: tuple[int, ...]) -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [(8, 8), (SIZE - 8, SIZE - 8)],
        radius=20,
        fill=BG_COLOR + (230,),
        outline=accent + (255,),
        width=3,
    )

    # Display word text
    display = word.replace("_", " ").upper()
    font_size = 40 if len(display) <= 6 else 28 if len(display) <= 10 else 20

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), display, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (SIZE - text_w) / 2
    y = (SIZE - text_h) / 2 - bbox[1]
    draw.text((x, y), display, fill=TEXT_COLOR, font=font)

    # "WORD" label at bottom
    try:
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except (OSError, IOError):
        try:
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except (OSError, IOError):
            small_font = ImageFont.load_default()

    draw.text((SIZE / 2 - 18, SIZE - 30), "WORD", fill=accent + (180,), font=small_font)

    # Hand icon placeholder at top
    draw.ellipse([(SIZE / 2 - 12, 16), (SIZE / 2 + 12, 40)], fill=accent + (100,))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def main() -> None:
    mapping_path = ASSETS_DIR / "mapping.json"
    with open(mapping_path) as f:
        data = json.load(f)

    words = data.get("words", {})
    words_dir = ASSETS_DIR / "words"

    count = 0
    for word, info in words.items():
        category = info.get("category", "basic")
        accent = CATEGORY_COLORS.get(category, ACCENT_COLOR)
        output = words_dir / f"{word}.png"
        generate_word_image(word, output, accent)
        print(f"  Created {output.name} ({category})")
        count += 1

    print(f"\nGenerated {count} word placeholder images in {words_dir}")


if __name__ == "__main__":
    main()
