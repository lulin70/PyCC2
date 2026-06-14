"""
Skirmish Mode — Generate random battles outside the campaign.

A "beyond CC2" feature: the original Close Combat 2 only had campaign
battles.  Skirmish mode lets players set up quick one-off fights with
configurable parameters, auto-generated victory locations, deployment
zones, and AI-purchased force compositions.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.systems.cc2_authentic_units import (
    CC2UnitTemplate,
    Faction,
    InfantryRole,
    VehicleType,
    get_units_for_faction,
)
from pycc2.domain.systems.environment import TimeOfDay, WeatherCondition
from pycc2.domain.systems.game_settings import ExperienceLevel
from pycc2.domain.value_objects.terrain_type import TerrainType

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap


# ========================================================================
# Enums
# ========================================================================


class SkirmishType(Enum):
    MEETING_ENGAGEMENT = auto()  # Both sides start from edges, symmetric
    ATTACK_DEFEND = auto()  # One side defends, other attacks
    BREAKTHROUGH = auto()  # Attacker must cross map, defender blocks
    HOLD_GROUND = auto()  # Defender holds VLs, attacker has more points


# ========================================================================
# Configuration
# ========================================================================


@dataclass(frozen=True, slots=True)
class SkirmishConfig:
    map_id: str = "random"
    allied_points: int = 200
    axis_points: int = 200
    allied_experience: ExperienceLevel = ExperienceLevel.REGULAR
    axis_experience: ExperienceLevel = ExperienceLevel.REGULAR
    time_of_day: str = "random"  # 'random' or specific name
    weather: str = "random"  # 'random' or specific name
    battle_type: SkirmishType = SkirmishType.MEETING_ENGAGEMENT


# ========================================================================
# Output dataclasses
# ========================================================================


@dataclass
class VictoryLocation:
    position: tuple[int, int]
    name: str
    strategic_value: int = 1  # 1 = minor, 2 = major


@dataclass
class DeploymentZone:
    min_x: int
    min_y: int
    max_x: int
    max_y: int


@dataclass
class UnitPurchase:
    template_id: str
    template: CC2UnitTemplate
    deployment_position: tuple[int, int]


@dataclass
class SkirmishSetup:
    map_id: str
    battle_type: SkirmishType
    time_of_day: TimeOfDay
    weather: WeatherCondition
    victory_locations: list[VictoryLocation]
    allied_deployment_zone: DeploymentZone
    axis_deployment_zone: DeploymentZone
    allied_units: list[UnitPurchase]
    axis_units: list[UnitPurchase]
    allied_points_remaining: int = 0
    axis_points_remaining: int = 0


# ========================================================================
# Force composition rules (percentage of total points)
# ========================================================================

_FORCE_COMPOSITION: dict[str, float] = {
    "infantry": 0.60,
    "support": 0.20,  # MG / AT
    "armor": 0.10,
    "recon": 0.10,
}

# Experience level → point efficiency multiplier
# Higher experience = fewer but better units per point
_EXP_COST_MULTIPLIER: dict[ExperienceLevel, float] = {
    ExperienceLevel.CONSCRIPT: 0.80,  # Cheaper units, can buy more
    ExperienceLevel.REGULAR: 1.00,
    ExperienceLevel.VETERAN: 1.20,  # More expensive, fewer units
    ExperienceLevel.ELITE: 1.50,
}

# Infantry roles for each category
_INFANTRY_ROLES: set[InfantryRole] = {
    InfantryRole.RIFLE,
    InfantryRole.HEAVY_ASSAULT,
    InfantryRole.ENGINEER,
    InfantryRole.FLAMETHROWER,
    InfantryRole.OFFICER,
    InfantryRole.RESERVE,
}
_SUPPORT_ROLES: set[InfantryRole] = {
    InfantryRole.MACHINE_GUN,
    InfantryRole.ANTI_TANK,
    InfantryRole.MORTAR,
    InfantryRole.SNIPER,
}
_RECON_ROLES: set[InfantryRole] = {
    InfantryRole.SCOUT,
    InfantryRole.RECON,
}
_ARMOR_TYPES: set[VehicleType] = {
    VehicleType.TANK_LIGHT,
    VehicleType.TANK_MEDIUM,
    VehicleType.TANK_HEAVY,
    VehicleType.TANK_DESTROYER,
    VehicleType.HALFTRACK,
    VehicleType.ARMORED_CAR,
    VehicleType.FLAME_TANK,
    VehicleType.SP_ARTILLERY,
}

# Strategic terrain types for victory location detection
_STRATEGIC_TERRAIN: set[TerrainType] = {
    TerrainType.BRIDGE,
    TerrainType.BUILDING_ENTERABLE,
}


# ========================================================================
# SkirmishGenerator
# ========================================================================


class SkirmishGenerator:
    """Generate a complete skirmish battle setup from a configuration."""

    def __init__(self, available_maps: dict[str, GameMap] | None = None) -> None:
        self._maps = available_maps or {}

    def register_map(self, map_id: str, game_map: GameMap) -> None:
        self._maps[map_id] = game_map

    def generate(self, config: SkirmishConfig) -> SkirmishSetup:
        game_map = self._resolve_map(config.map_id)

        time_of_day = self._resolve_time_of_day(config.time_of_day)
        weather = self._resolve_weather(config.weather)

        victory_locations = self._find_victory_locations(game_map)
        allied_zone, axis_zone = self._generate_deployment_zones(
            game_map,
            config.battle_type,
        )

        # Adjust points for HOLD_GROUND (attacker gets more)
        allied_pts = config.allied_points
        axis_pts = config.axis_points
        if config.battle_type == SkirmishType.HOLD_GROUND:
            axis_pts = int(axis_pts * 1.3)  # Attacker bonus
        elif config.battle_type == SkirmishType.BREAKTHROUGH:
            allied_pts = int(allied_pts * 1.2)  # Attacker bonus for allies

        allied_units = self._purchase_units(
            allied_pts,
            config.allied_experience,
            self._allied_factions(),
            allied_zone,
        )
        axis_units = self._purchase_units(
            axis_pts,
            config.axis_experience,
            {Faction.GERMAN},
            axis_zone,
        )

        allied_spent = sum(u.template.deployment_cost for u in allied_units)
        axis_spent = sum(u.template.deployment_cost for u in axis_units)

        return SkirmishSetup(
            map_id=game_map.id,
            battle_type=config.battle_type,
            time_of_day=time_of_day,
            weather=weather,
            victory_locations=victory_locations,
            allied_deployment_zone=allied_zone,
            axis_deployment_zone=axis_zone,
            allied_units=allied_units,
            axis_units=axis_units,
            allied_points_remaining=allied_pts - allied_spent,
            axis_points_remaining=axis_pts - axis_spent,
        )

    # ------------------------------------------------------------------
    # Map resolution
    # ------------------------------------------------------------------

    def _resolve_map(self, map_id: str) -> GameMap:
        if map_id == "random":
            if not self._maps:
                raise ValueError("No maps registered for skirmish generation")
            return random.choice(list(self._maps.values()))
        if map_id in self._maps:
            return self._maps[map_id]
        raise ValueError(f"Unknown map_id: {map_id!r}")

    # ------------------------------------------------------------------
    # Time / weather resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_time_of_day(spec: str) -> TimeOfDay:
        if spec == "random":
            return random.choice(list(TimeOfDay))
        return TimeOfDay[spec.upper()]

    @staticmethod
    def _resolve_weather(spec: str) -> WeatherCondition:
        if spec == "random":
            return random.choice(list(WeatherCondition))
        return WeatherCondition[spec.upper()]

    # ------------------------------------------------------------------
    # Victory location detection
    # ------------------------------------------------------------------

    def _find_victory_locations(self, game_map: GameMap) -> list[VictoryLocation]:
        """Scan the map for strategic points (bridges, road junctions, buildings)."""
        locations: list[VictoryLocation] = []

        # 1. Use existing map objectives if present
        if game_map.objectives:
            for obj in game_map.objectives:
                locations.append(
                    VictoryLocation(
                        position=(obj.position.x, obj.position.y),
                        name=obj.name,
                        strategic_value=2,
                    )
                )
            return locations

        # 2. Auto-detect from terrain
        height, width = game_map.height, game_map.width
        vl_index = 0

        for y in range(height):
            for x in range(width):
                terrain = TerrainType(int(game_map.tile_grid[y, x]))
                if terrain in _STRATEGIC_TERRAIN:
                    # Avoid clustering: skip if too close to existing VL
                    if any(
                        abs(x - vl.position[0]) + abs(y - vl.position[1]) < 8 for vl in locations
                    ):
                        continue
                    vl_index += 1
                    if terrain == TerrainType.BRIDGE:
                        name = f"Bridge {vl_index}"
                        value = 2
                    else:
                        name = f"Building {vl_index}"
                        value = 1
                    locations.append(
                        VictoryLocation(
                            position=(x, y),
                            name=name,
                            strategic_value=value,
                        )
                    )

        # 3. If still no VLs, place them at road junctions
        if not locations:
            locations = self._find_road_junctions(game_map)

        # 4. Fallback: place 3 VLs along the center line
        if not locations:
            mid_x = width // 2
            for i in range(3):
                y = height * (i + 1) // 4
                locations.append(
                    VictoryLocation(
                        position=(mid_x, y),
                        name=f"Objective {i + 1}",
                        strategic_value=2 if i == 1 else 1,
                    )
                )

        return locations

    @staticmethod
    def _find_road_junctions(game_map: GameMap) -> list[VictoryLocation]:
        """Detect road junctions (tiles with 3+ adjacent road tiles)."""
        junctions: list[VictoryLocation] = []
        height, width = game_map.height, game_map.width
        idx = 0
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if TerrainType(int(game_map.tile_grid[y, x])) != TerrainType.ROAD:
                    continue
                adj_roads = 0
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if (
                        0 <= nx < width
                        and 0 <= ny < height
                        and TerrainType(int(game_map.tile_grid[ny, nx])) == TerrainType.ROAD
                    ):
                        adj_roads += 1
                if adj_roads >= 3:
                    if any(abs(x - j.position[0]) + abs(y - j.position[1]) < 8 for j in junctions):
                        continue
                    idx += 1
                    junctions.append(
                        VictoryLocation(
                            position=(x, y),
                            name=f"Junction {idx}",
                            strategic_value=2,
                        )
                    )
        return junctions

    # ------------------------------------------------------------------
    # Deployment zone generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_deployment_zones(
        game_map: GameMap,
        battle_type: SkirmishType,
    ) -> tuple[DeploymentZone, DeploymentZone]:
        w, h = game_map.width, game_map.height

        if battle_type == SkirmishType.MEETING_ENGAGEMENT:
            # Symmetric: each side gets 1/4 of map from their edge
            allied = DeploymentZone(0, 0, w // 4, h)
            axis = DeploymentZone(w - w // 4, 0, w, h)
        elif battle_type == SkirmishType.ATTACK_DEFEND:
            # Defender (axis) gets center, attacker (allied) gets edge
            allied = DeploymentZone(0, 0, w // 5, h)
            axis = DeploymentZone(w // 3, 0, 2 * w // 3, h)
        elif battle_type == SkirmishType.BREAKTHROUGH:
            # Attacker (allied) starts from one edge, defender (axis) holds center
            allied = DeploymentZone(0, 0, w // 5, h)
            axis = DeploymentZone(w // 2, 0, w, h)
        elif battle_type == SkirmishType.HOLD_GROUND:
            # Defender (allied) holds center VLs, attacker (axis) from edge
            allied = DeploymentZone(w // 3, h // 4, 2 * w // 3, 3 * h // 4)
            axis = DeploymentZone(w - w // 5, 0, w, h)
        else:
            allied = DeploymentZone(0, 0, w // 4, h)
            axis = DeploymentZone(w - w // 4, 0, w, h)

        return allied, axis

    # ------------------------------------------------------------------
    # Unit auto-purchase
    # ------------------------------------------------------------------

    def _purchase_units(
        self,
        points: int,
        experience: ExperienceLevel,
        factions: set[Faction],
        zone: DeploymentZone,
    ) -> list[UnitPurchase]:
        cost_mult = _EXP_COST_MULTIPLIER[experience]
        purchases: list[UnitPurchase] = []

        # Collect available templates for these factions
        available: list[CC2UnitTemplate] = []
        for f in factions:
            available.extend(get_units_for_faction(f))

        # Categorize templates
        infantry_pool = [u for u in available if u.role in _INFANTRY_ROLES]
        support_pool = [u for u in available if u.role in _SUPPORT_ROLES]
        armor_pool = [u for u in available if u.role in _ARMOR_TYPES]
        recon_pool = [u for u in available if u.role in _RECON_ROLES]

        # Allocate points by category
        category_budgets = {
            "infantry": int(points * _FORCE_COMPOSITION["infantry"]),
            "support": int(points * _FORCE_COMPOSITION["support"]),
            "armor": int(points * _FORCE_COMPOSITION["armor"]),
            "recon": int(points * _FORCE_COMPOSITION["recon"]),
        }

        remaining = points - sum(category_budgets.values())
        category_budgets["infantry"] += remaining  # leftover goes to infantry

        # Buy from each category
        for cat_name, pool in [
            ("infantry", infantry_pool),
            ("support", support_pool),
            ("armor", armor_pool),
            ("recon", recon_pool),
        ]:
            budget = category_budgets[cat_name]
            spent = 0
            attempts = 0
            max_attempts = len(pool) * 3 + 10

            while spent < budget and attempts < max_attempts:
                attempts += 1
                if not pool:
                    break
                template = random.choice(pool)
                adjusted_cost = int(template.deployment_cost * cost_mult)
                if spent + adjusted_cost > budget:
                    # Try a cheaper unit
                    cheaper = [
                        u for u in pool if int(u.deployment_cost * cost_mult) <= budget - spent
                    ]
                    if not cheaper:
                        break
                    template = random.choice(cheaper)
                    adjusted_cost = int(template.deployment_cost * cost_mult)

                # Respect max_per_battle
                current_count = sum(1 for p in purchases if p.template_id == template.template_id)
                if current_count >= template.max_per_battle:
                    pool = [u for u in pool if u.template_id != template.template_id]
                    continue

                # Random position within deployment zone
                pos = self._random_position_in_zone(zone)
                purchases.append(
                    UnitPurchase(
                        template_id=template.template_id,
                        template=template,
                        deployment_position=pos,
                    )
                )
                spent += adjusted_cost

        return purchases

    @staticmethod
    def _random_position_in_zone(zone: DeploymentZone) -> tuple[int, int]:
        x = random.randint(zone.min_x, max(zone.min_x, zone.max_x - 1))
        y = random.randint(zone.min_y, max(zone.min_y, zone.max_y - 1))
        return (x, y)

    @staticmethod
    def _allied_factions() -> set[Faction]:
        return {Faction.AMERICAN, Faction.BRITISH, Faction.POLISH}
