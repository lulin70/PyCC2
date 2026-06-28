"""Eindhoven sector campaign data — extracted from campaign_data.py (P5-1 batch 1).

Contains 2 operations for the Eindhoven sector of Operation Market Garden.
Built by `build_eindhoven_sector()` returning a `SectorCampaignDefinition`.
"""

from __future__ import annotations

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.campaign_types import (
    BattleDefinition,
    OperationDefinition,
    SectorCampaignDefinition,
    VictoryLocationDef,
)


def build_eindhoven_sector() -> SectorCampaignDefinition:
    """Build the Eindhoven sector with all its operations."""
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
    return eindhoven_sector
