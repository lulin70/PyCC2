"""Vehicle Pixel Renderer - Extracted from PixelArtist3D God Class (P3-3).

Contains non-tank vehicle sprite generation logic:
- Halftrack (M3 Half-track, Allied/Axis variants)
- Jeep (scout car with windshield V-detail)
- AT gun (anti-tank gun with shield and trails)
- Mortar team (weapon + 2 crew)

Public API delegates through PixelArtist3D for backward compatibility.
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

from pycc2.domain.entities.unit import Faction
from pycc2.domain.value_objects.direction import (
    DIRECTION_ANGLES,
    DIRECTION_VECTORS,
    DIRECTION_VECTORS_REVERSE,
    Direction,
)
from pycc2.presentation.rendering.pixel_artist_color_palette import (
    CC2_PALETTE,
)
from pycc2.presentation.rendering.tank_pixel_renderer import TankPixelRenderer


class VehiclePixelRenderer:
    """Vehicle sprite renderer for non-tank units.

    Generates top-down sprites for support vehicles and towed weapons:
    - Halftrack: 40x44px, tracked cargo vehicle with MG mount
    - Jeep: 28x20px, light scout car with V-windshield
    - AT gun: 28x20px, anti-tank gun with split trails
    - Mortar team: 22x20px, mortar tube + 2 crew figures

    Uses TankPixelRenderer for faction insignia (star/iron cross) and
    rotation caching to ensure consistent visual style across unit types.
    """

    # ================================================================== #
    #  VEHICLE SPRITES
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
