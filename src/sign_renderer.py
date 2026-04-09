"""Load and manage hand sign images, provide rendering interface."""

from __future__ import annotations

import logging
from pathlib import Path

import pygame

from .text_to_sign import SignToken

logger = logging.getLogger(__name__)


class SignRenderer:
    def __init__(self, assets_path: str, size: int = 200) -> None:
        self.assets_path = Path(assets_path)
        self.size = size
        self._cache: dict[str, pygame.Surface] = {}
        self._placeholder: pygame.Surface | None = None

    def load_assets(self) -> None:
        if not self.assets_path.exists():
            raise FileNotFoundError(f"Assets directory not found: {self.assets_path}")

        # Load mapping to know what files to expect
        import json
        mapping_path = self.assets_path / "mapping.json"
        if not mapping_path.exists():
            raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

        with open(mapping_path, "r") as f:
            mapping = json.load(f)

        loaded = 0
        for category in ("alphabet", "numbers"):
            for key, info in mapping.get(category, {}).items():
                filepath = self.assets_path / info["file"]
                if filepath.exists():
                    surface = self._load_and_scale(filepath)
                    if surface:
                        self._cache[key] = surface
                        loaded += 1
                else:
                    logger.warning("Missing asset: %s", filepath)

        # Load word sign assets
        for key, info in mapping.get("words", {}).items():
            filepath = self.assets_path / info["file"]
            if filepath.exists():
                surface = self._load_and_scale(filepath)
                if surface:
                    self._cache[f"word:{key}"] = surface
                    loaded += 1
            else:
                logger.warning("Missing word asset: %s", filepath)

        # Load unknown/placeholder
        unknown_info = mapping.get("special", {}).get("unknown", {})
        if unknown_info.get("file"):
            unknown_path = self.assets_path / unknown_info["file"]
            if unknown_path.exists():
                self._placeholder = self._load_and_scale(unknown_path)

        if self._placeholder is None:
            self._placeholder = self._generate_fallback_placeholder()

        logger.info("Loaded %d sign assets from %s", loaded, self.assets_path)

    def get_sign_surface(self, sign_id: str) -> pygame.Surface | None:
        if sign_id == "space":
            return None
        return self._cache.get(sign_id, self._placeholder)

    def preload_sequence(self, sign_tokens: list[SignToken]) -> None:
        for token in sign_tokens:
            if token.sign_id not in self._cache and token.sign_id != "space":
                logger.debug("Sign '%s' not in cache, will use placeholder", token.sign_id)

    def _load_and_scale(self, filepath: Path) -> pygame.Surface | None:
        try:
            surface = pygame.image.load(str(filepath)).convert_alpha()
            return pygame.transform.smoothscale(surface, (self.size, self.size))
        except pygame.error as e:
            logger.error("Failed to load image %s: %s", filepath, e)
            return None

    def _generate_fallback_placeholder(self) -> pygame.Surface:
        surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        surface.fill((60, 60, 70, 200))
        font = pygame.font.SysFont(None, self.size // 2)
        text = font.render("?", True, (180, 180, 180))
        text_rect = text.get_rect(center=(self.size // 2, self.size // 2))
        surface.blit(text, text_rect)
        return surface
