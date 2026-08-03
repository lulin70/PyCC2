"""E2E tests for TC-015: Campaign multi-day progression with cross-battle unit inheritance.

Covers TC-015 (complete Day 1 multi-battle continuous progression) and
CampaignPersistence cross-battle unit inheritance (HP / morale / death flags
persisted across battles via CampaignPersistenceManager).

User journey:
  Day 1 Battle 1 -> save campaign progress -> Day 1 Battle 2 -> load progress ->
  surviving units inherit HP/morale, dead units marked dead, casualties
  accumulate across battles.

Uses the real GameLoop (assembled via conftest.GameLoopFactory) and real
CampaignPersistenceManager with tmp_path isolation - no Mock for domain objects.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest
from conftest import GameLoopFactory

from pycc2.domain.systems.campaign_persistence import (
    BattleOutcome,
    BattleResult,
    CampaignPersistenceManager,
    CampaignProgress,
    UnitBattleState,
)

# ---------------------------------------------------------------------------
# Helpers - build real persistence objects (no Mock)
# ---------------------------------------------------------------------------


def _make_unit_state(
    unit_id: str,
    faction: str,
    *,
    hp: float = 100.0,
    max_hp: float = 100.0,
    morale: float = 80.0,
    is_alive: bool = True,
    experience: int = 0,
    kills: int = 0,
) -> UnitBattleState:
    """Build a UnitBattleState with realistic veteran stats."""
    return UnitBattleState(
        unit_id=unit_id,
        unit_template_id=unit_id,
        faction=faction,
        is_alive=is_alive,
        current_hp=hp,
        max_hp=max_hp,
        morale=morale,
        experience=experience,
        kills=kills,
    )


def _make_battle_result(
    battle_id: str,
    day: int,
    outcome: BattleOutcome,
    unit_states: list[UnitBattleState],
    *,
    allied_casualties: int = 0,
    axis_casualties: int = 0,
    allied_vp: int = 0,
    axis_vp: int = 0,
) -> BattleResult:
    """Build a BattleResult for a Day-N battle."""
    return BattleResult(
        battle_id=battle_id,
        operation_id="op_market_garden",
        sector="arnhem",
        day=day,
        outcome=outcome,
        allied_casualties=allied_casualties,
        axis_casualties=axis_casualties,
        allied_units_start=10,
        allied_units_end=10 - allied_casualties,
        axis_units_start=10,
        axis_units_end=10 - axis_casualties,
        allied_vp_earned=allied_vp,
        axis_vp_earned=axis_vp,
        unit_states=unit_states,
    )


# ---------------------------------------------------------------------------
# TC-015: Campaign multi-day E2E
# ---------------------------------------------------------------------------


class TestCampaignMultiDayE2E:
    """TC-015: Complete Day 1 multi-battle progression + unit inheritance."""

    @pytest.fixture(autouse=True)
    def pygame_env(self):
        """Initialize pygame headless with a 1280x720 screen."""
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        yield
        pygame.quit()

    @pytest.fixture
    def game_loop(self):
        """Assemble a real GameLoop via GameLoopFactory (E2E assembly check)."""
        factory = GameLoopFactory(self.screen)
        yield factory.game_loop
        factory.shutdown()

    @pytest.fixture
    def manager(self, tmp_path: Path) -> CampaignPersistenceManager:
        """CampaignPersistenceManager isolated to tmp_path."""
        return CampaignPersistenceManager(base_dir=tmp_path)

    def test_campaign_save_persists_unit_hp(self, game_loop, tmp_path: Path) -> None:
        """Day1 Battle1 ends -> save -> unit HP state persisted to disk.

        Routes through the real GameLoop.campaign_persistence (replaced with a
        tmp_path-isolated manager) to verify E2E wiring.
        """
        game_loop._campaign_persistence = CampaignPersistenceManager(base_dir=tmp_path)

        progress = CampaignProgress(
            campaign_id="day1_hp",
            current_operation_id="op_market_garden",
        )
        units = [
            _make_unit_state("us_rifle_1", "allies", hp=80.0, morale=70.0),
            _make_unit_state("us_rifle_2", "allies", hp=55.0, morale=60.0),
            _make_unit_state("ge_mg_1", "axis", hp=30.0, morale=40.0),
        ]
        progress.add_battle_result(
            _make_battle_result(
                battle_id="day1_battle1",
                day=1,
                outcome=BattleOutcome.ALLIED_VICTORY,
                unit_states=units,
                allied_casualties=2,
                axis_casualties=4,
            )
        )

        saved = game_loop.campaign_persistence.save_campaign_progress("day1_hp", progress)
        assert saved is True, "save_campaign_progress should return True on success"

        # Verify real file on disk contains the HP values (not just API success)
        save_file = tmp_path / "campaign_saves" / "campaign_day1_hp.json"
        assert save_file.exists(), f"Save file should exist at {save_file}"
        with open(save_file) as f:
            data = json.load(f)
        saved_units = data["progress"]["current_unit_states"]
        hp_by_id = {u["unit_id"]: u["current_hp"] for u in saved_units}
        assert hp_by_id["us_rifle_1"] == 80.0, "us_rifle_1 HP should be persisted as 80"
        assert hp_by_id["us_rifle_2"] == 55.0, "us_rifle_2 HP should be persisted as 55"
        assert hp_by_id["ge_mg_1"] == 30.0, "ge_mg_1 HP should be persisted as 30"

    def test_campaign_load_restores_surviving_units(
        self, manager: CampaignPersistenceManager
    ) -> None:
        """Load saved campaign -> surviving units restored with HP/morale/experience."""
        units = [
            _make_unit_state("us_rifle_1", "allies", hp=72.0, morale=68.0, experience=12, kills=2),
            _make_unit_state("us_rifle_2", "allies", hp=45.0, morale=55.0, experience=8),
        ]
        progress = CampaignProgress(
            campaign_id="day1_survivors",
            current_operation_id="op_market_garden",
        )
        progress.add_battle_result(
            _make_battle_result(
                battle_id="day1_battle1",
                day=1,
                outcome=BattleOutcome.ALLIED_VICTORY,
                unit_states=units,
            )
        )
        manager.save_campaign_progress("day1_survivors", progress)

        loaded = manager.load_campaign_progress("day1_survivors")
        assert loaded is not None, "load_campaign_progress should return the progress"

        survivors = loaded.get_surviving_units("allies")
        assert len(survivors) == 2, "Both allied units should survive"
        survivor_ids = {u.unit_id for u in survivors}
        assert survivor_ids == {"us_rifle_1", "us_rifle_2"}

        # HP, morale, and experience restored exactly
        us1 = loaded.get_unit_state("us_rifle_1")
        assert us1 is not None
        assert us1.current_hp == 72.0, "Inherited HP should be 72"
        assert us1.morale == 68.0, "Inherited morale should be 68"
        assert us1.experience == 12, "Inherited experience should be 12"
        assert us1.kills == 2, "Inherited kills should be 2"

    def test_campaign_load_marks_dead_units(self, manager: CampaignPersistenceManager) -> None:
        """Load saved campaign -> dead units correctly marked is_alive=False."""
        units = [
            _make_unit_state("us_rifle_1", "allies", hp=80.0, is_alive=True),
            _make_unit_state("us_rifle_2", "allies", hp=0.0, is_alive=False),
            _make_unit_state("us_rifle_3", "allies", hp=0.0, is_alive=False),
        ]
        progress = CampaignProgress(
            campaign_id="day1_dead",
            current_operation_id="op_market_garden",
        )
        progress.add_battle_result(
            _make_battle_result(
                battle_id="day1_battle1",
                day=1,
                outcome=BattleOutcome.ALLIED_VICTORY,
                unit_states=units,
                allied_casualties=2,
            )
        )
        manager.save_campaign_progress("day1_dead", progress)

        loaded = manager.load_campaign_progress("day1_dead")
        assert loaded is not None

        # Surviving units exclude the dead
        survivors = loaded.get_surviving_units("allies")
        assert len(survivors) == 1, "Only 1 allied unit should survive"
        assert survivors[0].unit_id == "us_rifle_1"

        # Dead units marked correctly
        dead2 = loaded.get_unit_state("us_rifle_2")
        assert dead2 is not None
        assert dead2.is_alive is False, "us_rifle_2 should be marked dead"
        assert dead2.current_hp == 0.0, "Dead unit HP should be 0"

        dead3 = loaded.get_unit_state("us_rifle_3")
        assert dead3 is not None
        assert dead3.is_alive is False, "us_rifle_3 should be marked dead"

    def test_campaign_multi_battle_casualty_accumulation(
        self, manager: CampaignPersistenceManager
    ) -> None:
        """Day1: 2 consecutive battles -> casualties accumulate across battles."""
        progress = CampaignProgress(
            campaign_id="day1_accum",
            current_operation_id="op_market_garden",
        )

        # Battle 1: 3 allied casualties, 8 axis casualties
        units_b1 = [
            _make_unit_state("us_rifle_1", "allies", hp=70.0, is_alive=True),
            _make_unit_state("us_rifle_2", "allies", hp=0.0, is_alive=False),
        ]
        progress.add_battle_result(
            _make_battle_result(
                battle_id="day1_battle1",
                day=1,
                outcome=BattleOutcome.ALLIED_VICTORY,
                unit_states=units_b1,
                allied_casualties=3,
                axis_casualties=8,
            )
        )
        manager.save_campaign_progress("day1_accum", progress)

        # Battle 2: 2 more allied casualties, 5 more axis casualties
        units_b2 = [
            _make_unit_state("us_rifle_1", "allies", hp=50.0, is_alive=True),
            _make_unit_state("us_rifle_3", "allies", hp=0.0, is_alive=False),
        ]
        progress.add_battle_result(
            _make_battle_result(
                battle_id="day1_battle2",
                day=1,
                outcome=BattleOutcome.ALLIED_VICTORY,
                unit_states=units_b2,
                allied_casualties=2,
                axis_casualties=5,
            )
        )
        manager.save_campaign_progress("day1_accum", progress)

        loaded = manager.load_campaign_progress("day1_accum")
        assert loaded is not None

        # Casualties accumulated: 3+2=5 allied, 8+5=13 axis
        assert loaded.total_allied_casualties == 5, (
            "Total allied casualties should accumulate to 5 (3+2)"
        )
        assert loaded.total_axis_casualties == 13, (
            "Total axis casualties should accumulate to 13 (8+5)"
        )
        assert loaded.total_battles_completed == 2, "2 battles should be completed"
        assert len(loaded.battle_results) == 2, "2 battle results should be stored"

        # Latest unit states reflect battle 2
        assert loaded.current_unit_states[0].unit_id == "us_rifle_1"
        assert loaded.current_unit_states[0].current_hp == 50.0, (
            "Latest unit state should reflect battle 2 HP"
        )

    def test_campaign_save_load_roundtrip_no_data_loss(self, game_loop, tmp_path: Path) -> None:
        """Full save->load roundtrip -> no data loss across all CampaignProgress fields.

        Routes through the real GameLoop.campaign_persistence to verify E2E.
        """
        game_loop._campaign_persistence = CampaignPersistenceManager(base_dir=tmp_path)
        manager = game_loop.campaign_persistence

        units = [
            _make_unit_state("us_rifle_1", "allies", hp=65.0, morale=72.0, experience=15, kills=3),
            _make_unit_state("ge_mg_1", "axis", hp=40.0, morale=35.0, experience=5, kills=1),
        ]
        progress = CampaignProgress(
            campaign_id="day1_roundtrip",
            current_operation_id="op_market_garden",
            requisition_points_allies=650,
            requisition_points_axis=480,
            sectors_controlled={"arnhem": "allies", "nijmegen": "axis"},
        )
        progress.add_battle_result(
            _make_battle_result(
                battle_id="day1_battle1",
                day=1,
                outcome=BattleOutcome.ALLIED_VICTORY,
                unit_states=units,
                allied_casualties=2,
                axis_casualties=6,
                allied_vp=100,
                axis_vp=20,
            )
        )

        assert manager.save_campaign_progress("day1_roundtrip", progress) is True

        loaded = manager.load_campaign_progress("day1_roundtrip")
        assert loaded is not None

        # All top-level fields preserved
        assert loaded.campaign_id == "day1_roundtrip"
        assert loaded.current_operation_id == "op_market_garden"
        assert loaded.total_battles_completed == 1
        assert loaded.current_battle_index == 1
        assert loaded.requisition_points_allies == 650
        assert loaded.requisition_points_axis == 480
        assert loaded.total_allied_casualties == 2
        assert loaded.total_axis_casualties == 6
        assert loaded.sectors_controlled == {"arnhem": "allies", "nijmegen": "axis"}

        # Battle result preserved (including enum reconstruction)
        assert len(loaded.battle_results) == 1
        br = loaded.battle_results[0]
        assert br.battle_id == "day1_battle1"
        assert br.day == 1
        assert br.outcome == BattleOutcome.ALLIED_VICTORY, (
            "BattleOutcome enum should be reconstructed from saved string"
        )
        assert br.allied_vp_earned == 100
        assert br.axis_vp_earned == 20

        # Unit states preserved with all fields
        assert len(loaded.current_unit_states) == 2
        us1 = loaded.get_unit_state("us_rifle_1")
        assert us1 is not None
        assert us1.current_hp == 65.0
        assert us1.morale == 72.0
        assert us1.experience == 15
        assert us1.kills == 3
        assert us1.is_alive is True

    def test_campaign_list_saved_campaigns(self, manager: CampaignPersistenceManager) -> None:
        """list_saved_campaigns returns all saved campaigns with metadata."""
        # Save two distinct campaigns
        for cid, casualties in [("day1_list_a", 1), ("day1_list_b", 3)]:
            progress = CampaignProgress(
                campaign_id=cid,
                current_operation_id="op_market_garden",
            )
            progress.add_battle_result(
                _make_battle_result(
                    battle_id=f"{cid}_b1",
                    day=1,
                    outcome=BattleOutcome.ALLIED_VICTORY,
                    unit_states=[_make_unit_state(f"{cid}_u1", "allies", hp=80.0)],
                    allied_casualties=casualties,
                )
            )
            manager.save_campaign_progress(cid, progress)

        saves = manager.list_saved_campaigns()
        assert isinstance(saves, list)
        assert len(saves) >= 2, "list_saved_campaigns should return at least 2 entries"

        ids = {s["campaign_id"] for s in saves}
        assert "day1_list_a" in ids, "day1_list_a should be in the list"
        assert "day1_list_b" in ids, "day1_list_b should be in the list"

        # Each entry has required metadata fields
        for entry in saves:
            if entry["campaign_id"] in ("day1_list_a", "day1_list_b"):
                assert "saved_at" in entry, "Entry should have saved_at timestamp"
                assert "battles_completed" in entry
                assert entry["battles_completed"] == 1, (
                    "Each saved campaign should have 1 completed battle"
                )
                assert "file_path" in entry, "Entry should have file_path"
                assert "current_operation" in entry
                assert entry["current_operation"] == "op_market_garden"
