"""Infantry weapon drawing helpers (rifle / MG / AT / pistol / sniper / carbine / engineer / scout).

Extracted from infantry_pixel_renderer.py during Phase 2 P0-1 large file split (2026-07-04).
Each function operates on a pygame Surface passed in by the caller; stateless.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pycc2.domain.value_objects.direction import Direction
from pycc2.presentation.rendering.pixel_artist_enums import InfantryType

if TYPE_CHECKING:
    pass


def _get_weapon_position(direction: Direction, cx, cy) -> tuple:
    """Calculate weapon start/end positions based on direction.

    Args:
        direction: Facing direction.
        cx: Center x coordinate.
        cy: Center y coordinate.

    Returns:
        (start, end) tuple of (x, y) pairs.
    """
    length = 10
    angles = {
        Direction.NORTH: 270,
        Direction.NORTHEAST: 315,
        Direction.EAST: 0,
        Direction.SOUTHEAST: 45,
        Direction.SOUTH: 90,
        Direction.SOUTHWEST: 135,
        Direction.WEST: 180,
        Direction.NORTHWEST: 225,
    }
    angle_rad = math.radians(angles.get(direction, 0))

    start = (cx + math.cos(angle_rad) * 3, cy + math.sin(angle_rad) * 3)
    end = (
        cx + math.cos(angle_rad) * (3 + length),
        cy + math.sin(angle_rad) * (3 + length),
    )
    return start, end


def _draw_infantry_weapon(
    surface,
    direction,
    infantry_type,
    cx,
    cy,
    weapon_color,
    weapon_metal,
    weapon_wood,
    equip_color,
    equip_dark,
):
    """Draw differentiated weapons based on infantry type.

    Handles 8 infantry types: MG / AT / OFFICER / SNIPER / MEDIC / ENGINEER / SCOUT / default (rifleman).
    Each type has unique weapon length, width, and accessory rendering.

    Args:
        surface: pygame.Surface to draw on (modified in place).
        direction: Facing direction.
        infantry_type: InfantryType enum.
        cx: Center x coordinate.
        cy: Center y coordinate.
        weapon_color: Weapon base color.
        weapon_metal: Weapon metal accent color.
        weapon_wood: Weapon wood stock color.
        equip_color: Equipment color.
        equip_dark: Equipment dark variant.
    """
    import pygame

    weapon_start, weapon_end = _get_weapon_position(direction, cx, cy)

    if infantry_type == InfantryType.MG:
        pygame.draw.line(surface, weapon_color, weapon_start, weapon_end, 3)
        mid_x = (weapon_start[0] + weapon_end[0]) / 2
        mid_y = (weapon_start[1] + weapon_end[1]) / 2
        pygame.draw.line(
            surface, weapon_metal, (int(mid_x) - 1, int(mid_y)), (int(mid_x) + 1, int(mid_y)), 1
        )
        ammo_box_x = cx + (4 if direction.value <= 4 else -4)
        ammo_box_y = cy + 1
        pygame.draw.rect(surface, equip_color, (ammo_box_x - 2, ammo_box_y - 1, 4, 3))
        pygame.draw.rect(surface, equip_dark, (ammo_box_x - 2, ammo_box_y - 1, 4, 3), 1)
        tripod_base_x = int(weapon_end[0])
        tripod_base_y = int(weapon_end[1])
        pygame.draw.line(
            surface,
            weapon_metal,
            (tripod_base_x, tripod_base_y),
            (tripod_base_x - 2, tripod_base_y + 3),
            1,
        )
        pygame.draw.line(
            surface,
            weapon_metal,
            (tripod_base_x, tripod_base_y),
            (tripod_base_x + 2, tripod_base_y + 3),
            1,
        )

    elif infantry_type == InfantryType.AT:
        at_length = 12
        angles = {
            Direction.NORTH: 270,
            Direction.NORTHEAST: 315,
            Direction.EAST: 0,
            Direction.SOUTHEAST: 45,
            Direction.SOUTH: 90,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 180,
            Direction.NORTHWEST: 225,
        }
        angle_rad = math.radians(angles.get(direction, 0))
        at_start = (cx + math.cos(angle_rad) * 2, cy - 2 + math.sin(angle_rad) * 2)
        at_end = (
            cx + math.cos(angle_rad) * (2 + at_length),
            cy - 2 + math.sin(angle_rad) * (2 + at_length),
        )
        pygame.draw.line(surface, weapon_color, at_start, at_end, 3)
        end_x, end_y = int(at_end[0]), int(at_end[1])
        pygame.draw.circle(surface, weapon_metal, (end_x, end_y), 2)
        shoulder_x = int(at_start[0])
        shoulder_y = int(at_start[1])
        pygame.draw.line(
            surface, weapon_wood, (shoulder_x, shoulder_y), (shoulder_x, shoulder_y + 3), 1
        )

    elif infantry_type == InfantryType.OFFICER:
        pistol_length = 5
        angles = {
            Direction.NORTH: 270,
            Direction.NORTHEAST: 315,
            Direction.EAST: 0,
            Direction.SOUTHEAST: 45,
            Direction.SOUTH: 90,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 180,
            Direction.NORTHWEST: 225,
        }
        angle_rad = math.radians(angles.get(direction, 0))
        p_start = (cx + math.cos(angle_rad) * 3, cy + math.sin(angle_rad) * 3)
        p_end = (
            cx + math.cos(angle_rad) * (3 + pistol_length),
            cy + math.sin(angle_rad) * (3 + pistol_length),
        )
        pygame.draw.line(surface, weapon_color, p_start, p_end, 2)
        grip_x = int((p_start[0] + p_end[0]) / 2)
        grip_y = int((p_start[1] + p_end[1]) / 2)
        pygame.draw.line(surface, weapon_wood, (grip_x, grip_y), (grip_x, grip_y + 2), 1)

    elif infantry_type == InfantryType.SNIPER:
        sniper_length = 12
        angles = {
            Direction.NORTH: 270,
            Direction.NORTHEAST: 315,
            Direction.EAST: 0,
            Direction.SOUTHEAST: 45,
            Direction.SOUTH: 90,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 180,
            Direction.NORTHWEST: 225,
        }
        angle_rad = math.radians(angles.get(direction, 0))
        s_start = (cx + math.cos(angle_rad) * 3, cy + math.sin(angle_rad) * 3)
        s_end = (
            cx + math.cos(angle_rad) * (3 + sniper_length),
            cy + math.sin(angle_rad) * (3 + sniper_length),
        )
        pygame.draw.line(surface, weapon_color, s_start, s_end, 2)
        stock_x = int(s_start[0])
        stock_y = int(s_start[1])
        pygame.draw.line(
            surface, weapon_wood, (stock_x, stock_y), (stock_x - 1, stock_y + 2), 2
        )
        mid_x = int((s_start[0] + s_end[0]) / 2)
        mid_y = int((s_start[1] + s_end[1]) / 2)
        pygame.draw.line(surface, weapon_metal, (mid_x, mid_y), (mid_x, mid_y - 2), 1)
        pygame.draw.circle(surface, weapon_metal, (mid_x, mid_y - 2), 1)

    elif infantry_type == InfantryType.MEDIC:
        carbine_length = 7
        angles = {
            Direction.NORTH: 270,
            Direction.NORTHEAST: 315,
            Direction.EAST: 0,
            Direction.SOUTHEAST: 45,
            Direction.SOUTH: 90,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 180,
            Direction.NORTHWEST: 225,
        }
        angle_rad = math.radians(angles.get(direction, 0))
        c_start = (cx + math.cos(angle_rad) * 3, cy + math.sin(angle_rad) * 3)
        c_end = (
            cx + math.cos(angle_rad) * (3 + carbine_length),
            cy + math.sin(angle_rad) * (3 + carbine_length),
        )
        pygame.draw.line(surface, weapon_color, c_start, c_end, 2)
        stock_x = int(c_start[0])
        stock_y = int(c_start[1])
        pygame.draw.line(
            surface, weapon_wood, (stock_x, stock_y), (stock_x - 1, stock_y + 2), 1
        )

    elif infantry_type == InfantryType.ENGINEER:
        pygame.draw.line(surface, weapon_color, weapon_start, weapon_end, 2)
        stock_x = int(weapon_start[0])
        stock_y = int(weapon_start[1])
        pygame.draw.line(
            surface, weapon_wood, (stock_x, stock_y), (stock_x - 1, stock_y + 2), 2
        )
        mid_x = int((weapon_start[0] + weapon_end[0]) / 2)
        mid_y = int((weapon_start[1] + weapon_end[1]) / 2)
        pygame.draw.line(surface, weapon_metal, (mid_x - 1, mid_y), (mid_x + 1, mid_y), 1)

    elif infantry_type == InfantryType.SCOUT:
        scout_length = 6
        angles = {
            Direction.NORTH: 270,
            Direction.NORTHEAST: 315,
            Direction.EAST: 0,
            Direction.SOUTHEAST: 45,
            Direction.SOUTH: 90,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 180,
            Direction.NORTHWEST: 225,
        }
        angle_rad = math.radians(angles.get(direction, 0))
        sc_start = (cx + math.cos(angle_rad) * 3, cy + math.sin(angle_rad) * 3)
        sc_end = (
            cx + math.cos(angle_rad) * (3 + scout_length),
            cy + math.sin(angle_rad) * (3 + scout_length),
        )
        pygame.draw.line(surface, weapon_color, sc_start, sc_end, 2)
        grip_x = int((sc_start[0] + sc_end[0]) / 2)
        grip_y = int((sc_start[1] + sc_end[1]) / 2)
        pygame.draw.line(surface, weapon_wood, (grip_x, grip_y), (grip_x, grip_y + 2), 1)

    else:
        pygame.draw.line(surface, weapon_color, weapon_start, weapon_end, 2)
        stock_x = int(weapon_start[0])
        stock_y = int(weapon_start[1])
        pygame.draw.line(
            surface, weapon_wood, (stock_x, stock_y), (stock_x - 1, stock_y + 2), 2
        )
        mid_x = int((weapon_start[0] + weapon_end[0]) / 2)
        mid_y = int((weapon_start[1] + weapon_end[1]) / 2)
        pygame.draw.line(surface, weapon_metal, (mid_x - 1, mid_y), (mid_x + 1, mid_y), 1)
        pygame.draw.circle(surface, weapon_metal, (int(weapon_end[0]), int(weapon_end[1])), 1)
