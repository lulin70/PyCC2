"""Unit rendering mixin — extracted from sprite_renderer.py (D11-2 SRP split).

Contains unit-sprite rendering methods used by the SpriteRenderer facade:
  - _draw_units: depth-sort units and dispatch alive/dead rendering paths
  - _draw_sprite_unit: draw a single unit sprite with overlays/indicators
  - _facing_to_direction_index: convert facing radians to 8-direction index
  - _draw_turret_overlay: draw rotating tank turret overlay

This is a mixin — do not instantiate directly. The SpriteRenderer facade
inherits this mixin and provides all required attributes via SpriteRendererBase.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on. Cross-mixin method stubs (provided by
UnitOverlayRenderingMixin / SpriteRendererBase) are declared for typing only.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import pygame
from pygame import Surface, draw, transform

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.effect_renderer import EffectRenderer
    from pycc2.presentation.rendering.sprite_cache_manager import SpriteCacheManager

logger = logging.getLogger(__name__)

__all__ = ["UnitRenderingMixin"]


class UnitRenderingMixin:
    """Unit sprite rendering methods. Inherited by the SpriteRenderer facade,
    not instantiated.
    """

    # -- Facade attributes used by unit methods (no defaults; set by SpriteRendererBase) --
    SPRITE_SIZE: int
    draw_surface: Surface | None
    _cache_manager: SpriteCacheManager
    _effect_renderer: EffectRenderer

    if TYPE_CHECKING:
        # -- Cross-mixin method stubs (provided by SpriteRendererBase / UnitOverlayRenderingMixin).
        # Declared for typing only so they do not shadow the real implementations at runtime (MRO). --
        def _get_pooled_surface(self, w: int, h: int) -> pygame.Surface: ...
        def _draw_selection_outline(self, sprite: Surface, draw_pos: tuple[int, int]) -> None: ...
        def _draw_selection_ring(self, center: tuple[float, float], radius: int) -> None: ...
        def _draw_faction_flag(self, unit: Unit, sp: tuple[float, float], zoom: float) -> None: ...
        def _draw_unit_label(self, unit: Unit, sp: tuple[float, float], zoom: float) -> None: ...
        def _draw_health_bar(self, unit: Unit, sp: tuple[float, float], zoom: float) -> None: ...
        def _draw_enhanced_morale_indicator(
            self, unit: Unit, sp: tuple[float, float], zoom: float
        ) -> None: ...
        def _draw_movement_mode_indicator(
            self, unit: Unit, sp: tuple[float, float], zoom: float
        ) -> None: ...

    def _draw_units(
        self,
        units: list[Unit],
        camera: Camera,
        selected_ids: set[str] | None = None,
        position_overrides: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        """使用精灵绘制单位"""
        surface = self.draw_surface
        if surface is None:
            return

        sorted_units = sorted(units, key=lambda u: u.position.pixel_position.y)

        for unit in sorted_units:
            if not unit.is_alive:
                death = self._effect_renderer.death_animations.get(unit.id)
                if death:
                    self._effect_renderer.render_death_animation(
                        unit,
                        camera,
                        death,
                        self._cache_manager.sprite_cache,
                        self.SPRITE_SIZE,
                        surface,
                        self._facing_to_direction_index,
                    )
                continue

            is_selected = unit.id in (selected_ids or set())
            self._draw_sprite_unit(unit, camera, is_selected, position_overrides=position_overrides)

    def _draw_sprite_unit(
        self,
        unit: Unit,
        camera: Camera,
        is_selected: bool,
        position_overrides: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        surface = self.draw_surface
        if surface is None:
            return

        pos = unit.position.pixel_position
        if position_overrides and hasattr(unit, "id") and unit.id in position_overrides:
            ox, oy = position_overrides[unit.id]
            from pycc2.domain.value_objects.vec2 import Vec2

            pos = Vec2(ox, oy)
        sp = camera.world_to_screen(pos)

        dir_idx = self._facing_to_direction_index(unit.position.facing_rad)

        faction = unit.faction.name.lower()
        utype = unit.unit_type.name

        movement_mode = getattr(unit, "movement_mode", "normal")
        sprite_state = "idle"
        if movement_mode in ("sneak", "hide", "defend"):
            sprite_state = movement_mode

        prone_states = {"sneak", "hide", "defend"}
        is_prone = sprite_state in prone_states and "TANK" not in utype

        sprite: Surface | None
        if is_prone:
            sprite = self._cache_manager.create_unit_sprite(
                faction, utype, dir_idx, state=sprite_state
            )
        else:
            sprite = self._cache_manager.get_unit_sprite(faction, utype, dir_idx, self.SPRITE_SIZE)

        if sprite is None:
            r = int(12 * camera.zoom)
            in_building = unit.current_building_pos is not None
            if "TANK" in utype or "VEHICLE" in utype:
                color = (80, 80, 80)
                if in_building:
                    s = self._get_pooled_surface(r * 2, r * 2)
                    s.fill((*color, 160))
                    surface.blit(s, (int(sp[0]) - r, int(sp[1]) - r))
                else:
                    draw.rect(surface, color, (int(sp[0]) - r, int(sp[1]) - r, r * 2, r * 2))
            elif "SNIPER" in utype:
                color = (100, 200, 100)
                points = [
                    (int(sp[0]), int(sp[1]) - r),
                    (int(sp[0]) - r, int(sp[1]) + r),
                    (int(sp[0]) + r, int(sp[1]) + r),
                ]
                if in_building:
                    s = self._get_pooled_surface(r * 2 + 2, r * 2 + 2)
                    local_pts = [
                        (p[0] - int(sp[0]) + r + 1, p[1] - int(sp[1]) + r + 1) for p in points
                    ]
                    draw.polygon(s, (*color, 160), local_pts)
                    surface.blit(s, (int(sp[0]) - r - 1, int(sp[1]) - r - 1))
                else:
                    draw.polygon(surface, color, points)
            else:
                color = (74, 144, 217) if faction == "allies" else (217, 74, 74)
                if in_building:
                    s = self._get_pooled_surface(r * 2 + 2, r * 2 + 2)
                    draw.circle(s, (*color, 160), (r + 1, r + 1), r)
                    surface.blit(s, (int(sp[0]) - r - 1, int(sp[1]) - r - 1))
                else:
                    draw.circle(surface, color, (int(sp[0]), int(sp[1])), r)
            if in_building:
                icon_size = max(6, int(8 * camera.zoom))
                ix = int(sp[0]) - icon_size // 2
                iy = int(sp[1]) - r - icon_size - 2
                draw.rect(
                    surface,
                    (160, 140, 120),
                    (ix, iy + icon_size // 2, icon_size, icon_size // 2),
                )
                draw.polygon(
                    surface,
                    (120, 90, 60),
                    [
                        (ix - 1, iy + icon_size // 2),
                        (ix + icon_size // 2, iy),
                        (ix + icon_size + 1, iy + icon_size // 2),
                    ],
                )
            return

        zoom = camera.zoom
        sz = int(self.SPRITE_SIZE * zoom)
        if sz > 0:
            scaled = transform.scale(sprite, (sz, sz))
            offset = sz // 2

            animators = self._effect_renderer.unit_animators
            if unit.id not in animators:
                self._effect_renderer.ensure_animator(unit.id)

            animator = animators.get(unit.id)
            if animator:
                st = animator.state
                draw_pos = (
                    int(sp[0]) - offset + int(st.offset_x * zoom),
                    int(sp[1]) - offset + int(st.offset_y * zoom),
                )
                final_w = int(scaled.get_width() * st.scale_x)
                final_h = int(scaled.get_height() * st.scale_y)
                if final_w > 0 and final_h > 0:
                    scaled = transform.scale(scaled, (final_w, final_h))
                if st.alpha < 255:
                    scaled.set_alpha(st.alpha)
                if st.color_mod:
                    tinted = scaled.copy()
                    tinted.fill((*st.color_mod, 0), special_flags=pygame.BLEND_RGB_ADD)
                    scaled = tinted
            else:
                draw_pos = (int(sp[0]) - offset, int(sp[1]) - offset)

            if unit.current_building_pos is not None:
                scaled.set_alpha(160)

            hp_ratio = unit.health.hp_ratio
            if hp_ratio < 0.5:
                try:
                    from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D

                    scaled = PixelArtist3D.apply_wounded_overlay(scaled, hp_ratio)
                except (pygame.error, ValueError, TypeError) as e:
                    logging.debug("Wounded overlay failed: %s", e)

            surface.blit(scaled, draw_pos)

            if "TANK" in utype:
                self._draw_turret_overlay(unit, sp, zoom, faction)

        if is_selected:
            if sz > 0 and sprite is not None:
                self._draw_selection_outline(scaled, draw_pos)
            self._draw_selection_ring(sp, int(16 * zoom))

        self._draw_faction_flag(unit, sp, zoom)
        self._draw_unit_label(unit, sp, zoom)
        self._draw_health_bar(unit, sp, zoom)

        self._draw_enhanced_morale_indicator(unit, sp, zoom)
        self._draw_movement_mode_indicator(unit, sp, zoom)

        self._effect_renderer.render_hit_flash(unit.id, sp, sz, surface)

    def _facing_to_direction_index(self, rad: float) -> int:
        """将弧度转为8方向索引 (N=0, 顺时针: NE=1, E=2, SE=3, S=4, SW=5, W=6, NW=7)"""
        deg = math.degrees(rad) % 360
        if deg < 0:
            deg += 360
        idx = round((90 - deg) / 45) % 8
        return idx

    def _draw_turret_overlay(self, unit, sp, zoom, faction):
        """绘制独立旋转的坦克炮塔覆盖层"""
        surface = self.draw_surface
        if surface is None:
            return
        try:
            from pycc2.domain.entities.unit import Faction
            from pycc2.domain.value_objects.direction import Direction
            from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D
            from pycc2.presentation.rendering.pixel_artist_enums import TankType

            fac_enum = Faction.ALLIES if faction in ("allies", "polish") else Faction.AXIS
            tank_type = (
                TankType.SHERMAN_M4 if fac_enum == Faction.ALLIES else TankType.PANTHER_AUSFG
            )

            turret_base = PixelArtist3D.create_turret_overlay(
                faction=fac_enum,
                turret_direction=Direction.EAST,
                tank_type=tank_type,
            )

            sz = int(self.SPRITE_SIZE * zoom)
            if sz <= 0:
                return
            turret_scaled = transform.scale(turret_base, (sz, sz))

            facing_rad = unit.position.facing_rad
            rotate_angle = math.degrees(facing_rad)

            turret_rotated = pygame.transform.rotate(turret_scaled, rotate_angle)

            rot_rect = turret_rotated.get_rect(center=(int(sp[0]), int(sp[1])))
            surface.blit(turret_rotated, rot_rect)
        except (pygame.error, ValueError, TypeError, ImportError) as e:
            logging.debug("Turret overlay failed: %s", e)
