from __future__ import annotations

import logging
import math
import time
from typing import TYPE_CHECKING

import pygame
from pygame import Surface, draw, font, transform

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces.display_config import DisplayConfig
    from pycc2.presentation.rendering.camera import Camera

    from ..domain.value_objects.vec2 import Vec2

from pycc2.presentation.rendering.animation_system import (
    AnimationType,
    ParticleEmitter,
    ScreenShake,
    UnitAnimator,
)
from pycc2.presentation.rendering.effect_renderer import EffectRenderer
from pycc2.presentation.rendering.sprite_cache_manager import SpriteCacheManager
from pycc2.presentation.rendering.surface_pool import SurfacePool
from pycc2.presentation.rendering.tile_cache import TileCache


class SpriteRenderer:
    """Main rendering coordinator — composes SpriteCacheManager and EffectRenderer.

    After refactoring, this class acts as a coordinator that:
    - Delegates sprite caching to SpriteCacheManager
    - Delegates effect rendering to EffectRenderer
    - Retains terrain rendering, unit rendering, and UI overlay rendering
    """

    TILE_SIZE: int = 48  # CC2 authentic: 48×48 pixel tiles
    SPRITE_SIZE: int = 48  # CC2-style units (matched to 48px tiles)
    MAX_DAMAGE_NUMBERS: int = 50  # Upper limit for floating damage numbers

    def __init__(self, display_config: DisplayConfig | None = None):
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
    def _damage_numbers(self) -> list[dict]:
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
        if debug_mode:
            self._draw_debug_grid(game_map, camera)
        self._draw_vl_flags(game_map, camera)
        self._draw_units(units, camera, selected_unit_ids)
        self._effect_renderer.render_effects(self.draw_surface, camera)
        self._effect_renderer.render_damage_numbers(self.draw_surface, camera)
        self._effect_renderer.update_effects()

    # ====== 程序化精灵生成 (delegated) ======

    def _generate_all_sprites(self) -> None:
        """Delegated to SpriteCacheManager."""
        self._cache_manager._generate_all_sprites()

    def _create_unit_sprite(
        self,
        faction: str,
        unit_type: str,
        direction: int,
        turret_direction: int | None = None,
        state: str = "idle",
    ) -> Surface:
        """Delegated to SpriteCacheManager."""
        return self._cache_manager.create_unit_sprite(
            faction, unit_type, direction, turret_direction, state,
        )

    def _generate_terrain_tiles(self) -> None:
        """Delegated to SpriteCacheManager."""
        self._cache_manager._generate_terrain_tiles()

    # ====== 绘制方法 ======

    def _draw_terrain(self, game_map: GameMap, camera: Camera) -> None:
        """使用缓存的地形tile绘制地图（TileCache避免每帧transform.scale）"""
        from pycc2.domain.value_objects.vec2 import Vec2

        bounds = camera.view_bounds
        sx = max(0, int(bounds[0].x // self.TILE_SIZE))
        ex = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        sy = max(0, int(bounds[0].y // self.TILE_SIZE))
        ey = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tsz = int(self.TILE_SIZE * camera.zoom)
        if tsz <= 0:
            return

        for ty in range(sy, ey):
            for tx in range(sx, ex):
                tv = int(game_map.tile_grid[ty, tx])
                cached_surface = self._cache_manager.get_terrain_tile(tv, tsz)
                if cached_surface:
                    wx = tx * self.TILE_SIZE
                    wy = ty * self.TILE_SIZE
                    sp = camera.world_to_screen(Vec2(wx, wy))
                    self.draw_surface.blit(cached_surface, (int(sp[0]), int(sp[1])))

    def _draw_vl_flags(self, game_map: GameMap, camera: Camera) -> None:
        """Draw Victory Location flags on the map."""
        if self.draw_surface is None:
            return
        from pycc2.domain.value_objects.vec2 import Vec2

        objectives = getattr(game_map, "objectives", [])
        if not objectives:
            return

        screen_w = self.draw_surface.get_width()
        screen_h = self.draw_surface.get_height()

        off_screen_vls: list[tuple[int, int, str]] = []

        for obj in objectives:
            tile_x = obj.position.x * self.TILE_SIZE + self.TILE_SIZE // 2
            tile_y = obj.position.y * self.TILE_SIZE + self.TILE_SIZE // 2
            sp = camera.world_to_screen(Vec2(tile_x, tile_y))
            sx, sy = int(sp[0]), int(sp[1])

            owner = getattr(obj, "owner", None) or "neutral"
            is_contested = False
            capture_progress = 0.0

            margin = 60
            on_screen = -margin < sx < screen_w + margin and -margin < sy < screen_h + margin

            if on_screen:
                self._draw_vl_flag(self.draw_surface, sx, sy, owner, is_contested, capture_progress)
            else:
                off_screen_vls.append((tile_x, tile_y, owner))

        if off_screen_vls:
            self._draw_vl_edge_arrows(self.draw_surface, screen_w, screen_h, off_screen_vls, camera)

    def _draw_vl_flag(
        self,
        surface: Surface,
        x: int,
        y: int,
        owner: str,
        is_contested: bool,
        capture_progress: float,
    ) -> None:
        """Draw a single Victory Location flag on the map."""
        pygame.draw.line(surface, (80, 80, 80), (x, y), (x, y - 20), 2)

        if owner == "allies":
            flag_color = (60, 100, 200)
        elif owner == "axis":
            flag_color = (200, 60, 60)
        else:
            flag_color = (200, 200, 200)

        if is_contested and int(time.time() * 4) % 2 == 0:
            flag_color = (200, 200, 100)

        flag_points = [
            (x + 1, y - 20),
            (x + 14, y - 17),
            (x + 13, y - 10),
            (x + 1, y - 13),
        ]
        pygame.draw.polygon(surface, flag_color, flag_points)
        pygame.draw.polygon(surface, (0, 0, 0), flag_points, 1)

        if 0 < capture_progress < 1.0:
            bar_width = 16
            bar_height = 3
            bar_x = x - bar_width // 2
            bar_y = y + 4
            pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height))
            fill_width = int(bar_width * capture_progress)
            pygame.draw.rect(surface, (100, 255, 100), (bar_x, bar_y, fill_width, bar_height))

        if 0 < capture_progress < 1.0:
            alpha = int(128 + 127 * math.sin(time.time() * 6))
            glow_surf = self._get_pooled_surface(24, 24)
            pygame.draw.circle(glow_surf, (255, 255, 100, alpha // 3), (12, 12), 12)
            surface.blit(glow_surf, (x - 12, y - 22))

    def _draw_vl_edge_arrows(
        self,
        surface: Surface,
        screen_w: int,
        screen_h: int,
        vl_positions: list[tuple[int, int, str]],
        camera: Camera,
    ) -> None:
        """Draw arrows at screen edges pointing toward off-screen VLs."""
        from pycc2.domain.value_objects.vec2 import Vec2

        margin = 30

        for wx, wy, owner in vl_positions:
            sp = camera.world_to_screen(Vec2(wx, wy))
            sx, sy = sp[0], sp[1]

            cx = max(margin, min(screen_w - margin, sx))
            cy = max(margin, min(screen_h - margin, sy))

            if owner == "allies":
                color = (60, 100, 200)
            elif owner == "axis":
                color = (200, 60, 60)
            else:
                color = (200, 200, 200)

            angle = math.atan2(sy - cy, sx - cx)
            arrow_size = 10
            tip_x = cx + arrow_size * math.cos(angle)
            tip_y = cy + arrow_size * math.sin(angle)
            left_x = cx + arrow_size * math.cos(angle + 2.5)
            left_y = cy + arrow_size * math.sin(angle + 2.5)
            right_x = cx + arrow_size * math.cos(angle - 2.5)
            right_y = cy + arrow_size * math.sin(angle - 2.5)

            pygame.draw.polygon(
                surface,
                color,
                [
                    (int(tip_x), int(tip_y)),
                    (int(left_x), int(left_y)),
                    (int(right_x), int(right_y)),
                ],
            )

    def _draw_units(
        self,
        units: list[Unit],
        camera: Camera,
        selected_ids: set[str] | None = None,
        position_overrides: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        """使用精灵绘制单位"""
        from pycc2.presentation.rendering.camera import ProjectionMode

        if camera.projection == ProjectionMode.ISOMETRIC:
            from pycc2.presentation.rendering.isometric_transform import depth_sort_key

            sorted_units = sorted(
                units,
                key=lambda u: depth_sort_key(
                    u.position.pixel_position.x,
                    u.position.pixel_position.y,
                ),
            )
        else:
            sorted_units = sorted(units, key=lambda u: u.position.pixel_position.y)

        for unit in sorted_units:
            if not unit.is_alive:
                death = self._effect_renderer.death_animations.get(unit.id)
                if death:
                    self._effect_renderer.render_death_animation(
                        unit, camera, death,
                        self._cache_manager.sprite_cache,
                        self.SPRITE_SIZE,
                        self.draw_surface,
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

        if is_prone:
            sprite = self._cache_manager.create_unit_sprite(faction, utype, dir_idx, state=sprite_state)
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
                    self.draw_surface.blit(s, (int(sp[0]) - r, int(sp[1]) - r))
                else:
                    draw.rect(
                        self.draw_surface, color, (int(sp[0]) - r, int(sp[1]) - r, r * 2, r * 2)
                    )
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
                    self.draw_surface.blit(s, (int(sp[0]) - r - 1, int(sp[1]) - r - 1))
                else:
                    draw.polygon(self.draw_surface, color, points)
            else:
                color = (74, 144, 217) if faction == "allies" else (217, 74, 74)
                if in_building:
                    s = self._get_pooled_surface(r * 2 + 2, r * 2 + 2)
                    draw.circle(s, (*color, 160), (r + 1, r + 1), r)
                    self.draw_surface.blit(s, (int(sp[0]) - r - 1, int(sp[1]) - r - 1))
                else:
                    draw.circle(self.draw_surface, color, (int(sp[0]), int(sp[1])), r)
            if in_building:
                icon_size = max(6, int(8 * camera.zoom))
                ix = int(sp[0]) - icon_size // 2
                iy = int(sp[1]) - r - icon_size - 2
                draw.rect(
                    self.draw_surface,
                    (160, 140, 120),
                    (ix, iy + icon_size // 2, icon_size, icon_size // 2),
                )
                draw.polygon(
                    self.draw_surface,
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

            self.draw_surface.blit(scaled, draw_pos)

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

        self._effect_renderer.render_hit_flash(unit.id, sp, sz, self.draw_surface)

    def _facing_to_direction_index(self, rad: float) -> int:
        """将弧度转为8方向索引 (N=0, 顺时针: NE=1, E=2, SE=3, S=4, SW=5, W=6, NW=7)"""
        deg = math.degrees(rad) % 360
        if deg < 0:
            deg += 360
        idx = round((90 - deg) / 45) % 8
        return idx

    def _draw_turret_overlay(self, unit, sp, zoom, faction):
        """绘制独立旋转的坦克炮塔覆盖层"""
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
            self.draw_surface.blit(turret_rotated, rot_rect)
        except (pygame.error, ValueError, TypeError, ImportError) as e:
            logging.debug("Turret overlay failed: %s", e)

    def _draw_selection_ring(self, center: tuple[float, float], radius: int) -> None:
        """CC2风格：选中单位成员轮廓 - 基于时间脉动的黄色描边"""
        if self.draw_surface is None:
            return

        pulse = math.sin(self._effect_renderer.animation_tick * 0.105)
        alpha = 0.85 + 0.15 * pulse

        base_color = (255, 255, 0)
        color = (int(base_color[0] * alpha), int(base_color[1] * alpha), int(base_color[2] * alpha))

        draw.circle(self.draw_surface, color, (int(center[0]), int(center[1])), radius + 3, 2)

        glow_alpha = int(40 + 30 * pulse)
        if glow_alpha > 10:
            glow_surf = self._get_pooled_surface(radius * 2 + 20, radius * 2 + 20)
            glow_center = (radius + 10, radius + 10)
            draw.circle(glow_surf, (255, 255, 0, glow_alpha), glow_center, radius + 6, 1)
            self.draw_surface.blit(
                glow_surf, (int(center[0]) - radius - 10, int(center[1]) - radius - 10)
            )

    def _draw_selection_outline(self, sprite: Surface, draw_pos: tuple[int, int]) -> None:
        """CC2风格：在精灵周围绘制基于轮廓的黄色描边"""
        if self.draw_surface is None:
            return

        pulse = math.sin(self._effect_renderer.animation_tick * 0.105)
        base_alpha = int(170 + 55 * pulse)

        w, h = sprite.get_size()
        outline_w = w + 2
        outline_h = h + 2

        outline_surface = Surface((outline_w, outline_h), pygame.SRCALPHA)

        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if dx == 0 and dy == 0:
                    continue
                outline_surface.blit(sprite, (1 + dx, 1 + dy))

        mask_surface = Surface((outline_w, outline_h), pygame.SRCALPHA)
        mask_surface.blit(sprite, (1, 1))

        outline_only = Surface((outline_w, outline_h), pygame.SRCALPHA)
        outline_only.fill((255, 255, 0, base_alpha))

        pixel_array = pygame.surfarray.pixels_alpha(outline_surface)
        mask_array = pygame.surfarray.pixels_alpha(mask_surface)

        import numpy as np

        outline_alpha = pixel_array.copy()
        mask_alpha = mask_array.copy()

        result_alpha = np.where(
            (outline_alpha > 0) & (mask_alpha == 0), np.minimum(outline_alpha, 200), 0
        ).astype(np.uint8)

        pixel_array[:] = result_alpha
        del pixel_array
        del mask_array

        self.draw_surface.blit(outline_only, (draw_pos[0] - 1, draw_pos[1] - 1))

    def _draw_unit_label(self, unit: Unit, sp: tuple[float, float], zoom: float) -> None:
        """CC2原始风格：黄色纯文字标签（无背景框）"""
        if self.draw_surface is None:
            return
        label = unit.unit_type.name.replace("_", " ")
        font_obj = self._effect_renderer.get_font(11)
        text_surf = font_obj.render(label, True, (255, 215, 0))
        tx = int(sp[0]) - text_surf.get_width() // 2
        ty = int(sp[1]) - int(22 * zoom)
        self.draw_surface.blit(text_surf, (tx, ty))

    def _draw_faction_flag(self, unit: Unit, sp: tuple[float, float], zoom: float) -> None:
        """CC2原始风格：阵营旗帜指示器"""
        if self.draw_surface is None:
            return
        faction = unit.faction.name.lower()
        flag_w = max(6, int(8 * zoom))
        flag_h = max(4, int(5 * zoom))
        fx = int(sp[0]) - flag_w // 2
        fy = int(sp[1]) - int(36 * zoom)

        flag_color = (80, 200, 80) if faction in ("allies", "us", "uk", "polish") else (220, 60, 60)

        draw.rect(self.draw_surface, flag_color, (fx, fy, flag_w, flag_h))

    def _draw_health_bar(
        self,
        unit: Unit,
        sp: tuple[float, float],
        zoom: float,
    ) -> None:
        if self.draw_surface is None:
            return
        dc = self._display_config
        bar_w = max(24, int(24 * dc.ui_scale * zoom))
        bar_h = max(3, int(4 * dc.ui_scale * zoom))
        bx = int(sp[0]) - bar_w // 2
        by = int(sp[1]) - int(18 * dc.ui_scale * zoom)

        draw.rect(self.draw_surface, (40, 40, 40), (bx, by, bar_w, bar_h))
        hp_w = max(0, int(bar_w * unit.health.hp_ratio))
        if unit.health.hp_ratio > 0.5:
            hp_color = (80, 200, 80)
        elif unit.health.hp_ratio > 0.25:
            hp_color = (200, 200, 50)
        else:
            hp_color = (220, 60, 60)
        draw.rect(self.draw_surface, hp_color, (bx, by, hp_w, bar_h))
        draw.rect(self.draw_surface, (100, 100, 100), (bx, by, bar_w, bar_h), 1)

    def _draw_morale_icon(
        self,
        sp: tuple[float, float],
        zoom: float,
        state_val: int,
    ) -> None:
        """士气状态图标（旧版兼容）"""
        if self.draw_surface is None:
            return
        icon_size = max(6, int(8 * zoom))
        ix = int(sp[0]) + int(12 * zoom)
        iy = int(sp[1]) - int(14 * zoom)

        if state_val == 2:
            draw.circle(self.draw_surface, (255, 220, 50), (ix, iy), icon_size // 2)
        elif state_val == 3:
            draw.polygon(
                self.draw_surface,
                (255, 50, 50),
                [
                    (ix, iy - icon_size // 2),
                    (ix + icon_size // 2, iy + icon_size // 2),
                    (ix - icon_size // 2, iy + icon_size // 2),
                ],
            )

    def _draw_enhanced_morale_indicator(
        self,
        unit: Unit,
        sp: tuple[float, float],
        zoom: float,
    ) -> None:
        """CC2-authentic enhanced morale state visualization."""
        if self.draw_surface is None:
            return

        try:
            from pycc2.domain.systems.morale_system import MoraleState

            if not hasattr(unit, "morale_state"):
                return

            morale_state = unit.morale_state

            base_x = int(sp[0]) + int(14 * zoom)
            base_y = int(sp[1]) - int(16 * zoom)

            if morale_state == MoraleState.PINNED:
                self._draw_pinned_indicator(base_x, base_y, zoom)
            elif morale_state == MoraleState.BROKEN:
                self._draw_broken_indicator(base_x, base_y, zoom)
            elif morale_state == MoraleState.ROUTING:
                self._draw_routing_indicator(unit, sp, zoom)
            elif morale_state == MoraleState.WAVERING:
                self._draw_wavering_indicator(base_x, base_y, zoom)

        except (pygame.error, ValueError, AttributeError) as e:
            logger.warning("Failed to draw morale indicator: %s", e)
            try:
                if hasattr(unit, "morale") and hasattr(unit.morale, "state"):
                    ms = unit.morale.state.value
                    if ms >= 2:
                        self._draw_morale_icon(sp, zoom, ms)
            except (pygame.error, ValueError) as e:
                logging.debug("Morale icon draw failed: %s", e)

    def _draw_pinned_indicator(self, x: int, y: int, zoom: float) -> None:
        """Draw yellow "!" icon with pulsing ring for pinned units."""
        icon_size = max(8, int(10 * zoom))

        pulse = abs((self._effect_renderer.animation_tick % 30) - 15) / 15.0
        ring_alpha = int(150 + 105 * pulse)
        ring_radius = int(icon_size + 4 * pulse * zoom)

        ring_surf = self._get_pooled_surface(ring_radius * 2 + 4, ring_radius * 2 + 4)
        draw.circle(
            ring_surf,
            (255, 220, 50, ring_alpha),
            (ring_radius + 2, ring_radius + 2),
            ring_radius,
            2,
        )
        self.draw_surface.blit(ring_surf, (x - ring_radius - 2, y - ring_radius - 2))

        draw.circle(self.draw_surface, (255, 220, 0), (x, y), icon_size // 2)

        font_obj = self._effect_renderer.get_font(max(8, int(icon_size * 0.8)))
        text_surf = font_obj.render("!", True, (0, 0, 0))
        text_x = x - text_surf.get_width() // 2
        text_y = y - text_surf.get_height() // 2
        self.draw_surface.blit(text_surf, (text_x, text_y))

    def _draw_broken_indicator(self, x: int, y: int, zoom: float) -> None:
        """Draw red warning triangle for broken units."""
        icon_size = max(10, int(12 * zoom))

        pulse = abs((self._effect_renderer.animation_tick % 25) - 12) / 12.0
        glow_alpha = int(100 + 100 * pulse)

        half_size = icon_size // 2
        triangle_points = [
            (x, y - half_size),
            (x - half_size, y + half_size // 2),
            (x + half_size, y + half_size // 2),
        ]

        glow_surf = self._get_pooled_surface(icon_size * 2 + 8, icon_size * 2 + 8)
        glow_center = (icon_size + 4, icon_size + 4)
        adjusted_points = [
            (glow_center[0] + p[0] - x, glow_center[1] + p[1] - y) for p in triangle_points
        ]
        draw.polygon(glow_surf, (255, 50, 50, glow_alpha), adjusted_points)
        self.draw_surface.blit(glow_surf, (x - icon_size - 4, y - icon_size - 4))

        draw.polygon(self.draw_surface, (220, 30, 30), triangle_points)
        draw.polygon(self.draw_surface, (255, 80, 80), triangle_points, 2)

    def _draw_routing_indicator(self, unit: Unit, sp: tuple[float, float], zoom: float) -> None:
        """Draw fleeing indicator (red arrow) for routing units."""
        arrow_x = int(sp[0])
        arrow_y = int(sp[1]) - int(24 * zoom)
        arrow_length = max(12, int(18 * zoom))
        arrow_width = max(6, int(8 * zoom))

        direction = 0.0
        if hasattr(unit, "_routing_target") and unit._routing_target.position is not None:
            dx = unit._routing_target.position.x - unit.position.pixel_position.x
            dy = unit._routing_target.position.y - unit.position.pixel_position.y
            direction = math.atan2(dy, dx)

        end_x = arrow_x + int(math.cos(direction) * arrow_length)
        end_y = arrow_y + int(math.sin(direction) * arrow_length)

        head_angle1 = direction + math.pi * 0.75
        head_angle2 = direction - math.pi * 0.75
        head_length = arrow_width * 1.5

        head1_x = end_x + int(math.cos(head_angle1) * head_length)
        head1_y = end_y + int(math.sin(head_angle1) * head_length)
        head2_x = end_x + int(math.cos(head_angle2) * head_length)
        head2_y = end_y + int(math.sin(head_angle2) * head_length)

        pulse = abs((self._effect_renderer.animation_tick % 20) - 10) / 10.0
        alpha = int(180 + 75 * pulse)

        arrow_surf = self._get_pooled_surface(arrow_length * 2 + 10, arrow_length * 2 + 10)
        center = (arrow_length + 5, arrow_length + 5)

        local_end = (center[0] + end_x - arrow_x, center[1] + end_y - arrow_y)
        local_head1 = (center[0] + head1_x - arrow_x, center[1] + head1_y - arrow_y)
        local_head2 = (center[0] + head2_x - arrow_x, center[1] + head2_y - arrow_y)

        draw.line(
            arrow_surf, (255, 50, 50, alpha), (arrow_length + 5, arrow_length + 5), local_end, 3
        )
        draw.polygon(arrow_surf, (255, 50, 50, alpha), [local_end, local_head1, local_head2])

        self.draw_surface.blit(arrow_surf, (arrow_x - arrow_length - 5, arrow_y - arrow_length - 5))

    def _draw_wavering_indicator(self, x: int, y: int, zoom: float) -> None:
        """Draw subtle yellow pulse for wavering units."""
        icon_size = max(6, int(7 * zoom))

        pulse = abs((self._effect_renderer.animation_tick % 45) - 22) / 22.0
        alpha = int(80 + 60 * pulse)

        surf = self._get_pooled_surface(icon_size * 3, icon_size * 3)
        center = (icon_size * 1.5, icon_size * 1.5)

        draw.circle(surf, (255, 220, 50, alpha // 2), center, icon_size)
        draw.circle(surf, (255, 220, 0, alpha), center, icon_size // 2)

        self.draw_surface.blit(surf, (x - icon_size * 1.5, y - icon_size * 1.5))

    def _draw_movement_mode_indicator(
        self,
        unit: Unit,
        sp: tuple[float, float],
        zoom: float,
    ) -> None:
        """Draw visual indicator for unit's current movement mode."""
        if self.draw_surface is None:
            return

        if not hasattr(unit, "movement_mode"):
            return

        try:
            mode = unit.movement_mode
            if mode == "normal":
                return

            prone_states = {"sneak", "hide", "defend"}
            if mode in prone_states:
                return

            if mode == "fast_move":
                self._draw_fast_move_indicator(sp, zoom)
        except (pygame.error, ValueError) as e:
            logger.debug("Failed to draw movement mode indicator: %s", e)
            pass

    def _draw_defend_posture(self, x: int, y: int, size: int) -> None:
        """Draw shield icon for defending units."""
        shield_points = [
            (x, y - size),
            (x + size // 2, y - size // 2),
            (x + size // 2, y + size // 3),
            (x, y + size // 2),
            (x - size // 2, y + size // 3),
            (x - size // 2, y - size // 2),
        ]

        draw.polygon(self.draw_surface, (70, 130, 200), shield_points)
        draw.polygon(self.draw_surface, (150, 200, 255), shield_points, 2)

    def _draw_fast_move_indicator(
        self,
        sp: tuple[float, float],
        zoom: float,
    ) -> None:
        """Draw motion lines/speed effect for fast-moving units."""
        pulse = abs((self._effect_renderer.animation_tick % 15) - 7) / 7.0
        alpha = int(100 + 100 * pulse)

        base_x = int(sp[0])
        base_y = int(sp[1])
        line_length = max(15, int(25 * zoom))

        surf = self._get_pooled_surface(line_length + 10, 30)

        for i in range(3):
            offset_y = i * 10 - 10
            line_alpha = int(alpha * (1.0 - abs(offset_y) / 15))
            start_x = line_length + 5
            end_x = int(start_x - line_length * (0.6 + 0.4 * pulse))

            draw.line(
                surf,
                (255, 200, 50, line_alpha),
                (start_x, 15 + offset_y),
                (end_x, 15 + offset_y),
                2,
            )

        self.draw_surface.blit(surf, (base_x - line_length - 5, base_y - 15))

    def _draw_sneak_indicator(self, x: int, y: int, size: int) -> None:
        """Draw stealth/ghost icon for sneaking units."""
        pulse = abs((self._effect_renderer.animation_tick % 40) - 20) / 20.0
        alpha = int(120 + 80 * pulse)

        surf = self._get_pooled_surface(size * 2, size * 2)
        center = (size, size)

        draw.circle(surf, (150, 100, 200, alpha // 2), center, size)
        draw.circle(surf, (180, 140, 220, alpha), center, size // 2)
        eye_y = center[1] - size // 4
        draw.line(
            surf,
            (50, 30, 80, alpha),
            (center[0] - size // 3, eye_y),
            (center[0] + size // 3, eye_y),
            2,
        )

        self.draw_surface.blit(surf, (x - size, y - size))

    # ====== 战斗视觉反馈系统 (delegated) ======

    def spawn_hit_flash(self, unit_id: str) -> None:
        self._effect_renderer.spawn_hit_flash(unit_id)

    def spawn_damage_number(self, position: Vec2, damage: int, is_kill: bool = False) -> None:
        self._effect_renderer.spawn_damage_number(position, damage, is_kill)

    def spawn_muzzle_flash(self, position: Vec2, direction: float) -> None:
        self._effect_renderer.spawn_muzzle_flash(position, direction)

    def spawn_death_effect(self, unit_id: str, position: Vec2) -> None:
        self._effect_renderer.spawn_death_effect(unit_id, position)

    def spawn_explosion(self, position: Vec2, size: str = "medium") -> None:
        self._effect_renderer.spawn_explosion(position, size)

    def spawn_smoke_screen(self, position: Vec2, radius: float = 64.0) -> None:
        self._effect_renderer.spawn_smoke_screen(position, radius)

    def _draw_death_animation(
        self,
        unit: Unit,
        camera: Camera,
        death: dict,
    ) -> None:
        """Delegated to EffectRenderer."""
        self._effect_renderer.render_death_animation(
            unit, camera, death,
            self._cache_manager.sprite_cache,
            self.SPRITE_SIZE,
            self.draw_surface,
            self._facing_to_direction_index,
        )

    def _draw_effects(self, camera: Camera) -> None:
        """Delegated to EffectRenderer."""
        self._effect_renderer.render_effects(self.draw_surface, camera)

    def _draw_damage_numbers(self, camera: Camera) -> None:
        """Delegated to EffectRenderer."""
        self._effect_renderer.render_damage_numbers(self.draw_surface, camera)

    def _update_effects(self) -> None:
        """Delegated to EffectRenderer."""
        self._effect_renderer.update_effects()

    def ensure_animator(self, unit_id: str) -> UnitAnimator:
        return self._effect_renderer.ensure_animator(unit_id)

    def _get_font(self, size: int) -> font.Font:
        return self._effect_renderer.get_font(size)

    def update_animations(self) -> None:
        self._effect_renderer.update_animations()

    def update_flash(self, dt: float) -> None:
        self._effect_renderer.update_effects()

    def update_weather(self, dt: float) -> None:
        pass  # Weather rendering handled by dedicated weather renderer

    def update_shell_casings(self, dt: float) -> None:
        pass  # Shell casings handled by dedicated shell casing system

    def update_suppression_overlay(self, dt: float, units) -> None:
        pass  # Suppression overlay handled by dedicated overlay system

    def _smooth_positions(self, units, dt: float) -> None:
        pass  # Position smoothing handled by movement system

    def resize(self, w: int, h: int) -> None:
        """Handle window resize — invalidate viewport-dependent caches only."""
        self._surface_pool.clear()
        self._cache_manager.terrain_cache.clear()
        self._cache_manager.tile_cache.invalidate()

    def shutdown(self) -> None:
        self._screen = None
        self._cache_manager.clear()
        self._effect_renderer.clear()
        self._surface_pool.clear()
