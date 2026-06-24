"""Effect Renderer — handles visual effects rendering and lifecycle.

Extracted from SpriteRenderer to isolate effect-related concerns:
- Particle effects rendering (muzzle flash, explosion, smoke, etc.)
- Damage number rendering
- Hit flash effect
- Death animation rendering
- Effect state updates (lifecycle management)

Created: Refactoring — SpriteRenderer responsibility separation
"""

from __future__ import annotations

import logging
import math
from collections import deque
from typing import TYPE_CHECKING

import pygame
from pygame import Surface, draw, font, transform

from pycc2.presentation.rendering.animation_system import (
    AnimationType,
    ParticleEmitter,
    ScreenShake,
    UnitAnimator,
)
from pycc2.presentation.rendering.surface_pool import SurfacePool

if TYPE_CHECKING:
    from pycc2.domain.interfaces.display_config import DisplayConfig
    from pycc2.presentation.rendering.camera import Camera

    from pycc2.domain.value_objects.vec2 import Vec2

logger = logging.getLogger(__name__)


# Enhanced particles feature flag
try:
    from config.rendering_features import is_enhanced_particles_enabled

    _ENHANCED_PARTICLES_AVAILABLE = True
    if is_enhanced_particles_enabled():
        from pycc2.presentation.rendering.enhanced_particle_system import (
            EnhancedParticleSystem,  # noqa: F401
        )
except ImportError:
    _ENHANCED_PARTICLES_AVAILABLE = False


class EffectRenderer:
    """Handles all visual effect rendering and lifecycle management.

    Responsibilities:
    - Particle rendering (explosions, muzzle flash, smoke, blood, debris)
    - Damage number rendering (floating text with fade)
    - Hit flash overlay
    - Death animation rendering (4-frame flatten + fade)
    - Effect state updates (tick-based lifecycle)
    """

    MAX_DAMAGE_NUMBERS: int = 50

    def __init__(self, display_config: DisplayConfig | None = None):
        from pycc2.domain.interfaces.display_config import DisplayConfig as DC

        self._display_config: DisplayConfig = display_config or DC()
        self._animation_tick: int = 0
        self._effect_particles: list[dict] = []
        self._damage_numbers: deque[dict] = deque()
        self._flash_units: dict[str, int] = {}
        self._death_animations: dict[str, dict] = {}
        self._unit_animators: dict[str, UnitAnimator] = {}
        self._screen_shake = ScreenShake()
        self._particle_emitter = ParticleEmitter()
        self._font_cache: dict[int, font.Font] = {}
        self._surface_pool = SurfacePool(max_size=30)

    # ====== Public API: Spawn effects ======

    def spawn_hit_flash(self, unit_id: str) -> None:
        self._flash_units[unit_id] = 8
        self._screen_shake.trigger(intensity=2.0, duration_ticks=8)
        if unit_id in self._unit_animators:
            self._unit_animators[unit_id].set_animation(AnimationType.HIT_REACT)

    def spawn_damage_number(self, position: Vec2, damage: int, is_kill: bool = False) -> None:
        if len(self._damage_numbers) >= self.MAX_DAMAGE_NUMBERS:
            self._damage_numbers.popleft()
        self._damage_numbers.append(
            {
                "pos": (position.x, position.y),
                "damage": damage,
                "is_kill": is_kill,
                "life": 60,
                "vy": -1.5,
            }
        )

    def spawn_muzzle_flash(self, position: Vec2, direction: float) -> None:
        self._particle_emitter.emit_muzzle_flash(position.x, position.y, direction, count=10)
        self._screen_shake.trigger(intensity=3.0, duration_ticks=10)

    def spawn_death_effect(self, unit_id: str, position: Vec2) -> None:
        self._particle_emitter.emit_blood(position.x, position.y, count=12)
        self._particle_emitter.emit_debris(position.x, position.y, count=8)
        self._particle_emitter.emit_smoke(position.x, position.y, count=4)
        self._screen_shake.trigger(intensity=6.0, duration_ticks=20)
        if unit_id not in self._unit_animators:
            self._unit_animators[unit_id] = UnitAnimator()
        self._unit_animators[unit_id].set_animation(AnimationType.DEATH)
        facing_rad = 0.0
        try:
            facing_rad = getattr(position, "facing_rad", 0.0) or 0.0
        except (AttributeError, TypeError) as e:
            logging.debug("Facing direction read failed: %s", e)
        self._death_animations[unit_id] = {
            "progress": 0,
            "total_ticks": 40,
            "start_pos": (position.x, position.y),
            "facing_rad": facing_rad,
        }

    def spawn_explosion(self, position: Vec2, size: str = "medium") -> None:
        configs = {
            "small": {"core": 3, "smoke": 2, "debris": 3, "core_life": 10, "smoke_life": 18},
            "medium": {"core": 6, "smoke": 4, "debris": 6, "core_life": 18, "smoke_life": 30},
            "large": {"core": 10, "smoke": 6, "debris": 10, "core_life": 24, "smoke_life": 45},
        }
        cfg = configs.get(size, configs["medium"])
        x, y = position.x, position.y
        self._particle_emitter.emit_explosion_core(x, y, count=cfg["core"], life=cfg["core_life"])
        self._particle_emitter.emit_explosion_smoke_cloud(
            x, y, count=cfg["smoke"], life=cfg["smoke_life"]
        )
        self._particle_emitter.emit_debris(x, y, count=cfg["debris"])
        self._particle_emitter.emit_explosion_ring(x, y)

    def spawn_smoke_screen(self, position: Vec2, radius: float = 64.0) -> None:
        self._particle_emitter.emit_smoke_screen(position.x, position.y, radius=radius)

    # ====== Public API: Update ======

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
        self._particle_emitter.update()

    def update_effects(self) -> None:
        """Update all effect states (tick-based lifecycle)."""
        # Update hit flash
        expired_flash = [uid for uid, ticks in self._flash_units.items() if ticks <= 0]
        for uid in expired_flash:
            del self._flash_units[uid]
        for uid in list(self._flash_units.keys()):
            self._flash_units[uid] -= 1

        # Update particles
        alive_particles = []
        for p in self._effect_particles:
            p["pos"][0] += p["vx"] * 0.1
            p["pos"][1] += p["vy"] * 0.1
            p["vy"] += 0.5  # gravity
            p["life"] -= 1
            if p["life"] > 0:
                alive_particles.append(p)
        self._effect_particles = alive_particles

        # Update damage numbers
        alive_dn = []
        for dn in self._damage_numbers:
            dn["life"] -= 1
            if dn["life"] > 0:
                alive_dn.append(dn)
        self._damage_numbers = deque(alive_dn)

        # Update death animations
        expired_death = []
        for uid, death in self._death_animations.items():
            death["progress"] += 1
            if death["progress"] >= death["total_ticks"]:
                expired_death.append(uid)
        for uid in expired_death:
            del self._death_animations[uid]

    def tick(self) -> None:
        """Advance animation tick counter."""
        self._animation_tick += 1

    # ====== Public API: Render ======

    def render_effects(self, surface: Surface, camera: Camera) -> None:
        """Render particle effects."""
        from pygame import gfxdraw

        from pycc2.domain.value_objects.vec2 import Vec2

        sx, sy = self._screen_shake.update()

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
                            surface,
                            (*color[:3],),
                            (int(sp[0]), int(sp[1])),
                            ring_sz,
                            1,
                        )
                    except (TypeError, ValueError):
                        draw.circle(surface, color[:3], (int(sp[0]), int(sp[1])), ring_sz, 1)
            elif p.type in (
                ParticleEmitter.ParticleType.SMOKE,
                ParticleEmitter.ParticleType.SMOKE_SCREEN,
            ):
                if p.type == ParticleEmitter.ParticleType.SMOKE_SCREEN:
                    expand = 1.0 + p.progress * 1.5
                    smoke_sz = int(sz * expand)
                    smoke_alpha = int(alpha * (1.0 - p.progress * 0.7))
                    if smoke_sz > 0 and smoke_alpha > 0:
                        surf = self._get_pooled_surface(smoke_sz * 2, smoke_sz * 2)
                        draw.circle(
                            surf, (*p.color, min(255, smoke_alpha)), (smoke_sz, smoke_sz), smoke_sz
                        )
                        surface.blit(surf, (int(sp[0]) - smoke_sz, int(sp[1]) - smoke_sz))
                else:
                    surf = self._get_pooled_surface(sz * 2, sz * 2)
                    draw.circle(surf, color, (sz, sz), sz)
                    surface.blit(surf, (int(sp[0]) - sz, int(sp[1]) - sz))
            elif p.type == ParticleEmitter.ParticleType.EXPLOSION_CORE:
                core_sz = int(sz * (1.0 + p.progress * 2.0))
                core_alpha = int(alpha * (1.0 - p.progress))
                if core_sz > 0 and core_alpha > 0:
                    surf = self._get_pooled_surface(core_sz * 2, core_sz * 2)
                    draw.circle(surf, (*p.color, min(255, core_alpha)), (core_sz, core_sz), core_sz)
                    surface.blit(surf, (int(sp[0]) - core_sz, int(sp[1]) - core_sz))
            elif p.type in (ParticleEmitter.ParticleType.DEBRIS,):
                rect_surf = self._get_pooled_surface(sz, sz)
                rect_surf.fill(color)
                rotated = pygame.transform.rotate(rect_surf, p.rotation)
                surface.blit(
                    rotated,
                    (int(sp[0]) - rotated.get_width() // 2, int(sp[1]) - rotated.get_height() // 2),
                )
            else:
                draw.circle(surface, color, (int(sp[0]), int(sp[1])), sz)

        for p in self._effect_particles:
            px, py = p["pos"]
            wpos = Vec2(px, py)
            sp = camera.world_to_screen(wpos)
            sz = p["size"] * (p["life"] / 10)
            if p["type"] == "muzzle":
                color = (*p["color"], min(255, p["life"] * 30))
            else:
                color = (*p["color"], min(255, p["life"] * 12))
            draw.circle(surface, color, (int(sp[0]), int(sp[1])), max(1, int(sz)))

    def render_damage_numbers(self, surface: Surface, camera: Camera) -> None:
        """Render floating damage numbers."""
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

            surface.blit(shadow_surf, (int(sp[0]) + 2, int(sp[1]) + 2))
            surface.blit(text_surf, (int(sp[0]), int(sp[1])))

    def render_death_animation(
        self,
        unit,
        camera: Camera,
        death: dict,
        sprite_cache: dict[str, Surface],
        sprite_size: int,
        draw_surface: Surface,
        facing_to_direction_index,
    ) -> None:
        """Render death animation for a unit."""
        from pycc2.domain.value_objects.vec2 import Vec2

        progress = death["progress"]
        sx, sy = death["start_pos"]
        sp = camera.world_to_screen(Vec2(sx, sy))

        dir_idx = facing_to_direction_index(unit.position.facing_rad)
        faction = unit.faction.name.lower()
        utype = unit.unit_type.name
        base_key = f"{faction}_{utype}_d{dir_idx}"
        sprite = (
            sprite_cache.get(base_key)
            or sprite_cache.get(f"{base_key}_{sprite_size}")
            or sprite_cache.get(f"{faction}_{utype}_d0")
            or sprite_cache.get(f"{faction}_{utype}_d0_{sprite_size}")
            or None
        )

        zoom = camera.zoom
        sz = int(sprite_size * zoom)
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
            draw_surface.blit(flash_surf, (int(sp[0]) - offset, int(sp[1]) - offset))
        elif progress < 15:
            flatten = 0.8
            new_h = max(2, int(sz * flatten))
            flattened = transform.scale(scaled, (sz, new_h))
            alpha = int(255 * 0.9)
            flattened.set_alpha(alpha)
            draw_surface.blit(flattened, (int(sp[0]) - offset, int(sp[1]) - new_h // 2))
        elif progress < 25:
            flatten = 0.5
            new_h = max(2, int(sz * flatten))
            flattened = transform.scale(scaled, (sz, new_h))
            fade_progress = (progress - 15) / 10.0
            alpha = int(255 * (1.0 - fade_progress * 0.5))
            flattened.set_alpha(alpha)
            draw_surface.blit(flattened, (int(sp[0]) - offset, int(sp[1]) - new_h // 2))
        else:
            flatten = 0.3
            new_h = max(2, int(sz * flatten))
            flattened = transform.scale(scaled, (sz, new_h))
            fade_progress = (progress - 25) / 15.0
            alpha = int(128 * (1.0 - fade_progress))
            if alpha > 0:
                flattened.set_alpha(alpha)
                draw_surface.blit(flattened, (int(sp[0]) - offset, int(sp[1]) - new_h // 2))

    def render_hit_flash(
        self,
        unit_id: str,
        sp: tuple[float, float],
        sz: int,
        draw_surface: Surface,
    ) -> None:
        """Render hit flash overlay for a unit."""
        if unit_id in self._flash_units:
            offset = sz // 2
            flash_surf = self._get_pooled_surface(sz, sz)
            flash_surf.fill((255, 255, 255, 150))
            draw_surface.blit(flash_surf, (int(sp[0]) - offset, int(sp[1]) - offset))

    # ====== Public API: Accessors ======

    @property
    def flash_units(self) -> dict[str, int]:
        return self._flash_units

    @property
    def death_animations(self) -> dict[str, dict]:
        return self._death_animations

    @property
    def unit_animators(self) -> dict[str, UnitAnimator]:
        return self._unit_animators

    @property
    def particle_emitter(self) -> ParticleEmitter:
        return self._particle_emitter

    @property
    def effect_particles(self) -> list[dict]:
        return self._effect_particles

    @property
    def damage_numbers(self) -> deque[dict]:
        return self._damage_numbers

    @property
    def animation_tick(self) -> int:
        return self._animation_tick

    def ensure_animator(self, unit_id: str) -> UnitAnimator:
        if unit_id not in self._unit_animators:
            self._unit_animators[unit_id] = UnitAnimator()
        return self._unit_animators[unit_id]

    def get_font(self, size: int) -> font.Font | None:
        cached = self._font_cache.get(size)
        if cached is not None:
            return cached
        try:
            f = font.Font(None, size)
            self._font_cache[size] = f
            return f
        except (pygame.error, RuntimeError):
            return None

    def clear(self) -> None:
        """Clear all effect state."""
        self._unit_animators.clear()
        self._surface_pool.clear()
        self._particle_emitter.clear()
        self._flash_units.clear()
        self._damage_numbers.clear()
        self._effect_particles.clear()
        self._death_animations.clear()

    # ====== Private helpers ======

    def _get_pooled_surface(self, w: int, h: int) -> pygame.Surface:
        surf = self._surface_pool.get((w, h))
        surf.fill((0, 0, 0, 0))
        return surf
