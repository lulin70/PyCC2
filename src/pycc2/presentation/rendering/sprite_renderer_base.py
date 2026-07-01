"""Sprite renderer base — init, constants, properties, render orchestrator.

D11-2 SRP split: extracted from the original sprite_renderer.py monolith.
SpriteRendererBase provides __init__, class constants, backward-compat
properties, the render() orchestrator, spawn_*/update_* methods, and
resize/shutdown. The SpriteRenderer facade inherits this base plus four
focused rendering mixins. Public API 100% backward-compatible.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

import pygame
from pygame import Surface, font

from pycc2.presentation.rendering.animation_system import (
    ParticleEmitter,
    ScreenShake,
    UnitAnimator,
)
from pycc2.presentation.rendering.effect_renderer import EffectRenderer
from pycc2.presentation.rendering.sprite_cache_manager import SpriteCacheManager
from pycc2.presentation.rendering.surface_pool import SurfacePool
from pycc2.presentation.rendering.tile_cache import TileCache

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces.display_config import DisplayConfig
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.presentation.rendering.camera import Camera

# VP numeral pulse animation constants (mirrors ui_overlay_renderer.PULSE_*).
# Module-level to avoid per-instance allocation on the hot render path.
_VP_PULSE_BASE_ALPHA = 200
_VP_PULSE_AMPLITUDE = 55
_VP_PULSE_FREQUENCY = 2.0

__all__ = ["SpriteRendererBase"]


class SpriteRendererBase:
    """Base coordinator for sprite rendering — provides init, constants,
    backward-compat properties, render() orchestrator, spawn_*/update_* methods.

    Inherited by the SpriteRenderer facade along with four focused rendering
    mixins (terrain, vl-flag, unit, unit-overlay). Not instantiated directly.
    """

    TILE_SIZE: int = 48  # CC2 authentic: 48×48 pixel tiles
    SPRITE_SIZE: int = 48  # CC2-style units (matched to 48px tiles)
    MAX_DAMAGE_NUMBERS: int = 50  # Upper limit for floating damage numbers

    def __init__(self, display_config: DisplayConfig | None = None):
        """初始化精灵渲染器及其缓存、表面池与特效渲染器。"""
        from pycc2.domain.interfaces.display_config import DisplayConfig as DC

        self._display_config: DisplayConfig = display_config or DC()
        self.TILE_SIZE: int = 48
        self.SPRITE_SIZE: int = 48
        self._screen: Surface | None = None
        self._target_surface: Surface | None = None
        self._surface_pool = SurfacePool(max_size=30)

        # Delegated components
        self._cache_manager = SpriteCacheManager(display_config)
        self._effect_renderer = EffectRenderer(display_config)

    # ====== Backward-compatible property accessors ======
    # These properties preserve the old API so existing tests and callers
    # continue to work without modification.

    @property
    def _sprite_cache(self) -> dict[str, Surface]:
        return self._cache_manager.sprite_cache

    @property
    def _terrain_cache(self) -> dict[int, Surface]:
        return self._cache_manager.terrain_cache

    @property
    def _tile_cache(self) -> TileCache:
        return self._cache_manager.tile_cache

    @property
    def _asset_loader(self):
        return self._cache_manager.asset_loader

    @property
    def _animation_tick(self) -> int:
        return self._effect_renderer.animation_tick

    @property
    def _effect_particles(self) -> list[dict]:
        return self._effect_renderer.effect_particles

    @property
    def _damage_numbers(self) -> deque[dict]:
        return self._effect_renderer.damage_numbers

    @property
    def _flash_units(self) -> dict[str, int]:
        return self._effect_renderer.flash_units

    @property
    def _death_animations(self) -> dict[str, dict]:
        return self._effect_renderer.death_animations

    @property
    def _unit_animators(self) -> dict[str, UnitAnimator]:
        return self._effect_renderer.unit_animators

    @property
    def _screen_shake(self) -> ScreenShake:
        return self._effect_renderer._screen_shake

    @property
    def _particle_emitter(self) -> ParticleEmitter:
        return self._effect_renderer.particle_emitter

    @property
    def _font_cache(self) -> dict[int, font.Font]:
        return self._effect_renderer._font_cache

    def _get_pooled_surface(self, w: int, h: int) -> pygame.Surface:
        surf = self._surface_pool.get((w, h))
        surf.fill((0, 0, 0, 0))
        return surf

    def initialize(self, screen: Surface) -> None:
        """Initialize."""
        self._screen = screen
        self._cache_manager.initialize_png_sprites()

    @property
    def draw_surface(self) -> Surface | None:
        """获取当前绘制目标surface（优先使用_target_surface）"""
        return self._target_surface or self._screen

    def render(
        self,
        game_map: GameMap,
        units: list[Unit],
        camera: Camera,
        alpha: float = 1.0,
        selected_unit_ids: set[str] | None = None,
        debug_mode: bool = False,
    ) -> None:
        """主渲染方法"""
        if self.draw_surface is None:
            return
        self._effect_renderer.tick()
        self.update_animations()

        # 背景
        bg_color = (52, 73, 94)
        if alpha < 1.0:
            bg = Surface(self.draw_surface.get_size())
            bg.fill(bg_color)
            bg.set_alpha(int(255 * alpha))
            self.draw_surface.blit(bg, (0, 0))
        else:
            self.draw_surface.fill(bg_color)

        self._draw_terrain(game_map, camera)
        self._effect_renderer.render_decals(self.draw_surface, camera)
        if debug_mode:
            self._draw_debug_grid(game_map, camera)
        self._draw_vl_flags(game_map, camera)
        self._draw_units(units, camera, selected_unit_ids)
        self._effect_renderer.render_effects(self.draw_surface, camera)
        self._effect_renderer.render_damage_numbers(self.draw_surface, camera)
        self._effect_renderer.update_effects()

    # ====== 战斗视觉反馈系统 (delegated) ======

    def spawn_hit_flash(self, unit_id: str) -> None:
        """Spawn hit flash."""
        self._effect_renderer.spawn_hit_flash(unit_id)

    def spawn_damage_number(self, position: Vec2, damage: int, is_kill: bool = False) -> None:
        """Spawn damage number."""
        self._effect_renderer.spawn_damage_number(position, damage, is_kill)

    def spawn_muzzle_flash(self, position: Vec2, direction: float) -> None:
        """Spawn muzzle flash."""
        self._effect_renderer.spawn_muzzle_flash(position, direction)

    def spawn_death_effect(self, unit_id: str, position: Vec2) -> None:
        """Spawn death effect."""
        self._effect_renderer.spawn_death_effect(unit_id, position)

    def spawn_explosion(self, position: Vec2, size: str = "medium") -> None:
        """Spawn explosion."""
        self._effect_renderer.spawn_explosion(position, size)

    def clear_decals(self) -> None:
        """Clear persistent ground decals (call on map unload / battle end)."""
        self._effect_renderer.clear_decals()

    def spawn_smoke_screen(self, position: Vec2, radius: float = 64.0) -> None:
        """Spawn smoke screen."""
        self._effect_renderer.spawn_smoke_screen(position, radius)

    def _draw_death_animation(
        self,
        unit: Unit,
        camera: Camera,
        death: dict,
    ) -> None:
        """Delegated to EffectRenderer."""
        surface = self.draw_surface
        if surface is None:
            return
        self._effect_renderer.render_death_animation(
            unit,
            camera,
            death,
            self._cache_manager.sprite_cache,
            self.SPRITE_SIZE,
            surface,
            self._facing_to_direction_index,
        )

    def _draw_effects(self, camera: Camera) -> None:
        """Delegated to EffectRenderer."""
        surface = self.draw_surface
        if surface is None:
            return
        self._effect_renderer.render_effects(surface, camera)

    def _draw_damage_numbers(self, camera: Camera) -> None:
        """Delegated to EffectRenderer."""
        surface = self.draw_surface
        if surface is None:
            return
        self._effect_renderer.render_damage_numbers(surface, camera)

    def _update_effects(self) -> None:
        """Delegated to EffectRenderer."""
        self._effect_renderer.update_effects()

    def ensure_animator(self, unit_id: str) -> UnitAnimator:
        """Ensure animator."""
        return self._effect_renderer.ensure_animator(unit_id)

    def _get_font(self, size: int) -> font.Font | None:
        return self._effect_renderer.get_font(size)

    def update_animations(self) -> None:
        """Update animations."""
        self._effect_renderer.update_animations()

    def update_flash(self, dt: float) -> None:
        """Update flash."""
        self._effect_renderer.update_effects()

    def update_weather(self, dt: float) -> None:
        """Update weather."""
        pass  # Weather rendering handled by dedicated weather renderer

    def update_shell_casings(self, dt: float) -> None:
        """Update shell casings."""
        pass  # Shell casings handled by dedicated shell casing system

    def update_suppression_overlay(self, dt: float, units) -> None:
        """Update suppression overlay."""
        pass  # Suppression overlay handled by dedicated overlay system

    def _smooth_positions(self, units, dt: float) -> None:
        pass  # Position smoothing handled by movement system

    def resize(self, w: int, h: int) -> None:
        """Handle window resize — invalidate viewport-dependent caches only."""
        self._surface_pool.clear()
        self._cache_manager.terrain_cache.clear()
        self._cache_manager.tile_cache.invalidate()

    def shutdown(self) -> None:
        """Shut down the sprite renderer and release caches."""
        self._screen = None
        self._cache_manager.clear()
        self._effect_renderer.clear()
        self._surface_pool.clear()

    if TYPE_CHECKING:
        # -- Cross-mixin methods provided by rendering mixins --
        # Declared as TYPE_CHECKING-only stubs so mypy can verify the render()
        # orchestrator and _draw_death_animation callback without runtime
        # shadowing (base is last in MRO; real methods come from mixins).
        def _draw_terrain(self, game_map: GameMap, camera: Camera) -> None: ...
        def _draw_debug_grid(self, game_map: GameMap, camera: Camera) -> None: ...
        def _draw_vl_flags(self, game_map: GameMap, camera: Camera) -> None: ...
        def _draw_units(
            self,
            units: list[Unit],
            camera: Camera,
            selected_ids: set[str] | None = None,
            position_overrides: dict[str, tuple[float, float]] | None = None,
        ) -> None: ...
        def _facing_to_direction_index(self, rad: float) -> int: ...
