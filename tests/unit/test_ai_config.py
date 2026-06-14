
from pycc2.domain.ai.ai_config import AIConfig


class TestDefaultValues:
    """Verify all default values match the specification."""

    def test_threshold_defaults(self):
        cfg = AIConfig()
        assert cfg.retreat_force_ratio == 0.5
        assert cfg.cautious_force_ratio == 0.7
        assert cfg.low_morale_threshold == 30
        assert cfg.critical_morale_threshold == 15
        assert cfg.high_threat_distance == 8
        assert cfg.flank_min_units == 2

    def test_weight_defaults(self):
        cfg = AIConfig()
        assert cfg.threat_distance_weight == 0.4
        assert cfg.threat_type_weight == 0.3
        assert cfg.threat_health_weight == 0.3
        assert cfg.vl_capture_priority == 0.8
        assert cfg.vl_defend_priority == 0.6

    def test_timing_defaults(self):
        cfg = AIConfig()
        assert cfg.commander_tick_hz == 2
        assert cfg.squad_leader_tick_hz == 4
        assert cfg.unit_tick_hz == 8
        assert cfg.game_ticks_per_second == 30

    def test_behavior_defaults(self):
        cfg = AIConfig()
        assert cfg.suppression_persistence == 0.7
        assert cfg.flank_aggression == 0.6
        assert cfg.infantry_tank_coord_range == 10
        assert cfg.at_ambush_patience == 0.8
        assert cfg.retreat_cover_priority == 0.7


class TestValidate:
    """Validate method returns correct error lists."""

    def test_valid_config_returns_empty(self):
        cfg = AIConfig()
        assert cfg.validate() == []

    def test_weight_above_1(self):
        cfg = AIConfig(threat_distance_weight=1.5)
        errors = cfg.validate()
        assert any("threat_distance_weight" in e for e in errors)

    def test_weight_below_0(self):
        cfg = AIConfig(flank_aggression=-0.1)
        errors = cfg.validate()
        assert any("flank_aggression" in e for e in errors)

    def test_negative_threshold(self):
        cfg = AIConfig(low_morale_threshold=-5)
        errors = cfg.validate()
        assert any("low_morale_threshold" in e for e in errors)

    def test_zero_threshold(self):
        cfg = AIConfig(high_threat_distance=0)
        errors = cfg.validate()
        assert any("high_threat_distance" in e for e in errors)

    def test_zero_tick_hz(self):
        cfg = AIConfig(commander_tick_hz=0)
        errors = cfg.validate()
        assert any("commander_tick_hz" in e for e in errors)

    def test_negative_tick_hz(self):
        cfg = AIConfig(unit_tick_hz=-1)
        errors = cfg.validate()
        assert any("unit_tick_hz" in e for e in errors)

    def test_zero_game_ticks_per_second(self):
        cfg = AIConfig(game_ticks_per_second=0)
        errors = cfg.validate()
        assert any("game_ticks_per_second" in e for e in errors)

    def test_multiple_errors(self):
        cfg = AIConfig(
            threat_distance_weight=2.0,
            low_morale_threshold=-1,
            commander_tick_hz=0,
            game_ticks_per_second=-5,
        )
        errors = cfg.validate()
        assert len(errors) >= 4

    def test_weight_at_boundary_0(self):
        cfg = AIConfig(suppression_persistence=0.0)
        assert cfg.validate() == []

    def test_weight_at_boundary_1(self):
        cfg = AIConfig(suppression_persistence=1.0)
        assert cfg.validate() == []


class TestSerialization:
    """to_dict / from_dict round-trip and edge cases."""

    def test_to_dict_contains_all_fields(self):
        cfg = AIConfig()
        d = cfg.to_dict()
        from dataclasses import fields
        for f in fields(AIConfig):
            assert f.name in d

    def test_to_dict_values_match(self):
        cfg = AIConfig(retreat_force_ratio=0.3, commander_tick_hz=5)
        d = cfg.to_dict()
        assert d["retreat_force_ratio"] == 0.3
        assert d["commander_tick_hz"] == 5

    def test_from_dict_round_trip(self):
        original = AIConfig()
        restored = AIConfig.from_dict(original.to_dict())
        assert restored == original

    def test_from_dict_with_custom_values(self):
        data = {"retreat_force_ratio": 0.2, "flank_aggression": 0.9}
        cfg = AIConfig.from_dict(data)
        assert cfg.retreat_force_ratio == 0.2
        assert cfg.flank_aggression == 0.9
        # Non-specified fields should be defaults
        assert cfg.cautious_force_ratio == 0.7

    def test_from_dict_ignores_unknown_keys(self):
        data = {
            "retreat_force_ratio": 0.3,
            "unknown_key": 999,
            "another_fake": "hello",
        }
        cfg = AIConfig.from_dict(data)
        assert cfg.retreat_force_ratio == 0.3
        assert not hasattr(cfg, "unknown_key")


class TestPresetEasy:
    """PRESET_EASY should have lower values than NORMAL."""

    def test_lower_tick_hz(self):
        easy = AIConfig.PRESET_EASY()
        normal = AIConfig.PRESET_NORMAL()
        assert easy.commander_tick_hz < normal.commander_tick_hz
        assert easy.squad_leader_tick_hz < normal.squad_leader_tick_hz
        assert easy.unit_tick_hz < normal.unit_tick_hz

    def test_lower_aggression(self):
        easy = AIConfig.PRESET_EASY()
        normal = AIConfig.PRESET_NORMAL()
        assert easy.flank_aggression < normal.flank_aggression

    def test_lower_suppression_persistence(self):
        easy = AIConfig.PRESET_EASY()
        normal = AIConfig.PRESET_NORMAL()
        assert easy.suppression_persistence < normal.suppression_persistence

    def test_higher_retreat_threshold(self):
        easy = AIConfig.PRESET_EASY()
        normal = AIConfig.PRESET_NORMAL()
        assert easy.retreat_force_ratio > normal.retreat_force_ratio

    def test_valid_config(self):
        easy = AIConfig.PRESET_EASY()
        assert easy.validate() == []


class TestPresetHard:
    """PRESET_HARD should have higher values than NORMAL."""

    def test_higher_tick_hz(self):
        hard = AIConfig.PRESET_HARD()
        normal = AIConfig.PRESET_NORMAL()
        assert hard.commander_tick_hz > normal.commander_tick_hz
        assert hard.squad_leader_tick_hz > normal.squad_leader_tick_hz
        assert hard.unit_tick_hz > normal.unit_tick_hz

    def test_higher_aggression(self):
        hard = AIConfig.PRESET_HARD()
        normal = AIConfig.PRESET_NORMAL()
        assert hard.flank_aggression > normal.flank_aggression

    def test_higher_suppression_persistence(self):
        hard = AIConfig.PRESET_HARD()
        normal = AIConfig.PRESET_NORMAL()
        assert hard.suppression_persistence > normal.suppression_persistence

    def test_lower_retreat_threshold(self):
        hard = AIConfig.PRESET_HARD()
        normal = AIConfig.PRESET_NORMAL()
        assert hard.retreat_force_ratio < normal.retreat_force_ratio

    def test_valid_config(self):
        hard = AIConfig.PRESET_HARD()
        assert hard.validate() == []


class TestPresetVeteran:
    """PRESET_VETERAN should have the highest values."""

    def test_highest_tick_hz(self):
        veteran = AIConfig.PRESET_VETERAN()
        hard = AIConfig.PRESET_HARD()
        assert veteran.commander_tick_hz > hard.commander_tick_hz
        assert veteran.squad_leader_tick_hz > hard.squad_leader_tick_hz
        assert veteran.unit_tick_hz > hard.unit_tick_hz

    def test_highest_aggression(self):
        veteran = AIConfig.PRESET_VETERAN()
        hard = AIConfig.PRESET_HARD()
        assert veteran.flank_aggression > hard.flank_aggression

    def test_highest_suppression_persistence(self):
        veteran = AIConfig.PRESET_VETERAN()
        hard = AIConfig.PRESET_HARD()
        assert veteran.suppression_persistence > hard.suppression_persistence

    def test_smallest_retreat_threshold(self):
        veteran = AIConfig.PRESET_VETERAN()
        hard = AIConfig.PRESET_HARD()
        assert veteran.retreat_force_ratio < hard.retreat_force_ratio

    def test_valid_config(self):
        veteran = AIConfig.PRESET_VETERAN()
        assert veteran.validate() == []


class TestPresetProgression:
    """Verify monotonic progression across all presets."""

    def test_tick_hz_increases_with_difficulty(self):
        easy = AIConfig.PRESET_EASY()
        normal = AIConfig.PRESET_NORMAL()
        hard = AIConfig.PRESET_HARD()
        veteran = AIConfig.PRESET_VETERAN()
        assert easy.commander_tick_hz < normal.commander_tick_hz < hard.commander_tick_hz < veteran.commander_tick_hz

    def test_aggression_increases_with_difficulty(self):
        easy = AIConfig.PRESET_EASY()
        normal = AIConfig.PRESET_NORMAL()
        hard = AIConfig.PRESET_HARD()
        veteran = AIConfig.PRESET_VETERAN()
        assert easy.flank_aggression < normal.flank_aggression < hard.flank_aggression < veteran.flank_aggression

    def test_retreat_force_ratio_decreases_with_difficulty(self):
        easy = AIConfig.PRESET_EASY()
        normal = AIConfig.PRESET_NORMAL()
        hard = AIConfig.PRESET_HARD()
        veteran = AIConfig.PRESET_VETERAN()
        assert easy.retreat_force_ratio > normal.retreat_force_ratio > hard.retreat_force_ratio > veteran.retreat_force_ratio


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_from_dict_empty_dict(self):
        cfg = AIConfig.from_dict({})
        assert cfg == AIConfig()

    def test_presets_are_independent(self):
        """Each preset call returns a new independent instance."""
        a = AIConfig.PRESET_EASY()
        b = AIConfig.PRESET_EASY()
        assert a is not b
        a.retreat_force_ratio = 0.0
        assert b.retreat_force_ratio != 0.0

    def test_preset_normal_equals_default(self):
        normal = AIConfig.PRESET_NORMAL()
        default = AIConfig()
        assert normal == default

    def test_from_dict_preserves_all_types(self):
        original = AIConfig.PRESET_HARD()
        data = original.to_dict()
        restored = AIConfig.from_dict(data)
        assert type(restored.low_morale_threshold) is int
        assert type(restored.retreat_force_ratio) is float
        assert restored == original

    def test_validate_all_presets_are_valid(self):
        for preset_fn in (AIConfig.PRESET_EASY, AIConfig.PRESET_NORMAL, AIConfig.PRESET_HARD, AIConfig.PRESET_VETERAN):
            assert preset_fn().validate() == [], f"{preset_fn.__name__} has validation errors"
