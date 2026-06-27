"""Domain Value Objects Subsystem

Immutable value objects for type-safe domain modeling.
"""

from pycc2.domain.value_objects.damage import Damage
from pycc2.domain.value_objects.direction import Direction
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2

__all__ = [
    "Vec2",
    "TileCoord",
    "TerrainType",
    "Direction",
    "Damage",
]
