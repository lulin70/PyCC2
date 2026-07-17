"""Deployment phase data models and constants.

Extracted from deployment_ui.py for single responsibility.
Contains: Enums, dataclasses, terrain constants, color definitions.

TD-078 (v0.7.0): DeploymentUnit / UnitCategory / UNIT_TYPE_TO_CATEGORY /
IMPASSABLE_TERRAINS moved to ``domain.value_objects.deployment_types`` so
the services layer can use them without importing from presentation. This
module re-exports them for backward compatibility with the 18+ presentation
and test files that import from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

# TD-078 (v0.7.0): Re-export domain types for backward compatibility.
from pycc2.domain.value_objects.deployment_types import (
    UNIT_TYPE_TO_CATEGORY,
    DeploymentUnit,
    UnitCategory,
)


class DeploymentPhase(Enum):
    """Phases of the deployment workflow."""

    PLANNING = auto()
    DEPLOYING = auto()
    READY = auto()
    ACTIVE = auto()


class ZoneType(Enum):
    """Map zone classification during deployment."""

    FRIENDLY = auto()
    NO_MANS_LAND = auto()
    ENEMY_CONTROLLED = auto()


# Category display labels and icons
CATEGORY_INFO: dict[UnitCategory, tuple[str, str]] = {
    UnitCategory.INFANTRY: ("INFANTRY", "♟"),
    UnitCategory.SUPPORT: ("SUPPORT (MG/AT)", "⚔"),
    UnitCategory.ARMOR: ("ARMOR", "▣"),
    UnitCategory.RECON: ("RECON", "◉"),
}

# Terrain type constants (mirrors TerrainType int values for standalone use)
TERRAIN_OPEN = 0
TERRAIN_ROAD = 1
TERRAIN_GRASS = 2
TERRAIN_WOODS = 3
TERRAIN_BUILDING_ENTERABLE = 4
TERRAIN_BUILDING_SOLID = 5
TERRAIN_WATER = 6
TERRAIN_HEDGE = 7
TERRAIN_WALL = 8
TERRAIN_ROUGH = 9
TERRAIN_SHALLOW = 10
TERRAIN_BRIDGE = 11
TERRAIN_CRATER = 12
TERRAIN_SWAMP = 13

BUILDING_TERRAINS = {TERRAIN_BUILDING_ENTERABLE, TERRAIN_BUILDING_SOLID}
DEEP_WATER_TERRAINS = {TERRAIN_WATER}
SHALLOW_WATER_TERRAINS = {TERRAIN_SHALLOW}


@dataclass
class DeploymentState:
    """Full state of the deployment phase for one player."""

    phase: DeploymentPhase = DeploymentPhase.PLANNING
    available_units: list[DeploymentUnit] = field(default_factory=list)
    placed_units: list[DeploymentUnit] = field(default_factory=list)
    max_infantry: int = 15
    max_support: int = 10
    requisition_points: int = 0
    requisition_points_spent: int = 0
    friendly_zone: list[tuple[int, int]] = field(default_factory=list)
    enemy_zone: list[tuple[int, int]] = field(default_factory=list)
    no_mans_land: list[tuple[int, int]] = field(default_factory=list)


# Zone overlay colours (R, G, B, A)
ZONE_COLORS: dict[ZoneType, tuple[int, int, int, int]] = {
    ZoneType.FRIENDLY: (0, 0, 0, 0),
    ZoneType.NO_MANS_LAND: (120, 120, 120, 60),
    ZoneType.ENEMY_CONTROLLED: (60, 60, 60, 100),
}

ZONE_BORDER_COLORS: dict[ZoneType, tuple[int, int, int]] = {
    ZoneType.FRIENDLY: (0, 180, 0),
    ZoneType.NO_MANS_LAND: (160, 160, 160),
    ZoneType.ENEMY_CONTROLLED: (160, 60, 60),
}

VALID_PLACEMENT_COLOR = (0, 255, 100, 70)
INVALID_PLACEMENT_COLOR = (255, 60, 60, 50)
SELECTED_UNIT_HIGHLIGHT = (255, 255, 0)

# Roster panel colors
ROSTER_BG = (30, 34, 42, 230)
ROSTER_BORDER = (80, 84, 92)
ROSTER_TEXT = (230, 230, 230)
ROSTER_TEXT_DIM = (150, 150, 150)
ROSTER_SELECTED_BG = (60, 90, 140, 200)
ROSTER_PLACED_BG = (40, 70, 40, 180)
ROSTER_CATEGORY_BG = (45, 50, 60, 200)
ROSTER_CATEGORY_TEXT = (180, 170, 130)

# Button colors
BUTTON_BG_NORMAL = (70, 74, 82)
BUTTON_BG_HOVER = (90, 94, 102)
BUTTON_BG_DISABLED = (45, 48, 55)
BUTTON_BORDER = (100, 104, 112)
BUTTON_TEXT = (220, 220, 220)
BUTTON_TEXT_DISABLED = (120, 120, 120)
BUTTON_ACTIVE_BG = (40, 120, 40)

# Requisition points colors
RP_COLOR = (200, 180, 100)
RP_SPENT_COLOR = (180, 100, 100)


# Backward compatibility aliases (with underscore prefix for internal use)
_CATEGORY_INFO = CATEGORY_INFO
_UNIT_TYPE_TO_CATEGORY = UNIT_TYPE_TO_CATEGORY
_ZONE_COLORS = ZONE_COLORS
_ZONE_BORDER_COLORS = ZONE_BORDER_COLORS
_ROSTER_BG = ROSTER_BG
_ROSTER_BORDER = ROSTER_BORDER
_ROSTER_TEXT = ROSTER_TEXT
_ROSTER_TEXT_DIM = ROSTER_TEXT_DIM
_ROSTER_SELECTED_BG = ROSTER_SELECTED_BG
_ROSTER_PLACED_BG = ROSTER_PLACED_BG
_ROSTER_CATEGORY_BG = ROSTER_CATEGORY_BG
_ROSTER_CATEGORY_TEXT = ROSTER_CATEGORY_TEXT
_BUTTON_BG_NORMAL = BUTTON_BG_NORMAL
_BUTTON_BG_HOVER = BUTTON_BG_HOVER
_BUTTON_BG_DISABLED = BUTTON_BG_DISABLED
_BUTTON_BORDER = BUTTON_BORDER
_BUTTON_TEXT = BUTTON_TEXT
_BUTTON_TEXT_DISABLED = BUTTON_TEXT_DISABLED
_BUTTON_ACTIVE_BG = BUTTON_ACTIVE_BG
_RP_COLOR = RP_COLOR
_RP_SPENT_COLOR = RP_SPENT_COLOR
