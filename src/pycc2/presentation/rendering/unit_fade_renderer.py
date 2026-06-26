"""Unit death fade-out rendering.

Extracted from EnhancedRenderer to isolate P2-02 death fade ghost rendering
and lifecycle tracking.
"""

from __future__ import annotations

import logging
import time as _time
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.presentation.rendering.camera import Camera

logger = logging.getLogger(__name__)


class UnitFadeRenderer:
    """Renders semi-transparent death fade-out ghosts for dying units."""

    def __init__(self) -> None:
        # {unit_id: {"x": float, "y": float, "start_time": float, "duration": float}}
        self._fading_units: dict[str, dict] = {}

    def start_death_fade(self, unit_id: str, position, duration_ms: int = 500) -> None:
        """Register a unit for death fade-out animation (alpha 255→0)."""
        px = (
            position.x
            if hasattr(position, "x")
            else float(position[0])
            if hasattr(position, "__getitem__")
            else 0.0
        )
        py = (
            position.y
            if hasattr(position, "y")
            else float(position[1])
            if hasattr(position, "__getitem__")
            else 0.0
        )
        self._fading_units[unit_id] = {
            "x": px,
            "y": py,
            "start_time": _time.monotonic(),
            "duration": duration_ms / 1000.0,
            "alpha": 255,
        }

    def render_fading_units(
        self,
        offscreen: pygame.Surface | None,
        camera: Camera,
    ) -> None:
        """Render semi-transparent ghost for each dying unit; remove when fully faded."""
        if offscreen is None:
            return

        now = _time.monotonic()
        dead_ids: list[str] = []
        for uid, state in self._fading_units.items():
            elapsed = now - state["start_time"]
            progress = min(1.0, elapsed / max(0.001, state["duration"]))
            alpha = int(255 * (1.0 - progress))  # linear fade
            if alpha <= 1:
                dead_ids.append(uid)
                continue
            sx = int(state["x"] - camera.x + offscreen.get_width() // 2)
            sy = int(state["y"] - camera.y + offscreen.get_height() // 2)
            size = 12
            color = (60, 55, 50, alpha)  # CC2 dark gray ghost
            try:
                pygame.draw.circle(offscreen, color, (sx, sy), size)
            except (pygame.error, ValueError) as exc:
                logger.debug("Fading unit draw skipped: %s", exc)

        for uid in dead_ids:
            del self._fading_units[uid]

    def clear(self) -> None:
        """Clear all fading units."""
        self._fading_units.clear()
