import random

from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.difficulty_system import (
    DifficultyLevel,
    DifficultySystem,
)
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType


class TestDifficultyPresets:
    def test_easy_preset_values(self):
        cfg = DifficultySystem.PRESETS[DifficultyLevel.EASY]
        assert cfg.vision_range_multiplier == 0.7
        assert cfg.reaction_delay_ticks == 15
        assert cfg.perception_accuracy == 0.6
        assert cfg.base_hit_chance == 0.25
        assert cfg.coordination_enabled is False
        assert cfg.use_flanking is False
        assert cfg.aggressiveness == 0.2

    def test_medium_preset_baseline(self):
        cfg = DifficultySystem.PRESETS[DifficultyLevel.MEDIUM]
        assert cfg.vision_range_multiplier == 1.0
        assert cfg.reaction_delay_ticks == 0
        assert cfg.perception_accuracy == 1.0
        assert cfg.base_hit_chance == 0.5
        assert cfg.coordination_enabled is False
        assert cfg.aggressiveness == 0.5

    def test_hard_preset_enables_coordination(self):
        cfg = DifficultySystem.PRESETS[DifficultyLevel.HARD]
        assert cfg.coordination_enabled is True
        assert cfg.use_flanking is True
        assert cfg.use_suppression_tactics is True
        assert cfg.base_hit_chance == 0.65
        assert cfg.aggressiveness == 0.75

    def test_veteran_preset_most_aggressive(self):
        cfg = DifficultySystem.PRESETS[DifficultyLevel.VETERAN]
        assert cfg.base_hit_chance >= DifficultySystem.PRESETS[DifficultyLevel.HARD].base_hit_chance
        assert cfg.aggressiveness == 0.9
        assert cfg.aim_time_multiplier < 1.0
        assert (
            cfg.tactical_variety < DifficultySystem.PRESETS[DifficultyLevel.MEDIUM].tactical_variety
        )


class TestModifyAIDecision_Delay:
    def test_reaction_delay_returns_none(self):
        ds = DifficultySystem(DifficultyLevel.EASY)
        bb = Blackboard()
        intent = TacticIntent(unit_id="u1", tactic_type=TacticType.ATTACK)
        result = ds.modify_ai_decision(intent, bb)
        assert result is not None
        assert bb.get("reaction_delay_u1") == 15
        result2 = ds.modify_ai_decision(intent, bb)
        assert result2 is None
        assert bb.get("reaction_delay_u1") == 14

    def test_reaction_delay_consumes_to_zero(self):
        ds = DifficultySystem(DifficultyLevel.EASY)
        bb = Blackboard()
        intent = TacticIntent(unit_id="u2", tactic_type=TacticType.ATTACK)
        bb.set("reaction_delay_u2", 1)
        result = ds.modify_ai_decision(intent, bb)
        assert result is None
        assert bb.get("reaction_delay_u2") == 0

    def test_no_delay_on_medium(self):
        ds = DifficultySystem(DifficultyLevel.MEDIUM)
        bb = Blackboard()
        intent = TacticIntent(unit_id="u3", tactic_type=TacticType.ATTACK)
        result = ds.modify_ai_decision(intent, bb)
        assert result is not None


class TestModifyAIDecision_Perception:
    def test_low_perception_can_ignore_target(self):
        ds = DifficultySystem(DifficultyLevel.EASY)
        bb = Blackboard()
        intent = TacticIntent(unit_id="u4", tactic_type=TacticType.ATTACK, target_unit_id="e1")
        rng = random.Random(42)
        results = [ds.modify_ai_decision(intent, bb, rng=rng) for _ in range(50)]
        assert any(r is None for r in results)

    def test_full_perception_never_ignores(self):
        ds = DifficultySystem(DifficultyLevel.MEDIUM)
        bb = Blackboard()
        intent = TacticIntent(unit_id="u5", tactic_type=TacticType.ATTACK, target_unit_id="e1")
        rng = random.Random(99)
        for _ in range(30):
            result = ds.modify_ai_decision(intent, bb, rng=rng)
            assert result is not None


class TestModifyAIDecision_TacticalVariety:
    def test_tactical_variety_can_alternate(self):
        ds = DifficultySystem(DifficultyLevel.EASY)
        bb = Blackboard()
        intent = TacticIntent(unit_id="u6", tactic_type=TacticType.ATTACK)
        rng = random.Random(7)
        types_seen = set()
        for _ in range(200):
            result = ds.modify_ai_decision(intent, bb, rng=rng)
            if result:
                types_seen.add(result.tactic_type)
        assert len(types_seen) > 1


class TestModifyAIDecision_Aggressiveness:
    def test_low_aggressiveness_converts_attack_to_hold(self):
        ds = DifficultySystem(DifficultyLevel.EASY)
        bb = Blackboard()
        bb.set("health_ratio", 0.9)
        intent = TacticIntent(unit_id="u7", tactic_type=TacticType.ATTACK)
        rng = random.Random(123)
        holds = 0
        total_non_alt = 0
        for _ in range(300):
            result = ds.modify_ai_decision(intent, bb, rng=rng)
            if result and result.tactic_type == TacticType.ATTACK:
                total_non_alt += 1
            if result and result.tactic_type == TacticType.HOLD_POSITION:
                holds += 1
        assert holds > 10

    def test_high_aggressiveness_keeps_attack(self):
        ds = DifficultySystem(DifficultyLevel.VETERAN)
        bb = Blackboard()
        bb.set("health_ratio", 0.9)
        intent = TacticIntent(unit_id="u8", tactic_type=TacticType.ATTACK)
        rng = random.Random(456)
        attacks = 0
        total = 0
        for _ in range(500):
            result = ds.modify_ai_decision(intent, bb, rng=rng)
            if result:
                total += 1
                if result.tactic_type == TacticType.ATTACK:
                    attacks += 1
        assert attacks > 20


class TestModifyAIDecision_AmmoConservation:
    def test_low_ammo_skips_attack(self):
        ds = DifficultySystem(DifficultyLevel.EASY)
        bb = Blackboard()
        bb.set("ammo_ratio", 0.1)
        intent = TacticIntent(unit_id="u9", tactic_type=TacticType.ATTACK)
        rng = random.Random(77)
        skips = 0
        total = 0
        for _ in range(80):
            result = ds.modify_ai_decision(intent, bb, rng=rng)
            total += 1
            if result is None:
                skips += 1
        assert skips > total * 0.3

    def test_retreat_threshold_triggers_retreat(self):
        ds = DifficultySystem(DifficultyLevel.EASY)
        bb = Blackboard()
        bb.set("health_ratio", 0.25)
        intent = TacticIntent(unit_id="u10", tactic_type=TacticType.ATTACK)
        rng = random.Random(999)
        for _ in range(200):
            result = ds.modify_ai_decision(intent, bb, rng=rng)
            if result and result.tactic_type == TacticType.RETREAT:
                return
        raise AssertionError("Expected RETREAT after 200 attempts")


class TestShouldCoordinate:
    def test_easy_no_coordinate(self):
        assert DifficultySystem(DifficultyLevel.EASY).should_coordinate() is False

    def test_medium_no_coordinate(self):
        assert DifficultySystem(DifficultyLevel.MEDIUM).should_coordinate() is False

    def test_hard_coordinates(self):
        assert DifficultySystem(DifficultyLevel.HARD).should_coordinate() is True

    def test_veteran_coordinates(self):
        assert DifficultySystem(DifficultyLevel.VETERAN).should_coordinate() is True


class TestApplyCombatModifier:
    def test_easy_reduces_hit_chance(self):
        ds = DifficultySystem(DifficultyLevel.EASY)
        modified = ds.apply_combat_modifier(0.5)
        assert modified < 0.5

    def test_medium_preserves_hit_chance(self):
        ds = DifficultySystem(DifficultyLevel.MEDIUM)
        modified = ds.apply_combat_modifier(0.5)
        assert abs(modified - 0.5) < 0.01

    def test_hard_increases_hit_chance(self):
        ds = DifficultySystem(DifficultyLevel.HARD)
        modified = ds.apply_combat_modifier(0.5)
        assert modified > 0.5

    def test_clamped_range(self):
        ds = DifficultySystem(DifficultyLevel.VETERAN)
        low = ds.apply_combat_modifier(0.01)
        high = ds.apply_combat_modifier(2.0)
        assert 0.05 <= low <= 0.95
        assert 0.05 <= high <= 0.95


class TestSetLevel:
    def test_set_level_switches_config(self):
        ds = DifficultySystem(DifficultyLevel.MEDIUM)
        assert ds.level == DifficultyLevel.MEDIUM
        assert ds.config.base_hit_chance == 0.5
        ds.set_level(DifficultyLevel.HARD)
        assert ds.level == DifficultyLevel.HARD
        assert ds.config.base_hit_chance == 0.65

    def test_set_level_creates_independent_copy(self):
        ds = DifficultySystem(DifficultyLevel.HARD)
        original_id = id(ds.config)
        ds.set_level(DifficultyLevel.VETERAN)
        new_id = id(ds.config)
        assert original_id != new_id
