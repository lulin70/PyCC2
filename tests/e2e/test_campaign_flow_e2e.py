"""
E2E tests for the full campaign flow — Market Garden four-layer hierarchy.

Validates that the campaign definition, map data, and runtime state
all integrate correctly without requiring pygame/display.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.systems.campaign_four_layer import (
    BattleDefinition,
    BattleState,
    GrandCampaignDefinition,
    GrandCampaignState,
    OperationState,
    SectorState,
    create_market_garden_campaign,
)
from pycc2.domain.systems.cc2_authentic_weapons import Faction

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAPS_DIR = PROJECT_ROOT / "data" / "maps"


@pytest.fixture(scope="module")
def campaign() -> GrandCampaignDefinition:
    return create_market_garden_campaign()


@pytest.fixture(scope="module")
def all_battles(campaign: GrandCampaignDefinition) -> list[BattleDefinition]:
    battles: list[BattleDefinition] = []
    for sector in campaign.sectors:
        for op in sector.operations:
            battles.extend(op.battles)
    return battles


@pytest.fixture(scope="module")
def unique_map_ids(all_battles: list[BattleDefinition]) -> set[str]:
    return {b.map_id for b in all_battles}


# ---------------------------------------------------------------------------
# 1. Campaign creation
# ---------------------------------------------------------------------------


class TestCampaignCreation:
    def test_campaign_creation(self, campaign: GrandCampaignDefinition) -> None:
        assert campaign.campaign_id == "market_garden"
        assert campaign.name == "Operation Market Garden"
        assert len(campaign.sectors) == 3

        sector_ids = {s.sector_id for s in campaign.sectors}
        assert sector_ids == {"arnhem", "nijmegen", "eindhoven"}

        total_ops = sum(len(s.operations) for s in campaign.sectors)
        assert total_ops == 7, f"Expected 7 operations, got {total_ops}"

        total_battles = sum(len(op.battles) for s in campaign.sectors for op in s.operations)
        assert total_battles == 29, f"Expected 29 battles, got {total_battles}"


# ---------------------------------------------------------------------------
# 2. All battle map_ids resolve to loadable JSON files
# ---------------------------------------------------------------------------


class TestBattleMapResolution:
    def test_all_battle_map_ids_resolve(self, all_battles: list[BattleDefinition]) -> None:
        missing: list[str] = []
        for battle in all_battles:
            map_path = MAPS_DIR / f"{battle.map_id}.json"
            if not map_path.exists():
                missing.append(f"{battle.battle_id} -> {battle.map_id}.json")
        assert not missing, f"Missing map files for {len(missing)} battles: {missing[:5]}"


# ---------------------------------------------------------------------------
# 3. All maps load successfully via GameMap.from_json()
# ---------------------------------------------------------------------------


class TestMapLoading:
    def test_all_maps_load_successfully(self, unique_map_ids: set[str]) -> None:
        errors: list[str] = []
        for map_id in sorted(unique_map_ids):
            map_path = MAPS_DIR / f"{map_id}.json"
            try:
                game_map = GameMap.from_json(str(map_path))
                assert game_map.width > 0
                assert game_map.height > 0
            except Exception as exc:
                errors.append(f"{map_id}: {exc}")
        assert not errors, f"Failed to load {len(errors)} maps: {errors[:5]}"


# ---------------------------------------------------------------------------
# 4. Victory locations within map bounds
# ---------------------------------------------------------------------------


class TestVictoryLocationBounds:
    def test_victory_locations_within_map_bounds(self, all_battles: list[BattleDefinition]) -> None:
        violations: list[str] = []
        for battle in all_battles:
            map_path = MAPS_DIR / f"{battle.map_id}.json"
            if not map_path.exists():
                continue
            game_map = GameMap.from_json(str(map_path))
            for vl in battle.victory_locations:
                x, y = vl.position
                if x < 0 or x >= game_map.width or y < 0 or y >= game_map.height:
                    violations.append(
                        f"{battle.battle_id}/{vl.vl_id} pos=({x},{y}) "
                        f"exceeds map {battle.map_id} ({game_map.width}x{game_map.height})"
                    )
        assert not violations, f"VL out-of-bounds in {len(violations)} cases: {violations[:5]}"


# ---------------------------------------------------------------------------
# 5. Campaign day coverage
# ---------------------------------------------------------------------------


class TestCampaignDayCoverage:
    def test_campaign_day_coverage(self, campaign: GrandCampaignDefinition) -> None:
        sector_days: dict[str, set[int]] = {}
        for sector in campaign.sectors:
            days: set[int] = set()
            for op in sector.operations:
                for b in op.battles:
                    days.add(b.day)
            sector_days[sector.sector_id] = days

        # Arnhem and Nijmegen cover Day 1-9; Eindhoven covers Day 1-8
        for sector_id in ("arnhem", "nijmegen"):
            assert sector_id in sector_days, f"Missing sector {sector_id}"
            days = sector_days[sector_id]
            assert 1 in days, f"{sector_id} missing Day 1"
            assert 9 in days, f"{sector_id} missing Day 9"

        assert "eindhoven" in sector_days
        eindhoven_days = sector_days["eindhoven"]
        assert 1 in eindhoven_days, "eindhoven missing Day 1"
        # Eindhoven corridor defense covers Days 4-8 (no Day 9 battle)
        assert eindhoven_days == {1, 2, 3, 4, 6, 8}, (
            f"Unexpected Eindhoven day set: {eindhoven_days}"
        )


# ---------------------------------------------------------------------------
# 6. Battle factions valid
# ---------------------------------------------------------------------------


class TestBattleFactions:
    def test_battle_factions_valid(self, all_battles: list[BattleDefinition]) -> None:
        valid_factions = {Faction.AMERICAN, Faction.BRITISH, Faction.POLISH, Faction.GERMAN}
        for battle in all_battles:
            assert battle.attacker in valid_factions, (
                f"{battle.battle_id} attacker={battle.attacker}"
            )
            assert battle.defender in valid_factions, (
                f"{battle.battle_id} defender={battle.defender}"
            )
            assert battle.attacker != battle.defender, (
                f"{battle.battle_id}: attacker and defender are the same"
            )


# ---------------------------------------------------------------------------
# 7. Requisition points positive
# ---------------------------------------------------------------------------


class TestRequisitionPoints:
    def test_requisition_points_positive(self, campaign: GrandCampaignDefinition) -> None:
        for sector in campaign.sectors:
            for op in sector.operations:
                assert op.requisition_points_allies > 0, (
                    f"{op.operation_id} allies req={op.requisition_points_allies}"
                )
                assert op.requisition_points_axis > 0, (
                    f"{op.operation_id} axis req={op.requisition_points_axis}"
                )


# ---------------------------------------------------------------------------
# 8. GrandCampaignState initialization
# ---------------------------------------------------------------------------


class TestCampaignStateInitialization:
    def test_campaign_state_initialization(self) -> None:
        state = GrandCampaignState()
        assert state.current_day == 1
        assert state.supply_priority_sector == "arnhem"
        assert state.xxx_corps_position == "start"
        assert state.victory_determined is False
        assert len(state.sectors) == 0


# ---------------------------------------------------------------------------
# 9. Sector state transitions
# ---------------------------------------------------------------------------


class TestSectorStateTransitions:
    def test_sector_state_transitions(self) -> None:
        sector = SectorState(sector_id="arnhem", status="pending")
        assert sector.status == "pending"

        sector.status = "active"
        assert sector.status == "active"

        sector.status = "complete"
        assert sector.status == "complete"


# ---------------------------------------------------------------------------
# 10. Battle result persistence
# ---------------------------------------------------------------------------


class TestBattleResultPersistence:
    def test_battle_result_persistence(self) -> None:
        op_state = OperationState(
            operation_id="arnhem_landing",
            status="active",
        )
        assert len(op_state.battle_results) == 0

        battle_result = BattleState(
            battle_id="arnhem_d1_oosterbeek_lz",
            status="allied_victory",
            vl_control={"vl_oosterbeek_lz_1": Faction.BRITISH},
            casualties={
                "BRITISH": {"kia": 3, "wounded": 7},
                "GERMAN": {"kia": 8, "wounded": 12},
            },
            turns_elapsed=15,
        )
        op_state.battle_results.append(battle_result)
        assert len(op_state.battle_results) == 1
        assert op_state.battle_results[0].battle_id == "arnhem_d1_oosterbeek_lz"
        assert op_state.battle_results[0].status == "allied_victory"
        assert op_state.battle_results[0].turns_elapsed == 15
