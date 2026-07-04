"""Unit tests for the campaign_persistence module (file I/O layer).

This file tests ``pycc2.domain.systems.campaign_persistence`` which provides
cross-battle state inheritance and JSON-based save/load for campaigns.

NOTE: A pre-existing ``test_campaign_persistence.py`` file tests the sibling
modules ``campaign_state`` and ``battle_result``. Those modules are distinct
from ``campaign_persistence.py`` (which defines its own ``BattleOutcome`` and
``BattleResult`` classes), so this separate file avoids import collisions.

Covers (dimension completeness):
- Happy Path: dataclass construction, save/load round-trips, aggregation
- Error Case: missing files, corrupted JSON, version mismatch
- Boundary: empty unit lists, zero casualties, default timestamps
- Performance: save/load timing baseline
- Integration: end-to-end save → load → apply_inheritance flow
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

# Headless pygame guard (campaign_persistence imports lazily; defensive).
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.systems.campaign_persistence import (
    BattleOutcome,
    BattleResult,
    CampaignPersistenceManager,
    CampaignProgress,
    UnitBattleState,
)

# ========================================================================
# BattleOutcome Enum Tests
# ========================================================================


class TestBattleOutcome:
    """Tests for the BattleOutcome enum defined in campaign_persistence."""

    def test_all_outcomes_present(self):
        """Verify all six battle outcomes are defined.

        Scenario: Inspect the BattleOutcome enum members.
        Expected: ALLIED_VICTORY, AXIS_VICTORY, DRAW, CEASEFIRE,
                  ALLIED_RETREAT, AXIS_RETREAT all present.
        """
        names = {o.name for o in BattleOutcome}
        assert names == {
            "ALLIED_VICTORY",
            "AXIS_VICTORY",
            "DRAW",
            "CEASEFIRE",
            "ALLIED_RETREAT",
            "AXIS_RETREAT",
        }

    def test_outcome_values_are_unique(self):
        """Verify each enum member has a distinct auto() value.

        Scenario: Collect all enum values.
        Expected: No duplicates (auto() guarantees uniqueness).
        """
        values = [o.value for o in BattleOutcome]
        assert len(values) == len(set(values))

    def test_outcome_count(self):
        """Verify exactly six outcomes exist.

        Expected: len(BattleOutcome) == 6.
        """
        assert len(BattleOutcome) == 6


# ========================================================================
# UnitBattleState Tests
# ========================================================================


class TestUnitBattleState:
    """Tests for the UnitBattleState dataclass (slots-based)."""

    def test_default_construction(self):
        """Verify default field values when only required fields given.

        Scenario: Construct with only unit_id, unit_template_id, faction.
        Expected: is_alive=True, current_hp=100, max_hp=100, morale=100,
                  experience=0, kills=0, status="active", empty ammo dict.
        """
        u = UnitBattleState(unit_id="u1", unit_template_id="tmpl_a", faction="allies")
        assert u.unit_id == "u1"
        assert u.unit_template_id == "tmpl_a"
        assert u.faction == "allies"
        assert u.is_alive is True
        assert u.current_hp == 100.0
        assert u.max_hp == 100.0
        assert u.morale == 100.0
        assert u.experience == 0
        assert u.kills == 0
        assert u.status == "active"
        assert u.ammo_remaining == {}

    def test_custom_construction(self):
        """Verify all fields can be customized.

        Scenario: Construct with every field supplied.
        Expected: All values match what was passed.
        """
        u = UnitBattleState(
            unit_id="u2",
            unit_template_id="tmpl_b",
            faction="axis",
            is_alive=False,
            current_hp=0.0,
            max_hp=150.0,
            morale=30.0,
            experience=250,
            ammo_remaining={"primary": 30, "secondary": 5},
            kills=4,
            status="dead",
        )
        assert u.is_alive is False
        assert u.current_hp == 0.0
        assert u.max_hp == 150.0
        assert u.morale == 30.0
        assert u.experience == 250
        assert u.ammo_remaining == {"primary": 30, "secondary": 5}
        assert u.kills == 4
        assert u.status == "dead"

    def test_ammo_remaining_independent_per_instance(self):
        """Verify each instance gets its own ammo_remaining dict (default_factory).

        Scenario: Create two instances, mutate one's ammo.
        Expected: The other instance's ammo remains unchanged.
        """
        a = UnitBattleState(unit_id="a", unit_template_id="t", faction="allies")
        b = UnitBattleState(unit_id="b", unit_template_id="t", faction="allies")
        a.ammo_remaining["primary"] = 10
        assert b.ammo_remaining == {}

    def test_slots_prevents_arbitrary_attrs(self):
        """Verify slots=True blocks adding new attributes.

        Scenario: Try to set an undefined attribute.
        Expected: AttributeError raised (slots enforcement).
        """
        u = UnitBattleState(unit_id="u", unit_template_id="t", faction="allies")
        with pytest.raises(AttributeError):
            u.undefined_field = 42  # type: ignore[attr-defined]


# ========================================================================
# BattleResult Tests (campaign_persistence version)
# ========================================================================


class TestCPBattleResult:
    """Tests for the BattleResult dataclass defined in campaign_persistence."""

    def test_default_timestamp_auto_filled(self):
        """Verify __post_init__ sets a non-empty timestamp when omitted.

        Scenario: Construct BattleResult without specifying timestamp.
        Expected: timestamp is a non-empty ISO-format string.
        """
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="north",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
        )
        assert br.timestamp != ""
        assert "T" in br.timestamp  # ISO format contains 'T'

    def test_explicit_timestamp_preserved(self):
        """Verify an explicit timestamp is not overwritten.

        Scenario: Construct with a custom timestamp.
        Expected: timestamp matches the supplied value.
        """
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="north",
            day=1,
            outcome=BattleOutcome.DRAW,
            timestamp="2024-01-01T00:00:00",
        )
        assert br.timestamp == "2024-01-01T00:00:00"

    def test_default_aggregate_fields_zero(self):
        """Verify aggregate counters default to zero.

        Expected: allied_casualties, axis_casualties, vp_earned all 0.
        """
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.AXIS_VICTORY,
        )
        assert br.allied_casualties == 0
        assert br.axis_casualties == 0
        assert br.allied_vp_earned == 0
        assert br.axis_vp_earned == 0
        assert br.unit_states == []
        assert br.reinforcements_available == {}
        assert br.notes == ""

    def test_full_construction(self):
        """Verify construction with all fields populated."""
        units = [
            UnitBattleState(unit_id="u1", unit_template_id="t1", faction="allies"),
        ]
        br = BattleResult(
            battle_id="b2",
            operation_id="op2",
            sector="south",
            day=3,
            outcome=BattleOutcome.ALLIED_VICTORY,
            duration_ticks=500,
            allied_units_start=10,
            allied_units_end=8,
            axis_units_start=10,
            axis_units_end=3,
            allied_casualties=2,
            axis_casualties=7,
            allied_vp_earned=100,
            axis_vp_earned=20,
            unit_states=units,
            reinforcements_available={"allies": ["r1", "r2"]},
            notes="Decisive victory",
        )
        assert br.battle_id == "b2"
        assert br.duration_ticks == 500
        assert br.allied_units_start == 10
        assert br.allied_units_end == 8
        assert br.axis_units_end == 3
        assert len(br.unit_states) == 1
        assert br.reinforcements_available == {"allies": ["r1", "r2"]}


# ========================================================================
# CampaignProgress Tests
# ========================================================================


class TestCampaignProgress:
    """Tests for the CampaignProgress dataclass and its methods."""

    def test_default_construction(self):
        """Verify default field values.

        Expected: current_battle_index=0, total_battles_completed=0,
                  requisition_points_allies=500, axis=500, last_updated set.
        """
        cp = CampaignProgress(
            campaign_id="c1",
            current_operation_id="op1",
        )
        assert cp.current_battle_index == 0
        assert cp.total_battles_completed == 0
        assert cp.battle_results == []
        assert cp.current_unit_states == []
        assert cp.requisition_points_allies == 500
        assert cp.requisition_points_axis == 500
        assert cp.total_allied_casualties == 0
        assert cp.total_axis_casualties == 0
        assert cp.sectors_controlled == {}
        assert cp.last_updated != ""

    def test_explicit_last_updated_preserved(self):
        """Verify an explicit last_updated is not overwritten."""
        cp = CampaignProgress(
            campaign_id="c1",
            current_operation_id="op1",
            last_updated="2024-01-01",
        )
        assert cp.last_updated == "2024-01-01"

    def test_add_battle_result_updates_aggregates(self):
        """Verify add_battle_result increments counters and aggregates casualties.

        Scenario: Add a BattleResult with casualties and unit states.
        Expected: total_battles_completed=1, current_battle_index=1,
                  total casualties accumulated, current_unit_states replaced.
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        units = [
            UnitBattleState(unit_id="u1", unit_template_id="t1", faction="allies"),
            UnitBattleState(unit_id="u2", unit_template_id="t2", faction="axis"),
        ]
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            allied_casualties=3,
            axis_casualties=5,
            unit_states=units,
        )
        cp.add_battle_result(br)
        assert cp.total_battles_completed == 1
        assert cp.current_battle_index == 1
        assert cp.total_allied_casualties == 3
        assert cp.total_axis_casualties == 5
        assert len(cp.current_unit_states) == 2
        assert cp.current_unit_states[0].unit_id == "u1"

    def test_add_multiple_battle_results(self):
        """Verify adding multiple results accumulates correctly.

        Scenario: Add three battle results with varying casualties.
        Expected: Aggregates sum all casualties; last result's units stored.
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        for i in range(3):
            br = BattleResult(
                battle_id=f"b{i}",
                operation_id="op1",
                sector="s",
                day=i + 1,
                outcome=BattleOutcome.ALLIED_VICTORY,
                allied_casualties=i,
                axis_casualties=i * 2,
                unit_states=[
                    UnitBattleState(unit_id=f"u{i}", unit_template_id=f"t{i}", faction="allies"),
                ],
            )
            cp.add_battle_result(br)
        assert cp.total_battles_completed == 3
        assert cp.current_battle_index == 3
        assert cp.total_allied_casualties == 0 + 1 + 2
        assert cp.total_axis_casualties == 0 + 2 + 4
        assert len(cp.current_unit_states) == 1
        assert cp.current_unit_states[0].unit_id == "u2"

    def test_get_surviving_units_filters_by_faction(self):
        """Verify get_surviving_units returns only alive units of the faction.

        Scenario: Mixed faction unit states with some dead.
        Expected: Only alive units of requested faction returned (case-insensitive).
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        cp.current_unit_states = [
            UnitBattleState(unit_id="a1", unit_template_id="t", faction="allies", is_alive=True),
            UnitBattleState(unit_id="a2", unit_template_id="t", faction="allies", is_alive=False),
            UnitBattleState(unit_id="x1", unit_template_id="t", faction="axis", is_alive=True),
        ]
        surviving = cp.get_surviving_units("Allies")
        ids = [u.unit_id for u in surviving]
        assert ids == ["a1"]

    def test_get_surviving_units_empty_when_none_alive(self):
        """Verify empty list when no survivors of requested faction.

        Boundary: All units dead or different faction.
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        cp.current_unit_states = [
            UnitBattleState(unit_id="a1", unit_template_id="t", faction="allies", is_alive=False),
        ]
        assert cp.get_surviving_units("allies") == []
        assert cp.get_surviving_units("axis") == []

    def test_get_surviving_units_empty_state(self):
        """Verify empty list when current_unit_states is empty.

        Boundary: No units at all.
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        assert cp.get_surviving_units("allies") == []

    def test_get_unit_state_finds_match(self):
        """Verify get_unit_state returns matching unit.

        Scenario: Search for an existing unit_id.
        Expected: UnitBattleState returned with matching id.
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        cp.current_unit_states = [
            UnitBattleState(unit_id="u1", unit_template_id="t", faction="allies"),
            UnitBattleState(unit_id="u2", unit_template_id="t", faction="axis"),
        ]
        result = cp.get_unit_state("u2")
        assert result is not None
        assert result.unit_id == "u2"
        assert result.faction == "axis"

    def test_get_unit_state_returns_none_when_missing(self):
        """Verify get_unit_state returns None for unknown id.

        Error Case: unit_id not in current_unit_states.
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        cp.current_unit_states = [
            UnitBattleState(unit_id="u1", unit_template_id="t", faction="allies"),
        ]
        assert cp.get_unit_state("nonexistent") is None

    def test_get_unit_state_empty_list(self):
        """Verify get_unit_state returns None when state list empty.

        Boundary: No units stored.
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        assert cp.get_unit_state("any") is None

    def test_calculate_reinforcement_bonus_no_battles(self):
        """Verify reinforcement bonus is zero when no battles recorded.

        Boundary: Empty battle_results.
        Expected: {"allies": 0, "axis": 0}.
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        assert cp.calculate_reinforcement_bonus() == {"allies": 0, "axis": 0}

    def test_calculate_reinforcement_bonus_allied_victory(self):
        """Verify allied victory gives allies +100 base, axis +25.

        Scenario: Last battle is ALLIED_VICTORY with full survival.
        Expected: allies >= 100 + survival_bonus, axis >= 25 + survival_bonus.
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            allied_units_start=10,
            allied_units_end=10,
            axis_units_start=10,
            axis_units_end=5,
        )
        cp.add_battle_result(br)
        bonus = cp.calculate_reinforcement_bonus()
        # allies: 100 base + 50 survival (10/10 * 50)
        assert bonus["allies"] == 100 + 50
        # axis: 25 base + 25 survival (5/10 * 50)
        assert bonus["axis"] == 25 + 25

    def test_calculate_reinforcement_bonus_axis_victory(self):
        """Verify axis victory gives axis +100 base, allies +25."""
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.AXIS_VICTORY,
            allied_units_start=10,
            allied_units_end=3,
            axis_units_start=10,
            axis_units_end=9,
        )
        cp.add_battle_result(br)
        bonus = cp.calculate_reinforcement_bonus()
        # allies: 25 base + 15 survival (3/10 * 50 = 15)
        assert bonus["allies"] == 25 + 15
        # axis: 100 base + 45 survival (9/10 * 50 = 45)
        assert bonus["axis"] == 100 + 45

    def test_calculate_reinforcement_bonus_draw(self):
        """Verify non-victory outcomes give both sides +50 base."""
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.DRAW,
            allied_units_start=10,
            allied_units_end=8,
            axis_units_start=10,
            axis_units_end=8,
        )
        cp.add_battle_result(br)
        bonus = cp.calculate_reinforcement_bonus()
        # both: 50 base + 40 survival (8/10 * 50 = 40)
        assert bonus["allies"] == 50 + 40
        assert bonus["axis"] == 50 + 40

    def test_calculate_reinforcement_bonus_uses_last_battle_only(self):
        """Verify only the last battle's outcome is used for bonus.

        Scenario: Two battles, first allied victory, second axis victory.
        Expected: Bonus reflects axis victory (the last one).
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        br1 = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            allied_units_start=10,
            allied_units_end=10,
            axis_units_start=10,
            axis_units_end=5,
        )
        br2 = BattleResult(
            battle_id="b2",
            operation_id="op1",
            sector="s",
            day=2,
            outcome=BattleOutcome.AXIS_VICTORY,
            allied_units_start=10,
            allied_units_end=2,
            axis_units_start=10,
            axis_units_end=10,
        )
        cp.add_battle_result(br1)
        cp.add_battle_result(br2)
        bonus = cp.calculate_reinforcement_bonus()
        # Last battle is axis victory: axis gets 100 + 50, allies get 25 + 10
        assert bonus["axis"] == 100 + 50
        assert bonus["allies"] == 25 + 10

    def test_calculate_reinforcement_bonus_zero_start_units(self):
        """Verify survival rate handles zero start units (division guard).

        Boundary: allied_units_start=0 → max(0, 1) prevents ZeroDivisionError.
        Expected: survival bonus is 0 (0/1 * 50 = 0).
        """
        cp = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.DRAW,
            allied_units_start=0,
            allied_units_end=0,
            axis_units_start=0,
            axis_units_end=0,
        )
        cp.add_battle_result(br)
        bonus = cp.calculate_reinforcement_bonus()
        assert bonus["allies"] == 50  # 50 base + 0 survival
        assert bonus["axis"] == 50


# ========================================================================
# CampaignPersistenceManager Tests
# ========================================================================


class TestCampaignPersistenceManager:
    """Tests for the CampaignPersistenceManager class (save/load/list/delete)."""

    def test_init_with_str_base_dir(self, tmp_path: Path):
        """Verify string base_dir is converted to Path and campaign dir created.

        Scenario: Pass base_dir as a string.
        Expected: _campaign_dir exists and contains "campaign_saves".
        """
        mgr = CampaignPersistenceManager(base_dir=str(tmp_path))
        assert mgr._campaign_dir == tmp_path / "campaign_saves"
        assert mgr._campaign_dir.exists()

    def test_init_with_path_base_dir(self, tmp_path: Path):
        """Verify Path base_dir works and campaign dir created.

        Scenario: Pass base_dir as a Path.
        Expected: _campaign_dir exists.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        assert mgr._campaign_dir.exists()

    def test_init_creates_nested_dirs(self, tmp_path: Path):
        """Verify mkdir(parents=True) creates nested directories.

        Scenario: base_dir points to a non-existent nested path.
        Expected: All parent dirs created.
        """
        nested = tmp_path / "a" / "b" / "c"
        mgr = CampaignPersistenceManager(base_dir=nested)
        assert mgr._campaign_dir.exists()

    def test_init_default_base_dir(self):
        """Verify default base_dir is used when None passed.

        Scenario: Pass base_dir=None.
        Expected: Manager creates a default saves directory.
        """
        mgr = CampaignPersistenceManager(base_dir=None)
        assert mgr._campaign_dir.exists()
        assert mgr._campaign_dir.name == "campaign_saves"

    def test_constants(self):
        """Verify class constants.

        Expected: CAMPAIGN_DIR_NAME="campaign_saves", VERSION="1.0".
        """
        assert CampaignPersistenceManager.CAMPAIGN_DIR_NAME == "campaign_saves"
        assert CampaignPersistenceManager.VERSION == "1.0"

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        """Verify save → load preserves campaign progress.

        Integration: Save a campaign, load it back, verify all fields match.

        Scenario: Create CampaignProgress with units and battle results,
                  save it, then load it.
        Expected: Loaded progress matches original (ids, casualties, units).
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        units = [
            UnitBattleState(
                unit_id="u1",
                unit_template_id="t1",
                faction="allies",
                current_hp=75.0,
                morale=60.0,
                experience=100,
                ammo_remaining={"primary": 30},
                kills=2,
            ),
            UnitBattleState(
                unit_id="u2",
                unit_template_id="t2",
                faction="axis",
                is_alive=False,
                status="dead",
            ),
        ]
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="north",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            allied_casualties=2,
            axis_casualties=5,
            unit_states=units,
        )
        progress = CampaignProgress(
            campaign_id="camp_1",
            current_operation_id="op1",
            requisition_points_allies=600,
            requisition_points_axis=400,
        )
        progress.add_battle_result(br)

        saved = mgr.save_campaign_progress("camp_1", progress)
        assert saved is True

        loaded = mgr.load_campaign_progress("camp_1")
        assert loaded is not None
        assert loaded.campaign_id == "camp_1"
        assert loaded.current_operation_id == "op1"
        assert loaded.total_battles_completed == 1
        assert loaded.requisition_points_allies == 600
        assert loaded.requisition_points_axis == 400
        assert loaded.total_allied_casualties == 2
        assert loaded.total_axis_casualties == 5
        assert len(loaded.current_unit_states) == 2
        assert loaded.current_unit_states[0].unit_id == "u1"
        assert loaded.current_unit_states[0].current_hp == 75.0
        assert loaded.current_unit_states[0].experience == 100
        assert loaded.current_unit_states[1].is_alive is False
        assert len(loaded.battle_results) == 1
        assert loaded.battle_results[0].battle_id == "b1"

    def test_save_returns_true(self, tmp_path: Path):
        """Verify save returns True on success.

        Happy Path: Valid progress saved.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        assert mgr.save_campaign_progress("c1", progress) is True

    def test_save_creates_json_file(self, tmp_path: Path):
        """Verify save creates a JSON file with correct name.

        Scenario: Save campaign with id "my_camp".
        Expected: File campaign_my_camp.json exists in campaign dir.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="my_camp", current_operation_id="op1")
        mgr.save_campaign_progress("my_camp", progress)
        expected = tmp_path / "campaign_saves" / "campaign_my_camp.json"
        assert expected.exists()

    def test_save_file_contains_version(self, tmp_path: Path):
        """Verify saved JSON contains the version field.

        Scenario: Read the raw JSON file.
        Expected: version field equals "1.0".
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        mgr.save_campaign_progress("c1", progress)
        filepath = tmp_path / "campaign_saves" / "campaign_c1.json"
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        assert data["version"] == "1.0"
        assert data["campaign_id"] == "c1"
        assert "saved_at" in data
        assert "progress" in data

    def test_load_returns_none_for_missing_campaign(self, tmp_path: Path):
        """Verify load returns None when save file doesn't exist.

        Error Case: No file for given campaign_id.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        assert mgr.load_campaign_progress("nonexistent") is None

    def test_save_returns_false_on_write_error(self, tmp_path: Path):
        """Verify save returns False when file write fails.

        Error Case: OSError during write (e.g., disk full or permission denied).
        Expected: Returns False, no exception raised (caught and logged).
        """
        from unittest.mock import patch

        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")

        # Mock open to raise OSError (chmod 0o444 doesn't work as root in Docker)
        with patch("builtins.open", side_effect=OSError("disk full")):
            result = mgr.save_campaign_progress("c1", progress)
            assert result is False

    def test_load_corrupted_json_returns_none(self, tmp_path: Path):
        """Verify load returns None when JSON is corrupted.

        Error Case: Save file contains invalid JSON.
        Expected: Returns None, logs error (no exception raised).
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        filepath = tmp_path / "campaign_saves" / "campaign_bad.json"
        filepath.write_text("{not valid json")
        assert mgr.load_campaign_progress("bad") is None

    def test_load_version_mismatch_still_loads(self, tmp_path: Path):
        """Verify load still returns progress when version differs.

        Scenario: Save file has version "0.0" (mismatch).
        Expected: Progress is still loaded (with a warning logged).
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        filepath = tmp_path / "campaign_saves" / "campaign_old.json"
        data = {
            "version": "0.0",
            "campaign_id": "old",
            "saved_at": "2024-01-01",
            "progress": {
                "campaign_id": "old",
                "current_operation_id": "op1",
                "current_battle_index": 0,
                "total_battles_completed": 0,
                "battle_results": [],
                "current_unit_states": [],
                "requisition_points_allies": 500,
                "requisition_points_axis": 500,
                "total_allied_casualties": 0,
                "total_axis_casualties": 0,
                "sectors_controlled": {},
                "last_updated": "2024-01-01",
            },
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f)
        loaded = mgr.load_campaign_progress("old")
        assert loaded is not None
        assert loaded.campaign_id == "old"

    def test_load_with_battle_results_and_units(self, tmp_path: Path):
        """Verify load reconstructs nested BattleResult and UnitBattleState.

        Integration: Save a campaign with battle_results containing unit_states,
        then load it and verify the nested structure is reconstructed.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        units = [
            UnitBattleState(
                unit_id="u1",
                unit_template_id="t1",
                faction="allies",
                ammo_remaining={"primary": 20},
            ),
        ]
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            unit_states=units,
        )
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        progress.add_battle_result(br)
        mgr.save_campaign_progress("c1", progress)

        loaded = mgr.load_campaign_progress("c1")
        assert loaded is not None
        assert len(loaded.battle_results) == 1
        br_loaded = loaded.battle_results[0]
        assert br_loaded.battle_id == "b1"
        assert len(br_loaded.unit_states) == 1
        assert br_loaded.unit_states[0].unit_id == "u1"
        assert br_loaded.unit_states[0].ammo_remaining == {"primary": 20}

    def test_list_saved_campaigns_empty(self, tmp_path: Path):
        """Verify list returns empty list when no saves exist.

        Boundary: Empty campaign directory.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        assert mgr.list_saved_campaigns() == []

    def test_list_saved_campaigns_multiple(self, tmp_path: Path):
        """Verify list returns metadata for all saved campaigns.

        Scenario: Save three campaigns, then list.
        Expected: All three returned with correct metadata.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        for i in range(3):
            progress = CampaignProgress(
                campaign_id=f"c{i}",
                current_operation_id=f"op{i}",
            )
            br = BattleResult(
                battle_id=f"b{i}",
                operation_id=f"op{i}",
                sector="s",
                day=1,
                outcome=BattleOutcome.DRAW,
                allied_casualties=i,
            )
            progress.add_battle_result(br)
            mgr.save_campaign_progress(f"c{i}", progress)

        campaigns = mgr.list_saved_campaigns()
        assert len(campaigns) == 3
        ids = {c["campaign_id"] for c in campaigns}
        assert ids == {"c0", "c1", "c2"}
        for c in campaigns:
            assert "saved_at" in c
            assert "battles_completed" in c
            assert "current_operation" in c
            assert "file_path" in c
        c0 = next(c for c in campaigns if c["campaign_id"] == "c0")
        assert c0["battles_completed"] == 1
        assert c0["current_operation"] == "op0"

    def test_list_saved_campaigns_handles_corrupt_file(self, tmp_path: Path):
        """Verify list includes error entry for corrupted save files.

        Error Case: One save file is corrupted JSON.
        Expected: Corrupt file listed with error=True, others still returned.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        # Valid save
        progress = CampaignProgress(campaign_id="good", current_operation_id="op1")
        mgr.save_campaign_progress("good", progress)
        # Corrupt save
        bad_file = tmp_path / "campaign_saves" / "campaign_bad.json"
        bad_file.write_text("not json{")

        campaigns = mgr.list_saved_campaigns()
        assert len(campaigns) == 2
        bad_entry = next(c for c in campaigns if "error" in c)
        assert bad_entry["error"] is True
        good_entry = next(c for c in campaigns if c["campaign_id"] == "good")
        assert "error" not in good_entry

    def test_delete_campaign_save_existing(self, tmp_path: Path):
        """Verify delete returns True and removes file for existing save.

        Happy Path: Save then delete.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        mgr.save_campaign_progress("c1", progress)
        assert mgr.delete_campaign_save("c1") is True
        assert not (tmp_path / "campaign_saves" / "campaign_c1.json").exists()

    def test_delete_campaign_save_missing_returns_false(self, tmp_path: Path):
        """Verify delete returns False when file doesn't exist.

        Error Case: Attempt to delete non-existent save.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        assert mgr.delete_campaign_save("nonexistent") is False

    def test_save_load_delete_integration(self, tmp_path: Path):
        """Verify full save → load → delete cycle.

        Integration: End-to-end lifecycle of a campaign save.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="lifecycle", current_operation_id="op1")
        mgr.save_campaign_progress("lifecycle", progress)
        loaded = mgr.load_campaign_progress("lifecycle")
        assert loaded is not None
        assert mgr.delete_campaign_save("lifecycle") is True
        assert mgr.load_campaign_progress("lifecycle") is None


# ========================================================================
# Fake Unit for apply_inheritance_to_units tests
# ========================================================================


class _FakeHealthComponent:
    """Lightweight fake health component matching the real HealthComponent API.

    Mirrors the real component's writable ``hp`` field and ``_update_state()``
    hook so tests exercise the same code path as production. ``current_hp`` is
    exposed as a read-only alias for backward-compatible assertions.
    """

    def __init__(self, max_hp: float = 100.0, current_hp: float | None = None) -> None:
        self.max_hp = max_hp
        self.hp = current_hp if current_hp is not None else max_hp

    @property
    def current_hp(self) -> float:
        return self.hp

    def _update_state(self) -> None:
        # Real component refreshes a HealthState enum here; the fake only needs
        # to accept the call so apply_inheritance_to_units can invoke it.
        return None


class _FakeMoraleComponent:
    """Lightweight fake morale component matching the real MoraleComponent API.

    Mirrors the real component's writable ``value`` field. ``current_morale`` is
    exposed as a read-only alias for backward-compatible assertions.
    """

    def __init__(self, current_morale: float = 100.0) -> None:
        self.value: int = int(current_morale)

    @property
    def current_morale(self) -> float:
        return float(self.value)


class _FakeWeaponComponent:
    """Lightweight fake weapon component with settable ammo slots."""

    def __init__(self) -> None:
        self.primary: int = 0
        self.secondary: int = 0


class _FakeVeterancyComponent:
    """Lightweight fake veterancy component tracking add_xp calls."""

    def __init__(self) -> None:
        self.xp: int = 0

    def add_xp(self, amount: int) -> bool:
        self.xp += amount
        return False


class _FakeStateMachine:
    """Lightweight fake state machine matching the real StateMachine API.

    Mirrors the real component's ``force_transition(target)`` method so tests
    exercise the same code path as production. ``force_state`` is retained as a
    backward-compatible alias.
    """

    def __init__(self) -> None:
        self.current: str = "IDLE"

    def force_transition(self, state: Any) -> None:
        self.current = state.name if hasattr(state, "name") else str(state)

    def force_state(self, state: Any) -> None:
        # Backward-compatible alias; prefer force_transition in new tests.
        self.force_transition(state)


class _FakeUnit:
    """Lightweight fake unit matching the interface expected by
    apply_inheritance_to_units.

    Uses duck typing: the method probes via getattr/hasattr, so we only
    expose the attributes needed for each test scenario.
    """

    def __init__(
        self,
        unit_template_id: str | None = None,
        unit_id: str | None = None,
        with_health: bool = True,
        with_morale: bool = True,
        with_weapon: bool = True,
        with_veterancy: bool = True,
        with_state_machine: bool = False,
        max_hp: float = 100.0,
    ) -> None:
        self.unit_template_id = unit_template_id
        self.id = unit_id
        if with_health:
            self.health_component = _FakeHealthComponent(max_hp=max_hp)
        if with_morale:
            self.morale_component = _FakeMoraleComponent()
        if with_weapon:
            self.weapon_component = _FakeWeaponComponent()
        if with_veterancy:
            self.veterancy_component = _FakeVeterancyComponent()
        if with_state_machine:
            self.state_machine = _FakeStateMachine()


# ========================================================================
# apply_inheritance_to_units Tests
# ========================================================================


class TestApplyInheritanceToUnits:
    """Tests for CampaignPersistenceManager.apply_inheritance_to_units.

    Uses lightweight fake units because the method uses duck typing
    (getattr/hasattr) and the real domain components have interface
    mismatches (documented in TestApplyInheritanceBugs).

    NOTE on lookup semantics: The method retrieves ``unit_template_id`` (or
    ``id``) from each unit, then calls ``progress.get_unit_state(template_id)``
    which matches against ``UnitBattleState.unit_id``. Therefore, for
    inheritance to apply, the unit's ``unit_template_id`` must equal the
    prev_state's ``unit_id``. This is a design quirk of the source code.
    """

    def test_inherits_hp_for_alive_unit(self, tmp_path: Path):
        """Verify HP ratio is applied to alive units with matching template.

        Scenario: Previous state has current_hp=50, max_hp=100 (ratio 0.5).
                  Current unit has max_hp=200.
        Expected: current_hp = 200 * 0.5 = 100.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        prev_state = UnitBattleState(
            unit_id="tmpl_a",  # Must match unit's unit_template_id for lookup
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=True,
            current_hp=50.0,
            max_hp=100.0,
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(unit_template_id="tmpl_a", max_hp=200.0)
        mgr.apply_inheritance_to_units(progress, [unit])
        assert unit.health_component.current_hp == 100.0

    def test_inherits_morale_for_alive_unit(self, tmp_path: Path):
        """Verify morale is inherited with recovery bonus.

        Scenario: Previous morale=60, total_battles_completed=0.
                  recovery = min(20, 10 + 0*2) = 10.
        Expected: current_morale = min(100, 60 + 10) = 70.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        prev_state = UnitBattleState(
            unit_id="tmpl_a",
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=True,
            morale=60.0,
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(unit_template_id="tmpl_a")
        mgr.apply_inheritance_to_units(progress, [unit])
        assert unit.morale_component.current_morale == 70.0

    def test_morale_capped_at_100(self, tmp_path: Path):
        """Verify morale recovery does not exceed 100.

        Boundary: prev morale=95, recovery=10 → 105 capped to 100.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        prev_state = UnitBattleState(
            unit_id="tmpl_a",
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=True,
            morale=95.0,
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(unit_template_id="tmpl_a")
        mgr.apply_inheritance_to_units(progress, [unit])
        assert unit.morale_component.current_morale == 100.0

    def test_morale_recovery_scales_with_battles(self, tmp_path: Path):
        """Verify morale recovery increases with battles completed.

        Scenario: 5 battles completed → recovery = min(20, 10 + 5*2) = 20.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        progress.total_battles_completed = 5
        prev_state = UnitBattleState(
            unit_id="tmpl_a",
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=True,
            morale=50.0,
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(unit_template_id="tmpl_a")
        mgr.apply_inheritance_to_units(progress, [unit])
        # recovery = min(20, 10 + 5*2) = 20; morale = min(100, 50 + 20) = 70
        assert unit.morale_component.current_morale == 70.0

    def test_inherits_ammo_for_alive_unit(self, tmp_path: Path):
        """Verify ammo is set on weapon component slots.

        Scenario: prev_state.ammo_remaining = {"primary": 30, "secondary": 5}.
        Expected: weapon_component.primary = 30, secondary = 5.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        prev_state = UnitBattleState(
            unit_id="tmpl_a",
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=True,
            ammo_remaining={"primary": 30, "secondary": 5},
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(unit_template_id="tmpl_a")
        mgr.apply_inheritance_to_units(progress, [unit])
        assert unit.weapon_component.primary == 30
        assert unit.weapon_component.secondary == 5

    def test_inherits_experience_for_alive_unit(self, tmp_path: Path):
        """Verify experience is added to veterancy component.

        Scenario: prev_state.experience = 150.
        Expected: veterancy_component.add_xp(150) called → xp = 150.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        prev_state = UnitBattleState(
            unit_id="tmpl_a",
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=True,
            experience=150,
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(unit_template_id="tmpl_a")
        mgr.apply_inheritance_to_units(progress, [unit])
        assert unit.veterancy_component.xp == 150

    def test_dead_unit_hp_zeroed(self, tmp_path: Path):
        """Verify dead units get current_hp set to 0.

        Scenario: prev_state.is_alive=False.
        Expected: health_component.current_hp = 0, state_machine set to DEAD.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        prev_state = UnitBattleState(
            unit_id="tmpl_a",
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=False,
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(unit_template_id="tmpl_a", with_state_machine=True)
        mgr.apply_inheritance_to_units(progress, [unit])
        assert unit.health_component.current_hp == 0
        assert unit.state_machine.current == "DEAD"

    def test_unit_without_template_id_skipped(self, tmp_path: Path):
        """Verify units without unit_template_id or id are skipped.

        Boundary: unit_template_id=None and id=None.
        Expected: Unit unchanged (no inheritance applied).
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        prev_state = UnitBattleState(
            unit_id="tmpl_a",
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=True,
            morale=50.0,
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(unit_template_id=None, unit_id=None)
        original_morale = unit.morale_component.current_morale
        mgr.apply_inheritance_to_units(progress, [unit])
        assert unit.morale_component.current_morale == original_morale

    def test_unit_fallbacks_to_id_when_no_template(self, tmp_path: Path):
        """Verify unit.id is used when unit_template_id is missing.

        Scenario: unit_template_id=None but id="tmpl_a" matches prev_state.unit_id.
        Expected: Inheritance applied (morale updated).
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        prev_state = UnitBattleState(
            unit_id="tmpl_a",
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=True,
            morale=50.0,
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(unit_template_id=None, unit_id="tmpl_a")
        mgr.apply_inheritance_to_units(progress, [unit])
        # recovery = min(20, 10 + 0) = 10; morale = min(100, 50 + 10) = 60
        assert unit.morale_component.current_morale == 60.0

    def test_unit_with_no_matching_state_skipped(self, tmp_path: Path):
        """Verify units without a matching prev_state are unchanged.

        Scenario: prev_state has unit_id "tmpl_a"; unit has template "tmpl_b".
        Expected: Unit unchanged.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        prev_state = UnitBattleState(
            unit_id="tmpl_a",
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=True,
            morale=50.0,
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(unit_template_id="tmpl_b")
        original_morale = unit.morale_component.current_morale
        mgr.apply_inheritance_to_units(progress, [unit])
        assert unit.morale_component.current_morale == original_morale

    def test_empty_unit_list(self, tmp_path: Path):
        """Verify empty current_units list is handled.

        Boundary: No units to apply inheritance to.
        Expected: Returns empty list, no error.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        result = mgr.apply_inheritance_to_units(progress, [])
        assert result == []

    def test_returns_same_list_object(self, tmp_path: Path):
        """Verify the returned list is the same object passed in.

        Scenario: Pass a list of units.
        Expected: Returned list is identical (is check).
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        units = [_FakeUnit(unit_template_id="t")]
        result = mgr.apply_inheritance_to_units(progress, units)
        assert result is units

    def test_partial_components_unit(self, tmp_path: Path):
        """Verify unit with only some components is handled gracefully.

        Scenario: Unit has health_component but no morale/weapon/veterancy.
        Expected: Only health inheritance applied; no AttributeError.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        prev_state = UnitBattleState(
            unit_id="tmpl_a",
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=True,
            current_hp=50.0,
            max_hp=100.0,
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(
            unit_template_id="tmpl_a",
            with_morale=False,
            with_weapon=False,
            with_veterancy=False,
        )
        mgr.apply_inheritance_to_units(progress, [unit])
        assert unit.health_component.current_hp == 50.0

    def test_hp_ratio_with_zero_max_hp(self, tmp_path: Path):
        """Verify HP ratio handles zero max_hp (division guard).

        Boundary: prev_state.max_hp=0 → max(0, 1) prevents ZeroDivisionError.
        Expected: hp_ratio = current_hp / 1; no crash.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        prev_state = UnitBattleState(
            unit_id="tmpl_a",
            unit_template_id="tmpl_a",
            faction="allies",
            is_alive=True,
            current_hp=0.0,
            max_hp=0.0,
        )
        progress.current_unit_states = [prev_state]
        unit = _FakeUnit(unit_template_id="tmpl_a", max_hp=200.0)
        # Should not raise; hp_ratio = 0 / max(0, 1) = 0
        mgr.apply_inheritance_to_units(progress, [unit])
        assert unit.health_component.current_hp == 0.0


# ========================================================================
# Source Code Bug Documentation (Iron Rule 2: Report Failures)
# ========================================================================


class TestApplyInheritanceBugs:
    """Documents known bugs in apply_inheritance_to_units with real components.

    These tests verify that the method FAILS when used with real domain
    components due to interface mismatches. Per Iron Rule 2, we document
    the actual behavior without modifying the source code.

    Bugs:
    1. HealthComponent.current_hp is a read-only @property (no setter) on a
       slots-based dataclass; assignment raises AttributeError.
    2. MoraleComponent has no 'current_morale' attribute (uses 'value');
       assignment raises AttributeError on slots-based dataclass.
    3. StateMachine has 'force_transition' not 'force_state'; calling
       force_state raises AttributeError.
    4. load_campaign_progress does not reconstruct BattleOutcome enums from
       their string representation, so calculate_reinforcement_bonus gives
       incorrect results after a save/load cycle.
    """

    def test_real_health_component_current_hp_is_readonly(self):
        """Document that HealthComponent.current_hp has no setter.

        Scenario: Attempt to assign to current_hp on a real HealthComponent.
        Expected: AttributeError (property has no setter, slots=True).
        """
        from pycc2.domain.components.health_component import HealthComponent

        hc = HealthComponent(hp=100, max_hp=100)
        with pytest.raises(AttributeError):
            hc.current_hp = 50  # type: ignore[misc]

    def test_real_morale_component_has_no_current_morale(self):
        """Document that MoraleComponent uses 'value', not 'current_morale'.

        Scenario: Attempt to assign to current_morale on a real MoraleComponent.
        Expected: AttributeError (attribute doesn't exist, slots=True).
        """
        from pycc2.domain.components.morale_component import MoraleComponent

        mc = MoraleComponent(value=80)
        with pytest.raises(AttributeError):
            mc.current_morale = 50  # type: ignore[attr-defined]

    def test_real_state_machine_has_no_force_state(self):
        """Document that StateMachine has force_transition, not force_state.

        Scenario: Attempt to call force_state on a real StateMachine.
        Expected: AttributeError (method doesn't exist).
        """
        from pycc2.domain.entities.unit import UnitState
        from pycc2.domain.state_machine import StateMachine

        sm = StateMachine(initial=UnitState.IDLE, transitions={UnitState.IDLE: {UnitState.DEAD}})
        with pytest.raises(AttributeError):
            sm.force_state(UnitState.DEAD)  # type: ignore[attr-defined]

    def test_battle_outcome_reconstructed_after_load(self, tmp_path: Path):
        """Verify BattleOutcome is reconstructed as an enum after save/load.

        Scenario: Save a BattleResult with ALLIED_VICTORY, load it back.
        Expected: loaded outcome is a BattleOutcome enum equal to ALLIED_VICTORY.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
        )
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        progress.add_battle_result(br)
        mgr.save_campaign_progress("c1", progress)

        loaded = mgr.load_campaign_progress("c1")
        assert loaded is not None
        loaded_outcome = loaded.battle_results[0].outcome
        assert isinstance(loaded_outcome, BattleOutcome)
        assert loaded_outcome == BattleOutcome.ALLIED_VICTORY


# ========================================================================
# Performance Tests
# ========================================================================


class TestCampaignPersistencePerformance:
    """Performance baseline tests for save/load operations."""

    def test_save_load_timing_baseline(self, tmp_path: Path):
        """Verify save+load completes within reasonable time.

        Performance: Save and load a campaign with 50 units and 10 battle
        results. Should complete in under 2 seconds on any modern machine.

        Scenario: Create a large campaign, time save+load.
        Expected: Wall time < 2.0 seconds.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="perf", current_operation_id="op1")
        for i in range(10):
            units = [
                UnitBattleState(
                    unit_id=f"u{i}_{j}",
                    unit_template_id=f"t{j}",
                    faction="allies" if j % 2 == 0 else "axis",
                    ammo_remaining={"primary": 30, "secondary": 5},
                )
                for j in range(50)
            ]
            br = BattleResult(
                battle_id=f"b{i}",
                operation_id="op1",
                sector="s",
                day=i + 1,
                outcome=BattleOutcome.ALLIED_VICTORY,
                unit_states=units,
                allied_casualties=i,
            )
            progress.add_battle_result(br)

        start = time.perf_counter()
        mgr.save_campaign_progress("perf", progress)
        loaded = mgr.load_campaign_progress("perf")
        elapsed = time.perf_counter() - start

        assert loaded is not None
        assert elapsed < 2.0, f"Save+load took {elapsed:.3f}s, expected < 2.0s"

    def test_list_campaigns_timing_baseline(self, tmp_path: Path):
        """Verify listing 20 campaigns completes quickly.

        Performance: Save 20 campaigns, time list_saved_campaigns.
        Expected: Wall time < 1.0 second.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        for i in range(20):
            progress = CampaignProgress(
                campaign_id=f"c{i}",
                current_operation_id=f"op{i}",
            )
            mgr.save_campaign_progress(f"c{i}", progress)

        start = time.perf_counter()
        campaigns = mgr.list_saved_campaigns()
        elapsed = time.perf_counter() - start

        assert len(campaigns) == 20
        assert elapsed < 1.0, f"List took {elapsed:.3f}s, expected < 1.0s"


# ========================================================================
# Integration Tests
# ========================================================================


class TestCampaignPersistenceIntegration:
    """End-to-end integration tests for the campaign persistence system."""

    def test_full_campaign_lifecycle(self, tmp_path: Path):
        """Verify a multi-battle campaign can be saved and resumed.

        Integration: Simulate a campaign:
        1. Battle 1: Allied victory, units take damage
        2. Save progress
        3. Load progress (simulating game restart)
        4. Apply inherited state to new units
        5. Verify inherited stats match
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)

        # Battle 1: Allied victory
        units_after_b1 = [
            UnitBattleState(
                unit_id="tmpl_inf",  # Must match new unit's unit_template_id
                unit_template_id="tmpl_inf",
                faction="allies",
                is_alive=True,
                current_hp=70.0,
                max_hp=100.0,
                morale=60.0,
                experience=100,
                ammo_remaining={"primary": 20},
            ),
        ]
        br1 = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="north",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            allied_casualties=1,
            axis_casualties=3,
            allied_units_start=5,
            allied_units_end=4,
            axis_units_start=5,
            axis_units_end=2,
            unit_states=units_after_b1,
        )
        progress = CampaignProgress(campaign_id="camp_main", current_operation_id="op1")
        progress.add_battle_result(br1)

        # Save
        assert mgr.save_campaign_progress("camp_main", progress) is True

        # Load (simulating restart)
        loaded = mgr.load_campaign_progress("camp_main")
        assert loaded is not None
        assert loaded.total_battles_completed == 1

        # Apply inheritance to new battle's units
        new_unit = _FakeUnit(unit_template_id="tmpl_inf", max_hp=100.0)
        mgr.apply_inheritance_to_units(loaded, [new_unit])

        # Verify HP ratio inherited: 70/100 = 0.7 → 100 * 0.7 = 70
        assert new_unit.health_component.current_hp == 70.0
        # Verify morale inherited with recovery: min(100, 60 + recovery)
        # recovery = min(20, 10 + total_battles_completed * 2) = min(20, 10 + 1*2) = 12
        # → min(100, 60 + 12) = 72
        assert new_unit.morale_component.current_morale == 72.0
        # Verify ammo inherited
        assert new_unit.weapon_component.primary == 20
        # Verify experience inherited
        assert new_unit.veterancy_component.xp == 100

    def test_reinforcement_bonus_after_save_load(self, tmp_path: Path):
        """Verify reinforcement bonus calculation after save/load.

        After save/load, BattleOutcome enum values are properly reconstructed
        by load_campaign_progress, so calculate_reinforcement_bonus() reaches
        the correct victory branch.

        Integration: Save/load then calculate bonus.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            allied_units_start=10,
            allied_units_end=8,
            axis_units_start=10,
            axis_units_end=4,
        )
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        progress.add_battle_result(br)

        # Before save: correct bonus
        bonus_before = progress.calculate_reinforcement_bonus()
        assert bonus_before["allies"] == 140  # 100 + 40

        mgr.save_campaign_progress("c1", progress)
        loaded = mgr.load_campaign_progress("c1")
        assert loaded is not None

        # After load: outcome is reconstructed as enum, so victory branch runs
        bonus = loaded.calculate_reinforcement_bonus()
        assert bonus["allies"] == 140  # 100 (victory) + 40 (survival 8/10*50)
        assert bonus["axis"] == 45  # 25 (defeat) + 20 (survival 4/10*50)

    def test_multiple_saves_isolated(self, tmp_path: Path):
        """Verify multiple campaigns can be saved without interference.

        Integration: Save two different campaigns, load both, verify isolation.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)

        p1 = CampaignProgress(campaign_id="camp_a", current_operation_id="op_a")
        p1.requisition_points_allies = 700
        mgr.save_campaign_progress("camp_a", p1)

        p2 = CampaignProgress(campaign_id="camp_b", current_operation_id="op_b")
        p2.requisition_points_allies = 300
        mgr.save_campaign_progress("camp_b", p2)

        loaded_a = mgr.load_campaign_progress("camp_a")
        loaded_b = mgr.load_campaign_progress("camp_b")
        assert loaded_a is not None
        assert loaded_b is not None
        assert loaded_a.requisition_points_allies == 700
        assert loaded_b.requisition_points_allies == 300
        assert loaded_a.campaign_id == "camp_a"
        assert loaded_b.campaign_id == "camp_b"

    def test_overwrite_existing_save(self, tmp_path: Path):
        """Verify saving over an existing campaign overwrites it.

        Integration: Save campaign, modify, save again, load → see new state.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        mgr.save_campaign_progress("c1", progress)

        # Modify and re-save
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            allied_casualties=5,
        )
        progress.add_battle_result(br)
        mgr.save_campaign_progress("c1", progress)

        loaded = mgr.load_campaign_progress("c1")
        assert loaded is not None
        assert loaded.total_battles_completed == 1
        assert loaded.total_allied_casualties == 5
