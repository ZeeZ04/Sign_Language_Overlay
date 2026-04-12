"""Transform English text to ASL grammar structure.

ASL uses a different sentence structure from English:
- Topic-comment order (instead of SVO)
- Time markers go first
- Articles, copulas, and many prepositions are dropped
- WH-question words go at the end
- Negation goes at the end
- Verbs use base form (no tense inflection — tense is shown via time markers)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Words that indicate time — these move to the front of the sentence
TIME_WORDS: set[str] = {
    "yesterday", "today", "tomorrow", "now", "later", "soon",
    "morning", "afternoon", "evening", "night", "tonight",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "always", "sometimes", "often", "recently",
    "last", "next", "ago", "before", "after",
    "week", "month", "year",
}

# Multi-word time phrases (checked before single words)
TIME_PHRASES: list[list[str]] = [
    ["last", "week"], ["last", "month"], ["last", "year"], ["last", "night"],
    ["next", "week"], ["next", "month"], ["next", "year"],
    ["right", "now"], ["long", "ago"],
    ["this", "morning"], ["this", "afternoon"], ["this", "evening"],
    ["this", "week"], ["this", "month"], ["this", "year"],
]

# Words dropped in ASL (articles, copulas, prepositions, auxiliaries)
DROP_WORDS: set[str] = {
    # Articles
    "a", "an", "the",
    # Copulas / be verbs
    "is", "am", "are", "was", "were", "be", "been", "being",
    # Auxiliaries (when not carrying meaning)
    "do", "does", "did",
    # Common prepositions that ASL conveys spatially
    "to", "of", "in", "on", "at", "for", "with",
    "it", "its",
}

# WH-question words — these move to the end in ASL
WH_WORDS: set[str] = {"what", "where", "when", "why", "how", "who", "which"}

# Negation words — these move to the end in ASL
NEGATION_WORDS: set[str] = {"not", "no", "never", "nothing", "nobody", "nowhere", "none"}

# Contraction-to-negation mapping
CONTRACTION_MAP: dict[str, list[str]] = {
    "don't": ["not"],
    "doesn't": ["not"],
    "didn't": ["not"],
    "won't": ["not"],
    "wouldn't": ["not"],
    "can't": ["not"],
    "cannot": ["not"],
    "couldn't": ["not"],
    "shouldn't": ["not"],
    "isn't": ["not"],
    "aren't": ["not"],
    "wasn't": ["not"],
    "weren't": ["not"],
    "haven't": ["not"],
    "hasn't": ["not"],
    "hadn't": ["not"],
}

# Common irregular verb → base form
IRREGULAR_VERBS: dict[str, str] = {
    "went": "go", "gone": "go", "going": "go", "goes": "go",
    "ate": "eat", "eaten": "eat", "eating": "eat", "eats": "eat",
    "ran": "run", "running": "run", "runs": "run",
    "saw": "see", "seen": "see", "seeing": "see", "sees": "see",
    "came": "come", "coming": "come", "comes": "come",
    "had": "have", "has": "have", "having": "have",
    "got": "get", "gotten": "get", "getting": "get", "gets": "get",
    "made": "make", "making": "make", "makes": "make",
    "said": "say", "saying": "say", "says": "say",
    "took": "take", "taken": "take", "taking": "take", "takes": "take",
    "gave": "give", "given": "give", "giving": "give", "gives": "give",
    "told": "tell", "telling": "tell", "tells": "tell",
    "knew": "know", "known": "know", "knowing": "know", "knows": "know",
    "thought": "think", "thinking": "think", "thinks": "think",
    "felt": "feel", "feeling": "feel", "feels": "feel",
    "left": "leave", "leaving": "leave", "leaves": "leave",
    "found": "find", "finding": "find", "finds": "find",
    "wanted": "want", "wanting": "want", "wants": "want",
    "liked": "like", "liking": "like", "likes": "like",
    "loved": "love", "loving": "love", "loves": "love",
    "needed": "need", "needing": "need", "needs": "need",
    "worked": "work", "working": "work", "works": "work",
    "played": "play", "playing": "play", "plays": "play",
    "called": "call", "calling": "call", "calls": "call",
    "tried": "try", "trying": "try", "tries": "try",
    "asked": "ask", "asking": "ask", "asks": "ask",
    "helped": "help", "helping": "help", "helps": "help",
    "started": "start", "starting": "start", "starts": "start",
    "lived": "live", "living": "live", "lives": "live",
    "bought": "buy", "buying": "buy", "buys": "buy",
    "taught": "teach", "teaching": "teach", "teaches": "teach",
    "wrote": "write", "written": "write", "writing": "write", "writes": "write",
    "read": "read",  # irregular but same base form
    "slept": "sleep", "sleeping": "sleep", "sleeps": "sleep",
    "kept": "keep", "keeping": "keep", "keeps": "keep",
    "stood": "stand", "standing": "stand", "stands": "stand",
    "heard": "hear", "hearing": "hear", "hears": "hear",
    "met": "meet", "meeting": "meet", "meets": "meet",
    "brought": "bring", "bringing": "bring", "brings": "bring",
    "sat": "sit", "sitting": "sit", "sits": "sit",
    "spoke": "speak", "spoken": "speak", "speaking": "speak", "speaks": "speak",
    "lost": "lose", "losing": "lose", "loses": "lose",
    "paid": "pay", "paying": "pay", "pays": "pay",
    "sent": "send", "sending": "send", "sends": "send",
    "built": "build", "building": "build", "builds": "build",
    "spent": "spend", "spending": "spend", "spends": "spend",
    "fell": "fall", "fallen": "fall", "falling": "fall", "falls": "fall",
    "held": "hold", "holding": "hold", "holds": "hold",
    "began": "begin", "begun": "begin", "beginning": "begin", "begins": "begin",
    "wore": "wear", "worn": "wear", "wearing": "wear", "wears": "wear",
    "broke": "break", "broken": "break", "breaking": "break", "breaks": "break",
    "chose": "choose", "chosen": "choose", "choosing": "choose", "chooses": "choose",
    "drove": "drive", "driven": "drive", "driving": "drive", "drives": "drive",
    "sang": "sing", "sung": "sing", "singing": "sing", "sings": "sing",
    "drew": "draw", "drawn": "draw", "drawing": "draw", "draws": "draw",
    "grew": "grow", "grown": "grow", "growing": "grow", "grows": "grow",
    "threw": "throw", "thrown": "throw", "throwing": "throw", "throws": "throw",
    "flew": "fly", "flown": "fly", "flying": "fly", "flies": "fly",
    "caught": "catch", "catching": "catch", "catches": "catch",
    "drank": "drink", "drunk": "drink", "drinking": "drink", "drinks": "drink",
    "forgot": "forget", "forgotten": "forget", "forgetting": "forget", "forgets": "forget",
    "understood": "understand", "understanding": "understand", "understands": "understand",
}

_TOKENIZE_RE = re.compile(r"\S+")


@dataclass
class TransformResult:
    """Result of grammar transformation."""
    text: str
    is_question: bool = False
    is_negation: bool = False


class ASLGrammarTransformer:
    """Transform English sentences into ASL grammar order.

    This is a rule-based transformer — not a full NLP parser. It handles
    the most common patterns but won't perfectly reorder every sentence.
    """

    def __init__(self, language: str = "asl") -> None:
        self.language = language

    def transform(self, text: str) -> TransformResult:
        """Transform English text to ASL grammar order.

        Only applies to ASL. Other languages pass through unchanged.
        """
        if self.language != "asl":
            return TransformResult(text=text)

        if not text or not text.strip():
            return TransformResult(text="")

        original_text = text.strip()
        is_question = original_text.endswith("?")

        # Normalize: lowercase, strip trailing punctuation for processing
        working = re.sub(r"[.!?,;:]+$", "", original_text).strip().lower()
        words = self._tokenize(working)

        if not words:
            return TransformResult(text="")

        # Step 1: Expand contractions (don't → not, etc.)
        words = self._expand_contractions(words)

        # Step 2: Extract time markers → move to front
        time_markers, words = self._extract_time_markers(words)

        # Step 3: Handle negation → extract negation words
        negation_markers, words = self._extract_negation(words)

        # Step 4: Drop function words (articles, copulas, prepositions)
        words = self._drop_function_words(words)

        # Step 5: Handle questions
        wh_markers, words = self._extract_wh_words(words)

        # Step 6: Normalize verb tense
        words = [self._normalize_verb(w) for w in words]

        # Step 7: Reassemble in ASL order:
        # TIME + TOPIC/COMMENT + NEGATION + WH-WORD
        result_words = time_markers + words + negation_markers + wh_markers

        # Remove any empty strings
        result_words = [w for w in result_words if w]

        if not result_words:
            return TransformResult(text="")

        result_text = " ".join(result_words).upper()
        is_negation = len(negation_markers) > 0

        return TransformResult(
            text=result_text,
            is_question=is_question or len(wh_markers) > 0,
            is_negation=is_negation,
        )

    def _tokenize(self, text: str) -> list[str]:
        return _TOKENIZE_RE.findall(text)

    def _expand_contractions(self, words: list[str]) -> list[str]:
        result: list[str] = []
        for word in words:
            if word in CONTRACTION_MAP:
                result.extend(CONTRACTION_MAP[word])
            else:
                result.append(word)
        return result

    def _extract_time_markers(self, words: list[str]) -> tuple[list[str], list[str]]:
        """Extract time expressions and return (time_markers, remaining_words)."""
        time_markers: list[str] = []
        remaining = list(words)

        # Check multi-word time phrases first
        for phrase in TIME_PHRASES:
            phrase_len = len(phrase)
            i = 0
            while i <= len(remaining) - phrase_len:
                if remaining[i:i + phrase_len] == phrase:
                    time_markers.append(" ".join(phrase))
                    remaining = remaining[:i] + remaining[i + phrase_len:]
                else:
                    i += 1

        # Check single time words
        still_remaining: list[str] = []
        for word in remaining:
            if word in TIME_WORDS and word not in {"before", "after", "last", "next"}:
                # "last"/"next" alone aren't time markers (only in phrases)
                time_markers.append(word)
            else:
                still_remaining.append(word)

        return time_markers, still_remaining

    def _extract_negation(self, words: list[str]) -> tuple[list[str], list[str]]:
        """Extract negation words and return (negation_markers, remaining_words)."""
        negation: list[str] = []
        remaining: list[str] = []
        for word in words:
            if word in NEGATION_WORDS:
                if word not in negation:
                    negation.append(word)
            else:
                remaining.append(word)
        return negation, remaining

    def _extract_wh_words(self, words: list[str]) -> tuple[list[str], list[str]]:
        """Extract WH-question words and return (wh_markers, remaining_words)."""
        wh: list[str] = []
        remaining: list[str] = []
        for word in words:
            if word in WH_WORDS:
                wh.append(word)
            else:
                remaining.append(word)
        return wh, remaining

    def _drop_function_words(self, words: list[str]) -> list[str]:
        """Remove articles, copulas, and common prepositions."""
        return [w for w in words if w not in DROP_WORDS]

    def _normalize_verb(self, word: str) -> str:
        """Convert inflected verbs to base form."""
        # Check irregular verbs first
        if word in IRREGULAR_VERBS:
            return IRREGULAR_VERBS[word]

        # Regular verb suffix stripping
        if word.endswith("ing") and len(word) > 5:
            # running → run (double consonant)
            base = word[:-3]
            if len(base) >= 2 and base[-1] == base[-2]:
                return base[:-1]
            # eating → eat
            return base
        if word.endswith("ed") and len(word) > 4:
            base = word[:-2]
            # tried → try (ied → y)
            if word.endswith("ied"):
                return word[:-3] + "y"
            # played → play
            if base[-1] == base[-2] if len(base) >= 2 else False:
                return base[:-1]
            return base
        if word.endswith("es") and len(word) > 4:
            return word[:-2]
        if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
            return word[:-1]

        return word
