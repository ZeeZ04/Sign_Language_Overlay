"""Integrate ASL-LEX vocabulary data into the project's mapping.json.

Reads sign_props.json from ASL-LEX and adds word sign entries to the
existing mapping.json, generating placeholder images for new words.

ASL-LEX source: https://github.com/ASL-LEX/asl-lex
License: CC BY-NC 4.0 (non-commercial)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
ASL_ASSETS = PROJECT_ROOT / "assets" / "signs" / "asl"
MAPPING_PATH = ASL_ASSETS / "mapping.json"
WORDS_DIR = ASL_ASSETS / "words"

# Common words to prioritize (most useful for everyday communication)
PRIORITY_WORDS: set[str] = {
    # Greetings & social
    "hello", "goodbye", "please", "thank-you", "sorry", "welcome",
    # Pronouns
    "i", "you", "he", "she", "we", "they",
    # Common verbs
    "want", "need", "like", "love", "hate", "know", "think", "feel",
    "go", "come", "eat", "drink", "sleep", "work", "play", "help",
    "give", "take", "make", "see", "hear", "say", "tell", "ask",
    "learn", "teach", "read", "write", "understand", "remember",
    "wait", "stop", "start", "finish", "try", "find", "look",
    "sit", "stand", "walk", "run", "drive", "fly",
    "buy", "pay", "open", "close", "clean", "cook",
    # Common nouns
    "family", "mother", "father", "brother", "sister", "baby",
    "friend", "person", "man", "woman", "child", "boy", "girl",
    "house", "school", "hospital", "store", "church", "restaurant",
    "car", "bus", "train", "airplane",
    "food", "water", "coffee", "milk", "bread", "meat", "fruit",
    "cat", "dog", "bird", "fish",
    "book", "phone", "computer", "money", "key", "door", "window",
    "day", "night", "morning", "afternoon", "evening",
    "week", "month", "year", "today", "tomorrow", "yesterday",
    "time", "hour", "minute",
    # Common adjectives
    "good", "bad", "big", "small", "hot", "cold", "new", "old",
    "happy", "sad", "angry", "tired", "sick", "hungry", "thirsty",
    "beautiful", "ugly", "fast", "slow", "easy", "hard",
    "right", "wrong", "same", "different", "important",
    # Colors
    "red", "blue", "green", "yellow", "black", "white", "orange", "purple",
    # Numbers as words
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    # Question words
    "what", "where", "when", "why", "how", "who",
    # Other common
    "yes", "no", "maybe", "more", "again", "enough",
    "here", "there", "now", "later", "soon",
    "always", "never", "sometimes",
    "all", "some", "many", "few",
    "name", "age", "color",
}


def generate_word_placeholder(word: str, output_path: Path, size: int = 200) -> None:
    """Generate a labeled placeholder image for a word sign."""
    img = Image.new("RGBA", (size, size), (45, 55, 72, 220))
    draw = ImageDraw.Draw(img)

    # Draw border
    draw.rounded_rectangle(
        [(2, 2), (size - 3, size - 3)],
        radius=12,
        outline=(100, 140, 200, 255),
        width=2,
    )

    # Draw hand icon area
    center_y = size // 2 - 15
    draw.ellipse(
        [(size // 2 - 30, center_y - 30), (size // 2 + 30, center_y + 30)],
        fill=(60, 80, 110, 200),
        outline=(120, 160, 220, 255),
    )

    # Draw sign label
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
    except (OSError, IOError):
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Word text at bottom
    display_word = word.upper().replace("-", " ").replace("_", " ")
    if len(display_word) > 12:
        display_word = display_word[:11] + "..."
    bbox = draw.textbbox((0, 0), display_word, font=font_large)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((size - tw) / 2, size - 40),
        display_word,
        fill=(220, 230, 255, 255),
        font=font_large,
    )

    # "ASL" label at top
    draw.text((size // 2 - 12, 8), "ASL", fill=(150, 170, 200, 180), font=font_small)

    img.save(str(output_path), "PNG")


def load_asl_lex(asl_lex_path: str) -> list[dict]:
    """Load ASL-LEX sign_props.json."""
    path = Path(asl_lex_path)
    if not path.exists():
        logger.error("ASL-LEX data not found at: %s", path)
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    logger.info("Loaded %d signs from ASL-LEX", len(data))
    return data


def extract_word_entries(asl_lex_data: list[dict]) -> dict[str, dict]:
    """Extract word sign entries from ASL-LEX data."""
    words: dict[str, dict] = {}

    for entry in asl_lex_data:
        entry_id = entry.get("EntryID", "").strip().lower()
        if not entry_id:
            continue

        # Get English translations
        translations = entry.get("SignBankEnglishTranslations", "")
        dominant = entry.get("DominantTranslation", entry_id)

        # Normalize key (safe filename)
        key = entry_id.replace(" ", "_").replace("-", "_").replace("/", "_or_").replace("\\", "_")

        # Get phonological properties
        handshape = entry.get("Handshape.2.0", "")
        selected_fingers = entry.get("SelectedFingers.2.0", "")
        flexion = entry.get("Flexion.2.0", "")
        location = entry.get("MajorLocation.2.0", "")
        movement = entry.get("Movement.2.0", "")
        sign_type = entry.get("SignType.2.0", "")
        duration = entry.get("SignDuration(ms)", 600)
        lexical_class = entry.get("LexicalClass", "")
        semantic_field = entry.get("SignBankSemanticField", "")

        # Build variants list from translations
        variants = []
        if translations:
            for t in str(translations).split(","):
                t = t.strip().lower()
                if t and t != key.replace("_", " "):
                    variants.append(t)
        if dominant and dominant.lower() != key.replace("_", " "):
            variants.append(dominant.lower())

        # Determine priority
        is_priority = key.replace("_", "-") in PRIORITY_WORDS or key in PRIORITY_WORDS

        # Ensure duration is reasonable
        if not isinstance(duration, (int, float)) or duration <= 0:
            duration = 600
        duration = max(300, min(1200, int(duration)))

        words[key] = {
            "file": f"words/{key}.png",
            "duration_ms": duration,
            "variants": list(set(variants))[:5],  # Limit variants
            "category": semantic_field or lexical_class or "general",
            "handshape": handshape,
            "selected_fingers": selected_fingers,
            "flexion": flexion,
            "location": location,
            "movement": movement,
            "sign_type": sign_type,
            "priority": is_priority,
            "source": "asl-lex",
        }

    logger.info("Extracted %d word entries (%d priority)",
                len(words), sum(1 for w in words.values() if w.get("priority")))
    return words


def main() -> None:
    asl_lex_path = "/tmp/asl-lex/visualization/data/sign_props.json"

    # Load ASL-LEX
    asl_lex_data = load_asl_lex(asl_lex_path)

    # Extract word entries
    new_words = extract_word_entries(asl_lex_data)

    # Load existing mapping
    with open(MAPPING_PATH) as f:
        mapping = json.load(f)

    existing_words = mapping.get("words", {})
    logger.info("Existing words in mapping: %d", len(existing_words))

    # Merge: keep existing entries, add new ones
    # Remove variants that conflict with existing canonical words
    existing_keys = set(existing_words.keys())
    for key, entry in new_words.items():
        entry["variants"] = [v for v in entry.get("variants", [])
                             if v.replace(" ", "_") not in existing_keys]

    added = 0
    WORDS_DIR.mkdir(parents=True, exist_ok=True)
    for key, entry in new_words.items():
        if key not in existing_words:
            existing_words[key] = entry
            # Generate placeholder image
            img_path = ASL_ASSETS / entry["file"]
            if not img_path.exists():
                generate_word_placeholder(key, img_path)
            added += 1

    mapping["words"] = existing_words

    # Save updated mapping
    with open(MAPPING_PATH, "w") as f:
        json.dump(mapping, f, indent=2)

    logger.info("Added %d new word entries (total: %d)", added, len(existing_words))
    logger.info("Mapping saved to: %s", MAPPING_PATH)

    # Print priority words that were added
    priority_added = [k for k, v in new_words.items() if v.get("priority") and k not in set(existing_words) - set(new_words)]
    if priority_added:
        logger.info("Priority words available: %s", ", ".join(sorted(priority_added)[:30]))


if __name__ == "__main__":
    main()
