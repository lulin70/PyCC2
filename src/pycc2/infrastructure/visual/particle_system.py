"""Particle System - Visual effects for explosions, construction, and impacts.

Provides:
- Explosion particles (small/large)
- Building construction sparkles
- Impact debris particles
- Resource collection sparkles

All particles use pygame drawing primitives for performance.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pygame


class ParticleType(Enum):
    """Types of particle effects."""

    EXPLOSION_SMALL = auto()
    EXPLOSION_LARGE = auto()
    BUILDING_CONSTRUCT = auto()
    IMPACT_HIT = auto()
    RESOURCE_COLLECT = auto()


@dataclass
class Particle:
    """Individual particle in an effect."""

    x: float
    y: float
    vx: float  # Velocity X
    vy: float  # Velocity Y
    life: float  # Remaining lifetime (seconds)
    max_life: float  # Initial lifetime
    color: tuple[int, int, int]
    size: float

    def update(self, dt: float) -> bool:
        """Update particle position and lifetime.

        Args:
            dt: Delta time in seconds

        Returns:
            True if particle is still alive, False if dead
        """
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 200 * dt  # Gravity
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, camera_offset: tuple[int, int] = (0, 0)) -> None:
        """Draw particle to surface.

        Args:
            surface: Pygame surface to draw on
            camera_offset: Camera offset (x, y)
        """
        alpha = self.life / self.max_life
        size = int(self.size * alpha)
        if size < 1:
            return

        screen_x = int(self.x - camera_offset[0])
        screen_y = int(self.y - camera_offset[1])

        # Fade color based on lifetime
        color = tuple(int(c * alpha) for c in self.color)
        pygame.draw.circle(surface, color, (screen_x, screen_y), size)


class ParticleEffect:
    """Collection of particles forming a visual effect."""

    def __init__(self, x: float, y: float, effect_type: ParticleType) -> None:
        """Initialize particle effect.

        Args:
            x: World X position
            y: World Y position
            effect_type: Type of effect to create
        """
        self.x = x
        self.y = y
        self.particles: list[Particle] = []
        self._spawn_particles(effect_type)

    def _spawn_particles(self, effect_type: ParticleType) -> None:
        """Spawn particles based on effect type."""
        if effect_type == ParticleType.EXPLOSION_SMALL:
            self._spawn_explosion(count=20, speed=150, color=(255, 128, 0), size=4)
        elif effect_type == ParticleType.EXPLOSION_LARGE:
            self._spawn_explosion(count=50, speed=250, color=(255, 100, 0), size=6)
        elif effect_type == ParticleType.BUILDING_CONSTRUCT:
            self._spawn_sparkles(count=15, color=(255, 255, 100), size=3)
        elif effect_type == ParticleType.IMPACT_HIT:
            self._spawn_impact(count=10, color=(200, 200, 200), size=2)
        elif effect_type == ParticleType.RESOURCE_COLLECT:
            self._spawn_sparkles(count=12, color=(255, 215, 0), size=4)

    def _spawn_explosion(self, count: int, speed: float, color: tuple[int, int, int], size: float) -> None:
        """Spawn explosion particles radiating outward."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            velocity = random.uniform(speed * 0.5, speed * 1.5)
            self.particles.append(
                Particle(
                    x=self.x,
                    y=self.y,
                    vx=velocity * math.cos(angle),
                    vy=velocity * math.sin(angle) - 100,  # Upward bias
                    life=random.uniform(0.3, 0.8),
                    max_life=0.8,
                    color=color,
                    size=size,
                )
            )

    def _spawn_sparkles(self, count: int, color: tuple[int, int, int], size: float) -> None:
        """Spawn upward-floating sparkle particles."""
        for _ in range(count):
            angle = random.uniform(-math.pi / 6, math.pi / 6)  # Mostly upward
            speed = random.uniform(50, 150)
            self.particles.append(
                Particle(
                    x=self.x + random.uniform(-10, 10),
                    y=self.y,
                    vx=speed * math.sin(angle),
                    vy=-abs(speed * math.cos(angle)),  # Always upward
                    life=random.uniform(0.5, 1.2),
                    max_life=1.2,
                    color=color,
                    size=size,
                )
            )

    def _spawn_impact(self, count: int, color: tuple[int, int, int], size: float) -> None:
        """Spawn debris particles for impact."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(80, 180)
            self.particles.append(
                Particle(
                    x=self.x,
                    y=self.y,
                    vx=speed * math.cos(angle),
                    vy=speed * math.sin(angle) - 50,
                    life=random.uniform(0.2, 0.5),
                    max_life=0.5,
                    color=color,
                    size=size,
                )
            )

    def update(self, dt: float) -> bool:
        """Update all particles.

        Args:
            dt: Delta time in seconds

        Returns:
            True if effect still has live particles, False if done
        """
        self.particles = [p for p in self.particles if p.update(dt)]
        return len(self.particles) > 0

    def draw(self, surface: pygame.Surface, camera_offset: tuple[int, int] = (0, 0)) -> None:
        """Draw all particles.

        Args:
            surface: Pygame surface to draw on
            camera_offset: Camera offset (x, y)
        """
        for particle in self.particles:
            particle.draw(surface, camera_offset)


class ParticleSystem:
    """Manages all active particle effects in the game."""

    def __init__(self) -> None:
        """Initialize particle system."""
        self.effects: list[ParticleEffect] = []

    def spawn_effect(self, x: float, y: float, effect_type: ParticleType) -> None:
        """Spawn a new particle effect.

        Args:
            x: World X position
            y: World Y position
            effect_type: Type of effect to spawn
        """
        effect = ParticleEffect(x, y, effect_type)
        self.effects.append(effect)

    def update(self, dt: float) -> None:
        """Update all particle effects.

        Args:
            dt: Delta time in seconds
        """
        self.effects = [e for e in self.effects if e.update(dt)]

    def draw(self, surface: pygame.Surface, camera_offset: tuple[int, int] = (0, 0)) -> None:
        """Draw all particle effects.

        Args:
            surface: Pygame surface to draw on
            camera_offset: Camera offset (x, y)
        """
        for effect in self.effects:
            effect.draw(surface, camera_offset)

    def clear(self) -> None:
        """Clear all effects."""
        self.effects.clear()
