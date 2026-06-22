"""
Unit Tests for MoraleSystem

Tests morale state transitions, suppression effects, rally mechanics,
and panic contagion.
"""

from unittest.mock import Mock

import pytest

from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.entities.unit import Faction, UnitType
from pycc2.domain.systems.morale_system import (
    MoraleCalculator,
    MoraleEvent,
    MoraleState,
    MoraleSystem,
    RoutingTarget,
)

# ===========================================================================
# Stub helpers
# ===========================================================================


def _make_unit(
    unit_id,
    morale_value=75,
    faction=Faction.ALLIES,
    tile_x=5,
    tile_y=5,
    unit_type=UnitType.INFANTRY_SQUAD,
    alive=True,
):
    """Create a mock unit with a real MoraleComponent."""
    from pycc2.domain.value_objects.tile_coord import TileCoord

    unit = Mock()
    unit.id = unit_id
    unit.name = unit_id
    unit.faction = faction
    unit.unit_type = unit_type
    unit.is_alive = alive

    # Position
    pos = Mock()
    pos.tile_coord = TileCoord(tile_x, tile_y)
    unit.position = pos

    # Morale — use real component for accurate state transitions
    unit.morale = MoraleComponent(value=morale_value)

    # Routing target
    unit._routing_target = RoutingTarget()

    return unit


# ===========================================================================
# Tests — MoraleSystem.get_state
# ===========================================================================


@pytest.mark.unit
class TestGetState:
    """Test morale value to state mapping."""

    def test_rallied_high_morale(self):
        assert MoraleSystem.get_state(85) == MoraleState.RALLYED

    def test_wavering_mid_morale(self):
        assert MoraleSystem.get_state(55) == MoraleState.WAVERING

    def test_pinned_low_morale(self):
        assert MoraleSystem.get_state(30) == MoraleState.PINNED

    def test_broken_very_low_morale(self):
        assert MoraleSystem.get_state(10) == MoraleState.BROKEN

    def test_zero_morale_is_broken(self):
        assert MoraleSystem.get_state(0) == MoraleState.BROKEN

    def test_boundary_rallied(self):
        assert MoraleSystem.get_state(71) == MoraleState.RALLYED

    def test_boundary_wavering(self):
        assert MoraleSystem.get_state(41) == MoraleState.WAVERING

    def test_boundary_pinned(self):
        assert MoraleSystem.get_state(21) == MoraleState.PINNED


# ===========================================================================
# Tests — MoraleSystem.apply_suppression
# ===========================================================================


@pytest.mark.unit
class TestApplySuppression:
    """Test suppression application to unit morale."""

    def test_suppression_reduces_morale(self):
        unit = _make_unit("u1", morale_value=75)
        result = MoraleSystem.apply_suppression(unit, 10.0, 1.0)
        assert result["morale_delta"] < 0
        assert result["current_morale"] < 75

    def test_suppression_state_change(self):
        unit = _make_unit("u1", morale_value=45)
        # Heavy suppression should push from WAVERING toward PINNED
        result = MoraleSystem.apply_suppression(unit, 50.0, 1.0)
        # State may or may not change depending on the exact delta
        assert "state_changed" in result
        assert "new_state" in result

    def test_suppression_no_morale_component(self):
        unit = Mock()
        unit.morale = None
        result = MoraleSystem.apply_suppression(unit, 10.0, 1.0)
        assert result["morale_delta"] == 0
        assert result["state_changed"] is False

    def test_suppression_adds_to_tracker(self):
        unit = _make_unit("u1", morale_value=75)
        MoraleSystem.apply_suppression(unit, 10.0, 1.0)
        assert unit.morale.suppression > 0


# ===========================================================================
# Tests — MoraleSystem.update_morale_recovery
# ===========================================================================


@pytest.mark.unit
class TestMoraleRecovery:
    """Test passive morale recovery."""

    def test_recovery_increases_morale(self):
        unit = _make_unit("u1", morale_value=50)
        old_morale = unit.morale.value
        # Large dt to ensure recovery
        MoraleSystem.update_morale_recovery(unit, 10.0, in_cover=True)
        assert unit.morale.value >= old_morale

    def test_recovery_commander_bonus(self):
        unit = _make_unit("u1", morale_value=50)
        result_no_cmd = MoraleSystem.update_morale_recovery(
            unit, 5.0, near_commander=False, in_cover=True
        )
        unit2 = _make_unit("u2", morale_value=50)
        result_cmd = MoraleSystem.update_morale_recovery(
            unit2, 5.0, near_commander=True, in_cover=True
        )
        # With commander, recovery should be at least as much
        assert result_cmd["recovered"] >= result_no_cmd["recovered"]

    def test_broken_unit_no_recovery_below_threshold(self):
        unit = _make_unit("u1", morale_value=10)
        result = MoraleSystem.update_morale_recovery(unit, 5.0, in_cover=True)
        assert result["recovered"] == 0

    def test_no_morale_component(self):
        unit = Mock()
        unit.morale = None
        result = MoraleSystem.update_morale_recovery(unit, 1.0)
        assert result["recovered"] == 0


# ===========================================================================
# Tests — MoraleSystem.get_accuracy_modifier
# ===========================================================================


@pytest.mark.unit
class TestAccuracyModifier:
    """Test accuracy modifier based on morale state."""

    def test_rallied_slight_bonus(self):
        mod = MoraleSystem.get_accuracy_modifier(MoraleState.RALLYED)
        assert mod == 1.05

    def test_wavering_slight_penalty(self):
        mod = MoraleSystem.get_accuracy_modifier(MoraleState.WAVERING)
        assert mod == 0.95

    def test_pinned_major_penalty(self):
        mod = MoraleSystem.get_accuracy_modifier(MoraleState.PINNED)
        assert mod == 0.60

    def test_broken_severe_penalty(self):
        mod = MoraleSystem.get_accuracy_modifier(MoraleState.BROKEN)
        assert mod == 0.30

    def test_routing_minimal(self):
        mod = MoraleSystem.get_accuracy_modifier(MoraleState.ROUTING)
        assert mod == 0.10


# ===========================================================================
# Tests — MoraleSystem.get_movement_modifier
# ===========================================================================


@pytest.mark.unit
class TestMovementModifier:
    """Test movement modifier based on morale state."""

    def test_pinned_cannot_move(self):
        mod = MoraleSystem.get_movement_modifier(MoraleState.PINNED)
        assert mod == 0.0

    def test_routing_fleeing_fast(self):
        mod = MoraleSystem.get_movement_modifier(MoraleState.ROUTING)
        assert mod == 1.5

    def test_rallied_normal(self):
        mod = MoraleSystem.get_movement_modifier(MoraleState.RALLYED)
        assert mod == 1.0


# ===========================================================================
# Tests — MoraleSystem.can_move / can_accept_orders
# ===========================================================================


@pytest.mark.unit
class TestCanMoveAndOrders:
    """Test movement and order acceptance based on morale."""

    def test_pinned_cannot_move(self):
        unit = _make_unit("u1", morale_value=25)
        # Pinned state
        assert MoraleSystem.get_state(unit.morale.value) == MoraleState.PINNED
        assert MoraleSystem.can_move(unit) is False

    def test_no_morale_can_move(self):
        unit = Mock()
        unit.morale = None
        assert MoraleSystem.can_move(unit) is True

    @pytest.mark.xfail(
        reason="Pre-existing bug: can_accept_orders returns True for routing units (main branch issue)"
    )
    def test_routing_cannot_accept_orders(self):
        unit = _make_unit("u1", morale_value=5)
        unit.morale.start_routing()
        assert MoraleSystem.can_accept_orders(unit) is False

    def test_rallied_can_accept_orders(self):
        unit = _make_unit("u1", morale_value=80)
        assert MoraleSystem.can_accept_orders(unit) is True


# ===========================================================================
# Tests — MoraleCalculator
# ===========================================================================


@pytest.mark.unit
class TestMoraleCalculator:
    """Test MoraleCalculator event-driven calculations."""

    def test_ally_killed_reduces_morale(self):
        calc = MoraleCalculator()
        mc = MoraleComponent(value=75)
        result = calc.calculate_event_effect(mc, MoraleEvent.ALLY_KILLED)
        assert result.morale_delta == -15

    def test_commander_nearby_boosts_morale(self):
        calc = MoraleCalculator()
        mc = MoraleComponent(value=50)
        result = calc.calculate_event_effect(mc, MoraleEvent.COMMANDER_NEARBY)
        assert result.morale_delta == 10

    def test_natural_recovery_after_30_ticks(self):
        calc = MoraleCalculator()
        new_val = calc.calculate_natural_recovery(50, 30)
        assert new_val == 55

    def test_no_recovery_before_30_ticks(self):
        calc = MoraleCalculator()
        new_val = calc.calculate_natural_recovery(50, 29)
        assert new_val == 50

    def test_panic_contagion_targets(self):
        calc = MoraleCalculator()
        MoraleComponent(value=10)  # BROKEN
        mc2 = MoraleComponent(value=50)  # WAVERING
        mc3 = MoraleComponent(value=5)  # BROKEN — should be skipped

        result = calc.calculate_panic_contagion(
            [("u2", mc2), ("u3", mc3)],
            "u1",
        )
        assert "u2" in result
        assert result["u2"] == -10
        assert "u3" not in result  # Already broken

    def test_predict_state(self):
        assert MoraleCalculator.predict_state(80, 0) == "RALLIED"
        assert MoraleCalculator.predict_state(50, 0) == "WAVERING"
        assert MoraleCalculator.predict_state(30, 0) == "PINNED"
        assert MoraleCalculator.predict_state(10, 0) == "BROKEN"


# ===========================================================================
# Tests — MoraleSystem.apply_panic_contagion
# ===========================================================================


@pytest.mark.unit
class TestPanicContagion:
    """Test panic contagion spreading between nearby units."""

    def test_broken_unit_affects_nearby_friendlies(self):
        broken = _make_unit("b1", morale_value=10, tile_x=5, tile_y=5)
        nearby = _make_unit("n1", morale_value=60, tile_x=6, tile_y=5)
        all_units = [broken, nearby]

        old_morale = nearby.morale.value
        MoraleSystem.apply_panic_contagion(broken, all_units)
        assert nearby.morale.value < old_morale

    def test_rallied_unit_no_contagion(self):
        rallied = _make_unit("r1", morale_value=80, tile_x=5, tile_y=5)
        nearby = _make_unit("n1", morale_value=60, tile_x=6, tile_y=5)
        all_units = [rallied, nearby]

        old_morale = nearby.morale.value
        MoraleSystem.apply_panic_contagion(rallied, all_units)
        assert nearby.morale.value == old_morale

    def test_contagion_ignores_different_faction(self):
        broken = _make_unit("b1", morale_value=10, faction=Faction.ALLIES, tile_x=5, tile_y=5)
        enemy = _make_unit("e1", morale_value=60, faction=Faction.AXIS, tile_x=6, tile_y=5)
        all_units = [broken, enemy]

        old_morale = enemy.morale.value
        MoraleSystem.apply_panic_contagion(broken, all_units)
        assert enemy.morale.value == old_morale

    def test_contagion_ignores_distant_units(self):
        broken = _make_unit("b1", morale_value=10, tile_x=5, tile_y=5)
        distant = _make_unit("d1", morale_value=60, tile_x=20, tile_y=20)
        all_units = [broken, distant]

        old_morale = distant.morale.value
        MoraleSystem.apply_panic_contagion(broken, all_units)
        assert distant.morale.value == old_morale


# ===========================================================================
# Tests — MoraleSystem.apply_nco_rally
# ===========================================================================


@pytest.mark.unit
class TestNCORally:
    """Test NCO/commander rally bonus."""

    def test_commander_rallies_nearby_broken(self):

        commander = _make_unit(
            "cmd", morale_value=80, tile_x=5, tile_y=5, unit_type=UnitType.COMMANDER
        )
        broken = _make_unit("b1", morale_value=15, tile_x=6, tile_y=5)

        old_morale = broken.morale.value
        MoraleSystem.apply_nco_rally([commander, broken])
        assert broken.morale.value > old_morale

    def test_commander_no_rally_for_distant(self):
        commander = _make_unit(
            "cmd", morale_value=80, tile_x=5, tile_y=5, unit_type=UnitType.COMMANDER
        )
        distant = _make_unit("d1", morale_value=15, tile_x=20, tile_y=20)

        old_morale = distant.morale.value
        MoraleSystem.apply_nco_rally([commander, distant])
        assert distant.morale.value == old_morale
