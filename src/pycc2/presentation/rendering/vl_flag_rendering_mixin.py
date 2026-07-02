"""Victory-Location flag rendering mixin — extracted from sprite_renderer.py (D11-2 SRP split).

Contains VL-flag-related rendering methods used by the SpriteRenderer facade:
  - _draw_vl_flags: iterate map objectives and dispatch on/off-screen rendering
  - _draw_vl_flag: draw a single VL flag with optional VP numeral overlay
  - _draw_vl_edge_arrows: draw screen-edge arrows pointing at off-screen VLs

This is a mixin — do not instantiate directly. The SpriteRenderer facade
inherits this mixin and provides all required attributes via SpriteRendererBase.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

import pygame
from pygame import Surface

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.presentation.rendering.camera import Camera

# VP numeral pulse animation constants (mirrors ui_overlay_renderer.PULSE_*).
# Module-level to avoid per-instance allocation on the hot render path.
_VP_PULSE_BASE_ALPHA = 200
_VP_PULSE_AMPLITUDE = 55
_VP_PULSE_FREQUENCY = 2.0

__all__ = ["VlFlagRenderingMixin"]


class VlFlagRenderingMixin:
    """Victory-Location flag rendering methods. Inherited by the SpriteRenderer
    facade, not instantiated.
    """

    # -- Facade attributes used by VL-flag methods (no defaults; set by SpriteRendererBase) --
    TILE_SIZE: int
    draw_surface: Surface | None

    if TYPE_CHECKING:
        # -- Cross-mixin method provided by SpriteRendererBase (declared for typing only,
        # so it does not shadow the real implementation at runtime via MRO). --
        def _get_pooled_surface(self, w: int, h: int) -> pygame.Surface: ...

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
                vp_points = getattr(obj, "points", None)
                self._draw_vl_flag(
                    self.draw_surface,
                    sx,
                    sy,
                    owner,
                    is_contested,
                    capture_progress,
                    vp_points,
                )
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
        points: int | None = None,
    ) -> None:
        """Draw a single Victory Location flag with optional VP number overlay.

        CC2 original style: building-roof large yellow numeral with black
        outline and subtle pulse animation. Previously the production path
        only drew the flag polygon; the VP value was rendered solely in the
        ui_overlay_renderer fallback. This fix restores CC2-authentic VP
        display on the main render path.
        """
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

        # VP value numeral (CC2-authentic: large gold number with black outline)
        # Restored from ui_overlay_renderer fallback path; font enlarged from
        # 38 -> 52 to match CC2 building-roof numeral proportions.
        if points is not None and isinstance(points, (int, float)) and points > 0:
            try:
                vp_font = pygame.font.Font(None, 52)
                vp_text = str(int(points))
                pulse_scale = math.sin(time.time() * 3.0) * 0.05 + 1.0
                pulse_alpha = int(
                    _VP_PULSE_BASE_ALPHA
                    + _VP_PULSE_AMPLITUDE * abs(math.sin(time.time() * _VP_PULSE_FREQUENCY))
                )
                text_color = (255, 220, 100)
                base_x = x - vp_font.size(vp_text)[0] // 2
                base_y = y - 48

                # 4-direction 1px black outline for legibility over any terrain
                for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                    outline_surf = vp_font.render(vp_text, True, (0, 0, 0))
                    outline_surf.set_alpha(pulse_alpha)
                    surface.blit(
                        outline_surf,
                        (int(base_x + dx * pulse_scale), int(base_y + dy * pulse_scale)),
                    )

                # Main gold numeral with subtle pulse scale
                text_surf = vp_font.render(vp_text, True, text_color)
                text_surf.set_alpha(pulse_alpha)
                if pulse_scale != 1.0:
                    new_w = max(1, int(text_surf.get_width() * pulse_scale))
                    new_h = max(1, int(text_surf.get_height() * pulse_scale))
                    text_surf = pygame.transform.scale(text_surf, (new_w, new_h))
                final_x = int(base_x - (text_surf.get_width() - vp_font.size(vp_text)[0]) // 2)
                final_y = int(base_y - (text_surf.get_height() - vp_font.size(vp_text)[1]) // 2)
                surface.blit(text_surf, (final_x, final_y))
            except (AttributeError, ValueError):
                pass

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
