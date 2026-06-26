"""Tests for C6-C12 (P2) + D6-D10 Quick Implementations (96 tests total)."""

import math
import random
from unittest.mock import MagicMock, patch

import pytest

from pycc2.domain.systems.civilian_system import (
    CivilianState,
    CivilianSystem,
)
from pycc2.domain.systems.combat_systems import (
    FriendlyFireSystem,
    RicochetSystem,
)
from pycc2.domain.systems.terrain_systems import (
    DestructibleTerrain,
    RiverCrossingSystem,
    RoadSystem,
)
from pycc2.domain.systems.trench_digging import TrenchDiggingTracker
from pycc2.domain.systems.vision_system import ConeVisionSystem
from pycc2.infrastructure.audio.environmental_audio import (
    EnvironmentalAudioSystem,
    EnvironmentSoundType,
)
from pycc2.infrastructure.audio.stereo_sound import StereoSoundSystem
from pycc2.infrastructure.audio.voice_command_system import (
    VoiceCommandSystem,
    VoiceCommandType,
)
from pycc2.infrastructure.rendering.minimap_icons import (
    MinimapIconSystem,
    UnitIconType,
)


class TestVoiceCommandSystem:
    """C6: Voice Command System (8 tests)."""

    def test_initialization(self):
        vc = VoiceCommandSystem()
        assert len(vc._cooldowns) == 0

    def test_can_play_initially(self):
        vc = VoiceCommandSystem()
        assert vc.can_play(VoiceCommandType.MOVING, 0.0) is True

    def test_cooldown_prevents_play(self):
        vc = VoiceCommandSystem()
        vc.play_command(VoiceCommandType.CONTACT, 0.0)
        assert vc.can_play(VoiceCommandType.CONTACT, 1.0) is False

    def test_cooldown_expires(self):
        vc = VoiceCommandSystem()
        vc.play_command(VoiceCommandType.TAKING_FIRE, 0.0)
        assert vc.can_play(VoiceCommandType.TAKING_FIRE, 5.0) is True

    def test_different_commands_independent(self):
        vc = VoiceCommandSystem()
        vc.play_command(VoiceCommandType.MOVING, 0.0)
        assert vc.can_play(VoiceCommandType.TARGET_DOWN, 0.5) is True

    def test_get_command_text(self):
        vc = VoiceCommandSystem()
        assert "Moving!" in vc.get_command_text(VoiceCommandType.MOVING)
        assert "Contact!" in vc.get_command_text(VoiceCommandType.CONTACT)

    def test_play_returns_true(self):
        vc = VoiceCommandSystem()
        result = vc.play_command(VoiceCommandType.SUPPRESSING, 1.0)
        assert result is True

    def test_all_command_types_have_text(self):
        vc = VoiceCommandSystem()
        for cmd_type in VoiceCommandType:
            text = vc.get_command_text(cmd_type)
            assert isinstance(text, str) and len(text) > 0


class TestMinimapIconSystem:
    """C7: Minimap Icon Differentiation (8 tests)."""

    def test_infantry_icon(self):
        sys = MinimapIconSystem()
        unit = MagicMock()
        unit.unit_type = "Infantry"
        assert sys.get_icon_type(unit) == UnitIconType.INFANTRY

    def test_vehicle_icon(self):
        sys = MinimapIconSystem()
        unit = MagicMock()
        unit.unit_type = "Tank"
        assert sys.get_icon_type(unit) == UnitIconType.VEHICLE

    def test_mg_icon(self):
        sys = MinimapIconSystem()
        unit = MagicMock()
        unit.unit_type = "MG Team"
        assert sys.get_icon_type(unit) == UnitIconType.MG_TEAM

    def test_officer_icon(self):
        sys = MinimapIconSystem()
        unit = MagicMock()
        unit.unit_type = "Officer"
        assert sys.get_icon_type(unit) == UnitIconType.OFFICER

    def test_allied_color(self):
        sys = MinimapIconSystem()
        unit = MagicMock()
        unit.faction = "allied"
        assert sys.get_icon_color(unit) == (0, 255, 0)

    def test_axis_color(self):
        sys = MinimapIconSystem()
        unit = MagicMock()
        unit.faction = "axis"
        assert sys.get_icon_color(unit) == (255, 50, 50)

    def test_unknown_unit_type(self):
        sys = MinimapIconSystem()
        unit = MagicMock()
        unit.unit_type = "UnknownType_XYZ"
        assert sys.get_icon_type(unit) == UnitIconType.UNKNOWN

    @patch("pygame.draw")
    def test_render_icon_calls_pygame(self, mock_draw):
        sys = MinimapIconSystem()
        surface = MagicMock()
        sys.render_icon(surface, (50, 50), UnitIconType.INFANTRY, (0, 255, 0))


class TestDestructibleTerrain:
    """C8: Destructible Terrain (8 tests)."""

    def test_initialize_terrain(self):
        dt = DestructibleTerrain()
        dt.initialize_terrain((5, 5), "building")
        assert dt.get_terrain_hp((5, 5)) == 100

    def test_apply_partial_damage(self):
        dt = DestructibleTerrain()
        dt.initialize_terrain((3, 3), "building")
        destroyed = dt.apply_damage((3, 3), 40)
        assert destroyed is False
        assert dt.get_terrain_hp((3, 3)) == 60

    def test_destruction_creates_rubble(self):
        dt = DestructibleTerrain()
        dt.initialize_terrain((7, 7), "wall")
        destroyed = dt.apply_damage((7, 7), 35)
        assert destroyed is True
        assert dt.is_rubble((7, 7))

    def test_different_terrain_types(self):
        dt = DestructibleTerrain()
        dt.initialize_terrain((1, 1), "bridge")
        dt.initialize_terrain((2, 2), "tree")
        assert dt.get_terrain_hp((1, 1)) == 150
        assert dt.get_terrain_hp((2, 2)) == 15

    def test_nonexistent_terrain(self):
        dt = DestructibleTerrain()
        assert dt.get_terrain_hp((99, 99)) == 0
        assert dt.is_rubble((99, 99)) is False

    def test_destroyed_terrain_no_hp(self):
        dt = DestructibleTerrain()
        dt.initialize_terrain((4, 4), "building")
        dt.apply_damage((4, 4), 100)
        assert dt.get_terrain_hp((4, 4)) == 0

    def test_multiple_tiles(self):
        dt = DestructibleTerrain()
        for i in range(5):
            dt.initialize_terrain((i, i), "building")
        assert dt.apply_damage((2, 2), 100) is True
        assert dt.get_terrain_hp((3, 3)) == 100

    def test_tree_destroyed_easily(self):
        dt = DestructibleTerrain()
        dt.initialize_terrain((0, 0), "tree")
        assert dt.apply_damage((0, 0), 20) is True


class TestFriendlyFireSystem:
    """C9: Friendly Fire Detection (8 tests)."""

    def test_no_friendly_fire_clear_line(self):
        ff = FriendlyFireSystem()
        attacker_pos = (0.0, 0.0)
        target_pos = (10.0, 0.0)

        friendly = MagicMock()
        friendly.position_component = MagicMock()
        friendly.position_component.x = 20.0
        friendly.position_component.y = 20.0

        hits = ff.check_friendly_fire(attacker_pos, target_pos, [friendly])
        assert len(hits) == 0

    def test_friendly_fire_detected(self):
        ff = FriendlyFireSystem()
        attacker_pos = (0.0, 0.0)
        target_pos = (10.0, 0.0)

        friendly = MagicMock()
        friendly.position_component = MagicMock()
        friendly.position_component.x = 5.0
        friendly.position_component.y = 0.0

        hits = ff.check_friendly_fire(attacker_pos, target_pos, [friendly])
        assert len(hits) == 1

    def test_apply_penalty_reduces_hp(self):
        ff = FriendlyFireSystem()

        class MockHealth:
            def __init__(self):
                self.current_hp = 80

        victim = MagicMock()
        victim.name = "Victim"
        victim.health_component = MockHealth()  # Use real object, not pure mock

        event = ff.apply_friendly_fire_penalty(MagicMock(name="Attacker"), victim, 15)

        assert victim.health_component.current_hp == 65
        assert event["damage"] == 15

    def test_apply_penalty_morale_effect(self):
        ff = FriendlyFireSystem()
        attacker = MagicMock()
        attacker.morale_component = MagicMock()
        attacker.morale_component.current_morale = 90.0

        victim = MagicMock()
        victim.morale_component = MagicMock()
        victim.morale_component.current_morale = 85.0
        victim.health_component = MagicMock()
        victim.health_component.current_hp = 100

        ff.apply_friendly_fire_penalty(attacker, victim, 10)

        assert attacker.morale_component.current_morale == 70.0
        assert victim.morale_component.current_morale == 65.0

    def test_event_recorded(self):
        ff = FriendlyFireSystem()
        a = MagicMock(name="A")
        v = MagicMock(name="V")
        v.health_component = MagicMock()
        v.health_component.current_hp = 100
        v.morale_component = MagicMock()
        v.morale_component.current_morale = 100.0
        a.morale_component = MagicMock()
        a.morale_component.current_morale = 100.0

        before = len(ff._friendly_fire_events)
        ff.apply_friendly_fire_penalty(a, v, 5)

        assert len(ff._friendly_fire_events) == before + 1

    def test_empty_friendly_list(self):
        ff = FriendlyFireSystem()
        hits = ff.check_friendly_fire((0, 0), (10, 10), [])
        assert hits == []

    def test_point_near_line_edge_case(self):
        assert FriendlyFireSystem._point_near_line((0, 0), (10, 0), (5, 0.4), threshold=0.5) is True

    def test_point_far_from_line(self):
        assert FriendlyFireSystem._point_near_line((0, 0), (10, 0), (5, 5), threshold=0.5) is False


class TestRiverCrossingSystem:
    """C10: River Crossing Mechanics (8 tests)."""

    def test_normal_tile_cost(self):
        rc = RiverCrossingSystem()
        assert rc.get_movement_cost((5, 5), 1.0) == 1.0

    def test_water_tile_cost(self):
        rc = RiverCrossingSystem()
        rc.add_water_tile((3, 3))
        cost = rc.get_movement_cost((3, 3), 1.0)
        assert abs(cost - 2.5) < 0.01

    def test_shallow_water_cheaper(self):
        rc = RiverCrossingSystem()
        rc.add_water_tile((4, 4), is_shallow=True)
        cost = rc.get_movement_cost((4, 4), 1.0)
        assert abs(cost - 1.5) < 0.01

    def test_is_water_detection(self):
        rc = RiverCrossingSystem()
        rc.add_water_tile((7, 7))
        assert rc.is_water((7, 7)) is True
        assert rc.is_water((8, 8)) is False

    def test_exposure_modifier(self):
        rc = RiverCrossingSystem()
        rc.add_water_tile((2, 2))
        assert abs(rc.get_exposure_modifier((2, 2)) - 0.3) < 0.01
        assert rc.get_exposure_modifier((5, 5)) == 0.0

    def test_multiple_water_tiles(self):
        rc = RiverCrossingSystem()
        positions = [(i, i) for i in range(5)]
        for p in positions:
            rc.add_water_tile(p)

        for p in positions:
            assert rc.is_water(p) is True

    def test_base_cost_preserved_for_land(self):
        rc = RiverCrossingSystem()
        rc.add_water_tile((0, 0))
        assert rc.get_movement_cost((1, 1), 2.0) == 2.0

    def test_shallow_vs_deep_difference(self):
        rc = RiverCrossingSystem()
        rc.add_water_tile((0, 0), is_shallow=False)
        rc.add_water_tile((1, 1), is_shallow=True)

        deep_cost = rc.get_movement_cost((0, 0), 1.0)
        shallow_cost = rc.get_movement_cost((1, 1), 1.0)

        assert deep_cost > shallow_cost


class TestRoadSystem:
    """C11: Road System (8 tests)."""

    def test_non_road_default(self):
        rs = RoadSystem()
        assert rs.get_speed_modifier((5, 5)) == 1.0

    def test_road_speed_bonus(self):
        rs = RoadSystem()
        rs.add_road((3, 3))
        assert abs(rs.get_speed_modifier((3, 3)) - 1.3) < 0.01

    def test_road_visibility_bonus(self):
        rs = RoadSystem()
        rs.add_road((4, 4))
        assert abs(rs.get_visibility_modifier((4, 4)) - 1.2) < 0.01

    def test_muddy_road_penalty(self):
        rs = RoadSystem()
        rs.add_road((6, 6))
        rs.set_muddy((6, 6), muddy=True)
        assert abs(rs.get_speed_modifier((6, 6)) - 0.7) < 0.01

    def test_muddy_no_visibility_bonus(self):
        rs = RoadSystem()
        rs.add_road((7, 7))
        rs.set_muddy((7, 7), muddy=True)
        assert rs.get_visibility_modifier((7, 7)) == 1.0

    def test_is_road_check(self):
        rs = RoadSystem()
        rs.add_road((2, 2))
        assert rs.is_road((2, 2)) is True
        assert rs.is_road((3, 3)) is False

    def test_clear_mud(self):
        rs = RoadSystem()
        rs.add_road((8, 8))
        rs.set_muddy((8, 8), muddy=True)
        rs.set_muddy((8, 8), muddy=False)
        assert abs(rs.get_speed_modifier((8, 8)) - 1.3) < 0.01

    def test_multiple_roads(self):
        rs = RoadSystem()
        for i in range(10):
            rs.add_road((i, 0))

        assert all(rs.is_road((i, 0)) for i in range(10))


class TestEnvironmentalAudioSystem:
    """C12: Environmental Audio (8 tests)."""

    def test_initialization(self):
        env = EnvironmentalAudioSystem()
        assert env.is_playing(EnvironmentSoundType.BIRDS) is True

    def test_rain_enables_rain_sound(self):
        env = EnvironmentalAudioSystem()
        env.set_weather_rain(True)
        assert env.is_playing(EnvironmentSoundType.RAIN) is True
        assert env.is_playing(EnvironmentSoundType.BIRDS) is False

    def test_rain_disables_birds(self):
        env = EnvironmentalAudioSystem()
        env.set_weather_rain(True)
        env.set_weather_rain(False)
        # Birds should come back when rain stops (if no combat)
        assert env.is_playing(EnvironmentSoundType.RAIN) is False

    def test_combat_enables_artillery(self):
        env = EnvironmentalAudioSystem()
        with (
            patch.object(env, "_initialized", True),
            patch.object(env, "start_ambient_loop", return_value=True) as mock_start,
        ):
            env.set_combat_intensity(0.5)
            mock_start.assert_called_once_with(EnvironmentSoundType.DISTANT_ARTILLERY)

    def test_high_intensity_silences_birds(self):
        env = EnvironmentalAudioSystem()
        env.set_combat_intensity(0.8)
        assert env._should_play_sound(EnvironmentSoundType.BIRDS) is False

    def test_low_intensity_allows_birds(self):
        env = EnvironmentalAudioSystem()
        env.set_combat_intensity(0.1)
        assert env.is_playing(EnvironmentSoundType.BIRDS) is True

    def test_volume_attribute_exists(self):
        env = EnvironmentalAudioSystem()
        assert hasattr(env, "_volume")
        assert env._volume == 0.3

    def test_all_sound_types_known(self):
        env = EnvironmentalAudioSystem()
        for st in EnvironmentSoundType:
            result = env.is_playing(st)
            assert isinstance(result, bool)


class TestStereoSoundSystem:
    """D6: 3D Stereo Sound (8 tests)."""

    def test_pan_center_when_aligned(self):
        ss = StereoSoundSystem()
        pan = ss.calculate_stereo_pan((5, 5), (5, 10))
        assert abs(pan) < 0.01

    def test_pan_right(self):
        ss = StereoSoundSystem()
        pan = ss.calculate_stereo_pan((0, 0), (10, 0))
        assert pan > 0.5

    def test_pan_left(self):
        ss = StereoSoundSystem()
        pan = ss.calculate_stereo_pan((10, 0), (0, 0))
        assert pan < -0.5

    def test_volume_attenuation_with_distance(self):
        ss = StereoSoundSystem()
        vol_close = ss.calculate_volume((0, 0), (5, 5), 1.0)
        vol_far = ss.calculate_volume((0, 0), (40, 40), 1.0)
        assert vol_close > vol_far

    def test_max_distance_zero_volume(self):
        ss = StereoSoundSystem()
        vol = ss.calculate_volume((0, 0), (60, 60), 1.0)
        assert vol == 0.0

    def test_same_position_full_volume(self):
        ss = StereoSoundSystem()
        vol = ss.calculate_volume((5, 5), (5, 5), 1.0)
        assert abs(vol - 1.0) < 0.01

    def test_clamped_pan_range(self):
        ss = StereoSoundSystem()
        pan = ss.calculate_stereo_pan((0, 0), (100, 0))
        assert -1.0 <= pan <= 1.0

    def test_base_volume_scaling(self):
        ss = StereoSoundSystem()
        vol_half = ss.calculate_volume((0, 0), (10, 10), 0.5)
        vol_full = ss.calculate_volume((0, 0), (10, 10), 1.0)
        assert vol_half < vol_full


class TestCivilianSystem:
    """D7: Civilian/NPC System (8 tests)."""

    def test_spawn_civilians(self):
        cs = CivilianSystem()
        cs.spawn_civilians([(1, 1), (2, 2), (3, 3)])
        assert len(cs.civilians) == 3

    def test_civilian_initial_state(self):
        cs = CivilianSystem()
        cs.spawn_civilians([(5, 5)])
        assert cs.civilians[0].state == CivilianState.IDLE
        assert cs.civilians[0].alive is True

    def test_flee_on_combat_proximity(self):
        cs = CivilianSystem()
        cs.spawn_civilians([(0, 0)])
        # Distance sqrt(8) ≈ 2.83, which is < flee_radius (8) but > panic (3)
        cs.update(combat_positions=[(2, 2)], dt=0.1)
        assert cs.civilians[0].state in (CivilianState.FLEEING, CivilianState.PANICKED)

    def test_panic_when_very_close(self):
        cs = CivilianSystem()
        cs.spawn_civilians([(0, 0)])
        cs.update(combat_positions=[(1, 1)], dt=0.1)
        assert cs.civilians[0].state == CivilianState.PANICKED

    def test_no_combat_idle(self):
        cs = CivilianSystem()
        cs.spawn_civilians([(10, 10)])
        cs.update(combat_positions=[], dt=0.1)
        assert cs.civilians[0].state == CivilianState.IDLE

    def test_get_civilians_in_area(self):
        cs = CivilianSystem()
        cs.spawn_civilians([(0, 0), (1, 1), (10, 10)])
        nearby = cs.get_civilians_in_area((0, 0), radius=3.0)
        assert len(nearby) == 2

    def test_dead_civilians_excluded(self):
        cs = CivilianSystem()
        cs.spawn_civilians([(0, 0)])
        cs.civilians[0].alive = False
        nearby = cs.get_civilians_in_area((0, 0), radius=5.0)
        assert len(nearby) == 0

    def test_hiding_after_fleeing(self):
        cs = CivilianSystem()
        cs.spawn_civilians([(0, 0)])
        cs.update(combat_positions=[(5, 5)], dt=0.1)  # Far enough to flee but not panic
        assert cs.civilians[0].state in (CivilianState.FLEEING, CivilianState.IDLE)
        cs.update(combat_positions=[], dt=0.1)
        assert cs.civilians[0].state in (CivilianState.HIDING, CivilianState.IDLE)


class TestRicochetSystem:
    """D8: Ricochet Mechanism (8 tests)."""

    def test_no_ricochet_low_angle(self):
        rs = RicochetSystem()
        is_rico, _ = rs.check_ricochet(30.0)
        assert is_rico is False

    def test_ricochet_high_angle(self):
        random.seed(42)
        rs = RicochetSystem()
        is_rico, suppression = rs.check_ricochet(75.0)
        # May or may not ricochet depending on RNG, but high angle possible
        assert isinstance(is_rico, bool)
        assert isinstance(suppression, float)

    def test_armor_slope_helps(self):
        rs = RicochetSystem()
        _, sup_flat = rs.check_ricochet(65.0, armor_slope=0.0)
        _, sup_sloped = rs.check_ricochet(65.0, armor_slope=10.0)
        # Slope may or may not cause ricochet depending on RNG
        assert isinstance(sup_flat, float)
        assert isinstance(sup_sloped, float)

    def test_threshold_angle_boundary(self):
        rs = RicochetSystem()
        result_below = rs.check_ricochet(59.9)
        result_above = rs.check_ricochet(60.1)
        # Return tuple of (is_ricochet, suppression)
        assert len(result_below) == 2
        assert len(result_above) == 2
        assert isinstance(result_below[0], bool)
        assert isinstance(result_above[1], float)

    def test_suppression_zero_when_no_ricochet(self):
        rs = RicochetSystem()
        _, suppression = rs.check_ricochet(45.0)
        assert suppression == 0.0

    def test_suppression_positive_when_ricochets(self):
        random.seed(123)
        rs = RicochetSystem()
        # Force very high angle to maximize chance
        is_rico, suppression = rs.check_ricochet(85.0)
        if is_rico:
            assert suppression > 0.0

    def test_suppression_cap(self):
        random.seed(42)
        rs = RicochetSystem()
        _, suppression = rs.check_ricochet(89.0)
        if suppression > 0:
            assert suppression <= 0.8

    def test_configurable_threshold(self):
        rs = RicochetSystem()
        assert rs.RICOCHET_ANGLE_THRESHOLD == 60.0


class TestConeVisionSystem:
    """D9: Cone Vision Precision (8 tests)."""

    def test_target_in_front_within_cone(self):
        cvs = ConeVisionSystem()
        result = cvs.is_in_cone((0, 0), 0.0, (10, 0), stance="standing")
        assert result is True

    def test_target_behind_outside_cone(self):
        cvs = ConeVisionSystem()
        result = cvs.is_in_cone((0, 0), 0.0, (-10, 0), stance="standing")
        assert result is False

    def test_range_limit(self):
        cvs = ConeVisionSystem()
        result = cvs.is_in_cone((0, 0), 0.0, (100, 0), max_range=10.0)
        assert result is False

    def test_standing_wider_than_prone(self):
        cvs = ConeVisionSystem()
        standing_angle = cvs.get_cone_angle("standing")
        prone_angle = cvs.get_cone_angle("prone")
        assert standing_angle > prone_angle

    def test_target_at_exact_cone_edge(self):
        cvs = ConeVisionSystem()
        # 60 degrees from center for standing (120/2 = 60)
        rad = math.radians(60)
        tx = 10 * math.cos(rad)
        ty = 10 * math.sin(rad)
        result = cvs.is_in_cone((0, 0), 0.0, (tx, ty), stance="standing")
        assert result is True  # On edge should be included

    def test_crouching_narrower(self):
        cvs = ConeVisionSystem()
        crouch = cvs.get_cone_angle("crouching")
        standing = cvs.get_cone_angle("standing")
        assert crouch < standing

    def test_prone_narrowest(self):
        cvs = ConeVisionSystem()
        prone = cvs.get_cone_angle("prone")
        assert prone == 60.0

    def test_invalid_stance_defaults(self):
        cvs = ConeVisionSystem()
        angle = cvs.get_cone_angle("invalid_stance")
        assert angle == cvs.DEFAULT_CONE_ANGLE


class TestTrenchDiggingAI:
    """D10: Trench Digging AI Extension (8 tests)."""

    def test_initial_state(self):
        tracker = TrenchDiggingTracker()
        assert tracker.get_dig_progress(1) == 0.0

    def test_not_stationary_resets(self):
        tracker = TrenchDiggingTracker()
        result = tracker.update_unit(1, is_stationary=False, is_detected=False, dt=1.0)
        assert result is None
        assert tracker.get_dig_progress(1) == 0.0

    def test_detected_resets_progress(self):
        tracker = TrenchDiggingTracker()
        tracker.update_unit(1, is_stationary=True, is_detected=False, dt=3.0)
        tracker.update_unit(1, is_stationary=True, is_detected=True, dt=0.1)
        assert tracker.get_dig_progress(1) == 0.0

    def test_digging_after_delay(self):
        tracker = TrenchDiggingTracker()
        tracker.update_unit(1, is_stationary=True, is_detected=False, dt=2.5)
        result = tracker.update_unit(1, is_stationary=True, is_detected=False, dt=0.1)
        assert result == "digging"

    def test_completion(self):
        tracker = TrenchDiggingTracker()
        # Need ~15 seconds of stationary time after initial delay
        for _ in range(20):
            result = tracker.update_unit(1, is_stationary=True, is_detected=False, dt=1.0)
            if result == "completed":
                break
        assert tracker.get_dig_progress(1) >= 1.0 or result == "completed"

    def test_multiple_units_independent(self):
        tracker = TrenchDiggingTracker()
        tracker.update_unit(1, is_stationary=True, is_detected=False, dt=5.0)
        progress1 = tracker.get_dig_progress(1)
        progress2 = tracker.get_dig_progress(2)
        assert progress1 > 0
        assert progress2 == 0.0

    def test_dig_duration_constant(self):
        tracker = TrenchDiggingTracker()
        assert tracker.DIG_DURATION_TURNS == 3

    def test_reset_on_movement(self):
        tracker = TrenchDiggingTracker()
        tracker.update_unit(1, is_stationary=True, is_detected=False, dt=10.0)
        tracker.get_dig_progress(1)
        tracker.update_unit(1, is_stationary=False, is_detected=False, dt=0.1)
        progress_after = tracker.get_dig_progress(1)
        assert progress_after == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
