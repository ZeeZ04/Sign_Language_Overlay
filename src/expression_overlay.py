"""Display facial expression hints as visual indicators.

Sign languages use facial expressions grammatically. This provides
visual hints for important expressions like questions, negations, etc.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

import pygame

logger = logging.getLogger(__name__)


class ExpressionType(Enum):
    NONE = "none"
    QUESTION = "question"
    EMPHASIS = "emphasis"
    NEGATION = "negation"
    AFFIRMATIVE = "affirmative"
    POSITIVE = "positive"
    NEGATIVE = "negative"


@dataclass
class ExpressionHint:
    type: ExpressionType
    intensity: float = 1.0
    duration_ms: int = 1000


# Text labels (avoids emoji/font issues across platforms)
EXPRESSION_LABELS = {
    ExpressionType.NONE: "",
    ExpressionType.QUESTION: "?",
    ExpressionType.EMPHASIS: "!",
    ExpressionType.NEGATION: "X",
    ExpressionType.AFFIRMATIVE: "OK",
    ExpressionType.POSITIVE: "+",
    ExpressionType.NEGATIVE: "-",
}

EXPRESSION_COLORS = {
    ExpressionType.NONE: (255, 255, 255),
    ExpressionType.QUESTION: (100, 200, 255),
    ExpressionType.EMPHASIS: (255, 150, 100),
    ExpressionType.NEGATION: (255, 100, 100),
    ExpressionType.AFFIRMATIVE: (100, 255, 150),
    ExpressionType.POSITIVE: (255, 220, 100),
    ExpressionType.NEGATIVE: (150, 150, 200),
}


class ExpressionOverlay:
    """Display facial expression hints as icons alongside signs."""

    def __init__(self, font_size: int = 32) -> None:
        self.font_size = font_size
        self.current_hint: ExpressionHint | None = None
        self.elapsed_ms: float = 0
        self._font: pygame.font.Font | None = None

    def _ensure_font(self) -> None:
        if self._font is None:
            pygame.font.init()
            self._font = pygame.font.Font(None, self.font_size)

    def set_expression(self, hint: ExpressionHint) -> None:
        self.current_hint = hint
        self.elapsed_ms = 0

    def clear_expression(self) -> None:
        self.current_hint = None
        self.elapsed_ms = 0

    def update(self, dt_ms: float) -> None:
        if self.current_hint is None:
            return

        self.elapsed_ms += dt_ms

        if self.elapsed_ms >= self.current_hint.duration_ms:
            self.current_hint = None
            self.elapsed_ms = 0

    def render(self, size: tuple[int, int]) -> pygame.Surface | None:
        if self.current_hint is None or self.current_hint.type == ExpressionType.NONE:
            return None

        self._ensure_font()

        surface = pygame.Surface(size, pygame.SRCALPHA)
        label = EXPRESSION_LABELS.get(self.current_hint.type, "")
        color = EXPRESSION_COLORS.get(self.current_hint.type, (255, 255, 255))

        if not label:
            return None

        # Calculate fade-out in last 20% of duration
        alpha = 255
        if self.current_hint.duration_ms > 0:
            progress = self.elapsed_ms / self.current_hint.duration_ms
            if progress > 0.8:
                alpha = int(255 * (1 - (progress - 0.8) / 0.2))

        alpha = int(alpha * self.current_hint.intensity)

        # Draw a small circular background
        indicator_size = min(size[0], size[1]) // 3
        cx, cy = size[0] - indicator_size, 0
        pygame.draw.circle(
            surface,
            color + (max(0, min(255, alpha // 2)),),
            (cx + indicator_size // 2, cy + indicator_size // 2),
            indicator_size // 2,
        )

        # Render text label
        text_surface = self._font.render(label, True, (255, 255, 255))
        text_surface.set_alpha(alpha)
        text_rect = text_surface.get_rect(
            center=(cx + indicator_size // 2, cy + indicator_size // 2),
        )
        surface.blit(text_surface, text_rect)

        return surface

    def infer_expression(self, text: str) -> ExpressionHint | None:
        """Infer expression from text using simple heuristics."""
        text_stripped = text.strip()
        text_lower = text_stripped.lower()

        if text_stripped.endswith("?") or text_lower.startswith(
            ("what", "who", "where", "when", "why", "how", "is ", "are ", "do ", "does ",
             "can ", "could ", "would ", "should ")
        ):
            return ExpressionHint(ExpressionType.QUESTION, duration_ms=1500)

        negation_words = ("no", "not", "don't", "doesn't", "can't", "won't", "never", "none")
        if any(w in text_lower.split() for w in negation_words):
            return ExpressionHint(ExpressionType.NEGATION, duration_ms=1000)

        if text_stripped.endswith("!") or (len(text_stripped) > 3 and text_stripped.isupper()):
            return ExpressionHint(ExpressionType.EMPHASIS, duration_ms=800)

        positive_words = ("yes", "good", "great", "thanks", "please", "love", "like", "happy")
        if any(w in text_lower.split() for w in positive_words):
            return ExpressionHint(ExpressionType.POSITIVE, intensity=0.7, duration_ms=800)

        return None
