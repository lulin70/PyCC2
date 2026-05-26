"""Isometric coordinate transformation utilities.

CC2 uses 45-degree isometric projection with 2:1 pixel ratio.
Diamond tile: TILE_W=64, TILE_H=32

Coordinate system:
- World coords: (wx, wy) in tile units, origin at top-left
- Isometric screen coords: (sx, sy) after projection
- Z-axis: height in pixels (16px per elevation level)

Transforms:
  world_to_isometric(wx, wy, wz=0) -> (sx, sy)
    sx = (wx - wy) * TILE_W / 2
    sy = (wx + wy) * TILE_H / 2 - wz * HEIGHT_SCALE

  isometric_to_world(sx, sy, wz=0) -> (wx, wy)
    wx = (sx / (TILE_W/2) + sy / (TILE_H/2)) / 2 + wz * HEIGHT_SCALE / TILE_H
    wy = (sy / (TILE_H/2) - sx / (TILE_W/2)) / 2 + wz * HEIGHT_SCALE / TILE_H

Depth sorting:
  sort_key = wx + wy + wz * 0.01
  (painter's algorithm: draw back-to-front)
"""

# ⚠️ EXPERIMENTAL FEATURE
# CC2 uses Orthographic Top-Down projection, NOT Isometric.
# This module provides an optional isometric mode for future/modding use.
# It is NOT the primary rendering path and should not be used for CC2-fidelity work.

from __future__ import annotations

# ============================================================
# Constants
# ============================================================

TILE_W: int = 64
"""Width of an isometric diamond tile in pixels."""

TILE_H: int = 32
"""Height of an isometric diamond tile in pixels (half of TILE_W for 2:1 ratio)."""

HEIGHT_SCALE: int = 16
"""Pixels per elevation level on the Z-axis."""


# ============================================================
# Coordinate Transforms
# ============================================================


def world_to_isometric(wx: float, wy: float, wz: float = 0.0) -> tuple[float, float]:
    """Convert world coordinates to isometric screen coordinates.

    Args:
        wx: World X position (tile units).
        wy: World Y position (tile units).
        wz: World Z position (elevation in height units).

    Returns:
        (sx, sy) isometric screen coordinates in pixels.
    """
    sx = (wx - wy) * TILE_W / 2
    sy = (wx + wy) * TILE_H / 2 - wz * HEIGHT_SCALE
    return (sx, sy)


def isometric_to_world(sx: float, sy: float, wz: float = 0.0) -> tuple[float, float]:
    """Convert isometric screen coordinates back to world coordinates.

    Args:
        sx: Isometric screen X in pixels.
        sy: Isometric screen Y in pixels.
        wz: World Z position (elevation in height units), must match
            the wz used during projection for correct inversion.

    Returns:
        (wx, wy) world coordinates in tile units.
    """
    half_w = TILE_W / 2
    half_h = TILE_H / 2
    # Adjust sy for height offset before inversion
    sy_adjusted = sy + wz * HEIGHT_SCALE
    wx = (sx / half_w + sy_adjusted / half_h) / 2
    wy = (sy_adjusted / half_h - sx / half_w) / 2
    return (wx, wy)


# ============================================================
# Depth Sorting
# ============================================================


def depth_sort_key(wx: float, wy: float, wz: float = 0.0) -> float:
    """Compute a painter's algorithm sort key for back-to-front rendering.

    Objects with smaller keys should be drawn first (they are farther away).

    Args:
        wx: World X position.
        wy: World Y position.
        wz: World Z position (elevation).

    Returns:
        Sort key: lower values are drawn first (farther from viewer).
    """
    return wx + wy + wz * 0.01


# ============================================================
# Tile Geometry Helpers
# ============================================================


def tile_diamond_corners(cx: float, cy: float) -> list[tuple[float, float]]:
    """Return the 4 corners of a diamond tile centered at (cx, cy).

    The diamond is oriented with:
      - Top vertex at (cx, cy - TILE_H/2)
      - Right vertex at (cx + TILE_W/2, cy)
      - Bottom vertex at (cx, cy + TILE_H/2)
      - Left vertex at (cx - TILE_W/2, cy)

    Args:
        cx: Center X in screen pixels.
        cy: Center Y in screen pixels.

    Returns:
        List of 4 (x, y) tuples: [top, right, bottom, left].
    """
    half_w = TILE_W / 2
    half_h = TILE_H / 2
    return [
        (cx, cy - half_h),  # top
        (cx + half_w, cy),  # right
        (cx, cy + half_h),  # bottom
        (cx - half_w, cy),  # left
    ]


def is_point_in_diamond(px: float, py: float, cx: float, cy: float) -> bool:
    """Test whether a screen point lies inside a diamond tile.

    Uses the diamond's edge equations. The diamond is centered at (cx, cy)
    with half-width TILE_W/2 and half-height TILE_H/2.

    Args:
        px: Point X in screen pixels.
        py: Point Y in screen pixels.
        cx: Diamond center X.
        cy: Diamond center Y.

    Returns:
        True if the point is inside (or on the edge of) the diamond.
    """
    half_w = TILE_W / 2
    half_h = TILE_H / 2
    dx = abs(px - cx)
    dy = abs(py - cy)
    # Diamond test: |dx|/half_w + |dy|/half_h <= 1
    return dx / half_w + dy / half_h <= 1.0
