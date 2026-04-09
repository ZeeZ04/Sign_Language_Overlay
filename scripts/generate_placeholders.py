"""Generate placeholder hand sign images for development.

Creates colored squares with letters/numbers centered as stand-ins
for actual ASL fingerspelling images.
"""

from __future__ import annotations

import string
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent.parent / "assets" / "signs" / "asl"
SIZE = 200
BG_COLOR = (45, 45, 55)
TEXT_COLOR = (255, 255, 255)
LETTER_ACCENT = (100, 180, 255)
NUMBER_ACCENT = (255, 160, 80)


def generate_image(label: str, output_path: Path, accent_color: tuple[int, ...]) -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background
    draw.rounded_rectangle(
        [(10, 10), (SIZE - 10, SIZE - 10)],
        radius=20,
        fill=BG_COLOR + (220,),
        outline=accent_color + (255,),
        width=3,
    )

    # Draw label text
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        except (OSError, IOError):
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (SIZE - text_w) / 2
    y = (SIZE - text_h) / 2 - bbox[1]
    draw.text((x, y), label, fill=TEXT_COLOR, font=font)

    # Small "ASL" label at bottom
    try:
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except (OSError, IOError):
        try:
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except (OSError, IOError):
            small_font = ImageFont.load_default()

    draw.text((SIZE / 2 - 15, SIZE - 35), "ASL", fill=accent_color + (180,), font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def main() -> None:
    # Generate alphabet A-Z
    alphabet_dir = ASSETS_DIR / "alphabet"
    for letter in string.ascii_lowercase:
        output = alphabet_dir / f"{letter}.png"
        generate_image(letter.upper(), output, LETTER_ACCENT)
        print(f"  Created {output.name}")

    # Generate numbers 0-9
    numbers_dir = ASSETS_DIR / "numbers"
    for digit in range(10):
        output = numbers_dir / f"{digit}.png"
        generate_image(str(digit), output, NUMBER_ACCENT)
        print(f"  Created {output.name}")

    # Generate unknown placeholder
    unknown_path = ASSETS_DIR / "unknown.png"
    generate_image("?", unknown_path, (180, 180, 180))
    print(f"  Created {unknown_path.name}")

    print(f"\nGenerated {26 + 10 + 1} placeholder images in {ASSETS_DIR}")


if __name__ == "__main__":
    main()
