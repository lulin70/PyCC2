"""
Shell Casing Ejection System for PyCC2 renderer.

Extracted from EnhancedRenderer (God Class refactoring).
Responsible for physics-driven shell casing ejection, simulation, and rendering.

Responsibilities:
- Spawn shell casings at weapon fire position with randomized ejection physics
- Update projectile-like motion (gravity, bounce, lifetime)
- Render shell casings as fading ellipses on the offscreen buffer

State is fully self-contained; only depends on pygame.Surface for blitting
and camera for world-to-screen coordinate transform.
"""

from __future__ import annotations

import logging
import math
import random

import pygame

logger = logging.getLogger(__name__)


class ShellCasingSystem:
    """Physics-driven shell casing ejection and rendering system.

    Each casing is a dict with keys:
        x, y          - world position (float)
        vx, vy        - velocity in px/s (float)
        gravity       - downward acceleration in px/s² (float)
        life          - elapsed lifetime in seconds (float)
        max_life      - total lifetime before removal (float)
        size          - ellipse semi-axes in pixels (float)
        color         - RGB brass/bronze tuple (tuple[int,int,int])
        bounced       - whether ground bounce has occurred (bool)
    """

    def __init__(self) -> None:
        self._shell_casings: list[dict] = []
        self._casing_surf_cache: dict[tuple[int, int], pygame.Surface] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def spawn(self, x: float, y: float, direction_rad: float = 0) -> None:
        """Spawn a shell casing ejected from weapon position.

        Args:
            x: World X coordinate of ejection point.
            y: World Y coordinate of ejection point.
            direction_rad: Firing direction in radians (ejection is perpendicular).
        """
        eject_speed = random.uniform(60, 120)
        eject_angle = direction_rad + math.pi / 2 + random.uniform(-0.3, 0.3)
        vx = math.cos(eject_angle) * eject_speed
        vy = math.sin(eject_angle) * eject_speed - random.uniform(30, 80)  # upward arc
        self._shell_casings.append({
            "x": x, "y": y,
            "vx": vx, "vy": vy,
            "gravity": 400,  # pixels/s^2
            "life": 0.0,
            "max_life": random.uniform(1.5, 3.0),
            "size": random.uniform(2, 4),
            "color": random.choice([(210, 190, 140), (190, 170, 120), (220, 200, 150)]),
            "bounced": False,
        })

    def update(self, dt: float) -> None:
        """Update shell casing physics simulation.

        Args:
            dt: Delta time in seconds since last frame.
        """
        dead_indices: list[int] = []
        for i, c in enumerate(self._shell_casings):
            c["life"] += dt
            if c["life"] > c["max_life"]:
                dead_indices.append(i)
                continue
            c["vy"] += c["gravity"] * dt
            c["x"] += c["vx"] * dt
            c["y"] += c["vy"] * dt
            # Simple ground bounce
            if c["vy"] > 0 and not c["bounced"]:
                c["bounced"] = True
                c["vy"] *= -0.3
                c["vx"] *= 0.6
        for i in reversed(dead_indices):
            self._shell_casings.pop(i)

    def render(self, offscreen: pygame.Surface, camera) -> None:
        """Render shell casings as small ellipses with fade-out.

        Args:
            offscreen: The off-screen rendering surface to draw onto.
            camera: Camera object with x/y position and screen dimensions
                    for world-to-screen coordinate conversion.
        """
        if offscreen is None:
            return
        sw_half = offscreen.get_width() // 2
        sh_half = offscreen.get_height() // 2
        for c in self._shell_casings:
            sx = int(c["x"] - camera.x + sw_half)
            sy = int(c["y"] - camera.y + sh_half)
            fade = max(0, 1.0 - c["life"] / c["max_life"])
            alpha = int(255 * (1.0 - fade * 0.7))
            try:
                sw, sh = int(c["size"] * 2), int(c["size"])
                casing_surf = self._casing_surf_cache.get((sw, sh))
                if casing_surf is None:
                    casing_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                    self._casing_surf_cache[(sw, sh)] = casing_surf
                casing_surf.fill((0, 0, 0, 0))
                pygame.draw.ellipse(casing_surf, (*c["color"], alpha), casing_surf.get_rect())
                offscreen.blit(casing_surf, (sx - int(c["size"]), sy))
            except Exception:
                pass

    @property
    def count(self) -> int:
        """Return the number of active shell casings."""
        return len(self._shell_casings)

    def clear(self) -> None:
        """Remove all active shell casings."""
        self._shell_casings.clear()
