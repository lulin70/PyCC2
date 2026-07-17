"""Deployment domain types — shared between services and presentation layers.

TD-078 (v0.7.0): Extracted from ``presentation.ui.deployment_models`` to
remove the services→presentation dependency that existed when
``deployment_manager`` imported pure functions from the presentation layer.

These types are domain concepts (unit classification, deployable unit
definition, terrain passability) that belong in the domain layer so both
services and presentation can depend on them without layering violations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pycc2.domain.value_objects.terrain_type import TerrainType


class UnitCategory(Enum):
    """Unit category for roster grouping."""

    INFANTRY = "infantry"
    SUPPORT = "support"
    ARMOR = "vehicle"
    RECON = "recon"


# Mapping from unit_type string to UnitCategory
UNIT_TYPE_TO_CATEGORY: dict[str, UnitCategory] = {
    "infantry": UnitCategory.INFANTRY,
    "support": UnitCategory.SUPPORT,
    "vehicle": UnitCategory.ARMOR,
    "recon": UnitCategory.RECON,
}


@dataclass
class DeploymentUnit:
    """A single deployable unit entry in the roster."""

    unit_template_id: str
    display_name: str
    unit_type: str  # 'infantry', 'support', 'vehicle', 'recon'
    deployment_cost: int
    position: tuple[int, int] | None = None  # None = not yet placed
    is_placed: bool = False

    @property
    def category(self) -> UnitCategory:
        """Get the category."""
        return UNIT_TYPE_TO_CATEGORY.get(self.unit_type, UnitCategory.INFANTRY)


# Terrain types that block unit placement (mirror TerrainType int values).
# Used by deployment factory to filter valid placement positions.
IMPASSABLE_TERRAINS: frozenset[int] = frozenset(
    {
        TerrainType.BUILDING_SOLID.value,
        TerrainType.WATER.value,
        TerrainType.WALL.value,
    }
)
