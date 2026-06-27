"""Isometric building renderer for CC2-style structures.

Renders buildings with visible wall sides in isometric view:
- Top diamond face (roof)
- Left wall (darker, facing away from light)
- Right wall (lighter, facing toward light)

Building types and their heights:
- House: 2 levels
- Church: 3 levels
- Barn: 2 levels

Damage states affect wall color and structural detail.
"""

# ⚠️ EXPERIMENTAL FEATURE
# CC2 uses Orthographic Top-Down projection, NOT Isometric.
# This module provides an optional isometric mode for future/modding use.
# It is NOT the primary rendering path and should not be used for CC2-fidelity work.

from __future__ import annotations

from enum import Enum

import pygame

from pycc2.presentation.rendering.isometric_tile_generator import CC2_ISOMETRIC_PALETTE
from pycc2.presentation.rendering.isometric_transform import (
    HEIGHT_SCALE,
    TILE_H,
    TILE_W,
    tile_diamond_corners,
)


class BuildingType(Enum):
    """Building type determines wall height and visual style."""

    HOUSE = "house"
    CHURCH = "church"
    BARN = "barn"
    WALL = "wall"
    GENERIC = "generic"


class DamageState(Enum):
    """Building damage state affects color and detail."""

    INTACT = "intact"
    DAMAGED = "damaged"
    DESTROYED = "destroyed"


# Default height levels per building type
BUILDING_HEIGHTS: dict[BuildingType, int] = {
    BuildingType.HOUSE: 2,
    BuildingType.CHURCH: 3,
    BuildingType.BARN: 2,
    BuildingType.WALL: 1,
    BuildingType.GENERIC: 2,
}

# Terrain IDs that correspond to buildings
_BUILDING_TERRAIN_IDS = {4, 5, 8}  # BUILDING_ENTERABLE, BUILDING_SOLID, WALL


def _damage_color_mod(state: DamageState) -> tuple[int, int, int]:
    """Return RGB offset to apply based on damage state."""
    if state == DamageState.DAMAGED:
        return (-20, -15, -10)
    if state == DamageState.DESTROYED:
        return (-40, -35, -30)
    return (0, 0, 0)


def _apply_color_mod(
    color: tuple[int, int, int], mod: tuple[int, int, int]
) -> tuple[int, int, int]:
    """Apply a color modifier, clamping to [0, 255]."""
    return (
        max(0, min(255, color[0] + mod[0])),
        max(0, min(255, color[1] + mod[1])),
        max(0, min(255, color[2] + mod[2])),
    )


def render_building(
    building_type: BuildingType = BuildingType.GENERIC,
    height_levels: int | None = None,
    damage: DamageState = DamageState.INTACT,
) -> pygame.Surface:
    """Render a building with top face and wall sides.

    Args:
        building_type: Type of building (determines default height).
        height_levels: Override for number of elevation levels.
            If None, uses the default for building_type.
        damage: Damage state affecting color.

    Returns:
        A pygame.Surface with the building (top face + walls).

    """
    if height_levels is None:
        height_levels = BUILDING_HEIGHTS.get(building_type, 2)

    extra_height = height_levels * HEIGHT_SCALE
    total_height = TILE_H + extra_height
    surface = pygame.Surface((TILE_W, total_height), pygame.SRCALPHA)

    mod = _damage_color_mod(damage)

    # Top face center Y
    top_cy = TILE_H // 2
    top_corners = tile_diamond_corners(TILE_W / 2, top_cy)
    int_top = [(int(x), int(y)) for x, y in top_corners]

    # Roof color depends on building type
    if building_type == BuildingType.CHURCH:
        roof_color = _apply_color_mod(CC2_ISOMETRIC_PALETTE["roof_gray"], mod)
    elif building_type == BuildingType.BARN:
        roof_color = _apply_color_mod(CC2_ISOMETRIC_PALETTE["roof_red"], mod)
    else:
        roof_color = _apply_color_mod(CC2_ISOMETRIC_PALETTE["roof_brown"], mod)

    # Draw roof (top diamond face)
    pygame.draw.polygon(surface, roof_color, int_top)
    roof_outline = _apply_color_mod(CC2_ISOMETRIC_PALETTE["roof_red"], mod)
    pygame.draw.polygon(surface, roof_outline, int_top, 1)

    # Left wall (darker side)
    left_wall = [
        int_top[3],  # left vertex
        int_top[2],  # bottom vertex
        (int_top[2][0], int_top[2][1] + extra_height),
        (int_top[3][0], int_top[3][1] + extra_height),
    ]
    wall_dark = _apply_color_mod(CC2_ISOMETRIC_PALETTE["wall_dark"], mod)
    wall_shadow = _apply_color_mod(CC2_ISOMETRIC_PALETTE["wall_shadow"], mod)
    pygame.draw.polygon(surface, wall_dark, left_wall)
    pygame.draw.polygon(surface, wall_shadow, left_wall, 1)

    # Right wall (lighter side)
    right_wall = [
        int_top[2],  # bottom vertex
        int_top[1],  # right vertex
        (int_top[1][0], int_top[1][1] + extra_height),
        (int_top[2][0], int_top[2][1] + extra_height),
    ]
    wall_light = _apply_color_mod(CC2_ISOMETRIC_PALETTE["wall_light"], mod)
    pygame.draw.polygon(surface, wall_light, right_wall)
    pygame.draw.polygon(surface, wall_shadow, right_wall, 1)

    # Window detail on right wall
    if height_levels >= 2 and damage != DamageState.DESTROYED:
        mid_y = (right_wall[0][1] + right_wall[3][1]) // 2
        mid_x = (right_wall[0][0] + right_wall[1][0]) // 2
        window_color = (150, 185, 215) if damage == DamageState.INTACT else (100, 100, 100)
        pygame.draw.rect(surface, window_color, (mid_x - 2, mid_y - 2, 4, 4))

    # Damage cracks on destroyed buildings
    if damage == DamageState.DESTROYED:
        cx, cy = TILE_W // 2, top_cy + extra_height // 2
        crack_color = (50, 45, 40)
        pygame.draw.line(surface, crack_color, (cx - 5, cy - 3), (cx + 3, cy + 5), 1)
        pygame.draw.line(surface, crack_color, (cx + 2, cy - 4), (cx - 4, cy + 3), 1)

    return surface


def is_building_terrain(terrain_id: int) -> bool:
    """Check if a terrain ID represents a building type."""
    return terrain_id in _BUILDING_TERRAIN_IDS


def terrain_to_building_type(terrain_id: int) -> BuildingType:
    """Map terrain ID to building type."""
    if terrain_id == 5:  # BUILDING_SOLID
        return BuildingType.WALL
    if terrain_id == 8:  # WALL
        return BuildingType.WALL
    return BuildingType.GENERIC
