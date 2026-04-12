"""Generate improved ASL alphabet illustrations using Pillow.

Creates recognizable hand sign illustrations for A-Z and 0-9 by drawing
simplified hand shapes. These are better than the current solid-color
placeholders but should still be replaced with real photographs or
professional illustrations when available.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).parent.parent
ASL_ALPHABET_DIR = PROJECT_ROOT / "assets" / "signs" / "asl" / "alphabet"
ASL_NUMBERS_DIR = PROJECT_ROOT / "assets" / "signs" / "asl" / "numbers"

SIZE = 200
BG_COLOR = (35, 40, 55, 230)
SKIN_COLOR = (227, 180, 140, 255)
SKIN_DARK = (190, 145, 110, 255)
OUTLINE_COLOR = (180, 140, 105, 255)
LABEL_COLOR = (200, 210, 230, 200)


def draw_palm(draw: ImageDraw.Draw, cx: int, cy: int, w: int, h: int) -> None:
    """Draw a palm shape."""
    draw.rounded_rectangle(
        [(cx - w // 2, cy - h // 2), (cx + w // 2, cy + h // 2)],
        radius=12,
        fill=SKIN_COLOR,
        outline=OUTLINE_COLOR,
        width=1,
    )


def draw_finger(draw: ImageDraw.Draw, x1: int, y1: int, x2: int, y2: int,
                width: int = 14, tip_round: bool = True) -> None:
    """Draw a finger from base to tip."""
    # Draw finger body as a rounded line
    angle = math.atan2(y2 - y1, x2 - x1)
    dx = math.sin(angle) * width / 2
    dy = -math.cos(angle) * width / 2
    points = [
        (x1 - dx, y1 - dy),
        (x2 - dx, y2 - dy),
        (x2 + dx, y2 + dy),
        (x1 + dx, y1 + dy),
    ]
    draw.polygon(points, fill=SKIN_COLOR, outline=OUTLINE_COLOR)
    if tip_round:
        draw.ellipse(
            [(x2 - width // 2, y2 - width // 2), (x2 + width // 2, y2 + width // 2)],
            fill=SKIN_COLOR, outline=OUTLINE_COLOR,
        )


def draw_thumb(draw: ImageDraw.Draw, x1: int, y1: int, x2: int, y2: int,
               width: int = 16) -> None:
    """Draw a thumb (slightly thicker finger)."""
    draw_finger(draw, x1, y1, x2, y2, width=width)


def add_label(draw: ImageDraw.Draw, label: str, size: int = SIZE) -> None:
    """Add a letter/number label."""
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except (OSError, IOError):
        font = ImageFont.load_default()
    draw.text((8, size - 28), label, fill=LABEL_COLOR, font=font)


def create_base_image() -> tuple[Image.Image, ImageDraw.Draw]:
    img = Image.new("RGBA", (SIZE, SIZE), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(2, 2), (SIZE - 3, SIZE - 3)], radius=12,
                            outline=(80, 100, 130, 200), width=1)
    return img, draw


# ── ASL Letter Drawings ──────────────────────────────────────────────────────

def draw_letter_a(draw: ImageDraw.Draw) -> None:
    """A: Fist with thumb alongside."""
    cx, cy = 100, 90
    draw_palm(draw, cx, cy, 55, 60)
    # Curled fingers (fist shape)
    for i in range(4):
        x = cx - 20 + i * 13
        draw.ellipse([(x - 7, cy - 35), (x + 7, cy - 22)], fill=SKIN_DARK, outline=OUTLINE_COLOR)
    # Thumb alongside
    draw_thumb(draw, cx - 32, cy, cx - 32, cy - 30)


def draw_letter_b(draw: ImageDraw.Draw) -> None:
    """B: Flat hand, fingers together pointing up, thumb across palm."""
    cx, cy = 100, 100
    draw_palm(draw, cx, cy + 15, 50, 45)
    # Four fingers up
    for i in range(4):
        x = cx - 20 + i * 13
        draw_finger(draw, x, cy, x, cy - 55, width=12)
    # Thumb across palm
    draw_thumb(draw, cx - 30, cy + 20, cx - 10, cy + 20, width=14)


def draw_letter_c(draw: ImageDraw.Draw) -> None:
    """C: Curved hand forming C shape."""
    cx, cy = 100, 90
    # Draw a C-curve using arc
    draw.arc([(cx - 35, cy - 40), (cx + 35, cy + 40)], start=-60, end=60,
             fill=SKIN_COLOR, width=20)
    draw.arc([(cx - 35, cy - 40), (cx + 35, cy + 40)], start=-60, end=60,
             fill=OUTLINE_COLOR, width=2)


def draw_generic_letter(draw: ImageDraw.Draw, letter: str) -> None:
    """Generic hand shape with letter overlay for letters we haven't custom drawn."""
    cx, cy = 100, 85
    draw_palm(draw, cx, cy, 55, 65)
    # Partially extended fingers
    for i in range(4):
        x = cx - 18 + i * 12
        draw_finger(draw, x, cy - 30, x + (i - 1.5) * 3, cy - 55, width=11)
    # Thumb
    draw_thumb(draw, cx - 32, cy, cx - 42, cy - 20)
    # Letter overlay
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except (OSError, IOError):
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), letter, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((SIZE - tw) / 2, cy - th / 2),
        letter,
        fill=(255, 255, 255, 180),
        font=font,
    )


CUSTOM_LETTERS = {
    "a": draw_letter_a,
    "b": draw_letter_b,
    "c": draw_letter_c,
}


def generate_alphabet() -> None:
    """Generate illustrations for A-Z."""
    ASL_ALPHABET_DIR.mkdir(parents=True, exist_ok=True)

    for i in range(26):
        letter = chr(ord("a") + i)
        img, draw = create_base_image()

        if letter in CUSTOM_LETTERS:
            CUSTOM_LETTERS[letter](draw)
        else:
            draw_generic_letter(draw, letter.upper())

        add_label(draw, letter.upper())
        img.save(str(ASL_ALPHABET_DIR / f"{letter}.png"), "PNG")

    print(f"Generated 26 alphabet images in {ASL_ALPHABET_DIR}")


def generate_numbers() -> None:
    """Generate illustrations for 0-9."""
    ASL_NUMBERS_DIR.mkdir(parents=True, exist_ok=True)

    for digit in range(10):
        img, draw = create_base_image()
        cx, cy = 100, 85
        draw_palm(draw, cx, cy, 55, 60)

        # Draw extended fingers based on count
        extended = min(digit, 5) if digit > 0 else 0
        for i in range(4):
            x = cx - 18 + i * 12
            if i < extended:
                draw_finger(draw, x, cy - 28, x, cy - 58, width=12)
            else:
                draw.ellipse([(x - 6, cy - 34), (x + 6, cy - 22)],
                             fill=SKIN_DARK, outline=OUTLINE_COLOR)

        # Thumb: extended for some numbers
        if digit in (1, 2, 3, 4, 5, 10):
            draw_thumb(draw, cx - 32, cy, cx - 42, cy - 20)
        else:
            draw_thumb(draw, cx - 30, cy + 5, cx - 20, cy + 5, width=14)

        # Number overlay
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        except (OSError, IOError):
            font = ImageFont.load_default()
        label = str(digit)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((SIZE - tw) / 2, cy - 10), label, fill=(255, 255, 255, 160), font=font)

        add_label(draw, str(digit))
        img.save(str(ASL_NUMBERS_DIR / f"{digit}.png"), "PNG")

    print(f"Generated 10 number images in {ASL_NUMBERS_DIR}")


if __name__ == "__main__":
    generate_alphabet()
    generate_numbers()
    print("Done! Images are improved placeholders — replace with real illustrations when available.")
