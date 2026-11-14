"""Building Entity - Sprint 3 Day 11 FUNC-05.

Represents buildings (barracks, power plants, defense towers) with construction state.
Supports construction progress tracking and resource consumption validation.
"""

# STATUS: ORPHAN (TD-080, 2026-11-14) — 0 external src references (create_building factory unused); see docs/TECH_DEBT.md TD-080

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import cast

from pycc2.domain.value_objects.tile_coord import TileCoord


class BuildingType(Enum):
    """Building categories."""

    BARRACKS = auto()  # Train infantry units
    POWER_PLANT = auto()  # Generate power
    DEFENSE_TOWER = auto()  # Attack enemy units
    COMMAND_CENTER = auto()  # Base building
    REFINERY = auto()  # Resource processing


class BuildingState(Enum):
    """Construction states."""

    PLANNING = auto()  # Placement preview (not built yet)
    CONSTRUCTING = auto()  # Under construction
    COMPLETED = auto()  # Fully built and operational
    DESTROYED = auto()  # Destroyed by enemy


@dataclass
class BuildingCost:
    """Resource cost for building construction."""

    gold: float = 0.0
    wood: float = 0.0
    power: int = 0  # Power consumed (not cost)


@dataclass
class Building:
    """Building entity with construction state machine.

    Lifecycle: PLANNING → CONSTRUCTING → COMPLETED

    Attributes:
        id: Unique building ID
        building_type: Type of building
        position: Tile position (top-left corner)
        width: Building width in tiles
        height: Building height in tiles
        state: Current construction state
        construction_progress: Progress (0.0 to 1.0)
        construction_time: Total construction time (seconds)
        cost: Resource cost
        hp: Current hit points
        max_hp: Maximum hit points
    """

    id: str
    building_type: BuildingType
    position: TileCoord
    width: int = 2  # Default 2x2 tiles
    height: int = 2
    state: BuildingState = BuildingState.PLANNING
    construction_progress: float = 0.0
    construction_time: float = 10.0  # Default 10 seconds to build
    cost: BuildingCost = field(default_factory=BuildingCost)
    hp: int = 100
    max_hp: int = 100
    owner_faction: str = "PLAYER"

    def start_construction(self) -> None:
        """Start construction from PLANNING state."""
        if self.state != BuildingState.PLANNING:
            raise ValueError(f"Cannot start construction from {self.state}")

        self.state = BuildingState.CONSTRUCTING
        self.construction_progress = 0.0

    def update_construction(self, delta_time: float) -> None:
        """Update construction progress.

        Args:
            delta_time: Time elapsed since last update (seconds)
        """
        if self.state != BuildingState.CONSTRUCTING:
            return

        self.construction_progress += delta_time / self.construction_time

        if self.construction_progress >= 1.0:
            self.construction_progress = 1.0
            self.state = BuildingState.COMPLETED

    def is_completed(self) -> bool:
        """Check if building is fully constructed."""
        return self.state == BuildingState.COMPLETED

    def is_constructing(self) -> bool:
        """Check if building is under construction."""
        return self.state == BuildingState.CONSTRUCTING

    def get_occupied_tiles(self) -> list[TileCoord]:
        """Get list of tiles occupied by this building.

        Returns:
            List of TileCoord covering building footprint
        """
        tiles = []
        for dy in range(self.height):
            for dx in range(self.width):
                tiles.append(TileCoord(self.position.x + dx, self.position.y + dy))
        return tiles

    def overlaps_with(self, other: Building) -> bool:
        """Check if this building overlaps with another.

        Args:
            other: Another building to check

        Returns:
            True if buildings overlap
        """
        return not (
            self.position.x + self.width <= other.position.x
            or other.position.x + other.width <= self.position.x
            or self.position.y + self.height <= other.position.y
            or other.position.y + other.height <= self.position.y
        )

    def take_damage(self, damage: int) -> None:
        """Take damage from attack.

        Args:
            damage: Damage amount
        """
        self.hp = max(0, self.hp - damage)
        if self.hp == 0:
            self.state = BuildingState.DESTROYED


# Building type presets
BUILDING_PRESETS = {
    BuildingType.BARRACKS: {
        "width": 3,
        "height": 3,
        "cost": BuildingCost(gold=300, wood=150, power=10),
        "construction_time": 15.0,
        "max_hp": 500,
    },
    BuildingType.POWER_PLANT: {
        "width": 2,
        "height": 2,
        "cost": BuildingCost(gold=200, wood=100, power=0),
        "construction_time": 10.0,
        "max_hp": 300,
    },
    BuildingType.DEFENSE_TOWER: {
        "width": 2,
        "height": 2,
        "cost": BuildingCost(gold=250, wood=50, power=15),
        "construction_time": 12.0,
        "max_hp": 400,
    },
    BuildingType.COMMAND_CENTER: {
        "width": 4,
        "height": 4,
        "cost": BuildingCost(gold=500, wood=200, power=0),
        "construction_time": 20.0,
        "max_hp": 1000,
    },
    BuildingType.REFINERY: {
        "width": 3,
        "height": 2,
        "cost": BuildingCost(gold=350, wood=100, power=5),
        "construction_time": 12.0,
        "max_hp": 400,
    },
}


def create_building(
    building_id: str,
    building_type: BuildingType,
    position: TileCoord,
    owner_faction: str = "PLAYER",
) -> Building:
    """Factory function to create building with preset values.

    Args:
        building_id: Unique ID
        building_type: Type of building
        position: Tile position
        owner_faction: Owner faction

    Returns:
        Building instance with preset values
    """
    preset = BUILDING_PRESETS.get(building_type, {})

    return Building(
        id=building_id,
        building_type=building_type,
        position=position,
        width=cast(int, preset.get("width", 2)),
        height=cast(int, preset.get("height", 2)),
        cost=cast(BuildingCost, preset.get("cost", BuildingCost())),
        construction_time=cast(float, preset.get("construction_time", 10.0)),
        max_hp=cast(int, preset.get("max_hp", 100)),
        hp=cast(int, preset.get("max_hp", 100)),
        owner_faction=owner_faction,
    )
