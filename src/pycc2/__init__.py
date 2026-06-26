"""
PyCC2 - Python Company Command 2
Tactical Infantry Combat Simulator
"""

__version__ = "0.3.42"
__author__ = "PyCC2 Team"
__license__ = "MIT"

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Unit
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.vec2 import Vec2

__all__ = [
    "__version__",
    "Unit",
    "GameMap",
    "Vec2",
    "TerrainType",
]
