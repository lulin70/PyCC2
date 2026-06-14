"""
Deployment LOS Preview System — Line-of-sight visualization for deployment phase.

Extracted from deployment_ui.py God Class (v0.3.29 SRP refactoring).
Handles hit probability estimation and LOS line rendering.
"""

from __future__ import annotations

import math

import pygame

from pycc2.presentation.rendering.rendering_utils import draw_dashed_line
from pycc2.presentation.ui.deployment_models import (
    BUILDING_TERRAINS,
    TERRAIN_HEDGE,
    TERRAIN_WALL,
    TERRAIN_WOODS,
    DeploymentUnit,
)


class DeploymentLOSSystem:
    """LOS preview system for deployment phase.

    Renders dashed lines from placed units to Victory Locations,
    color-coded by estimated hit probability (4-color CC2 scheme).
    """

    _LOS_DEFAULT_RANGE = 15
    _LOS_COLOR_HIGH = (0, 200, 0, 180)  # Green: >=60%
    _LOS_COLOR_MODERATE = (200, 200, 0, 150)  # Yellow: 30-59%
    _LOS_COLOR_LOW = (255, 100, 0, 120)  # Red: 10-29%
    _LOS_COLOR_IMPOSSIBLE = (50, 50, 50, 100)  # Black: <10%

    def __init__(
        self,
        get_tile_grid=None,
        get_terrain_at=None,
        get_victory_locations=None,
        get_state=None,
        get_selected_index=None,
    ):
        self._get_tile_grid = get_tile_grid
        self._get_terrain_at = get_terrain_at
        self._get_victory_locations = get_victory_locations
        self._get_state = get_state
        self._get_selected_index = get_selected_index

    def render_los_preview(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        """Render LOS preview lines from placed/selected units to VLs."""
        if screen is None:
            return

        victory_locations = self._get_victory_locations()
        if not victory_locations:
            return

        state = self._get_state()
        selected_idx = self._get_selected_index()

        # Collect units to show LOS for
        units_to_preview: list[DeploymentUnit] = []
        for pu in state.placed_units:
            if pu.position is not None:
                units_to_preview.append(pu)

        # Also add currently selected unit if placed
        if selected_idx is not None:
            sel_unit = state.available_units[selected_idx]
            if getattr(sel_unit, "is_placed", False) and sel_unit.position is not None:
                if sel_unit not in units_to_preview:
                    units_to_preview.append(sel_unit)

        if not units_to_preview:
            return

        tile_grid = self._get_tile_grid()

        for pu in units_to_preview:
            if pu.position is None:
                continue
            src_x, src_y = pu.position
            sx = ox + src_x * ts + ts // 2
            sy = oy + src_y * ts + ts // 2

            for vl in victory_locations:
                vl_pos = vl.get("position")
                if vl_pos is None:
                    continue

                if isinstance(vl_pos, (list, tuple)) and len(vl_pos) >= 2:
                    dst_x, dst_y = int(vl_pos[0]), int(vl_pos[1])
                else:
                    continue

                dx_tiles = abs(dst_x - src_x)
                dy_tiles = abs(dst_y - src_y)
                distance = (dx_tiles * dx_tiles + dy_tiles * dy_tiles) ** 0.5

                hit_prob = self.estimate_hit_probability(
                    src_x,
                    src_y,
                    dst_x,
                    dst_y,
                    distance,
                    pu,
                    tile_grid,
                )

                line_color = self.hit_probability_to_color(hit_prob)

                dx_screen = ox + dst_x * ts + ts // 2
                dy_screen = oy + dst_y * ts + ts // 2

                draw_dashed_line(
                    screen,
                    line_color,
                    (sx, sy),
                    (dx_screen, dy_screen),
                    dash_length=4,
                    gap_length=3,
                )

                pygame.draw.circle(screen, line_color[:3], (dx_screen, dy_screen), 3)

    @staticmethod
    def estimate_hit_probability(
        src_x: int,
        src_y: int,
        dst_x: int,
        dst_y: int,
        distance: float,
        unit: DeploymentUnit,
        tile_grid=None,
        terrain_getter=None,
    ) -> float:
        """Estimate hit probability from a deployment position to a VL."""
        type_ranges = {
            "vehicle": 20,
            "support": 18,
            "recon": 16,
            "infantry": 15,
        }
        effective_range = type_ranges.get(unit.unit_type, DeploymentLOSSystem._LOS_DEFAULT_RANGE)

        if effective_range <= 0:
            return 0.0
        distance_ratio = min(distance / effective_range, 1.5)

        if distance_ratio > 1.0:
            return 0.05

        base_prob = 0.9 if distance_ratio <= 0.3 else 0.9 - 0.7 * ((distance_ratio - 0.3) / 0.7)
        base_prob = max(base_prob, 0.05)

        # Terrain blocking check
        block_penalty = 0.0
        if tile_grid is not None and terrain_getter is not None:
            steps = max(int(distance), 1)
            for step in range(1, steps):
                t = step / steps
                check_x = int(src_x + (dst_x - src_x) * t)
                check_y = int(src_y + (dst_y - src_y) * t)
                terrain = terrain_getter(check_x, check_y)

                if terrain in BUILDING_TERRAINS:
                    block_penalty += 0.3
                elif terrain == TERRAIN_WOODS:
                    block_penalty += 0.15
                elif terrain == TERRAIN_HEDGE:
                    block_penalty += 0.1
                elif terrain == TERRAIN_WALL:
                    block_penalty += 0.4

        if block_penalty >= 0.5:
            return 0.05

        hit_prob = base_prob - block_penalty
        return max(0.0, min(hit_prob, 1.0))

    @staticmethod
    def hit_probability_to_color(hit_prob: float) -> tuple[int, int, int, int]:
        """Map hit probability to LOS preview line color (4-color CC2 scheme)."""
        if hit_prob >= 0.60:
            return DeploymentLOSSystem._LOS_COLOR_HIGH
        elif hit_prob >= 0.30:
            return DeploymentLOSSystem._LOS_COLOR_MODERATE
        elif hit_prob >= 0.10:
            return DeploymentLOSSystem._LOS_COLOR_LOW
        else:
            return DeploymentLOSSystem._LOS_COLOR_IMPOSSIBLE

    @staticmethod
    def draw_arrowhead(
        surface: pygame.Surface,
        color: tuple[int, int, int],
        start: tuple[int, int],
        end: tuple[int, int],
        size: int = 8,
    ) -> None:
        """Draw an arrowhead at the end point pointing from start to end."""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1:
            return

        angle = math.atan2(dy, dx)

        p1 = (end[0], end[1])
        p2 = (
            int(end[0] - size * math.cos(angle - math.pi / 6)),
            int(end[1] - size * math.sin(angle - math.pi / 6)),
        )
        p3 = (
            int(end[0] - size * math.cos(angle + math.pi / 6)),
            int(end[1] - size * math.sin(angle + math.pi / 6)),
        )

        pygame.draw.polygon(surface, color, [p1, p2, p3])
