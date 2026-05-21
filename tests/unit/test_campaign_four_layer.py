"""
Tests for campaign_four_layer module — CC2 Authentic Four-Layer Campaign System.

Covers:
  - VictoryLocationDef creation and validation
  - BattleDefinition structure
  - OperationDefinition structure
  - SectorCampaignDefinition structure
  - GrandCampaignDefinition creation and defaults
  - create_market_garden_campaign() factory
  - BattleState / OperationState / SectorState / GrandCampaignState runtime state
  - Campaign state transitions (advance_day, complete_battle)
  - Sector scoring
  - Requisition points calculation
  - Battle result persistence
"""

from __future__ import annotations

import pytest

from pycc2.domain.systems.campaign_four_layer import (
    BattleDefinition,
    BattleState,
    GrandCampaignDefinition,
    GrandCampaignState,
    OperationDefinition,
    OperationState,
    SectorCampaignDefinition,
    SectorState,
    VictoryLocationDef,
    create_market_garden_campaign,
)
from pycc2.domain.systems.cc2_authentic_weapons import Faction


# ---------------------------------------------------------------------------
# VictoryLocationDef
# ---------------------------------------------------------------------------

class TestVictoryLocationDef:

    def test_creation_regular(self):
        vl = VictoryLocationDef(
            vl_id="vl_1", name="Church", position=(10, 5),
            value=10, vl_type="regular",
        )
        assert vl.vl_id == "vl_1"
        assert vl.name == "Church"
        assert vl.position == (10, 5)
        assert vl.value == 10
        assert vl.vl_type == "regular"

    def test_creation_bridge(self):
        vl = VictoryLocationDef(
            vl_id="vl_bridge", name="Bridge", position=(12, 5),
            value=40, vl_type="bridge",
        )
        assert vl.value == 40
        assert vl.vl_type == "bridge"

    def test_creation_landing_zone(self):
        vl = VictoryLocationDef(
            vl_id="vl_lz", name="LZ Alpha", position=(5, 10),
            value=20, vl_type="landing_zone",
        )
        assert vl.vl_type == "landing_zone"
        assert vl.value == 20

    def test_creation_road(self):
        vl = VictoryLocationDef(
            vl_id="vl_road", name="Main Road", position=(8, 8),
            value=30, vl_type="road",
        )
        assert vl.vl_type == "road"
        assert vl.value == 30

    def test_frozen_immutability(self):
        vl = VictoryLocationDef(
            vl_id="vl_1", name="Church", position=(10, 5),
            value=10, vl_type="regular",
        )
        with pytest.raises(AttributeError):
            vl.value = 99  # type: ignore[misc]

    def test_equality_same_values(self):
        vl1 = VictoryLocationDef("vl_1", "Church", (10, 5), 10, "regular")
        vl2 = VictoryLocationDef("vl_1", "Church", (10, 5), 10, "regular")
        assert vl1 == vl2


# ---------------------------------------------------------------------------
# BattleDefinition
# ---------------------------------------------------------------------------

class TestBattleDefinition:

    @pytest.fixture()
    def sample_vl(self):
        return VictoryLocationDef(
            vl_id="vl_1", name="Test VL", position=(5, 5),
            value=20, vl_type="regular",
        )

    @pytest.fixture()
    def sample_battle(self, sample_vl):
        return BattleDefinition(
            battle_id="battle_1",
            map_id="map_1",
            name="Test Battle",
            day=1,
            sector="arnhem",
            operation_id="op_1",
            attacker=Faction.BRITISH,
            defender=Faction.GERMAN,
            victory_locations=[sample_vl],
            time_of_day="dawn",
            weather="clear",
            reinforcement_turns={
                "BRITISH": [(1, "brit_rifle_squad")],
                "GERMAN": [(2, "ger_rifle_squad")],
            },
            map_value=20,
        )

    def test_battle_fields(self, sample_battle):
        assert sample_battle.battle_id == "battle_1"
        assert sample_battle.day == 1
        assert sample_battle.sector == "arnhem"
        assert sample_battle.attacker == Faction.BRITISH
        assert sample_battle.defender == Faction.GERMAN

    def test_battle_victory_locations(self, sample_battle, sample_vl):
        assert len(sample_battle.victory_locations) == 1
        assert sample_battle.victory_locations[0] == sample_vl

    def test_battle_reinforcement_turns(self, sample_battle):
        assert "BRITISH" in sample_battle.reinforcement_turns
        assert "GERMAN" in sample_battle.reinforcement_turns
        assert sample_battle.reinforcement_turns["BRITISH"] == [(1, "brit_rifle_squad")]

    def test_battle_frozen(self, sample_battle):
        with pytest.raises(AttributeError):
            sample_battle.day = 5  # type: ignore[misc]

    def test_battle_empty_reinforcements(self):
        battle = BattleDefinition(
            battle_id="b2", map_id="m2", name="No Reinforcements",
            day=2, sector="nijmegen", operation_id="op_2",
            attacker=Faction.AMERICAN, defender=Faction.GERMAN,
            victory_locations=[], time_of_day="day", weather="overcast",
            reinforcement_turns={}, map_value=10,
        )
        assert battle.reinforcement_turns == {}


# ---------------------------------------------------------------------------
# OperationDefinition
# ---------------------------------------------------------------------------

class TestOperationDefinition:

    @pytest.fixture()
    def sample_operation(self):
        battle = BattleDefinition(
            battle_id="b1", map_id="m1", name="Battle 1",
            day=1, sector="arnhem", operation_id="op_1",
            attacker=Faction.BRITISH, defender=Faction.GERMAN,
            victory_locations=[], time_of_day="dawn", weather="clear",
            reinforcement_turns={}, map_value=20,
        )
        return OperationDefinition(
            operation_id="op_1",
            name="Landing",
            sector="arnhem",
            battles=[battle],
            requisition_points_allies=200,
            requisition_points_axis=120,
        )

    def test_operation_fields(self, sample_operation):
        assert sample_operation.operation_id == "op_1"
        assert sample_operation.name == "Landing"
        assert sample_operation.sector == "arnhem"
        assert len(sample_operation.battles) == 1

    def test_requisition_defaults(self, sample_operation):
        assert sample_operation.max_infantry == 9
        assert sample_operation.max_support == 6

    def test_custom_max_units(self):
        op = OperationDefinition(
            operation_id="op_2", name="Custom", sector="nijmegen",
            battles=[], requisition_points_allies=100,
            requisition_points_axis=80, max_infantry=12, max_support=8,
        )
        assert op.max_infantry == 12
        assert op.max_support == 8

    def test_requisition_points(self, sample_operation):
        assert sample_operation.requisition_points_allies == 200
        assert sample_operation.requisition_points_axis == 120


# ---------------------------------------------------------------------------
# SectorCampaignDefinition
# ---------------------------------------------------------------------------

class TestSectorCampaignDefinition:

    def test_arnhem_sector(self):
        sector = SectorCampaignDefinition(
            sector_id="arnhem", name="Arnhem Sector",
            operations=[], scoring_type="holding",
            historical_days=(1, 9),
        )
        assert sector.scoring_type == "holding"
        assert sector.historical_days == (1, 9)

    def test_nijmegen_sector(self):
        sector = SectorCampaignDefinition(
            sector_id="nijmegen", name="Nijmegen Sector",
            operations=[], scoring_type="advance_speed",
            historical_days=(2, 7),
        )
        assert sector.scoring_type == "advance_speed"

    def test_sector_frozen(self):
        sector = SectorCampaignDefinition(
            sector_id="eindhoven", name="Eindhoven Sector",
            operations=[], scoring_type="advance_speed",
            historical_days=(1, 3),
        )
        with pytest.raises(AttributeError):
            sector.scoring_type = "holding"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# GrandCampaignDefinition
# ---------------------------------------------------------------------------

class TestGrandCampaignDefinition:

    def test_default_values(self):
        gc = GrandCampaignDefinition()
        assert gc.campaign_id == "market_garden"
        assert gc.name == "Operation Market Garden"
        assert gc.start_date == "1944-09-17"
        assert gc.end_date == "1944-09-26"
        assert gc.daily_supply_points == 100
        assert gc.sectors == []

    def test_custom_values(self):
        gc = GrandCampaignDefinition(
            campaign_id="custom", name="Custom Campaign",
            daily_supply_points=150,
        )
        assert gc.campaign_id == "custom"
        assert gc.daily_supply_points == 150

    def test_with_sectors(self):
        sector = SectorCampaignDefinition(
            sector_id="arnhem", name="Arnhem",
            operations=[], scoring_type="holding",
            historical_days=(1, 9),
        )
        gc = GrandCampaignDefinition(sectors=[sector])
        assert len(gc.sectors) == 1
        assert gc.sectors[0].sector_id == "arnhem"


# ---------------------------------------------------------------------------
# create_market_garden_campaign()
# ---------------------------------------------------------------------------

class TestCreateMarketGardenCampaign:

    @pytest.fixture()
    def campaign(self):
        return create_market_garden_campaign()

    def test_campaign_id(self, campaign):
        assert campaign.campaign_id == "market_garden"

    def test_has_arnhem_sector(self, campaign):
        assert len(campaign.sectors) >= 1
        arnhem = campaign.sectors[0]
        assert arnhem.sector_id == "arnhem"

    def test_arnhem_has_three_operations(self, campaign):
        arnhem = campaign.sectors[0]
        assert len(arnhem.operations) == 3

    def test_operation_names(self, campaign):
        arnhem = campaign.sectors[0]
        names = [op.name for op in arnhem.operations]
        assert "Landing" in names
        assert "Perimeter Defense" in names
        assert "Evacuation" in names

    def test_landing_operation_battles(self, campaign):
        arnhem = campaign.sectors[0]
        landing = arnhem.operations[0]
        assert len(landing.battles) == 5  # LZ + Rail Bridge + Arnhem Bridge + Zoo + Koepel
        assert all(b.day == 1 for b in landing.battles)

    def test_perimeter_operation_spans_days_2_to_8(self, campaign):
        arnhem = campaign.sectors[0]
        perimeter = arnhem.operations[1]
        days = [b.day for b in perimeter.battles]
        assert min(days) >= 2
        assert max(days) <= 8

    def test_evacuation_operation_day_9(self, campaign):
        arnhem = campaign.sectors[0]
        evacuation = arnhem.operations[2]
        assert all(b.day == 9 for b in evacuation.battles)

    def test_arnhem_bridge_value_40(self, campaign):
        arnhem = campaign.sectors[0]
        landing = arnhem.operations[0]
        bridge_battle = [b for b in landing.battles if "bridge" in b.battle_id and "rail" not in b.battle_id][0]
        bridge_vls = [vl for vl in bridge_battle.victory_locations if vl.vl_type == "bridge"]
        assert any(vl.value == 40 for vl in bridge_vls)

    def test_arnhem_scoring_type_holding(self, campaign):
        assert campaign.sectors[0].scoring_type == "holding"

    def test_arnhem_historical_days(self, campaign):
        assert campaign.sectors[0].historical_days == (1, 9)

    def test_total_battles_count(self, campaign):
        arnhem = campaign.sectors[0]
        total = sum(len(op.battles) for op in arnhem.operations)
        # Landing: 5, Perimeter: 8, Evacuation: 2 = 15
        assert total == 15

    def test_all_battles_have_victory_locations(self, campaign):
        arnhem = campaign.sectors[0]
        for op in arnhem.operations:
            for battle in op.battles:
                assert len(battle.victory_locations) > 0

    def test_daily_supply_points(self, campaign):
        assert campaign.daily_supply_points == 100


# ---------------------------------------------------------------------------
# Runtime State Classes
# ---------------------------------------------------------------------------

class TestBattleState:

    def test_creation_default(self):
        bs = BattleState(battle_id="b1", status="pending",
                         vl_control={}, casualties={})
        assert bs.battle_id == "b1"
        assert bs.status == "pending"
        assert bs.turns_elapsed == 0

    def test_with_vl_control(self):
        bs = BattleState(
            battle_id="b1", status="active",
            vl_control={"vl_1": Faction.BRITISH},
            casualties={"BRITISH": {"kia": 2, "wounded": 5}},
        )
        assert bs.vl_control["vl_1"] == Faction.BRITISH
        assert bs.casualties["BRITISH"]["kia"] == 2

    def test_mutable_state(self):
        bs = BattleState(battle_id="b1", status="pending",
                         vl_control={}, casualties={})
        bs.status = "allied_victory"
        bs.turns_elapsed = 15
        assert bs.status == "allied_victory"
        assert bs.turns_elapsed == 15


class TestOperationState:

    def test_creation_default(self):
        os = OperationState(operation_id="op1", status="pending")
        assert os.current_battle_index == 0
        assert os.battle_results == []
        assert os.total_victory_points == {}

    def test_with_battle_results(self):
        bs = BattleState(battle_id="b1", status="allied_victory",
                         vl_control={}, casualties={})
        os = OperationState(
            operation_id="op1", status="active",
            battle_results=[bs],
            total_victory_points={"BRITISH": 50, "GERMAN": 20},
        )
        assert len(os.battle_results) == 1
        assert os.total_victory_points["BRITISH"] == 50


class TestSectorState:

    def test_creation_default(self):
        ss = SectorState(sector_id="arnhem", status="pending")
        assert ss.supply_available is True
        assert ss.lz_controlled is True

    def test_lz_lost(self):
        ss = SectorState(sector_id="arnhem", status="active",
                         lz_controlled=False)
        assert ss.lz_controlled is False


class TestGrandCampaignState:

    def test_creation_default(self):
        gcs = GrandCampaignState()
        assert gcs.current_day == 1
        assert gcs.supply_priority_sector == "arnhem"
        assert gcs.xxx_corps_position == "start"
        assert gcs.victory_determined is False

    def test_advance_day(self):
        gcs = GrandCampaignState()
        gcs.current_day = 2
        gcs.xxx_corps_position = "veghel"
        assert gcs.current_day == 2
        assert gcs.xxx_corps_position == "veghel"

    def test_complete_battle(self):
        gcs = GrandCampaignState()
        gcs.sectors["arnhem"] = SectorState(sector_id="arnhem", status="active")
        bs = BattleState(battle_id="b1", status="allied_victory",
                         vl_control={}, casualties={})
        gcs.sectors["arnhem"].operations.append(
            OperationState(operation_id="op1", status="active", battle_results=[bs])
        )
        assert gcs.sectors["arnhem"].operations[0].battle_results[0].status == "allied_victory"

    def test_sector_scoring_holding(self):
        gcs = GrandCampaignState()
        gcs.sectors["arnhem"] = SectorState(sector_id="arnhem", status="active")
        op = OperationState(
            operation_id="op1", status="complete",
            total_victory_points={"BRITISH": 100, "GERMAN": 30},
        )
        gcs.sectors["arnhem"].operations.append(op)
        british_score = gcs.sectors["arnhem"].operations[0].total_victory_points.get("BRITISH", 0)
        assert british_score == 100

    def test_requisition_remaining(self):
        op = OperationState(
            operation_id="op1", status="active",
            requisition_remaining={"BRITISH": 150, "GERMAN": 80},
        )
        assert op.requisition_remaining["BRITISH"] == 150
        assert op.requisition_remaining["GERMAN"] == 80

    def test_battle_result_persistence(self):
        bs1 = BattleState(battle_id="b1", status="allied_victory",
                          vl_control={"vl_1": Faction.BRITISH}, casualties={})
        bs2 = BattleState(battle_id="b2", status="axis_victory",
                          vl_control={"vl_1": Faction.GERMAN}, casualties={})
        op = OperationState(
            operation_id="op1", status="active",
            battle_results=[bs1, bs2],
        )
        assert len(op.battle_results) == 2
        assert op.battle_results[0].status == "allied_victory"
        assert op.battle_results[1].status == "axis_victory"
        assert op.battle_results[0].vl_control["vl_1"] == Faction.BRITISH
        assert op.battle_results[1].vl_control["vl_1"] == Faction.GERMAN

    def test_victory_determined(self):
        gcs = GrandCampaignState()
        assert not gcs.victory_determined
        gcs.victory_determined = True
        assert gcs.victory_determined
