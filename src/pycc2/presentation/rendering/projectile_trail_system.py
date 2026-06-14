"""
Projectile Trail System - Visualizes bullet and shell trajectories.

Renders animated projectile trails for:
- Small arms fire (thin, fast, short trail)
- Machine gun bursts (multiple thin trails)
- Tank/AP gun shells (thick, bright, long trail)
- Mortar/artillery arcs (curved trajectory with smoke)
- AT rocket trails (bright flame trail)

Integrates with existing ParticleSystem and AnimationSystem.
"""

import math
import random
from typing import List

import pygame


class ProjectileTrail:
    """A single projectile trail with position, velocity, and visual properties."""

    _surface_cache: dict[int, pygame.Surface] = {}

    def __init__(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        trail_type: str = "bullet",
        duration: float = 0.3,
    ):
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.trail_type = trail_type
        self.duration = duration
        self.elapsed = 0.0
        self._particles: List[dict] = []

        self._init_particles()

    def _init_particles(self) -> None:
        """Create trail particles based on type."""
        if self.trail_type == "bullet":
            count = 5
            for i in range(count):
                t = i / count
                self._particles.append({
                    "x": self.start_x + (self.end_x - self.start_x) * t,
                    "y": self.start_y + (self.end_y - self.start_y) * t,
                    "alpha": int(255 * (1 - t * 0.7)),
                    "size": max(1, 3 - int(t * 2)),
                })
        elif self.trail_type == "shell":
            count = 8
            for i in range(count):
                t = i / count
                self._particles.append({
                    "x": self.start_x + (self.end_x - self.start_x) * t,
                    "y": self.start_y + (self.end_y - self.start_y) * t,
                    "alpha": int(255 * (1 - t * 0.5)),
                    "size": max(2, 5 - int(t * 3)),
                })
        elif self.trail_type == "rocket":
            count = 12
            for i in range(count):
                t = i / count
                spread = random.uniform(-3, 3)
                self._particles.append({
                    "x": self.start_x + (self.end_x - self.start_x) * t + spread,
                    "y": self.start_y + (self.end_y - self.start_y) * t + spread,
                    "alpha": int(255 * (1 - t * 0.4)),
                    "size": max(2, 6 - int(t * 3)),
                })
        elif self.trail_type == "mortar":
            count = 15
            arc_height = abs(self.end_x - self.start_x) * 0.3
            for i in range(count):
                t = i / count
                arc_y = -arc_height * math.sin(t * math.pi)
                self._particles.append({
                    "x": self.start_x + (self.end_x - self.start_x) * t,
                    "y": self.start_y + (self.end_y - self.start_y) * t + arc_y,
                    "alpha": int(200 * (1 - t * 0.5)),
                    "size": max(2, 4 - int(t * 2)),
                })

    def update(self, dt: float) -> bool:
        """Update trail. Returns True if still active."""
        self.elapsed += dt
        return self.elapsed < self.duration

    def render(self, surface: pygame.Surface) -> None:
        """Render trail particles to surface."""
        fade = max(0.0, 1.0 - (self.elapsed / self.duration))

        for p in self._particles:
            alpha = int(p["alpha"] * fade)
            if alpha <= 0:
                continue
            size = p["size"]
            x, y = int(p["x"]), int(p["y"])

            if self.trail_type == "bullet":
                color = (255, 255, 200, alpha)
            elif self.trail_type == "shell":
                color = (255, 200, 100, alpha)
            elif self.trail_type == "rocket":
                color = (255, 150, 50, alpha)
            elif self.trail_type == "mortar":
                color = (200, 200, 200, alpha)
            else:
                color = (255, 255, 255, alpha)

            if size <= 1:
                try:
                    surface.set_at((x, y), color[:3])
                except (IndexError, TypeError):
                    pass
            else:
                diameter = size * 2
                trail_surf = ProjectileTrail._surface_cache.get(diameter)
                if trail_surf is None:
                    trail_surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
                    ProjectileTrail._surface_cache[diameter] = trail_surf
                trail_surf.fill((0, 0, 0, 0))
                pygame.draw.circle(trail_surf, color, (size, size), size)
                surface.blit(trail_surf, (x - size, y - size))


class ProjectileTrailSystem:
    """Manages all active projectile trails."""

    def __init__(self, max_trails: int = 50):
        self._trails: List[ProjectileTrail] = []
        self._max_trails = max_trails

    def add_trail(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        trail_type: str = "bullet",
        duration: float = 0.3,
    ) -> None:
        """Add a new projectile trail."""
        if len(self._trails) >= self._max_trails:
            self._trails.pop(0)
        self._trails.append(
            ProjectileTrail(start_x, start_y, end_x, end_y, trail_type, duration)
        )

    def add_bullet_trail(self, sx: float, sy: float, ex: float, ey: float) -> None:
        self.add_trail(sx, sy, ex, ey, "bullet", duration=0.15)

    def add_shell_trail(self, sx: float, sy: float, ex: float, ey: float) -> None:
        self.add_trail(sx, sy, ex, ey, "shell", duration=0.25)

    def add_rocket_trail(self, sx: float, sy: float, ex: float, ey: float) -> None:
        self.add_trail(sx, sy, ex, ey, "rocket", duration=0.4)

    def add_mortar_trail(self, sx: float, sy: float, ex: float, ey: float) -> None:
        self.add_trail(sx, sy, ex, ey, "mortar", duration=0.5)

    def update(self, dt: float) -> None:
        """Update all trails, removing expired ones."""
        self._trails = [t for t in self._trails if t.update(dt)]

    def render(self, surface: pygame.Surface) -> None:
        """Render all active trails."""
        for trail in self._trails:
            trail.render(surface)

    def clear(self) -> None:
        self._trails.clear()

    def count(self) -> int:
        return len(self._trails)
