"""Unit visual effects renderer.

Extracted from UnitRenderer to isolate unit overlay helpers that do not
require the full unit drawing fallback logic:
- Damage VFX (smoke / fire particles)
- Direction indicator arrow
- Movement mode overlay (fast_move, sneak, defend)

Dependencies are injected via RenderContext.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import pygame

from pycc2.presentation.rendering.render_context import RenderContext

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class UnitVisualEffectsRenderer:
    """Handles unit-specific visual overlay effects."""

    def __init__(self, ctx: RenderContext):
        """Initialize the UnitVisualEffectsRenderer."""
        self._ctx = ctx

    def draw_damage_vfx(self, unit: Unit, cx: int, cy: int) -> None:
        """Render smoke/fire particles for damaged units."""
        if not hasattr(unit, "damage_state"):
            return

        state = unit.damage_state
        if state == "undamaged":
            return

        if hasattr(unit, "update_damage_vfx"):
            if not getattr(unit, "_smoke_particles", None):
                unit.update_damage_vfx()

        get_pooled = self._ctx.get_pooled_surface
        offscreen = self._ctx.offscreen
        if get_pooled is None or offscreen is None:
            return

        smoke_particles = getattr(unit, "_smoke_particles", [])
        for particle in smoke_particles[:8]:
            px = cx + particle.get("x", 0)
            py = cy + particle.get("y", 0)
            alpha = particle.get("alpha", 100)
            size = particle.get("size", 3)

            smoke_color = (120, 120, 120)
            smoke_surf = get_pooled((size * 2, size * 2))
            pygame.draw.circle(smoke_surf, (*smoke_color, alpha), (size, size), size)
            offscreen.blit(smoke_surf, (px - size, py - size))

        fire_particles = getattr(unit, "_fire_particles", [])
        for particle in fire_particles[:6]:
            px = cx + particle.get("x", 0)
            py = cy + particle.get("y", 0)
            color = particle.get("color", (220, 120, 20))
            size = particle.get("size", 3)

            glow_size = size + 2
            glow_surf = get_pooled((glow_size * 2, glow_size * 2))
            pygame.draw.circle(glow_surf, (*color, 80), (glow_size, glow_size), glow_size)
            offscreen.blit(glow_surf, (px - glow_size, py - glow_size))

            bright_color = tuple(min(255, c + 40) for c in color)
            core_surf = get_pooled((size * 2, size * 2))
            pygame.draw.circle(core_surf, (*bright_color, 200), (size, size), size // 2 + 1)
            offscreen.blit(core_surf, (px - size, py - size))

    def draw_direction_indicator(
        self, cx: int, cy: int, radius: int, unit_color: tuple, unit
    ) -> None:
        """Draw a direction arrow on top of a unit showing facing direction."""
        offscreen = self._ctx.offscreen
        if offscreen is None:
            return

        facing = -math.pi / 2
        if hasattr(unit, "facing_direction"):
            facing = unit.facing_direction
        elif hasattr(unit, "direction"):
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
        """Draw visual overlay for movement mode states."""
        offscreen = self._ctx.offscreen
        get_pooled = self._ctx.get_pooled_surface
        if offscreen is None or get_pooled is None:
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
            trail_surf = get_pooled((trail_size, trail_size))
            trail_center = trail_size // 2

            trail_color = (*base_color[:3], 100)
            trail_radius = max(3, radius - 2)
            pygame.draw.circle(trail_surf, trail_color, (trail_center, trail_center), trail_radius)

            offscreen.blit(trail_surf, (trail_cx - trail_center, trail_cy - trail_center))

        elif movement_mode == "sneak":
            alpha_surface = get_pooled((radius * 2 + 10, radius * 2 + 10))
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
            shield_surf = get_pooled((radius * 2 + 20, radius * 2 + 20))
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

    def _draw_direction_arrow(
        self,
        surface: pygame.Surface,
        cx: int,
        cy: int,
        radius: int,
        unit,
        unit_color: tuple,
    ) -> None:
        """Draw a direction arrow showing unit facing direction.

        Reads facing from unit.position.facing_rad (PositionComponent).
        Falls back to -π/2 (up) if no facing info available.
        """
        facing = -math.pi / 2
        if hasattr(unit, "position") and hasattr(unit.position, "facing_rad"):
            facing = unit.position.facing_rad
        elif hasattr(unit, "facing_direction"):
            facing = unit.facing_direction
        elif hasattr(unit, "direction"):
            facing = unit.direction

        arrow_length = max(6, int(radius * 0.7))
        arrow_width = max(3, arrow_length // 3)

        end_x = cx + int(arrow_length * math.cos(facing))
        end_y = cy + int(arrow_length * math.sin(facing))

        brightness = sum(unit_color[:3]) / 3
        arrow_color = (40, 40, 40) if brightness > 127 else (255, 255, 255)

        pygame.draw.line(surface, arrow_color, (cx, cy), (end_x, end_y), 2)

        left_angle = facing + math.pi - (math.pi / 6)
        right_angle = facing + math.pi + (math.pi / 6)

        left_x = end_x + int(arrow_width * math.cos(left_angle))
        left_y = end_y + int(arrow_width * math.sin(left_angle))
        right_x = end_x + int(arrow_width * math.cos(right_angle))
        right_y = end_y + int(arrow_width * math.sin(right_angle))

        pygame.draw.polygon(
            surface,
            arrow_color,
            [(end_x, end_y), (left_x, left_y), (right_x, right_y)],
        )
