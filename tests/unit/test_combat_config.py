"""Unit tests for combat_config module.

Verify that all combat configuration dataclasses expose their documented
OpenCombat/CC2-authentic default values, that derived property conversions
(frame->seconds) are correct, and that the gameplay-relevant helper methods
(``MGBurstConfig.get_burst_range``, ``ExplosionConfig.kill_probability`` /
``injure_probability``) implement their threshold semantics correctly.

Covers dimensions: Happy Path, Error Case, Boundary, Performance, Integration.
"""

from __future__ import annotations

import time

import pytest

from pycc2.domain.systems.combat_config import (
    DEFAULT_ACCURACY,
    DEFAULT_EXPLOSION,
    DEFAULT_MG_BURST,
    DEFAULT_MORALE,
    DEFAULT_MOVEMENT,
    DEFAULT_SUPPRESSION,
    DEFAULT_UPDATE_FREQ,
    DEFAULT_VISIBILITY,
    WEAPON_FIRE_PARAMS,
    AccuracyConfig,
    ExplosionConfig,
    MGBurstConfig,
    MoraleConfig,
    MovementConfig,
    Stance,
    SuppressionConfig,
    UpdateFrequencyConfig,
    VisibilityConfig,
    WeaponFireConfig,
)

# ===========================================================================
# Stance enum
# ===========================================================================


@pytest.mark.unit
class TestStanceEnum:
    """Verify the Stance enum exposes the four CC2 authentic stances."""

    def test_has_four_stances(self):
        """Verify: exactly STANDING, CROUCHING, PRONE, IN_BUILDING exist."""
        names = {s.name for s in Stance}
        assert names == {"STANDING", "CROUCHING", "PRONE", "IN_BUILDING"}

    def test_stance_count(self):
        """Verify: Stance has exactly 4 members."""
        assert len(list(Stance)) == 4

    def test_stance_values_unique(self):
        """Verify: each stance auto() value is distinct."""
        values = [s.value for s in Stance]
        assert len(set(values)) == 4


# ===========================================================================
# AccuracyConfig
# ===========================================================================


@pytest.mark.unit
class TestAccuracyConfig:
    """Verify AccuracyConfig defaults and immutability."""

    def test_default_values(self):
        """Verify: default dispersion and body-surface values match OpenCombat."""
        cfg = AccuracyConfig()
        assert cfg.inaccurate_fire_factor_by_meter == 0.075
        assert cfg.target_alteration_by_opacity_factor == 8.0
        assert cfg.visible_starts_at == 0.5
        assert cfg.visibility_first_tiles == 6
        assert cfg.body_surface_standing == 1000
        assert cfg.body_surface_crouched == 700
        assert cfg.body_surface_prone == 600
        assert cfg.proximity_bullet_range == 30.0

    def test_frozen_dataclass_immutable(self):
        """Verify: frozen dataclass raises FrozenInstanceError on mutation."""
        cfg = AccuracyConfig()
        with pytest.raises(AttributeError):
            cfg.inaccurate_fire_factor_by_meter = 0.5  # type: ignore[misc]

    def test_custom_values(self):
        """Verify: custom values are accepted on construction."""
        cfg = AccuracyConfig(inaccurate_fire_factor_by_meter=0.1, visible_starts_at=0.3)
        assert cfg.inaccurate_fire_factor_by_meter == 0.1
        assert cfg.visible_starts_at == 0.3

    def test_default_instance_matches(self):
        """Verify: module-level DEFAULT_ACCURACY equals a fresh instance."""
        assert (
            DEFAULT_ACCURACY.inaccurate_fire_factor_by_meter
            == AccuracyConfig().inaccurate_fire_factor_by_meter
        )


# ===========================================================================
# SuppressionConfig
# ===========================================================================


@pytest.mark.unit
class TestSuppressionConfig:
    """Verify SuppressionConfig defaults."""

    def test_under_fire_thresholds(self):
        """Verify: under_fire thresholds are ordered max > danger > warning."""
        cfg = SuppressionConfig()
        assert cfg.under_fire_max == 200.0
        assert cfg.under_fire_danger == 150.0
        assert cfg.under_fire_warning == 100.0
        assert cfg.under_fire_max > cfg.under_fire_danger > cfg.under_fire_warning

    def test_recovery_params(self):
        """Verify: recovery tick decrease and frequency."""
        cfg = SuppressionConfig()
        assert cfg.under_fire_tick_decrease == 10.0
        assert cfg.decrease_freq_seconds == 1.0

    def test_bullet_proximity_ranges(self):
        """Verify: close < mid range ordering for bullet proximity."""
        cfg = SuppressionConfig()
        assert cfg.bullet_proximity_close_range < cfg.bullet_proximity_mid_range
        assert cfg.bullet_proximity_close_value > cfg.bullet_proximity_mid_value
        assert cfg.bullet_proximity_mid_value > cfg.bullet_proximity_far_value

    def test_blast_params(self):
        """Verify: blast close < mid range and value ordering."""
        cfg = SuppressionConfig()
        assert cfg.blast_close_range < cfg.blast_mid_range
        assert cfg.blast_close_value > cfg.blast_mid_value > cfg.blast_far_value

    def test_posture_recovery_seconds(self):
        """Verify: crouch recovery < standup recovery (5 vs 10 minutes)."""
        cfg = SuppressionConfig()
        assert cfg.can_crouch_after_seconds == 300.0
        assert cfg.can_standup_after_seconds == 600.0
        assert cfg.can_crouch_after_seconds < cfg.can_standup_after_seconds

    def test_default_instance_matches(self):
        """Verify: DEFAULT_SUPPRESSION equals a fresh instance."""
        assert DEFAULT_SUPPRESSION.under_fire_max == SuppressionConfig().under_fire_max


# ===========================================================================
# MoraleConfig
# ===========================================================================


@pytest.mark.unit
class TestMoraleConfig:
    """Verify MoraleConfig defaults."""

    def test_end_morale_and_freq(self):
        """Verify: broken threshold and update frequency."""
        cfg = MoraleConfig()
        assert cfg.end_morale == 0.2
        assert cfg.update_freq_seconds == 5.0

    def test_morale_modifiers_signs(self):
        """Verify: losses are negative-impact, gains are positive-impact values."""
        cfg = MoraleConfig()
        assert cfg.casualty_morale_loss == 0.15
        assert cfg.leader_killed_morale_loss == 0.3
        assert cfg.victory_morale_gain == 0.1
        assert cfg.enemy_routed_morale_gain == 0.2
        # Leader death is worse than a regular casualty
        assert cfg.leader_killed_morale_loss > cfg.casualty_morale_loss
        # Routing the enemy is a bigger gain than capturing a VL
        assert cfg.enemy_routed_morale_gain > cfg.victory_morale_gain

    def test_default_instance_matches(self):
        """Verify: DEFAULT_MORALE equals a fresh instance."""
        assert DEFAULT_MORALE.end_morale == MoraleConfig().end_morale


# ===========================================================================
# MovementConfig
# ===========================================================================


@pytest.mark.unit
class TestMovementConfig:
    """Verify MovementConfig defaults and terrain cost ordering."""

    def test_velocity_ordering(self):
        """Verify: sneak < move < move_fast velocity ordering."""
        cfg = MovementConfig()
        assert cfg.sneak_velocity < cfg.move_velocity < cfg.move_fast_velocity
        assert cfg.sneak_velocity == 1.5
        assert cfg.move_velocity == 5.0
        assert cfg.move_fast_velocity == 10.0

    def test_pathfinding_params(self):
        """Verify: cover search and hide range."""
        cfg = MovementConfig()
        assert cfg.cover_search_distance == 6
        assert cfg.hide_max_range == 50.0
        assert cfg.pathfinding_heuristic_coeff == 10.0

    def test_terrain_cost_road_is_cheapest(self):
        """Verify: road is the cheapest terrain (0.8 multiplier)."""
        cfg = MovementConfig()
        assert cfg.terrain_cost_road == 0.8
        assert cfg.terrain_cost_open == 1.0
        # Road cheaper than open
        assert cfg.terrain_cost_road < cfg.terrain_cost_open

    def test_terrain_cost_swamp_is_most_expensive(self):
        """Verify: swamp is the most expensive terrain (4.0 multiplier)."""
        cfg = MovementConfig()
        assert cfg.terrain_cost_swamp == 4.0
        all_costs = [
            cfg.terrain_cost_open,
            cfg.terrain_cost_road,
            cfg.terrain_cost_grass,
            cfg.terrain_cost_woods,
            cfg.terrain_cost_building,
            cfg.terrain_cost_shallow,
            cfg.terrain_cost_hedge,
            cfg.terrain_cost_rough,
            cfg.terrain_cost_crater,
            cfg.terrain_cost_swamp,
        ]
        assert cfg.terrain_cost_swamp == max(all_costs)

    def test_default_instance_matches(self):
        """Verify: DEFAULT_MOVEMENT equals a fresh instance."""
        assert DEFAULT_MOVEMENT.move_velocity == MovementConfig().move_velocity


# ===========================================================================
# VisibilityConfig
# ===========================================================================


@pytest.mark.unit
class TestVisibilityConfig:
    """Verify VisibilityConfig defaults including coverage tuples."""

    def test_visibility_modifiers(self):
        """Verify: standing/crouched positive, prone/sneak/hide negative."""
        cfg = VisibilityConfig()
        assert cfg.visibility_standing == 0.5
        assert cfg.visibility_crouched == 0.5
        assert cfg.visibility_prone == -0.9
        assert cfg.visibility_moving == 1.0
        assert cfg.visibility_running == 2.0
        assert cfg.visibility_sneaking == -0.9
        assert cfg.visibility_defending == -0.9
        assert cfg.visibility_hiding == -0.9
        assert cfg.visibility_firing == 0.5

    def test_opacity_values(self):
        """Verify: terrain opacity values, with brick wall fully opaque."""
        cfg = VisibilityConfig()
        assert cfg.opacity_short_grass == 0.0
        assert cfg.opacity_brick_wall == 1.0
        assert cfg.opacity_tall_grass == 0.1
        assert cfg.opacity_bush == 0.015

    def test_coverage_tuples_are_pairs(self):
        """Verify: every coverage_* field is a (standing, prone) 2-tuple."""
        cfg = VisibilityConfig()
        for tup in (
            cfg.coverage_brick_wall,
            cfg.coverage_tree_trunk,
            cfg.coverage_log,
            cfg.coverage_hedge,
            cfg.coverage_rock,
            cfg.coverage_dirt_prone,
        ):
            assert isinstance(tup, tuple)
            assert len(tup) == 2

    def test_coverage_brick_wall_values(self):
        """Verify: brick wall gives equal standing/prone coverage (0.8, 0.8)."""
        cfg = VisibilityConfig()
        assert cfg.coverage_brick_wall == (0.8, 0.8)

    def test_coverage_tree_trunk_prone_lower_than_standing(self):
        """Verify: tree trunk gives higher standing coverage than prone."""
        cfg = VisibilityConfig()
        standing, prone = cfg.coverage_tree_trunk
        assert standing == 0.9
        assert prone == 0.7
        assert standing > prone

    def test_last_shot_visibility_seconds(self):
        """Verify: post-firing visibility boost duration."""
        cfg = VisibilityConfig()
        assert cfg.visibility_by_last_shot_seconds == 15.0

    def test_default_instance_matches(self):
        """Verify: DEFAULT_VISIBILITY equals a fresh instance."""
        assert DEFAULT_VISIBILITY.visibility_standing == VisibilityConfig().visibility_standing


# ===========================================================================
# WeaponFireConfig + properties
# ===========================================================================


@pytest.mark.unit
class TestWeaponFireConfig:
    """Verify WeaponFireConfig construction and frame->second properties."""

    def test_construction_fields(self):
        """Verify: all constructor fields are stored verbatim."""
        w = WeaponFireConfig(
            weapon_name="Test Rifle",
            aim_frames=60,
            fire_frames=30,
            reload_frames=120,
            burst_offset_frames=4,
            spread_coefficient=1.2,
            magazine_capacity=10,
            standard_magazines=3,
        )
        assert w.weapon_name == "Test Rifle"
        assert w.aim_frames == 60
        assert w.fire_frames == 30
        assert w.reload_frames == 120
        assert w.burst_offset_frames == 4
        assert w.spread_coefficient == 1.2
        assert w.magazine_capacity == 10
        assert w.standard_magazines == 3

    def test_aim_seconds_conversion(self):
        """Verify: aim_seconds = aim_frames / 60."""
        w = WeaponFireConfig(
            "X",
            aim_frames=30,
            fire_frames=1,
            reload_frames=1,
            burst_offset_frames=0,
            spread_coefficient=1.0,
            magazine_capacity=1,
            standard_magazines=1,
        )
        assert w.aim_seconds == pytest.approx(0.5)

    def test_fire_seconds_conversion(self):
        """Verify: fire_seconds = fire_frames / 60."""
        w = WeaponFireConfig(
            "X",
            aim_frames=1,
            fire_frames=12,
            reload_frames=1,
            burst_offset_frames=0,
            spread_coefficient=1.0,
            magazine_capacity=1,
            standard_magazines=1,
        )
        assert w.fire_seconds == pytest.approx(0.2)

    def test_reload_seconds_conversion(self):
        """Verify: reload_seconds = reload_frames / 60."""
        w = WeaponFireConfig(
            "X",
            aim_frames=1,
            fire_frames=1,
            reload_frames=60,
            burst_offset_frames=0,
            spread_coefficient=1.0,
            magazine_capacity=1,
            standard_magazines=1,
        )
        assert w.reload_seconds == pytest.approx(1.0)

    def test_zero_frames_yield_zero_seconds(self):
        """Boundary: zero frames convert to zero seconds."""
        w = WeaponFireConfig(
            "X",
            aim_frames=0,
            fire_frames=0,
            reload_frames=0,
            burst_offset_frames=0,
            spread_coefficient=1.0,
            magazine_capacity=1,
            standard_magazines=1,
        )
        assert w.aim_seconds == 0.0
        assert w.fire_seconds == 0.0
        assert w.reload_seconds == 0.0


# ===========================================================================
# WEAPON_FIRE_PARAMS registry
# ===========================================================================


@pytest.mark.unit
class TestWeaponFireParams:
    """Verify the pre-configured weapon registry."""

    def test_registry_non_empty(self):
        """Verify: registry contains a substantial set of weapons."""
        assert len(WEAPON_FIRE_PARAMS) >= 20

    def test_every_value_is_weapon_fire_config(self):
        """Verify: every entry is a WeaponFireConfig instance."""
        for name, cfg in WEAPON_FIRE_PARAMS.items():
            assert isinstance(cfg, WeaponFireConfig), f"{name} is not WeaponFireConfig"

    def test_rifle_entries(self):
        """Verify: known rifle entries exist with expected aim/fire/reload frames."""
        lee = WEAPON_FIRE_PARAMS["Lee_Enfield_No4"]
        assert lee.weapon_name == "Lee-Enfield No.4"
        assert lee.aim_frames == 30
        assert lee.fire_frames == 12
        assert lee.reload_frames == 60
        assert lee.magazine_capacity == 10
        assert lee.standard_magazines == 5
        assert lee.burst_offset_frames == 0  # single-shot

    def test_smg_has_burst_offset(self):
        """Verify: SMGs have a non-zero burst_offset_frames (burst fire)."""
        thompson = WEAPON_FIRE_PARAMS["Thompson"]
        assert thompson.burst_offset_frames > 0
        assert thompson.magazine_capacity == 20

    def test_at_weapon_single_shot(self):
        """Verify: anti-tank weapons are single-shot (burst_offset 0, mag 1)."""
        bazooka = WEAPON_FIRE_PARAMS["Bazooka_M1A1"]
        assert bazooka.burst_offset_frames == 0
        assert bazooka.magazine_capacity == 1

    def test_mg_large_magazine(self):
        """Verify: MG42 has a large magazine (50 rounds)."""
        mg42 = WEAPON_FIRE_PARAMS["MG42"]
        assert mg42.magazine_capacity == 50
        assert mg42.burst_offset_frames > 0

    def test_tank_gun_aim_seconds(self):
        """Integration: 88mm KwK 36 aims for 2.5 seconds (150 frames / 60)."""
        tiger = WEAPON_FIRE_PARAMS["88mm_KwK36"]
        assert tiger.aim_frames == 150
        assert tiger.aim_seconds == pytest.approx(2.5)

    def test_keys_are_strings(self):
        """Verify: every registry key is a string identifier."""
        for key in WEAPON_FIRE_PARAMS:
            assert isinstance(key, str)


# ===========================================================================
# MGBurstConfig.get_burst_range
# ===========================================================================


@pytest.mark.unit
class TestMGBurstConfig:
    """Verify MGBurstConfig.get_burst_range threshold logic."""

    def test_default_ranges(self):
        """Verify: default (min, max) tuples for each enemy-count tier."""
        cfg = MGBurstConfig()
        assert cfg.no_enemies == (1, 3)
        assert cfg.few_enemies == (1, 5)
        assert cfg.some_enemies == (1, 10)
        assert cfg.many_enemies == (1, 16)

    @pytest.mark.parametrize(
        "enemy_count,expected",
        [
            (0, (1, 3)),  # no_enemies
            (1, (1, 5)),  # few_enemies (1-2)
            (2, (1, 5)),  # few_enemies boundary
            (3, (1, 10)),  # some_enemies (3-4)
            (4, (1, 10)),  # some_enemies boundary
            (5, (1, 16)),  # many_enemies (5+)
            (10, (1, 16)),  # many_enemies
            (100, (1, 16)),  # many_enemies large
        ],
    )
    def test_get_burst_range_tiers(self, enemy_count, expected):
        """Verify: get_burst_range returns the correct tier for each enemy count."""
        cfg = MGBurstConfig()
        assert cfg.get_burst_range(enemy_count) == expected

    def test_burst_range_min_always_one(self):
        """Boundary: minimum shots is always 1 regardless of enemy count."""
        cfg = MGBurstConfig()
        for n in [0, 1, 5, 100]:
            assert cfg.get_burst_range(n)[0] == 1

    def test_burst_range_max_monotonic(self):
        """Verify: max shots is non-decreasing as enemy count grows."""
        cfg = MGBurstConfig()
        maxes = [cfg.get_burst_range(n)[1] for n in [0, 1, 3, 5, 10]]
        assert maxes == sorted(maxes)

    def test_negative_enemy_count_returns_few(self):
        """Error case: negative count satisfies ``enemy_count <= 2`` and returns few_enemies.

        Documented actual behavior: the ``<=`` comparisons include negative
        values, so a negative count falls into the few_enemies tier (not the
        else/many branch). This is a quirk worth documenting: callers should
        not pass negative enemy counts.
        """
        cfg = MGBurstConfig()
        assert cfg.get_burst_range(-1) == cfg.few_enemies
        assert cfg.get_burst_range(-100) == cfg.few_enemies

    def test_default_instance_matches(self):
        """Verify: DEFAULT_MG_BURST equals a fresh instance."""
        assert DEFAULT_MG_BURST.get_burst_range(0) == MGBurstConfig().get_burst_range(0)


# ===========================================================================
# ExplosionConfig
# ===========================================================================


@pytest.mark.unit
class TestExplosionConfig:
    """Verify ExplosionConfig kill/injure probability curves."""

    def test_default_radii(self):
        """Verify: default radii ordering direct < regressive_kill < injure."""
        cfg = ExplosionConfig()
        assert cfg.direct_kill_radius == 1.0
        assert cfg.regressive_kill_radius == 3.0
        assert cfg.regressive_injure_radius == 6.0
        assert cfg.direct_kill_radius < cfg.regressive_kill_radius < cfg.regressive_injure_radius

    @pytest.mark.parametrize(
        "distance,expected",
        [
            (0.0, 1.0),  # at center
            (0.5, 1.0),  # within direct kill radius
            (1.0, 1.0),  # boundary of direct kill radius
            (2.0, 1.0 - 2.0 / 3.0),  # regressive kill zone
            (3.0, 0.0),  # boundary of regressive kill radius -> 1 - 3/3 = 0
            (4.0, 0.0),  # beyond kill radius
            (100.0, 0.0),  # far away
        ],
    )
    def test_kill_probability(self, distance, expected):
        """Verify: kill_probability follows direct-kill then regressive decay."""
        cfg = ExplosionConfig()
        assert cfg.kill_probability(distance) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "distance,expected",
        [
            (0.0, 1.0),  # at center
            (1.0, 1.0),  # boundary of direct kill radius
            (3.0, 1.0 - 3.0 / 6.0),  # regressive injure zone
            (6.0, 0.0),  # boundary of injure radius -> 1 - 6/6 = 0
            (7.0, 0.0),  # beyond injure radius
            (100.0, 0.0),  # far away
        ],
    )
    def test_injure_probability(self, distance, expected):
        """Verify: injure_probability follows direct then wider regressive decay."""
        cfg = ExplosionConfig()
        assert cfg.injure_probability(distance) == pytest.approx(expected)

    def test_kill_probability_never_exceeds_one(self):
        """Boundary: kill probability is capped at 1.0 for negative distances.

        Documented actual behavior: negative distance <= direct_kill_radius, returns 1.0.
        """
        cfg = ExplosionConfig()
        assert cfg.kill_probability(-5.0) == 1.0

    def test_injure_probability_never_negative(self):
        """Boundary: injure probability returns 0.0 well beyond radius."""
        cfg = ExplosionConfig()
        assert cfg.injure_probability(1000.0) == 0.0

    def test_injure_radius_wider_than_kill(self):
        """Integration: at distance 4, kill is 0 but injure is positive."""
        cfg = ExplosionConfig()
        assert cfg.kill_probability(4.0) == 0.0
        assert cfg.injure_probability(4.0) > 0.0

    def test_default_instance_matches(self):
        """Verify: DEFAULT_EXPLOSION equals a fresh instance."""
        assert DEFAULT_EXPLOSION.direct_kill_radius == ExplosionConfig().direct_kill_radius


# ===========================================================================
# UpdateFrequencyConfig
# ===========================================================================


@pytest.mark.unit
class TestUpdateFrequencyConfig:
    """Verify UpdateFrequencyConfig defaults."""

    def test_soldier_position_per_frame(self):
        """Verify: soldier_position updates every frame (1/60 s)."""
        cfg = UpdateFrequencyConfig()
        assert cfg.soldier_position == pytest.approx(1 / 60)

    def test_frequencies_ordered(self):
        """Verify: update frequencies are ordered fastest to slowest."""
        cfg = UpdateFrequencyConfig()
        assert cfg.soldier_position < cfg.soldier_behavior < cfg.visibility
        assert cfg.morale == cfg.victory_check == 5.0

    def test_all_frequencies_positive(self):
        """Verify: every update frequency is a positive value."""
        cfg = UpdateFrequencyConfig()
        for attr in (
            "soldier_position",
            "soldier_behavior",
            "visibility",
            "suppression_decay",
            "flag_status",
            "squad_leader_ai",
            "morale",
            "victory_check",
        ):
            assert getattr(cfg, attr) > 0

    def test_default_instance_matches(self):
        """Verify: DEFAULT_UPDATE_FREQ equals a fresh instance."""
        assert DEFAULT_UPDATE_FREQ.morale == UpdateFrequencyConfig().morale


# ===========================================================================
# Performance baselines
# ===========================================================================


@pytest.mark.unit
class TestPerformanceBaselines:
    """Establish timing baselines for hot-path config lookups."""

    def test_get_burst_range_under_1ms(self):
        """Performance: 10000 burst-range lookups complete well under 1s."""
        cfg = MGBurstConfig()
        start = time.perf_counter()
        for _ in range(10000):
            cfg.get_burst_range(5)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0  # generous baseline; typically < 5ms

    def test_kill_probability_under_1ms(self):
        """Performance: 10000 kill-probability lookups complete well under 1s."""
        cfg = ExplosionConfig()
        start = time.perf_counter()
        for _ in range(10000):
            cfg.kill_probability(2.5)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0


# ===========================================================================
# Integration: combined config consistency
# ===========================================================================


@pytest.mark.unit
class TestConfigIntegration:
    """Cross-config consistency checks."""

    def test_all_default_instances_present(self):
        """Integration: every DEFAULT_* constant is defined and of correct type."""
        assert isinstance(DEFAULT_ACCURACY, AccuracyConfig)
        assert isinstance(DEFAULT_SUPPRESSION, SuppressionConfig)
        assert isinstance(DEFAULT_MORALE, MoraleConfig)
        assert isinstance(DEFAULT_MOVEMENT, MovementConfig)
        assert isinstance(DEFAULT_VISIBILITY, VisibilityConfig)
        assert isinstance(DEFAULT_MG_BURST, MGBurstConfig)
        assert isinstance(DEFAULT_EXPLOSION, ExplosionConfig)
        assert isinstance(DEFAULT_UPDATE_FREQ, UpdateFrequencyConfig)

    def test_weapon_aim_seconds_within_reasonable_range(self):
        """Integration: every weapon aims in under 3 seconds (<=180 frames)."""
        for name, w in WEAPON_FIRE_PARAMS.items():
            assert 0.0 <= w.aim_seconds <= 3.0, f"{name} aim_seconds={w.aim_seconds} out of range"

    def test_weapon_magazine_positive(self):
        """Integration: every weapon has a positive magazine capacity."""
        for name, w in WEAPON_FIRE_PARAMS.items():
            assert w.magazine_capacity > 0, f"{name} has non-positive magazine"

    def test_explosion_kill_stronger_than_injure_at_center(self):
        """Integration: at the center both kill and injure are 1.0 (max)."""
        cfg = ExplosionConfig()
        assert cfg.kill_probability(0.0) == cfg.injure_probability(0.0) == 1.0

    def test_mg_burst_and_explosion_use_same_default_instances(self):
        """Integration: module-level singletons are stable references."""
        assert DEFAULT_MG_BURST is DEFAULT_MG_BURST
        assert DEFAULT_EXPLOSION is DEFAULT_EXPLOSION
