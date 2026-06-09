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

from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.render_context import RenderContext

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

    def draw_units(self, units: list[Unit], camera: Camera, selected_unit_ids: set[str] | None = None,
                   position_overrides: dict[str, tuple[float, float]] | None = None) -> None:
        if self._ctx.screen is None or self._ctx.offscreen is None:
            return

        if len(units) == 0:
            return

        if self._ctx.sprite_renderer is not None:
            self._ctx.sprite_renderer._target_surface = self._ctx.offscreen
            self._ctx.sprite_renderer._draw_units(units, camera, selected_unit_ids)
            self._ctx.sprite_renderer._target_surface = None
            return
        else:
            logger.warning("[EnhancedRenderer] SpriteRenderer is None! Using fallback shapes (no PNG sprites)")

        screen_w, screen_h = self._ctx.screen.get_size()

        for idx, unit in enumerate(units):
            try:
                cx, cy = None, None

                if hasattr(unit, 'position') and unit.position is not None:
                    # P2-04: Use smoothed (lerped) position if available
                    use_pos = unit.position.pixel_position
                    if position_overrides and hasattr(unit, 'id') and unit.id in position_overrides:
                        ox, oy = position_overrides[unit.id]
                        from pycc2.domain.value_objects.vec2 import Vec2
                        use_pos = Vec2(ox, oy)

                    if hasattr(unit.position, 'pixel_position'):
                        try:
                            pos = camera.world_to_screen(use_pos)
                            cx, cy = int(pos[0]), int(pos[1])
                        except (ValueError, TypeError) as e:
                            logging.debug(f"Unit pixel_position conversion failed: {e}")

                if (cx is None or cy is None) and hasattr(unit, 'position') and unit.position is not None:
                    if hasattr(unit.position, 'tile_position') or hasattr(unit.position, 'tile_x'):
                        try:
                            tile_x = getattr(unit.position, 'tile_x', None)
                            tile_y = getattr(unit.position, 'tile_y', None)
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

                if hasattr(unit, 'display_name'):
                    unit_name = str(unit.display_name)[:4]
                elif hasattr(unit, 'name'):
                    unit_name = str(unit.name)[:4]
                else:
                    unit_name = f"U{idx}"

                if hasattr(unit, 'unit_type'):
                    unit_type_str = str(unit.unit_type).lower()
                elif hasattr(unit, 'category'):
                    unit_type_str = str(unit.category).lower()

                base_radius = max(12, int(15 * camera.zoom))

                get_health_tinted = self._ctx.get_health_tinted_color
                offscreen = self._ctx.offscreen

                if "tank" in unit_type_str or "armor" in unit_type_str or "sherman" in unit_type_str or "vehicle" in unit_type_str:
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

                elif "mg" in unit_type_str or "machine" in unit_type_str or "at" in unit_type_str or "support" in unit_type_str:
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

                elif "sniper" in unit_type_str or "recon" in unit_type_str or "scout" in unit_type_str:
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
                        label_surf.get_height() + 2 * bg_padding
                    )
                    pygame.draw.rect(offscreen, (0, 0, 0), bg_rect, border_radius=3)
                    pygame.draw.rect(offscreen, (100, 100, 100), bg_rect, width=1, border_radius=3)

                    offscreen.blit(label_surf, (label_x, label_y))
                except (ValueError, pygame.error) as e:
                    logging.debug(f"Unit label rendering failed: {e}")

                is_selected = selected_unit_ids and unit.id in selected_unit_ids
                if is_selected:
                    pulse = abs(math.sin(pygame.time.get_ticks() * 0.008)) * 8
                    select_radius = radius + 8 + int(pulse)

                    outer_glow_radius = radius + 15 + int(pulse * 0.7)
                    glow_surf = pygame.Surface(
                        (outer_glow_radius * 2 + 10, outer_glow_radius * 2 + 10),
                        pygame.SRCALPHA,
                    )
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
                    self.draw_direction_indicator(cx, cy, radius, color, unit)

                if self._ctx.draw_movement_mode_overlay:
                    self.draw_movement_mode_overlay(unit, cx, cy, radius, color)

                if hasattr(unit, 'is_damaged') and unit.is_damaged:
                    self.draw_damage_vfx(unit, cx, cy)

            except (AttributeError, ValueError) as e:
                logger.warning("Failed to render unit %s: %s", idx, e)
                continue

    def draw_damage_vfx(self, unit: Unit, cx: int, cy: int) -> None:
        if not hasattr(unit, 'damage_state'):
            return

        state = unit.damage_state
        if state == "undamaged":
            return

        if hasattr(unit, 'update_damage_vfx'):
            if not getattr(unit, '_smoke_particles', None):
                unit.update_damage_vfx()

        get_pooled = self._ctx.get_pooled_surface
        offscreen = self._ctx.offscreen

        smoke_particles = getattr(unit, '_smoke_particles', [])
        for particle in smoke_particles[:8]:
            px = cx + particle.get('x', 0)
            py = cy + particle.get('y', 0)
            alpha = particle.get('alpha', 100)
            size = particle.get('size', 3)

            smoke_color = (120, 120, 120)

            if get_pooled:
                smoke_surf = get_pooled((size * 2, size * 2))
            else:
                smoke_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(smoke_surf, (*smoke_color, alpha), (size, size), size)
            offscreen.blit(smoke_surf, (px - size, py - size))

        fire_particles = getattr(unit, '_fire_particles', [])
        for particle in fire_particles[:6]:
            px = cx + particle.get('x', 0)
            py = cy + particle.get('y', 0)
            color = particle.get('color', (220, 120, 20))
            size = particle.get('size', 3)

            glow_size = size + 2
            if get_pooled:
                glow_surf = get_pooled((glow_size * 2, glow_size * 2))
            else:
                glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*color, 80), (glow_size, glow_size), glow_size)
            offscreen.blit(glow_surf, (px - glow_size, py - glow_size))

            bright_color = tuple(min(255, c + 40) for c in color)
            if get_pooled:
                core_surf = get_pooled((size * 2, size * 2))
            else:
                core_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(core_surf, (*bright_color, 200), (size, size), size // 2 + 1)
            offscreen.blit(core_surf, (px - size, py - size))

    # ------------------------------------------------------------------ #
    #  Unit Shape & Overlay Helpers
    # ------------------------------------------------------------------ #

    def draw_hexagon(
        self, cx: int, cy: int, radius: int, color: tuple[int, int, int],
        selected: bool = False
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

        outline_color = (
            max(0, color[0] - 50),
            max(0, color[1] - 50),
            max(0, color[2] - 50)
        )
        pygame.draw.polygon(offscreen, outline_color, points, 2)

        if selected:
            select_color = (255, 255, 0)
            pygame.draw.circle(offscreen, select_color, (cx, cy), radius + 3, 2)

    def draw_direction_indicator(
        self, cx: int, cy: int, radius: int, unit_color: tuple, unit
    ) -> None:
        """Draw a direction arrow on top of unit showing facing direction.

        Arrow length = radius * 0.6, color contrasts with unit color.
        Uses unit.facing_direction or unit.direction, defaults to up (-π/2).
        """
        offscreen = self._ctx.offscreen
        if offscreen is None:
            return

        facing = -math.pi / 2
        if hasattr(unit, 'facing_direction'):
            facing = unit.facing_direction
        elif hasattr(unit, 'direction'):
            facing = unit.direction

        arrow_length = max(4, int(radius * 0.6))
        arrow_width = max(2, arrow_length // 3)

        end_x = cx + int(arrow_length * math.cos(facing))
        end_y = cy + int(arrow_length * math.sin(facing))

        brightness = sum(unit_color[:3]) / 3
        arrow_color = (0, 0, 0) if brightness > 127 else (255, 255, 255)

        pygame.draw.line(offscreen, arrow_color, (cx, cy), (end_x, end_y), 2)

        left_angle = facing + math.pi - (math.pi / 6)
        right_angle = facing + math.pi + (math.pi / 6)

        left_x = end_x + int(arrow_width * math.cos(left_angle))
        left_y = end_y + int(arrow_width * math.sin(left_angle))
        right_x = end_x + int(arrow_width * math.cos(right_angle))
        right_y = end_y + int(arrow_width * math.sin(right_angle))

        pygame.draw.polygon(
            offscreen,
            arrow_color,
            [(end_x, end_y), (left_x, left_y), (right_x, right_y)],
        )

    def draw_movement_mode_overlay(
        self, unit, cx: int, cy: int, radius: int, base_color: tuple
    ) -> None:
        """Draw visual overlay for movement mode states.

        Modes:
        - fast_move: Motion trail (semi-transparent copy offset backward)
        - sneak: Reduced opacity + edge blur effect
        - defend: Shield indicator ring or armor arc
        - normal: No overlay
        """
        offscreen = self._ctx.offscreen
        get_pooled = self._ctx.get_pooled_surface
        if offscreen is None:
            return

        movement_mode = getattr(unit, "movement_mode", "normal")

        if movement_mode == "fast_move":
            facing = -math.pi / 2
            if hasattr(unit, "facing_direction"):
                facing = unit.facing_direction
            elif hasattr(unit, "direction"):
                facing = unit.direction

            offset_dist = 3
            trail_cx = cx - int(offset_dist * math.cos(facing))
            trail_cy = cy - int(offset_dist * math.sin(facing))

            trail_size = radius * 2 + 4
            if get_pooled:
                trail_surf = get_pooled((trail_size, trail_size))
            else:
                trail_surf = pygame.Surface((trail_size, trail_size), pygame.SRCALPHA)
            trail_center = trail_size // 2

            trail_color = (*base_color[:3], 100)

            trail_radius = max(3, radius - 2)
            pygame.draw.circle(trail_surf, trail_color, (trail_center, trail_center), trail_radius)

            offscreen.blit(trail_surf, (trail_cx - trail_center, trail_cy - trail_center))

        elif movement_mode == "sneak":
            if get_pooled:
                alpha_surface = get_pooled((radius * 2 + 10, radius * 2 + 10))
            else:
                alpha_surface = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
            center = radius + 5

            sneak_color = (*base_color[:3], 140)
            pygame.draw.circle(alpha_surface, sneak_color, (center, center), radius)

            edge_alpha = 80
            for i in range(3):
                edge_r = radius + 2 + i
                edge_color = (*base_color[:3], edge_alpha - i * 20)
                pygame.draw.circle(alpha_surface, edge_color, (center, center), edge_r, 1)

            offscreen.blit(alpha_surface, (cx - center, cy - center))

        elif movement_mode == "defend":
            shield_color = (100, 200, 255, 180)
            if get_pooled:
                shield_surf = get_pooled((radius * 2 + 20, radius * 2 + 20))
            else:
                shield_surf = pygame.Surface((radius * 2 + 20, radius * 2 + 20), pygame.SRCALPHA)
            center = radius + 10

            inner_r = radius + 4
            outer_r = radius + 8

            pygame.draw.arc(
                shield_surf,
                shield_color,
                (
                    center - outer_r,
                    center - outer_r,
                    outer_r * 2,
                    outer_r * 2,
                ),
                math.pi * 0.75,
                math.pi * 2.25,
                3,
            )
            pygame.draw.arc(
                shield_surf,
                (*shield_color[:3], 120),
                (
                    center - inner_r,
                    center - inner_r,
                    inner_r * 2,
                    inner_r * 2,
                ),
                math.pi * 0.75,
                math.pi * 2.25,
                2,
            )

            offscreen.blit(shield_surf, (cx - center, cy - center))
