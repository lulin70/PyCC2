"""Market Garden campaign data — factory function with all battle/operation/sector definitions.

This module contains the complete Market Garden campaign data (~1400 lines of battle
definitions organized into operations and sectors).

See campaign_types.py for type definitions.
See campaign_four_layer.py for FourLayerCampaignManager engine.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.campaign_types import (
    BattleDefinition,
    GrandCampaignDefinition,
    OperationDefinition,
    SectorCampaignDefinition,
    VictoryLocationDef,
)

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
# Supply / recovery constants used by FourLayerCampaignManager
# ========================================================================

# Supply line resupply rates (ammo is NOT fully resupplied)
_SUPPLY_LINE_AMMO_RESUPPLY = {
    "allies_land": 0.60,  # XXX Corps land supply: 60% ammo resupply
    "allies_airdrop": 0.40,  # Airdrop supply: 40% ammo resupply
    "allies_no_supply": 0.15,  # No supply line: 15% ammo resupply (scrounging)
    "axis_land": 0.50,  # German land supply: 50% ammo resupply
}

_HP_RECOVERY_PER_DAY = 0.20  # 20% HP recovery between days for wounded
