"""
CC2 Authentic Four-Layer Campaign System

Implements the true Close Combat 2 campaign hierarchy:

    GrandCampaign          Full Market Garden, Sept 17-26 1944
      └─ SectorCampaign    Arnhem / Nijmegen / Eindhoven
           └─ Operation    Series of 2-5 battles over days in one area
                └─ Battle  Single engagement on one map

Key CC2 mechanics modeled:
  - Map value system: Bridge=40, Road=30, LZ=20, Regular=10-19
  - Requisition points to buy units (max 9 infantry + 6 support)
  - Ceasefire / Retreat options between battles
  - Supply: Allied airdrops depend on LZ control; German always has land supply
  - Victory: XXX Corps speed to Arnhem + 1st Airborne holding
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

from pycc2.domain.entities.squad import MemberState
from pycc2.domain.entities.unit import Faction

# ========================================================================
# Layer 1 — Battle: Single engagement on one map
# ========================================================================


@dataclass(frozen=True)
class VictoryLocationDef:
    """A victory location on a battle map with point value and type."""

    vl_id: str
    name: str
    position: tuple[int, int]
    value: int  # 10 / 20 / 30 / 40
    vl_type: str  # 'regular', 'landing_zone', 'road', 'bridge'


@dataclass(frozen=True)
class BattleDefinition:
    """Single engagement on one map — the atomic unit of the campaign."""

    battle_id: str
    map_id: str
    name: str
    day: int  # Day 1-9
    sector: str  # 'arnhem', 'nijmegen', 'eindhoven'
    operation_id: str
    attacker: Faction
    defender: Faction
    victory_locations: list[VictoryLocationDef]
    time_of_day: str  # 'dawn', 'day', 'dusk', 'night'
    weather: str  # 'clear', 'overcast', 'rain', 'fog'
    reinforcement_turns: dict[str, list[tuple[int, str]]]  # faction -> [(turn, unit_template_id)]
    map_value: int  # 10-40 points


# ========================================================================
# Layer 2 — Operation: Series of 2-5 battles over days in one area
# ========================================================================


@dataclass(frozen=True)
class OperationDefinition:
    """Series of 2-5 battles over days in one area.

    CC2 mechanics:
      - Requisition points to buy units (max 9 infantry + 6 support)
      - Ceasefire option (1-7 hours rest) between battles
      - Retreat option (risk of capture)
      - Damaged units slowly replenish between battles
    """

    operation_id: str
    name: str
    sector: str
    battles: list[BattleDefinition]
    requisition_points_allies: int
    requisition_points_axis: int
    max_infantry: int = 9
    max_support: int = 6


# ========================================================================
# Layer 3 — SectorCampaign: One of three sectors
# ========================================================================


@dataclass(frozen=True)
class SectorCampaignDefinition:
    """One of three sectors (Arnhem / Nijmegen / Eindhoven).

    CC2 mechanics:
      - Multiple operations running in parallel
      - Arnhem: scored by British/Polish holding
      - Nijmegen/Eindhoven: scored by XXX Corps advance speed
      - Germans capturing LZ blocks Allied supply drops
      - Germans can attack highway after XXX Corps passes
    """

    sector_id: str  # 'arnhem', 'nijmegen', 'eindhoven'
    name: str
    operations: list[OperationDefinition]
    scoring_type: str  # 'holding', 'advance_speed'
    historical_days: tuple[int, int]  # (start_day, end_day)


# ========================================================================
# Layer 4 — GrandCampaign: Full Market Garden
# ========================================================================


@dataclass(frozen=True)
class GrandCampaignDefinition:
    """Full Market Garden, Sept 17-26, 1944.

    CC2 mechanics:
      - Three sectors running simultaneously
      - Daily supply allocation (choose priority sector)
      - German always has land supply
      - Allied: only XXX Corps areas have land supply;
        others need airdrops (blocked if LZ lost)
      - Victory: XXX Corps speed to Arnhem + 1st Airborne holding
    """

    campaign_id: str = "market_garden"
    name: str = "Operation Market Garden"
    start_date: str = "1944-09-17"
    end_date: str = "1944-09-26"
    sectors: list[SectorCampaignDefinition] = field(default_factory=list)
    daily_supply_points: int = 100


# ========================================================================
# Runtime State Classes
# ========================================================================


@dataclass
class BattleState:
    """Runtime state of a single battle."""

    battle_id: str
    status: str  # 'pending', 'active', 'allied_victory', 'axis_victory', 'draw'
    vl_control: dict[str, Faction]  # vl_id -> controlling faction
    casualties: dict[str, dict[str, int]]  # faction_name -> {kia, wounded}
    turns_elapsed: int = 0


@dataclass
class OperationState:
    """Runtime state of an operation (series of battles)."""

    operation_id: str
    status: str  # 'pending', 'active', 'complete'
    current_battle_index: int = 0
    battle_results: list[BattleState] = field(default_factory=list)
    total_victory_points: dict[str, int] = field(default_factory=dict)  # faction_name -> points
    requisition_remaining: dict[str, int] = field(default_factory=dict)
    damaged_units: list[Any] = field(default_factory=list)


@dataclass
class SectorState:
    """Runtime state of a sector campaign."""

    sector_id: str
    status: str  # 'pending', 'active', 'complete'
    operations: list[OperationState] = field(default_factory=list)
    supply_available: bool = True
    lz_controlled: bool = True  # For Arnhem sector


@dataclass
class GrandCampaignState:
    """Runtime state of the full grand campaign."""

    current_day: int = 1
    sectors: dict[str, SectorState] = field(default_factory=dict)
    supply_priority_sector: str = "arnhem"
    xxx_corps_position: str = "start"  # How far XXX Corps has advanced
    victory_determined: bool = False


# ========================================================================
# Factory — DEFAULT_MARKET_GARDEN_CAMPAIGN
# ========================================================================


def create_market_garden_campaign() -> GrandCampaignDefinition:
    """Build the full Market Garden campaign with all three sectors (Day 1-9).

    Arnhem Sector Operations:
      - Op "Landing" (Day 1): Battles at Oosterbeek LZ, Arnhem Rail Bridge, Arnhem Bridge
      - Op "Perimeter Defense" (Days 2-8): Battles at Oosterbeek Caldron,
        Arnhem Suburbs, Arnhem West Approach
      - Op "Evacuation" (Day 9): Battle at Driel Ferry

    Nijmegen Sector Operations:
      - Op "Waal Crossing" (Days 1-4): Landing at Groesbeek, defense against
        Reichswald counterattack, Waal River crossing, Nijmegen Bridge capture
      - Op "Bridge Defense" (Days 5-9): German counterattacks on Nijmegen Bridge

    Eindhoven Sector Operations:
      - Op "Hell's Highway" (Days 1-3): Son Bridge, Veghel landing, XXX Corps
        linkup at Eindhoven, corridor defense
      - Op "Corridor Defense" (Days 4-9): German counterattacks on the corridor
    """

    # ------------------------------------------------------------------
    # Operation 1: Landing (Day 1)
    # ------------------------------------------------------------------
    op_landing_battles: list[BattleDefinition] = [
        BattleDefinition(
            battle_id="arnhem_d1_oosterbeek_lz",
            map_id="oosterbeek_lz",
            name="Oosterbeek Landing Zone",
            day=1,
            sector="arnhem",
            operation_id="arnhem_landing",
            attacker=Faction.BRITISH,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_oosterbeek_lz_1",
                    name="Drop Zone Alpha",
                    position=(5, 10),
                    value=20,
                    vl_type="landing_zone",
                ),
                VictoryLocationDef(
                    vl_id="vl_oosterbeek_lz_2",
                    name="Drop Zone Bravo",
                    position=(8, 14),
                    value=20,
                    vl_type="landing_zone",
                ),
                VictoryLocationDef(
                    vl_id="vl_oosterbeek_lz_3",
                    name="Oosterbeek Church",
                    position=(12, 8),
                    value=10,
                    vl_type="regular",
                ),
            ],
            time_of_day="dawn",
            weather="clear",
            reinforcement_turns={
                "BRITISH": [(1, "brit_rifle_squad"), (2, "brit_rifle_squad"), (3, "brit_mg_team")],
                "GERMAN": [(3, "ger_rifle_squad"), (5, "ger_rifle_squad")],
            },
            map_value=20,
        ),
        BattleDefinition(
            battle_id="arnhem_d1_rail_bridge",
            map_id="arnhem_rail_bridge",
            name="Arnhem Rail Bridge",
            day=1,
            sector="arnhem",
            operation_id="arnhem_landing",
            attacker=Faction.BRITISH,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_rail_bridge",
                    name="Rail Bridge",
                    position=(15, 10),
                    value=30,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_rail_approach",
                    name="Rail Approach Road",
                    position=(10, 10),
                    value=10,
                    vl_type="road",
                ),
            ],
            time_of_day="day",
            weather="clear",
            reinforcement_turns={
                "BRITISH": [(1, "brit_rifle_squad"), (2, "brit_rifle_squad")],
                "GERMAN": [(2, "ger_rifle_squad"), (4, "ger_at_team")],
            },
            map_value=30,
        ),
        BattleDefinition(
            battle_id="arnhem_d1_arnhem_bridge",
            map_id="arnhem",
            name="Arnhem Bridge",
            day=1,
            sector="arnhem",
            operation_id="arnhem_landing",
            attacker=Faction.BRITISH,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_arnhem_bridge_north",
                    name="Bridge North End",
                    position=(12, 5),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_arnhem_bridge_south",
                    name="Bridge South End",
                    position=(12, 15),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_bridge_road",
                    name="Bridge Approach Road",
                    position=(12, 10),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="dusk",
            weather="clear",
            reinforcement_turns={
                "BRITISH": [
                    (1, "brit_rifle_squad"),
                    (2, "brit_rifle_squad"),
                    (3, "brit_rifle_squad"),
                ],
                "GERMAN": [(2, "ger_rifle_squad"), (3, "ger_rifle_squad"), (5, "ger_armor")],
            },
            map_value=40,
        ),
        BattleDefinition(
            battle_id="arnhem_d1_zoo",
            map_id="arnhem_zoo",
            name="Arnhem Zoo",
            day=1,
            sector="arnhem",
            operation_id="arnhem_landing",
            attacker=Faction.BRITISH,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_zoo_gate",
                    name="Zoo Main Gate",
                    position=(8, 10),
                    value=15,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_zoo_walls",
                    name="Zoo Thick Walls",
                    position=(10, 8),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_zoo_road",
                    name="Zoo Approach Road",
                    position=(6, 12),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="day",
            weather="clear",
            reinforcement_turns={
                "BRITISH": [(1, "brit_rifle_squad"), (2, "brit_rifle_squad"), (3, "brit_mg_team")],
                "GERMAN": [(2, "ger_rifle_squad"), (4, "ger_rifle_squad")],
            },
            map_value=19,
        ),
        BattleDefinition(
            battle_id="arnhem_d1_koepel",
            map_id="arnhem_koepel",
            name="Arnhem Koepel",
            day=1,
            sector="arnhem",
            operation_id="arnhem_landing",
            attacker=Faction.BRITISH,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_koepel_church",
                    name="Koepel Church",
                    position=(10, 10),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_koepel_square",
                    name="Church Square",
                    position=(12, 8),
                    value=15,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_koepel_road",
                    name="Koepel Road Junction",
                    position=(8, 12),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="dusk",
            weather="overcast",
            reinforcement_turns={
                "BRITISH": [(1, "brit_rifle_squad"), (2, "brit_rifle_squad")],
                "GERMAN": [(2, "ger_rifle_squad"), (3, "ger_at_team")],
            },
            map_value=19,
        ),
    ]

    op_landing = OperationDefinition(
        operation_id="arnhem_landing",
        name="Landing",
        sector="arnhem",
        battles=op_landing_battles,
        requisition_points_allies=200,
        requisition_points_axis=120,
    )

    # ------------------------------------------------------------------
    # Operation 2: Perimeter Defense (Days 2-8)
    # ------------------------------------------------------------------
    op_perimeter_battles: list[BattleDefinition] = [
        BattleDefinition(
            battle_id="arnhem_d2_oosterbeek_caldron",
            map_id="oosterbeek_caldron",
            name="Oosterbeek Caldron",
            day=2,
            sector="arnhem",
            operation_id="arnhem_perimeter",
            attacker=Faction.GERMAN,
            defender=Faction.BRITISH,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_caldron_church",
                    name="Oosterbeek Church",
                    position=(10, 10),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_caldron_hotel",
                    name="Hartenstein Hotel",
                    position=(8, 12),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_caldron_lz",
                    name="Perimeter LZ",
                    position=(5, 8),
                    value=20,
                    vl_type="landing_zone",
                ),
            ],
            time_of_day="day",
            weather="overcast",
            reinforcement_turns={
                "GERMAN": [(1, "ger_rifle_squad"), (2, "ger_rifle_squad"), (3, "ger_armor")],
                "BRITISH": [(3, "brit_rifle_squad"), (5, "brit_rifle_squad")],
            },
            map_value=19,
        ),
        BattleDefinition(
            battle_id="arnhem_d3_oosterbeek_north",
            map_id="oosterbeek_north",
            name="Oosterbeek North",
            day=3,
            sector="arnhem",
            operation_id="arnhem_perimeter",
            attacker=Faction.GERMAN,
            defender=Faction.BRITISH,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_oosterbeek_north_bridge",
                    name="Rail-Road Junction Bridge",
                    position=(10, 6),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_oosterbeek_north_road",
                    name="North Approach Road",
                    position=(8, 10),
                    value=30,
                    vl_type="road",
                ),
                VictoryLocationDef(
                    vl_id="vl_oosterbeek_north_village",
                    name="North Village",
                    position=(12, 8),
                    value=15,
                    vl_type="regular",
                ),
            ],
            time_of_day="dawn",
            weather="overcast",
            reinforcement_turns={
                "GERMAN": [(1, "ger_rifle_squad"), (2, "ger_rifle_squad"), (3, "ger_armor")],
                "BRITISH": [(2, "brit_rifle_squad"), (4, "brit_rifle_squad")],
            },
            map_value=40,
        ),
        BattleDefinition(
            battle_id="arnhem_d4_arnhem_suburbs",
            map_id="arnhem_suburbs",
            name="Arnhem Suburbs",
            day=4,
            sector="arnhem",
            operation_id="arnhem_perimeter",
            attacker=Faction.GERMAN,
            defender=Faction.BRITISH,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_suburbs_crossroads",
                    name="Suburb Crossroads",
                    position=(12, 8),
                    value=15,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_suburbs_road",
                    name="Main Road Junction",
                    position=(10, 12),
                    value=30,
                    vl_type="road",
                ),
                VictoryLocationDef(
                    vl_id="vl_suburbs_station",
                    name="Railway Station",
                    position=(14, 6),
                    value=19,
                    vl_type="regular",
                ),
            ],
            time_of_day="day",
            weather="rain",
            reinforcement_turns={
                "GERMAN": [(1, "ger_rifle_squad"), (2, "ger_armor"), (4, "ger_rifle_squad")],
                "BRITISH": [(2, "brit_rifle_squad"), (4, "brit_at_team")],
            },
            map_value=15,
        ),
        BattleDefinition(
            battle_id="arnhem_d5_tree_road",
            map_id="arnhem_tree_road",
            name="Arnhem Tree Road",
            day=5,
            sector="arnhem",
            operation_id="arnhem_perimeter",
            attacker=Faction.GERMAN,
            defender=Faction.BRITISH,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_tree_road_bridge",
                    name="River Bridge",
                    position=(10, 10),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_tree_road_south",
                    name="South Bank Key Area",
                    position=(10, 14),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_tree_road_north",
                    name="Tree-Lined Road",
                    position=(8, 6),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="day",
            weather="rain",
            reinforcement_turns={
                "GERMAN": [(1, "ger_rifle_squad"), (2, "ger_rifle_squad"), (3, "ger_armor")],
                "BRITISH": [(2, "brit_rifle_squad"), (4, "brit_rifle_squad")],
            },
            map_value=40,
        ),
        BattleDefinition(
            battle_id="arnhem_d5_st_elizabeth",
            map_id="arnhem_st_elizabeth",
            name="St Elizabeth Hospital",
            day=5,
            sector="arnhem",
            operation_id="arnhem_perimeter",
            attacker=Faction.GERMAN,
            defender=Faction.BRITISH,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_st_elizabeth_main",
                    name="Hospital Main Building",
                    position=(10, 10),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_st_elizabeth_ward",
                    name="Hospital Ward",
                    position=(12, 8),
                    value=15,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_st_elizabeth_road",
                    name="Hospital Access Road",
                    position=(8, 12),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="dusk",
            weather="overcast",
            reinforcement_turns={
                "GERMAN": [(1, "ger_rifle_squad"), (2, "ger_rifle_squad"), (3, "ger_armor")],
                "BRITISH": [(2, "brit_rifle_squad"), (4, "brit_mg_team")],
            },
            map_value=19,
        ),
        BattleDefinition(
            battle_id="arnhem_d6_west_approach",
            map_id="arnhem_west_approach",
            name="Arnhem West Approach",
            day=6,
            sector="arnhem",
            operation_id="arnhem_perimeter",
            attacker=Faction.GERMAN,
            defender=Faction.BRITISH,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_west_road",
                    name="West Approach Road",
                    position=(6, 10),
                    value=30,
                    vl_type="road",
                ),
                VictoryLocationDef(
                    vl_id="vl_west_village",
                    name="West Village",
                    position=(4, 8),
                    value=15,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_west_lz",
                    name="Western LZ",
                    position=(3, 12),
                    value=20,
                    vl_type="landing_zone",
                ),
            ],
            time_of_day="dawn",
            weather="fog",
            reinforcement_turns={
                "GERMAN": [
                    (1, "ger_rifle_squad"),
                    (2, "ger_rifle_squad"),
                    (3, "ger_armor"),
                    (5, "ger_armor"),
                ],
                "BRITISH": [(3, "brit_rifle_squad"), (5, "brit_rifle_squad")],
                "POLISH": [(4, "pol_rifle_squad"), (5, "pol_rifle_squad")],
            },
            map_value=30,
        ),
        BattleDefinition(
            battle_id="arnhem_d7_perimeter_shrink",
            map_id="oosterbeek_perimeter",
            name="Shrinking Perimeter",
            day=7,
            sector="arnhem",
            operation_id="arnhem_perimeter",
            attacker=Faction.GERMAN,
            defender=Faction.BRITISH,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_perimeter_hq",
                    name="Division HQ",
                    position=(8, 10),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_perimeter_lz",
                    name="Supply LZ",
                    position=(6, 8),
                    value=20,
                    vl_type="landing_zone",
                ),
                VictoryLocationDef(
                    vl_id="vl_perimeter_road",
                    name="Perimeter Road",
                    position=(10, 12),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="day",
            weather="overcast",
            reinforcement_turns={
                "GERMAN": [
                    (1, "ger_rifle_squad"),
                    (2, "ger_armor"),
                    (3, "ger_rifle_squad"),
                    (4, "ger_armor"),
                ],
                "BRITISH": [(3, "brit_rifle_squad")],
            },
            map_value=19,
        ),
        BattleDefinition(
            battle_id="arnhem_d8_last_stand",
            map_id="oosterbeek_last_stand",
            name="Last Stand at Oosterbeek",
            day=8,
            sector="arnhem",
            operation_id="arnhem_perimeter",
            attacker=Faction.GERMAN,
            defender=Faction.BRITISH,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_last_river_bank",
                    name="Rhine River Bank",
                    position=(4, 10),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_last_church",
                    name="Oosterbeek Church",
                    position=(8, 8),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_last_lz",
                    name="Final LZ",
                    position=(6, 6),
                    value=20,
                    vl_type="landing_zone",
                ),
            ],
            time_of_day="dusk",
            weather="rain",
            reinforcement_turns={
                "GERMAN": [
                    (1, "ger_rifle_squad"),
                    (2, "ger_rifle_squad"),
                    (3, "ger_armor"),
                    (4, "ger_armor"),
                ],
                "BRITISH": [],
                "POLISH": [(2, "pol_rifle_squad")],
            },
            map_value=19,
        ),
    ]

    op_perimeter = OperationDefinition(
        operation_id="arnhem_perimeter",
        name="Perimeter Defense",
        sector="arnhem",
        battles=op_perimeter_battles,
        requisition_points_allies=300,
        requisition_points_axis=250,
    )

    # ------------------------------------------------------------------
    # Operation 3: Evacuation (Day 9)
    # ------------------------------------------------------------------
    op_evacuation_battles: list[BattleDefinition] = [
        BattleDefinition(
            battle_id="arnhem_d9_driel_ferry",
            map_id="driel_ferry",
            name="Driel Ferry Crossing",
            day=9,
            sector="arnhem",
            operation_id="arnhem_evacuation",
            attacker=Faction.BRITISH,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_driel_ferry",
                    name="Driel Ferry",
                    position=(10, 5),
                    value=30,
                    vl_type="road",
                ),
                VictoryLocationDef(
                    vl_id="vl_driel_bank",
                    name="South Bank",
                    position=(10, 15),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_driel_road",
                    name="Escape Road",
                    position=(6, 10),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="night",
            weather="rain",
            reinforcement_turns={
                "BRITISH": [(1, "brit_rifle_squad"), (2, "brit_rifle_squad")],
                "POLISH": [(1, "pol_rifle_squad"), (2, "pol_rifle_squad")],
                "GERMAN": [(2, "ger_rifle_squad"), (3, "ger_rifle_squad"), (4, "ger_armor")],
            },
            map_value=30,
        ),
        BattleDefinition(
            battle_id="arnhem_d9_rail_bridge",
            map_id="oosterbeek_rail_bridge",
            name="Oosterbeek Rail Bridge",
            day=9,
            sector="arnhem",
            operation_id="arnhem_evacuation",
            attacker=Faction.BRITISH,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_rail_bridge_evac",
                    name="Rail Bridge",
                    position=(10, 8),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_rail_bridge_north",
                    name="North Bank Approach",
                    position=(10, 4),
                    value=30,
                    vl_type="road",
                ),
                VictoryLocationDef(
                    vl_id="vl_rail_bridge_south",
                    name="South Bank Escape Route",
                    position=(10, 12),
                    value=19,
                    vl_type="regular",
                ),
            ],
            time_of_day="night",
            weather="rain",
            reinforcement_turns={
                "BRITISH": [(1, "brit_rifle_squad"), (2, "brit_rifle_squad")],
                "POLISH": [(1, "pol_rifle_squad")],
                "GERMAN": [(2, "ger_rifle_squad"), (3, "ger_rifle_squad"), (3, "ger_armor")],
            },
            map_value=40,
        ),
    ]

    op_evacuation = OperationDefinition(
        operation_id="arnhem_evacuation",
        name="Evacuation",
        sector="arnhem",
        battles=op_evacuation_battles,
        requisition_points_allies=100,
        requisition_points_axis=200,
    )

    # ------------------------------------------------------------------
    # Arnhem Sector
    # ------------------------------------------------------------------
    arnhem_sector = SectorCampaignDefinition(
        sector_id="arnhem",
        name="Arnhem Sector",
        operations=[op_landing, op_perimeter, op_evacuation],
        scoring_type="holding",
        historical_days=(1, 9),
    )

    # ------------------------------------------------------------------
    # NIJMEGEN SECTOR
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Nijmegen Operation 1: Waal Crossing (Days 1-4)
    # ------------------------------------------------------------------
    op_waal_crossing_battles: list[BattleDefinition] = [
        BattleDefinition(
            battle_id="nijmegen_d1_groesbeek_lz",
            map_id="nijmegen",
            name="Landing at Groesbeek",
            day=1,
            sector="nijmegen",
            operation_id="nijmegen_waal_crossing",
            attacker=Faction.AMERICAN,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_groesbeek_lz_north",
                    name="Drop Zone North",
                    position=(6, 8),
                    value=20,
                    vl_type="landing_zone",
                ),
                VictoryLocationDef(
                    vl_id="vl_groesbeek_lz_south",
                    name="Drop Zone South",
                    position=(6, 14),
                    value=20,
                    vl_type="landing_zone",
                ),
                VictoryLocationDef(
                    vl_id="vl_groesbeek_village",
                    name="Groesbeek Village",
                    position=(10, 10),
                    value=15,
                    vl_type="regular",
                ),
            ],
            time_of_day="dawn",
            weather="clear",
            reinforcement_turns={
                "AMERICAN": [
                    (1, "us_para_rifle_squad_82nd"),
                    (2, "us_para_rifle_squad_82nd"),
                    (3, "us_para_mg_30cal"),
                ],
                "GERMAN": [(3, "ger_rifle_squad"), (5, "ger_rifle_squad")],
            },
            map_value=20,
        ),
        BattleDefinition(
            battle_id="nijmegen_d2_reichswald_defense",
            map_id="schijndel_road",
            name="Defense against Reichswald Counterattack",
            day=2,
            sector="nijmegen",
            operation_id="nijmegen_waal_crossing",
            attacker=Faction.GERMAN,
            defender=Faction.AMERICAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_reichswald_road",
                    name="Reichswald Road",
                    position=(8, 10),
                    value=30,
                    vl_type="road",
                ),
                VictoryLocationDef(
                    vl_id="vl_reichswald_woods",
                    name="Woods Position",
                    position=(4, 8),
                    value=15,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_reichswald_crossroads",
                    name="Groesbeek Crossroads",
                    position=(12, 12),
                    value=19,
                    vl_type="regular",
                ),
            ],
            time_of_day="day",
            weather="overcast",
            reinforcement_turns={
                "GERMAN": [(1, "ger_rifle_squad"), (2, "ger_rifle_squad"), (3, "ger_armor")],
                "AMERICAN": [(3, "us_para_rifle_squad_82nd"), (5, "us_para_at_bazooka")],
            },
            map_value=30,
        ),
        BattleDefinition(
            battle_id="nijmegen_d3_waal_crossing",
            map_id="grave",
            name="Assault Crossing of the Waal River",
            day=3,
            sector="nijmegen",
            operation_id="nijmegen_waal_crossing",
            attacker=Faction.AMERICAN,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_waal_north_bank",
                    name="North Bank Landing",
                    position=(10, 5),
                    value=20,
                    vl_type="landing_zone",
                ),
                VictoryLocationDef(
                    vl_id="vl_waal_south_bank",
                    name="South Bank Departure",
                    position=(10, 15),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_waal_river",
                    name="Waal River Crossing Point",
                    position=(10, 10),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="day",
            weather="clear",
            reinforcement_turns={
                "AMERICAN": [
                    (1, "us_para_rifle_squad_82nd"),
                    (2, "us_para_rifle_squad_82nd"),
                    (3, "us_para_rifle_squad_82nd"),
                ],
                "BRITISH": [(2, "brit_rifle_squad"), (4, "brit_armor")],
                "GERMAN": [(2, "ger_rifle_squad"), (3, "ger_rifle_squad"), (5, "ger_at_team")],
            },
            map_value=30,
        ),
        BattleDefinition(
            battle_id="nijmegen_d4_bridge_capture",
            map_id="nijmegen",
            name="Capture of Nijmegen Bridge",
            day=4,
            sector="nijmegen",
            operation_id="nijmegen_waal_crossing",
            attacker=Faction.AMERICAN,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_nijmegen_bridge_north",
                    name="Bridge North End",
                    position=(12, 5),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_nijmegen_bridge_south",
                    name="Bridge South End",
                    position=(12, 15),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_nijmegen_approach",
                    name="Bridge Approach Road",
                    position=(12, 10),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="dusk",
            weather="clear",
            reinforcement_turns={
                "AMERICAN": [
                    (1, "us_para_rifle_squad_82nd"),
                    (2, "us_para_rifle_squad_82nd"),
                    (3, "us_para_at_bazooka"),
                ],
                "BRITISH": [(2, "brit_armor"), (4, "brit_rifle_squad")],
                "GERMAN": [(2, "ger_rifle_squad"), (3, "ger_armor"), (5, "ger_armor")],
            },
            map_value=40,
        ),
    ]

    op_waal_crossing = OperationDefinition(
        operation_id="nijmegen_waal_crossing",
        name="Waal Crossing",
        sector="nijmegen",
        battles=op_waal_crossing_battles,
        requisition_points_allies=250,
        requisition_points_axis=150,
    )

    # ------------------------------------------------------------------
    # Nijmegen Operation 2: Bridge Defense (Days 5-9)
    # ------------------------------------------------------------------
    op_bridge_defense_battles: list[BattleDefinition] = [
        BattleDefinition(
            battle_id="nijmegen_d5_bridge_counterattack",
            map_id="nijmegen",
            name="German Counterattack on Nijmegen Bridge",
            day=5,
            sector="nijmegen",
            operation_id="nijmegen_bridge_defense",
            attacker=Faction.GERMAN,
            defender=Faction.AMERICAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_nijmegen_def_north",
                    name="Bridge North End",
                    position=(12, 5),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_nijmegen_def_south",
                    name="Bridge South End",
                    position=(12, 15),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_nijmegen_def_road",
                    name="Bridge Approach Road",
                    position=(12, 10),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="dawn",
            weather="overcast",
            reinforcement_turns={
                "GERMAN": [
                    (1, "ger_rifle_squad"),
                    (2, "ger_rifle_squad"),
                    (3, "ger_armor"),
                    (5, "ger_armor"),
                ],
                "AMERICAN": [(3, "us_para_rifle_squad_82nd"), (5, "us_para_at_bazooka")],
                "BRITISH": [(2, "brit_armor"), (4, "brit_rifle_squad")],
            },
            map_value=40,
        ),
        BattleDefinition(
            battle_id="nijmegen_d7_bridgehead_defense",
            map_id="schijndel_road",
            name="Defense of the Bridgehead",
            day=7,
            sector="nijmegen",
            operation_id="nijmegen_bridge_defense",
            attacker=Faction.GERMAN,
            defender=Faction.BRITISH,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_bridgehead_road",
                    name="Bridgehead Road",
                    position=(8, 10),
                    value=30,
                    vl_type="road",
                ),
                VictoryLocationDef(
                    vl_id="vl_bridgehead_village",
                    name="Bridgehead Village",
                    position=(6, 8),
                    value=15,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_bridgehead_crossroads",
                    name="Northern Crossroads",
                    position=(10, 6),
                    value=19,
                    vl_type="regular",
                ),
            ],
            time_of_day="day",
            weather="rain",
            reinforcement_turns={
                "GERMAN": [
                    (1, "ger_rifle_squad"),
                    (2, "ger_armor"),
                    (3, "ger_rifle_squad"),
                    (4, "ger_armor"),
                ],
                "BRITISH": [(2, "brit_rifle_squad"), (4, "brit_rifle_squad")],
                "AMERICAN": [(3, "us_para_rifle_squad_82nd")],
            },
            map_value=30,
        ),
        BattleDefinition(
            battle_id="nijmegen_d9_final_assault_repulsed",
            map_id="nijmegen",
            name="Final German Assault Repulsed",
            day=9,
            sector="nijmegen",
            operation_id="nijmegen_bridge_defense",
            attacker=Faction.GERMAN,
            defender=Faction.AMERICAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_final_bridge_north",
                    name="Bridge North End",
                    position=(12, 5),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_final_bridge_south",
                    name="Bridge South End",
                    position=(12, 15),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_final_approach",
                    name="Bridge Approach Road",
                    position=(12, 10),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="day",
            weather="overcast",
            reinforcement_turns={
                "GERMAN": [
                    (1, "ger_rifle_squad"),
                    (2, "ger_rifle_squad"),
                    (3, "ger_armor"),
                    (4, "ger_armor"),
                    (5, "ger_armor"),
                ],
                "AMERICAN": [(3, "us_para_rifle_squad_82nd"), (5, "us_para_at_bazooka")],
                "BRITISH": [(2, "brit_armor"), (4, "brit_rifle_squad")],
            },
            map_value=40,
        ),
    ]

    op_bridge_defense = OperationDefinition(
        operation_id="nijmegen_bridge_defense",
        name="Bridge Defense",
        sector="nijmegen",
        battles=op_bridge_defense_battles,
        requisition_points_allies=300,
        requisition_points_axis=250,
    )

    # ------------------------------------------------------------------
    # Nijmegen Sector
    # ------------------------------------------------------------------
    nijmegen_sector = SectorCampaignDefinition(
        sector_id="nijmegen",
        name="Nijmegen Sector",
        operations=[op_waal_crossing, op_bridge_defense],
        scoring_type="advance_speed",
        historical_days=(1, 9),
    )

    # ------------------------------------------------------------------
    # EINDHOVEN SECTOR
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Eindhoven Operation 1: Hell's Highway (Days 1-3)
    # ------------------------------------------------------------------
    op_hells_highway_battles: list[BattleDefinition] = [
        BattleDefinition(
            battle_id="eindhoven_d1_son_bridge",
            map_id="son_town",
            name="Son Bridge Capture",
            day=1,
            sector="eindhoven",
            operation_id="eindhoven_hells_highway",
            attacker=Faction.AMERICAN,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_son_bridge_north",
                    name="Son Bridge North",
                    position=(10, 5),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_son_bridge_south",
                    name="Son Bridge South",
                    position=(10, 15),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_son_road",
                    name="Son Main Road",
                    position=(10, 10),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="dawn",
            weather="clear",
            reinforcement_turns={
                "AMERICAN": [
                    (1, "us_para_rifle_squad_101st"),
                    (2, "us_para_rifle_squad_101st"),
                    (3, "us_para_mg_30cal"),
                ],
                "GERMAN": [(2, "ger_rifle_squad"), (4, "ger_at_team"), (5, "ger_rifle_squad")],
            },
            map_value=40,
        ),
        BattleDefinition(
            battle_id="eindhoven_d1_veghel_landing",
            map_id="veghel",
            name="Veghel Landing and Defense",
            day=1,
            sector="eindhoven",
            operation_id="eindhoven_hells_highway",
            attacker=Faction.AMERICAN,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_veghel_lz",
                    name="Veghel Drop Zone",
                    position=(6, 10),
                    value=20,
                    vl_type="landing_zone",
                ),
                VictoryLocationDef(
                    vl_id="vl_veghel_village",
                    name="Veghel Village",
                    position=(10, 8),
                    value=15,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_veghel_road",
                    name="Veghel Crossroads",
                    position=(8, 12),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="day",
            weather="clear",
            reinforcement_turns={
                "AMERICAN": [
                    (1, "us_para_rifle_squad_101st"),
                    (2, "us_para_rifle_squad_101st"),
                    (3, "us_para_mg_30cal"),
                ],
                "GERMAN": [(3, "ger_rifle_squad"), (5, "ger_rifle_squad")],
            },
            map_value=20,
        ),
        BattleDefinition(
            battle_id="eindhoven_d2_xxx_corps_linkup",
            map_id="eindhoven_city",
            name="XXX Corps Links Up at Eindhoven",
            day=2,
            sector="eindhoven",
            operation_id="eindhoven_hells_highway",
            attacker=Faction.BRITISH,
            defender=Faction.GERMAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_eindhoven_center",
                    name="Eindhoven City Center",
                    position=(12, 10),
                    value=19,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_eindhoven_north_road",
                    name="North Road Junction",
                    position=(12, 5),
                    value=30,
                    vl_type="road",
                ),
                VictoryLocationDef(
                    vl_id="vl_eindhoven_south_road",
                    name="South Road Junction",
                    position=(12, 15),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="day",
            weather="overcast",
            reinforcement_turns={
                "BRITISH": [(1, "brit_rifle_squad"), (2, "brit_armor"), (3, "brit_rifle_squad")],
                "AMERICAN": [(2, "us_para_rifle_squad_101st"), (4, "us_para_at_bazooka")],
                "GERMAN": [(2, "ger_rifle_squad"), (4, "ger_at_team")],
            },
            map_value=30,
        ),
        BattleDefinition(
            battle_id="eindhoven_d3_corridor_defense",
            map_id="arnhem_best",
            name="Defense of the Corridor",
            day=3,
            sector="eindhoven",
            operation_id="eindhoven_hells_highway",
            attacker=Faction.GERMAN,
            defender=Faction.AMERICAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_best_road",
                    name="Best Road Junction",
                    position=(8, 10),
                    value=30,
                    vl_type="road",
                ),
                VictoryLocationDef(
                    vl_id="vl_best_village",
                    name="Best Village",
                    position=(6, 8),
                    value=15,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_best_crossroads",
                    name="Corridor Crossroads",
                    position=(10, 12),
                    value=19,
                    vl_type="regular",
                ),
            ],
            time_of_day="day",
            weather="overcast",
            reinforcement_turns={
                "GERMAN": [(1, "ger_rifle_squad"), (2, "ger_rifle_squad"), (3, "ger_armor")],
                "AMERICAN": [(2, "us_para_rifle_squad_101st"), (4, "us_para_at_bazooka")],
                "BRITISH": [(3, "brit_armor")],
            },
            map_value=30,
        ),
    ]

    op_hells_highway = OperationDefinition(
        operation_id="eindhoven_hells_highway",
        name="Hell's Highway",
        sector="eindhoven",
        battles=op_hells_highway_battles,
        requisition_points_allies=250,
        requisition_points_axis=120,
    )

    # ------------------------------------------------------------------
    # Eindhoven Operation 2: Corridor Defense (Days 4-9)
    # ------------------------------------------------------------------
    op_corridor_defense_battles: list[BattleDefinition] = [
        BattleDefinition(
            battle_id="eindhoven_d4_veghel_counterattack",
            map_id="veghel",
            name="German Counterattack on Veghel",
            day=4,
            sector="eindhoven",
            operation_id="eindhoven_corridor_defense",
            attacker=Faction.GERMAN,
            defender=Faction.AMERICAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_veghel_def_lz",
                    name="Veghel Drop Zone",
                    position=(6, 10),
                    value=20,
                    vl_type="landing_zone",
                ),
                VictoryLocationDef(
                    vl_id="vl_veghel_def_village",
                    name="Veghel Village",
                    position=(10, 8),
                    value=15,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_veghel_def_road",
                    name="Veghel Crossroads",
                    position=(8, 12),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="dawn",
            weather="overcast",
            reinforcement_turns={
                "GERMAN": [(1, "ger_rifle_squad"), (2, "ger_rifle_squad"), (3, "ger_armor")],
                "AMERICAN": [(2, "us_para_rifle_squad_101st"), (4, "us_para_at_bazooka")],
                "BRITISH": [(3, "brit_armor")],
            },
            map_value=30,
        ),
        BattleDefinition(
            battle_id="eindhoven_d6_schijndel_defense",
            map_id="schijndel_road",
            name="Defense of the Corridor near Schijndel",
            day=6,
            sector="eindhoven",
            operation_id="eindhoven_corridor_defense",
            attacker=Faction.GERMAN,
            defender=Faction.BRITISH,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_schijndel_road",
                    name="Schijndel Road",
                    position=(8, 10),
                    value=30,
                    vl_type="road",
                ),
                VictoryLocationDef(
                    vl_id="vl_schijndel_village",
                    name="Schijndel Village",
                    position=(6, 8),
                    value=15,
                    vl_type="regular",
                ),
                VictoryLocationDef(
                    vl_id="vl_schijndel_crossroads",
                    name="Corridor Crossroads",
                    position=(10, 12),
                    value=19,
                    vl_type="regular",
                ),
            ],
            time_of_day="day",
            weather="rain",
            reinforcement_turns={
                "GERMAN": [
                    (1, "ger_rifle_squad"),
                    (2, "ger_armor"),
                    (3, "ger_rifle_squad"),
                    (5, "ger_armor"),
                ],
                "BRITISH": [(2, "brit_rifle_squad"), (4, "brit_rifle_squad")],
                "AMERICAN": [(3, "us_para_rifle_squad_101st")],
            },
            map_value=30,
        ),
        BattleDefinition(
            battle_id="eindhoven_d8_son_assault",
            map_id="son_town",
            name="Final German Assault on Corridor",
            day=8,
            sector="eindhoven",
            operation_id="eindhoven_corridor_defense",
            attacker=Faction.GERMAN,
            defender=Faction.AMERICAN,
            victory_locations=[
                VictoryLocationDef(
                    vl_id="vl_son_def_bridge_north",
                    name="Son Bridge North",
                    position=(10, 5),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_son_def_bridge_south",
                    name="Son Bridge South",
                    position=(10, 15),
                    value=40,
                    vl_type="bridge",
                ),
                VictoryLocationDef(
                    vl_id="vl_son_def_road",
                    name="Son Main Road",
                    position=(10, 10),
                    value=30,
                    vl_type="road",
                ),
            ],
            time_of_day="dusk",
            weather="overcast",
            reinforcement_turns={
                "GERMAN": [
                    (1, "ger_rifle_squad"),
                    (2, "ger_rifle_squad"),
                    (3, "ger_armor"),
                    (4, "ger_armor"),
                ],
                "AMERICAN": [(2, "us_para_rifle_squad_101st"), (4, "us_para_at_bazooka")],
                "BRITISH": [(3, "brit_armor"), (5, "brit_rifle_squad")],
            },
            map_value=40,
        ),
    ]

    op_corridor_defense = OperationDefinition(
        operation_id="eindhoven_corridor_defense",
        name="Corridor Defense",
        sector="eindhoven",
        battles=op_corridor_defense_battles,
        requisition_points_allies=300,
        requisition_points_axis=200,
    )

    # ------------------------------------------------------------------
    # Eindhoven Sector
    # ------------------------------------------------------------------
    eindhoven_sector = SectorCampaignDefinition(
        sector_id="eindhoven",
        name="Eindhoven Sector",
        operations=[op_hells_highway, op_corridor_defense],
        scoring_type="advance_speed",
        historical_days=(1, 9),
    )

    # ------------------------------------------------------------------
    # Grand Campaign
    # ------------------------------------------------------------------
    return GrandCampaignDefinition(
        campaign_id="market_garden",
        name="Operation Market Garden",
        start_date="1944-09-17",
        end_date="1944-09-26",
        sectors=[arnhem_sector, nijmegen_sector, eindhoven_sector],
        daily_supply_points=100,
    )


# Pre-built default instance
DEFAULT_MARKET_GARDEN_CAMPAIGN = create_market_garden_campaign()


# ========================================================================
# FourLayerCampaignManager — Campaign orchestration with unit carryover
# ========================================================================

# Supply line resupply rates (ammo is NOT fully resupplied)
_SUPPLY_LINE_AMMO_RESUPPLY = {
    "allies_land": 0.60,  # XXX Corps land supply: 60% ammo resupply
    "allies_airdrop": 0.40,  # Airdrop supply: 40% ammo resupply
    "allies_no_supply": 0.15,  # No supply line: 15% ammo resupply (scrounging)
    "axis_land": 0.50,  # German land supply: 50% ammo resupply
}

_HP_RECOVERY_PER_DAY = 0.20  # 20% HP recovery between days for wounded


@dataclass
class UnitCarryoverState:
    """Persistent state of a unit that carries over between battles."""

    unit_id: str
    faction: str
    is_alive: bool = True
    current_hp: float = 100.0
    max_hp: float = 100.0
    morale: float = 100.0
    experience: int = 0
    ammo_remaining: int = 0
    max_ammo: int = 0
    kills: int = 0
    status: str = "active"  # 'active', 'wounded', 'kia', 'mia'

    # Squad-level carryover
    squad_members_alive: int = 0
    squad_members_wounded: int = 0
    squad_members_dead: int = 0
    squad_total_size: int = 0


class FourLayerCampaignManager:
    """Manages the four-layer campaign with battle-to-battle unit carryover.

    CC2 mechanics:
      - KIA soldiers are removed from the squad permanently
      - WIA soldiers start the next battle with reduced HP
      - Surviving soldiers keep their experience gains
      - Ammo is NOT fully resupplied (only partially, based on supply lines)
    """

    def __init__(self, campaign_def: GrandCampaignDefinition | None = None) -> None:
        self._campaign_def = campaign_def or DEFAULT_MARKET_GARDEN_CAMPAIGN
        self._campaign_state = GrandCampaignState()
        self._saved_unit_states: dict[str, UnitCarryoverState] = {}
        self._persistence = None

    @property
    def campaign_definition(self) -> GrandCampaignDefinition:
        return self._campaign_def

    @property
    def campaign_state(self) -> GrandCampaignState:
        return self._campaign_state

    @property
    def saved_unit_states(self) -> dict[str, UnitCarryoverState]:
        return self._saved_unit_states

    def get_battles_for_day(self, day: int) -> list[BattleDefinition]:
        """Get all battles scheduled for a specific day across all sectors."""
        battles: list[BattleDefinition] = []
        for sector in self._campaign_def.sectors:
            for operation in sector.operations:
                for battle in operation.battles:
                    if battle.day == day:
                        battles.append(battle)
        return battles

    def get_operation_for_battle(self, battle_id: str) -> OperationDefinition | None:
        """Find the operation containing a given battle."""
        for sector in self._campaign_def.sectors:
            for operation in sector.operations:
                for battle in operation.battles:
                    if battle.battle_id == battle_id:
                        return operation
        return None

    def get_sector_for_battle(self, battle_id: str) -> SectorCampaignDefinition | None:
        """Find the sector containing a given battle."""
        for sector in self._campaign_def.sectors:
            for operation in sector.operations:
                for battle in operation.battles:
                    if battle.battle_id == battle_id:
                        return sector
        return None

    def advance_day(self) -> None:
        """Advance the campaign to the next day."""
        self._campaign_state.current_day += 1
        if self._campaign_state.current_day > 9:
            self._campaign_state.current_day = 9
            self._campaign_state.victory_determined = True

    def _get_supply_type(self, faction: str, sector_id: str) -> str:
        """Determine supply line type for a faction in a sector."""
        if faction.lower() in ("german", "axis"):
            return "axis_land"

        sector_state = self._campaign_state.sectors.get(sector_id)
        if sector_id == "eindhoven":
            # XXX Corps advances through Eindhoven — land supply
            return "allies_land"
        elif sector_id == "nijmegen":
            # After bridge capture, land supply; before that, airdrop
            if sector_state and sector_state.lz_controlled:
                return "allies_airdrop"
            return "allies_airdrop"
        elif sector_id == "arnhem":
            # Arnhem relies on airdrops; if LZ lost, minimal supply
            if sector_state and not sector_state.lz_controlled:
                return "allies_no_supply"
            return "allies_airdrop"
        return "allies_airdrop"

    # ------------------------------------------------------------------
    # Core carryover methods
    # ------------------------------------------------------------------

    def _save_battle_results(
        self,
        battle_id: str,
        units: list,
    ) -> None:
        """Save each unit's state after a battle ends.

        Captures HP, morale, ammo, experience, KIA/WIA status for carryover
        to the next battle.

        Args:
            battle_id: The battle that just ended
            units: List of Unit objects from the completed battle
        """
        for unit in units:
            unit_id = getattr(unit, "id", None) or getattr(unit, "unit_id", str(id(unit)))

            # Determine faction
            faction = "allies"
            if hasattr(unit, "faction"):
                f = unit.faction
                faction = f.name.lower() if hasattr(f, "name") else str(f).lower()

            # Determine alive status
            is_alive = True
            if hasattr(unit, "is_alive"):
                is_alive = unit.is_alive
            elif hasattr(unit, "health"):
                is_alive = unit.health.is_alive

            # Get HP
            current_hp = 100.0
            max_hp = 100.0
            if hasattr(unit, "health_component"):
                current_hp = float(unit.health_component.hp)
                max_hp = float(unit.health_component.max_hp)
            elif hasattr(unit, "health"):
                current_hp = float(unit.health.hp)
                max_hp = float(unit.health.max_hp)

            # Get morale
            morale = 100.0
            if hasattr(unit, "morale_component"):
                morale = float(unit.morale_component.value)
            elif hasattr(unit, "morale"):
                morale = float(getattr(unit.morale, "value", 100))

            # Get experience
            experience = 0
            kills = 0
            if hasattr(unit, "veterancy_component") and unit.veterancy_component is not None:
                experience = unit.veterancy_component.xp
                kills = unit.veterancy_component.kills
            elif hasattr(unit, "veterancy") and unit.veterancy is not None:
                experience = unit.veterancy.xp
                kills = unit.veterancy.kills

            # Get ammo
            ammo_remaining = 0
            max_ammo = 0
            if hasattr(unit, "weapon_component") and unit.weapon_component is not None:
                ammo_remaining = unit.weapon_component.ammo_remaining
                max_ammo = unit.weapon_component.max_ammo
            elif hasattr(unit, "weapon") and unit.weapon is not None:
                ammo_remaining = unit.weapon.ammo_remaining
                max_ammo = unit.weapon.max_ammo

            # Determine status
            status = "active"
            if not is_alive:
                status = "kia"
            elif current_hp / max(max_hp, 1) < 0.7:
                status = "wounded"

            # Squad-level carryover
            squad_alive = 0
            squad_wounded = 0
            squad_dead = 0
            squad_total = 0
            if hasattr(unit, "squad_ref") and unit.squad_ref is not None:
                squad = unit.squad_ref
                squad_alive = squad.alive_count
                squad_wounded = squad.wounded_count
                squad_dead = squad.dead_count
                squad_total = squad.size

            carryover = UnitCarryoverState(
                unit_id=unit_id,
                faction=faction,
                is_alive=is_alive,
                current_hp=current_hp,
                max_hp=max_hp,
                morale=morale,
                experience=experience,
                ammo_remaining=ammo_remaining,
                max_ammo=max_ammo,
                kills=kills,
                status=status,
                squad_members_alive=squad_alive,
                squad_members_wounded=squad_wounded,
                squad_members_dead=squad_dead,
                squad_total_size=squad_total,
            )
            self._saved_unit_states[unit_id] = carryover

    def _load_unit_states_for_battle(
        self,
        battle_id: str,
        units: list,
    ) -> list:
        """Apply saved unit states to the new battle's units.

        Carryover rules (CC2 authentic):
          - KIA soldiers are removed from the squad permanently
          - WIA soldiers start the next battle with reduced HP
          - Surviving soldiers keep their experience gains
          - Ammo is NOT fully resupplied (only partially, based on supply lines)

        Args:
            battle_id: The battle about to start
            units: List of Unit objects for the new battle

        Returns:
            Updated units with inherited stats
        """
        if not self._saved_unit_states:
            return units

        # Find the sector for supply line determination
        sector = self.get_sector_for_battle(battle_id)
        sector_id = sector.sector_id if sector else "arnhem"

        inherited_count = 0

        for unit in units:
            unit_id = getattr(unit, "id", None) or getattr(unit, "unit_id", str(id(unit)))
            saved = self._saved_unit_states.get(unit_id)

            if saved is None:
                continue

            if not saved.is_alive:
                # KIA: Remove from squad permanently
                if hasattr(unit, "health_component"):
                    unit.health_component.hp = 0
                    unit.health_component._update_state()
                elif hasattr(unit, "health"):
                    unit.health.hp = 0
                    unit.health._update_state()

                if hasattr(unit, "state_machine"):
                    from pycc2.domain.entities.unit import UnitState

                    try:
                        unit.state_machine.force_transition(UnitState.DEAD)
                    except Exception as e:
                        logging.warning(f"Unit state transition to DEAD failed: {e}")

                # Remove dead members from squad
                if hasattr(unit, "squad_ref") and unit.squad_ref is not None:
                    unit.squad_ref.remove_dead()

                inherited_count += 1
                continue

            # --- Alive unit: Apply carryover ---

            # HP: WIA soldiers start with reduced HP
            if saved.status == "wounded":
                # Wounded soldiers recover partially between battles
                recovery = saved.max_hp * _HP_RECOVERY_PER_DAY
                new_hp = min(saved.max_hp, saved.current_hp + recovery)
            else:
                # Healthy soldiers keep their HP
                new_hp = saved.current_hp

            if hasattr(unit, "health_component"):
                unit.health_component.hp = int(new_hp)
                unit.health_component._update_state()
            elif hasattr(unit, "health"):
                unit.health.hp = int(new_hp)
                unit.health._update_state()

            # Morale: Partial recovery between battles
            morale_recovery = min(20, 10 + self._campaign_state.current_day * 2)
            new_morale = min(100, int(saved.morale + morale_recovery))
            if hasattr(unit, "morale_component"):
                unit.morale_component.value = new_morale
                unit.morale_component._update_state()
            elif hasattr(unit, "morale"):
                unit.morale.value = new_morale
                unit.morale._update_state()

            # Experience: Surviving soldiers keep their experience gains
            if saved.experience > 0:
                if hasattr(unit, "veterancy_component") and unit.veterancy_component is not None:
                    unit.veterancy_component.add_xp(saved.experience)
                elif hasattr(unit, "veterancy") and unit.veterancy is not None:
                    unit.veterancy.add_xp(saved.experience)

            if saved.kills > 0:
                if hasattr(unit, "veterancy_component") and unit.veterancy_component is not None:
                    unit.veterancy_component.kills += saved.kills
                elif hasattr(unit, "veterancy") and unit.veterancy is not None:
                    unit.veterancy.kills += saved.kills

            # Ammo: NOT fully resupplied — partial resupply based on supply lines
            faction = saved.faction
            supply_type = self._get_supply_type(faction, sector_id)
            resupply_rate = _SUPPLY_LINE_AMMO_RESUPPLY.get(supply_type, 0.3)
            ammo_resupply = int(saved.max_ammo * resupply_rate)
            new_ammo = min(saved.max_ammo, saved.ammo_remaining + ammo_resupply)

            if hasattr(unit, "weapon_component") and unit.weapon_component is not None:
                unit.weapon_component.ammo_remaining = new_ammo
                unit.weapon_component._update_state()
            elif hasattr(unit, "weapon") and unit.weapon is not None:
                unit.weapon.ammo_remaining = new_ammo
                unit.weapon._update_state()

            # Squad-level carryover: Remove KIA members, keep WIA
            if hasattr(unit, "squad_ref") and unit.squad_ref is not None:
                squad = unit.squad_ref
                # Remove dead members from previous battle
                squad.remove_dead()
                # Wounded members keep their wounded state
                for member in squad.members:
                    if member.state == MemberState.WOUNDED:
                        # Wounded soldiers recover partially
                        member.hp = min(100, member.hp + 20)

            inherited_count += 1

        return units

    def get_campaign_summary(self) -> dict:
        """Generate a summary of the campaign outcome.

        Returns a dict with:
          - result: 'ALLIES_VICTORY' / 'AXIS_VICTORY' / 'DRAW'
          - day_ended: the day the campaign ended (1-9)
          - allied_casualties: dict with 'kia' and 'wia' counts
          - axis_casualties: dict with 'kia' and 'wia' counts
          - bridge_status: dict mapping bridge VL names to
            'captured_allied' / 'captured_axis' / 'destroyed' / 'contested'
        """
        state = self._campaign_state

        # --- Determine overall result ---
        # Count victory points across all sectors
        allied_vp = 0
        axis_vp = 0
        for sector_state in state.sectors.values():
            for op_state in sector_state.operations:
                for faction_name, pts in op_state.total_victory_points.items():
                    fname = faction_name.lower()
                    if fname in ("allies", "british", "american", "polish"):
                        allied_vp += pts
                    elif fname in ("axis", "german"):
                        axis_vp += pts

        # Also factor in XXX Corps position for advance_speed sectors
        xxx_pos = state.xxx_corps_position
        if xxx_pos in ("arnhem", "oosterbeek"):
            allied_vp += 100
        elif xxx_pos in ("nijmegen",):
            allied_vp += 50
        elif xxx_pos in ("eindhoven",):
            allied_vp += 25

        if allied_vp > axis_vp * 1.5:
            result = "ALLIES_VICTORY"
        elif axis_vp > allied_vp * 1.5:
            result = "AXIS_VICTORY"
        else:
            result = "DRAW"

        # --- Count casualties from saved unit states ---
        allied_kia = 0
        allied_wia = 0
        axis_kia = 0
        axis_wia = 0
        for unit_state in self._saved_unit_states.values():
            faction = unit_state.faction.lower()
            if faction in ("allies", "british", "american", "polish"):
                if unit_state.status == "kia":
                    allied_kia += 1
                elif unit_state.status == "wounded":
                    allied_wia += 1
            elif faction in ("axis", "german"):
                if unit_state.status == "kia":
                    axis_kia += 1
                elif unit_state.status == "wounded":
                    axis_wia += 1

        # --- Bridge status ---
        bridge_status: dict[str, str] = {}
        for sector in self._campaign_def.sectors:
            for operation in sector.operations:
                for battle in operation.battles:
                    for vl in battle.victory_locations:
                        if vl.vl_type == "bridge":
                            # Check VL control from battle state
                            sector_state = state.sectors.get(sector.sector_id)
                            controlled_by = None
                            if sector_state:
                                for op_state in sector_state.operations:
                                    for bs in op_state.battle_results:
                                        ctrl = bs.vl_control.get(vl.vl_id)
                                        if ctrl is not None:
                                            fname = ctrl.name.lower()
                                            if fname in ("allies", "british", "american", "polish"):
                                                controlled_by = "captured_allied"
                                            elif fname in ("axis", "german"):
                                                controlled_by = "captured_axis"
                                            else:
                                                controlled_by = "contested"

                            if controlled_by is None:
                                controlled_by = "contested"
                            bridge_status[vl.name] = controlled_by

        return {
            "result": result,
            "day_ended": state.current_day,
            "allied_casualties": {"kia": allied_kia, "wia": allied_wia},
            "axis_casualties": {"kia": axis_kia, "wia": axis_wia},
            "bridge_status": bridge_status,
        }
