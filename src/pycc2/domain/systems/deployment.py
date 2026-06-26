"""CC2 deployment phase system."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.systems.cc2_authentic_weapons import (
    Faction,
    InfantryRole,
)
from pycc2.domain.systems.unit_database import get_cc2_units

if TYPE_CHECKING:
    pass

_ALLY_FACTIONS = (Faction.AMERICAN, Faction.BRITISH, Faction.POLISH)


class ZoneType(Enum):
    """CC2 map zone types during deployment."""

    FRIENDLY = auto()  # Clear shading - player can deploy here
    NO_MANS_LAND = auto()  # Light gray - contested area
    ENEMY_CONTROLLED = auto()  # Dark gray - enemy territory


@dataclass
class TileZone:
    """Zone assignment for a single tile during deployment."""

    x: int
    y: int
    zone: ZoneType


@dataclass
class DeploymentConfig:
    """
    Configuration for a battle's deployment phase.

    Defines where each side can place their units.
    """

    map_width: int
    map_height: int

    # Zone assignments per tile (indexed by [y][x])
    ally_zones: list[list[ZoneType]]
    axis_zones: list[list[ZoneType]]

    # Deployment constraints
    max_infantry: int = 9  # Max infantry units (CC2 default)
    max_support: int = 6  # Max support units (vehicles/mortars/MGs)
    max_total: int = 15  # Absolute maximum

    # Time limit for deployment (seconds)
    time_limit: int = 300  # 5 minutes default

    def can_deploy_at(self, x: int, y: int, faction: Faction) -> bool:
        """Check if a tile is legal for deployment by given faction."""
        if not (0 <= x < self.map_width and 0 <= y < self.map_height):
            return False

        zones = (
            self.ally_zones
            if faction in [Faction.AMERICAN, Faction.BRITISH, Faction.POLISH]
            else self.axis_zones
        )
        return zones[y][x] == ZoneType.FRIENDLY


class DeploymentPhase:
    """
    Manages the pre-battle deployment phase.

    Implements CC2's drag-and-drop unit placement system.
    """

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.deployed_units: dict[Faction, list[tuple[int, int, str]]] = {
            faction: [] for faction in Faction
        }
        self.is_complete: bool = False
        self.current_faction: Faction | None = None

    def start_deployment(self, faction: Faction) -> None:
        """Begin deployment for a specific faction."""
        self.current_faction = faction
        self.deployed_units[faction] = []
        self.is_complete = False

    def place_unit(self, unit_template_id: str, x: int, y: int) -> bool:
        """
        Attempt to place a unit at specified position.

        Returns True if placement succeeded.
        """
        if not self.current_faction:
            return False

        # Check zone legality
        if not self.config.can_deploy_at(x, y, self.current_faction):
            return False

        # Check unit limits
        current_count = len(self.deployed_units[self.current_faction])
        if current_count >= self.config.max_total:
            return False

        # Get unit type to check infantry/support limits
        unit_db = get_cc2_units()
        unit = unit_db.get(unit_template_id)
        if not unit:
            return False

        # Count current infantry vs support
        infantry_count = sum(
            1
            for _, _, tid in self.deployed_units[self.current_faction]
            if tid in unit_db and unit_db[tid].role in [r for r in InfantryRole]
        )
        support_count = current_count - infantry_count

        is_infantry = unit.role in [r for r in InfantryRole]

        if is_infantry and infantry_count >= self.config.max_infantry:
            return False
        if not is_infantry and support_count >= self.config.max_support:
            return False

        # Check terrain legality (no tanks in buildings, etc.)
        # This would need map data integration

        # Place the unit
        self.deployed_units[self.current_faction].append((x, y, unit_template_id))
        return True

    def remove_unit(self, index: int) -> bool:
        """Remove a previously placed unit."""
        if not self.current_faction:
            return False

        if 0 <= index < len(self.deployed_units[self.current_faction]):
            self.deployed_units[self.current_faction].pop(index)
            return True
        return False

    def confirm_deployment(self) -> bool:
        """Confirm and lock in deployment."""
        if not self.current_faction:
            return False

        self.is_complete = True
        return True

    def get_deployed_positions(self, faction: Faction) -> list[tuple[int, int, str]]:
        """Return all deployed unit positions for a faction."""
        return self.deployed_units.get(faction, [])

    def generate_zone_map_for_display(self, faction: Faction) -> list[list[int]]:
        """
        Generate numeric zone map for rendering.

        Returns 2D array: 0=friendly, 1=no mans land, 2=enemy
        """
        zones = (
            self.config.ally_zones
            if faction in [Faction.AMERICAN, Faction.BRITISH, Faction.POLISH]
            else self.config.axis_zones
        )

        zone_map = []
        for row in zones:
            numeric_row = []
            for z in row:
                if z == ZoneType.FRIENDLY:
                    numeric_row.append(0)
                elif z == ZoneType.NO_MANS_LAND:
                    numeric_row.append(1)
                else:
                    numeric_row.append(2)
            zone_map.append(numeric_row)

        return zone_map


def create_default_deployment_config(map_width: int, map_height: int) -> DeploymentConfig:
    """
    Create a standard split-map deployment configuration.

    Default: Allies get left third, Axis gets right third, middle is no-man's-land.
    """
    ally_zones = [[ZoneType.NO_MANS_LAND for _ in range(map_width)] for _ in range(map_height)]
    axis_zones = [[ZoneType.NO_MANS_LAND for _ in range(map_width)] for _ in range(map_height)]

    third = map_width // 3

    for y in range(map_height):
        for x in range(map_width):
            if x < third - 1:
                ally_zones[y][x] = ZoneType.FRIENDLY
            elif x >= map_width - third + 1:
                axis_zones[y][x] = ZoneType.FRIENDLY

    return DeploymentConfig(
        map_width=map_width,
        map_height=map_height,
        ally_zones=ally_zones,
        axis_zones=axis_zones,
        max_infantry=9,
        max_support=6,
        max_total=15,
    )
