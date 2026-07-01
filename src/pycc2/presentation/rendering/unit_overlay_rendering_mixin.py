"""Unit overlay rendering mixin — extracted from sprite_renderer.py (D11-2 SRP split).

Contains unit overlay/indicator rendering methods used by the SpriteRenderer facade:
  - Selection: _draw_selection_ring, _draw_selection_outline
  - Labels/flags: _draw_unit_label, _draw_faction_flag, _draw_health_bar
  - Morale: _draw_morale_icon, _draw_enhanced_morale_indicator,
            _draw_pinned_indicator, _draw_broken_indicator,
            _draw_routing_indicator, _draw_wavering_indicator
  - Movement mode: _draw_movement_mode_indicator, _draw_defend_posture,
                    _draw_fast_move_indicator, _draw_sneak_indicator

This is a mixin — do not instantiate directly. The SpriteRenderer facade
inherits this mixin and provides all required attributes via SpriteRendererBase.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import pygame
from pygame import Surface, draw

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces.display_config import DisplayConfig
    from pycc2.presentation.rendering.effect_renderer import EffectRenderer

logger = logging.getLogger(__name__)

__all__ = ["UnitOverlayRenderingMixin"]


class UnitOverlayRenderingMixin:
    """Unit overlay/indicator rendering methods. Inherited by the SpriteRenderer
    facade, not instantiated.
    """

    # -- Facade attributes used by overlay methods (no defaults; set by SpriteRendererBase) --
    draw_surface: Surface | None
    _display_config: DisplayConfig
    _effect_renderer: EffectRenderer

    if TYPE_CHECKING:
        # -- Cross-mixin method stub (provided by SpriteRendererBase). Declared for typing
        # only so it does not shadow the real implementation at runtime (MRO). --
        def _get_pooled_surface(self, w: int, h: int) -> pygame.Surface: ...

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
        if font_obj is None:
            return
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
        surface = self.draw_surface
        if surface is None:
            return
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
        surface.blit(ring_surf, (x - ring_radius - 2, y - ring_radius - 2))

        draw.circle(surface, (255, 220, 0), (x, y), icon_size // 2)

        font_obj = self._effect_renderer.get_font(max(8, int(icon_size * 0.8)))
        if font_obj is None:
            return
        text_surf = font_obj.render("!", True, (0, 0, 0))
        text_x = x - text_surf.get_width() // 2
        text_y = y - text_surf.get_height() // 2
        surface.blit(text_surf, (text_x, text_y))

    def _draw_broken_indicator(self, x: int, y: int, zoom: float) -> None:
        """Draw red warning triangle for broken units."""
        surface = self.draw_surface
        if surface is None:
            return
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
        surface.blit(glow_surf, (x - icon_size - 4, y - icon_size - 4))

        draw.polygon(surface, (220, 30, 30), triangle_points)
        draw.polygon(surface, (255, 80, 80), triangle_points, 2)

    def _draw_routing_indicator(self, unit: Unit, sp: tuple[float, float], zoom: float) -> None:
        """Draw fleeing indicator (red arrow) for routing units."""
        surface = self.draw_surface
        if surface is None:
            return
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

        surface.blit(arrow_surf, (arrow_x - arrow_length - 5, arrow_y - arrow_length - 5))

    def _draw_wavering_indicator(self, x: int, y: int, zoom: float) -> None:
        """Draw subtle yellow pulse for wavering units."""
        surface = self.draw_surface
        if surface is None:
            return
        icon_size = max(6, int(7 * zoom))

        pulse = abs((self._effect_renderer.animation_tick % 45) - 22) / 22.0
        alpha = int(80 + 60 * pulse)

        surf = self._get_pooled_surface(icon_size * 3, icon_size * 3)
        center = (icon_size * 1.5, icon_size * 1.5)

        draw.circle(surf, (255, 220, 50, alpha // 2), center, icon_size)
        draw.circle(surf, (255, 220, 0, alpha), center, icon_size // 2)

        surface.blit(surf, (x - icon_size * 1.5, y - icon_size * 1.5))

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
        surface = self.draw_surface
        if surface is None:
            return
        shield_points = [
            (x, y - size),
            (x + size // 2, y - size // 2),
            (x + size // 2, y + size // 3),
            (x, y + size // 2),
            (x - size // 2, y + size // 3),
            (x - size // 2, y - size // 2),
        ]

        draw.polygon(surface, (70, 130, 200), shield_points)
        draw.polygon(surface, (150, 200, 255), shield_points, 2)

    def _draw_fast_move_indicator(
        self,
        sp: tuple[float, float],
        zoom: float,
    ) -> None:
        """Draw motion lines/speed effect for fast-moving units."""
        surface = self.draw_surface
        if surface is None:
            return
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

        surface.blit(surf, (base_x - line_length - 5, base_y - 15))

    def _draw_sneak_indicator(self, x: int, y: int, size: int) -> None:
        """Draw stealth/ghost icon for sneaking units."""
        surface = self.draw_surface
        if surface is None:
            return
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

        surface.blit(surf, (x - size, y - size))
