"""
Tank Pixel Renderer - Extracted from PixelArtist3D God Class.

Contains all tank-related sprite generation logic:
- Rotation pre-cache system (P0-4)
- Tank sprite creation (Sherman M4, Panther Ausf.G, Tiger I)
- Turret overlay rendering
- Faction insignia helpers (star / iron cross)

Public API delegates through PixelArtist3D for backward compatibility.
"""

from __future__ import annotations

import logging
import math
import random
from typing import Dict

logger = logging.getLogger(__name__)

from pycc2.domain.value_objects.direction import Direction
from pycc2.domain.entities.unit import Faction
from pycc2.presentation.rendering.pixel_artist_enums import (
    InfantryAnimState,
    InfantryType,
    TankType,
)
from pycc2.presentation.rendering.pixel_artist_color_palette import (
    CC2_PALETTE,
    TANK_PALETTES,
    TANK_SIZES,
)


class TankPixelRenderer:
    """
    Tank sprite renderer with rotation pre-cache system.

    Supports three WWII Normandy campaign tank types:
    - Sherman M4 (US medium): 36x36px, rounded hull, small turret, VVSS suspension
    - Panther Ausf.G (German medium-heavy): 38x38px, sloped armor, long L/70 gun, interleaved wheels
    - Tiger I (German super-heavy): 44x44px, boxy hull, large rectangular turret, 88mm KwK36

    Rotation Pre-cache System (P0-4):
    - All pygame.transform.rotate() results cached in _rotation_cache
    - Cache key: (surface_id, angle_rounded)
    - Pre-cached angles: every 15 degrees, 24 directions total
    - Avoids micro-stutter from real-time rotation in large-unit scenes
    """

    ISOMETRIC_ANGLE = 30
    PIXEL_SCALE = 1

    # ===== Rotation Pre-cache (P0-4) =====
    _rotation_cache: Dict[tuple, 'pygame.Surface'] = {}
    _PRECACHE_ANGLES = [i * 15 for i in range(24)]  # 0, 15, 30, ..., 345

    # ------------------------------------------------------------------ #
    #  Rotation cache API
    # ------------------------------------------------------------------ #

    @classmethod
    def get_rotated_surface(cls, base: 'pygame.Surface', angle: float) -> 'pygame.Surface':
        """Cached rotation operation to avoid redundant computation.

        Args:
            base: Original surface (unrotated reference image).
            angle: Rotation angle in degrees.

        Returns:
            Rotated surface (from cache or newly computed).
        """
        cache_key = (base.get_width(), base.get_height(), round(angle, 1))
        if cache_key not in cls._rotation_cache:
            import pygame
            cls._rotation_cache[cache_key] = pygame.transform.rotate(base, angle)
        return cls._rotation_cache[cache_key]

    @classmethod
    def precache_tank_rotations(cls):
        """Pre-cache common rotation angles for all tank types.

        Call once during game initialization to generate 24-direction
        rotation results ahead of time.
        """
        import pygame
        from pycc2.presentation.rendering.pixel_artist_enums import TankType
        from pycc2.presentation.rendering.pixel_artist_color_palette import TANK_PALETTES, TANK_SIZES

        for tank_type in TankType:
            tank_w, tank_h = TANK_SIZES[tank_type]
            size = max(tank_w, tank_h)

            dummy = pygame.Surface((size, size), pygame.SRCALPHA)
            dummy.fill((0, 0, 0, 0))

            for angle in cls._PRECACHE_ANGLES:
                if angle != 0:
                    cls.get_rotated_surface(dummy, angle)

    @classmethod
    def clear_rotation_cache(cls):
        """Clear the rotation cache. Call when switching levels or releasing bulk resources."""
        cls._rotation_cache.clear()

    # ------------------------------------------------------------------ #
    #  Public tank sprite API
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
        """Create a tank sprite - historically accurate version with size differentiation.

        Supports three main WWII Normandy tanks:
        - Sherman M4 (US medium): 36x36px, rounded hull, small turret, VVSS suspension
        - Panther Ausf.G (German medium-heavy): 38x38px, sloped armor, long L/70, Schurzen
        - Tiger I (German super-heavy): 44x44px, boxy hull, large rect turret, 88mm KwK36

        Args:
            direction: Hull facing direction.
            faction: ALLIES or AXIS.
            turret_direction: Turret facing direction (defaults to same as hull).
            state: idle/move/shoot/die.
            frame: Animation frame number.
            tank_type: Tank type (auto-selected by faction if None).

        Returns:
            pygame.Surface with alpha channel (size varies by tank_type).
        """
        import pygame

        if turret_direction is None:
            turret_direction = direction

        if tank_type is None:
            tank_type = TankType.SHERMAN_M4 if faction == Faction.ALLIES else TankType.PANTHER_AUSFG

        tank_w, tank_h = TANK_SIZES[tank_type]

        surface = pygame.Surface((tank_w, tank_h), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        tp = TANK_PALETTES[tank_type]

        cx, cy = tank_w // 2, tank_h // 2

        if tank_type == TankType.SHERMAN_M4:
            TankPixelRenderer._draw_sherman_m4(surface, direction, turret_direction, state, frame, tp, cx, cy)
        elif tank_type == TankType.PANTHER_AUSFG:
            TankPixelRenderer._draw_panther_ausfg(surface, direction, turret_direction, state, frame, tp, cx, cy)
        elif tank_type == TankType.TIGER_I:
            TankPixelRenderer._draw_tiger_i(surface, direction, turret_direction, state, frame, tp, cx, cy)

        return surface

    @staticmethod
    def create_turret_overlay(
        faction: Faction,
        turret_direction: Direction,
        tank_type: TankType | None = None,
    ):
        """Create a standalone turret overlay sprite - pure top-down view.

        Turret is drawn facing north, then rotated per turret_direction.

        Args:
            faction: ALLIES or AXIS.
            turret_direction: Turret facing direction.
            tank_type: Tank type.

        Returns:
            pygame.Surface with alpha channel (size varies by tank_type).
        """
        import pygame

        if tank_type is None:
            tank_type = TankType.SHERMAN_M4 if faction == Faction.ALLIES else TankType.PANTHER_AUSFG

        tank_w, tank_h = TANK_SIZES[tank_type]
        tp = TANK_PALETTES[tank_type]

        overlay_size = max(tank_w, tank_h)
        surface = pygame.Surface((overlay_size, overlay_size), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        cx, cy = overlay_size // 2, overlay_size // 2

        if tank_type == TankType.SHERMAN_M4:
            tw, th = 12, 10
            tx = cx - tw // 2
            ty = cy - th // 2
            pygame.draw.rect(surface, tp['turret_base'], (tx, ty, tw, th), border_radius=3)
            pygame.draw.ellipse(surface, tp['turret_dark'], (tx + 2, ty + 2, tw - 4, th - 4))
            pygame.draw.circle(surface, tp['cupola'], (cx + 2, cy), 2)
            pygame.draw.circle(surface, tp['mg_mount'], (cx - 3, cy - 3), 1)
        elif tank_type == TankType.PANTHER_AUSFG:
            tw, th = 14, 12
            tx = cx - tw // 2
            ty = cy - th // 2
            pygame.draw.rect(surface, tp['turret_base'], (tx, ty, tw, th), border_radius=2)
            pygame.draw.ellipse(surface, tp['turret_dark'], (tx + 3, ty + 3, tw - 6, th - 5))
            schurzen_y = ty + 4
            pygame.draw.line(surface, tp['schurzen'], (tx - 1, schurzen_y), (tx - 1, schurzen_y + 5), 1)
            pygame.draw.line(surface, tp['schurzen'], (tx + tw, schurzen_y), (tx + tw, schurzen_y + 5), 1)
        elif tank_type == TankType.TIGER_I:
            tw, th = 16, 14
            tx = cx - tw // 2
            ty = cy - th // 2
            pygame.draw.rect(surface, tp['turret_base'], (tx, ty, tw, th), border_radius=1)
            pygame.draw.rect(surface, tp['turret_dark'], (tx + 2, ty + 2, tw - 4, th - 4), 1)
            pygame.draw.circle(surface, tp['porte_cupola'], (cx, cy), 3)
            pygame.draw.circle(surface, tp['turret_dark'], (cx, cy), 3, 1)

        gun_length = 12 if tank_type == TankType.SHERMAN_M4 else 16 if tank_type == TankType.PANTHER_AUSFG else 14
        gun_width = 2 if tank_type != TankType.TIGER_I else 3
        gun_end_y = ty - gun_length
        pygame.draw.line(surface, tp['gun_barrel'], (cx, ty), (cx, gun_end_y), gun_width)

        if tank_type == TankType.TIGER_I:
            pygame.draw.circle(surface, (60, 60, 60), (cx, gun_end_y), 3)
        else:
            pygame.draw.rect(surface, (60, 60, 60), (cx - 2, gun_end_y - 1, 4, 2))

        direction_angles = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: -45,
            Direction.EAST: -90,
            Direction.SOUTHEAST: -135,
            Direction.SOUTH: 180,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 90,
            Direction.NORTHWEST: 45,
        }
        angle = direction_angles.get(turret_direction, 0)
        if angle != 0:
            surface = TankPixelRenderer.get_rotated_surface(surface, angle)

        return surface

    # ------------------------------------------------------------------ #
    #  Tank-type-specific drawing methods
    # ------------------------------------------------------------------ #

    @staticmethod
    def _draw_sherman_m4(
        surface, direction, turret_direction, state, frame, tp, cx, cy
    ):
        """Draw Sherman M4 medium tank - pure top-down view.

        Top-down features:
        - Rectangular hull (long front-to-back, narrow side-to-side)
        - Track rectangles on each side (4-6px wide)
        - Center-forward round/rounded-rect turret
        - Gun barrel extending from turret toward facing dir (8-12px long, 2px wide)
        - Hull armor plate seam lines (1px dark lines)
        - Rear engine deck (darker rectangle)
        """
        import pygame

        size = 36

        hull_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        hull_temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        hull_w, hull_h = 18, 26
        hull_x = tcx - hull_w // 2
        hull_y = tcy - hull_h // 2

        track_w = 5
        track_h = hull_h + 2
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x - track_w, hull_y - 1, track_w, track_h))
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x + hull_w, hull_y - 1, track_w, track_h))

        for ty in range(hull_y - 1, hull_y + track_h, 2):
            pygame.draw.line(hull_temp, (55, 55, 55), (hull_x - track_w, ty), (hull_x, ty), 1)
            pygame.draw.line(hull_temp, (55, 55, 55), (hull_x + hull_w, ty), (hull_x + hull_w + track_w, ty), 1)

        pygame.draw.rect(hull_temp, tp['body_base'], (hull_x, hull_y, hull_w, hull_h))

        seam = tuple(max(0, c - 15) for c in tp['body_dark'])
        pygame.draw.line(hull_temp, seam, (hull_x + 1, hull_y + 7), (hull_x + hull_w - 1, hull_y + 7), 1)
        pygame.draw.line(hull_temp, seam, (hull_x + 1, hull_y + hull_h - 7), (hull_x + hull_w - 1, hull_y + hull_h - 7), 1)
        pygame.draw.line(hull_temp, seam, (tcx, hull_y + 1), (tcx, hull_y + hull_h - 1), 1)

        engine_h = 6
        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x + 2, hull_y + hull_h - engine_h, hull_w - 4, engine_h))
        for vy in range(hull_y + hull_h - engine_h + 1, hull_y + hull_h - 1, 2):
            pygame.draw.line(hull_temp, seam, (hull_x + 4, vy), (hull_x + hull_w - 4, vy), 1)

        TankPixelRenderer._draw_star(hull_temp, tcx, hull_y + hull_h // 2 + 2, 3, tp['white_star'])

        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x, hull_y, hull_w, hull_h), 1)

        turret_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        turret_temp.fill((0, 0, 0, 0))

        tw, th = 12, 10
        tx = tcx - tw // 2
        ty = tcy - th // 2 - 2
        pygame.draw.rect(turret_temp, tp['turret_base'], (tx, ty, tw, th), border_radius=3)
        pygame.draw.ellipse(turret_temp, tp['turret_dark'], (tx + 2, ty + 2, tw - 4, th - 4))

        pygame.draw.circle(turret_temp, tp['cupola'], (tcx + 2, ty + th // 2), 2)
        pygame.draw.circle(turret_temp, tp['mg_mount'], (tcx - 3, ty + 3), 1)

        gun_length = 12
        gun_end_y = ty - gun_length
        pygame.draw.line(turret_temp, tp['gun_barrel'], (tcx, ty), (tcx, gun_end_y), 2)
        pygame.draw.rect(turret_temp, (60, 60, 60), (tcx - 2, gun_end_y - 1, 4, 2))

        direction_angles = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: -45,
            Direction.EAST: -90,
            Direction.SOUTHEAST: -135,
            Direction.SOUTH: 180,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 90,
            Direction.NORTHWEST: 45,
        }

        hull_angle = direction_angles.get(direction, 0)
        turret_angle = direction_angles.get(turret_direction, 0)

        if hull_angle != 0:
            hull_temp = TankPixelRenderer.get_rotated_surface(hull_temp, hull_angle)
        if turret_angle != 0:
            turret_temp = TankPixelRenderer.get_rotated_surface(turret_temp, turret_angle)

        hull_rect = hull_temp.get_rect(center=(cx, cy))
        surface.blit(hull_temp, hull_rect)

        turret_rect = turret_temp.get_rect(center=(cx, cy))
        surface.blit(turret_temp, turret_rect)

        if state == "shoot" and frame == 1:
            direction_vectors = {
                Direction.NORTH: (0, -1),
                Direction.NORTHEAST: (0.707, -0.707),
                Direction.EAST: (1, 0),
                Direction.SOUTHEAST: (0.707, 0.707),
                Direction.SOUTH: (0, 1),
                Direction.SOUTHWEST: (-0.707, 0.707),
                Direction.WEST: (-1, 0),
                Direction.NORTHWEST: (-0.707, -0.707),
            }
            dvx, dvy = direction_vectors.get(turret_direction, (0, -1))
            flash_dist = 18
            flash_x = cx + int(dvx * flash_dist)
            flash_y = cy + int(dvy * flash_dist)
            pygame.draw.ellipse(surface, (255, 255, 100), (flash_x - 4, flash_y - 3, 8, 6))

        if state == "move":
            direction_vectors = {
                Direction.NORTH: (0, 1),
                Direction.NORTHEAST: (-0.707, 0.707),
                Direction.EAST: (-1, 0),
                Direction.SOUTHEAST: (-0.707, -0.707),
                Direction.SOUTH: (0, -1),
                Direction.SOUTHWEST: (0.707, -0.707),
                Direction.WEST: (1, 0),
                Direction.NORTHWEST: (0.707, 0.707),
            }
            dvx, dvy = direction_vectors.get(direction, (0, 1))
            for i in range(3):
                dust_dist = 16 + i * 3
                dust_x = cx + int(dvx * dust_dist)
                dust_y = cy + int(dvy * dust_dist)
                pygame.draw.circle(surface, (139, 119, 66), (dust_x, dust_y), 1 + i % 2)

    @staticmethod
    def _draw_panther_ausfg(
        surface, direction, turret_direction, state, frame, tp, cx, cy
    ):
        """Draw Panther Ausf.G tank - pure top-down view.

        Top-down features:
        - Wider hull rectangle
        - Wider track rectangles on each side
        - Large curved turret
        - Extra-long gun barrel (75mm KwK42 L/70)
        - Schurzen side skirts (thin lines on turret sides)
        - Dunkelgelb dark-yellow base + camouflage stripes
        """
        import pygame

        size = 38

        hull_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        hull_temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        hull_w, hull_h = 20, 28
        hull_x = tcx - hull_w // 2
        hull_y = tcy - hull_h // 2

        track_w = 6
        track_h = hull_h + 2
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x - track_w, hull_y - 1, track_w, track_h))
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x + hull_w, hull_y - 1, track_w, track_h))

        for ty in range(hull_y - 1, hull_y + track_h, 2):
            pygame.draw.line(hull_temp, (48, 48, 48), (hull_x - track_w, ty), (hull_x, ty), 1)
            pygame.draw.line(hull_temp, (48, 48, 48), (hull_x + hull_w, ty), (hull_x + hull_w + track_w, ty), 1)

        pygame.draw.rect(hull_temp, tp['body_base'], (hull_x, hull_y, hull_w, hull_h))

        camo_rng = random.Random(42)
        if camo_rng.random() > 0.5:
            for stripe_y in range(hull_y + 4, hull_y + hull_h - 4, 3):
                stripe_start = camo_rng.randint(hull_x + 2, hull_x + hull_w // 2)
                stripe_len = camo_rng.randint(4, 10)
                pygame.draw.line(hull_temp, tp['camo_red_brown'],
                               (stripe_start, stripe_y), (stripe_start + stripe_len, stripe_y), 1)

        panther_seam = tuple(max(0, c - 18) for c in tp['body_dark'])
        pygame.draw.line(hull_temp, panther_seam, (hull_x + 1, hull_y + 8), (hull_x + hull_w - 1, hull_y + 8), 1)
        pygame.draw.line(hull_temp, panther_seam, (hull_x + 1, hull_y + hull_h - 8), (hull_x + hull_w - 1, hull_y + hull_h - 8), 1)
        pygame.draw.line(hull_temp, panther_seam, (tcx, hull_y + 1), (tcx, hull_y + hull_h - 1), 1)

        engine_h = 7
        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x + 2, hull_y + hull_h - engine_h, hull_w - 4, engine_h))
        for vy in range(hull_y + hull_h - engine_h + 1, hull_y + hull_h - 1, 2):
            pygame.draw.line(hull_temp, panther_seam, (hull_x + 4, vy), (hull_x + hull_w - 4, vy), 1)

        pygame.draw.rect(hull_temp, tp['exhaust_pipe'], (hull_x + 1, hull_y + hull_h - 5, 3, 2))
        pygame.draw.rect(hull_temp, tp['exhaust_pipe'], (hull_x + 1, hull_y + hull_h - 3, 3, 2))

        TankPixelRenderer._draw_iron_cross(hull_temp, tcx, hull_y + hull_h // 2 + 2, tp['iron_cross'])

        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x, hull_y, hull_w, hull_h), 1)

        turret_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        turret_temp.fill((0, 0, 0, 0))

        tw, th = 14, 12
        tx = tcx - tw // 2
        ty = tcy - th // 2 - 2
        pygame.draw.rect(turret_temp, tp['turret_base'], (tx, ty, tw, th), border_radius=2)
        pygame.draw.ellipse(turret_temp, tp['turret_dark'], (tx + 3, ty + 3, tw - 6, th - 5))

        schurzen_y = ty + 4
        pygame.draw.line(turret_temp, tp['schurzen'], (tx - 1, schurzen_y), (tx - 1, schurzen_y + 5), 1)
        pygame.draw.line(turret_temp, tp['schurzen'], (tx + tw, schurzen_y), (tx + tw, schurzen_y + 5), 1)

        gun_length = 16
        gun_end_y = ty - gun_length
        pygame.draw.line(turret_temp, tp['gun_barrel'], (tcx, ty), (tcx, gun_end_y), 2)
        pygame.draw.rect(turret_temp, (55, 55, 55), (tcx - 2, gun_end_y - 1, 4, 3))

        direction_angles = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: -45,
            Direction.EAST: -90,
            Direction.SOUTHEAST: -135,
            Direction.SOUTH: 180,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 90,
            Direction.NORTHWEST: 45,
        }

        hull_angle = direction_angles.get(direction, 0)
        turret_angle = direction_angles.get(turret_direction, 0)

        if hull_angle != 0:
            hull_temp = TankPixelRenderer.get_rotated_surface(hull_temp, hull_angle)
        if turret_angle != 0:
            turret_temp = TankPixelRenderer.get_rotated_surface(turret_temp, turret_angle)

        hull_rect = hull_temp.get_rect(center=(cx, cy))
        surface.blit(hull_temp, hull_rect)

        turret_rect = turret_temp.get_rect(center=(cx, cy))
        surface.blit(turret_temp, turret_rect)

        if state == "shoot" and frame == 1:
            direction_vectors = {
                Direction.NORTH: (0, -1),
                Direction.NORTHEAST: (0.707, -0.707),
                Direction.EAST: (1, 0),
                Direction.SOUTHEAST: (0.707, 0.707),
                Direction.SOUTH: (0, 1),
                Direction.SOUTHWEST: (-0.707, 0.707),
                Direction.WEST: (-1, 0),
                Direction.NORTHWEST: (-0.707, -0.707),
            }
            dvx, dvy = direction_vectors.get(turret_direction, (0, -1))
            flash_dist = 20
            flash_x = cx + int(dvx * flash_dist)
            flash_y = cy + int(dvy * flash_dist)
            pygame.draw.ellipse(surface, (255, 255, 100), (flash_x - 5, flash_y - 4, 10, 8))

        if state == "move":
            direction_vectors = {
                Direction.NORTH: (0, 1),
                Direction.NORTHEAST: (-0.707, 0.707),
                Direction.EAST: (-1, 0),
                Direction.SOUTHEAST: (-0.707, -0.707),
                Direction.SOUTH: (0, -1),
                Direction.SOUTHWEST: (0.707, -0.707),
                Direction.WEST: (1, 0),
                Direction.NORTHWEST: (0.707, 0.707),
            }
            dvx, dvy = direction_vectors.get(direction, (0, 1))
            for i in range(4):
                dust_dist = 18 + i * 3
                dust_x = cx + int(dvx * dust_dist)
                dust_y = cy + int(dvy * dust_dist)
                pygame.draw.circle(surface, (139, 119, 66), (dust_x, dust_y), 1 + i % 2)

    @staticmethod
    def _draw_tiger_i(
        surface, direction, turret_direction, state, frame, tp, cx, cy
    ):
        """Draw Tiger I heavy tank - pure top-down view.

        Top-down features:
        - Wide boxy hull rectangle
        - Ultra-wide track rectangles
        - Large rectangular turret (low corner radius, boxy shape)
        - 88mm KwK36 barrel (thick, 3px wide)
        - Porte armored cupola (center of turret)
        - "Mobile bunker" appearance
        """
        import pygame

        size = 44

        hull_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        hull_temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        hull_w, hull_h = 24, 32
        hull_x = tcx - hull_w // 2
        hull_y = tcy - hull_h // 2

        track_w = 6
        track_h = hull_h + 2
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x - track_w, hull_y - 1, track_w, track_h))
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x + hull_w, hull_y - 1, track_w, track_h))

        for ty in range(hull_y - 1, hull_y + track_h, 2):
            pygame.draw.line(hull_temp, (42, 42, 42), (hull_x - track_w, ty), (hull_x, ty), 1)
            pygame.draw.line(hull_temp, (42, 42, 42), (hull_x + hull_w, ty), (hull_x + hull_w + track_w, ty), 1)

        pygame.draw.rect(hull_temp, tp['body_base'], (hull_x, hull_y, hull_w, hull_h))

        tiger_seam = tuple(max(0, c - 20) for c in tp['body_dark'])
        pygame.draw.line(hull_temp, tiger_seam, (hull_x + 1, hull_y + 8), (hull_x + hull_w - 1, hull_y + 8), 1)
        pygame.draw.line(hull_temp, tiger_seam, (hull_x + 1, hull_y + hull_h - 8), (hull_x + hull_w - 1, hull_y + hull_h - 8), 1)
        pygame.draw.line(hull_temp, tiger_seam, (tcx - 4, hull_y + 1), (tcx - 4, hull_y + hull_h - 1), 1)
        pygame.draw.line(hull_temp, tiger_seam, (tcx + 4, hull_y + 1), (tcx + 4, hull_y + hull_h - 1), 1)

        engine_h = 8
        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x + 2, hull_y + hull_h - engine_h, hull_w - 4, engine_h))
        for vy in range(hull_y + hull_h - engine_h + 1, hull_y + hull_h - 1, 2):
            pygame.draw.line(hull_temp, tiger_seam, (hull_x + 4, vy), (hull_x + hull_w - 4, vy), 1)

        primer_rng = random.Random(77)
        if primer_rng.random() > 0.6:
            primer_x = primer_rng.randint(hull_x + 3, hull_x + hull_w - 5)
            primer_y = primer_rng.randint(hull_y + 10, hull_y + hull_h - 10)
            pygame.draw.rect(hull_temp, tp['red_primer'], (primer_x, primer_y, 3, 2))

        TankPixelRenderer._draw_iron_cross(hull_temp, tcx, hull_y + hull_h // 2 + 2, tp['iron_cross'])

        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x, hull_y, hull_w, hull_h), 2)

        turret_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        turret_temp.fill((0, 0, 0, 0))

        tw, th = 16, 14
        tx = tcx - tw // 2
        ty = tcy - th // 2 - 2
        pygame.draw.rect(turret_temp, tp['turret_base'], (tx, ty, tw, th), border_radius=1)
        pygame.draw.rect(turret_temp, tp['turret_dark'], (tx + 2, ty + 2, tw - 4, th - 4), 1)

        pygame.draw.circle(turret_temp, tp['porte_cupola'], (tcx, ty + th // 2), 3)
        pygame.draw.circle(turret_temp, tp['turret_dark'], (tcx, ty + th // 2), 3, 1)

        gun_length = 14
        gun_end_y = ty - gun_length
        pygame.draw.line(turret_temp, tp['gun_barrel'], (tcx, ty), (tcx, gun_end_y), 3)
        pygame.draw.circle(turret_temp, (60, 60, 60), (tcx, gun_end_y), 3)
        pygame.draw.circle(turret_temp, tp['gun_barrel'], (tcx, gun_end_y), 2, 1)

        direction_angles = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: -45,
            Direction.EAST: -90,
            Direction.SOUTHEAST: -135,
            Direction.SOUTH: 180,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 90,
            Direction.NORTHWEST: 45,
        }

        hull_angle = direction_angles.get(direction, 0)
        turret_angle = direction_angles.get(turret_direction, 0)

        if hull_angle != 0:
            hull_temp = TankPixelRenderer.get_rotated_surface(hull_temp, hull_angle)
        if turret_angle != 0:
            turret_temp = TankPixelRenderer.get_rotated_surface(turret_temp, turret_angle)

        hull_rect = hull_temp.get_rect(center=(cx, cy))
        surface.blit(hull_temp, hull_rect)

        turret_rect = turret_temp.get_rect(center=(cx, cy))
        surface.blit(turret_temp, turret_rect)

        if state == "shoot" and frame == 1:
            direction_vectors = {
                Direction.NORTH: (0, -1),
                Direction.NORTHEAST: (0.707, -0.707),
                Direction.EAST: (1, 0),
                Direction.SOUTHEAST: (0.707, 0.707),
                Direction.SOUTH: (0, 1),
                Direction.SOUTHWEST: (-0.707, 0.707),
                Direction.WEST: (-1, 0),
                Direction.NORTHWEST: (-0.707, -0.707),
            }
            dvx, dvy = direction_vectors.get(turret_direction, (0, -1))
            flash_dist = 20
            flash_x = cx + int(dvx * flash_dist)
            flash_y = cy + int(dvy * flash_dist)
            pygame.draw.ellipse(surface, (255, 255, 100), (flash_x - 6, flash_y - 4, 12, 8))

        if state == "move":
            direction_vectors = {
                Direction.NORTH: (0, 1),
                Direction.NORTHEAST: (-0.707, 0.707),
                Direction.EAST: (-1, 0),
                Direction.SOUTHEAST: (-0.707, -0.707),
                Direction.SOUTH: (0, -1),
                Direction.SOUTHWEST: (0.707, -0.707),
                Direction.WEST: (1, 0),
                Direction.NORTHWEST: (0.707, 0.707),
            }
            dvx, dvy = direction_vectors.get(direction, (0, 1))
            for i in range(5):
                dust_dist = 20 + i * 3
                dust_x = cx + int(dvx * dust_dist)
                dust_y = cy + int(dvy * dust_dist)
                pygame.draw.circle(surface, (139, 119, 66), (dust_x, dust_y), 2 if i % 2 == 0 else 1)

    # ------------------------------------------------------------------ #
    #  Faction insignia helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _draw_star(surface, cx, cy, radius, color):
        """Draw a five-pointed star (Allied faction insignia)."""
        import pygame

        points = []
        for i in range(5):
            angle = math.radians(-90 + i * 72)
            points.append((
                cx + int(radius * math.cos(angle)),
                cy + int(radius * math.sin(angle)),
            ))
            angle_inner = math.radians(-90 + i * 72 + 36)
            inner_r = radius * 0.4
            points.append((
                cx + int(inner_r * math.cos(angle_inner)),
                cy + int(inner_r * math.sin(angle_inner)),
            ))
        if len(points) >= 3:
            pygame.draw.polygon(surface, color, points)

    @staticmethod
    def _draw_iron_cross(surface, cx, cy, color):
        """Draw an iron cross (Axis faction insignia)."""
        import pygame

        pygame.draw.circle(surface, color, (cx, cy), 2)
        pygame.draw.line(surface, color, (cx - 3, cy), (cx + 3, cy), 1)
        pygame.draw.line(surface, color, (cx, cy - 3), (cx, cy + 3), 1)
