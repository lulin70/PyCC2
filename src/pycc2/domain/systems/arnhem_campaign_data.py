"""Arnhem sector campaign data — extracted from campaign_data.py (P5-1 batch 1).

Contains 3 operations for the Arnhem sector of Operation Market Garden.
Built by `build_arnhem_sector()` returning a `SectorCampaignDefinition`.
"""

from __future__ import annotations

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.campaign_types import (
    BattleDefinition,
    OperationDefinition,
    SectorCampaignDefinition,
    VictoryLocationDef,
)


def build_arnhem_sector() -> SectorCampaignDefinition:
    """Build the Arnhem sector with all its operations."""
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
    return arnhem_sector
