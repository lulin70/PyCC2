"""
Unit Renderer Sub-Module for CC2-Style Games

Handles unit-specific rendering operations:
- Unit drawing with SpriteRenderer (PNG) and fallback shapes
- Damage visual effects (smoke/fire particles)

Dependencies are injected via RenderContext.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import pygame

from pycc2.presentation.rendering.render_context import RenderContext
from pycc2.presentation.rendering.unit_visual_effects_renderer import (
    UnitVisualEffectsRenderer,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera


class UnitRenderer:
    """Handles all unit rendering operations.

    Manages:
    - Drawing units with SpriteRenderer (PNG support) or fallback shapes
    - Health-based color tinting
    - Direction indicators and movement mode overlays
    - Damage VFX (smoke/fire particles)
    - Selection highlighting
    """

    def __init__(self, ctx: RenderContext):
        self._ctx = ctx
        self._vfx_renderer = UnitVisualEffectsRenderer(ctx)
        # Glow surface cache – lazy init
        self._glow_surf_cache: pygame.Surface | None = None
        self._glow_surf_cache_size: tuple[int, int] | None = None

    def draw_units(
        self,
        units: list[Unit],
        camera: Camera,
        selected_unit_ids: set[str] | None = None,
        position_overrides: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        if self._ctx.screen is None or self._ctx.offscreen is None:
            return

        if len(units) == 0:
            return

        if self._ctx.sprite_renderer is not None:
            self._ctx.sprite_renderer._target_surface = self._ctx.offscreen
            self._ctx.sprite_renderer._draw_units(
                units, camera, selected_unit_ids, position_overrides=position_overrides
            )
            self._ctx.sprite_renderer._target_surface = None
            return
        else:
            logger.warning(
                "[EnhancedRenderer] SpriteRenderer is None! Using fallback shapes (no PNG sprites)"
            )

        screen_w, screen_h = self._ctx.screen.get_size()

        for idx, unit in enumerate(units):
            try:
                cx, cy = None, None

                if hasattr(unit, "position") and unit.position is not None:
                    # P2-04: Use smoothed (lerped) position if available
                    use_pos = unit.position.pixel_position
                    if position_overrides and hasattr(unit, "id") and unit.id in position_overrides:
                        ox, oy = position_overrides[unit.id]
                        from pycc2.domain.value_objects.vec2 import Vec2

                        use_pos = Vec2(ox, oy)

                    if hasattr(unit.position, "pixel_position"):
                        try:
                            pos = camera.world_to_screen(use_pos)
                            cx, cy = int(pos[0]), int(pos[1])
                        except (ValueError, TypeError) as e:
                            logging.debug(f"Unit pixel_position conversion failed: {e}")

                if (
                    (cx is None or cy is None)
                    and hasattr(unit, "position")
                    and unit.position is not None
                ):
                    if hasattr(unit.position, "tile_position") or hasattr(unit.position, "tile_x"):
                        try:
                            tile_x = getattr(unit.position, "tile_x", None)
                            tile_y = getattr(unit.position, "tile_y", None)
                            if tile_x is not None and tile_y is not None:
                                world_pos = Vec2(tile_x * 16, tile_y * 16)
                                pos = camera.world_to_screen(world_pos)
                                cx, cy = int(pos[0]), int(pos[1])
                        except (ValueError, TypeError) as e:
                            logging.debug(f"Unit tile_position conversion failed: {e}")

                if cx is None or cy is None:
                    grid_x = (idx % 10) * 60 + 100
                    grid_y = (idx // 10) * 60 + 100
                    cx, cy = grid_x, grid_y

                if cx < -50 or cx > screen_w + 50 or cy < -50 or cy > screen_h + 50:
                    continue

                unit_name = ""
                unit_type_str = "infantry"

                if hasattr(unit, "display_name"):
                    unit_name = str(unit.display_name)[:4]
                elif hasattr(unit, "name"):
                    unit_name = str(unit.name)[:4]
                else:
                    unit_name = f"U{idx}"

                if hasattr(unit, "unit_type"):
                    unit_type_str = str(unit.unit_type).lower()
                elif hasattr(unit, "category"):
                    unit_type_str = str(unit.category).lower()

                # P3 fix: Increased base radius from 12→24 for better visibility
                base_radius = max(32, int(32 * camera.zoom))

                get_health_tinted = self._ctx.get_health_tinted_color
                offscreen = self._ctx.offscreen

                # Determine faction color for outer ring (Allies=blue, Axis=red)
                faction_color = (100, 149, 237)  # Default cornflower blue
                if hasattr(unit, "faction"):
                    from pycc2.domain.entities.unit import Faction

                    if unit.faction == Faction.AXIS:
                        faction_color = (220, 60, 60)  # Red for Axis
                    elif unit.faction == Faction.ALLIES:
                        faction_color = (100, 149, 237)  # Blue for Allies

                # Draw faction-colored outer ring (3px wide, radius+4)
                outer_ring_radius = base_radius + 4
                pygame.draw.circle(offscreen, faction_color, (cx, cy), outer_ring_radius, 3)

                if (
                    "tank" in unit_type_str
                    or "armor" in unit_type_str
                    or "sherman" in unit_type_str
                    or "vehicle" in unit_type_str
                ):
                    color = (255, 200, 0)
                    radius = base_radius + 6
                    points = []
                    for i in range(6):
                        angle = math.pi / 3 * i
                        x = cx + int(radius * math.cos(angle))
                        y = cy + int(radius * math.sin(angle))
                        points.append((x, y))

                    color = get_health_tinted(color, unit) if get_health_tinted else color
                    pygame.draw.polygon(offscreen, color, points)
                    pygame.draw.polygon(offscreen, (255, 255, 255), points, 3)

                elif (
                    "mg" in unit_type_str
                    or "machine" in unit_type_str
                    or "at" in unit_type_str
                    or "support" in unit_type_str
                ):
                    color = (0, 220, 255)
                    radius = base_radius + 3
                    points = []
                    for i in range(3):
                        angle = math.pi / 3 * 2 * i - math.pi / 2
                        x = cx + int(radius * math.cos(angle))
                        y = cy + int(radius * math.sin(angle))
                        points.append((x, y))

                    color = get_health_tinted(color, unit) if get_health_tinted else color
                    pygame.draw.polygon(offscreen, color, points)
                    pygame.draw.polygon(offscreen, (255, 255, 255), points, 2)

                elif (
                    "sniper" in unit_type_str
                    or "recon" in unit_type_str
                    or "scout" in unit_type_str
                ):
                    color = (255, 0, 255)
                    radius = base_radius - 2
                    half = radius // 2
                    points = [
                        (cx, cy - radius),
                        (cx + half, cy),
                        (cx, cy + radius),
                        (cx - half, cy),
                    ]

                    color = get_health_tinted(color, unit) if get_health_tinted else color
                    pygame.draw.polygon(offscreen, color, points)
                    pygame.draw.polygon(offscreen, (255, 200, 255), points, 2)

                else:
                    color = (0, 255, 80)
                    radius = base_radius

                    color = get_health_tinted(color, unit) if get_health_tinted else color
                    pygame.draw.circle(offscreen, color, (cx, cy), radius)
                    pygame.draw.circle(offscreen, (255, 255, 255), (cx, cy), radius, 2)

                # P3 fix: Draw direction indicator arrow based on unit facing
                self._vfx_renderer._draw_direction_arrow(
                    offscreen, cx, cy, base_radius, unit, color
                )

                try:
                    font = pygame.font.Font(None, max(16, int(18 * camera.zoom)))
                    label_surf = font.render(unit_name, True, (255, 255, 255))
                    label_x = cx - label_surf.get_width() // 2
                    label_y = cy + radius + 3

                    bg_padding = 3
                    bg_rect = pygame.Rect(
                        label_x - bg_padding,
                        label_y - bg_padding,
                        label_surf.get_width() + 2 * bg_padding,
                        label_surf.get_height() + 2 * bg_padding,
                    )
                    pygame.draw.rect(offscreen, (0, 0, 0), bg_rect, border_radius=3)
                    pygame.draw.rect(offscreen, (100, 100, 100), bg_rect, width=1, border_radius=3)

                    offscreen.blit(label_surf, (label_x, label_y))
                except (ValueError, pygame.error) as e:
                    logging.debug(f"Unit label rendering failed: {e}")

                is_selected = selected_unit_ids and unit.id in selected_unit_ids
                if is_selected:
                    pulse = abs(math.sin(pygame.time.get_ticks() * 0.008)) * 8
                    radius + 8 + int(pulse)

                    outer_glow_radius = radius + 15 + int(pulse * 0.7)
                    glow_size = (outer_glow_radius * 2 + 10, outer_glow_radius * 2 + 10)
                    if self._glow_surf_cache is None or self._glow_surf_cache_size != glow_size:
                        self._glow_surf_cache = pygame.Surface(glow_size, pygame.SRCALPHA)
                        self._glow_surf_cache_size = glow_size
                    glow_surf = self._glow_surf_cache
                    glow_surf.fill((0, 0, 0, 0))
                    glow_center = outer_glow_radius + 5
                    pygame.draw.circle(
                        glow_surf,
                        (255, 255, 255, 40),
                        (glow_center, glow_center),
                        outer_glow_radius,
                    )
                    offscreen.blit(
                        glow_surf,
                        (cx - glow_center, cy - glow_center),
                    )

                    inner_ring_radius = radius + 5 + int(pulse)
                    pygame.draw.circle(
                        offscreen,
                        (255, 255, 0),
                        (cx, cy),
                        inner_ring_radius,
                        3,
                    )
                    pygame.draw.circle(
                        offscreen,
                        (0, 255, 255),
                        (cx, cy),
                        inner_ring_radius - 2,
                        2,
                    )

                    corner_size = 8
                    corner_offset = radius + 12 + int(pulse * 0.5)
                    corner_color = (255, 255, 0)
                    corners = [
                        (cx - corner_offset, cy - corner_offset),
                        (cx + corner_offset, cy - corner_offset),
                        (cx - corner_offset, cy + corner_offset),
                        (cx + corner_offset, cy + corner_offset),
                    ]
                    for corner_x, corner_y in corners:
                        pygame.draw.line(
                            offscreen,
                            corner_color,
                            (corner_x, corner_y),
                            (corner_x + corner_size, corner_y),
                            2,
                        )
                        pygame.draw.line(
                            offscreen,
                            corner_color,
                            (corner_x, corner_y),
                            (corner_x, corner_y + corner_size),
                            2,
                        )

                if self._ctx.draw_direction_indicator:
                    self._vfx_renderer.draw_direction_indicator(cx, cy, radius, color, unit)

                if self._ctx.draw_movement_mode_overlay:
                    self._vfx_renderer.draw_movement_mode_overlay(unit, cx, cy, radius, color)

                if hasattr(unit, "is_damaged") and unit.is_damaged:
                    self._vfx_renderer.draw_damage_vfx(unit, cx, cy)

            except (AttributeError, ValueError) as e:
                logger.warning("Failed to render unit %s: %s", idx, e)
                continue

    def draw_damage_vfx(self, unit: Unit, cx: int, cy: int) -> None:
        """Delegate to UnitVisualEffectsRenderer."""
        self._vfx_renderer.draw_damage_vfx(unit, cx, cy)

    # ------------------------------------------------------------------ #
    #  Unit Shape & Overlay Helpers
    # ------------------------------------------------------------------ #

    def draw_hexagon(
        self, cx: int, cy: int, radius: int, color: tuple[int, int, int], selected: bool = False
    ) -> None:
        """Draw a hexagon-shaped unit (mimics CC2 style)."""
        offscreen = self._ctx.offscreen
        if offscreen is None:
            return

        points = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 6
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            points.append((x, y))

        pygame.draw.polygon(offscreen, color, points)

        outline_color = (max(0, color[0] - 50), max(0, color[1] - 50), max(0, color[2] - 50))
        pygame.draw.polygon(offscreen, outline_color, points, 2)

        if selected:
            select_color = (255, 255, 0)
            pygame.draw.circle(offscreen, select_color, (cx, cy), radius + 3, 2)

    def draw_direction_indicator(
        self, cx: int, cy: int, radius: int, unit_color: tuple, unit
    ) -> None:
        """Delegate to UnitVisualEffectsRenderer."""
        self._vfx_renderer.draw_direction_indicator(cx, cy, radius, unit_color, unit)

    def draw_movement_mode_overlay(
        self, unit, cx: int, cy: int, radius: int, base_color: tuple
    ) -> None:
        """Delegate to UnitVisualEffectsRenderer."""
        self._vfx_renderer.draw_movement_mode_overlay(unit, cx, cy, radius, base_color)

    def _draw_direction_arrow(
        self,
        surface: pygame.Surface,
        cx: int,
        cy: int,
        radius: int,
        unit,
        unit_color: tuple,
    ) -> None:
        """Delegate to UnitVisualEffectsRenderer."""
        self._vfx_renderer._draw_direction_arrow(surface, cx, cy, radius, unit, unit_color)
