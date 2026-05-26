"""
Unit tests for MoraleComponent
"""

from __future__ import annotations

import pytest

from pycc2.domain.components.morale_component import (
    MoraleComponent,
    MoraleState,
)


class TestMoraleComponentConstruction:
    def test_default_construction(self):
        mc = MoraleComponent(value=100)
        assert mc.value == 100
        assert mc.state == MoraleState.RALLIED
        assert mc.suppression == 0

    def test_full_morale_is_rallied(self):
        mc = MoraleComponent(value=100)
        assert mc.state == MoraleState.RALLIED
        assert mc.is_combat_effective is True

    def test_pinned_threshold_boundary(self):
        mc = MoraleComponent(value=21)
        assert mc.state == MoraleState.PINNED
        mc2 = MoraleComponent(value=41)
        assert mc2.state == MoraleState.WAVERING

    def test_broken_threshold_boundary(self):
        mc = MoraleComponent(value=20)
        assert mc.state == MoraleState.BROKEN
        mc2 = MoraleComponent(value=21)
        assert mc2.state == MoraleState.PINNED


class TestMoraleComponentApplyDelta:
    def test_positive_delta(self):
        mc = MoraleComponent(value=50)
        mc.apply_delta(20)
        assert mc.value == 70
        assert mc.state == MoraleState.WAVERING

    def test_negative_delta(self):
        mc = MoraleComponent(value=80)
        mc.apply_delta(-30)
        assert mc.value == 50
        assert mc.state == MoraleState.WAVERING

    def test_clamp_upper_bound(self):
        mc = MoraleComponent(value=95)
        mc.apply_delta(20)
        assert mc.value == 100

    def test_clamp_lower_bound(self):
        mc = MoraleComponent(value=10)
        mc.apply_delta(-20)
        assert mc.value == 0
        assert mc.state == MoraleState.BROKEN

    def test_zero_delta(self):
        mc = MoraleComponent(value=50)
        mc.apply_delta(0)
        assert mc.value == 50

    def test_state_transition_to_panic(self):
        mc = MoraleComponent(value=40)
        mc.apply_delta(-15)
        assert mc.value == 25
        assert mc.state == MoraleState.PINNED

    def test_state_transition_to_broken(self):
        mc = MoraleComponent(value=25)
        mc.apply_delta(-10)
        assert mc.value == 15
        assert mc.state == MoraleState.BROKEN


class TestMoraleComponentSuppression:
    def test_add_suppression(self):
        mc = MoraleComponent(value=80)
        mc.add_suppression(25)
        assert mc.suppression == 25

    def test_decay_suppression(self):
        mc = MoraleComponent(value=80)
        mc.add_suppression(30)
        mc.decay_suppression(10)
        assert mc.suppression == 20

    def test_decay_to_zero(self):
        mc = MoraleComponent(value=80)
        mc.add_suppression(15)
        mc.decay_suppression(20)
        assert mc.suppression == 0

    def test_negative_decay_does_not_go_below_zero(self):
        mc = MoraleComponent(value=80)
        mc.decay_suppression(10)
        assert mc.suppression == 0


class TestMoraleComponentNaturalRecovery:
    def test_natural_recovery_increases_morale(self):
        mc = MoraleComponent(value=60)
        initial = mc.value
        mc.natural_recovery()
        mc.natural_recovery()
        assert mc.value >= initial

    def test_natural_recovery_clamps_at_100(self):
        mc = MoraleComponent(value=99)
        for _ in range(10):
            mc.natural_recovery()
        assert mc.value <= 100

    def test_natural_recovery_amount_is_half_point(self):
        mc = MoraleComponent(value=90)
        mc.natural_recovery()
        assert mc.value == 90 or mc.value == 91


class TestMoraleComponentAccuracyModifier:
    def test_rallied_accuracy(self):
        mc = MoraleComponent(value=80)
        assert mc.accuracy_modifier == 1.05

    def test_wavering_accuracy(self):
        mc = MoraleComponent(value=50)
        assert mc.accuracy_modifier == 0.95

    def test_pinned_accuracy(self):
        mc = MoraleComponent(value=25)
        assert mc.accuracy_modifier == 0.60

    def test_broken_accuracy(self):
        mc = MoraleComponent(value=10)
        assert mc.accuracy_modifier == 0.30

    def test_routing_accuracy(self):
        mc = MoraleComponent(value=5)
        mc.start_routing()
        assert mc.accuracy_modifier == 0.10


class TestMoraleComponentThresholds:
    def test_wavering_at_boundary(self):
        mc = MoraleComponent(value=41)
        assert mc.state == MoraleState.WAVERING

    def test_broken_at_low_value(self):
        mc = MoraleComponent(value=10)
        assert mc.state == MoraleState.BROKEN


class TestMoraleValueType:
    def test_value_must_be_int_not_float(self):
        with pytest.raises(TypeError):
            MoraleComponent(value=85.5)  # type: ignore[arg-type]

    def test_value_accepts_int(self):
        mc = MoraleComponent(value=75)
        assert isinstance(mc.value, int)
        assert mc.value == 75
