"""Infantry sprite generator - main public API for infantry sprite creation.

Extracted from infantry_pixel_renderer.py during Phase 2 P0-1 large file split (2026-07-04).
Contains:
  - create_infantry_sprite: 24x24 px top-down orthographic sprite
  - apply_wounded_overlay: HP-ratio-based wound effects
  - create_infantry_animation_sheet: full 8x8 direction/anim-state sprite sheet
  - _get_infantry_direction_params: 8-direction visual parameter table
  - _get_isometric_offset: 45-degree pseudo-3D direction offset (preserved, currently unused)
  - _anim_state_to_params: InfantryAnimState -> (state, frame) mapping

Cross-module imports:
  - infantry_pose_drawing._draw_infantry_prone_topdown
  - infantry_pose_drawing._draw_infantry_death_topdown
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from pycc2.domain.entities.unit import Faction
from pycc2.domain.value_objects.direction import Direction
from pycc2.presentation.rendering.infantry_pose_drawing import (
    _draw_infantry_death_topdown,
    _draw_infantry_prone_topdown,
)
from pycc2.presentation.rendering.pixel_artist_color_palette import CC2_PALETTE
from pycc2.presentation.rendering.pixel_artist_enums import InfantryAnimState, InfantryType

if TYPE_CHECKING:
    import pygame

logger = logging.getLogger(__name__)


def create_infantry_sprite(
    direction: Direction,
    faction: Faction,
    state: str = "idle",
    frame: int = 0,
    infantry_type: InfantryType | None = None,
):
    """Create an infantry sprite (24x24 px) - Pure Top-Down Orthographic.

    CC2 top-down features:
    - Helmet: circle (helmet top looks like a disc from above)
    - Body: ellipse (shoulders/back seen from above)
    - Weapon: thin line (extending in facing direction)
    - Legs: small dots (facing opposite direction, nearly invisible)
    - No face, no arms, no side-view components
    """
    import pygame

    if infantry_type is None:
        infantry_type = InfantryType.RIFLEMAN

    surface = pygame.Surface((24, 24), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))

    faction_key = faction.name.lower()
    palette = CC2_PALETTE.get(faction_key) or CC2_PALETTE.get("allies") or {}
    body_color = palette["uniform"]
    body_dark = palette["uniform_dark"]
    helmet_color = palette["helmet"]
    weapon_color = palette["weapon"]
    weapon_metal = palette["weapon_metal"]
    boots_color = palette["boots"]

    prone_states = {"crawl", "defend", "attack", "sneak", "hide"}
    is_prone = state in prone_states

    if is_prone and state != "die":
        return _draw_infantry_prone_topdown(
            surface,
            direction,
            state,
            frame,
            palette,
            infantry_type,
            body_color,
            weapon_color,
            weapon_metal,
            boots_color,
        )

    if state == "die":
        return _draw_infantry_death_topdown(
            surface,
            direction,
            frame,
            palette,
            infantry_type,
            body_color,
            helmet_color,
            weapon_color,
            boots_color,
        )

    cx, cy = 12, 12

    if state == "walk":
        walk_offsets = [0, -1, 0, 1]
        offset = walk_offsets[frame % 4]
    else:
        offset = 0

    dp = _get_infantry_direction_params(direction)

    dir_angles = {
        Direction.NORTH: 270,
        Direction.NORTHEAST: 315,
        Direction.EAST: 0,
        Direction.SOUTHEAST: 45,
        Direction.SOUTH: 90,
        Direction.SOUTHWEST: 135,
        Direction.WEST: 180,
        Direction.NORTHWEST: 225,
    }
    base_angle = math.radians(dir_angles.get(direction, 0))

    # --- Helmet: apply direction-specific size and highlight offset ---
    helmet_r = 3 + dp["helmet_size_mod"]
    hx = cx + int(math.cos(base_angle + math.pi / 2) * offset * 0.3)
    hy = cy - 2 + int(math.sin(base_angle + math.pi / 2) * offset * 0.3)
    pygame.draw.circle(surface, helmet_color, (hx, hy), helmet_r)

    hl_color = palette.get("helmet_highlight", tuple(min(255, c + 40) for c in helmet_color))
    hl_dx, hl_dy = dp["helmet_highlight_offset"]
    pygame.draw.circle(surface, hl_color, (hx + hl_dx, hy + hl_dy), 1)

    # --- Body: apply direction-specific width/height correction ---
    body_w = 8 + dp["body_width_mod"]
    body_h = 5 + dp["body_height_mod"]
    bx = cx - body_w // 2 + int(math.cos(base_angle + math.pi / 2) * offset * 0.5)
    by = cy + int(math.sin(base_angle + math.pi / 2) * offset * 0.5)
    pygame.draw.ellipse(surface, body_color, (bx, by, body_w, body_h))
    if body_w > 2 and body_h > 2:
        pygame.draw.ellipse(surface, body_dark, (bx + 1, by + 1, body_w - 2, body_h - 2))

    # --- Weapon: apply direction angle correction and hand-side difference ---
    weapon_angle_rad = base_angle + math.radians(dp["weapon_angle_mod"])
    weapon_len = 10
    wx = cx + int(math.cos(weapon_angle_rad) * weapon_len)
    wy = cy + int(math.sin(weapon_angle_rad) * weapon_len)
    weapon_width = 2 if infantry_type in [InfantryType.MG, InfantryType.AT] else 1
    pygame.draw.line(surface, weapon_color, (cx, cy), (wx, wy), weapon_width)

    # --- Equipment/backpack: only visible for rear-facing directions (S/SW) ---
    equip_color = palette.get("equipment", tuple(max(0, c - 20) for c in body_color))
    if dp["equipment_visibility"] > 0.8:
        pack_x = cx + int(math.cos(weapon_angle_rad) * (-3))
        pack_y = cy + int(math.sin(weapon_angle_rad) * (-3))
        pygame.draw.ellipse(surface, equip_color, (pack_x - 2, pack_y - 1, 4, 3))

    if infantry_type == InfantryType.MG:
        mid_x = (cx + wx) // 2
        mid_y = (cy + wy) // 2
        pygame.draw.line(surface, weapon_metal, (mid_x - 1, mid_y), (mid_x + 1, mid_y), 1)
    elif infantry_type == InfantryType.OFFICER:
        pistol_len = 5
        px = cx + int(math.cos(base_angle) * pistol_len)
        py = cy + int(math.sin(base_angle) * pistol_len)
        pygame.draw.line(surface, weapon_color, (cx, cy), (px, py), 1)
    elif infantry_type == InfantryType.MEDIC:
        red_cross = (220, 40, 40)
        perp_angle = base_angle + math.pi / 2
        rx = cx + int(math.cos(perp_angle) * 3)
        ry = cy + int(math.sin(perp_angle) * 3)
        pygame.draw.line(surface, red_cross, (rx, ry - 1), (rx, ry + 1), 1)
        pygame.draw.line(surface, red_cross, (rx - 1, ry), (rx + 1, ry), 1)

    # --- Legs: apply direction-specific leg spread ---
    leg_len = 4
    spread = dp["leg_spread_mod"]
    back_angle = base_angle + math.pi
    perp_leg = base_angle + math.pi / 2
    lx1 = cx + int(math.cos(back_angle) * leg_len) + int(math.cos(perp_leg) * spread)
    ly1 = cy + int(math.sin(back_angle) * leg_len) + int(math.sin(perp_leg) * spread)
    lx2 = cx + int(math.cos(back_angle + 0.4) * leg_len * 0.7) - int(math.cos(perp_leg) * spread)
    ly2 = cy + int(math.sin(back_angle + 0.4) * leg_len * 0.7) - int(math.sin(perp_leg) * spread)
    pygame.draw.circle(surface, boots_color, (lx1, ly1), 1)
    pygame.draw.circle(surface, boots_color, (lx2, ly2), 1)

    shadow_surface = pygame.Surface((24, 24), pygame.SRCALPHA)
    shadow_ox, shadow_oy = dp["shadow_offset"]
    pygame.draw.ellipse(
        shadow_surface, (0, 0, 0, 35), (cx - 4 + shadow_ox, cy + 5 + shadow_oy, 8, 3)
    )
    surface.blit(shadow_surface, (0, 0))

    if state == "shoot" and frame == 1:
        flash_x = wx + int(math.cos(weapon_angle_rad) * 2)
        flash_y = wy + int(math.sin(weapon_angle_rad) * 2)
        pygame.draw.ellipse(surface, (255, 255, 100), (flash_x - 2, flash_y - 1, 4, 3))

    if state == "hit":
        overlay = surface.copy()
        overlay.fill((255, 0, 0, 100))
        surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    return surface


def apply_wounded_overlay(surface, hp_ratio: float) -> pygame.Surface:
    """Apply wounded visual overlay based on HP ratio.

    HP < 50%: Red cross/bandage icon on head
    HP < 25%: Red tint overlay

    Args:
        surface: Original sprite surface.
        hp_ratio: HP ratio (0.0-1.0).

    Returns:
        Surface with wound effects applied.

    """
    import pygame

    if hp_ratio >= 0.5:
        return surface

    result = surface.copy()
    w, h = result.get_size()

    desat_alpha = int(255 * (0.3 if hp_ratio < 0.25 else 0.15))
    gray_overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    gray_overlay.fill((128, 128, 128, desat_alpha))
    result.blit(gray_overlay, (0, 0))

    if hp_ratio < 0.25:
        red_overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        red_overlay.fill((180, 0, 0, 70))
        result.blit(red_overlay, (0, 0))

    cross_x = w // 2
    cross_y = 2
    red = (220, 40, 40)
    pygame.draw.line(result, red, (cross_x, cross_y), (cross_x, cross_y + 3), 1)
    pygame.draw.line(result, red, (cross_x - 1, cross_y + 1), (cross_x + 1, cross_y + 1), 1)

    return result


def _get_infantry_direction_params(direction: Direction) -> dict:
    """Get direction-specific visual parameters for enhanced differentiation.

    Each direction has unique visual traits to distinguish adjacent directions:
    - helmet_highlight_offset: helmet highlight position shift
    - body_width_mod: body width adjustment (N/S=-2->6px, E/W=0->8px)
    - body_height_mod: body height adjustment (-2 to +1)
    - weapon_angle_mod: weapon angle correction (degrees)
    - shadow_offset: shadow offset (dx, dy)
    - visibility_factor: visibility factor (0.0-1.0)
    - helmet_size_mod: helmet size adjustment (-1 to +1)
    - leg_spread_mod: leg spread degree (0-3)
    - shoulder_tilt: shoulder tilt angle (degrees)
    - equipment_visibility: equipment visibility (0.0-1.0)
    - helmet_shape: helmet shape descriptor
    - weapon_base_angle: weapon base angle (0/45/90/135/180/225/270/315)
    """
    params = {
        Direction.NORTH: {
            "helmet_highlight_offset": (0, -2),
            "body_width_mod": -2,
            "body_height_mod": 1,
            "weapon_angle_mod": -20,
            "shadow_offset": (0, 4),
            "visibility_factor": 1.0,
            "helmet_size_mod": 1,
            "leg_spread_mod": 3,
            "shoulder_tilt": -10,
            "equipment_visibility": 0.9,
            "helmet_shape": "circle",
            "weapon_base_angle": 0,
            "description": "Front view: round helmet max visible, shoulders level, legs apart, weapon up",
        },
        Direction.NORTHEAST: {
            "helmet_highlight_offset": (2, -2),
            "body_width_mod": -1,
            "body_height_mod": 0,
            "weapon_angle_mod": -5,
            "shadow_offset": (-3, 3),
            "visibility_factor": 0.9,
            "helmet_size_mod": 0,
            "leg_spread_mod": 1,
            "shoulder_tilt": -5,
            "equipment_visibility": 0.7,
            "helmet_shape": "oval",
            "weapon_base_angle": 45,
            "description": "Right-front 45deg: body rotated, left shoulder back, right leg forward, weapon 45deg",
        },
        Direction.EAST: {
            "helmet_highlight_offset": (3, 0),
            "body_width_mod": 0,
            "body_height_mod": -1,
            "weapon_angle_mod": 15,
            "shadow_offset": (-4, 0),
            "visibility_factor": 0.8,
            "helmet_size_mod": -1,
            "leg_spread_mod": 0,
            "shoulder_tilt": 0,
            "equipment_visibility": 0.5,
            "helmet_shape": "side_oval",
            "weapon_base_angle": 90,
            "description": "Right profile: widest body, side-view helmet oval, weapon horizontal right",
        },
        Direction.SOUTHEAST: {
            "helmet_highlight_offset": (2, 2),
            "body_width_mod": -1,
            "body_height_mod": -1,
            "weapon_angle_mod": 25,
            "shadow_offset": (-3, -3),
            "visibility_factor": 0.7,
            "helmet_size_mod": -1,
            "leg_spread_mod": 1,
            "shoulder_tilt": 8,
            "equipment_visibility": 0.4,
            "helmet_shape": "oval",
            "weapon_base_angle": 135,
            "description": "Right-rear 45deg: back starting visible, right shoulder forward, weapon 135deg",
        },
        Direction.SOUTH: {
            "helmet_highlight_offset": (0, 3),
            "body_width_mod": -2,
            "body_height_mod": -2,
            "weapon_angle_mod": 35,
            "shadow_offset": (0, -4),
            "visibility_factor": 0.6,
            "helmet_size_mod": 0,
            "leg_spread_mod": 3,
            "shoulder_tilt": 12,
            "equipment_visibility": 1.0,
            "helmet_shape": "circle",
            "weapon_base_angle": 180,
            "description": "Back view: helmet/back visible, weapon over shoulder pointing down, gear fully visible",
        },
        Direction.SOUTHWEST: {
            "helmet_highlight_offset": (-2, 2),
            "body_width_mod": -1,
            "body_height_mod": -1,
            "weapon_angle_mod": 155,
            "shadow_offset": (3, -3),
            "visibility_factor": 0.7,
            "helmet_size_mod": -1,
            "leg_spread_mod": 1,
            "shoulder_tilt": 8,
            "equipment_visibility": 0.4,
            "helmet_shape": "oval",
            "weapon_base_angle": 225,
            "description": "Left-rear 45deg: SE mirror, left shoulder forward, weapon 225deg",
        },
        Direction.WEST: {
            "helmet_highlight_offset": (-3, 0),
            "body_width_mod": 0,
            "body_height_mod": -1,
            "weapon_angle_mod": 165,
            "shadow_offset": (4, 0),
            "visibility_factor": 0.8,
            "helmet_size_mod": -1,
            "leg_spread_mod": 0,
            "shoulder_tilt": 0,
            "equipment_visibility": 0.5,
            "helmet_shape": "side_oval",
            "weapon_base_angle": 270,
            "description": "Left profile: full E mirror, widest body, weapon horizontal left",
        },
        Direction.NORTHWEST: {
            "helmet_highlight_offset": (-2, -2),
            "body_width_mod": -1,
            "body_height_mod": 0,
            "weapon_angle_mod": 200,
            "shadow_offset": (3, 3),
            "visibility_factor": 0.9,
            "helmet_size_mod": 0,
            "leg_spread_mod": 1,
            "shoulder_tilt": -5,
            "equipment_visibility": 0.7,
            "helmet_shape": "oval",
            "weapon_base_angle": 315,
            "description": "Left-front 45deg: NE mirror, right shoulder back, weapon 315deg",
        },
    }
    return params.get(direction, params[Direction.NORTH])


def _get_isometric_offset(direction: Direction) -> tuple:
    """Calculate 45-degree pseudo-3D direction offset for depth effect.

    Note: Currently unused in production code paths; preserved for potential
    future isometric projection support.
    """
    offsets = {
        Direction.NORTH: (0, -2),
        Direction.NORTHEAST: (2, -1),
        Direction.EAST: (3, 0),
        Direction.SOUTHEAST: (2, 1),
        Direction.SOUTH: (0, 2),
        Direction.SOUTHWEST: (-2, 1),
        Direction.WEST: (-3, 0),
        Direction.NORTHWEST: (-2, -1),
    }
    return offsets.get(direction, (0, 0))


def _anim_state_to_params(anim_state: InfantryAnimState) -> tuple[str, int]:
    """Convert InfantryAnimState to (state, frame) params for create_infantry_sprite."""
    mapping = {
        InfantryAnimState.IDLE: ("idle", 0),
        InfantryAnimState.WALK_1: ("walk", 1),
        InfantryAnimState.WALK_2: ("walk", 3),
        InfantryAnimState.SHOOT: ("shoot", 1),
        InfantryAnimState.PRONE: ("crawl", 0),
        InfantryAnimState.DIE_1: ("die", 1),
        InfantryAnimState.DIE_2: ("die", 2),
        InfantryAnimState.DEAD: ("die", 3),
    }
    return mapping.get(anim_state, ("idle", 0))


def create_infantry_animation_sheet(
    faction: Faction,
    infantry_type: InfantryType | None = None,
):
    """Generate a full animation frame sprite sheet for infantry.

    Generates sprites for all 8 directions x all 8 animation states,
    arranged as a sprite sheet.
    Layout: row=direction (N,NE,E,SE,S,SW,W,NW), col=animation state
    Each sprite is 24x24px.

    Args:
        faction: ALLIES or AXIS.
        infantry_type: Infantry type (default RIFLEMAN).

    Returns:
        (sprite_sheet, direction_order, anim_state_order) tuple.
        sprite_sheet: pygame.Surface (192x192, 8 cols x 8 rows).
        direction_order: list of directions.
        anim_state_order: list of animation states.

    """
    import pygame

    if infantry_type is None:
        infantry_type = InfantryType.RIFLEMAN

    sprite_size = 24
    cols = 8
    rows = 8

    sheet = pygame.Surface((cols * sprite_size, rows * sprite_size), pygame.SRCALPHA)
    sheet.fill((0, 0, 0, 0))

    direction_order = [
        Direction.NORTH,
        Direction.NORTHEAST,
        Direction.EAST,
        Direction.SOUTHEAST,
        Direction.SOUTH,
        Direction.SOUTHWEST,
        Direction.WEST,
        Direction.NORTHWEST,
    ]
    anim_state_order = [
        InfantryAnimState.IDLE,
        InfantryAnimState.WALK_1,
        InfantryAnimState.WALK_2,
        InfantryAnimState.SHOOT,
        InfantryAnimState.PRONE,
        InfantryAnimState.DIE_1,
        InfantryAnimState.DIE_2,
        InfantryAnimState.DEAD,
    ]

    for row, direction in enumerate(direction_order):
        for col, anim_state in enumerate(anim_state_order):
            state, frame = _anim_state_to_params(anim_state)
            sprite = create_infantry_sprite(
                direction=direction,
                faction=faction,
                state=state,
                frame=frame,
                infantry_type=infantry_type,
            )
            sheet.blit(sprite, (col * sprite_size, row * sprite_size))

    return sheet, direction_order, anim_state_order
