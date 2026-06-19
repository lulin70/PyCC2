"""
Infantry Pixel Renderer - Extracted from PixelArtist3D God Class.

Contains all infantry-related sprite generation logic:
- Infantry sprite creation (24x24 px, pure top-down orthographic)
- Direction-differentiated rendering (8 directions with unique visual params)
- Infantry type variants (rifleman, MG, AT, officer, sniper, medic, engineer, scout)
- Wounded overlay system
- Animation state management (InfantryAnimator)
- Full animation sheet generation

Public API delegates through PixelArtist3D for backward compatibility.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame

logger = logging.getLogger(__name__)

from pycc2.domain.entities.unit import Faction
from pycc2.domain.value_objects.direction import Direction
from pycc2.presentation.rendering.pixel_artist_color_palette import (
    CC2_PALETTE,
)
from pycc2.presentation.rendering.pixel_artist_enums import (
    InfantryAnimState,
    InfantryType,
)


class InfantryPixelRenderer:
    """
    Infantry sprite renderer with direction-differentiated top-down view.

    CC2 Top-Down Features:
    - Helmet: circle (top-down view of helmet dome)
    - Body: ellipse (shoulders/back from above)
    - Weapon: thin line (extending in facing direction)
    - Legs: small dots (facing opposite direction, barely visible)
    - No face, no arms, no side-view components

    Direction Differentiation System:
    - Each direction (0-7) has unique visual characteristics
    - Helmet highlight position varies by direction
    - Body width adjusts per viewing angle
    - Weapon angle clearly distinguishes each direction
    - Shadow offset enhances 3D perception
    """

    ISOMETRIC_ANGLE = 30
    PIXEL_SCALE = 1

    # ------------------------------------------------------------------ #
    #  Public infantry sprite API
    # ------------------------------------------------------------------ #

    @staticmethod
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
        palette = CC2_PALETTE.get(faction_key, CC2_PALETTE.get("allies"))
        body_color = palette["uniform"]
        body_dark = palette["uniform_dark"]
        helmet_color = palette["helmet"]
        weapon_color = palette["weapon"]
        weapon_metal = palette["weapon_metal"]
        boots_color = palette["boots"]

        prone_states = {"crawl", "defend", "attack", "sneak", "hide"}
        is_prone = state in prone_states

        if is_prone and state != "die":
            return InfantryPixelRenderer._draw_infantry_prone_topdown(
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
            return InfantryPixelRenderer._draw_infantry_death_topdown(
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

        dp = InfantryPixelRenderer._get_infantry_direction_params(direction)

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
        lx2 = (
            cx + int(math.cos(back_angle + 0.4) * leg_len * 0.7) - int(math.cos(perp_leg) * spread)
        )
        ly2 = (
            cy + int(math.sin(back_angle + 0.4) * leg_len * 0.7) - int(math.sin(perp_leg) * spread)
        )
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

    @staticmethod
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

    # ------------------------------------------------------------------ #
    #  Direction parameter system
    # ------------------------------------------------------------------ #

    @staticmethod
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

    @staticmethod
    def _get_isometric_offset(direction: Direction) -> tuple:
        """Calculate 45-degree pseudo-3D direction offset for depth effect."""
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

    @staticmethod
    def _get_weapon_position(direction, cx, cy) -> tuple:
        """Calculate weapon position based on direction."""
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

    # ------------------------------------------------------------------ #
    #  Infantry-type-specific weapon drawing
    # ------------------------------------------------------------------ #

    @staticmethod
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
        """Draw differentiated weapons based on infantry type."""
        import pygame

        weapon_start, weapon_end = InfantryPixelRenderer._get_weapon_position(direction, cx, cy)

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

    # ------------------------------------------------------------------ #
    #  Special state drawing methods
    # ------------------------------------------------------------------ #

    @staticmethod
    def _draw_infantry_prone_topdown(
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
    ):
        """Enhanced top-down prone soldier with state-specific details.
        
        States handled:
        - crawl: crawling animation with moving limbs
        - defend: stable prone firing position
        - attack: aggressive prone advance
        - sneak: low-profile infiltration
        - hide: camouflaged/ambush position
        """
        import math

        import pygame

        cx, cy = 12, 12

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
        angle = math.radians(dir_angles.get(direction, 0))
        
        # 根据状态调整参数
        if state == "crawl":
            body_len = 18
            body_w = 4
            helmet_size = 2
            weapon_offset = 6
            # 爬行动画：交替移动肘部/膝盖
            limb_offset = 2 if frame % 2 == 1 else -2
        elif state == "defend":
            body_len = 16
            body_w = 5  # 更宽 - 稳定射击姿态
            helmet_size = 3
            weapon_offset = 8  # 武器向前延伸
            limb_offset = 0  # 稳定姿态
        elif state in ["attack", "sneak"]:
            body_len = 17
            body_w = 3
            helmet_size = 2
            weapon_offset = 7
            limb_offset = 1 if frame % 2 == 1 else -1
        else:  # hide
            body_len = 15
            body_w = 4
            helmet_size = 2
            weapon_offset = 5
            limb_offset = 0
            # 隐蔽时颜色变暗
            body_color = tuple(int(c * 0.85) for c in body_color)

        # 绘制更大的阴影（卧倒时阴影更分散）
        shadow_surface = pygame.Surface((24, 24), pygame.SRCALPHA)
        shadow_width = body_len + 4
        shadow_height = body_w + 2
        shadow_x = cx - shadow_width // 2
        shadow_y = cy - shadow_height // 2
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 35), 
                          (shadow_x, shadow_y, shadow_width, shadow_height))
        surface.blit(shadow_surface, (0, 0))

        # 绘制身体（增强的椭圆形）
        body_dark = tuple(max(0, c - 25) for c in body_color)
        for i in range(body_len):
            t = i / max(body_len - 1, 1)
            # 身体中间最宽
            width_factor = 1.0 - abs(t - 0.5) * 0.4
            current_w = int(body_w * width_factor)
            
            perp_x = int(math.sin(angle) * (t - 0.5) * current_w)
            perp_y = int(-math.cos(angle) * (t - 0.5) * current_w)
            px = cx + int(math.cos(angle) * (i - body_len // 2)) + perp_x
            py = cy + int(math.sin(angle) * (i - body_len // 2)) + perp_y
            
            # 使用渐变色增加立体感
            if 0 <= px < 24 and 0 <= py < 24:
                color = body_color if i % 3 != 1 else body_dark
                surface.set_at((px, py), color)

        # 绘制钢盔（在身体前端）
        helmet_color = palette.get("helmet", (85, 85, 75))
        helmet_x = cx + int(math.cos(angle) * (body_len // 2 - 2))
        helmet_y = cy + int(math.sin(angle) * (body_len // 2 - 2))
        pygame.draw.circle(surface, helmet_color, (helmet_x, helmet_y), helmet_size)
        
        # 钢盔高光
        hl_color = tuple(min(255, c + 40) for c in helmet_color)
        hl_x = helmet_x + int(math.cos(angle - math.pi/4))
        hl_y = helmet_y + int(math.sin(angle - math.pi/4))
        if 0 <= hl_x < 24 and 0 <= hl_y < 24:
            surface.set_at((hl_x, hl_y), hl_color)

        # 绘制四肢（肘部和膝盖）
        if state == "crawl":
            # 爬行时显示弯曲的肘部
            elbow_dist = body_len // 3
            perp_angle = angle + math.pi / 2
            elbow1_x = cx + int(math.cos(angle) * elbow_dist) + int(math.cos(perp_angle) * (2 + limb_offset))
            elbow1_y = cy + int(math.sin(angle) * elbow_dist) + int(math.sin(perp_angle) * (2 + limb_offset))
            elbow2_x = cx + int(math.cos(angle) * elbow_dist) - int(math.cos(perp_angle) * (2 - limb_offset))
            elbow2_y = cy + int(math.sin(angle) * elbow_dist) - int(math.sin(perp_angle) * (2 - limb_offset))
            
            pygame.draw.circle(surface, body_dark, (elbow1_x, elbow1_y), 1)
            pygame.draw.circle(surface, body_dark, (elbow2_x, elbow2_y), 1)
            
            # 膝盖
            knee_dist = -body_len // 4
            knee1_x = cx + int(math.cos(angle) * knee_dist) + int(math.cos(perp_angle) * (2 - limb_offset))
            knee1_y = cy + int(math.sin(angle) * knee_dist) + int(math.sin(perp_angle) * (2 - limb_offset))
            knee2_x = cx + int(math.cos(angle) * knee_dist) - int(math.cos(perp_angle) * (2 + limb_offset))
            knee2_y = cy + int(math.sin(angle) * knee_dist) - int(math.sin(perp_angle) * (2 + limb_offset))
            
            pygame.draw.circle(surface, boots_color, (knee1_x, knee1_y), 1)
            pygame.draw.circle(surface, boots_color, (knee2_x, knee2_y), 1)
        
        elif state == "defend":
            # 防御姿态：双腿分开稳定
            leg_spread = 4
            perp_angle = angle + math.pi / 2
            foot1_x = cx - int(math.cos(angle) * (body_len // 3)) + int(math.cos(perp_angle) * leg_spread)
            foot1_y = cy - int(math.sin(angle) * (body_len // 3)) + int(math.sin(perp_angle) * leg_spread)
            foot2_x = cx - int(math.cos(angle) * (body_len // 3)) - int(math.cos(perp_angle) * leg_spread)
            foot2_y = cy - int(math.sin(angle) * (body_len // 3)) - int(math.sin(perp_angle) * leg_spread)
            
            pygame.draw.circle(surface, boots_color, (foot1_x, foot1_y), 1)
            pygame.draw.circle(surface, boots_color, (foot2_x, foot2_y), 1)

        # 绘制武器
        tip_x = cx + int(math.cos(angle) * (body_len // 2 + weapon_offset))
        tip_y = cy + int(math.sin(angle) * (body_len // 2 + weapon_offset))
        weapon_start_x = cx + int(math.cos(angle) * (body_len // 4))
        weapon_start_y = cy + int(math.sin(angle) * (body_len // 4))
        
        w_width = 2 if infantry_type == InfantryType.MG else 1
        pygame.draw.line(surface, weapon_color, (weapon_start_x, weapon_start_y), (tip_x, tip_y), w_width)
        
        # 机枪双脚架
        if infantry_type == InfantryType.MG:
            bipod_x = tip_x - int(math.cos(angle) * 2)
            bipod_y = tip_y - int(math.sin(angle) * 2)
            perp = angle + math.pi / 2
            pygame.draw.line(surface, weapon_metal, 
                           (bipod_x, bipod_y),
                           (bipod_x + int(math.cos(perp) * 2), bipod_y + int(math.sin(perp) * 2)), 1)
            pygame.draw.line(surface, weapon_metal,
                           (bipod_x, bipod_y),
                           (bipod_x - int(math.cos(perp) * 2), bipod_y - int(math.sin(perp) * 2)), 1)

        # 绘制装备（背包在背部可见）
        equipment_color = palette.get("equipment", tuple(max(0, c - 20) for c in body_color))
        pack_x = cx - int(math.cos(angle) * 3)
        pack_y = cy - int(math.sin(angle) * 3)
        pygame.draw.ellipse(surface, equipment_color, (pack_x - 2, pack_y - 1, 4, 3))

        return surface

    @staticmethod
    def _draw_infantry_death_topdown(
        surface,
        direction,
        frame,
        palette,
        infantry_type,
        body_color,
        helmet_color,
        weapon_color,
        boots_color,
    ):
        """Pure top-down death animation - flattened body, no weapon."""
        import math

        import pygame

        cx, cy = 12, 12

        if frame == 0:
            pygame.draw.circle(surface, helmet_color, (cx, cy - 2), 3)
            pygame.draw.ellipse(surface, body_color, (cx - 4, cy, 8, 5))
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
            angle = math.radians(dir_angles.get(direction, 0))
            wx = cx + int(math.cos(angle) * 10)
            wy = cy + int(math.sin(angle) * 10)
            pygame.draw.line(surface, weapon_color, (cx, cy), (wx, wy), 1)

        elif frame == 1:
            pygame.draw.circle(surface, helmet_color, (cx, cy - 1), 2)
            pygame.draw.ellipse(surface, body_color, (cx - 5, cy + 1, 10, 4))

        elif frame == 2:
            ground_y = cy + 6
            pygame.draw.ellipse(surface, body_color, (cx - 7, ground_y - 2, 14, 3))
            pygame.draw.circle(surface, helmet_color, (cx - 6, ground_y), 2)

        else:
            ground_y = cy + 8
            pygame.draw.ellipse(surface, body_color, (cx - 8, ground_y - 2, 16, 3))
            pygame.draw.circle(surface, helmet_color, (cx - 7, ground_y), 2)
            pygame.draw.circle(surface, (140, 20, 20), (cx + 2, ground_y), 1)

            dark_overlay = pygame.Surface((24, 24), pygame.SRCALPHA)
            dark_overlay.fill((100, 100, 100, 150))
            surface.blit(dark_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        return surface

    # ------------------------------------------------------------------ #
    #  Animation sheet generation
    # ------------------------------------------------------------------ #

    @staticmethod
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

    @staticmethod
    def create_infantry_animation_sheet(
        faction: Faction,
        infantry_type: InfantryType | None = None,
    ):
        """
        Generate a full animation frame sprite sheet for infantry.

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
                state, frame = InfantryPixelRenderer._anim_state_to_params(anim_state)
                sprite = InfantryPixelRenderer.create_infantry_sprite(
                    direction=direction,
                    faction=faction,
                    state=state,
                    frame=frame,
                    infantry_type=infantry_type,
                )
                sheet.blit(sprite, (col * sprite_size, row * sprite_size))

        return sheet, direction_order, anim_state_order


# ====================================================================== #
#  InfantryAnimator - extracted from PixelArtist3D
# ====================================================================== #


class InfantryAnimator:
    """
    Infantry animation state manager - manages frame cycling and state transitions.

    Automatically switches animation states based on unit behavior
    (move/shoot/death) and cycles walk frames at fixed intervals.
    """

    WALK_CYCLE_INTERVAL = 0.2  # Walk frame switch interval (seconds), ~5 FPS

    def __init__(self):
        self._frame: int = 0
        self._state: InfantryAnimState = InfantryAnimState.IDLE
        self._walk_timer: float = 0.0
        self._walk_cycle: list[InfantryAnimState] = [
            InfantryAnimState.WALK_1,
            InfantryAnimState.IDLE,
            InfantryAnimState.WALK_2,
            InfantryAnimState.IDLE,
        ]
        self._shoot_timer: float = 0.0
        self._shoot_duration: float = 0.15
        self._die_timer: float = 0.0
        self._die_duration: float = 0.3

    @property
    def state(self) -> InfantryAnimState:
        """Current animation state."""
        return self._state

    def update(
        self,
        dt: float,
        is_moving: bool = False,
        is_firing: bool = False,
        is_dead: bool = False,
        is_prone: bool = False,
    ) -> InfantryAnimState:
        """
        Update animation state based on unit behavior.

        Args:
            dt: Time since last update (seconds).
            is_moving: Whether the unit is moving.
            is_firing: Whether the unit is firing.
            is_dead: Whether the unit is dead.
            is_prone: Whether the unit is prone.

        Returns:
            Current InfantryAnimState.
        """
        if self._state == InfantryAnimState.DEAD:
            return self._state

        if is_dead:
            self._die_timer += dt
            if self._die_timer < self._die_duration:
                self._state = InfantryAnimState.DIE_1
            elif self._die_timer < self._die_duration * 2:
                self._state = InfantryAnimState.DIE_2
            else:
                self._state = InfantryAnimState.DEAD
            return self._state

        if is_firing:
            self._shoot_timer += dt
            self._state = InfantryAnimState.SHOOT
            if self._shoot_timer > self._shoot_duration:
                self._shoot_timer = 0.0
            return self._state
        else:
            self._shoot_timer = 0.0

        if is_prone:
            self._state = InfantryAnimState.PRONE
            return self._state

        if is_moving:
            self._walk_timer += dt
            if self._walk_timer > self.WALK_CYCLE_INTERVAL:
                self._walk_timer = 0.0
                self._frame = (self._frame + 1) % len(self._walk_cycle)
            self._state = self._walk_cycle[self._frame]
        else:
            self._walk_timer = 0.0
            self._frame = 0
            self._state = InfantryAnimState.IDLE

        return self._state

    def reset(self):
        """Reset animation state to initial values."""
        self._frame = 0
        self._state = InfantryAnimState.IDLE
        self._walk_timer = 0.0
        self._shoot_timer = 0.0
        self._die_timer = 0.0
