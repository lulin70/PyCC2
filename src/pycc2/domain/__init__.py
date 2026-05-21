"""
Domain Layer - Layer 3 (Core Business Logic)

Contains all business rules, entities, value objects, and domain services.
This layer has ZERO framework dependencies - pure Python only.
"""

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.squad import Squad
from pycc2.domain.entities.unit import Unit
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.vec2 import Vec2

__all__ = [
    "Unit",
    "Squad",
    "GameMap",
    "Vec2",
    "TerrainType",
]
