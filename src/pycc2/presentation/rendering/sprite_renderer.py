from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame
from pygame import Surface, draw, font, transform

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.display_config import DisplayConfig

    from ..domain.value_objects.vec2 import Vec2

from pycc2.presentation.rendering.animation_system import (
    AnimationType,
    ParticleEmitter,
    ScreenShake,
    UnitAnimator,
)
from pycc2.presentation.rendering.tile_cache import TileCache


class SpriteRenderer:
    TILE_SIZE: int = 32
    SPRITE_SIZE: int = 24  # CC2-style: small but visible units (was 128, too large)

    def __init__(self, display_config: DisplayConfig | None = None):
        from pycc2.presentation.rendering.display_config import DisplayConfig as DC
        from pycc2.presentation.rendering.asset_loader import AssetLoader

        self._display_config: DisplayConfig = display_config or DC()
        self.TILE_SIZE: int = self._display_config.base_tile_size
        self.SPRITE_SIZE: int = 24  # CC2-style small units
        self._screen: Surface | None = None
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
        self._asset_loader: AssetLoader = AssetLoader()  # 新增资产加载器

        self._generate_all_sprites()
        self._generate_terrain_tiles()

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
        if self._screen is None:
            return
        self._animation_tick += 1
        self.update_animations()

        # 背景
        bg_color = (52, 73, 94)
        if alpha < 1.0:
            bg = Surface(self._screen.get_size())
            bg.fill(bg_color)
            bg.set_alpha(int(255 * alpha))
            self._screen.blit(bg, (0, 0))
        else:
            self._screen.fill(bg_color)

        self._draw_terrain(game_map, camera)
        if debug_mode:
            self._draw_debug_grid(game_map, camera)
        self._draw_units(units, camera, selected_unit_ids)
        self._draw_effects(camera)
        self._draw_damage_numbers(camera)
        self._update_effects()

    # ====== 程序化精灵生成 ======

    def _generate_all_sprites(self) -> None:
        """预生成所有单位类型的精灵（8方向 × 2阵营）"""
        for faction in ["allies", "axis"]:
            for unit_type_name in [
                "INFANTRY_SQUAD",
                "MACHINE_GUN_SQUAD",
                "COMMANDER",
                "TANK",
                "SNIPER_TEAM",
                "MEDIC_TEAM",
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

    def _create_unit_sprite(self, faction: str, unit_type: str, direction: int) -> Surface:
        """创建单位精灵 - 优先从assets加载，fallback到程序化生成"""
        from pycc2.presentation.rendering.pixel_artist import create_unit_sprite
        import logging
        logger = logging.getLogger(__name__)

        # 尝试从assets加载
        loaded_sprite = self._asset_loader.load_unit_sprite(
            faction=faction,
            unit_type=unit_type,
            direction=direction,
            size=self.SPRITE_SIZE,
        )
        
        if loaded_sprite is not None:
            logger.info(f"[SPRITE] ✅ Loaded PNG: {faction}_{unit_type}_d{direction}")
            return loaded_sprite
        
        # Fallback: 程序化生成（高分辨率）
        logger.info(f"[SPRITE] ⚠️  Fallback to procedural: {faction}_{unit_type}_d{direction}")
        canvas = create_unit_sprite(
            faction=faction,
            unit_type=unit_type,
            direction=direction,
            size=self.SPRITE_SIZE,
        )
        return canvas.to_surface()

    def _generate_terrain_tiles(self) -> None:
        """生成地形tiles - 优先从assets加载"""
        from pycc2.presentation.rendering.pixel_artist import create_terrain_tile

        for tid in range(14):
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
                    self._screen.blit(cached_surface, (int(sp[0]), int(sp[1])))

    def _draw_units(
        self,
        units: list[Unit],
        camera: Camera,
        selected_ids: set[str] | None = None,
    ) -> None:
        """使用精灵绘制单位"""
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
        sprite_key = f"{faction}_{utype}_d{dir_idx}"

        sprite = self._sprite_cache.get(sprite_key)
        if sprite is None:
            sprite = self._sprite_cache.get(f"{faction}_{utype}_d0")
        if sprite is None:
            r = int(12 * camera.zoom)
            color = (74, 144, 217) if faction == "allies" else (217, 74, 74)
            draw.circle(self._screen, color, (int(sp[0]), int(sp[1])), r)
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

            self._screen.blit(scaled, draw_pos)

        if is_selected:
            self._draw_selection_ring(sp, int(16 * zoom))

        self._draw_health_bar(unit, sp, zoom)

        ms = unit.morale.state.value
        if ms >= 2:
            self._draw_morale_icon(sp, zoom, ms)

        if unit.id in self._flash_units:
            flash_surf = Surface((sz, sz), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, 150))
            self._screen.blit(flash_surf, (int(sp[0]) - offset, int(sp[1]) - offset))

    def _facing_to_direction_index(self, rad: float) -> int:
        """将弧度转为8方向索引"""
        deg = math.degrees(rad) % 360
        if deg < 0:
            deg += 360
        # 每个方向45度，N=0(向上/-Y), 顺时针
        idx = round(deg / 45) % 8
        return idx

    def _draw_selection_ring(self, center: tuple[float, float], radius: int) -> None:
        """选中光环（改进版：半透明圆环而非虚线）"""
        if self._screen is None:
            return
        color = (255, 255, 100) if self._animation_tick % 20 < 10 else (255, 220, 50)
        surf = Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        draw.circle(surf, (*color, 100), (radius + 2, radius + 2), radius, 3)
        self._screen.blit(surf, (int(center[0]) - radius - 2, int(center[1]) - radius - 2))

    def _draw_health_bar(
        self,
        unit: Unit,
        sp: tuple[float, float],
        zoom: float,
    ) -> None:
        if self._screen is None:
            return
        dc = self._display_config
        bar_w = max(24, int(24 * dc.ui_scale * zoom))
        bar_h = max(3, int(4 * dc.ui_scale * zoom))
        bx = int(sp[0]) - bar_w // 2
        by = int(sp[1]) - int(18 * dc.ui_scale * zoom)

        draw.rect(self._screen, (40, 40, 40), (bx, by, bar_w, bar_h))
        hp_w = max(0, int(bar_w * unit.health.hp_ratio))
        if unit.health.hp_ratio > 0.5:
            hp_color = (80, 200, 80)
        elif unit.health.hp_ratio > 0.25:
            hp_color = (200, 200, 50)
        else:
            hp_color = (220, 60, 60)
        draw.rect(self._screen, hp_color, (bx, by, hp_w, bar_h))
        draw.rect(self._screen, (100, 100, 100), (bx, by, bar_w, bar_h), 1)

    def _draw_morale_icon(
        self,
        sp: tuple[float, float],
        zoom: float,
        state_val: int,
    ) -> None:
        """士气状态图标"""
        if self._screen is None:
            return
        icon_size = max(6, int(8 * zoom))
        ix = int(sp[0]) + int(12 * zoom)
        iy = int(sp[1]) - int(14 * zoom)

        if state_val == 2:  # SUPPRESSED — 黄色!
            draw.circle(self._screen, (255, 220, 50), (ix, iy), icon_size // 2)
        elif state_val == 3:  # PANICED — 红色!
            draw.polygon(
                self._screen,
                (255, 50, 50),
                [
                    (ix, iy - icon_size // 2),
                    (ix + icon_size // 2, iy + icon_size // 2),
                    (ix - icon_size // 2, iy + icon_size // 2),
                ],
            )

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

    def _draw_death_animation(
        self,
        unit: Unit,
        camera: Camera,
        death: dict,
    ) -> None:
        """绘制死亡收缩+淡出动画"""
        from pycc2.domain.value_objects.vec2 import Vec2

        progress = death["progress"] / death["total_ticks"]
        sx, sy = death["start_pos"]
        sp = camera.world_to_screen(Vec2(sx, sy))

        scale = 1.0 - progress * 0.7  # 收缩到30%
        alpha = int(255 * (1.0 - progress))

        size = int(self.SPRITE_SIZE * camera.zoom * scale)
        if size > 0 and alpha > 0:
            surf = Surface((size, size), pygame.SRCALPHA)
            fade_color = (150, 80, 80, alpha)
            surf.fill(fade_color)
            draw.circle(surf, (180, 60, 60, alpha), (size // 2, size // 2), size // 2)
            self._screen.blit(surf, (int(sp[0]) - size // 2, int(sp[1]) - size // 2))

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
                            self._screen, (*color[:3],), (int(sp[0]), int(sp[1])), ring_sz, 1
                        )
                    except (TypeError, ValueError):
                        draw.circle(self._screen, color[:3], (int(sp[0]), int(sp[1])), ring_sz, 1)
            elif p.type in (ParticleEmitter.ParticleType.SMOKE,):
                surf = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
                draw.circle(surf, color, (sz, sz), sz)
                self._screen.blit(surf, (int(sp[0]) - sz, int(sp[1]) - sz))
            elif p.type in (ParticleEmitter.ParticleType.DEBRIS,):
                rect_surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
                rect_surf.fill(color)
                rotated = pygame.transform.rotate(rect_surf, p.rotation)
                self._screen.blit(
                    rotated,
                    (int(sp[0]) - rotated.get_width() // 2, int(sp[1]) - rotated.get_height() // 2),
                )
            else:
                draw.circle(self._screen, color, (int(sp[0]), int(sp[1])), sz)

        for p in self._effect_particles:
            px, py = p["pos"]
            wpos = Vec2(px, py)
            sp = camera.world_to_screen(wpos)
            sz = p["size"] * (p["life"] / 10)
            if p["type"] == "muzzle":
                color = (*p["color"], min(255, p["life"] * 30))
            else:
                color = (*p["color"], min(255, p["life"] * 12))
            draw.circle(self._screen, color, (int(sp[0]), int(sp[1])), max(1, int(sz)))

    def _draw_damage_numbers(self, camera: Camera) -> None:
        if self._screen is None:
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

            self._screen.blit(shadow_surf, (int(sp[0]) + 2, int(sp[1]) + 2))
            self._screen.blit(text_surf, (int(sp[0]), int(sp[1])))

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
        if hasattr(self, "_particle_emitter"):
            self._particle_emitter.clear()
