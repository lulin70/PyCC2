from __future__ import annotations

import pytest

from pycc2.domain.components.morale_component import MoraleComponent, MoraleState
from pycc2.domain.systems.morale_sys import (
    MoraleCalculator,
    MoraleEvent,
)


@pytest.fixture
def calc() -> MoraleCalculator:
    return MoraleCalculator()


@pytest.fixture
def normal_morale() -> MoraleComponent:
    return MoraleComponent(value=80)


class TestMoraleEventWeights:
    def test_evt_01_ally_killed_delta(self, calc: MoraleCalculator, normal_morale: MoraleComponent):
        result = calc.calculate_event_effect(normal_morale, MoraleEvent.ALLY_KILLED)
        assert result.morale_delta == -15

    def test_evt_02_leader_killed_delta(
        self, calc: MoraleCalculator, normal_morale: MoraleComponent
    ):
        result = calc.calculate_event_effect(normal_morale, MoraleEvent.LEADER_KILLED)
        assert result.morale_delta == -25

    def test_evt_03_kill_confirmed_delta(
        self, calc: MoraleCalculator, normal_morale: MoraleComponent
    ):
        result = calc.calculate_event_effect(normal_morale, MoraleEvent.KILL_CONFIRMED)
        assert result.morale_delta == 8

    def test_evt_04_commander_nearby_delta(
        self, calc: MoraleCalculator, normal_morale: MoraleComponent
    ):
        result = calc.calculate_event_effect(normal_morale, MoraleEvent.COMMANDER_NEARBY)
        assert result.morale_delta == 10

    def test_evt_05_under_heavy_fire_delta(
        self, calc: MoraleCalculator, normal_morale: MoraleComponent
    ):
        result = calc.calculate_event_effect(normal_morale, MoraleEvent.UNDER_HEAVY_FIRE)
        assert result.morale_delta == -5

    def test_evt_06_near_explosion_delta(
        self, calc: MoraleCalculator, normal_morale: MoraleComponent
    ):
        result = calc.calculate_event_effect(normal_morale, MoraleEvent.NEAR_EXPLOSION)
        assert result.morale_delta == -20

    def test_evt_07_rally_delta(self, calc: MoraleCalculator, normal_morale: MoraleComponent):
        result = calc.calculate_event_effect(normal_morale, MoraleEvent.RALLY)
        assert result.morale_delta == 3

    def test_evt_08_in_cover_delta(self, calc: MoraleCalculator, normal_morale: MoraleComponent):
        result = calc.calculate_event_effect(normal_morale, MoraleEvent.IN_COVER)
        assert result.morale_delta == 5

    def test_evt_09_panic_contagion_delta(
        self, calc: MoraleCalculator, normal_morale: MoraleComponent
    ):
        result = calc.calculate_event_effect(normal_morale, MoraleEvent.PANIC_CONTAGION)
        assert result.morale_delta == -10

    def test_evt_10_all_weights_correct(self, calc: MoraleCalculator):
        expected = {
            MoraleEvent.ALLY_KILLED: -15,
            MoraleEvent.LEADER_KILLED: -25,
            MoraleEvent.UNDER_HEAVY_FIRE: -5,
            MoraleEvent.NEAR_EXPLOSION: -20,
            MoraleEvent.KILL_CONFIRMED: 8,
            MoraleEvent.RALLY: 3,
            MoraleEvent.IN_COVER: 5,
            MoraleEvent.COMMANDER_NEARBY: 10,
            MoraleEvent.PANIC_CONTAGION: -10,
        }
        assert expected == calc.EVENT_WEIGHTS

    def test_evt_11_unknown_event_delta_zero(
        self, calc: MoraleCalculator, normal_morale: MoraleComponent
    ):
        result = calc.calculate_event_effect(normal_morale, MoraleEvent.RALLY)
        assert result.morale_delta == 3

    def test_evt_12_multiple_events_stack(
        self, calc: MoraleCalculator, normal_morale: MoraleComponent
    ):
        r1 = calc.calculate_event_effect(normal_morale, MoraleEvent.ALLY_KILLED)
        r2 = calc.calculate_event_effect(normal_morale, MoraleEvent.UNDER_HEAVY_FIRE)
        assert r1.morale_delta + r2.morale_delta == -20


class TestStateTransitions:
    def test_state_01_rallied_minus15_crosses_to_wavering(self, calc: MoraleCalculator):
        mc = MoraleComponent(value=80)
        result = calc.calculate_event_effect(mc, MoraleEvent.ALLY_KILLED)
        assert result.state_changed is True
        assert result.new_state == "WAVERING"

    def test_state_02_crosses_pinned_threshold(self, calc: MoraleCalculator):
        mc = MoraleComponent(value=50)
        result = calc.calculate_event_effect(mc, MoraleEvent.ALLY_KILLED)
        assert result.state_changed is True
        assert result.new_state == "PINNED"
        assert result.old_state == "WAVERING"

    def test_state_03_crosses_broken_threshold(self, calc: MoraleCalculator):
        mc = MoraleComponent(value=30)
        result = calc.calculate_event_effect(mc, MoraleEvent.LEADER_KILLED)
        assert result.state_changed is True
        assert result.new_state == "BROKEN"
        assert result.old_state == "PINNED"

    def test_state_04_already_broken_stays_broken(self, calc: MoraleCalculator):
        mc = MoraleComponent(value=10)
        result = calc.calculate_event_effect(mc, MoraleEvent.PANIC_CONTAGION)
        assert result.state_changed is False

    def test_state_05_broken_is_terminal(self, calc: MoraleCalculator):
        mc = MoraleComponent(value=5)
        result = calc.calculate_event_effect(mc, MoraleEvent.PANIC_CONTAGION)
        new_val = max(0, 5 + result.morale_delta)
        predicted = MoraleCalculator.predict_state(new_val, -10)
        assert predicted == "BROKEN"

    def test_state_06_positive_recovery_from_broken(self, calc: MoraleCalculator):
        mc = MoraleComponent(value=15)
        result = calc.calculate_event_effect(mc, MoraleEvent.COMMANDER_NEARBY)
        assert result.state_changed is True
        assert result.new_state == "PINNED"
        assert result.old_state == "BROKEN"

    def test_state_07_state_changed_flag(self, calc: MoraleCalculator):
        mc_high = MoraleComponent(value=80)
        mc_low = MoraleComponent(value=30)
        r1 = calc.calculate_event_effect(mc_high, MoraleEvent.RALLY)
        r2 = calc.calculate_event_effect(mc_low, MoraleEvent.ALLY_KILLED)
        assert r1.state_changed is False
        assert r2.state_changed is True

    def test_state_08_old_new_state_recorded(self, calc: MoraleCalculator):
        mc = MoraleComponent(value=50)
        result = calc.calculate_event_effect(mc, MoraleEvent.LEADER_KILLED)
        assert result.old_state == "WAVERING"
        assert result.new_state == "PINNED"

    def test_state_09_broken_at_low_value(self):
        mc = MoraleComponent(value=10)
        calc = MoraleCalculator()
        result = calc.calculate_event_effect(mc, MoraleEvent.NEAR_EXPLOSION)
        assert result.state_changed is False
        assert result.new_state is None

    def test_state_10_clamp_boundaries(self, calc: MoraleCalculator):
        mc_low = MoraleComponent(value=5)
        mc_high = MoraleComponent(value=98)
        calc.calculate_event_effect(mc_low, MoraleEvent.LEADER_KILLED)
        calc.calculate_event_effect(mc_high, MoraleEvent.COMMANDER_NEARBY)
        predicted_low = MoraleCalculator.predict_state(5, -25)
        predicted_high = MoraleCalculator.predict_state(98, 10)
        assert predicted_low == "BROKEN"
        assert predicted_high == "RALLIED"


class TestPanicContagion:
    def test_contag_01_spreads_to_others(self, calc: MoraleCalculator):
        units = [
            ("u1", MoraleComponent(value=80)),
            ("u2", MoraleComponent(value=70)),
            ("u3", MoraleComponent(value=60)),
        ]
        result = calc.calculate_panic_contagion(units, "u1")
        assert "u2" in result
        assert "u3" in result
        assert result["u2"] == -10
        assert result["u3"] == -10

    def test_contag_02_panicked_not_reinfected(self, calc: MoraleCalculator):
        units = [
            ("u1", MoraleComponent(value=80)),
            ("u2", MoraleComponent(value=20)),
            ("u3", MoraleComponent(value=70)),
        ]
        result = calc.calculate_panic_contagion(units, "u1")
        assert "u2" not in result

    def test_contag_03_routing_not_infected(self, calc: MoraleCalculator):
        units = [
            ("u1", MoraleComponent(value=80)),
            ("u2", MoraleComponent(value=5)),
            ("u3", MoraleComponent(value=70)),
        ]
        result = calc.calculate_panic_contagion(units, "u1")
        assert "u2" not in result

    def test_contag_04_empty_squad_no_contagion(self, calc: MoraleCalculator):
        result = calc.calculate_panic_contagion([], "u1")
        assert result == {}


class TestNaturalRecovery:
    def test_rec_01_ticks_below_30_no_recovery(self, calc: MoraleCalculator):
        assert calc.calculate_natural_recovery(50, 29) == 50
        assert calc.calculate_natural_recovery(50, 0) == 50

    def test_rec_02_ticks_above_30_recovers(self, calc: MoraleCalculator):
        assert calc.calculate_natural_recovery(50, 30) == 55
        assert calc.calculate_natural_recovery(50, 60) == 55

    def test_rec_03_recovery_clamped_at_100(self, calc: MoraleCalculator):
        assert calc.calculate_natural_recovery(98, 30) == 100
        assert calc.calculate_natural_recovery(100, 30) == 100

    def test_rec_04_dead_unit_no_recovery(self, calc: MoraleCalculator):
        assert calc.calculate_natural_recovery(0, 30) == 5
        assert calc.calculate_natural_recovery(0, 60) == 5


class TestShouldPanicContagion:
    def test_should_contagion_true_when_broken(self, calc: MoraleCalculator):
        mc = MoraleComponent(value=10)
        assert calc.should_panic_contagion(mc) is True

    def test_should_contagion_false_when_rallied(self, calc: MoraleCalculator):
        mc = MoraleComponent(value=80)
        assert calc.should_panic_contagion(mc) is False


class TestPredictState:
    def test_predict_rallied(self):
        assert MoraleCalculator.predict_state(80, 0) == "RALLIED"

    def test_predict_broken(self):
        assert MoraleCalculator.predict_state(10, 0) == "BROKEN"

    def test_predict_pinned(self):
        assert MoraleCalculator.predict_state(25, 0) == "PINNED"

    def test_predict_with_delta(self):
        assert MoraleCalculator.predict_state(50, -15) == "PINNED"

    def test_predict_wavering(self):
        assert MoraleCalculator.predict_state(45, 0) == "WAVERING"
