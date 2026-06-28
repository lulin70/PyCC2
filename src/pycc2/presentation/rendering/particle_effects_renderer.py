"""Particle Effects Renderer for PyCC2 - Extracted from EnhancedRenderer

Handles all combat visual effects and particle systems:
- Damage VFX (smoke, fire for damaged units)
- Hit flash effects
- Damage number floating text
- Muzzle flash (both SpriteRenderer and ParticleSystem versions)
- Death animations
- Explosions (both versions)
- Smoke screens
- Particle system lifecycle management

This module was extracted from EnhancedRenderer following SRP (Single Responsibility Principle).
All method signatures remain unchanged for backward compatibility.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.particle_system import TopDownParticleSystem

logger = logging.getLogger(__name__)


class ParticleEffectsRenderer:
    """Manages all particle-based visual effects and combat feedback.

    Delegated by EnhancedRenderer to maintain clean separation of concerns.
    Requires references to:
    - SpriteRenderer: For PNG-based combat effects
    - TopDownParticleSystem: For procedural particle effects
    - Surface pool: From coordinator for performance optimization
    """

    def __init__(self):
        """Initialize the ParticleEffectsRenderer."""
        self._sprite_renderer = None  # Set via set_sprite_renderer()
        self._particle_system = None  # Set via set_particle_system()
        self._offscreen = None  # Set via set_offscreen()
        self._get_pooled_surface = None  # Set via set_surface_pool_fn()

    def set_dependencies(
        self,
        sprite_renderer=None,
        particle_system: TopDownParticleSystem | None = None,
        offscreen=None,
        surface_pool_fn=None,
    ) -> None:
        """Inject dependencies from coordinator."""
        self._sprite_renderer = sprite_renderer
        self._particle_system = particle_system
        self._offscreen = offscreen
        self._get_pooled_surface = surface_pool_fn

    def _draw_damage_vfx(self, unit: Unit, cx: int, cy: int) -> None:
        """STEP A-2: Render damage visual effects (smoke/fire) for damaged units.

        Based on unit.damage_state:
        - undamaged: No effects
        - light: Light gray smoke wisps (2-3 particles)
        - moderate: Thicker smoke (4-5 particles)
        - heavy: Thick smoke + orange fire glow (6+ particles)
        - destroyed: Intense fire + thick black smoke
        """
        if not hasattr(unit, "damage_state"):
            return

        state = unit.damage_state
        if state == "undamaged":
            return

        # Ensure VFX particles are generated
        if hasattr(unit, "update_damage_vfx"):
            if not getattr(unit, "_smoke_particles", None):
                unit.update_damage_vfx()

        # Draw smoke particles
        smoke_particles = getattr(unit, "_smoke_particles", [])
        for particle in smoke_particles[:8]:  # Limit to 8 for performance
            px = cx + particle.get("x", 0)
            py = cy + particle.get("y", 0)
            alpha = particle.get("alpha", 100)
            size = particle.get("size", 3)

            # Smoke color: gray with transparency
            smoke_color = (120, 120, 120)

            # Create temporary surface for alpha blending (pooled - PERF-001)
            if self._get_pooled_surface and self._offscreen:
                smoke_surf = self._get_pooled_surface((size * 2, size * 2))
                pygame.draw.circle(smoke_surf, (*smoke_color, alpha), (size, size), size)
                self._offscreen.blit(smoke_surf, (px - size, py - size))

        # Draw fire particles (for heavy/destroyed)
        fire_particles = getattr(unit, "_fire_particles", [])
        for particle in fire_particles[:6]:  # Limit to 6 for performance
            px = cx + particle.get("x", 0)
            py = cy + particle.get("y", 0)
            color = particle.get("color", (220, 120, 20))
            size = particle.get("size", 3)

            # Fire glow effect (pooled - PERF-001)
            if self._get_pooled_surface and self._offscreen:
                glow_size = size + 2
                glow_surf = self._get_pooled_surface((glow_size * 2, glow_size * 2))
                pygame.draw.circle(glow_surf, (*color, 80), (glow_size, glow_size), glow_size)
                self._offscreen.blit(glow_surf, (px - glow_size, py - glow_size))

                # Fire core (pooled - PERF-001)
                bright_color = tuple(min(255, c + 40) for c in color)
                core_surf = self._get_pooled_surface((size * 2, size * 2))
                pygame.draw.circle(core_surf, (*bright_color, 200), (size, size), size // 2 + 1)
                self._offscreen.blit(core_surf, (px - size, py - size))

    def spawn_hit_flash(self, unit_id: str) -> None:
        """Spawn hit flash effect when unit takes damage."""
        if self._sprite_renderer:
            self._sprite_renderer.spawn_hit_flash(unit_id)

    def spawn_damage_number(self, position, damage: int, is_kill: bool = False) -> None:
        """Spawn floating damage number at position."""
        if self._sprite_renderer:
            self._sprite_renderer.spawn_damage_number(position, damage, is_kill)

    def spawn_muzzle_flash(self, position, direction: float) -> None:
        """Spawn muzzle flash effect (SpriteRenderer version).

        CC2 Authentic: White dot flash + short line along fire direction
        """
        if self._sprite_renderer:
            self._sprite_renderer.spawn_muzzle_flash(position, direction)

    def spawn_death_effect(self, unit_id: str, position) -> None:
        """Spawn death animation effect when unit is destroyed."""
        if self._sprite_renderer:
            self._sprite_renderer.spawn_death_effect(unit_id, position)

    def spawn_explosion_sprite(self, position, size: str = "medium") -> None:
        """Spawn explosion effect using SpriteRenderer (PNG-based)."""
        if self._sprite_renderer:
            self._sprite_renderer.spawn_explosion(position, size)

    def spawn_smoke_screen(self, position, radius: float = 64.0) -> None:
        """Spawn smoke screen effect at position."""
        if self._sprite_renderer:
            self._sprite_renderer.spawn_smoke_screen(position, radius)

    def update_particles(self, dt_ms: int) -> None:
        """Update all particle effects - call from game loop.

        Args:
            dt_ms: Delta time in milliseconds since last frame

        """
        if self._particle_system:
            self._particle_system.update(dt_ms)

    def spawn_explosion_ring(
        self, position, max_radius=40, duration_ms=500, color=(255, 200, 50)
    ) -> None:
        """Spawn explosion ring effect at position.

        CC2 Authentic: Yellow/orange circular expanding ring (not 3D fireball)
        Automatically triggers dynamic light effect.

        Args:
            position: (x, y) world coordinates or Vec2
            max_radius: Maximum ring radius in pixels (default 40)
            duration_ms: Animation duration (default 500ms)
            color: Base color tuple (default yellow-orange)

        """
        if self._particle_system:
            x = position[0] if hasattr(position, "__getitem__") else position.x
            y = position[1] if hasattr(position, "__getitem__") else position.y

            self._particle_system.spawn_explosion_ring(x, y, max_radius, duration_ms, color)

    def spawn_muzzle_flash_particle(self, position, direction) -> None:
        """Spawn muzzle flash effect (ParticleSystem version).

        CC2 Authentic: White dot flash + short line along fire direction
        """
        if self._particle_system:
            x = position[0] if hasattr(position, "__getitem__") else position.x
            y = position[1] if hasattr(position, "__getitem__") else position.y

            self._particle_system.spawn_muzzle_flash(x, y, direction)

    def particle_count(self) -> int:
        """Get current active particle count for performance monitoring."""
        if self._particle_system:
            return self._particle_system.active_count
        return 0

    def spawn_dirt_splash(self, x: float, y: float, count: int = 12) -> None:
        """Spawn dirt splash particles at position (delegates to TopDownParticleSystem)."""
        if self._particle_system:
            self._particle_system.spawn_dirt_splash(x, y, count)

    def spawn_blood_pool(self, x: float, y: float, size: int = 8) -> None:
        """Spawn persistent blood pool stain at position (delegates to TopDownParticleSystem)."""
        if self._particle_system:
            self._particle_system.spawn_blood_pool(x, y, size)

    def spawn_hit_marker(self, x: float, y: float, damage_type: str = "normal") -> None:
        """Spawn hit marker visual feedback at position (delegates to TopDownParticleSystem).

        Args:
            damage_type: 'normal', 'critical', 'armor_penetrate', or 'ricochet'

        """
        if self._particle_system:
            self._particle_system.spawn_hit_marker(x, y, damage_type)
