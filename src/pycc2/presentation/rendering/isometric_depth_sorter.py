"""Isometric depth sorter for back-to-front rendering.

Uses the painter's algorithm: objects farther from the viewer are drawn first.
Sort key combines rendering layer priority with the isometric depth value
computed by ``depth_sort_key`` from ``isometric_transform``.

Typical usage::

    renderables = [tile_to_renderable(x, y, tile), unit_to_renderable(unit)]
    for obj in sort_for_isometric(renderables):
        draw(obj)
"""

# ⚠️ EXPERIMENTAL FEATURE
# CC2 uses Orthographic Top-Down projection, NOT Isometric.
# This module provides an optional isometric mode for future/modding use.
# It is NOT the primary rendering path and should not be used for CC2-fidelity work.

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from pycc2.presentation.rendering.isometric_transform import depth_sort_key

# ============================================================
# Render Layer
# ============================================================


class RenderLayer(IntEnum):
    """Rendering layer priority. Lower values are drawn first."""

    TERRAIN = 0
    DECORATION = 1
    BUILDING = 2
    UNIT = 3
    EFFECT = 4
    UI_OVERLAY = 5


# ============================================================
# Renderable Data
# ============================================================


@dataclass
class IsometricRenderable:
    """An object that can be depth-sorted for isometric rendering."""

    world_x: float
    world_y: float
    world_z: float = 0.0
    layer: RenderLayer = RenderLayer.TERRAIN
    data: Any = None  # Reference to the actual game object (unit, tile, effect, etc.)


# ============================================================
# Depth Sorter
# ============================================================


def sort_for_isometric(
    renderables: list[IsometricRenderable],
) -> list[IsometricRenderable]:
    """Sort renderables for back-to-front isometric rendering.

    Sort key: ``(layer, wx + wy + wz * 0.01)``

    Objects with smaller keys are drawn first (farther from viewer).
    Layer takes precedence so terrain is always drawn before units
    regardless of world position.

    Args:
        renderables: List of renderable objects to sort.

    Returns:
        New list sorted in back-to-front order.

    """
    return sorted(
        renderables,
        key=lambda r: (
            r.layer,
            depth_sort_key(r.world_x, r.world_y, r.world_z),
        ),
    )


# ============================================================
# Conversion Helpers
# ============================================================


def tile_to_renderable(tile_x: int, tile_y: int, tile_data: Any) -> IsometricRenderable:
    """Convert a map tile to a renderable.

    Args:
        tile_x: Tile X coordinate in world units.
        tile_y: Tile Y coordinate in world units.
        tile_data: Reference to the tile game object.

    Returns:
        An ``IsometricRenderable`` on the TERRAIN layer.

    """
    return IsometricRenderable(
        world_x=float(tile_x),
        world_y=float(tile_y),
        world_z=0.0,
        layer=RenderLayer.TERRAIN,
        data=tile_data,
    )


def unit_to_renderable(unit: Any) -> IsometricRenderable:
    """Convert a unit to a renderable.

    Uses ``unit.position`` for world coordinates.

    Args:
        unit: Game unit object with a ``position`` attribute (x, y, z).

    Returns:
        An ``IsometricRenderable`` on the UNIT layer.

    """
    pos = unit.position
    return IsometricRenderable(
        world_x=float(pos.x),
        world_y=float(pos.y),
        world_z=float(getattr(pos, "z", 0.0)),
        layer=RenderLayer.UNIT,
        data=unit,
    )


def effect_to_renderable(x: float, y: float, z: float, effect_data: Any) -> IsometricRenderable:
    """Convert a visual effect to a renderable.

    Args:
        x: World X position.
        y: World Y position.
        z: World Z position (elevation).
        effect_data: Reference to the effect game object.

    Returns:
        An ``IsometricRenderable`` on the EFFECT layer.

    """
    return IsometricRenderable(
        world_x=x,
        world_y=y,
        world_z=z,
        layer=RenderLayer.EFFECT,
        data=effect_data,
    )
