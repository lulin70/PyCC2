"""
Unit Renderer Sub-Module for CC2-Style Games

Extracted from EnhancedRenderer via DELEGATE PATTERN.
Handles unit-specific rendering operations:
- Unit drawing with SpriteRenderer (PNG) and fallback shapes
- Damage visual effects (smoke/fire particles)

Dependencies are injected via parent_renderer reference.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import pygame

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera


class UnitRenderer:
    """Handles all unit rendering operations (delegate pattern).

    Manages:
    - Drawing units with SpriteRenderer (PNG support) or fallback shapes
    - Health-based color tinting
    - Direction indicators and movement mode overlays
    - Damage VFX (smoke/fire particles)
    - Selection highlighting
    """

    def __init__(self, parent_renderer):
        self._parent = parent_renderer

    def draw_units(self, units: list[Unit], camera: Camera, selected_unit_ids: set[str] | None = None) -> None:
        if self._parent._screen is None or self._parent._offscreen is None:
            return

        if len(units) == 0:
            return

        if self._parent._sprite_renderer is not None:
            self._parent._sprite_renderer._target_surface = self._parent._offscreen
            self._parent._sprite_renderer._draw_units(units, camera, selected_unit_ids)
            self._parent._sprite_renderer._target_surface = None
            return
        else:
            logger.warning("[EnhancedRenderer] SpriteRenderer is None! Using fallback shapes (no PNG sprites)")

        screen_w, screen_h = self._parent._screen.get_size()

        for idx, unit in enumerate(units):
            try:
                cx, cy = None, None

                if hasattr(unit, 'position') and unit.position is not None:
                    if hasattr(unit.position, 'pixel_position'):
                        try:
                            pos = camera.world_to_screen(unit.position.pixel_position)
                            cx, cy = int(pos[0]), int(pos[1])
                        except (ValueError, TypeError) as e:
                            logging.debug(f"Unit pixel_position conversion failed: {e}")

                if (cx is None or cy is None) and hasattr(unit, 'position') and unit.position is not None:
                    if hasattr(unit.position, 'tile_position') or hasattr(unit.position, 'tile_x'):
                        try:
                            tile_x = getattr(unit.position, 'tile_x', None)
                            tile_y = getattr(unit.position, 'tile_y', None)
                            if tile_x is not None and tile_y is not None:
                                from pycc2.domain.value_objects.vec2 import Vec2
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

                if "tank" in unit_type_str or "armor" in unit_type_str or "sherman" in unit_type_str or "vehicle" in unit_type_str:
                    color = (255, 200, 0)
                    radius = base_radius + 6
                    points = []
                    for i in range(6):
                        angle = math.pi / 3 * i
                        x = cx + int(radius * math.cos(angle))
                        y = cy + int(radius * math.sin(angle))
                        points.append((x, y))

                    color = self._parent._get_health_tinted_color(color, unit)
                    pygame.draw.polygon(self._parent._offscreen, color, points)
                    pygame.draw.polygon(self._parent._offscreen, (255, 255, 255), points, 3)

                elif "mg" in unit_type_str or "machine" in unit_type_str or "at" in unit_type_str or "support" in unit_type_str:
                    color = (0, 220, 255)
                    radius = base_radius + 3
                    points = []
                    for i in range(3):
                        angle = math.pi / 3 * 2 * i - math.pi / 2
                        x = cx + int(radius * math.cos(angle))
                        y = cy + int(radius * math.sin(angle))
                        points.append((x, y))

                    color = self._parent._get_health_tinted_color(color, unit)
                    pygame.draw.polygon(self._parent._offscreen, color, points)
                    pygame.draw.polygon(self._parent._offscreen, (255, 255, 255), points, 2)

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

                    color = self._parent._get_health_tinted_color(color, unit)
                    pygame.draw.polygon(self._parent._offscreen, color, points)
                    pygame.draw.polygon(self._parent._offscreen, (255, 200, 255), points, 2)

                else:
                    color = (0, 255, 80)
                    radius = base_radius

                    color = self._parent._get_health_tinted_color(color, unit)
                    pygame.draw.circle(self._parent._offscreen, color, (cx, cy), radius)
                    pygame.draw.circle(self._parent._offscreen, (255, 255, 255), (cx, cy), radius, 2)

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
                    pygame.draw.rect(self._parent._offscreen, (0, 0, 0), bg_rect, border_radius=3)
                    pygame.draw.rect(self._parent._offscreen, (100, 100, 100), bg_rect, width=1, border_radius=3)

                    self._parent._offscreen.blit(label_surf, (label_x, label_y))
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
                    self._parent._offscreen.blit(
                        glow_surf,
                        (cx - glow_center, cy - glow_center),
                    )

                    inner_ring_radius = radius + 5 + int(pulse)
                    pygame.draw.circle(
                        self._parent._offscreen,
                        (255, 255, 0),
                        (cx, cy),
                        inner_ring_radius,
                        3,
                    )
                    pygame.draw.circle(
                        self._parent._offscreen,
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
                            self._parent._offscreen,
                            corner_color,
                            (corner_x, corner_y),
                            (corner_x + corner_size, corner_y),
                            2,
                        )
                        pygame.draw.line(
                            self._parent._offscreen,
                            corner_color,
                            (corner_x, corner_y),
                            (corner_x, corner_y + corner_size),
                            2,
                        )

                self._parent._draw_direction_indicator(cx, cy, radius, color)

                self._parent._draw_movement_mode_overlay(unit, cx, cy, radius, color)

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

        smoke_particles = getattr(unit, '_smoke_particles', [])
        for particle in smoke_particles[:8]:
            px = cx + particle.get('x', 0)
            py = cy + particle.get('y', 0)
            alpha = particle.get('alpha', 100)
            size = particle.get('size', 3)

            smoke_color = (120, 120, 120)

            smoke_surf = self._parent._get_pooled_surface((size * 2, size * 2))
            pygame.draw.circle(smoke_surf, (*smoke_color, alpha), (size, size), size)
            self._parent._offscreen.blit(smoke_surf, (px - size, py - size))

        fire_particles = getattr(unit, '_fire_particles', [])
        for particle in fire_particles[:6]:
            px = cx + particle.get('x', 0)
            py = cy + particle.get('y', 0)
            color = particle.get('color', (220, 120, 20))
            size = particle.get('size', 3)

            glow_size = size + 2
            glow_surf = self._parent._get_pooled_surface((glow_size * 2, glow_size * 2))
            pygame.draw.circle(glow_surf, (*color, 80), (glow_size, glow_size), glow_size)
            self._parent._offscreen.blit(glow_surf, (px - glow_size, py - glow_size))

            bright_color = tuple(min(255, c + 40) for c in color)
            core_surf = self._parent._get_pooled_surface((size * 2, size * 2))
            pygame.draw.circle(core_surf, (*bright_color, 200), (size, size), size // 2 + 1)
            self._parent._offscreen.blit(core_surf, (px - size, py - size))
