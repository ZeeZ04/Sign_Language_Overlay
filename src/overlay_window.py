"""Create a transparent, always-on-top window for displaying signs."""

from __future__ import annotations

import logging
import platform
import os

import pygame

logger = logging.getLogger(__name__)

POSITIONS = {
    "top-left": (20, 20),
    "top-right": (-20, 20),  # negative = offset from right/bottom edge
    "bottom-left": (20, -20),
    "bottom-right": (-20, -20),
}


class OverlayWindow:
    def __init__(self, position: str = "bottom-right", size: int = 200, opacity: float = 0.8) -> None:
        self.position = position
        self.size = size
        self.opacity = opacity
        self._running = False
        self._screen: pygame.Surface | None = None
        self._current_surface: pygame.Surface | None = None
        self._bg_color = (30, 30, 40)
        self._window_size = (size + 20, size + 20)  # padding around sign

    def show(self) -> None:
        screen_info = pygame.display.Info()
        screen_w, screen_h = screen_info.current_w, screen_info.current_h

        x, y = self._calculate_position(screen_w, screen_h)
        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x},{y}"

        self._screen = pygame.display.set_mode(
            self._window_size,
            pygame.NOFRAME,
        )
        pygame.display.set_caption("Sign Language Overlay")

        self._set_always_on_top()
        self._running = True
        logger.info("Overlay window shown at position %s (%d, %d)", self.position, x, y)

    def hide(self) -> None:
        self._running = False

    def update(self, surface: pygame.Surface | None) -> None:
        self._current_surface = surface

    def set_position(self, position: str) -> None:
        if position not in POSITIONS:
            raise ValueError(f"Invalid position: {position}. Use one of {list(POSITIONS.keys())}")
        self.position = position

    def render_frame(self) -> None:
        if self._screen is None:
            return

        # Draw background
        bg = pygame.Surface(self._window_size, pygame.SRCALPHA)
        alpha = int(self.opacity * 255)
        bg.fill(self._bg_color + (alpha,))

        # Draw rounded corners effect
        pygame.draw.rect(bg, self._bg_color + (alpha,), bg.get_rect(), border_radius=12)
        self._screen.blit(bg, (0, 0))

        # Draw current sign
        if self._current_surface is not None:
            padding = 10
            self._screen.blit(self._current_surface, (padding, padding))
        else:
            # Show a subtle "waiting" indicator
            font = pygame.font.SysFont(None, 24)
            text = font.render("...", True, (120, 120, 130))
            text_rect = text.get_rect(center=(self._window_size[0] // 2, self._window_size[1] // 2))
            self._screen.blit(text, text_rect)

        pygame.display.flip()

    def stop(self) -> None:
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def _calculate_position(self, screen_w: int, screen_h: int) -> tuple[int, int]:
        offsets = POSITIONS.get(self.position, POSITIONS["bottom-right"])
        ox, oy = offsets

        x = ox if ox >= 0 else screen_w + ox - self._window_size[0]
        y = oy if oy >= 0 else screen_h + oy - self._window_size[1]
        return x, y

    def _set_always_on_top(self) -> None:
        system = platform.system()
        try:
            if system == "Darwin":
                # macOS: use SDL hint
                from ctypes import cdll, c_void_p, c_int
                try:
                    cocoa = cdll.LoadLibrary("/System/Library/Frameworks/Cocoa.framework/Cocoa")
                    logger.debug("macOS: Attempting always-on-top via Cocoa")
                except OSError:
                    logger.debug("macOS: Could not load Cocoa framework, window may not stay on top")
            elif system == "Windows":
                import ctypes
                hwnd = pygame.display.get_wm_info().get("window")
                if hwnd:
                    ctypes.windll.user32.SetWindowPos(
                        hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040
                    )
                    logger.debug("Windows: Set always-on-top via SetWindowPos")
            elif system == "Linux":
                logger.debug("Linux: Always-on-top may require window manager support")
        except Exception as e:
            logger.warning("Could not set always-on-top: %s", e)
