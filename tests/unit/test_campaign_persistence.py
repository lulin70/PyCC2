"""
Unit tests for P5.1 Campaign Persistence system.
Covers: VeterancyComponent, UnitBattleRecord, BattleResult, PersistentUnit, CampaignState
"""

from __future__ import annotations

import pytest

from pycc2.domain.components.veterancy_component import (
    RANK_BONUSES,
    VeterancyComponent,
    VeteranRank,
)
from pycc2.domain.systems.battle_result import (
    BattleOutcome,
    BattleResult,
    UnitBattleRecord,
)
from pycc2.domain.systems.campaign_state import (
    BRIDGE_NAMES,
    CampaignState,
    OperationPhase,
    PersistentUnit,
)


class TestVeterancyComponentConstruction:
    def test_default_is_recruit(self):
        v = VeterancyComponent()
        assert v.rank == VeteranRank.RECRUIT
        assert v.xp == 0
        assert v.kills == 0
        assert v.battles_survived == 0

    def test_custom_initial_xp(self):
        v = VeterancyComponent(xp=150)
        assert v.rank == VeteranRank.REGULAR

    def test_veteran_threshold(self):
        v = VeterancyComponent(xp=300)
        assert v.rank == VeteranRank.VETERAN

    def test_elite_threshold(self):
        v = VeterancyComponent(xp=600)
        assert v.rank == VeteranRank.ELITE


class TestVeterancyXPGrowth:
    def test_add_xp_no_rank_change(self):
        v = VeterancyComponent()
        changed = v.add_xp(50)
        assert changed is False
        assert v.xp == 50
        assert v.rank == VeteranRank.RECRUIT

    def test_add_xp_triggers_rank_up(self):
        v = VeterancyComponent()
        changed = v.add_xp(100)
        assert changed is True
        assert v.rank == VeteranRank.REGULAR

    def test_multiple_rankups(self):
        v = VeterancyComponent()
        r1 = v.add_xp(100)
        assert r1 is True
        assert v.rank == VeteranRank.REGULAR
        r2 = v.add_xp(200)
        assert r2 is True
        assert v.rank == VeteranRank.VETERAN
        r3 = v.add_xp(300)
        assert r3 is True
        assert v.rank == VeteranRank.ELITE

    def test_record_kill(self):
        v = VeterancyComponent()
        v.record_kill()
        assert v.kills == 1
        assert v.xp == 15

    def test_record_kill_with_custom_xp(self):
        v = VeterancyComponent()
        v.record_kill(xp_reward=30)
        assert v.kills == 1
        assert v.xp == 30

    def test_record_battle_survived(self):
        v = VeterancyComponent()
        changed = v.record_battle_survived()
        assert changed is False
        assert v.battles_survived == 1
        assert v.xp == 25


class TestVeterancyShotsAndAccuracy:
    def test_record_shot_hit(self):
        v = VeterancyComponent()
        v.record_shot(hit=True, damage=25.0)
        assert v.shots_fired == 1
        assert v.shots_hit == 1
        assert v.total_damage_dealt == 25.0

    def test_record_shot_miss(self):
        v = VeterancyComponent()
        v.record_shot(hit=False)
        assert v.shots_fired == 1
        assert v.shots_hit == 0

    def test_accuracy_zero_when_no_shots(self):
        v = VeterancyComponent()
        assert v.accuracy == 0.0

    def test_accuracy_calculation(self):
        v = VeterancyComponent()
        for _ in range(7):
            v.record_shot(hit=True, damage=10.0)
        for _ in range(3):
            v.record_shot(hit=False)
        assert v.accuracy == pytest.approx(0.7)

    def test_total_damage_accumulates(self):
        v = VeterancyComponent()
        v.record_shot(hit=True, damage=15.5)
        v.record_shot(hit=True, damage=10.3)
        assert v.total_damage_dealt == pytest.approx(25.8)


class TestVeterancyRankBonuses:
    def test_recruit_no_bonus(self):
        v = VeterancyComponent()
        assert v.accuracy_bonus == 1.0
        assert v.morale_resistance == 1.0
        assert v.panic_probability_mod == 1.0

    def test_regular_bonuses(self):
        v = VeterancyComponent(xp=100)
        assert v.accuracy_bonus == 1.08
        assert v.morale_resistance == 1.1
        assert v.panic_probability_mod == 0.92

    def test_veteran_bonuses(self):
        v = VeterancyComponent(xp=300)
        assert v.accuracy_bonus == 1.15
        assert v.morale_resistance == 1.2
        assert v.panic_probability_mod == 0.80

    def test_elite_bonuses(self):
        v = VeterancyComponent(xp=600)
        assert v.accuracy_bonus == 1.22
        assert v.morale_resistance == 1.35
        assert v.panic_probability_mod == 0.65

    def test_elite_panic_resistance_strongest(self):
        bonuses = [RANK_BONUSES[r]["panic_chance"] for r in VeteranRank]
        assert bonuses == sorted(bonuses, reverse=True)


class TestVeterancyProgression:
    def test_xp_to_next_rank_from_recruit(self):
        v = VeterancyComponent()
        assert v.xp_to_next_rank() == 100

    def test_xp_to_next_rank_partial_progress(self):
        v = VeterancyComponent(xp=50)
        assert v.xp_to_next_rank() == 50

    def test_xp_to_next_rank_at_max(self):
        v = VeterancyComponent(xp=600)
        assert v.xp_to_next_rank() == 0

    def test_progress_zero_at_start(self):
        v = VeterancyComponent()
        assert v.progress_to_next_rank() == 0.0

    def test_progress_halfway(self):
        v = VeterancyComponent(xp=50)
        assert v.progress_to_next_rank() == pytest.approx(0.5)

    def test_progress_max_at_elite(self):
        v = VeterancyComponent(xp=600)
        assert v.progress_to_next_rank() == 1.0

    def test_progress_clamped_at_1(self):
        v = VeterancyComponent(xp=9999)
        assert v.progress_to_next_rank() == 1.0


class TestVeterancySerialization:
    def test_roundtrip_dict(self):
        v = VeterancyComponent(
            xp=250,
            kills=5,
            battles_survived=3,
            shots_fired=40,
            shots_hit=28,
            total_damage_dealt=140.5,
        )
        d = v.to_dict()
        restored = VeterancyComponent.from_dict(d)
        assert restored.xp == 250
        assert restored.kills == 5
        assert restored.battles_survived == 3
        assert restored.shots_fired == 40
        assert restored.shots_hit == 28
        assert restored.total_damage_dealt == pytest.approx(140.5)
        assert restored.rank == v.rank

    def test_from_empty_dict(self):
        v = VeterancyComponent.from_dict({})
        assert v.xp == 0
        assert v.rank == VeteranRank.RECRUIT

    def test_dict_contains_rank_name(self):
        v = VeterancyComponent(xp=350)
        d = v.to_dict()
        assert d["rank"] == "VETERAN"


class TestUnitBattleRecord:
    def test_efficiency_all_hits(self):
        r = UnitBattleRecord(
            unit_id="u1",
            unit_type="INFANTRY",
            faction="allies",
            survived=True,
            hp_start=100,
            hp_end=80,
            damage_dealt=45.0,
            damage_taken=20,
            kills=2,
            shots_fired=10,
            shots_hit=8,
        )
        assert r.efficiency == pytest.approx(0.8)

    def test_efficiency_no_shots(self):
        r = UnitBattleRecord(
            unit_id="u1",
            unit_type="INFANTRY",
            faction="allies",
            survived=True,
            hp_start=100,
            hp_end=100,
            damage_dealt=0,
            damage_taken=0,
            kills=0,
            shots_fired=0,
            shots_hit=0,
        )
        assert r.efficiency == 0.0

    def test_survived_true(self):
        r = UnitBattleRecord(
            unit_id="u1",
            unit_type="TANK",
            faction="axis",
            survived=True,
            hp_start=150,
            hp_end=30,
            damage_dealt=120.0,
            damage_taken=120,
            kills=3,
            shots_fired=15,
            shots_hit=12,
        )
        assert r.survived is True

    def test_default_xp_gained(self):
        r = UnitBattleRecord(
            unit_id="u1",
            unit_type="INFANTRY",
            faction="allies",
            survived=True,
            hp_start=100,
            hp_end=90,
            damage_dealt=30.0,
            damage_taken=10,
            kills=1,
            shots_fired=5,
            shots_hit=4,
        )
        assert r.xp_gained == 0


class TestBattleResultConstruction:
    def test_basic_construction(self):
        br = BattleResult(
            mission_id="m1",
            mission_name="Test Mission",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=3000,
        )
        assert br.mission_id == "m1"
        assert br.outcome == BattleOutcome.VICTORY
        assert br.is_victory is True

    def test_defeat_not_victory(self):
        br = BattleResult(
            mission_id="m2",
            mission_name="Loss",
            outcome=BattleOutcome.DEFEAT,
            ticks_elapsed=1500,
        )
        assert br.is_victory is False

    def test_timeout_victory_counts_as_win(self):
        br = BattleResult(
            mission_id="m3",
            mission_name="Timeout Win",
            outcome=BattleOutcome.TIME_OUT_VICTORY,
            ticks_elapsed=5400,
        )
        assert br.is_victory is True

    def test_timeout_defeat_not_win(self):
        br = BattleResult(
            mission_id="m4",
            mission_name="Timeout Loss",
            outcome=BattleOutcome.TIME_OUT_DEFEAT,
            ticks_elapsed=5400,
        )
        assert br.is_victory is False


class TestBattleResultStats:
    def test_allies_accuracy(self):
        br = BattleResult(
            mission_id="m1",
            mission_name="Stat Test",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=2000,
            total_shots_fired_allies=100,
            total_shots_hit_allies=65,
        )
        assert br.allies_accuracy == pytest.approx(0.65)

    def test_axis_accuracy_zero_when_no_shots(self):
        br = BattleResult(
            mission_id="m1",
            mission_name="No Shots",
            outcome=BattleOutcome.DRAW,
            ticks_elapsed=500,
        )
        assert br.axis_accuracy == 0.0

    def test_survival_rate_all_units_live(self):
        br = BattleResult(
            mission_id="m1",
            mission_name="Perfect",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=1000,
            unit_records=[
                UnitBattleRecord("a1", "INF", "allies", True, 100, 100, 0, 0, 0, 0, 0),
                UnitBattleRecord("a2", "INF", "allies", True, 100, 90, 0, 10, 1, 5, 3),
                UnitBattleRecord("x1", "INF", "axis", False, 100, 0, 0, 100, 0, 2, 0),
            ],
        )
        assert br.survival_rate_allies == pytest.approx(1.0)

    def test_survival_rate_partial_losses(self):
        br = BattleResult(
            mission_id="m1",
            mission_name="Casualties",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=2000,
            unit_records=[
                UnitBattleRecord("a1", "INF", "allies", True, 100, 60, 20, 40, 1, 10, 7),
                UnitBattleRecord("a2", "INF", "allies", False, 100, 0, 5, 100, 0, 3, 1),
                UnitBattleRecord("a3", "INF", "allies", True, 100, 80, 15, 20, 0, 8, 5),
            ],
        )
        assert br.survival_rate_allies == pytest.approx(2 / 3)

    def test_survival_rate_no_ally_records(self):
        br = BattleResult(
            mission_id="m1",
            mission_name="Empty Allies",
            outcome=BattleOutcome.DEFEAT,
            ticks_elapsed=500,
            unit_records=[
                UnitBattleRecord("x1", "INF", "axis", True, 100, 80, 0, 20, 0, 0, 0),
            ],
        )
        assert br.survival_rate_allies == 0.0


class TestBattleResultVPCalculation:
    def test_vp_clean_victory(self):
        br = BattleResult(
            mission_id="m1",
            mission_name="Clean Win",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=1800,
            axis_killed=5,
            allies_killed=0,
            objectives_completed=2,
            objectives_total=2,
            unit_records=[
                UnitBattleRecord("a1", "INF", "allies", True, 100, 95, 0, 5, 0, 0, 0),
                UnitBattleRecord("a2", "INF", "allies", True, 100, 90, 0, 10, 0, 0, 0),
                UnitBattleRecord("a3", "INF", "allies", True, 100, 88, 0, 12, 0, 0, 0),
            ],
        )
        vp = br.calculate_vp()
        assert vp > 0
        assert br.victory_points == vp

    def test_vp_pyrrhic_victory(self):
        br = BattleResult(
            mission_id="m1",
            mission_name="Pyrrhic",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=4000,
            axis_killed=8,
            allies_killed=6,
            allies_routed=2,
            objectives_completed=1,
            unit_records=[
                UnitBattleRecord("a1", "INF", "allies", False, 100, 0, 30, 100, 2, 15, 10),
                UnitBattleRecord("a2", "INF", "allies", False, 100, 0, 20, 100, 1, 8, 5),
                UnitBattleRecord("a3", "INF", "allies", True, 100, 30, 40, 70, 3, 20, 14),
                UnitBattleRecord("a4", "INF", "allies", True, 100, 45, 35, 55, 1, 12, 8),
            ],
        )
        vp = br.calculate_vp()
        assert vp >= 0

    def test_vp_defeat_is_non_negative(self):
        br = BattleResult(
            mission_id="m1",
            mission_name="Crushing Defeat",
            outcome=BattleOutcome.DEFEAT,
            ticks_elapsed=800,
            axis_killed=0,
            allies_killed=10,
            allies_routed=3,
            unit_records=[
                UnitBattleRecord(f"a{i}", "INF", "allies", False, 100, 0, 0, 100, 0, 0, 0)
                for i in range(5)
            ],
        )
        vp = br.calculate_vp()
        assert vp >= 0

    def test_vp_survival_bonus_high(self):
        br = BattleResult(
            mission_id="m1",
            mission_name="Survivors",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=2000,
            unit_records=[
                UnitBattleRecord(
                    f"a{i}", "INF", "allies", True, 100, 90 + i * 2, 0, 10 - i * 2, 0, 5, 3
                )
                for i in range(5)
            ],
        )
        br.calculate_vp()
        base_vp = 100 + 0 * 25 + 0 * 15 + 0 * 10 - 0 * 20 - 0 * 15
        assert br.victory_points >= base_vp + 30


class TestBattleResultSerialization:
    def test_roundtrip_dict(self):
        br = BattleResult(
            mission_id="m1",
            mission_name="Serialize Test",
            outcome=BattleOutcome.TIME_OUT_VICTORY,
            ticks_elapsed=5400,
            date_in_campaign=3,
            allies_killed=2,
            axis_killed=7,
            allies_routed=1,
            axis_routed=3,
            victory_points=145,
            unit_records=[
                UnitBattleRecord("a1", "INF", "allies", True, 100, 70, 55.5, 30, 3, 20, 14, 45),
            ],
        )
        d = br.to_dict()
        restored = BattleResult.from_dict(d)
        assert restored.mission_id == "m1"
        assert restored.outcome == BattleOutcome.TIME_OUT_VICTORY
        assert restored.date_in_campaign == 3
        assert restored.allies_killed == 2
        assert restored.axis_killed == 7
        assert restored.victory_points == 145
        assert len(restored.unit_records) == 1
        assert restored.unit_records[0].unit_id == "a1"
        assert restored.unit_records[0].xp_gained == 45


class TestPersistentUnit:
    def test_default_construction(self):
        pu = PersistentUnit(unit_id="A-101", name="Alpha", unit_type="INFANTRY_SQUAD")
        assert pu.is_alive is True
        assert pu.current_hp == 100
        assert pu.hp_ratio == 1.0
        assert pu.ammo_ratio == 1.0
        assert pu.veterancy.rank == VeteranRank.RECRUIT
        assert pu.battles_participated == 0

    def test_hp_ratio_calculation(self):
        pu = PersistentUnit(
            unit_id="A-102", name="Bravo", unit_type="TANK", current_hp=60, max_hp=100
        )
        assert pu.hp_ratio == 0.6

    def test_ammo_ratio_calculation(self):
        pu = PersistentUnit(
            unit_id="A-103", name="Charlie", unit_type="MG", current_ammo=30, max_ammo=80
        )
        assert pu.ammo_ratio == pytest.approx(0.375)

    def test_apply_battle_result_survives(self):
        pu = PersistentUnit(unit_id="A-101", name="Alpha", unit_type="INFANTRY")
        pu.apply_battle_result(
            {
                "hp_end": 75,
                "survived": True,
                "xp_gained": 40,
                "kills": 2,
                "ammo_used": 12,
            }
        )
        assert pu.current_hp == 75
        assert pu.is_alive is True
        assert pu.current_ammo == 88
        assert pu.battles_participated == 1
        assert pu.veterancy.xp == 40
        assert pu.veterancy.kills == 2

    def test_apply_battle_result_dies(self):
        pu = PersistentUnit(unit_id="A-201", name="Dead Unit", unit_type="INFANTRY")
        pu.apply_battle_result({"hp_end": 0, "survived": False})
        assert pu.is_alive is False
        assert pu.current_hp == 0

    def test_replenish_recovers_hp_and_ammo(self):
        pu = PersistentUnit(
            unit_id="A-101",
            name="Wounded",
            unit_type="INFANTRY",
            current_hp=40,
            max_hp=100,
            current_ammo=20,
            max_ammo=100,
        )
        pu.replenish(hp_pct=0.5, ammo_pct=0.6)
        assert pu.current_hp == 90
        assert pu.current_ammo == 80

    def test_replenish_does_not_exceed_max(self):
        pu = PersistentUnit(
            unit_id="A-101",
            name="Healthy",
            unit_type="INFANTRY",
            current_hp=90,
            max_hp=100,
            current_ammo=95,
            max_ammo=100,
        )
        pu.replenish(hp_pct=1.0, ammo_pct=1.0)
        assert pu.current_hp == 100
        assert pu.current_ammo == 100

    def test_replenish_dead_unit_no_effect(self):
        pu = PersistentUnit(
            unit_id="A-301",
            name="KIA",
            unit_type="INFANTRY",
            is_alive=False,
            current_hp=0,
            max_hp=100,
            current_ammo=0,
            max_ammo=100,
        )
        pu.replenish()
        assert pu.current_hp == 0
        assert pu.current_ammo == 0

    def test_serialization_roundtrip(self):
        pu = PersistentUnit(
            unit_id="A-101",
            name="Veteran Squad",
            unit_type="INFANTRY_SQUAD",
            current_hp=72,
            max_hp=100,
            current_ammo=55,
            max_ammo=80,
            battles_participated=5,
        )
        pu.veterancy.add_xp(350)
        pu.veterancy.kills = 8
        d = pu.to_dict()
        restored = PersistentUnit.from_dict(d)
        assert restored.unit_id == "A-101"
        assert restored.name == "Veteran Squad"
        assert restored.current_hp == 72
        assert restored.is_alive is True
        assert restored.battles_participated == 5
        assert restored.veterancy.xp == 350
        assert restored.veterancy.kills == 8
        assert restored.veterancy.rank == VeteranRank.VETERAN

    def test_from_dict_missing_optional_fields(self):
        d = {"unit_id": "X-1", "name": "Min", "unit_type": "INF"}
        pu = PersistentUnit.from_dict(d)
        assert pu.is_alive is True
        assert pu.current_hp == 100
        assert pu.max_hp == 100
        assert pu.veterancy.rank == VeteranRank.RECRUIT


class TestCampaignStateDefaults:
    def test_create_default_has_units(self):
        state = CampaignState.create_default()
        assert len(state.allied_units) == 3
        assert state.alive_allied_count == 3
        assert state.campaign_id == "market_garden"

    def test_default_day_is_sept17(self):
        state = CampaignState.create_default()
        assert state.current_day == OperationPhase.DAY_1_SEPT17

    def test_default_bridges_all_uncaptured(self):
        state = CampaignState.create_default()
        assert all(v is False for v in state.bridges_captured.values())
        assert state.bridges_held == 0

    def test_default_reinforcements(self):
        state = CampaignState.create_default()
        assert state.available_reinforcements == 3

    def test_default_modifiers(self):
        state = CampaignState.create_default()
        assert state.enemy_strength_modifier == 1.0
        assert state.morale_modifier == 1.0


class TestCampaignStateBridges:
    def test_capture_bridge(self):
        state = CampaignState.create_default()
        result = state.capture_bridge("son")
        assert result is True
        assert state.bridges_captured["son"] is True
        assert state.bridges_held == 1

    def test_capture_invalid_bridge_returns_false(self):
        state = CampaignState.create_default()
        result = state.capture_bridge("nonexistent")
        assert result is False

    def test_capture_all_bridges(self):
        state = CampaignState.create_default()
        for key in BRIDGE_NAMES:
            state.capture_bridge(key)
        assert state.bridges_held == 5
        assert state.campaign_progress_pct == 1.0

    def test_bridge_names_constant(self):
        assert "son" in BRIDGE_NAMES
        assert "arnhem" in BRIDGE_NAMES
        assert len(BRIDGE_NAMES) == 5


class TestCampaignStateDayProgression:
    def test_advance_day(self):
        state = CampaignState.create_default()
        assert state.current_day == OperationPhase.DAY_1_SEPT17
        state.advance_day()
        assert state.current_day == OperationPhase.DAY_2_SEPT18

    def test_advance_day_increases_enemy_strength(self):
        state = CampaignState.create_default()
        initial = state.enemy_strength_modifier
        state.advance_day()
        assert state.enemy_strength_modifier > initial

    def test_advance_to_final_day(self):
        state = CampaignState.create_default()
        days = list(OperationPhase)
        for _ in range(len(days) - 2):
            state.advance_day()
        assert state.current_day == OperationPhase.DAY_6_SEPT22

    def test_advance_past_last_day_stays(self):
        state = CampaignState()
        state.current_day = OperationPhase.DAY_6_SEPT22
        old_day = state.current_day
        state.advance_day()
        assert state.current_day == old_day


class TestCampaignStateBattleRecording:
    def test_record_battle_increments_counters(self):
        state = CampaignState.create_default()
        br = BattleResult(
            mission_id="m1",
            mission_name="First Blood",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=2000,
            victory_points=120,
        )
        state.record_battle(br)
        assert state.total_battles_played == 1
        assert state.current_battle_number == 1
        assert state.total_vp == 120
        assert len(state.battle_history) == 1

    def test_record_multiple_battles(self):
        state = CampaignState.create_default()
        for i in range(3):
            br = BattleResult(
                mission_id=f"m{i}",
                mission_name=f"Battle {i}",
                outcome=BattleOutcome.VICTORY if i % 2 == 0 else BattleOutcome.DEFEAT,
                ticks_elapsed=1000 * (i + 1),
                victory_points=50 + i * 30,
            )
            state.record_battle(br)
        assert state.total_battles_played == 3
        assert state.total_vp == 50 + 80 + 110

    def test_morale_modifier_rises_with_wins(self):
        state = CampaignState.create_default()
        for _ in range(3):
            br = BattleResult(
                mission_id="win",
                mission_name="Win",
                outcome=BattleOutcome.VICTORY,
                ticks_elapsed=1000,
                victory_points=100,
            )
            state.record_battle(br)
        assert state.morale_modifier > 1.0

    def test_morale_modifier_drops_with_losses(self):
        state = CampaignState.create_default()
        for _ in range(3):
            br = BattleResult(
                mission_id="loss",
                mission_name="Loss",
                outcome=BattleOutcome.DEFEAT,
                ticks_elapsed=800,
                victory_points=10,
            )
            state.record_battle(br)
        assert state.morale_modifier < 1.0

    def test_morale_modifier_clamped(self):
        state = CampaignState.create_default()
        for _ in range(10):
            br = BattleResult(
                mission_id="big_loss",
                mission_name="Bad",
                outcome=BattleOutcome.DEFEAT,
                ticks_elapsed=200,
                victory_points=0,
            )
            state.record_battle(br)
        assert state.morale_modifier >= 0.7

    def test_unit_records_applied_to_persistent_units(self):
        state = CampaignState.create_default()
        br = BattleResult(
            mission_id="m1",
            mission_name="Apply Units",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=1500,
            unit_records=[
                UnitBattleRecord("A-101", "INF", "allies", True, 100, 70, 30, 30, 2, 15, 10, 40),
                UnitBattleRecord("A-102", "INF", "allies", True, 100, 45, 20, 55, 1, 10, 6, 25),
            ],
        )
        state.record_battle(br)
        a101 = next(u for u in state.allied_units if u.unit_id == "A-101")
        assert a101.current_hp == 70
        assert a101.battles_participated == 1
        assert a101.veterancy.xp == 40


class TestCampaignStateReplenishment:
    def test_replenish_all_units(self):
        state = CampaignState.create_default()
        for u in state.allied_units:
            u.current_hp = 40
            u.current_ammo = 20
        state.replenish_all_units()
        for u in state.allied_units:
            assert u.current_hp > 40
            assert u.current_ammo > 20
            assert u.current_hp <= 100

    def test_replenish_dead_units_unchanged(self):
        state = CampaignState.create_default()
        state.allied_units[0].is_alive = False
        state.allied_units[0].current_hp = 0
        state.replenish_all_units()
        assert state.allied_units[0].current_hp == 0


class TestCampaignStateEndConditions:
    def test_not_over_at_start(self):
        state = CampaignState.create_default()
        assert state.is_campaign_over is False
        assert state.campaign_outcome == "ongoing"

    def test_victory_all_bridges_captured(self):
        state = CampaignState.create_default()
        for key in BRIDGE_NAMES:
            state.capture_bridge(key)
        assert state.is_campaign_over is True
        assert state.campaign_outcome == "decisive_victory"

    def test_defeat_no_allies_left(self):
        state = CampaignState.create_default()
        for u in state.allied_units:
            u.is_alive = False
        assert state.is_campaign_over is True
        assert state.campaign_outcome == "defeat"

    def test_tactical_victory_some_bridges_on_final_day(self):
        state = CampaignState()
        state.current_day = OperationPhase.DAY_6_SEPT22
        state.capture_bridge("son")
        state.capture_bridge("veghel")
        state.capture_bridge("grave")
        assert state.is_campaign_over is True
        assert state.campaign_outcome == "tactical_victory"

    def test_marginal_result_one_bridge(self):
        state = CampaignState.create_default()
        state.current_day = OperationPhase.DAY_6_SEPT22
        assert state.bridges_held == 0
        assert state.alive_allied_count > 0
        assert state.is_campaign_over is True
        assert state.campaign_outcome == "marginal_result"


class TestCampaignStateAverageVeterancy:
    def test_average_veterancy_all_recruits(self):
        state = CampaignState.create_default()
        assert state.average_allied_veterancy == 0.0

    def test_average_veterancy_mixed(self):
        state = CampaignState.create_default()
        state.allied_units[0].veterancy.add_xp(150)
        state.allied_units[1].veterancy.add_xp(350)
        state.allied_units[2].veterancy.add_xp(600)
        avg = state.average_allied_veterancy
        assert avg == pytest.approx((1.0 + 2.0 + 3.0) / 3.0)

    def test_average_veterancy_no_alive_units(self):
        state = CampaignState.create_default()
        for u in state.allied_units:
            u.is_alive = False
        assert state.average_allied_veterancy == 0.0


class TestCampaignStateSerialization:
    def test_full_roundtrip(self):
        state = CampaignState.create_default()
        state.capture_bridge("son")
        state.advance_day()
        state.allied_units[0].veterancy.add_xp(200)
        br = BattleResult(
            mission_id="m1",
            mission_name="Saved Battle",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=2500,
            date_in_campaign=2,
            victory_points=95,
            allies_killed=1,
            axis_killed=4,
            unit_records=[
                UnitBattleRecord("A-101", "INF", "allies", True, 100, 80, 35, 20, 2, 12, 8, 50),
            ],
        )
        state.record_battle(br)
        d = state.to_dict()
        restored = CampaignState.from_dict(d)
        assert restored.campaign_id == "market_garden"
        assert restored.current_day == OperationPhase.DAY_2_SEPT18
        assert restored.bridges_captured["son"] is True
        assert restored.total_battles_played == 1
        assert restored.total_vp == 95
        assert len(restored.allied_units) == 3
        assert restored.allied_units[0].veterancy.xp == 250
        assert len(restored.battle_history) == 1

    def test_from_empty_dict_defaults(self):
        state = CampaignState.from_dict({})
        assert state.campaign_id == "market_garden"
        assert state.current_day == OperationPhase.DAY_1_SEPT17
        assert state.alive_allied_count == 0

    def test_from_dict_invalid_day_fallback(self):
        state = CampaignState.from_dict({"current_day": "INVALID_DAY"})
        assert state.current_day == OperationPhase.DAY_1_SEPT17


class TestCampaignStateIntegration:
    def test_full_campaign_flow(self):
        state = CampaignState.create_default()

        battle1 = BattleResult(
            mission_id="m_son",
            mission_name="Son Bridge",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=2800,
            date_in_campaign=1,
            axis_killed=6,
            allies_killed=1,
            objectives_completed=1,
            objectives_total=1,
            victory_points=130,
            unit_records=[
                UnitBattleRecord("A-101", "INF", "allies", True, 100, 70, 40, 30, 3, 18, 12, 55),
                UnitBattleRecord("A-102", "INF", "allies", True, 100, 55, 25, 45, 1, 14, 8, 35),
                UnitBattleRecord("A-103", "CMD", "allies", True, 100, 85, 15, 15, 0, 4, 2, 15),
            ],
        )
        state.record_battle(battle1)
        state.capture_bridge("son")
        state.replenish_all_units()

        assert state.total_battles_played == 1
        assert state.bridges_held == 1
        assert state.is_campaign_over is False

        state.advance_day()

        battle2 = BattleResult(
            mission_id="m_veghel",
            mission_name="Veghel",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=3200,
            date_in_campaign=2,
            axis_killed=8,
            allies_killed=2,
            objectives_completed=1,
            objectives_total=1,
            victory_points=115,
            unit_records=[
                UnitBattleRecord("A-101", "INF", "allies", True, 78, 60, 30, 18, 2, 10, 7, 40),
                UnitBattleRecord("A-102", "INF", "allies", False, 68, 0, 15, 68, 0, 6, 2, 0),
                UnitBattleRecord("A-103", "CMD", "allies", True, 92, 80, 20, 12, 1, 8, 5, 30),
            ],
        )
        state.record_battle(battle2)
        state.capture_bridge("veghel")

        assert state.alive_allied_count == 2
        assert state.morale_modifier > 1.0
        assert state.campaign_outcome == "ongoing"

        a101 = next(u for u in state.allied_units if u.unit_id == "A-101")
        assert a101.veterancy.xp >= 95
        assert a101.battles_participated == 2
