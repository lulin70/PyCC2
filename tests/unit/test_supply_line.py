"""
Tests for supply_line module — CC2 Supply Line System.

Covers:
  - SupplyType enum values
  - SupplyLevel enum values
  - SupplyState creation and calculate_supply()
  - XXXCorpsPosition enum values
  - XXX_CORPS_TIMELINE historical accuracy
  - SupplyLineManager creation
  - advance_day() updates positions correctly
  - Sector supply calculation (Eindhoven on Day 2, Nijmegen on Day 5, Arnhem never)
  - Priority allocation
  - Supply distribution
"""

from __future__ import annotations

import pytest

from pycc2.domain.systems.supply_line import (
    XXX_CORPS_TIMELINE,
    SupplyLevel,
    SupplyLineManager,
    SupplyState,
    SupplyType,
    XXXCorpsPosition,
)

# ---------------------------------------------------------------------------
# SupplyType enum
# ---------------------------------------------------------------------------


class TestSupplyType:
    def test_has_land(self):
        assert SupplyType.LAND is not None

    def test_has_airdrop(self):
        assert SupplyType.AIRDROP is not None

    def test_has_blocked(self):
        assert SupplyType.BLOCKED is not None

    def test_three_values(self):
        assert len(SupplyType) == 3

    def test_distinct_values(self):
        vals = [s.value for s in SupplyType]
        assert len(set(vals)) == 3


# ---------------------------------------------------------------------------
# SupplyLevel enum
# ---------------------------------------------------------------------------


class TestSupplyLevel:
    def test_has_full(self):
        assert SupplyLevel.FULL is not None

    def test_has_reduced(self):
        assert SupplyLevel.REDUCED is not None

    def test_has_minimal(self):
        assert SupplyLevel.MINIMAL is not None

    def test_has_none(self):
        assert SupplyLevel.NONE is not None

    def test_four_values(self):
        assert len(SupplyLevel) == 4


# ---------------------------------------------------------------------------
# SupplyState
# ---------------------------------------------------------------------------


class TestSupplyState:
    def test_creation_defaults(self):
        ss = SupplyState(sector_id="arnhem", day=1)
        assert ss.sector_id == "arnhem"
        assert ss.day == 1
        assert ss.supply_type == SupplyType.BLOCKED
        assert ss.supply_level == SupplyLevel.NONE
        assert ss.lz_controlled is True
        assert ss.xxx_corps_reached is False
        assert ss.ammo_replenishment_rate == 0.0
        assert ss.reinforcement_rate == 0.0
        assert ss.morale_recovery_rate == 0.0

    def test_calculate_supply_land(self):
        ss = SupplyState(sector_id="eindhoven", day=2, supply_type=SupplyType.LAND)
        result = ss.calculate_supply()
        assert result == SupplyLevel.FULL
        assert ss.ammo_replenishment_rate == 1.0
        assert ss.reinforcement_rate == 1.0
        assert ss.morale_recovery_rate == 0.8

    def test_calculate_supply_airdrop_lz_controlled(self):
        ss = SupplyState(
            sector_id="arnhem",
            day=1,
            supply_type=SupplyType.AIRDROP,
            lz_controlled=True,
        )
        result = ss.calculate_supply()
        assert result == SupplyLevel.REDUCED
        assert ss.ammo_replenishment_rate == 0.6
        assert ss.reinforcement_rate == 0.4
        assert ss.morale_recovery_rate == 0.5

    def test_calculate_supply_airdrop_lz_lost(self):
        ss = SupplyState(
            sector_id="arnhem",
            day=3,
            supply_type=SupplyType.AIRDROP,
            lz_controlled=False,
        )
        result = ss.calculate_supply()
        assert result == SupplyLevel.NONE
        assert ss.ammo_replenishment_rate == 0.0
        assert ss.reinforcement_rate == 0.0
        assert ss.morale_recovery_rate == 0.1

    def test_calculate_supply_blocked(self):
        ss = SupplyState(sector_id="arnhem", day=1, supply_type=SupplyType.BLOCKED)
        result = ss.calculate_supply()
        assert result == SupplyLevel.NONE
        assert ss.ammo_replenishment_rate == 0.0
        assert ss.reinforcement_rate == 0.0
        assert ss.morale_recovery_rate == 0.1

    def test_lz_name_field(self):
        ss = SupplyState(
            sector_id="arnhem",
            day=1,
            lz_controlled=True,
            lz_name="LZ-S/DZ-X",
        )
        assert ss.lz_name == "LZ-S/DZ-X"

    def test_mutable_state(self):
        ss = SupplyState(sector_id="arnhem", day=1)
        ss.supply_type = SupplyType.LAND
        ss.calculate_supply()
        assert ss.supply_level == SupplyLevel.FULL


# ---------------------------------------------------------------------------
# XXXCorpsPosition enum
# ---------------------------------------------------------------------------


class TestXXXCorpsPosition:
    def test_has_all_positions(self):
        assert XXXCorpsPosition.START is not None
        assert XXXCorpsPosition.VEGHEL is not None
        assert XXXCorpsPosition.SON is not None
        assert XXXCorpsPosition.GRAVE is not None
        assert XXXCorpsPosition.NIJMEGEN is not None
        assert XXXCorpsPosition.ELST is not None
        assert XXXCorpsPosition.ARNHEM_SOUTH is not None

    def test_seven_positions(self):
        assert len(XXXCorpsPosition) == 7


# ---------------------------------------------------------------------------
# XXX_CORPS_TIMELINE
# ---------------------------------------------------------------------------


class TestXXXCorpsTimeline:
    def test_day_1_start(self):
        assert XXX_CORPS_TIMELINE[1] == XXXCorpsPosition.START

    def test_day_2_veghel(self):
        assert XXX_CORPS_TIMELINE[2] == XXXCorpsPosition.VEGHEL

    def test_day_3_son(self):
        assert XXX_CORPS_TIMELINE[3] == XXXCorpsPosition.SON

    def test_day_4_grave(self):
        assert XXX_CORPS_TIMELINE[4] == XXXCorpsPosition.GRAVE

    def test_day_5_nijmegen(self):
        assert XXX_CORPS_TIMELINE[5] == XXXCorpsPosition.NIJMEGEN

    def test_day_6_nijmegen_still(self):
        assert XXX_CORPS_TIMELINE[6] == XXXCorpsPosition.NIJMEGEN

    def test_day_7_elst(self):
        assert XXX_CORPS_TIMELINE[7] == XXXCorpsPosition.ELST

    def test_day_8_elst_still(self):
        assert XXX_CORPS_TIMELINE[8] == XXXCorpsPosition.ELST

    def test_day_9_arnhem_south(self):
        assert XXX_CORPS_TIMELINE[9] == XXXCorpsPosition.ARNHEM_SOUTH

    def test_covers_days_1_through_9(self):
        assert set(XXX_CORPS_TIMELINE.keys()) == set(range(1, 10))


# ---------------------------------------------------------------------------
# SupplyLineManager
# ---------------------------------------------------------------------------


class TestSupplyLineManager:
    def test_creation_defaults(self):
        mgr = SupplyLineManager()
        assert mgr.daily_supply_points == 100
        assert mgr.priority_allocation == 0.6
        assert mgr.current_day == 1
        assert mgr.xxx_corps_position == XXXCorpsPosition.START
        assert mgr.priority_sector == "arnhem"
        assert mgr.sector_supply == {}

    def test_create_default(self):
        mgr = SupplyLineManager.create_default()
        assert "arnhem" in mgr.sector_supply
        assert "nijmegen" in mgr.sector_supply
        assert "eindhoven" in mgr.sector_supply

    def test_create_default_all_airdrop_day1(self):
        mgr = SupplyLineManager.create_default()
        for ss in mgr.sector_supply.values():
            assert ss.supply_type == SupplyType.AIRDROP
            assert ss.supply_level == SupplyLevel.REDUCED

    def test_create_default_lz_names(self):
        mgr = SupplyLineManager.create_default()
        assert mgr.sector_supply["arnhem"].lz_name == "LZ-S/DZ-X"
        assert mgr.sector_supply["nijmegen"].lz_name == "LZ-T"
        assert mgr.sector_supply["eindhoven"].lz_name == "LZ-W"


class TestSupplyLineManagerAdvanceDay:
    def test_advance_day_increments(self):
        mgr = SupplyLineManager.create_default()
        mgr.advance_day()
        assert mgr.current_day == 2

    def test_advance_day_updates_corps_position(self):
        mgr = SupplyLineManager.create_default()
        mgr.advance_day()  # Day 2
        assert mgr.xxx_corps_position == XXXCorpsPosition.VEGHEL

    def test_advance_multiple_days(self):
        mgr = SupplyLineManager.create_default()
        for _ in range(4):  # Day 5
            mgr.advance_day()
        assert mgr.current_day == 5
        assert mgr.xxx_corps_position == XXXCorpsPosition.NIJMEGEN

    def test_eindhoven_gets_land_supply_day2(self):
        mgr = SupplyLineManager.create_default()
        mgr.advance_day()  # Day 2
        assert mgr.sector_supply["eindhoven"].supply_type == SupplyType.LAND
        assert mgr.sector_supply["eindhoven"].supply_level == SupplyLevel.FULL

    def test_eindhoven_airdrop_day1(self):
        mgr = SupplyLineManager.create_default()
        assert mgr.sector_supply["eindhoven"].supply_type == SupplyType.AIRDROP

    def test_nijmegen_gets_land_supply_day5(self):
        mgr = SupplyLineManager.create_default()
        for _ in range(4):  # Day 5
            mgr.advance_day()
        assert mgr.sector_supply["nijmegen"].supply_type == SupplyType.LAND
        assert mgr.sector_supply["nijmegen"].supply_level == SupplyLevel.FULL

    def test_nijmegen_airdrop_before_day5(self):
        mgr = SupplyLineManager.create_default()
        for _ in range(3):  # Day 4
            mgr.advance_day()
        assert mgr.sector_supply["nijmegen"].supply_type == SupplyType.AIRDROP

    def test_arnhem_never_gets_land_supply(self):
        mgr = SupplyLineManager.create_default()
        for _ in range(8):  # Day 9
            mgr.advance_day()
        # Arnhem always uses airdrop, even though xxx_corps_reached becomes True on day 9
        # The code sets supply_type = AIRDROP regardless for arnhem
        assert mgr.sector_supply["arnhem"].supply_type == SupplyType.AIRDROP

    def test_arnhem_airdrop_day1(self):
        mgr = SupplyLineManager.create_default()
        assert mgr.sector_supply["arnhem"].supply_type == SupplyType.AIRDROP
        assert mgr.sector_supply["arnhem"].supply_level == SupplyLevel.REDUCED


class TestSupplyLineManagerAllocation:
    def test_allocate_empty_sectors(self):
        mgr = SupplyLineManager()
        assert mgr.allocate_supply() == {}

    def test_allocate_priority_sector_gets_60_percent(self):
        mgr = SupplyLineManager.create_default()
        allocation = mgr.allocate_supply()
        assert allocation["arnhem"] == 60.0  # 100 * 0.6

    def test_allocate_other_sectors_split_40_percent(self):
        mgr = SupplyLineManager.create_default()
        allocation = mgr.allocate_supply()
        # 40 points split between 2 other sectors = 20 each
        assert allocation["nijmegen"] == 20.0
        assert allocation["eindhoven"] == 20.0

    def test_allocate_total_equals_daily_supply(self):
        mgr = SupplyLineManager.create_default()
        allocation = mgr.allocate_supply()
        assert sum(allocation.values()) == pytest.approx(100.0)

    def test_allocate_single_sector(self):
        mgr = SupplyLineManager()
        mgr.sector_supply = {
            "arnhem": SupplyState(sector_id="arnhem", day=1),
        }
        allocation = mgr.allocate_supply()
        # Only one sector: priority gets 60, remaining 40 / max(0, 1) = 40
        assert allocation["arnhem"] == 60.0

    def test_allocate_custom_priority_sector(self):
        mgr = SupplyLineManager.create_default()
        mgr.priority_sector = "nijmegen"
        allocation = mgr.allocate_supply()
        assert allocation["nijmegen"] == 60.0
        assert allocation["arnhem"] == 20.0


class TestSupplyLineManagerGermanSupply:
    def test_german_supply_always_land(self):
        mgr = SupplyLineManager.create_default()
        gs = mgr.get_german_supply("arnhem")
        assert gs.supply_type == SupplyType.LAND
        assert gs.supply_level == SupplyLevel.FULL

    def test_german_supply_full_ammo(self):
        mgr = SupplyLineManager.create_default()
        gs = mgr.get_german_supply("nijmegen")
        assert gs.ammo_replenishment_rate == 1.0

    def test_german_supply_slightly_reduced_reinforcement(self):
        mgr = SupplyLineManager.create_default()
        gs = mgr.get_german_supply("eindhoven")
        assert gs.reinforcement_rate == 0.8
        assert gs.morale_recovery_rate == 0.7

    def test_german_supply_day_matches_current(self):
        mgr = SupplyLineManager.create_default()
        mgr.advance_day()
        gs = mgr.get_german_supply("arnhem")
        assert gs.day == 2


class TestSupplyLineManagerLZControl:
    def test_lz_lost_blocks_airdrop(self):
        mgr = SupplyLineManager.create_default()
        mgr.sector_supply["arnhem"].lz_controlled = False
        mgr.sector_supply["arnhem"].calculate_supply()
        assert mgr.sector_supply["arnhem"].supply_level == SupplyLevel.NONE
        assert mgr.sector_supply["arnhem"].ammo_replenishment_rate == 0.0

    def test_lz_regained_restores_airdrop(self):
        mgr = SupplyLineManager.create_default()
        mgr.sector_supply["arnhem"].lz_controlled = False
        mgr.sector_supply["arnhem"].calculate_supply()
        assert mgr.sector_supply["arnhem"].supply_level == SupplyLevel.NONE
        mgr.sector_supply["arnhem"].lz_controlled = True
        mgr.sector_supply["arnhem"].calculate_supply()
        assert mgr.sector_supply["arnhem"].supply_level == SupplyLevel.REDUCED
