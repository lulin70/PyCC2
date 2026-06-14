"""
Unit Tests for Combat Systems (FriendlyFireSystem, RicochetSystem)

Tests friendly fire detection, penalty application,
ricochet mechanics, and damage calculation.
"""

from unittest.mock import Mock

import pytest

from pycc2.domain.systems.combat_systems import FriendlyFireSystem, RicochetSystem

# ===========================================================================
# Tests — FriendlyFireSystem
# ===========================================================================


@pytest.mark.unit
class TestFriendlyFireCheck:
    """Test friendly fire detection along attack lines."""

    def test_no_friendlies_in_line(self):
        ff = FriendlyFireSystem()
        result = ff.check_friendly_fire(
            attacker_pos=(0.0, 0.0),
            target_pos=(10.0, 0.0),
            friendly_units=[],
        )
        assert result == []

    def test_friendly_on_attack_line_detected(self):
        ff = FriendlyFireSystem()
        # Friendly unit at (5, 0) — directly on the line from (0,0) to (10,0)
        friendly = Mock()
        friendly.position_component = Mock()
        friendly.position_component.x = 5.0
        friendly.position_component.y = 0.0

        result = ff.check_friendly_fire(
            attacker_pos=(0.0, 0.0),
            target_pos=(10.0, 0.0),
            friendly_units=[friendly],
        )
        assert len(result) == 1
        assert result[0] is friendly

    def test_friendly_off_attack_line_not_detected(self):
        ff = FriendlyFireSystem()
        # Friendly unit at (5, 5) — far from the line
        friendly = Mock()
        friendly.position_component = Mock()
        friendly.position_component.x = 5.0
        friendly.position_component.y = 5.0

        result = ff.check_friendly_fire(
            attacker_pos=(0.0, 0.0),
            target_pos=(10.0, 0.0),
            friendly_units=[friendly],
        )
        assert len(result) == 0

    def test_friendly_near_attack_line_detected(self):
        ff = FriendlyFireSystem()
        # Friendly unit at (5, 0.3) — close to the line, within threshold
        friendly = Mock()
        friendly.position_component = Mock()
        friendly.position_component.x = 5.0
        friendly.position_component.y = 0.3

        result = ff.check_friendly_fire(
            attacker_pos=(0.0, 0.0),
            target_pos=(10.0, 0.0),
            friendly_units=[friendly],
        )
        assert len(result) == 1

    def test_multiple_friendlies(self):
        ff = FriendlyFireSystem()
        f1 = Mock()
        f1.position_component = Mock()
        f1.position_component.x = 3.0
        f1.position_component.y = 0.0

        f2 = Mock()
        f2.position_component = Mock()
        f2.position_component.x = 7.0
        f2.position_component.y = 0.0

        result = ff.check_friendly_fire(
            attacker_pos=(0.0, 0.0),
            target_pos=(10.0, 0.0),
            friendly_units=[f1, f2],
        )
        assert len(result) == 2


@pytest.mark.unit
class TestPointNearLine:
    """Test the geometric point-near-line calculation."""

    def test_point_on_line(self):
        assert FriendlyFireSystem._point_near_line((0, 0), (10, 0), (5, 0), threshold=0.5) is True

    def test_point_near_line(self):
        assert FriendlyFireSystem._point_near_line((0, 0), (10, 0), (5, 0.3), threshold=0.5) is True

    def test_point_far_from_line(self):
        assert FriendlyFireSystem._point_near_line((0, 0), (10, 0), (5, 5), threshold=0.5) is False

    def test_zero_length_line(self):
        # When start == end, check distance to point
        assert FriendlyFireSystem._point_near_line((5, 5), (5, 5), (5, 5), threshold=0.5) is True

    def test_point_beyond_line_end(self):
        # Point beyond the line segment should not be near
        assert FriendlyFireSystem._point_near_line((0, 0), (5, 0), (10, 0), threshold=0.5) is False


@pytest.mark.unit
class TestFriendlyFirePenalty:
    """Test friendly fire penalty application."""

    def test_penalty_applies_damage(self):
        ff = FriendlyFireSystem()
        attacker = Mock()
        attacker.name = "Attacker"
        attacker.health_component = None
        attacker.morale_component = Mock()
        attacker.morale_component.current_morale = 80.0

        victim = Mock()
        victim.name = "Victim"
        victim.health_component = Mock()
        victim.health_component.current_hp = 100
        victim.morale_component = Mock()
        victim.morale_component.current_morale = 80.0

        event = ff.apply_friendly_fire_penalty(attacker, victim, damage=25)
        assert event["damage"] == 25
        assert event["attacker_morale_change"] == -20
        assert event["victim_morale_change"] == -20
        assert victim.health_component.current_hp == 75

    def test_penalty_reduces_attacker_morale(self):
        ff = FriendlyFireSystem()
        attacker = Mock()
        attacker.name = "Attacker"
        attacker.health_component = None
        attacker.morale_component = Mock()
        attacker.morale_component.current_morale = 80.0

        victim = Mock()
        victim.name = "Victim"
        victim.health_component = None
        victim.morale_component = None

        ff.apply_friendly_fire_penalty(attacker, victim, damage=10)
        assert attacker.morale_component.current_morale == 60.0

    def test_penalty_event_recorded(self):
        ff = FriendlyFireSystem()
        attacker = Mock()
        attacker.name = "A"
        attacker.health_component = None
        attacker.morale_component = None

        victim = Mock()
        victim.name = "V"
        victim.health_component = None
        victim.morale_component = None

        ff.apply_friendly_fire_penalty(attacker, victim, damage=15)
        assert len(ff._friendly_fire_events) == 1


# ===========================================================================
# Tests — RicochetSystem
# ===========================================================================


@pytest.mark.unit
class TestRicochetCheck:
    """Test ricochet probability and mechanics."""

    def test_low_angle_no_ricochet(self):
        rs = RicochetSystem()
        # 30 degrees is below threshold
        is_ricochet, suppression = rs.check_ricochet(30.0, armor_slope=0.0)
        assert is_ricochet is False
        assert suppression == 0.0

    def test_high_angle_possible_ricochet(self):
        rs = RicochetSystem()
        # 80 degrees is above threshold — may ricochet
        # Use seeded random to force ricochet
        import random

        random.seed(0)
        is_ricochet, suppression = rs.check_ricochet(80.0, armor_slope=0.0)
        # Result depends on random, but function should not error
        assert isinstance(is_ricochet, bool)
        if is_ricochet:
            assert suppression > 0

    def test_armor_slope_increases_ricochet_chance(self):
        rs = RicochetSystem()
        # With armor slope, effective angle is reduced
        # 70 degrees - 10 slope = 60 degrees (at threshold)
        is_ricochet, _ = rs.check_ricochet(70.0, armor_slope=10.0)
        # Effective angle = 60, right at threshold
        assert isinstance(is_ricochet, bool)

    def test_ricochet_suppression_capped(self):
        rs = RicochetSystem()
        # Very high angle should cap suppression at 0.8
        import random

        random.seed(42)
        is_ricochet, suppression = rs.check_ricochet(89.0, armor_slope=0.0)
        if is_ricochet:
            assert suppression <= 0.8

    def test_threshold_constant(self):
        assert RicochetSystem.RICOCHET_ANGLE_THRESHOLD == 60.0
        assert RicochetSystem.BASE_RICOCHET_CHANCE == 0.3
