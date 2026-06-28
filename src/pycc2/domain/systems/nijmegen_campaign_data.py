"""Nijmegen sector campaign data — extracted from campaign_data.py (P5-1 batch 1).

Contains 2 operations for the Nijmegen sector of Operation Market Garden.
Built by `build_nijmegen_sector()` returning a `SectorCampaignDefinition`.
"""

from __future__ import annotations

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.campaign_types import (
    BattleDefinition,
    OperationDefinition,
    SectorCampaignDefinition,
    VictoryLocationDef,
)


def build_nijmegen_sector() -> SectorCampaignDefinition:
    """Build the Nijmegen sector with all its operations."""
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
    return nijmegen_sector
