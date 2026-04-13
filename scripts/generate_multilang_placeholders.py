"""Generate placeholder images and mapping.json for ISL and Auslan.

Also generates curated word sign entries for BSL, ISL, and Auslan.
Each language gets alphabet, numbers, word placeholders, and a mapping.json.
"""

from __future__ import annotations

import json
import string
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_BASE = PROJECT_ROOT / "assets" / "signs"
SIZE = 200

# Language configurations
LANGUAGES = {
    "isl": {
        "name": "Irish Sign Language",
        "two_handed": True,
        "notes": "Related to French Sign Language (LSF). Two-handed alphabet.",
        "bg_color": (35, 65, 45),
        "text_color": (200, 255, 180),
        "accent_color": (80, 180, 100),
    },
    "auslan": {
        "name": "Australian Sign Language",
        "two_handed": True,
        "notes": "Related to BSL. Two-handed alphabet.",
        "bg_color": (60, 45, 35),
        "text_color": (255, 220, 160),
        "accent_color": (200, 140, 80),
    },
}

# --- Curated word vocabularies ---
# These are common everyday words. Since BSL, ISL, and Auslan don't have
# freely downloadable sign datasets, we curate a starter vocabulary.
# The image files are placeholders; replace with real illustrations later.

# Core vocabulary shared across all three languages.
# Each sign language has its own signs for these words, but the English
# glosses are shared. Duration estimates are based on typical sign durations.
COMMON_WORDS = {
    # Greetings & social
    "hello": {"duration_ms": 500, "category": "greeting"},
    "goodbye": {"duration_ms": 600, "category": "greeting"},
    "please": {"duration_ms": 500, "category": "social"},
    "thank_you": {"duration_ms": 600, "category": "social", "variants": ["thanks"]},
    "sorry": {"duration_ms": 500, "category": "social"},
    "welcome": {"duration_ms": 500, "category": "social"},
    "yes": {"duration_ms": 400, "category": "social"},
    "no": {"duration_ms": 400, "category": "social"},
    # Pronouns
    "i": {"duration_ms": 300, "category": "pronoun", "variants": ["me"]},
    "you": {"duration_ms": 300, "category": "pronoun"},
    "he": {"duration_ms": 300, "category": "pronoun"},
    "she": {"duration_ms": 300, "category": "pronoun"},
    "we": {"duration_ms": 300, "category": "pronoun", "variants": ["us"]},
    "they": {"duration_ms": 300, "category": "pronoun", "variants": ["them"]},
    # Common verbs
    "want": {"duration_ms": 500, "category": "verb"},
    "need": {"duration_ms": 500, "category": "verb"},
    "like": {"duration_ms": 500, "category": "verb"},
    "love": {"duration_ms": 500, "category": "verb"},
    "know": {"duration_ms": 500, "category": "verb"},
    "think": {"duration_ms": 500, "category": "verb"},
    "go": {"duration_ms": 500, "category": "verb"},
    "come": {"duration_ms": 500, "category": "verb"},
    "eat": {"duration_ms": 500, "category": "verb"},
    "drink": {"duration_ms": 500, "category": "verb"},
    "sleep": {"duration_ms": 600, "category": "verb"},
    "work": {"duration_ms": 500, "category": "verb"},
    "help": {"duration_ms": 500, "category": "verb"},
    "give": {"duration_ms": 500, "category": "verb"},
    "see": {"duration_ms": 400, "category": "verb", "variants": ["look"]},
    "hear": {"duration_ms": 500, "category": "verb", "variants": ["listen"]},
    "say": {"duration_ms": 500, "category": "verb", "variants": ["tell"]},
    "learn": {"duration_ms": 600, "category": "verb"},
    "teach": {"duration_ms": 600, "category": "verb"},
    "understand": {"duration_ms": 600, "category": "verb"},
    "wait": {"duration_ms": 500, "category": "verb"},
    "stop": {"duration_ms": 400, "category": "verb"},
    "start": {"duration_ms": 500, "category": "verb", "variants": ["begin"]},
    "finish": {"duration_ms": 500, "category": "verb", "variants": ["done", "end"]},
    "try": {"duration_ms": 500, "category": "verb"},
    "find": {"duration_ms": 500, "category": "verb"},
    "sit": {"duration_ms": 500, "category": "verb"},
    "stand": {"duration_ms": 500, "category": "verb"},
    "walk": {"duration_ms": 500, "category": "verb"},
    "run": {"duration_ms": 500, "category": "verb"},
    "buy": {"duration_ms": 500, "category": "verb"},
    "open": {"duration_ms": 500, "category": "verb"},
    "close": {"duration_ms": 500, "category": "verb", "variants": ["shut"]},
    "read": {"duration_ms": 500, "category": "verb"},
    "write": {"duration_ms": 500, "category": "verb"},
    "play": {"duration_ms": 500, "category": "verb"},
    "cook": {"duration_ms": 600, "category": "verb"},
    "clean": {"duration_ms": 500, "category": "verb"},
    "remember": {"duration_ms": 600, "category": "verb"},
    "forget": {"duration_ms": 600, "category": "verb"},
    # Common nouns
    "family": {"duration_ms": 600, "category": "people"},
    "mother": {"duration_ms": 500, "category": "people", "variants": ["mum", "mom"]},
    "father": {"duration_ms": 500, "category": "people", "variants": ["dad"]},
    "brother": {"duration_ms": 500, "category": "people"},
    "sister": {"duration_ms": 500, "category": "people"},
    "baby": {"duration_ms": 500, "category": "people"},
    "friend": {"duration_ms": 500, "category": "people"},
    "person": {"duration_ms": 500, "category": "people"},
    "man": {"duration_ms": 400, "category": "people"},
    "woman": {"duration_ms": 400, "category": "people"},
    "child": {"duration_ms": 500, "category": "people", "variants": ["kid"]},
    "boy": {"duration_ms": 400, "category": "people"},
    "girl": {"duration_ms": 400, "category": "people"},
    "teacher": {"duration_ms": 600, "category": "people"},
    "doctor": {"duration_ms": 600, "category": "people"},
    # Places
    "house": {"duration_ms": 600, "category": "place", "variants": ["home"]},
    "school": {"duration_ms": 500, "category": "place"},
    "hospital": {"duration_ms": 600, "category": "place"},
    "shop": {"duration_ms": 500, "category": "place", "variants": ["store"]},
    # Objects
    "food": {"duration_ms": 500, "category": "object"},
    "water": {"duration_ms": 500, "category": "object"},
    "coffee": {"duration_ms": 500, "category": "object"},
    "tea": {"duration_ms": 500, "category": "object"},
    "book": {"duration_ms": 500, "category": "object"},
    "phone": {"duration_ms": 500, "category": "object"},
    "computer": {"duration_ms": 600, "category": "object"},
    "money": {"duration_ms": 500, "category": "object"},
    "car": {"duration_ms": 500, "category": "object"},
    "bus": {"duration_ms": 500, "category": "object"},
    "door": {"duration_ms": 500, "category": "object"},
    # Time
    "today": {"duration_ms": 500, "category": "time"},
    "tomorrow": {"duration_ms": 500, "category": "time"},
    "yesterday": {"duration_ms": 500, "category": "time"},
    "morning": {"duration_ms": 500, "category": "time"},
    "afternoon": {"duration_ms": 500, "category": "time"},
    "evening": {"duration_ms": 500, "category": "time", "variants": ["night"]},
    "now": {"duration_ms": 400, "category": "time"},
    "later": {"duration_ms": 500, "category": "time"},
    "week": {"duration_ms": 500, "category": "time"},
    "month": {"duration_ms": 500, "category": "time"},
    "year": {"duration_ms": 500, "category": "time"},
    # Adjectives
    "good": {"duration_ms": 500, "category": "adjective"},
    "bad": {"duration_ms": 500, "category": "adjective"},
    "big": {"duration_ms": 500, "category": "adjective", "variants": ["large"]},
    "small": {"duration_ms": 500, "category": "adjective", "variants": ["little"]},
    "hot": {"duration_ms": 400, "category": "adjective"},
    "cold": {"duration_ms": 400, "category": "adjective"},
    "new": {"duration_ms": 400, "category": "adjective"},
    "old": {"duration_ms": 400, "category": "adjective"},
    "happy": {"duration_ms": 500, "category": "adjective"},
    "sad": {"duration_ms": 500, "category": "adjective"},
    "angry": {"duration_ms": 500, "category": "adjective"},
    "tired": {"duration_ms": 500, "category": "adjective"},
    "sick": {"duration_ms": 500, "category": "adjective", "variants": ["ill"]},
    "hungry": {"duration_ms": 500, "category": "adjective"},
    "beautiful": {"duration_ms": 600, "category": "adjective"},
    "easy": {"duration_ms": 400, "category": "adjective"},
    "hard": {"duration_ms": 400, "category": "adjective", "variants": ["difficult"]},
    "right": {"duration_ms": 400, "category": "adjective", "variants": ["correct"]},
    "wrong": {"duration_ms": 400, "category": "adjective"},
    "same": {"duration_ms": 400, "category": "adjective"},
    "different": {"duration_ms": 500, "category": "adjective"},
    "important": {"duration_ms": 600, "category": "adjective"},
    # Colors
    "red": {"duration_ms": 400, "category": "color"},
    "blue": {"duration_ms": 400, "category": "color"},
    "green": {"duration_ms": 400, "category": "color"},
    "yellow": {"duration_ms": 400, "category": "color"},
    "black": {"duration_ms": 400, "category": "color"},
    "white": {"duration_ms": 400, "category": "color"},
    # Question words
    "what": {"duration_ms": 400, "category": "question"},
    "where": {"duration_ms": 400, "category": "question"},
    "when": {"duration_ms": 400, "category": "question"},
    "why": {"duration_ms": 400, "category": "question"},
    "how": {"duration_ms": 400, "category": "question"},
    "who": {"duration_ms": 400, "category": "question"},
    # Other common
    "more": {"duration_ms": 400, "category": "other"},
    "again": {"duration_ms": 500, "category": "other"},
    "enough": {"duration_ms": 500, "category": "other"},
    "here": {"duration_ms": 400, "category": "other"},
    "there": {"duration_ms": 400, "category": "other"},
    "always": {"duration_ms": 500, "category": "other"},
    "never": {"duration_ms": 500, "category": "other"},
    "sometimes": {"duration_ms": 600, "category": "other"},
    "maybe": {"duration_ms": 500, "category": "other"},
    "all": {"duration_ms": 400, "category": "other", "variants": ["everything"]},
    "name": {"duration_ms": 500, "category": "other"},
}

# BSL-specific additional words (British English variants)
BSL_EXTRA = {
    "brilliant": {"duration_ms": 600, "category": "adjective", "variants": ["great"]},
    "rubbish": {"duration_ms": 500, "category": "adjective"},
    "toilet": {"duration_ms": 500, "category": "place", "variants": ["loo"]},
    "holiday": {"duration_ms": 600, "category": "time", "variants": ["vacation"]},
    "flat": {"duration_ms": 500, "category": "place", "variants": ["apartment"]},
    "deaf": {"duration_ms": 400, "category": "adjective"},
    "hearing": {"duration_ms": 500, "category": "adjective"},
    "sign": {"duration_ms": 400, "category": "verb"},
    "language": {"duration_ms": 600, "category": "noun"},
    "interpreter": {"duration_ms": 700, "category": "people"},
}

# ISL-specific additional words
ISL_EXTRA = {
    "deaf": {"duration_ms": 400, "category": "adjective"},
    "hearing": {"duration_ms": 500, "category": "adjective"},
    "sign": {"duration_ms": 400, "category": "verb"},
    "language": {"duration_ms": 600, "category": "noun"},
    "ireland": {"duration_ms": 600, "category": "place"},
    "dublin": {"duration_ms": 600, "category": "place"},
}

# Auslan-specific additional words
AUSLAN_EXTRA = {
    "deaf": {"duration_ms": 400, "category": "adjective"},
    "hearing": {"duration_ms": 500, "category": "adjective"},
    "sign": {"duration_ms": 400, "category": "verb"},
    "language": {"duration_ms": 600, "category": "noun"},
    "australia": {"duration_ms": 600, "category": "place"},
    "mate": {"duration_ms": 400, "category": "social", "variants": ["friend"]},
}


def _get_fonts() -> tuple:
    for path in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            big = ImageFont.truetype(path, 80)
            med = ImageFont.truetype(path, 18)
            small = ImageFont.truetype(path, 11)
            return big, med, small
        except OSError:
            continue
    fallback = ImageFont.load_default()
    return fallback, fallback, fallback


def generate_letter_image(
    label: str, output_path: Path, tag: str, bg_color: tuple, text_color: tuple, accent_color: tuple,
) -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    big_font, _, small_font = _get_fonts()

    draw.rounded_rectangle(
        [(10, 10), (SIZE - 10, SIZE - 10)],
        radius=20,
        fill=bg_color + (230,),
        outline=accent_color + (255,),
        width=3,
    )

    bbox = draw.textbbox((0, 0), label, font=big_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((SIZE - tw) / 2, (SIZE - th) / 2 - bbox[1]), label, fill=text_color, font=big_font)
    draw.text((SIZE / 2 - 12, SIZE - 35), tag, fill=accent_color + (180,), font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def generate_word_image(
    word: str, output_path: Path, tag: str, bg_color: tuple, text_color: tuple, accent_color: tuple,
) -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _, med_font, small_font = _get_fonts()

    draw.rounded_rectangle(
        [(2, 2), (SIZE - 3, SIZE - 3)],
        radius=12,
        fill=bg_color + (220,),
        outline=accent_color + (255,),
        width=2,
    )

    # Hand icon area
    center_y = SIZE // 2 - 15
    draw.ellipse(
        [(SIZE // 2 - 30, center_y - 30), (SIZE // 2 + 30, center_y + 30)],
        fill=tuple(max(0, c - 15) for c in bg_color) + (200,),
        outline=accent_color + (255,),
    )

    # Word label
    display = word.upper().replace("_", " ")
    if len(display) > 12:
        display = display[:11] + "..."
    bbox = draw.textbbox((0, 0), display, font=med_font)
    tw = bbox[2] - bbox[0]
    draw.text(((SIZE - tw) / 2, SIZE - 40), display, fill=text_color + (255,), font=med_font)

    # Tag
    draw.text((SIZE // 2 - 14, 8), tag.upper(), fill=accent_color + (180,), font=small_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def build_language(
    lang_code: str,
    lang_name: str,
    two_handed: bool,
    notes: str,
    extra_words: dict,
    bg_color: tuple,
    text_color: tuple,
    accent_color: tuple,
) -> None:
    assets_dir = ASSETS_BASE / lang_code
    tag = lang_code.upper()

    print(f"\n=== {lang_name} ({lang_code}) ===")

    # Alphabet
    for letter in string.ascii_lowercase:
        path = assets_dir / "alphabet" / f"{letter}.png"
        if not path.exists():
            generate_letter_image(letter.upper(), path, tag, bg_color, text_color, accent_color)
    print("  Alphabet: 26 letters")

    # Numbers
    for digit in range(10):
        path = assets_dir / "numbers" / f"{digit}.png"
        if not path.exists():
            generate_letter_image(str(digit), path, tag, bg_color, text_color, accent_color)
    print("  Numbers: 0-9")

    # Word signs (common + language-specific)
    all_words = {**COMMON_WORDS, **extra_words}
    words_dir = assets_dir / "words"
    words_dir.mkdir(parents=True, exist_ok=True)

    word_entries = {}
    for word, info in all_words.items():
        img_path = words_dir / f"{word}.png"
        if not img_path.exists():
            generate_word_image(word, img_path, tag, bg_color, text_color, accent_color)

        entry = {
            "file": f"words/{word}.png",
            "duration_ms": info["duration_ms"],
            "category": info.get("category", "general"),
            "priority": True,
            "source": "curated",
        }
        if "variants" in info:
            entry["variants"] = info["variants"]
        word_entries[word] = entry

    print(f"  Words: {len(word_entries)} signs")

    # Build mapping.json
    mapping = {
        "alphabet": {
            c: {"file": f"alphabet/{c}.png", "duration_ms": 350}
            for c in string.ascii_lowercase
        },
        "numbers": {
            str(n): {"file": f"numbers/{n}.png", "duration_ms": 400}
            for n in range(10)
        },
        "words": word_entries,
        "special": {
            "space": {"file": None, "duration_ms": 200},
            "unknown": {"file": "alphabet/a.png", "duration_ms": 250},
        },
        "meta": {
            "language": lang_code,
            "name": lang_name,
            "two_handed": two_handed,
            "notes": notes,
        },
    }

    with open(assets_dir / "mapping.json", "w") as f:
        json.dump(mapping, f, indent=2)

    print(f"  mapping.json written ({26 + 10 + len(word_entries)} total entries)")


def update_bsl_words() -> None:
    """Add word signs to the existing BSL mapping."""
    bsl_dir = ASSETS_BASE / "bsl"
    mapping_path = bsl_dir / "mapping.json"

    with open(mapping_path) as f:
        mapping = json.load(f)

    existing_words = mapping.get("words", {})
    all_words = {**COMMON_WORDS, **BSL_EXTRA}
    tag = "BSL"
    cfg = {
        "bg_color": (40, 60, 80),
        "text_color": (255, 200, 100),
        "accent_color": (100, 160, 220),
    }

    words_dir = bsl_dir / "words"
    words_dir.mkdir(parents=True, exist_ok=True)
    added = 0

    for word, info in all_words.items():
        if word in existing_words:
            continue

        img_path = words_dir / f"{word}.png"
        if not img_path.exists():
            generate_word_image(
                word, img_path, tag,
                cfg["bg_color"], cfg["text_color"], cfg["accent_color"],
            )

        entry = {
            "file": f"words/{word}.png",
            "duration_ms": info["duration_ms"],
            "category": info.get("category", "general"),
            "priority": True,
            "source": "curated",
        }
        if "variants" in info:
            entry["variants"] = info["variants"]
        existing_words[word] = entry
        added += 1

    mapping["words"] = existing_words

    with open(mapping_path, "w") as f:
        json.dump(mapping, f, indent=2)

    print("\n=== British Sign Language (bsl) ===")
    print(f"  Added {added} word signs (total: {len(existing_words)})")
    print("  mapping.json updated")


def main() -> None:
    print("Generating multi-language sign assets...")

    # Update BSL with word signs
    update_bsl_words()

    # Generate ISL
    isl_cfg = LANGUAGES["isl"]
    build_language(
        "isl", isl_cfg["name"], isl_cfg["two_handed"], isl_cfg["notes"],
        ISL_EXTRA, isl_cfg["bg_color"], isl_cfg["text_color"], isl_cfg["accent_color"],
    )

    # Generate Auslan
    auslan_cfg = LANGUAGES["auslan"]
    build_language(
        "auslan", auslan_cfg["name"], auslan_cfg["two_handed"], auslan_cfg["notes"],
        AUSLAN_EXTRA, auslan_cfg["bg_color"], auslan_cfg["text_color"], auslan_cfg["accent_color"],
    )

    print("\nDone! Run with: python main.py -s subtitles.srt -l bsl --use-word-signs")


if __name__ == "__main__":
    main()
