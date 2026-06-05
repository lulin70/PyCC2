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
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.domain.interfaces.display_config import DisplayConfig

    from ..domain.value_objects.vec2 import Vec2

from pycc2.presentation.rendering.animation_system import (
    AnimationType,
    ParticleEmitter,
    ScreenShake,
    UnitAnimator,
)
from pycc2.presentation.rendering.tile_cache import TileCache


class SpriteRenderer:
    TILE_SIZE: int = 48  # CC2 authentic: 48×48 pixel tiles
    SPRITE_SIZE: int = 32  # CC2-style units (scaled up for 48px tiles)

    def __init__(self, display_config: DisplayConfig | None = None):
        from pycc2.domain.interfaces.display_config import DisplayConfig as DC
        from pycc2.presentation.rendering.asset_loader import AssetLoader

        self._display_config: DisplayConfig = display_config or DC()
        self.TILE_SIZE: int = 48  # CC2 authentic: matches EnhancedRenderer and Vec2.TILE_SIZE
        self.SPRITE_SIZE: int = 32  # CC2-style units (scaled for 48px tiles)
        self._screen: Surface | None = None
        self._target_surface: Surface | None = None  # 绘制目标（优先于_screen）
        self._sprite_cache: dict[str, Surface] = {}
        self._terrain_cache: dict[int, Surface] = {}
        self._tile_cache: TileCache = TileCache()
        self._animation_tick: int = 0
        self._effect_particles: list[dict] = []
        self._damage_numbers: list[dict] = []
        self._flash_units: dict[str, int] = {}
        self._death_animations: dict[str, dict] = {}
        self._unit_animators: dict[str, UnitAnimator] = {}
        self._screen_shake = ScreenShake()
        self._particle_emitter = ParticleEmitter()
        self._font_cache: dict[int, Font] = {}
        self._asset_loader: AssetLoader = AssetLoader()
        self._surface_pool: dict[tuple[int, int], pygame.Surface] = {}

        self._generate_all_sprites()
        self._generate_terrain_tiles()

    def _get_pooled_surface(self, w: int, h: int) -> pygame.Surface:
        key = (w, h)
        surf = self._surface_pool.get(key)
        if surf is None:
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            self._surface_pool[key] = surf
            if len(self._surface_pool) > 30:
                oldest_key = next(iter(self._surface_pool))
                del self._surface_pool[oldest_key]
        surf.fill((0, 0, 0, 0))
        return surf

    def initialize(self, screen: Surface) -> None:
        self._screen = screen

        # 将AssetLoader加载的PNG精灵复制到_sprite_cache，覆盖程序化精灵
        if hasattr(self._asset_loader, '_sprite_cache'):
            png_count = 0
            for key, sprite_surface in self._asset_loader._sprite_cache.items():
                self._sprite_cache[key] = sprite_surface
                png_count += 1
            print(f"[SpriteRenderer] ✅ 已将 {png_count} 个PNG精灵加载到缓存")
        else:
            print("[SpriteRenderer] ⚠️  AssetLoader没有_sprite_cache属性，使用程序化精灵")

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
        self._animation_tick += 1
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
        # ============================================================
        # ⚠️ RELEASE MODE GUARD: Debug网格线仅在 debug_mode=True 时绘制
        # - _draw_debug_grid(): 调试网格（开发用）
        # - 正式发布: debug_mode=False → 完全跳过
        # ============================================================
        if debug_mode:
            self._draw_debug_grid(game_map, camera)
        self._draw_vl_flags(game_map, camera)
        self._draw_units(units, camera, selected_unit_ids)
        self._draw_effects(camera)
        self._draw_damage_numbers(camera)
        self._update_effects()

    # ====== 程序化精灵生成 ======

    def _generate_all_sprites(self) -> None:
        """预生成所有单位类型的精灵（8方向 × 3阵营）"""
        for faction in ["allies", "axis", "polish"]:
            for unit_type_name in [
                "INFANTRY_SQUAD",
                "MACHINE_GUN_SQUAD",
                "COMMANDER",
                "TANK",
                "HALFTRACK",
                "JEEP",
                "SCOUT_CAR",
                "SNIPER_TEAM",
                "MEDIC_TEAM",
                "AT_GUN_TEAM",
                "MORTAR_TEAM",
            ]:
                for direction in range(8):  # N, NE, E, SE, S, SW, W, NW
                    key = f"{faction}_{unit_type_name}_d{direction}"
                    sprite = self._create_unit_sprite(faction, unit_type_name, direction)
                    self._sprite_cache[key] = sprite

                # 也生成一个默认方向(d0=朝北)的fallback
                default_key = f"{faction}_{unit_type_name}_d0"
                if default_key not in self._sprite_cache:
                    self._sprite_cache[default_key] = self._create_unit_sprite(
                        faction, unit_type_name, 0
                    )

    def _create_unit_sprite(self, faction: str, unit_type: str, direction: int, turret_direction: int | None = None, state: str = 'idle') -> Surface:
        """创建单位精灵 - 优先使用CC2写实像素艺术生成器"""

        # 尝试从assets加载（原有逻辑）
        loaded_sprite = self._asset_loader.load_unit_sprite(
            faction=faction,
            unit_type=unit_type,
            direction=direction,
            size=self.SPRITE_SIZE,
        )

        if loaded_sprite is not None:
            logger.info(f"[SPRITE] ✅ Loaded PNG: {faction}_{unit_type}_d{direction}")
            return loaded_sprite

        # 优先使用新的CC2写实像素艺术生成器
        try:
            from pycc2.domain.value_objects.direction import Direction
            from pycc2.domain.entities.unit import Faction
            from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D

            dir_enum = list(Direction)[direction] if direction < 8 else Direction.SOUTH
            # POLISH使用ALLIES的视觉风格（同属盟军）
            # Faction enum uses auto() integer values; map string names to enum members
            _FACTION_MAP = {
                "allies": Faction.ALLIES, "american": Faction.AMERICAN,
                "british": Faction.BRITISH, "polish": Faction.POLISH,
                "axis": Faction.AXIS, "german": Faction.GERMAN,
            }
            fac_enum = _FACTION_MAP.get(faction, Faction.ALLIES)

            # 根据单位类型选择正确的生成方法
            if unit_type in ("TANK",):
                # 炮塔方向：如果指定了则使用，否则与车体同向
                turret_enum = None
                if turret_direction is not None:
                    turret_enum = list(Direction)[turret_direction % 8]
                cc2_sprite = PixelArtist3D.create_tank_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    turret_direction=turret_enum,
                    state='idle',
                    frame=0
                )
            elif unit_type in ("HALFTRACK",):
                cc2_sprite = PixelArtist3D.create_halftrack_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state='idle',
                    frame=0
                )
            elif unit_type in ("JEEP", "SCOUT_CAR"):
                cc2_sprite = PixelArtist3D.create_jeep_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state='idle',
                    frame=0
                )
            elif unit_type in ("AT_GUN_TEAM",):
                cc2_sprite = PixelArtist3D.create_at_gun_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state='idle',
                    frame=0
                )
            elif unit_type in ("MORTAR_TEAM",):
                cc2_sprite = PixelArtist3D.create_mortar_team_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state='idle',
                    frame=0
                )
            else:
                # 步兵类单位 (INFANTRY_SQUAD, MACHINE_GUN_SQUAD, COMMANDER, SNIPER_TEAM, MEDIC_TEAM)
                cc2_sprite = PixelArtist3D.create_infantry_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state=state,
                    frame=0
                )

            logger.info(f"[SPRITE] ✅ Generated CC2 pixel art: {faction}_{unit_type}_d{direction}")
            return cc2_sprite

        except Exception as e:
            logger.warning(f"[SPRITE] ❌ CC2 generation failed: {e}, using legacy fallback")

        # Fallback: 使用旧的程序化生成器（高分辨率）
        from pycc2.presentation.rendering.pixel_artist import create_unit_sprite

        logger.info(f"[SPRITE] ⚠️  Fallback to legacy procedural: {faction}_{unit_type}_d{direction}")
        canvas = create_unit_sprite(
            faction=faction,
            unit_type=unit_type,
            direction=direction,
            size=self.SPRITE_SIZE,
            state=state,
        )
        return canvas.to_surface()

    def _generate_terrain_tiles(self) -> None:
        """生成地形tiles - 优先从assets加载"""
        from pycc2.presentation.rendering.pixel_artist import create_terrain_tile

        for tid in range(22):
            # 尝试从assets加载
            loaded_tile = self._asset_loader.load_terrain_tile(tid, size=self.TILE_SIZE)
            
            if loaded_tile is not None:
                self._terrain_cache[tid] = loaded_tile
            else:
                # Fallback: 程序化生成
                canvas = create_terrain_tile(tid, size=self.TILE_SIZE)
                self._terrain_cache[tid] = canvas.to_surface()

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
                cached_surface = self._tile_cache.get_tile(tv, tsz)
                if cached_surface:
                    wx = tx * self.TILE_SIZE
                    wy = ty * self.TILE_SIZE
                    sp = camera.world_to_screen(Vec2(wx, wy))
                    self.draw_surface.blit(cached_surface, (int(sp[0]), int(sp[1])))

    def _draw_vl_flags(self, game_map: GameMap, camera: Camera) -> None:
        """Draw Victory Location flags on the map.

        Iterates over game_map.objectives (MapObjective list) and renders
        a flag at each VL position.  Flags change colour based on ownership
        and show a capture progress bar when contested.
        """
        if self.draw_surface is None:
            return
        from pycc2.domain.value_objects.vec2 import Vec2

        objectives = getattr(game_map, 'objectives', [])
        if not objectives:
            return

        screen_w = self.draw_surface.get_width()
        screen_h = self.draw_surface.get_height()

        # Collect off-screen VL positions for edge arrows
        off_screen_vls: list[tuple[int, int, str]] = []

        for obj in objectives:
            # Convert tile coord → world pixel coord → screen coord
            tile_x = obj.position.x * self.TILE_SIZE + self.TILE_SIZE // 2
            tile_y = obj.position.y * self.TILE_SIZE + self.TILE_SIZE // 2
            sp = camera.world_to_screen(Vec2(tile_x, tile_y))
            sx, sy = int(sp[0]), int(sp[1])

            owner = getattr(obj, 'owner', None) or 'neutral'
            is_contested = False
            capture_progress = 0.0

            # Determine if VL is on screen (with margin)
            margin = 60
            on_screen = (-margin < sx < screen_w + margin and -margin < sy < screen_h + margin)

            if on_screen:
                self._draw_vl_flag(self.draw_surface, sx, sy, owner, is_contested, capture_progress)
            else:
                # Store world position for edge arrow rendering
                off_screen_vls.append((tile_x, tile_y, owner))

        # Draw edge arrows for off-screen VLs
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
        """Draw a single Victory Location flag on the map.

        Args:
            surface: Target surface
            x, y: Screen coordinates of the VL center
            owner: 'allies', 'axis', or 'neutral'
            is_contested: Whether both sides are present
            capture_progress: 0.0-1.0 capture progress
        """
        # Flag pole
        pygame.draw.line(surface, (80, 80, 80), (x, y), (x, y - 20), 2)

        # Flag colours based on owner
        if owner == 'allies':
            flag_color = (60, 100, 200)   # Blue
        elif owner == 'axis':
            flag_color = (200, 60, 60)    # Red
        else:
            flag_color = (200, 200, 200)  # White/neutral

        # If contested, flash between colours
        if is_contested:
            if int(time.time() * 4) % 2 == 0:
                flag_color = (200, 200, 100)  # Yellow flash

        # Draw flag (small waving rectangle)
        flag_points = [
            (x + 1, y - 20),
            (x + 14, y - 17),
            (x + 13, y - 10),
            (x + 1, y - 13),
        ]
        pygame.draw.polygon(surface, flag_color, flag_points)
        pygame.draw.polygon(surface, (0, 0, 0), flag_points, 1)

        # Capture progress bar (if capturing)
        if 0 < capture_progress < 1.0:
            bar_width = 16
            bar_height = 3
            bar_x = x - bar_width // 2
            bar_y = y + 4
            pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height))
            fill_width = int(bar_width * capture_progress)
            pygame.draw.rect(surface, (100, 255, 100), (bar_x, bar_y, fill_width, bar_height))

        # Pulsing glow for active capture
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
        """Draw arrows at screen edges pointing toward off-screen VLs.

        Args:
            vl_positions: List of (world_x, world_y, owner) tuples in pixels.
            camera: Camera object for coordinate conversion.
        """
        from pycc2.domain.value_objects.vec2 import Vec2

        margin = 30  # pixels from edge

        for wx, wy, owner in vl_positions:
            # Convert to screen coords
            sp = camera.world_to_screen(Vec2(wx, wy))
            sx, sy = sp[0], sp[1]

            # Clamp to screen edge
            cx = max(margin, min(screen_w - margin, sx))
            cy = max(margin, min(screen_h - margin, sy))

            # Arrow colour based on owner
            if owner == 'allies':
                color = (60, 100, 200)
            elif owner == 'axis':
                color = (200, 60, 60)
            else:
                color = (200, 200, 200)

            # Draw arrow pointing toward VL
            angle = math.atan2(sy - cy, sx - cx)
            arrow_size = 10
            tip_x = cx + arrow_size * math.cos(angle)
            tip_y = cy + arrow_size * math.sin(angle)
            left_x = cx + arrow_size * math.cos(angle + 2.5)
            left_y = cy + arrow_size * math.sin(angle + 2.5)
            right_x = cx + arrow_size * math.cos(angle - 2.5)
            right_y = cy + arrow_size * math.sin(angle - 2.5)

            pygame.draw.polygon(
                surface, color,
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
    ) -> None:
        """使用精灵绘制单位"""
        from pycc2.presentation.rendering.camera import ProjectionMode

        if camera.projection == ProjectionMode.ISOMETRIC:
            # In isometric mode, sort by depth key for correct draw ordering
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
                # 检查是否有死亡动画
                death = self._death_animations.get(unit.id)
                if death:
                    self._draw_death_animation(unit, camera, death)
                continue

            is_selected = unit.id in (selected_ids or set())
            self._draw_sprite_unit(unit, camera, is_selected)

    def _draw_sprite_unit(self, unit: Unit, camera: Camera, is_selected: bool) -> None:
        pos = unit.position.pixel_position
        sp = camera.world_to_screen(pos)

        dir_idx = self._facing_to_direction_index(unit.position.facing_rad)

        faction = unit.faction.name.lower()
        utype = unit.unit_type.name

        movement_mode = getattr(unit, 'movement_mode', 'normal')
        sprite_state = 'idle'
        if movement_mode in ('sneak', 'hide', 'defend'):
            sprite_state = movement_mode

        prone_states = {'sneak', 'hide', 'defend'}
        is_prone = sprite_state in prone_states and 'TANK' not in utype

        if is_prone:
            sprite = self._create_unit_sprite(faction, utype, dir_idx, state=sprite_state)
        else:
            base_key = f"{faction}_{utype}_d{dir_idx}"
            sprite = (
                self._sprite_cache.get(base_key) or
                self._sprite_cache.get(f"{base_key}_{self.SPRITE_SIZE}") or
                self._sprite_cache.get(f"{faction}_{utype}_d0") or
                self._sprite_cache.get(f"{faction}_{utype}_d0_{self.SPRITE_SIZE}") or
                None
            )
        
        if sprite is None:
            # 最终fallback：使用简单形状（但至少是方形表示不同单位类型）
            r = int(12 * camera.zoom)
            # Building garrison: use semi-transparent rendering
            in_building = unit.current_building_pos is not None
            if 'TANK' in utype or 'VEHICLE' in utype:
                color = (80, 80, 80)
                if in_building:
                    s = self._get_pooled_surface(r*2, r*2)
                    s.fill((*color, 160))
                    self.draw_surface.blit(s, (int(sp[0])-r, int(sp[1])-r))
                else:
                    draw.rect(self.draw_surface, color,
                             (int(sp[0])-r, int(sp[1])-r, r*2, r*2))
            elif 'SNIPER' in utype:
                color = (100, 200, 100)
                points = [
                    (int(sp[0]), int(sp[1])-r),
                    (int(sp[0])-r, int(sp[1])+r),
                    (int(sp[0])+r, int(sp[1])+r)
                ]
                if in_building:
                    s = self._get_pooled_surface(r*2+2, r*2+2)
                    local_pts = [(p[0] - int(sp[0]) + r + 1, p[1] - int(sp[1]) + r + 1) for p in points]
                    draw.polygon(s, (*color, 160), local_pts)
                    self.draw_surface.blit(s, (int(sp[0])-r-1, int(sp[1])-r-1))
                else:
                    draw.polygon(self.draw_surface, color, points)
            else:
                color = (74, 144, 217) if faction == "allies" else (217, 74, 74)
                if in_building:
                    s = self._get_pooled_surface(r*2+2, r*2+2)
                    draw.circle(s, (*color, 160), (r+1, r+1), r)
                    self.draw_surface.blit(s, (int(sp[0])-r-1, int(sp[1])-r-1))
                else:
                    draw.circle(self.draw_surface, color, (int(sp[0]), int(sp[1])), r)
            # Building garrison icon overlay: small house icon above unit
            if in_building:
                icon_size = max(6, int(8 * camera.zoom))
                ix = int(sp[0]) - icon_size // 2
                iy = int(sp[1]) - r - icon_size - 2
                draw.rect(self.draw_surface, (160, 140, 120), (ix, iy + icon_size // 2, icon_size, icon_size // 2))
                draw.polygon(self.draw_surface, (120, 90, 60), [
                    (ix - 1, iy + icon_size // 2),
                    (ix + icon_size // 2, iy),
                    (ix + icon_size + 1, iy + icon_size // 2),
                ])
            return

        zoom = camera.zoom
        sz = int(self.SPRITE_SIZE * zoom)
        if sz > 0:
            scaled = transform.scale(sprite, (sz, sz))
            offset = sz // 2

            if unit.id not in self._unit_animators:
                self._unit_animators[unit.id] = UnitAnimator()

            animator = self._unit_animators.get(unit.id)
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

            # Building garrison: render unit semi-transparent when inside a building
            if unit.current_building_pos is not None:
                scaled.set_alpha(160)  # Semi-transparent to indicate inside building

            # Wounded visual state: apply red cross/bandage or red tint overlay
            hp_ratio = unit.health.hp_ratio
            if hp_ratio < 0.5:
                try:
                    from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D
                    scaled = PixelArtist3D.apply_wounded_overlay(scaled, hp_ratio)
                except Exception as e:
                    logging.debug(f"Wounded overlay failed: {e}")

            self.draw_surface.blit(scaled, draw_pos)

            # 坦克炮塔独立旋转覆盖层
            if 'TANK' in utype:
                self._draw_turret_overlay(unit, sp, zoom, faction)

        if is_selected:
            if sz > 0 and sprite is not None:
                self._draw_selection_outline(scaled, draw_pos)
            self._draw_selection_ring(sp, int(16 * zoom))

        self._draw_faction_flag(unit, sp, zoom)
        self._draw_unit_label(unit, sp, zoom)
        self._draw_health_bar(unit, sp, zoom)

        # Enhanced morale state visualization
        self._draw_enhanced_morale_indicator(unit, sp, zoom)
        
        # Draw movement mode indicator (Defend, Fast Move, Sneak)
        self._draw_movement_mode_indicator(unit, sp, zoom)

        if unit.id in self._flash_units:
            flash_surf = self._get_pooled_surface(sz, sz)
            flash_surf.fill((255, 255, 255, 150))
            self.draw_surface.blit(flash_surf, (int(sp[0]) - offset, int(sp[1]) - offset))

    def _facing_to_direction_index(self, rad: float) -> int:
        """将弧度转为8方向索引 (N=0, 顺时针: NE=1, E=2, SE=3, S=4, SW=5, W=6, NW=7)

        facing_rad使用数学坐标系: 0=East, pi/2=North (Y翻转后)
        Direction索引使用CC2屏幕坐标系: 0=North, 2=East
        需要旋转-90度来对齐。
        """
        deg = math.degrees(rad) % 360
        if deg < 0:
            deg += 360
        # 旋转-90度: math坐标系(E=0) → CC2坐标系(N=0)
        idx = round((90 - deg) / 45) % 8
        return idx

    def _draw_turret_overlay(self, unit, sp, zoom, faction):
        """绘制独立旋转的坦克炮塔覆盖层

        使用 PixelArtist3D.create_turret_overlay() 生成基础炮塔(朝东)，
        然后用 pygame.transform.rotate() 旋转到单位面朝角度，
        实现炮塔平滑旋转而非8方向离散跳变。
        """
        try:
            from pycc2.domain.value_objects.direction import Direction
            from pycc2.domain.entities.unit import Faction
            from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D
            from pycc2.presentation.rendering.pixel_artist_enums import TankType

            fac_enum = Faction.ALLIES if faction in ("allies", "polish") else Faction.AXIS
            tank_type = TankType.SHERMAN_M4 if fac_enum == Faction.ALLIES else TankType.PANTHER_AUSFG

            # 创建基础炮塔 (朝东=0°, 不旋转)
            turret_base = PixelArtist3D.create_turret_overlay(
                faction=fac_enum,
                turret_direction=Direction.EAST,
                tank_type=tank_type,
            )

            # 缩放到与身体精灵相同大小
            sz = int(self.SPRITE_SIZE * zoom)
            if sz <= 0:
                return
            turret_scaled = transform.scale(turret_base, (sz, sz))

            # 计算旋转角度 (facing_rad → pygame逆时针角度)
            facing_rad = unit.position.facing_rad
            rotate_angle = math.degrees(facing_rad)

            # 旋转炮塔
            turret_rotated = pygame.transform.rotate(turret_scaled, rotate_angle)

            # 居中覆盖在单位位置上
            rot_rect = turret_rotated.get_rect(center=(int(sp[0]), int(sp[1])))
            self.draw_surface.blit(turret_rotated, rot_rect)
        except Exception as e:
            logging.debug(f"Turret overlay failed: {e}")

    def _draw_selection_ring(self, center: tuple[float, float], radius: int) -> None:
        """CC2风格：选中单位成员轮廓 - 基于时间脉动的黄色描边（P2-12优化）

        使用sin函数控制alpha值在0.7-1.0之间周期性变化，
        产生呼吸脉动效果，提升视觉反馈质量。
        """
        if self.draw_surface is None:
            return

        # Pulsing alpha calculation using sin function (range: 0.7 - 1.0)
        # Period: ~60 ticks (1 second at 60 FPS) for smooth breathing effect
        pulse = math.sin(self._animation_tick * 0.105)  # 0.105 ≈ 2π/60
        alpha = 0.85 + 0.15 * pulse  # Range: 0.7 - 1.0

        base_color = (255, 255, 0)
        color = (
            int(base_color[0] * alpha),
            int(base_color[1] * alpha),
            int(base_color[2] * alpha)
        )

        # Draw pulsing selection ring
        draw.circle(self.draw_surface, color, (int(center[0]), int(center[1])), radius + 3, 2)

        # Optional: Add subtle outer glow ring (very faint, follows same pulse)
        glow_alpha = int(40 + 30 * pulse)  # Range: 10 - 70
        if glow_alpha > 10:
            glow_surf = self._get_pooled_surface(radius * 2 + 20, radius * 2 + 20)
            glow_center = (radius + 10, radius + 10)
            draw.circle(glow_surf, (255, 255, 0, glow_alpha), glow_center, radius + 6, 1)
            self.draw_surface.blit(glow_surf,
                                   (int(center[0]) - radius - 10, int(center[1]) - radius - 10))

    def _draw_selection_outline(self, sprite: Surface, draw_pos: tuple[int, int]) -> None:
        """CC2风格：在精灵周围绘制基于轮廓的黄色描边（P2-12优化：脉动效果）

        实现方法：
        1. 创建精灵的放大副本（每边扩展1px）
        2. 将放大副本填充为脉动黄色
        3. 在其上绘制原始精灵
        4. 结果：精灵轮廓周围出现1px黄色描边（带呼吸脉动）

        P2-12增强：
        - 使用sin函数控制alpha值周期性变化（0.7-1.0）
        - 脉动周期约60 ticks（1秒@60FPS）
        - 提供平滑的视觉反馈
        """
        if self.draw_surface is None:
            return

        # Pulsing alpha calculation (same as _draw_selection_ring for consistency)
        pulse = math.sin(self._animation_tick * 0.105)
        base_alpha = int(170 + 55 * pulse)  # Range: 115 - 225 (centered around 170)

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
        # Apply pulsing alpha to yellow color
        outline_only.fill((255, 255, 0, base_alpha))

        pixel_array = pygame.surfarray.pixels_alpha(outline_surface)
        mask_array = pygame.surfarray.pixels_alpha(mask_surface)

        import numpy as np
        outline_alpha = pixel_array.copy()
        mask_alpha = mask_array.copy()

        result_alpha = np.where(
            (outline_alpha > 0) & (mask_alpha == 0),
            np.minimum(outline_alpha, 200),
            0
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
        font_obj = self._get_font(11)
        text_surf = font_obj.render(label, True, (255, 215, 0))
        tx = int(sp[0]) - text_surf.get_width() // 2
        ty = int(sp[1]) - int(22 * zoom)
        self.draw_surface.blit(text_surf, (tx, ty))

    def _draw_faction_flag(self, unit: Unit, sp: tuple[float, float], zoom: float) -> None:
        """CC2原始风格：阵营旗帜指示器（小彩色矩形：绿色=盟军，红色=轴心国）"""
        if self.draw_surface is None:
            return
        faction = unit.faction.name.lower()
        flag_w = max(6, int(8 * zoom))
        flag_h = max(4, int(5 * zoom))
        fx = int(sp[0]) - flag_w // 2
        fy = int(sp[1]) - int(36 * zoom)

        if faction in ("allies", "us", "uk", "polish"):
            flag_color = (80, 200, 80)   # Green for allies
        else:
            flag_color = (220, 60, 60)   # Red for axis

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

        if state_val == 2:  # SUPPRESSED — 黄色!
            draw.circle(self.draw_surface, (255, 220, 50), (ix, iy), icon_size // 2)
        elif state_val == 3:  # PANICED — 红色!
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
        """
        CC2-authentic enhanced morale state visualization.
        
        Shows different indicators based on MoraleSystem state:
        - RALLYED (>70): Green checkmark or no indicator (normal)
        - WAVERING (40-70): Yellow subtle pulse (slight concern)
        - PINNED (20-40): Yellow "!" icon with pulsing ring (cannot move)
        - BROKEN (<20): Red warning triangle above unit (may flee)
        - ROUTING: Red directional arrow showing flee direction
        """
        if self.draw_surface is None:
            return
        
        # Get morale state from unit
        try:
            from pycc2.domain.systems.morale_system import MoraleState, MoraleSystem
            
            if not hasattr(unit, 'morale_state'):
                return
            
            morale_state = unit.morale_state
            
            # Position for indicator (above and to the right of unit)
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
            # RALLYED: No indicator needed (normal operation)
            
        except Exception as e:
            logger.warning(f"Failed to draw morale indicator: {e}")
            # Fallback to old method if available
            try:
                if hasattr(unit, 'morale') and hasattr(unit.morale, 'state'):
                    ms = unit.morale.state.value
                    if ms >= 2:
                        self._draw_morale_icon(sp, zoom, ms)
            except Exception as e:
                logging.debug(f"Morale icon draw failed: {e}")

    def _draw_pinned_indicator(self, x: int, y: int, zoom: float) -> None:
        """Draw yellow "!" icon with pulsing ring for pinned units."""
        icon_size = max(8, int(10 * zoom))
        
        # Pulsing yellow ring effect
        pulse = abs((self._animation_tick % 30) - 15) / 15.0  # 0.0 to 1.0
        ring_alpha = int(150 + 105 * pulse)  # 150-255
        ring_radius = int(icon_size + 4 * pulse * zoom)
        
        # Draw outer pulsing ring
        ring_surf = self._get_pooled_surface(ring_radius * 2 + 4, ring_radius * 2 + 4)
        draw.circle(ring_surf, (255, 220, 50, ring_alpha), 
                   (ring_radius + 2, ring_radius + 2), ring_radius, 2)
        self.draw_surface.blit(ring_surf, (x - ring_radius - 2, y - ring_radius - 2))
        
        # Draw yellow "!" circle
        draw.circle(self.draw_surface, (255, 220, 0), (x, y), icon_size // 2)
        
        # Draw "!" mark
        font_obj = self._get_font(max(8, int(icon_size * 0.8)))
        text_surf = font_obj.render("!", True, (0, 0, 0))
        text_x = x - text_surf.get_width() // 2
        text_y = y - text_surf.get_height() // 2
        self.draw_surface.blit(text_surf, (text_x, text_y))

    def _draw_broken_indicator(self, x: int, y: int, zoom: float) -> None:
        """Draw red warning triangle for broken units."""
        icon_size = max(10, int(12 * zoom))
        
        # Pulsing red glow
        pulse = abs((self._animation_tick % 25) - 12) / 12.0
        glow_alpha = int(100 + 100 * pulse)
        
        # Red triangle (warning symbol)
        half_size = icon_size // 2
        triangle_points = [
            (x, y - half_size),           # Top point
            (x - half_size, y + half_size // 2),  # Bottom left
            (x + half_size, y + half_size // 2),  # Bottom right
        ]
        
        # Glow effect
        glow_surf = self._get_pooled_surface(icon_size * 2 + 8, icon_size * 2 + 8)
        glow_center = (icon_size + 4, icon_size + 4)
        adjusted_points = [
            (glow_center[0] + p[0] - x, glow_center[1] + p[1] - y) 
            for p in triangle_points
        ]
        draw.polygon(glow_surf, (255, 50, 50, glow_alpha), adjusted_points)
        self.draw_surface.blit(glow_surf, (x - icon_size - 4, y - icon_size - 4))
        
        # Main red triangle
        draw.polygon(self.draw_surface, (220, 30, 30), triangle_points)
        draw.polygon(self.draw_surface, (255, 80, 80), triangle_points, 2)  # Border

    def _draw_routing_indicator(self, unit: Unit, sp: tuple[float, float], zoom: float) -> None:
        """Draw fleeing indicator (red arrow) for routing units."""
        from pycc2.domain.value_objects.vec2 import Vec2
        
        # Arrow position (above unit)
        arrow_x = int(sp[0])
        arrow_y = int(sp[1]) - int(24 * zoom)
        arrow_length = max(12, int(18 * zoom))
        arrow_width = max(6, int(8 * zoom))
        
        # Calculate flee direction (toward target or default right)
        direction = 0.0  # Default: flee to the right (East)
        if hasattr(unit, '_routing_target') and unit._routing_target.position is not None:
            dx = unit._routing_target.position.x - unit.position.pixel_position.x
            dy = unit._routing_target.position.y - unit.position.pixel_position.y
            direction = math.atan2(dy, dx)
        
        # Arrow end point
        end_x = arrow_x + int(math.cos(direction) * arrow_length)
        end_y = arrow_y + int(math.sin(direction) * arrow_length)
        
        # Arrow head points
        head_angle1 = direction + math.pi * 0.75
        head_angle2 = direction - math.pi * 0.75
        head_length = arrow_width * 1.5
        
        head1_x = end_x + int(math.cos(head_angle1) * head_length)
        head1_y = end_y + int(math.sin(head_angle1) * head_length)
        head2_x = end_x + int(math.cos(head_angle2) * head_length)
        head2_y = end_y + int(math.sin(head_angle2) * head_length)
        
        # Pulsing alpha
        pulse = abs((self._animation_tick % 20) - 10) / 10.0
        alpha = int(180 + 75 * pulse)
        
        # Draw arrow on transparent surface
        arrow_surf = self._get_pooled_surface(arrow_length * 2 + 10, arrow_length * 2 + 10)
        center = (arrow_length + 5, arrow_length + 5)
        
        # Offset all points to surface center
        local_start = (center[0] + arrow_x - center[0], center[1] + arrow_y - center[1])
        local_end = (center[0] + end_x - arrow_x, center[1] + end_y - arrow_y)
        local_head1 = (center[0] + head1_x - arrow_x, center[1] + head1_y - arrow_y)
        local_head2 = (center[0] + head2_x - arrow_x, center[1] + head2_y - arrow_y)
        
        # Draw arrow shaft
        draw.line(arrow_surf, (255, 50, 50, alpha), 
                 (arrow_length + 5, arrow_length + 5), local_end, 3)
        
        # Draw arrow head
        draw.polygon(arrow_surf, (255, 50, 50, alpha),
                    [local_end, local_head1, local_head2])
        
        self.draw_surface.blit(arrow_surf, (arrow_x - arrow_length - 5, arrow_y - arrow_length - 5))

    def _draw_wavering_indicator(self, x: int, y: int, zoom: float) -> None:
        """Draw subtle yellow pulse for wavering units."""
        icon_size = max(6, int(7 * zoom))
        
        # Subtle pulse effect (slower than pinned)
        pulse = abs((self._animation_tick % 45) - 22) / 22.0
        alpha = int(80 + 60 * pulse)  # Subtle: 80-140
        
        # Small yellow dot with soft glow
        surf = self._get_pooled_surface(icon_size * 3, icon_size * 3)
        center = (icon_size * 1.5, icon_size * 1.5)
        
        # Outer glow
        draw.circle(surf, (255, 220, 50, alpha // 2), center, icon_size)
        # Inner core
        draw.circle(surf, (255, 220, 0, alpha), center, icon_size // 2)
        
        self.draw_surface.blit(surf, (x - icon_size * 1.5, y - icon_size * 1.5))

    def _draw_movement_mode_indicator(
        self,
        unit: Unit,
        sp: tuple[float, float],
        zoom: float,
    ) -> None:
        """
        Draw visual indicator for unit's current movement mode.
        
        CC2 behavior: sneak/defend/hide show PRONE SPRITE as the only indicator.
        No extra icons needed — the elongated body posture speaks for itself.
        Only fast_move gets an additional speed indicator.
        """
        if self.draw_surface is None:
            return
        
        if not hasattr(unit, 'movement_mode'):
            return
        
        try:
            mode = unit.movement_mode
            if mode == "normal":
                return
            
            prone_states = {'sneak', 'hide', 'defend'}
            if mode in prone_states:
                return  # Prone sprite IS the indicator — no extra icon needed
            
            if mode == "fast_move":
                self._draw_fast_move_indicator(sp, zoom)
        except Exception as e:
            logger.debug(f"Failed to draw movement mode indicator: {e}")
            pass

    def _draw_defend_posture(self, x: int, y: int, size: int) -> None:
        """Draw shield icon for defending units."""
        # Shield shape (hexagon-like)
        shield_points = [
            (x, y - size),                    # Top point
            (x + size // 2, y - size // 2),   # Upper right
            (x + size // 2, y + size // 3),   # Lower right
            (x, y + size // 2),               # Bottom point
            (x - size // 2, y + size // 3),   # Lower left
            (x - size // 2, y - size // 2),   # Upper left
        ]
        
        # Blue shield with white border
        draw.polygon(self.draw_surface, (70, 130, 200), shield_points)
        draw.polygon(self.draw_surface, (150, 200, 255), shield_points, 2)

    def _draw_fast_move_indicator(
        self,
        sp: tuple[float, float],
        zoom: float,
    ) -> None:
        """Draw motion lines/speed effect for fast-moving units."""
        # Pulsing speed lines behind unit
        pulse = abs((self._animation_tick % 15) - 7) / 7.0
        alpha = int(100 + 100 * pulse)
        
        base_x = int(sp[0])
        base_y = int(sp[1])
        line_length = max(15, int(25 * zoom))
        
        # Draw 3 horizontal speed lines to the left (showing forward motion)
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
                2
            )
        
        self.draw_surface.blit(surf, (base_x - line_length - 5, base_y - 15))

    def _draw_sneak_indicator(self, x: int, y: int, size: int) -> None:
        """Draw stealth/ghost icon for sneaking units."""
        # Semi-transparent ghost figure or eye icon
        pulse = abs((self._animation_tick % 40) - 20) / 20.0
        alpha = int(120 + 80 * pulse)
        
        # Ghostly circle with semi-transparency
        surf = self._get_pooled_surface(size * 2, size * 2)
        center = (size, size)
        
        # Outer glow (purple/stealth color)
        draw.circle(surf, (150, 100, 200, alpha // 2), center, size)
        # Inner core
        draw.circle(surf, (180, 140, 220, alpha), center, size // 2)
        # Eye slit (to suggest "shhh" stealth)
        eye_y = center[1] - size // 4
        draw.line(surf, (50, 30, 80, alpha),
                 (center[0] - size // 3, eye_y),
                 (center[0] + size // 3, eye_y), 2)
        
        self.draw_surface.blit(surf, (x - size, y - size))

    # ====== 战斗视觉反馈系统 ======

    def spawn_hit_flash(self, unit_id: str) -> None:
        self._flash_units[unit_id] = 8
        if hasattr(self, "_screen_shake"):
            self._screen_shake.trigger(intensity=2.0, duration_ticks=8)
        if unit_id in self._unit_animators:
            self._unit_animators[unit_id].set_animation(AnimationType.HIT_REACT)

    def spawn_damage_number(self, position: Vec2, damage: int, is_kill: bool = False) -> None:
        """生成浮动伤害数字"""
        self._damage_numbers.append(
            {
                "pos": (position.x, position.y),
                "damage": damage,
                "is_kill": is_kill,
                "life": 60,  # 显示60tick
                "vy": -1.5,  # 初始上飘速度
            }
        )

    def spawn_muzzle_flash(self, position: Vec2, direction: float) -> None:
        if hasattr(self, "_particle_emitter"):
            self._particle_emitter.emit_muzzle_flash(position.x, position.y, direction, count=10)
        if hasattr(self, "_screen_shake"):
            self._screen_shake.trigger(intensity=3.0, duration_ticks=10)

    def spawn_death_effect(self, unit_id: str, position: Vec2) -> None:
        if hasattr(self, "_particle_emitter"):
            self._particle_emitter.emit_blood(position.x, position.y, count=12)
            self._particle_emitter.emit_debris(position.x, position.y, count=8)
            self._particle_emitter.emit_smoke(position.x, position.y, count=4)
        if hasattr(self, "_screen_shake"):
            self._screen_shake.trigger(intensity=6.0, duration_ticks=20)
        if unit_id not in self._unit_animators:
            self._unit_animators[unit_id] = UnitAnimator()
        self._unit_animators[unit_id].set_animation(AnimationType.DEATH)
        # Create death animation entry for 4-frame falling sequence (40 ticks total)
        # Store facing direction so the unit falls in the direction it was facing
        facing_rad = 0.0
        try:
            facing_rad = getattr(unit.position, 'facing_rad', 0.0) or 0.0
        except Exception as e:
            logging.debug(f"Facing direction read failed: {e}")
        self._death_animations[unit_id] = {
            "progress": 0,
            "total_ticks": 40,
            "start_pos": (position.x, position.y),
            "facing_rad": facing_rad,
        }

    def spawn_explosion(self, position: Vec2, size: str = "medium") -> None:
        if not hasattr(self, "_particle_emitter"):
            return
        configs = {
            "small": {"core": 3, "smoke": 2, "debris": 3, "core_life": 10, "smoke_life": 18},
            "medium": {"core": 6, "smoke": 4, "debris": 6, "core_life": 18, "smoke_life": 30},
            "large": {"core": 10, "smoke": 6, "debris": 10, "core_life": 24, "smoke_life": 45},
        }
        cfg = configs.get(size, configs["medium"])
        x, y = position.x, position.y
        self._particle_emitter.emit_explosion_core(x, y, count=cfg["core"], life=cfg["core_life"])
        self._particle_emitter.emit_explosion_smoke_cloud(x, y, count=cfg["smoke"], life=cfg["smoke_life"])
        self._particle_emitter.emit_debris(x, y, count=cfg["debris"])
        self._particle_emitter.emit_explosion_ring(x, y)

    def spawn_smoke_screen(self, position: Vec2, radius: float = 64.0) -> None:
        if hasattr(self, "_particle_emitter"):
            self._particle_emitter.emit_smoke_screen(position.x, position.y, radius=radius)

    def _draw_death_animation(
        self,
        unit: Unit,
        camera: Camera,
        death: dict,
    ) -> None:
        """Top-down death animation: unit flattens and fades on the ground plane.

        Frame 1 (0-5 ticks): Flash red
        Frame 2 (5-15 ticks): Slightly flatten (scale Y to 0.8), start fading
        Frame 3 (15-25 ticks): More flatten (scale Y to 0.5), fade to 50%
        Frame 4 (25-40 ticks): Fully flattened (scale Y to 0.3), fade out
        """
        from pycc2.domain.value_objects.vec2 import Vec2

        progress = death["progress"]
        sx, sy = death["start_pos"]
        sp = camera.world_to_screen(Vec2(sx, sy))

        dir_idx = self._facing_to_direction_index(unit.position.facing_rad)
        faction = unit.faction.name.lower()
        utype = unit.unit_type.name
        base_key = f"{faction}_{utype}_d{dir_idx}"
        sprite = (
            self._sprite_cache.get(base_key) or
            self._sprite_cache.get(f"{base_key}_{self.SPRITE_SIZE}") or
            self._sprite_cache.get(f"{faction}_{utype}_d0") or
            self._sprite_cache.get(f"{faction}_{utype}_d0_{self.SPRITE_SIZE}") or
            None
        )

        zoom = camera.zoom
        sz = int(self.SPRITE_SIZE * zoom)
        if sz <= 0:
            return

        if sprite is not None:
            scaled = transform.scale(sprite, (sz, sz))
        else:
            scaled = self._get_pooled_surface(sz, sz)
            color = (74, 144, 217) if faction == "allies" else (217, 74, 74)
            draw.circle(scaled, color, (sz // 2, sz // 2), sz // 2)

        offset = sz // 2

        if progress < 5:
            flash_surf = scaled.copy()
            flash_surf.fill((200, 40, 40, 0), special_flags=pygame.BLEND_RGB_ADD)
            self.draw_surface.blit(flash_surf, (int(sp[0]) - offset, int(sp[1]) - offset))
        elif progress < 15:
            flatten = 0.8
            new_h = max(2, int(sz * flatten))
            flattened = transform.scale(scaled, (sz, new_h))
            alpha = int(255 * 0.9)
            flattened.set_alpha(alpha)
            self.draw_surface.blit(flattened, (int(sp[0]) - offset, int(sp[1]) - new_h // 2))
        elif progress < 25:
            flatten = 0.5
            new_h = max(2, int(sz * flatten))
            flattened = transform.scale(scaled, (sz, new_h))
            fade_progress = (progress - 15) / 10.0
            alpha = int(255 * (1.0 - fade_progress * 0.5))
            flattened.set_alpha(alpha)
            self.draw_surface.blit(flattened, (int(sp[0]) - offset, int(sp[1]) - new_h // 2))
        else:
            flatten = 0.3
            new_h = max(2, int(sz * flatten))
            flattened = transform.scale(scaled, (sz, new_h))
            fade_progress = (progress - 25) / 15.0
            alpha = int(128 * (1.0 - fade_progress))
            if alpha > 0:
                flattened.set_alpha(alpha)
                self.draw_surface.blit(flattened, (int(sp[0]) - offset, int(sp[1]) - new_h // 2))

    def _draw_effects(self, camera: Camera) -> None:
        import pygame
        from pygame import draw, gfxdraw

        from pycc2.domain.value_objects.vec2 import Vec2

        sx, sy = self._screen_shake.update() if hasattr(self, "_screen_shake") else (0, 0)

        for p in self._particle_emitter.particles:
            wpos = Vec2(p.x + sx, p.y + sy)
            sp = camera.world_to_screen(wpos)
            sz = max(1, int(p.size * (1.0 - p.progress * 0.5)))
            alpha = p.alpha
            if alpha <= 0 or sz <= 0:
                continue

            color = (*p.color, min(255, alpha))

            if p.type == ParticleEmitter.ParticleType.EXPLOSION_RING:
                ring_sz = int(sz * p.progress * 3)
                if ring_sz > 0:
                    try:
                        gfxdraw.circle(
                            self.draw_surface, (*color[:3],), (int(sp[0]), int(sp[1])), ring_sz, 1
                        )
                    except (TypeError, ValueError):
                        draw.circle(self.draw_surface, color[:3], (int(sp[0]), int(sp[1])), ring_sz, 1)
            elif p.type in (ParticleEmitter.ParticleType.SMOKE, ParticleEmitter.ParticleType.SMOKE_SCREEN):
                if p.type == ParticleEmitter.ParticleType.SMOKE_SCREEN:
                    expand = 1.0 + p.progress * 1.5
                    smoke_sz = int(sz * expand)
                    smoke_alpha = int(alpha * (1.0 - p.progress * 0.7))
                    if smoke_sz > 0 and smoke_alpha > 0:
                        surf = self._get_pooled_surface(smoke_sz * 2, smoke_sz * 2)
                        draw.circle(surf, (*p.color, min(255, smoke_alpha)), (smoke_sz, smoke_sz), smoke_sz)
                        self.draw_surface.blit(surf, (int(sp[0]) - smoke_sz, int(sp[1]) - smoke_sz))
                else:
                    surf = self._get_pooled_surface(sz * 2, sz * 2)
                    draw.circle(surf, color, (sz, sz), sz)
                    self.draw_surface.blit(surf, (int(sp[0]) - sz, int(sp[1]) - sz))
            elif p.type == ParticleEmitter.ParticleType.EXPLOSION_CORE:
                core_sz = int(sz * (1.0 + p.progress * 2.0))
                core_alpha = int(alpha * (1.0 - p.progress))
                if core_sz > 0 and core_alpha > 0:
                    surf = self._get_pooled_surface(core_sz * 2, core_sz * 2)
                    draw.circle(surf, (*p.color, min(255, core_alpha)), (core_sz, core_sz), core_sz)
                    self.draw_surface.blit(surf, (int(sp[0]) - core_sz, int(sp[1]) - core_sz))
            elif p.type in (ParticleEmitter.ParticleType.DEBRIS,):
                rect_surf = self._get_pooled_surface(sz, sz)
                rect_surf.fill(color)
                rotated = pygame.transform.rotate(rect_surf, p.rotation)
                self.draw_surface.blit(
                    rotated,
                    (int(sp[0]) - rotated.get_width() // 2, int(sp[1]) - rotated.get_height() // 2),
                )
            else:
                draw.circle(self.draw_surface, color, (int(sp[0]), int(sp[1])), sz)

        for p in self._effect_particles:
            px, py = p["pos"]
            wpos = Vec2(px, py)
            sp = camera.world_to_screen(wpos)
            sz = p["size"] * (p["life"] / 10)
            if p["type"] == "muzzle":
                color = (*p["color"], min(255, p["life"] * 30))
            else:
                color = (*p["color"], min(255, p["life"] * 12))
            draw.circle(self.draw_surface, color, (int(sp[0]), int(sp[1])), max(1, int(sz)))

    def _draw_damage_numbers(self, camera: Camera) -> None:
        if self.draw_surface is None:
            return
        from pycc2.domain.value_objects.vec2 import Vec2

        dc = self._display_config
        for dn in self._damage_numbers:
            x, y = dn["pos"]
            text = str(dn["damage"])

            if dn.get("is_kill"):
                text += " \u2620"
                font_size = int(dc.font_size_large * 1.3)
                color = (255, 40, 40)
                shadow_color = (120, 0, 0)
            elif dn["damage"] >= 20:
                font_size = int(dc.font_size_large * 1.1)
                color = (255, 80, 80)
                shadow_color = (120, 20, 20)
            elif dn["damage"] >= 10:
                font_size = dc.font_size_large
                color = (255, 180, 80)
                shadow_color = (120, 80, 0)
            else:
                font_size = dc.font_size_normal
                color = (255, 255, 200)
                shadow_color = (100, 100, 50)

            font_obj = self._get_font(font_size)
            text_surf = font_obj.render(text, True, color)

            shadow_surf = font_obj.render(text, True, shadow_color)

            life_ratio = dn["life"] / 60.0
            offset_y = (60 - dn["life"]) * dn.get("vy", -1.5)
            wobble_x = math.sin(dn["life"] * 0.3) * 3 if dn["life"] > 30 else 0
            wpos = Vec2(x + wobble_x, y + offset_y)
            sp = camera.world_to_screen(wpos)

            scale = 1.0 + (1.0 - life_ratio) * 0.5 if dn["life"] > 50 else 1.0
            if scale != 1.0:
                new_w = int(text_surf.get_width() * scale)
                new_h = int(text_surf.get_height() * scale)
                if new_w > 0 and new_h > 0:
                    text_surf = transform.scale(text_surf, (new_w, new_h))
                    shadow_surf = transform.scale(shadow_surf, (new_w, new_h))

            if dn["life"] < 15:
                alpha = int(255 * (dn["life"] / 15))
                text_surf.set_alpha(alpha)
                shadow_surf.set_alpha(alpha)

            self.draw_surface.blit(shadow_surf, (int(sp[0]) + 2, int(sp[1]) + 2))
            self.draw_surface.blit(text_surf, (int(sp[0]), int(sp[1])))

    def _update_effects(self) -> None:
        """更新所有特效状态"""
        # 更新闪白
        expired_flash = [uid for uid, ticks in self._flash_units.items() if ticks <= 0]
        for uid in expired_flash:
            del self._flash_units[uid]
        for uid in list(self._flash_units.keys()):
            self._flash_units[uid] -= 1

        # 更新粒子
        alive_particles = []
        for p in self._effect_particles:
            p["pos"][0] += p["vx"] * 0.1
            p["pos"][1] += p["vy"] * 0.1
            p["vy"] += 0.5  # 重力
            p["life"] -= 1
            if p["life"] > 0:
                alive_particles.append(p)
        self._effect_particles = alive_particles

        # 更新伤害数字
        alive_dn = []
        for dn in self._damage_numbers:
            dn["life"] -= 1
            if dn["life"] > 0:
                alive_dn.append(dn)
        self._damage_numbers = alive_dn

        # 更新死亡动画
        expired_death = []
        for uid, death in self._death_animations.items():
            death["progress"] += 1
            if death["progress"] >= death["total_ticks"]:
                expired_death.append(uid)
        for uid in expired_death:
            del self._death_animations[uid]

    def ensure_animator(self, unit_id: str) -> UnitAnimator:
        if unit_id not in self._unit_animators:
            self._unit_animators[unit_id] = UnitAnimator()
        return self._unit_animators[unit_id]

    def _get_font(self, size: int) -> Font:
        cached = self._font_cache.get(size)
        if cached is not None:
            return cached
        f = font.Font(None, size)
        self._font_cache[size] = f
        return f

    def update_animations(self) -> None:
        dead_anims = []
        for uid, animator in self._unit_animators.items():
            if not animator.update():
                if animator.state.anim_type == AnimationType.DEATH:
                    pass
                else:
                    dead_anims.append(uid)
        for uid in dead_anims:
            del self._unit_animators[uid]
        if hasattr(self, "_particle_emitter"):
            self._particle_emitter.update()

    def resize(self, w: int, h: int) -> None:
        pass

    def shutdown(self) -> None:
        self._screen = None
        self._sprite_cache.clear()
        self._terrain_cache.clear()
        self._tile_cache.invalidate()
        self._unit_animators.clear()
        self._surface_pool.clear()
        if hasattr(self, "_particle_emitter"):
            self._particle_emitter.clear()
