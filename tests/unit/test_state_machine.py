"""
Tests for StateMachine
"""

from __future__ import annotations

from enum import Enum, auto

import pytest

from pycc2.domain.state_machine import StateMachine, TransitionError


class TestState(Enum):
    IDLE = auto()
    MOVING = auto()
    ATTACKING = auto()
    DEAD = auto()


class TestStateMachineConstruction:
    def test_initial_state(self):
        sm = StateMachine(
            initial=TestState.IDLE,
            transitions={
                TestState.IDLE: {TestState.MOVING},
                TestState.MOVING: {TestState.IDLE},
            },
        )
        assert sm.current == TestState.IDLE

    def test_initial_history_empty(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={TestState.IDLE: set()})
        assert len(sm.history) == 0

    def test_type_guard_rejects_non_enum(self):
        with pytest.raises(TypeError, match="must be an Enum"):
            StateMachine(initial="idle", transitions={})


class TestCanTransitionTo:
    def test_valid_transition(self):
        sm = StateMachine(
            initial=TestState.IDLE,
            transitions={
                TestState.IDLE: {TestState.MOVING, TestState.ATTACKING},
                TestState.MOVING: {TestState.IDLE},
            },
        )
        assert sm.can_transition_to(TestState.MOVING) is True
        assert sm.can_transition_to(TestState.ATTACKING) is True

    def test_invalid_transition(self):
        sm = StateMachine(
            initial=TestState.IDLE,
            transitions={
                TestState.IDLE: {TestState.MOVING},
                TestState.MOVING: {TestState.IDLE},
            },
        )
        assert sm.can_transition_to(TestState.DEAD) is False

    def test_terminal_state_no_transitions(self):
        sm = StateMachine(initial=TestState.DEAD, transitions={TestState.DEAD: set()})
        assert sm.can_transition_to(TestState.IDLE) is False


class TestTryTransition:
    def test_successful_transition(self):
        sm = StateMachine(
            initial=TestState.IDLE,
            transitions={
                TestState.IDLE: {TestState.MOVING},
                TestState.MOVING: {TestState.IDLE},
            },
        )
        result = sm.try_transition(TestState.MOVING)
        assert result is True
        assert sm.current == TestState.MOVING

    def test_failed_transition(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={TestState.IDLE: set()})
        result = sm.try_transition(TestState.MOVING)
        assert result is False
        assert sm.current == TestState.IDLE

    def test_failed_transition_does_not_record_history(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={TestState.IDLE: set()})
        sm.try_transition(TestState.MOVING)
        assert len(sm.history) == 0


class TestTransitionOrRaise:
    def test_successful_transition(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={TestState.IDLE: {TestState.MOVING}})
        sm.transition_or_raise(TestState.MOVING)
        assert sm.current == TestState.MOVING

    def test_invalid_raises_error(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={TestState.IDLE: set()})
        with pytest.raises(TransitionError):
            sm.transition_or_raise(TestState.MOVING)


class TestForceTransition:
    def test_bypasses_validation(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={TestState.IDLE: set()})
        sm.force_transition(TestState.DEAD)
        assert sm.current == TestState.DEAD

    def test_records_history(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={})
        sm.force_transition(TestState.MOVING)
        assert len(sm.history) == 1
        assert sm.history[0] == (TestState.IDLE, TestState.MOVING)


class TestCallbacks:
    def test_on_enter_callback_fired(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={TestState.IDLE: {TestState.MOVING}})
        called_states = []
        sm.on_enter(TestState.MOVING, lambda s: called_states.append(s))
        sm.try_transition(TestState.MOVING)
        assert TestState.MOVING in called_states

    def test_on_exit_callback_fired(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={TestState.IDLE: {TestState.MOVING}})
        called_states = []
        sm.on_exit(TestState.IDLE, lambda s: called_states.append(s))
        sm.try_transition(TestState.MOVING)
        assert TestState.IDLE in called_states

    def test_multiple_callbacks_same_state(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={TestState.IDLE: {TestState.MOVING}})
        call_count = [0]
        sm.on_enter(TestState.MOVING, lambda s: call_count.__setitem__(0, call_count[0] + 1))
        sm.on_enter(TestState.MOVING, lambda s: call_count.__setitem__(0, call_count[0] + 1))
        sm.force_transition(TestState.MOVING)
        assert call_count[0] == 2


class TestHistory:
    def test_history_records_transitions(self):
        sm = StateMachine(
            initial=TestState.IDLE,
            transitions={
                TestState.IDLE: {TestState.MOVING},
                TestState.MOVING: {TestState.ATTACKING},
            },
        )
        sm.transition_or_raise(TestState.MOVING)
        sm.transition_or_raise(TestState.ATTACKING)
        assert len(sm.history) == 2
        assert sm.history[0] == (TestState.IDLE, TestState.MOVING)
        assert sm.history[1] == (TestState.MOVING, TestState.ATTACKING)


class TestReset:
    def test_reset_clears_history(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={TestState.IDLE: {TestState.MOVING}})
        sm.transition_or_raise(TestState.MOVING)
        sm.reset()
        assert len(sm.history) == 0
        assert sm.current == TestState.MOVING

    def test_reset_to_specific_state(self):
        sm = StateMachine(initial=TestState.IDLE, transitions={TestState.IDLE: {TestState.MOVING}})
        sm.transition_or_raise(TestState.MOVING)
        sm.reset(state=TestState.IDLE)
        assert sm.current == TestState.IDLE
        assert len(sm.history) == 0
