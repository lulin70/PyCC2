"""Combat effects coordinator - high-level combat visual effect orchestration.

Extracted from EnhancedRenderer to keep the coordinator focused on public API
delegation. Composes low-level particle/sprite effects with dynamic lighting
and unit fade-out rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.presentation.rendering.environment_renderer import EnvironmentRenderer
    from pycc2.presentation.rendering.particle_effects_renderer import ParticleEffectsRenderer
    from pycc2.presentation.rendering.unit_fade_renderer import UnitFadeRenderer


class CombatEffectsCoordinator:
    """Coordinates combat visual effects across particle, lighting, and fade systems."""

    def __init__(
        self,
        particle_effects: ParticleEffectsRenderer,
        unit_fade_renderer: UnitFadeRenderer,
        environment_renderer: EnvironmentRenderer,
    ) -> None:
        self._particle_effects = particle_effects
        self._unit_fade_renderer = unit_fade_renderer
        self._environment_renderer = environment_renderer

    def spawn_hit_flash(self, unit_id: str) -> None:
        """Spawn hit flash effect when unit takes damage."""
        self._particle_effects.spawn_hit_flash(unit_id)

    def spawn_damage_number(self, position, damage: int, is_kill: bool = False) -> None:
        """Spawn floating damage number at position."""
        self._particle_effects.spawn_damage_number(position, damage, is_kill)

    def spawn_death_effect(self, unit_id: str, position) -> None:
        """Spawn death animation effect and start fade-out ghost."""
        self._particle_effects.spawn_death_effect(unit_id, position)
        self._unit_fade_renderer.start_death_fade(unit_id, position, duration_ms=500)

    def spawn_smoke_screen(self, position, radius: float = 64.0) -> None:
        """Spawn smoke screen effect at position."""
        self._particle_effects.spawn_smoke_screen(position, radius)

    def spawn_dirt_splash(self, x: float, y: float, count: int = 8) -> None:
        """Spawn dirt splash particles on hit."""
        self._particle_effects.spawn_dirt_splash(x, y, count)

    def spawn_blood_pool(self, x: float, y: float, size: int = 10) -> None:
        """Spawn persistent blood pool stain."""
        self._particle_effects.spawn_blood_pool(x, y, size)

    def spawn_hit_marker(self, x: float, y: float, damage_type: str = "normal") -> None:
        """Spawn hit marker visual feedback."""
        self._particle_effects.spawn_hit_marker(x, y, damage_type)

    def update_particles(self, dt_ms: int) -> None:
        """Update all particle effects."""
        self._particle_effects.update_particles(dt_ms)

    def spawn_explosion(
        self, position, max_radius=40, duration_ms=500, color=(255, 200, 50)
    ) -> None:
        """Spawn explosion ring effect and dynamic light."""
        self._particle_effects.spawn_explosion_ring(position, max_radius, duration_ms, color)
        self._environment_renderer.spawn_dynamic_light(
            position, radius=60, intensity=1.5, color=(255, 200, 100), duration_ms=duration_ms
        )

    def spawn_muzzle_flash(self, position, direction) -> None:
        """Spawn muzzle flash effect."""
        self._particle_effects.spawn_muzzle_flash_particle(position, direction)

    def particle_count(self) -> int:
        """Return current active particle count."""
        return self._particle_effects.particle_count()
