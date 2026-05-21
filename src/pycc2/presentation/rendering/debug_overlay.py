"""
Debug Overlay System

Multi-level debug visualization overlay for development and testing.
Levels: OFF, BASIC, VERBOSE
"""

from enum import Enum, auto
from typing import Any

import pygame
from pygame import Font, Surface

from pycc2.infra.config import Settings


class DebugLevel(Enum):
    """Debug overlay verbosity levels."""

    OFF = auto()
    BASIC = auto()
    VERBOSE = auto()


class DebugOverlay:
    """Debug overlay manager with multiple detail levels."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._level: DebugLevel = DebugLevel.OFF
        self._font: Font | None = None
        self._debug_info: dict = {}
        self._performance_metrics: dict = {}
        self._ai_decisions: list[dict] = []

    def initialize(self) -> None:
        """Initialize debug overlay resources."""
        pygame.font.init()
        self._font = pygame.font.Font(None, 18)

    def set_level(self, level: DebugLevel) -> None:
        """Set debug overlay level."""
        self._level = level

    def cycle_level(self) -> DebugLevel:
        """Cycle through debug levels."""
        levels = list(DebugLevel)
        current_idx = levels.index(self._level)
        next_idx = (current_idx + 1) % len(levels)
        self._level = levels[next_idx]
        return self._level

    def update_debug_info(self, key: str, value: Any) -> None:
        """Update a debug info entry."""
        self._debug_info[key] = value

    def update_performance(self, metric: str, value: float) -> None:
        """Update performance metric."""
        self._performance_metrics[metric] = value

    def add_ai_decision(self, decision: dict) -> None:
        """Add an AI decision trace entry."""
        if len(self._ai_decisions) > 20:
            self._ai_decisions.pop(0)
        self._ai_decisions.append(decision)

    def render(self, surface: Surface) -> None:
        """Render debug overlay based on current level."""
        if self._level == DebugLevel.OFF or not self._font:
            return

        if self._level.value >= DebugLevel.BASIC.value:
            self._render_basic_info(surface)

        if self._level == DebugLevel.VERBOSE:
            self._render_verbose_info(surface)

    def _render_basic_info(self, surface: Surface) -> None:
        """Render basic debug info (FPS, position, etc.)."""
        y_offset = 35
        lines = [
            f"Debug Mode: {self._level.name}",
            f"FPS: {self._performance_metrics.get('fps', 0):.1f}",
            f"UPS: {self._performance_metrics.get('ups', 0):.1f}",
            f"Frame Time: {self._performance_metrics.get('frame_time_ms', 0):.2f}ms",
        ]

        for key, value in self._debug_info.items():
            lines.append(f"{key}: {value}")

        for line in lines:
            text = self._font.render(line, True, (255, 255, 0))
            shadow = self._font.render(line, True, (0, 0, 0))
            surface.blit(shadow, (12, y_offset + 1))
            surface.blit(text, (10, y_offset))
            y_offset += 18

    def _render_verbose_info(self, surface: Surface) -> None:
        """Render verbose debug info including AI decisions."""
        basic_height = 35 + 5 * 18
        y_offset = basic_height + 10

        title = self._font.render("=== AI Decision Log ===", True, (0, 255, 255))
        surface.blit(title, (10, y_offset))
        y_offset += 22

        for decision in self._ai_decisions[-10:]:
            unit_info = decision.get("unit", "Unknown")
            action = decision.get("action", "None")
            reason = decision.get("reason", "")
            text = f"{unit_info}: {action} - {reason[:30]}"
            rendered = self._font.render(text, True, (200, 255, 200))
            surface.blit(rendered, (10, y_offset))
            y_offset += 16

    def clear_ai_log(self) -> None:
        """Clear AI decision log."""
        self._ai_decisions.clear()

    def clear_all(self) -> None:
        """Clear all debug data."""
        self._debug_info.clear()
        self._performance_metrics.clear()
        self._ai_decisions.clear()

    @property
    def level(self) -> DebugLevel:
        """Get current debug level."""
        return self._level

    def cleanup(self) -> None:
        """Clean up resources."""
        pass
