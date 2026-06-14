"""
CC2-style Orthographic Top-Down Pixel Art Generator (Facade)

This module serves as the public API facade for pixel art generation.
Heavy subsystems have been extracted to dedicated modules:
- Tank sprite generation -> tank_pixel_renderer.TankPixelRenderer
- Infantry sprite generation -> infantry_pixel_renderer.InfantryPixelRenderer

Remaining in this file:
- Vehicle sprites (halftrack, jeep, AT gun, mortar team)
- Environment sprites (tree, building)
- Delegation wrappers preserving backward-compatible PixelArtist3D API
- Module-level convenience functions
"""

from __future__ import annotations

import logging
import math
import random
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Import domain value objects
from pycc2.domain.entities.unit import Faction
from pycc2.domain.value_objects.direction import (
    DIRECTION_ANGLES,
    DIRECTION_VECTORS,
    DIRECTION_VECTORS_REVERSE,
    Direction,
)
from pycc2.presentation.rendering.infantry_pixel_renderer import (
    InfantryAnimator as _InfantryAnimator,
)
from pycc2.presentation.rendering.infantry_pixel_renderer import (
    InfantryPixelRenderer,
)

# Import extracted color palettes
from pycc2.presentation.rendering.pixel_artist_color_palette import (
    CC2_PALETTE,
)

# Import extracted enums
from pycc2.presentation.rendering.pixel_artist_enums import (
    InfantryAnimState,
    InfantryType,
    TankType,
)

# Import extracted renderers
from pycc2.presentation.rendering.tank_pixel_renderer import TankPixelRenderer

if TYPE_CHECKING:
    pass


class PixelArtist3D:
    """
    CC2-style orthographic top-down pixel art generator facade.

    This class delegates to specialized renderers while maintaining
    the original public API for backward compatibility.

    Extracted subsystems:
    - TankPixelRenderer: tanks, turrets, rotation cache, faction insignia
    - InfantryPixelRenderer: infantry sprites, animation, direction params

    Remaining (in this file):
    - Halftrack, jeep, AT gun, mortar team vehicle sprites
    - Tree and building environment sprites
    """

    ISOMETRIC_ANGLE = 30
    PIXEL_SCALE = 1

    # ===== Rotation Pre-cache (delegates to TankPixelRenderer) =====
    _rotation_cache: dict[tuple, pygame.Surface] = {}
    _PRECACHE_ANGLES = [i * 15 for i in range(24)]

    # ------------------------------------------------------------------ #
    #  Rotation cache API — delegates to TankPixelRenderer
    # ------------------------------------------------------------------ #

    @classmethod
    def _get_rotated_surface(cls, base: pygame.Surface, angle: float) -> pygame.Surface:
        """Cached rotation operation. Delegates to TankPixelRenderer."""
        return TankPixelRenderer.get_rotated_surface(base, angle)

    @classmethod
    def precache_tank_rotations(cls):
        """Pre-cache common rotation angles for all tank types. Delegates to TankPixelRenderer."""
        return TankPixelRenderer.precache_tank_rotations()

    @classmethod
    def clear_rotation_cache(cls):
        """Clear rotation cache. Delegates to TankPixelRenderer."""
        return TankPixelRenderer.clear_rotation_cache()

    # ------------------------------------------------------------------ #
    #  Infantry API — delegates to InfantryPixelRenderer
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_infantry_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
        infantry_type: InfantryType | None = None,
    ):
        """Create an infantry sprite (24x24 px). Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer.create_infantry_sprite(
            direction,
            faction,
            state,
            frame,
            infantry_type,
        )

    @staticmethod
    def apply_wounded_overlay(surface, hp_ratio: float) -> pygame.Surface:
        """Apply wounded visual overlay based on HP ratio. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer.apply_wounded_overlay(surface, hp_ratio)

    @staticmethod
    def _get_direction_params(direction: Direction) -> dict:
        """Get direction-specific visual parameters. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._get_infantry_direction_params(direction)

    @staticmethod
    def _get_isometric_offset(direction: Direction) -> tuple:
        """Calculate pseudo-3D direction offset. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._get_isometric_offset(direction)

    @staticmethod
    def _get_weapon_position(direction, cx, cy) -> tuple:
        """Calculate weapon position by direction. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._get_weapon_position(direction, cx, cy)

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
        """Draw differentiated weapon by infantry type. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._draw_infantry_weapon(
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
        )

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
        """Draw prone soldier top-down. Delegates to InfantryPixelRenderer."""
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
        """Draw death animation top-down. Delegates to InfantryPixelRenderer."""
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

    @staticmethod
    def _anim_state_to_params(anim_state: InfantryAnimState) -> tuple[str, int]:
        """Convert InfantryAnimState to (state, frame). Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._anim_state_to_params(anim_state)

    @staticmethod
    def create_infantry_animation_sheet(
        faction: Faction,
        infantry_type: InfantryType | None = None,
    ):
        """Generate full animation frame sprite sheet. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer.create_infantry_animation_sheet(faction, infantry_type)

    # ------------------------------------------------------------------ #
    #  Tank API — delegates to TankPixelRenderer
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_tank_sprite(
        direction: Direction,
        faction: Faction,
        turret_direction: Direction | None = None,
        state: str = "idle",
        frame: int = 0,
        tank_type: TankType | None = None,
    ):
        """Create a tank sprite. Delegates to TankPixelRenderer."""
        return TankPixelRenderer.create_tank_sprite(
            direction,
            faction,
            turret_direction,
            state,
            frame,
            tank_type,
        )

    @staticmethod
    def create_turret_overlay(
        faction: Faction,
        turret_direction: Direction,
        tank_type: TankType | None = None,
    ):
        """Create standalone turret overlay sprite. Delegates to TankPixelRenderer."""
        return TankPixelRenderer.create_turret_overlay(faction, turret_direction, tank_type)

    @staticmethod
    def _draw_sherman_m4(surface, direction, turret_direction, state, frame, tp, cx, cy):
        """Draw Sherman M4. Delegates to TankPixelRenderer."""
        return TankPixelRenderer._draw_sherman_m4(
            surface, direction, turret_direction, state, frame, tp, cx, cy
        )

    @staticmethod
    def _draw_panther_ausfg(surface, direction, turret_direction, state, frame, tp, cx, cy):
        """Draw Panther Ausf.G. Delegates to TankPixelRenderer."""
        return TankPixelRenderer._draw_panther_ausfg(
            surface, direction, turret_direction, state, frame, tp, cx, cy
        )

    @staticmethod
    def _draw_tiger_i(surface, direction, turret_direction, state, frame, tp, cx, cy):
        """Draw Tiger I. Delegates to TankPixelRenderer."""
        return TankPixelRenderer._draw_tiger_i(
            surface, direction, turret_direction, state, frame, tp, cx, cy
        )

    @staticmethod
    def _draw_star(surface, cx, cy, radius, color):
        """Draw five-pointed star (Allied insignia). Delegates to TankPixelRenderer."""
        return TankPixelRenderer._draw_star(surface, cx, cy, radius, color)

    @staticmethod
    def _draw_iron_cross(surface, cx, cy, color):
        """Draw iron cross (Axis insignia). Delegates to TankPixelRenderer."""
        return TankPixelRenderer._draw_iron_cross(surface, cx, cy, color)

    # ================================================================== #
    #  VEHICLE SPRITES (remaining in this file — not extracted)
    # ================================================================== #

    @staticmethod
    def create_halftrack_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """Create a half-track sprite - pure top-down view.

        P2-10 Enhanced Version:
        - Enhanced track texture lines (dark lines every 2px for tread detail)
        - Prominent gun barrel (front MG mount with longer barrel)
        - Body seam lines (panel gaps and armor plate seams)
        """
        import pygame

        surface = pygame.Surface((40, 44), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        if faction == Faction.ALLIES:
            body_color = (74, 93, 35)
            dark_color = (56, 70, 26)
            track_color = (40, 45, 35)
            wheel_color = (30, 30, 30)
            cargo_color = (82, 100, 42)
        else:
            body_color = (85, 93, 80)
            dark_color = (65, 72, 62)
            track_color = (50, 55, 48)
            wheel_color = (35, 35, 35)
            cargo_color = (92, 100, 88)

        cx, cy = 20, 22

        size = 44
        temp = pygame.Surface((size, size), pygame.SRCALPHA)
        temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        body_w, body_h = 16, 28
        body_x = tcx - body_w // 2
        body_y = tcy - body_h // 2
        pygame.draw.rect(temp, body_color, (body_x, body_y, body_w, body_h), border_radius=2)

        track_w = 20
        track_h = 12
        track_x = tcx - track_w // 2
        track_y = body_y + body_h - track_h
        pygame.draw.rect(temp, track_color, (track_x, track_y, track_w, track_h))

        track_line_dark = (30, 35, 28)
        for ty in range(track_y, track_y + track_h, 2):
            pygame.draw.line(temp, track_line_dark, (track_x, ty), (track_x + track_w, ty), 1)

        track_line_fine = (35, 40, 32)
        for ty in range(track_y + 1, track_y + track_h - 1, 4):
            if ty < track_y + track_h:
                pygame.draw.line(
                    temp, track_line_fine, (track_x + 1, ty), (track_x + track_w - 1, ty), 1
                )

        track_edge_light = (55, 60, 50)
        pygame.draw.line(
            temp, track_edge_light, (track_x, track_y), (track_x, track_y + track_h), 1
        )
        pygame.draw.line(
            temp,
            track_edge_light,
            (track_x + track_w - 1, track_y),
            (track_x + track_w - 1, track_y + track_h),
            1,
        )

        wheel_radius = 3
        wheel_y = body_y + 4
        pygame.draw.circle(temp, wheel_color, (tcx - 5, wheel_y), wheel_radius)
        pygame.draw.circle(temp, dark_color, (tcx - 5, wheel_y), wheel_radius, 1)
        pygame.draw.circle(temp, wheel_color, (tcx + 5, wheel_y), wheel_radius)
        pygame.draw.circle(temp, dark_color, (tcx + 5, wheel_y), wheel_radius, 1)

        hub_color = (50, 50, 50)
        pygame.draw.circle(temp, hub_color, (tcx - 5, wheel_y), 1)
        pygame.draw.circle(temp, hub_color, (tcx + 5, wheel_y), 1)

        cargo_w = body_w - 4
        cargo_h = track_h - 2
        cargo_x = tcx - cargo_w // 2
        cargo_y = track_y + 1
        pygame.draw.rect(temp, cargo_color, (cargo_x, cargo_y, cargo_w, cargo_h), 1)

        cargo_brace = (70, 88, 36)
        pygame.draw.line(
            temp,
            cargo_brace,
            (cargo_x + 2, cargo_y + 2),
            (cargo_x + cargo_w - 2, cargo_y + cargo_h - 2),
            1,
        )
        pygame.draw.line(
            temp,
            cargo_brace,
            (cargo_x + cargo_w - 2, cargo_y + 2),
            (cargo_x + 2, cargo_y + cargo_h - 2),
            1,
        )

        mg_mount_color = (45, 45, 45)
        mg_barrel_color = (35, 35, 35)
        mg_barrel_length = 6

        pygame.draw.circle(temp, mg_mount_color, (tcx, body_y + 1), 2)

        barrel_start_y = body_y + 1
        barrel_end_y = barrel_start_y - mg_barrel_length
        pygame.draw.line(temp, mg_barrel_color, (tcx, barrel_start_y), (tcx, barrel_end_y), 2)

        muzzle_color = (25, 25, 25)
        pygame.draw.circle(temp, muzzle_color, (tcx, barrel_end_y), 2)
        pygame.draw.circle(temp, mg_barrel_color, (tcx, barrel_end_y), 2, 1)

        seam_color = tuple(max(0, c - 18) for c in dark_color)

        hood_seam_y = body_y + body_h // 3
        pygame.draw.line(
            temp, seam_color, (body_x + 1, hood_seam_y), (body_x + body_w - 1, hood_seam_y), 1
        )

        center_seam_x = tcx
        pygame.draw.line(
            temp,
            seam_color,
            (center_seam_x, body_y + 2),
            (center_seam_x, body_y + body_h - track_h - 2),
            1,
        )

        door_seam_offset = body_w // 4
        pygame.draw.line(
            temp,
            seam_color,
            (body_x + door_seam_offset, hood_seam_y + 2),
            (body_x + door_seam_offset, body_y + body_h - track_h - 2),
            1,
        )
        pygame.draw.line(
            temp,
            seam_color,
            (body_x + body_w - door_seam_offset, hood_seam_y + 2),
            (body_x + body_w - door_seam_offset, body_y + body_h - track_h - 2),
            1,
        )

        fender_y = wheel_y + wheel_radius + 1
        if fender_y < body_y + body_h:
            pygame.draw.line(temp, dark_color, (body_x, fender_y), (body_x + body_w, fender_y), 1)

        pygame.draw.rect(temp, dark_color, (body_x, body_y, body_w, body_h), 1)

        if faction == Faction.ALLIES:
            TankPixelRenderer._draw_star(temp, tcx, tcy - 2, 3, (200, 200, 200))
        else:
            TankPixelRenderer._draw_iron_cross(temp, tcx, tcy - 2, (180, 180, 180))

        angle = DIRECTION_ANGLES.get(direction, 0)
        if angle != 0:
            temp = TankPixelRenderer.get_rotated_surface(temp, angle)

        rect = temp.get_rect(center=(cx, cy))
        surface.blit(temp, rect)

        if state == "move":
            dvx, dvy = DIRECTION_VECTORS_REVERSE.get(direction, (0, 1))
            for i in range(3):
                dust_dist = 18 + i * 3
                dust_x = cx + int(dvx * dust_dist)
                dust_y = cy + int(dvy * dust_dist)
                if 0 <= dust_x < 40 and 0 <= dust_y < 44:
                    pygame.draw.circle(surface, (139, 119, 66), (dust_x, dust_y), 1 + i % 2)

        return surface

    @staticmethod
    def create_jeep_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """Create a jeep/scout car sprite - pure top-down view.

        P2-10 Enhanced Version:
        - Body seam lines (hood, door, panel gaps)
        - Enhanced windshield V-shape detail
        - Wheel hub details
        """
        import pygame

        surface = pygame.Surface((28, 20), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        if faction == Faction.ALLIES:
            body_color = (92, 107, 53)
            dark_color = (72, 84, 41)
        else:
            body_color = (96, 104, 88)
            dark_color = (76, 82, 70)

        cx, cy = 14, 10

        size = 28
        temp = pygame.Surface((size, size), pygame.SRCALPHA)
        temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        body_w, body_h = 12, 18
        body_x = tcx - body_w // 2
        body_y = tcy - body_h // 2
        pygame.draw.rect(temp, body_color, (body_x, body_y, body_w, body_h), border_radius=1)
        pygame.draw.rect(temp, dark_color, (body_x, body_y, body_w, body_h), 1)

        windshield_v_color = (60, 68, 35) if faction == Faction.ALLIES else (65, 70, 62)
        pygame.draw.line(temp, windshield_v_color, (body_x + 2, body_y + 5), (tcx, body_y + 2), 1)
        pygame.draw.line(
            temp, windshield_v_color, (tcx, body_y + 2), (body_x + body_w - 2, body_y + 5), 1
        )

        pygame.draw.line(temp, dark_color, (body_x + 3, body_y + 6), (tcx, body_y + 3), 1)
        pygame.draw.line(temp, dark_color, (tcx, body_y + 3), (body_x + body_w - 3, body_y + 6), 1)

        wheel_color = (30, 30, 30)
        wheel_offset_x = body_w // 2 + 1
        wheel_offset_y_front = 3
        wheel_offset_y_rear = body_h - 3
        for wx_off in [-wheel_offset_x, wheel_offset_x]:
            for wy_off in [wheel_offset_y_front, wheel_offset_y_rear]:
                pygame.draw.circle(temp, wheel_color, (tcx + wx_off, body_y + wy_off), 2)
                hub_color = (50, 50, 50)
                pygame.draw.circle(temp, hub_color, (tcx + wx_off, body_y + wy_off), 1)

        steering_color = (55, 55, 55)
        pygame.draw.circle(temp, steering_color, (tcx, body_y + 4), 1)

        seam_color = tuple(max(0, c - 15) for c in dark_color)

        hood_seam_y = body_y + body_h // 3
        pygame.draw.line(
            temp, seam_color, (body_x + 1, hood_seam_y), (body_x + body_w - 1, hood_seam_y), 1
        )

        door_seam_x = tcx
        pygame.draw.line(
            temp, seam_color, (door_seam_x, hood_seam_y + 2), (door_seam_x, body_y + body_h - 3), 1
        )

        rear_seam_y = body_y + int(0.75 * body_h)
        pygame.draw.line(
            temp, seam_color, (body_x + 1, rear_seam_y), (body_x + body_w - 1, rear_seam_y), 1
        )

        side_seam_offset = body_w // 4
        pygame.draw.line(
            temp,
            seam_color,
            (body_x + side_seam_offset, hood_seam_y + 1),
            (body_x + side_seam_offset, rear_seam_y - 1),
            1,
        )
        pygame.draw.line(
            temp,
            seam_color,
            (body_x + body_w - side_seam_offset, hood_seam_y + 1),
            (body_x + body_w - side_seam_offset, rear_seam_y - 1),
            1,
        )

        fender_y_front = body_y + wheel_offset_y_front + 3
        if fender_y_front < body_y + body_h:
            pygame.draw.line(
                temp, dark_color, (body_x, fender_y_front), (body_x + body_w, fender_y_front), 1
            )

        tailgate_y = body_y + body_h - 2
        pygame.draw.line(
            temp, seam_color, (body_x + 2, tailgate_y), (body_x + body_w - 2, tailgate_y), 1
        )

        angle = DIRECTION_ANGLES.get(direction, 0)
        if angle != 0:
            temp = TankPixelRenderer.get_rotated_surface(temp, angle)

        rect = temp.get_rect(center=(cx, cy))
        surface.blit(temp, rect)

        return surface

    @staticmethod
    def create_at_gun_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """Create an anti-tank gun sprite - pure top-down view."""
        import pygame

        surface = pygame.Surface((28, 20), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        body_color = (60, 65, 55)
        dark_color = (45, 50, 42)
        barrel_color = (40, 40, 40)
        shield_color = (55, 58, 52)

        cx, cy = 14, 10

        size = 28
        temp = pygame.Surface((size, size), pygame.SRCALPHA)
        temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        base_w, base_h = 6, 4
        base_x = tcx - base_w // 2
        base_y = tcy - base_h // 2
        pygame.draw.rect(temp, body_color, (base_x, base_y, base_w, base_h))
        pygame.draw.rect(temp, dark_color, (base_x, base_y, base_w, base_h), 1)

        shield_w, shield_h = 8, 4
        shield_x = tcx - shield_w // 2
        shield_y = base_y - shield_h
        pygame.draw.rect(temp, shield_color, (shield_x, shield_y, shield_w, shield_h))
        pygame.draw.rect(temp, dark_color, (shield_x, shield_y, shield_w, shield_h), 1)

        barrel_length = 14
        barrel_start_y = shield_y
        barrel_end_y = barrel_start_y - barrel_length
        pygame.draw.line(temp, barrel_color, (tcx, barrel_start_y), (tcx, barrel_end_y), 2)
        pygame.draw.circle(temp, (30, 30, 30), (tcx, barrel_end_y), 2)

        leg_length = 8
        leg_spread = 5
        pygame.draw.line(
            temp,
            dark_color,
            (tcx - 1, base_y + base_h),
            (tcx - leg_spread, base_y + base_h + leg_length),
            2,
        )
        pygame.draw.line(
            temp,
            dark_color,
            (tcx + 1, base_y + base_h),
            (tcx + leg_spread, base_y + base_h + leg_length),
            2,
        )

        angle = DIRECTION_ANGLES.get(direction, 0)
        if angle != 0:
            temp = TankPixelRenderer.get_rotated_surface(temp, angle)

        rect = temp.get_rect(center=(cx, cy))
        surface.blit(temp, rect)

        if state == "shoot" and frame == 1:
            dvx, dvy = DIRECTION_VECTORS.get(direction, (0, -1))
            flash_dist = 16
            flash_x = cx + int(dvx * flash_dist)
            flash_y = cy + int(dvy * flash_dist)
            pygame.draw.ellipse(surface, (255, 255, 100), (flash_x - 2, flash_y - 2, 4, 4))

        return surface

    @staticmethod
    def create_mortar_team_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """Create a mortar team sprite (22x20 px, with weapon and crew)."""
        import pygame

        surface = pygame.Surface((22, 20), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        palette = CC2_PALETTE["allies" if faction == Faction.ALLIES else "axis"]
        uniform_color = palette["uniform"]
        helmet_color = palette["helmet"]
        weapon_color = palette["weapon"]

        cx, cy = 11, 12

        plate_size = 4
        plate_x = cx - plate_size // 2
        plate_y = cy + 4
        pygame.draw.rect(surface, (50, 50, 50), (plate_x, plate_y, plate_size, plate_size))
        pygame.draw.rect(surface, (35, 35, 35), (plate_x, plate_y, plate_size, plate_size), 1)

        tube_length = 8
        tube_width = 2
        tube_angle = math.radians(-45)

        direction_offsets = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: 0.2,
            Direction.EAST: 0.4,
            Direction.SOUTHEAST: 0.6,
            Direction.SOUTH: 0.8,
            Direction.SOUTHWEST: -0.6,
            Direction.WEST: -0.4,
            Direction.NORTHWEST: -0.2,
        }
        tube_angle += direction_offsets.get(direction, 0)

        tube_start_x = cx
        tube_start_y = cy
        tube_end_x = tube_start_x + math.cos(tube_angle) * tube_length
        tube_end_y = tube_start_y + math.sin(tube_angle) * tube_length

        pygame.draw.line(
            surface,
            weapon_color,
            (int(tube_start_x), int(tube_start_y)),
            (int(tube_end_x), int(tube_end_y)),
            tube_width,
        )

        pygame.draw.circle(surface, (60, 60, 60), (int(tube_end_x), int(tube_end_y)), 2)

        leg1_end_x = cx - 3
        leg1_end_y = cy + 5
        leg2_end_x = cx + 3
        leg2_end_y = cy + 5
        pygame.draw.line(
            surface,
            (60, 60, 60),
            (int(tube_start_x), int(tube_start_y)),
            (leg1_end_x, leg1_end_y),
            1,
        )
        pygame.draw.line(
            surface,
            (60, 60, 60),
            (int(tube_start_x), int(tube_start_y)),
            (leg2_end_x, leg2_end_y),
            1,
        )

        crew1_x = cx - 5
        crew1_y = cy + 2
        pygame.draw.circle(surface, helmet_color, (crew1_x, crew1_y), 2)
        pygame.draw.rect(surface, uniform_color, (crew1_x - 2, crew1_y + 2, 4, 5))

        crew2_x = cx + 5
        crew2_y = cy + 3
        pygame.draw.circle(surface, helmet_color, (crew2_x, crew2_y), 2)
        pygame.draw.rect(surface, uniform_color, (crew2_x - 2, crew2_y + 2, 4, 4))

        if state == "shoot" and frame == 1:
            flash_size = 3
            pygame.draw.ellipse(
                surface,
                (255, 255, 100),
                (
                    int(tube_end_x) - flash_size // 2,
                    int(tube_end_y) - flash_size // 2,
                    flash_size,
                    flash_size,
                ),
            )

        return surface

    # ================================================================== #
    #  ENVIRONMENT SPRITES (remaining in this file — not extracted)
    # ================================================================== #

    @staticmethod
    def create_tree_sprite(variant: int = 0, size: str = "medium"):
        """Create a CC2-style multi-tone canopy tree sprite with irregular edges.

        Phase 1 Fix 0.3 + Fix 0.5 enhanced version:
        - Multi-tone canopy: 4 green layers (base/highlight/shadow/accent)
        - Irregular edges: perturbed radius +/-2px per 30 degrees
        - Light source simulation: upper-left highlight, lower-right shadow
        - Size variants: small(20x20)/medium(28x28)/large(36x36)
        """
        import pygame

        size_config = {
            "small": {"canvas": 20, "radius": 10},
            "medium": {"canvas": 28, "radius": 14},
            "large": {"canvas": 36, "radius": 18},
        }
        config = size_config.get(size, size_config["medium"])
        canvas_size = config["canvas"]
        canopy_radius = config["radius"]

        surface = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        cx, cy = canvas_size // 2, canvas_size // 2 - 1

        shadow_surface = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        shadow_offset_x, shadow_offset_y = 3, 3
        shadow_w = canopy_radius * 2 - 4
        shadow_h = canopy_radius * 1.5 - 2
        pygame.draw.ellipse(
            shadow_surface,
            (0, 0, 0, 50),
            (
                cx - shadow_w // 2 + shadow_offset_x,
                cy - shadow_h // 2 + shadow_offset_y,
                shadow_w,
                shadow_h,
            ),
        )
        surface.blit(shadow_surface, (0, 0))

        base_canopy = (34, 68, 28)
        accent_light = (45, 90, 38)
        highlight = (55, 110, 48)
        shadow_green = (22, 50, 18)
        trunk_color = (60, 40, 20)

        points = []
        num_points = 36
        rng_edge = random.Random(variant * 73 + 11)

        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            radius_perturb = canopy_radius + rng_edge.randint(-2, 2)
            px = cx + int(math.cos(angle) * radius_perturb)
            py = cy + int(math.sin(angle) * radius_perturb)
            points.append((px, py))

        if len(points) >= 3:
            pygame.draw.polygon(surface, base_canopy, points)

        pygame.draw.circle(surface, base_canopy, (cx, cy), canopy_radius - 1)

        rng_accent1 = random.Random(variant * 41 + 3)
        accent1_count = rng_accent1.randint(15, 20)
        for _ in range(accent1_count):
            angle = rng_accent1.uniform(0, 2 * math.pi)
            dist = rng_accent1.uniform(0, canopy_radius - 3)
            ax = int(cx + math.cos(angle) * dist)
            ay = int(cy + math.sin(angle) * dist)
            if 0 <= ax < canvas_size and 0 <= ay < canvas_size:
                surface.set_at((ax, ay), accent_light)

        rng_highlight = random.Random(variant * 59 + 7)
        highlight_count = rng_highlight.randint(5, 8)
        for _ in range(highlight_count):
            angle = rng_highlight.uniform(-3 * math.pi / 4, -math.pi / 4)
            dist = rng_highlight.uniform(canopy_radius * 0.2, canopy_radius * 0.6)
            hx = int(cx + math.cos(angle) * dist)
            hy = int(cy + math.sin(angle) * dist)
            if 0 <= hx < canvas_size and 0 <= hy < canvas_size:
                surface.set_at((hx, hy), highlight)

        rng_shadow = random.Random(variant * 83 + 13)
        shadow_count = rng_shadow.randint(8, 10)
        for _ in range(shadow_count):
            angle = rng_shadow.uniform(math.pi / 4, 3 * math.pi / 4)
            dist = rng_shadow.uniform(canopy_radius * 0.3, canopy_radius * 0.7)
            sx = int(cx + math.cos(angle) * dist)
            sy = int(cy + math.sin(angle) * dist)
            if 0 <= sx < canvas_size and 0 <= sy < canvas_size:
                surface.set_at((sx, sy), shadow_green)

        trunk_y = cy + canopy_radius // 3
        if 0 <= trunk_y < canvas_size:
            pygame.draw.circle(surface, trunk_color, (cx, trunk_y), 2)

        edge_color = (28, 58, 24)
        if len(points) >= 3:
            for i in range(len(points)):
                p1 = points[i]
                p2 = points[(i + 1) % len(points)]
                pygame.draw.line(surface, edge_color, p1, p2, 1)

        return surface

    @staticmethod
    def create_building_sprite(building_type: str = "house", variant: int = 0):
        """Create a CC2-style building sprite (32x32 px).

        Supports multiple building types with visual differentiation:
        - house: residential building with roof detail
        - factory: industrial building with chimney/smoke
        - bunker: fortified concrete structure
        """
        import pygame

        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        cx, cy = 16, 16

        if building_type == "house":
            wall_color = (140, 120, 95)
            roof_color = (110, 75, 50)
            dark_color = (100, 85, 68)

            wall_w, wall_h = 20, 16
            wall_x = cx - wall_w // 2
            wall_y = cy - wall_h // 2
            pygame.draw.rect(surface, wall_color, (wall_x, wall_y, wall_w, wall_h))
            pygame.draw.rect(surface, dark_color, (wall_x, wall_y, wall_w, wall_h), 1)

            roof_points = [
                (wall_x - 2, wall_y + 2),
                (cx, wall_y - 6),
                (wall_x + wall_w + 2, wall_y + 2),
            ]
            pygame.draw.polygon(surface, roof_color, roof_points)
            pygame.draw.polygon(surface, dark_color, roof_points, 1)

            door_w, door_h = 4, 6
            door_x = cx - door_w // 2
            door_y = wall_y + wall_h - door_h
            pygame.draw.rect(surface, (80, 55, 35), (door_x, door_y, door_w, door_h))

            for win_y in [wall_y + 3, wall_y + wall_h - 8]:
                for win_x_off in [-6, 6]:
                    win_x = cx + win_x_off
                    pygame.draw.rect(surface, (180, 200, 220), (win_x, win_y, 4, 4))
                    pygame.draw.rect(surface, dark_color, (win_x, win_y, 4, 4), 1)

                    cross_x = win_x + 2
                    cross_y = win_y + 2
                    pygame.draw.line(
                        surface, dark_color, (cross_x, cross_y - 1), (cross_x, cross_y + 1), 1
                    )
                    pygame.draw.line(
                        surface, dark_color, (cross_x - 1, cross_y), (cross_x + 1, cross_y), 1
                    )

        elif building_type == "factory":
            wall_color = (120, 115, 105)
            roof_color = (85, 80, 75)
            dark_color = (90, 85, 78)

            wall_w, wall_h = 24, 14
            wall_x = cx - wall_w // 2
            wall_y = cy - wall_h // 2 + 2
            pygame.draw.rect(surface, wall_color, (wall_x, wall_y, wall_w, wall_h))
            pygame.draw.rect(surface, dark_color, (wall_x, wall_y, wall_w, wall_h), 1)

            pygame.draw.rect(surface, roof_color, (wall_x, wall_y - 3, wall_w, 3))
            pygame.draw.line(surface, dark_color, (wall_x, wall_y), (wall_x + wall_w, wall_y), 1)

            chimney_x = cx + 6
            chimney_y = wall_y - 8
            pygame.draw.rect(surface, (70, 65, 60), (chimney_x, chimney_y, 4, 6))
            pygame.draw.rect(surface, dark_color, (chimney_x, chimney_y, 4, 6), 1)

            smoke_rng = random.Random(variant + 42)
            for i in range(3):
                smoke_r = 2 + i
                smoke_x = chimney_x + 2 + smoke_rng.randint(-2, 2)
                smoke_y = chimney_y - 3 - i * 3
                smoke_alpha = max(20, 80 - i * 25)
                smoke_surf = pygame.Surface((smoke_r * 2, smoke_r * 2), pygame.SRCALPHA)
                smoke_surf.fill((0, 0, 0, 0))
                pygame.draw.circle(
                    smoke_surf, (180, 180, 175, smoke_alpha), (smoke_r, smoke_r), smoke_r
                )
                surface.blit(smoke_surf, (smoke_x - smoke_r, smoke_y - smoke_r))

            for bx in range(wall_x + 2, wall_x + wall_w - 2, 6):
                pygame.draw.rect(surface, (150, 155, 140), (bx, wall_y + 3, 4, 5))
                pygame.draw.line(surface, dark_color, (bx, wall_y + 3), (bx, wall_y + 8), 1)
                pygame.draw.line(surface, dark_color, (bx + 4, wall_y + 3), (bx + 4, wall_y + 8), 1)
                pygame.draw.line(surface, dark_color, (bx, wall_y + 5), (bx + 4, wall_y + 5), 1)

        elif building_type == "bunker":
            wall_color = (130, 125, 118)
            dark_color = (95, 90, 83)

            bunker_w, bunker_h = 22, 18
            bunker_x = cx - bunker_w // 2
            bunker_y = cy - bunker_h // 2
            pygame.draw.rect(
                surface, wall_color, (bunker_x, bunker_y, bunker_w, bunker_h), border_radius=2
            )
            pygame.draw.rect(surface, dark_color, (bunker_x, bunker_y, bunker_w, bunker_h), 2)

            bagstone_rng = random.Random(variant + 99)
            for _ in range(15):
                sx = bagstone_rng.randint(bunker_x + 2, bunker_x + bunker_w - 3)
                sy = bagstone_rng.randint(bunker_y + 2, bunker_y + bunker_h - 3)
                stone_dark = tuple(max(0, c - 20) for c in wall_color)
                pygame.draw.circle(surface, stone_dark, (sx, sy), 1)

            emplacement_w, emplacement_h = 10, 6
            emp_x = cx - emplacement_w // 2
            emp_y = bunker_y + bunker_h - emplacement_h - 2
            emp_inner_color = (50, 48, 45)
            pygame.draw.rect(surface, emp_inner_color, (emp_x, emp_y, emplacement_w, emplacement_h))
            pygame.draw.rect(surface, dark_color, (emp_x, emp_y, emplacement_w, emplacement_h), 1)

            sandbag_y = emp_y - 2
            for sb_x in range(emp_x - 1, emp_x + emplacement_w + 1, 3):
                sb_color = (150, 140, 115)
                pygame.draw.rect(surface, sb_color, (sb_x, sandbag_y, 3, 2))
                pygame.draw.rect(surface, dark_color, (sb_x, sandbag_y, 3, 2), 1)

        else:
            wall_color = (128, 128, 128)
            dark_color = (96, 96, 96)
            pygame.draw.rect(surface, wall_color, (cx - 10, cy - 8, 20, 16))
            pygame.draw.rect(surface, dark_color, (cx - 10, cy - 8, 20, 16), 1)

        shadow_surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 40), (cx - 12, cy + 10, 24, 6))
        surface.blit(shadow_surface, (0, 0))

        return surface


# Re-export InfantryAnimator from its new home for backward compatibility
InfantryAnimator = _InfantryAnimator


# ====================================================================== #
#  Module-level convenience functions (unchanged API)
# ====================================================================== #


def create_cc2_infantry_sprite(
    direction: int,
    faction: str = "allies",
    state: str = "idle",
    frame: int = 0,
    infantry_type: str = "rifleman",
):
    """
    Convenience function: create a CC2-style infantry sprite.

    Args:
        direction: 0-7 (N, NE, E, SE, S, SW, W, NW)
        faction: "allies" or "axis"
        state: idle/walk/shoot/die/hit
        frame: Animation frame number
        infantry_type: rifleman/mg/at/officer/sniper/medic/engineer/scout

    Returns:
        pygame.Surface (24x24)
    """
    dir_enum = list(Direction)[direction % 8]
    faction_enum = Faction.ALLIES if faction == "allies" else Faction.AXIS
    type_map = {t.value: t for t in InfantryType}
    type_enum = type_map.get(infantry_type, InfantryType.RIFLEMAN)
    return InfantryPixelRenderer.create_infantry_sprite(
        dir_enum, faction_enum, state, frame, type_enum
    )


def create_cc2_tank_sprite(
    direction: int,
    faction: str = "allies",
    turret_direction: int | None = None,
    state: str = "idle",
    frame: int = 0,
):
    """
    Convenience function: create a CC2-style tank sprite.

    Args:
        direction: Hull facing 0-7
        faction: "allies" or "axis"
        turret_direction: Turret facing 0-7 (optional)
        state: idle/move/shoot
        frame: Animation frame number

    Returns:
        pygame.Surface (36x36)
    """
    dir_enum = list(Direction)[direction % 8]
    faction_enum = Faction.ALLIES if faction == "allies" else Faction.AXIS
    turret_enum = list(Direction)[turret_direction % 8] if turret_direction is not None else None
    return TankPixelRenderer.create_tank_sprite(dir_enum, faction_enum, turret_enum, state, frame)


if __name__ == "__main__":
    import pygame

    pygame.init()

    logger.info("CC2 45° Isometric Pixel Artist - Test Generation")
    logger.info("=" * 50)

    test_surface = pygame.Surface((400, 300), pygame.SRCALPHA)
    test_surface.fill((40, 80, 28))

    directions = list(Direction)
    for i, direction in enumerate(directions):
        sprite = PixelArtist3D.create_infantry_sprite(
            direction=direction,
            faction=Faction.ALLIES,
            state="idle",
            frame=0,
        )
        x = (i % 4) * 90 + 20
        y = (i // 4) * 100 + 20
        test_surface.blit(sprite, (x, y))

        font = pygame.font.Font(None, 16)
        text = font.render(direction.name[:2], True, (240, 220, 40))
        test_surface.blit(text, (x + 6, y + 26))

    tank_sprite = PixelArtist3D.create_tank_sprite(
        direction=Direction.SOUTH,
        faction=Faction.ALLIES,
        state="idle",
    )
    test_surface.blit(tank_sprite, (320, 200))

    tree_sprite = PixelArtist3D.create_tree_sprite(variant=0)
    test_surface.blit(tree_sprite, (350, 240))

    building_sprite = PixelArtist3D.create_building_sprite(building_type="house")
    test_surface.blit(building_sprite, (180, 200))

    import tempfile as _tf

    _preview_path = str(_tf.gettempdir() / "cc2_style_preview.png")
    pygame.image.save(test_surface, _preview_path)
    logger.info("Preview saved to %s", _preview_path)
    logger.info("   Generated %d infantry sprites + tank + tree + building", len(directions))

    pygame.quit()
