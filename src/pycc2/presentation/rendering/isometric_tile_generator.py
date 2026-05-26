"""Procedural isometric tile generator for CC2-style terrain.

Generates diamond-shaped (64x32) terrain tiles with CC2 authentic colors.
All tiles use the CC2 color palette derived from UI_REALISTIC_PIXEL_SPEC.md.
"""

# ⚠️ EXPERIMENTAL FEATURE
# CC2 uses Orthographic Top-Down projection, NOT Isometric.
# This module provides an optional isometric mode for future/modding use.
# It is NOT the primary rendering path and should not be used for CC2-fidelity work.

from __future__ import annotations

import random

import pygame

from pycc2.presentation.rendering.isometric_transform import (
    HEIGHT_SCALE,
    TILE_H,
    TILE_W,
    tile_diamond_corners,
)

# ============================================================
# CC2 Isometric Color Palette
# ============================================================

CC2_ISOMETRIC_PALETTE: dict[str, tuple[int, int, int]] = {
    # Terrain
    "grass_base": (56, 104, 36),
    "grass_light": (76, 132, 52),
    "grass_dark": (40, 80, 28),
    "dirt_road": (140, 110, 60),
    "dirt_dark": (110, 85, 45),
    "dirt_light": (160, 130, 75),
    "road_base": (149, 126, 94),
    "road_stone": (158, 158, 158),
    "road_stone_dark": (110, 110, 110),
    "road_gap": (80, 80, 80),
    "water_base": (64, 120, 172),
    "water_light": (100, 160, 210),
    "water_dark": (40, 80, 140),
    "water_foam": (180, 210, 230),
    # Building
    "wall_light": (180, 170, 155),
    "wall_dark": (120, 115, 105),
    "wall_shadow": (80, 78, 72),
    "roof_red": (160, 50, 40),
    "roof_brown": (140, 90, 50),
    "roof_gray": (100, 100, 100),
    # Crater
    "crater_base": (90, 75, 50),
    "crater_dark": (60, 50, 35),
    "crater_rim": (150, 130, 90),
    "crater_water": (50, 90, 130),
    # Hedgerow
    "hedgerow_base": (34, 72, 30),
    "hedgerow_light": (50, 95, 42),
    "hedgerow_dark": (20, 48, 18),
    "hedgerow_shadow": (15, 35, 12),
}


# ============================================================
# Helper Functions
# ============================================================


def _create_diamond_mask(width: int = TILE_W, height: int = TILE_H) -> pygame.Mask:
    """Create a mask in the shape of an isometric diamond.

    Args:
        width: Diamond width in pixels (default TILE_W=64).
        height: Diamond height in pixels (default TILE_H=32).

    Returns:
        A pygame.Mask with the diamond shape filled.
    """
    mask_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    corners = [
        (width // 2, 0),  # top
        (width - 1, height // 2),  # right
        (width // 2, height - 1),  # bottom
        (0, height // 2),  # left
    ]
    pygame.draw.polygon(mask_surface, (255, 255, 255, 255), corners)
    return pygame.mask.from_surface(mask_surface)


def _draw_on_diamond(
    surface: pygame.Surface,
    draw_func: callable,  # type: ignore[type-arg]
    width: int = TILE_W,
    height: int = TILE_H,
) -> None:
    """Execute a draw function clipped to the diamond tile shape.

    Args:
        surface: Target surface (must be at least width x height).
        draw_func: Callable accepting a pygame.Surface to draw on.
        width: Diamond width in pixels.
        height: Diamond height in pixels.
    """
    # Create a temporary surface for drawing
    temp = pygame.Surface((width, height), pygame.SRCALPHA)
    draw_func(temp)

    # Apply diamond clip mask
    mask = _create_diamond_mask(width, height)
    clip_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    # Blit through mask: only keep pixels inside the diamond
    for y in range(height):
        for x in range(width):
            if mask.get_at((x, y)):
                clip_surface.set_at((x, y), temp.get_at((x, y)))

    surface.blit(clip_surface, (0, 0))


def _fill_diamond(surface: pygame.Surface, color: tuple[int, int, int]) -> None:
    """Fill a diamond shape on the surface with a solid color.

    Args:
        surface: Target surface (expected width=TILE_W, height=TILE_H).
        color: RGB fill color.
    """
    corners = tile_diamond_corners(TILE_W / 2, TILE_H / 2)
    int_corners = [(int(x), int(y)) for x, y in corners]
    pygame.draw.polygon(surface, color, int_corners)


def _draw_diamond_outline(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    width: int = 1,
) -> None:
    """Draw an outline around the diamond shape.

    Args:
        surface: Target surface.
        color: RGB outline color.
        width: Line width in pixels.
    """
    corners = tile_diamond_corners(TILE_W / 2, TILE_H / 2)
    int_corners = [(int(x), int(y)) for x, y in corners]
    pygame.draw.polygon(surface, color, int_corners, width)


# ============================================================
# Tile Generators
# ============================================================


def generate_grass_tile() -> pygame.Surface:
    """Generate a grass terrain tile.

    Returns:
        A 64x32 pygame.Surface with a green diamond tile with grass detail.
    """
    surface = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)

    def _draw(temp: pygame.Surface) -> None:
        _fill_diamond(temp, CC2_ISOMETRIC_PALETTE["grass_base"])
        # Add grass detail: small lighter/darker patches
        rng = random.Random(42)  # deterministic seed for consistent tiles
        for _ in range(6):
            dx = rng.randint(8, TILE_W - 9)
            dy = rng.randint(4, TILE_H - 5)
            color = rng.choice(
                [CC2_ISOMETRIC_PALETTE["grass_light"], CC2_ISOMETRIC_PALETTE["grass_dark"]]
            )
            temp.set_at((dx, dy), color)
        # Subtle grass blade lines
        for _ in range(4):
            dx = rng.randint(12, TILE_W - 13)
            dy = rng.randint(6, TILE_H - 7)
            pygame.draw.line(temp, CC2_ISOMETRIC_PALETTE["grass_light"], (dx, dy), (dx, dy - 2), 1)

    _draw_on_diamond(surface, _draw)
    return surface


def generate_dirt_tile() -> pygame.Surface:
    """Generate a dirt terrain tile.

    Returns:
        A 64x32 pygame.Surface with a brown diamond tile with track marks.
    """
    surface = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)

    def _draw(temp: pygame.Surface) -> None:
        _fill_diamond(temp, CC2_ISOMETRIC_PALETTE["dirt_road"])
        # Track marks: two parallel darker lines
        cx, cy = TILE_W // 2, TILE_H // 2
        pygame.draw.line(
            temp,
            CC2_ISOMETRIC_PALETTE["dirt_dark"],
            (cx - 10, cy - 4),
            (cx + 10, cy + 4),
            2,
        )
        pygame.draw.line(
            temp,
            CC2_ISOMETRIC_PALETTE["dirt_dark"],
            (cx - 10, cy + 4),
            (cx + 10, cy - 4),
            2,
        )
        # Scattered pebbles
        rng = random.Random(99)
        for _ in range(5):
            dx = rng.randint(10, TILE_W - 11)
            dy = rng.randint(5, TILE_H - 6)
            temp.set_at((dx, dy), CC2_ISOMETRIC_PALETTE["dirt_light"])

    _draw_on_diamond(surface, _draw)
    return surface


def generate_road_tile() -> pygame.Surface:
    """Generate a cobblestone road tile.

    Returns:
        A 64x32 pygame.Surface with a gray cobblestone diamond tile.
    """
    surface = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)

    def _draw(temp: pygame.Surface) -> None:
        _fill_diamond(temp, CC2_ISOMETRIC_PALETTE["road_base"])
        # Cobblestone pattern: small rectangular stones
        rng = random.Random(77)
        for row in range(3):
            for col in range(5):
                sx = 8 + col * 10 + (row % 2) * 5
                sy = 6 + row * 8
                stone_color = rng.choice(
                    [CC2_ISOMETRIC_PALETTE["road_stone"], CC2_ISOMETRIC_PALETTE["road_stone_dark"]]
                )
                pygame.draw.rect(temp, stone_color, (sx, sy, 7, 5))
                pygame.draw.rect(temp, CC2_ISOMETRIC_PALETTE["road_gap"], (sx, sy, 7, 5), 1)

    _draw_on_diamond(surface, _draw)
    return surface


def generate_water_tile() -> pygame.Surface:
    """Generate a water terrain tile.

    Returns:
        A 64x32 pygame.Surface with a blue diamond tile with wave lines.
    """
    surface = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)

    def _draw(temp: pygame.Surface) -> None:
        _fill_diamond(temp, CC2_ISOMETRIC_PALETTE["water_base"])
        # Wave lines: short bright streaks
        cx, cy = TILE_W // 2, TILE_H // 2
        pygame.draw.line(
            temp,
            CC2_ISOMETRIC_PALETTE["water_light"],
            (cx - 8, cy - 3),
            (cx - 2, cy - 5),
            1,
        )
        pygame.draw.line(
            temp,
            CC2_ISOMETRIC_PALETTE["water_light"],
            (cx + 4, cy + 1),
            (cx + 10, cy - 1),
            1,
        )
        pygame.draw.line(
            temp,
            CC2_ISOMETRIC_PALETTE["water_foam"],
            (cx - 3, cy + 4),
            (cx + 3, cy + 3),
            1,
        )
        # Darker depth patches
        rng = random.Random(55)
        for _ in range(3):
            dx = rng.randint(14, TILE_W - 15)
            dy = rng.randint(7, TILE_H - 8)
            temp.set_at((dx, dy), CC2_ISOMETRIC_PALETTE["water_dark"])

    _draw_on_diamond(surface, _draw)
    return surface


def generate_building_tile(height_levels: int = 2) -> pygame.Surface:
    """Generate a building tile with visible wall sides.

    The building extends above the base diamond by height_levels * HEIGHT_SCALE pixels.
    The surface is sized to accommodate the full building height.

    Args:
        height_levels: Number of elevation levels (default 2).

    Returns:
        A pygame.Surface with the building (top face + wall sides).
    """
    extra_height = height_levels * HEIGHT_SCALE
    total_height = TILE_H + extra_height
    surface = pygame.Surface((TILE_W, total_height), pygame.SRCALPHA)

    # The top face is drawn at the top of the surface
    top_cy = TILE_H // 2  # center Y of the top diamond face

    # Draw top face (roof)
    top_corners = tile_diamond_corners(TILE_W / 2, top_cy)
    int_top_corners = [(int(x), int(y)) for x, y in top_corners]
    pygame.draw.polygon(surface, CC2_ISOMETRIC_PALETTE["roof_brown"], int_top_corners)
    pygame.draw.polygon(surface, CC2_ISOMETRIC_PALETTE["roof_red"], int_top_corners, 1)

    # Draw left wall (from bottom-left edge of top face down)
    left_wall = [
        int_top_corners[3],  # left vertex of top face
        int_top_corners[2],  # bottom vertex of top face
        (int_top_corners[2][0], int_top_corners[2][1] + extra_height),
        (int_top_corners[3][0], int_top_corners[3][1] + extra_height),
    ]
    pygame.draw.polygon(surface, CC2_ISOMETRIC_PALETTE["wall_dark"], left_wall)
    pygame.draw.polygon(surface, CC2_ISOMETRIC_PALETTE["wall_shadow"], left_wall, 1)

    # Draw right wall (from bottom-right edge of top face down)
    right_wall = [
        int_top_corners[2],  # bottom vertex of top face
        int_top_corners[1],  # right vertex of top face
        (int_top_corners[1][0], int_top_corners[1][1] + extra_height),
        (int_top_corners[2][0], int_top_corners[2][1] + extra_height),
    ]
    pygame.draw.polygon(surface, CC2_ISOMETRIC_PALETTE["wall_light"], right_wall)
    pygame.draw.polygon(surface, CC2_ISOMETRIC_PALETTE["wall_shadow"], right_wall, 1)

    # Window detail on right wall
    if height_levels >= 2:
        mid_y = (right_wall[0][1] + right_wall[3][1]) // 2
        mid_x = (right_wall[0][0] + right_wall[1][0]) // 2
        pygame.draw.rect(surface, CC2_ISOMETRIC_PALETTE["wall_shadow"], (mid_x - 2, mid_y - 2, 4, 4))

    return surface


def generate_crater_tile() -> pygame.Surface:
    """Generate a shell crater tile (dark depression).

    Returns:
        A 64x32 pygame.Surface with a crater diamond tile.
    """
    surface = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)

    def _draw(temp: pygame.Surface) -> None:
        _fill_diamond(temp, CC2_ISOMETRIC_PALETTE["crater_base"])
        # Inner depression (darker, smaller diamond)
        cx, cy = TILE_W // 2, TILE_H // 2
        inner_corners = [
            (cx, cy - 6),
            (cx + 12, cy),
            (cx, cy + 6),
            (cx - 12, cy),
        ]
        pygame.draw.polygon(temp, CC2_ISOMETRIC_PALETTE["crater_dark"], inner_corners)
        # Rim highlight
        outer_corners = tile_diamond_corners(cx, cy)
        int_corners = [(int(x), int(y)) for x, y in outer_corners]
        pygame.draw.polygon(temp, CC2_ISOMETRIC_PALETTE["crater_rim"], int_corners, 1)
        # Possible water puddle at center
        pygame.draw.circle(temp, CC2_ISOMETRIC_PALETTE["crater_water"], (cx, cy), 2)

    _draw_on_diamond(surface, _draw)
    return surface


def generate_hedgerow_tile() -> pygame.Surface:
    """Generate a hedgerow tile (dense green with shadow).

    Returns:
        A 64x32 pygame.Surface with a hedgerow diamond tile.
    """
    surface = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)

    def _draw(temp: pygame.Surface) -> None:
        _fill_diamond(temp, CC2_ISOMETRIC_PALETTE["hedgerow_base"])
        # Dense bush texture: random lighter/darker spots
        rng = random.Random(123)
        for _ in range(12):
            dx = rng.randint(8, TILE_W - 9)
            dy = rng.randint(4, TILE_H - 5)
            color = rng.choice(
                [
                    CC2_ISOMETRIC_PALETTE["hedgerow_light"],
                    CC2_ISOMETRIC_PALETTE["hedgerow_dark"],
                ]
            )
            temp.set_at((dx, dy), color)
        # Shadow along bottom edge
        cx, cy = TILE_W // 2, TILE_H // 2
        pygame.draw.line(
            temp,
            CC2_ISOMETRIC_PALETTE["hedgerow_shadow"],
            (cx - 12, cy + 6),
            (cx + 12, cy + 6),
            2,
        )

    _draw_on_diamond(surface, _draw)
    return surface
