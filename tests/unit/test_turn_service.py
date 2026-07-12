"""
Unit Tests for TurnService

Tests turn/time management: TurnState dataclass, GamePhase enum, phase
progression, turn advancement, callbacks, time tracking, and state summary.

Follows the StubEventBus pattern from test_combat_director_unit.py.
"""

import pytest

from pycc2.services.turn_service import GamePhase, TurnService, TurnState

# ===========================================================================
# Stub helpers
# ===========================================================================


class StubEventBus:
    """Minimal event bus stub that records published events.

    TypedDicts (TurnStartedEvent, TurnEndedEvent, GamePhaseChangedEvent) are
    plain dicts at runtime, so type identity is lost. We identify events by
    their required keys instead (see helpers below).
    """

    def __init__(self):
        self.published = []

    def subscribe(self, event_type, handler):
        pass

    def publish(self, event):
        self.published.append(event)

    def publish_named(self, name, data):
        self.published.append({"name": name, "data": data})


def _has_keys(evt, keys):
    """Check if a published event dict contains all required keys."""
    return isinstance(evt, dict) and keys.issubset(evt.keys())


def _turn_started_events(bus):
    """TurnStartedEvent: has turn_number + faction, no old_phase."""
    return [
        e
        for e in bus.published
        if _has_keys(e, {"turn_number", "faction"}) and "old_phase" not in e
    ]


def _turn_ended_events(bus):
    """TurnEndedEvent: has turn_number, no faction, no old_phase."""
    return [
        e
        for e in bus.published
        if _has_keys(e, {"turn_number"})
        and "faction" not in e
        and "old_phase" not in e
    ]


def _phase_changed_events(bus):
    """GamePhaseChangedEvent: has old_phase + new_phase + turn_number."""
    return [e for e in bus.published if _has_keys(e, {"old_phase", "new_phase", "turn_number"})]


# ===========================================================================
# TurnState dataclass tests
# ===========================================================================


@pytest.mark.unit
class TestTurnStateDefaults:
    """Test TurnState default values and post-init behavior."""

    def test_default_values(self):
        state = TurnState()
        assert state.current_turn == 1
        assert state.current_phase == GamePhase.PLANNING
        assert state.turn_order == ["allied", "axis"]
        assert state.current_faction_index == 0
        assert state.max_turns is None
        assert state.time_elapsed_seconds == 0.0

    def test_post_init_empty_turn_order_fills_default(self):
        state = TurnState(turn_order=[])
        assert state.turn_order == ["allied", "axis"]

    def test_post_init_preserves_custom_turn_order(self):
        state = TurnState(turn_order=["red", "blue", "green"])
        assert state.turn_order == ["red", "blue", "green"]

    def test_custom_max_turns(self):
        state = TurnState(max_turns=10)
        assert state.max_turns == 10

    def test_custom_initial_phase(self):
        state = TurnState(current_phase=GamePhase.COMBAT)
        assert state.current_phase == GamePhase.COMBAT

    def test_custom_current_turn(self):
        state = TurnState(current_turn=5)
        assert state.current_turn == 5


# ===========================================================================
# GamePhase enum tests
# ===========================================================================


@pytest.mark.unit
class TestGamePhase:
    """Test GamePhase enum membership and ordering."""

    def test_all_four_phases_exist(self):
        assert GamePhase.PLANNING is not None
        assert GamePhase.MOVEMENT is not None
        assert GamePhase.COMBAT is not None
        assert GamePhase.RESOLUTION is not None

    def test_phase_count(self):
        assert len(list(GamePhase)) == 4

    def test_phases_distinct(self):
        phases = list(GamePhase)
        assert len(set(phases)) == 4

    def test_phase_order(self):
        phases = list(GamePhase)
        assert phases == [
            GamePhase.PLANNING,
            GamePhase.MOVEMENT,
            GamePhase.COMBAT,
            GamePhase.RESOLUTION,
        ]

    def test_phase_is_enum(self):
        from enum import Enum

        assert isinstance(GamePhase.PLANNING, GamePhase)
        assert isinstance(GamePhase.PLANNING, Enum)


# ===========================================================================
# TurnService __init__ tests
# ===========================================================================


@pytest.mark.unit
class TestTurnServiceInit:
    """Test TurnService initialization."""

    def test_init_stores_event_bus(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        assert svc.event_bus is bus

    def test_init_creates_default_state(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        assert isinstance(svc.state, TurnState)
        assert svc.state.current_turn == 1
        assert svc.state.current_phase == GamePhase.PLANNING
        assert svc.state.current_faction_index == 0
        assert svc.state.time_elapsed_seconds == 0.0

    def test_init_state_has_default_turn_order(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        assert svc.state.turn_order == ["allied", "axis"]

    def test_init_default_max_turns_none(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        assert svc.state.max_turns is None

    def test_init_custom_max_turns(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=15)
        assert svc.state.max_turns == 15

    def test_init_empty_callback_dicts(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        assert svc._phase_callbacks == {}
        assert svc._turn_start_callbacks == []
        assert svc._turn_end_callbacks == []


# ===========================================================================
# Callback registration tests
# ===========================================================================


@pytest.mark.unit
class TestCallbackRegistration:
    """Test callback registration methods."""

    def test_register_phase_callback_stores_callable(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)

        def cb():
            pass

        svc.register_phase_callback(GamePhase.COMBAT, cb)
        assert svc._phase_callbacks[GamePhase.COMBAT] is cb

    def test_register_phase_callback_overwrites_previous(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)

        def first():
            pass

        def second():
            pass

        svc.register_phase_callback(GamePhase.MOVEMENT, first)
        svc.register_phase_callback(GamePhase.MOVEMENT, second)
        assert svc._phase_callbacks[GamePhase.MOVEMENT] is second
        assert len(svc._phase_callbacks) == 1

    def test_register_turn_start_callback_appends(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)

        def cb1():
            pass

        def cb2():
            pass

        svc.register_turn_start_callback(cb1)
        svc.register_turn_start_callback(cb2)
        assert svc._turn_start_callbacks == [cb1, cb2]

    def test_register_turn_end_callback_appends(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)

        def cb1():
            pass

        def cb2():
            pass

        svc.register_turn_end_callback(cb1)
        svc.register_turn_end_callback(cb2)
        assert svc._turn_end_callbacks == [cb1, cb2]


# ===========================================================================
# start_game tests
# ===========================================================================


@pytest.mark.unit
class TestStartGame:
    """Test start_game initializes and publishes TurnStartedEvent."""

    def test_start_game_resets_turn_to_one(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.current_turn = 5
        svc.start_game()
        assert svc.state.current_turn == 1

    def test_start_game_resets_phase_to_planning(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.current_phase = GamePhase.COMBAT
        svc.start_game()
        assert svc.state.current_phase == GamePhase.PLANNING

    def test_start_game_resets_faction_index_to_zero(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.current_faction_index = 1
        svc.start_game()
        assert svc.state.current_faction_index == 0

    def test_start_game_resets_time_to_zero(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.time_elapsed_seconds = 42.5
        svc.start_game()
        assert svc.state.time_elapsed_seconds == 0.0

    def test_start_game_publishes_turn_started_event(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.start_game()
        assert len(bus.published) == 1
        started = _turn_started_events(bus)
        assert len(started) == 1
        assert started[0]["turn_number"] == 1
        assert started[0]["faction"] == "allied"

    def test_start_game_publishes_exactly_one_event(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.start_game()
        assert len(bus.published) == 1


# ===========================================================================
# advance_phase tests
# ===========================================================================


@pytest.mark.unit
class TestAdvancePhase:
    """Test phase progression logic."""

    def test_planning_to_movement(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        new_phase = svc.advance_phase()
        assert new_phase == GamePhase.MOVEMENT
        assert svc.state.current_phase == GamePhase.MOVEMENT

    def test_movement_to_combat(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.advance_phase()  # PLANNING -> MOVEMENT
        new_phase = svc.advance_phase()
        assert new_phase == GamePhase.COMBAT
        assert svc.state.current_phase == GamePhase.COMBAT

    def test_combat_to_resolution(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.advance_phase()  # -> MOVEMENT
        svc.advance_phase()  # -> COMBAT
        new_phase = svc.advance_phase()
        assert new_phase == GamePhase.RESOLUTION
        assert svc.state.current_phase == GamePhase.RESOLUTION

    def test_resolution_to_planning_triggers_advance_turn(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.advance_phase()  # -> MOVEMENT
        svc.advance_phase()  # -> COMBAT
        svc.advance_phase()  # -> RESOLUTION
        new_phase = svc.advance_phase()  # -> PLANNING (advance turn)
        assert new_phase == GamePhase.PLANNING
        assert svc.state.current_turn == 2

    def test_advance_phase_publishes_game_phase_changed_event(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.advance_phase()
        phase_events = _phase_changed_events(bus)
        assert len(phase_events) == 1
        evt = phase_events[0]
        assert evt["old_phase"] == "PLANNING"
        assert evt["new_phase"] == "MOVEMENT"
        assert evt["turn_number"] == 1

    def test_advance_phase_invokes_phase_callback(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        called = []
        svc.register_phase_callback(GamePhase.MOVEMENT, lambda: called.append("movement"))
        svc.advance_phase()
        assert called == ["movement"]

    def test_advance_phase_no_callback_does_not_raise(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        # No callback registered for MOVEMENT; should not raise
        new_phase = svc.advance_phase()
        assert new_phase == GamePhase.MOVEMENT

    def test_advance_phase_full_cycle_returns_to_planning(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.advance_phase()  # -> MOVEMENT
        svc.advance_phase()  # -> COMBAT
        svc.advance_phase()  # -> RESOLUTION
        # Don't start_game; rely on advance_turn behavior.
        # current_turn increments to 2 and TurnEndedEvent/TurnStartedEvent published.
        starting_published_count = len(bus.published)
        svc.advance_phase()  # -> PLANNING (advance turn)
        assert svc.state.current_phase == GamePhase.PLANNING
        # Should publish GamePhaseChangedEvent + TurnEndedEvent + TurnStartedEvent
        assert len(bus.published) - starting_published_count == 3


# ===========================================================================
# _advance_turn tests (via advance_phase from RESOLUTION)
# ===========================================================================


@pytest.mark.unit
class TestAdvanceTurn:
    """Test turn advancement behavior."""

    def test_advance_turn_increments_turn_number(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        # Drive through full phase cycle to trigger _advance_turn
        for _ in range(4):
            svc.advance_phase()
        assert svc.state.current_turn == 2

    def test_advance_turn_calls_turn_end_callbacks(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        end_calls = []
        svc.register_turn_end_callback(lambda: end_calls.append("ended"))
        for _ in range(4):
            svc.advance_phase()
        assert end_calls == ["ended"]

    def test_advance_turn_calls_turn_start_callbacks_when_not_at_limit(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=5)
        start_calls = []
        svc.register_turn_start_callback(lambda: start_calls.append("started"))
        for _ in range(4):
            svc.advance_phase()
        assert start_calls == ["started"]

    def test_advance_turn_publishes_turn_ended_event(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        for _ in range(4):
            svc.advance_phase()
        ended_events = _turn_ended_events(bus)
        assert len(ended_events) == 1
        # current_turn was 1 before advance, now 2; TurnEndedEvent records turn 1
        assert ended_events[0]["turn_number"] == 1

    def test_advance_turn_publishes_turn_started_event(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        for _ in range(4):
            svc.advance_phase()
        started_events = _turn_started_events(bus)
        # Only one TurnStartedEvent, published during _advance_turn.
        assert len(started_events) == 1
        assert started_events[0]["turn_number"] == 2
        assert started_events[0]["faction"] == "axis"  # faction index advanced to 1

    def test_advance_turn_advances_faction_index(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        for _ in range(4):
            svc.advance_phase()
        assert svc.state.current_faction_index == 1
        assert svc.get_current_faction() == "axis"

    def test_advance_turn_wraps_faction_index(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        # Advance through two full phase cycles to wrap faction index back to 0
        for _ in range(4):
            svc.advance_phase()
        for _ in range(4):
            svc.advance_phase()
        assert svc.state.current_faction_index == 0
        assert svc.get_current_faction() == "allied"

    def test_advance_turn_at_max_turns_stops_without_turn_started(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=1)
        start_calls = []
        svc.register_turn_start_callback(lambda: start_calls.append("started"))
        # Complete one full phase cycle: turn goes from 1 -> 2 (>max_turns=1)
        for _ in range(4):
            svc.advance_phase()
        # Turn limit reached: no TurnStartedEvent published, no start callback
        started_events = _turn_started_events(bus)
        assert started_events == []
        assert start_calls == []
        assert svc.state.current_turn == 2

    def test_advance_turn_at_max_turns_calls_end_callbacks(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=1)
        end_calls = []
        svc.register_turn_end_callback(lambda: end_calls.append("ended"))
        for _ in range(4):
            svc.advance_phase()
        # End callbacks ARE called before the max_turns check
        assert end_calls == ["ended"]

    def test_advance_turn_at_max_turns_no_turn_ended_event(self):
        """When max_turns reached, neither TurnEndedEvent nor TurnStartedEvent
        is published — only turn_end_callbacks fire. This is the current
        source behavior (see bug note in report)."""
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=1)
        for _ in range(4):
            svc.advance_phase()
        ended_events = _turn_ended_events(bus)
        started_events = _turn_started_events(bus)
        assert ended_events == []
        assert started_events == []


# ===========================================================================
# end_current_turn tests
# ===========================================================================


@pytest.mark.unit
class TestEndCurrentTurn:
    """Test end_current_turn forces RESOLUTION then advances."""

    def test_end_current_turn_sets_resolution_phase(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        # Force-set to MOVEMENT first; end_current_turn sets RESOLUTION then advance
        svc.state.current_phase = GamePhase.MOVEMENT
        svc.end_current_turn()
        # After end_current_turn: phase set to RESOLUTION, then advance_phase
        # wraps to PLANNING and triggers _advance_turn.
        assert svc.state.current_phase == GamePhase.PLANNING

    def test_end_current_turn_increments_turn(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.end_current_turn()
        assert svc.state.current_turn == 2

    def test_end_current_turn_publishes_phase_changed_with_resolution(self):
        """end_current_turn sets phase=RESOLUTION directly (no event), then
        advance_phase publishes RESOLUTION -> PLANNING."""
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.current_phase = GamePhase.MOVEMENT
        svc.end_current_turn()
        phase_events = _phase_changed_events(bus)
        # Only ONE phase-changed event: RESOLUTION -> PLANNING (the direct
        # set to RESOLUTION does NOT publish a phase-changed event).
        assert len(phase_events) == 1
        assert phase_events[0]["old_phase"] == "RESOLUTION"
        assert phase_events[0]["new_phase"] == "PLANNING"

    def test_end_current_turn_from_planning_advances_turn(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.end_current_turn()
        # Should advance to turn 2 with appropriate events
        started_events = _turn_started_events(bus)
        assert any(e["turn_number"] == 2 for e in started_events)


# ===========================================================================
# update_time tests
# ===========================================================================


@pytest.mark.unit
class TestUpdateTime:
    """Test elapsed time accumulation."""

    def test_update_time_accumulates(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.update_time(10.0)
        assert svc.state.time_elapsed_seconds == 10.0

    def test_update_time_multiple_calls(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.update_time(5.0)
        svc.update_time(7.5)
        svc.update_time(2.5)
        assert svc.state.time_elapsed_seconds == 15.0

    def test_update_time_zero(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.update_time(0.0)
        assert svc.state.time_elapsed_seconds == 0.0

    def test_update_time_negative(self):
        """Negative dt is allowed by the implementation; it subtracts."""
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.update_time(10.0)
        svc.update_time(-3.0)
        assert svc.state.time_elapsed_seconds == 7.0


# ===========================================================================
# get_current_faction tests
# ===========================================================================


@pytest.mark.unit
class TestGetCurrentFaction:
    """Test faction lookup."""

    def test_default_faction_allied(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        assert svc.get_current_faction() == "allied"

    def test_faction_after_index_change(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.current_faction_index = 1
        assert svc.get_current_faction() == "axis"

    def test_faction_with_custom_turn_order(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.turn_order = ["red", "blue", "green"]
        svc.state.current_faction_index = 2
        assert svc.get_current_faction() == "green"


# ===========================================================================
# is_player_turn tests
# ===========================================================================


@pytest.mark.unit
class TestIsPlayerTurn:
    """Test is_player_turn comparison."""

    def test_player_turn_true_when_matches(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        assert svc.is_player_turn("allied") is True

    def test_player_turn_false_when_mismatch(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        assert svc.is_player_turn("axis") is False

    def test_player_turn_after_faction_change(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.current_faction_index = 1
        assert svc.is_player_turn("axis") is True
        assert svc.is_player_turn("allied") is False


# ===========================================================================
# is_turn_limit_reached property tests
# ===========================================================================


@pytest.mark.unit
class TestIsTurnLimitReached:
    """Test is_turn_limit_reached property."""

    def test_no_max_turns_returns_false(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        assert svc.is_turn_limit_reached is False

    def test_no_max_turns_even_high_turn_returns_false(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.current_turn = 100
        assert svc.is_turn_limit_reached is False

    def test_under_limit_returns_false(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=5)
        svc.state.current_turn = 3
        assert svc.is_turn_limit_reached is False

    def test_at_limit_returns_false(self):
        """current_turn == max_turns is NOT over the limit."""
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=5)
        svc.state.current_turn = 5
        assert svc.is_turn_limit_reached is False

    def test_over_limit_returns_true(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=5)
        svc.state.current_turn = 6
        assert svc.is_turn_limit_reached is True


# ===========================================================================
# formatted_time property tests
# ===========================================================================


@pytest.mark.unit
class TestFormattedTime:
    """Test formatted_time MM:SS property."""

    def test_zero_time(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        assert svc.formatted_time == "00:00"

    def test_under_minute(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.time_elapsed_seconds = 45.0
        assert svc.formatted_time == "00:45"

    def test_exactly_one_minute(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.time_elapsed_seconds = 60.0
        assert svc.formatted_time == "01:00"

    def test_over_one_minute(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.time_elapsed_seconds = 65.0
        assert svc.formatted_time == "01:05"

    def test_two_digits_minutes(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.time_elapsed_seconds = 125.0
        assert svc.formatted_time == "02:05"

    def test_truncates_fractional_seconds(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.time_elapsed_seconds = 65.7
        # int(65.7) = 65 -> "01:05"
        assert svc.formatted_time == "01:05"

    def test_large_value(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.time_elapsed_seconds = 3661.0  # 61:01
        assert svc.formatted_time == "61:01"


# ===========================================================================
# reset tests
# ===========================================================================


@pytest.mark.unit
class TestReset:
    """Test reset() restores initial state."""

    def test_reset_restores_turn_to_one(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.current_turn = 7
        svc.reset()
        assert svc.state.current_turn == 1

    def test_reset_restores_phase_to_planning(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.current_phase = GamePhase.COMBAT
        svc.reset()
        assert svc.state.current_phase == GamePhase.PLANNING

    def test_reset_restores_faction_index_to_zero(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.current_faction_index = 1
        svc.reset()
        assert svc.state.current_faction_index == 0

    def test_reset_restores_time_to_zero(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.time_elapsed_seconds = 99.9
        svc.reset()
        assert svc.state.time_elapsed_seconds == 0.0

    def test_reset_restores_turn_order_to_default(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.turn_order = ["custom"]
        svc.reset()
        assert svc.state.turn_order == ["allied", "axis"]

    def test_reset_preserves_max_turns(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=10)
        svc.reset()
        assert svc.state.max_turns == 10

    def test_reset_replaces_state_instance(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        old_state = svc.state
        svc.reset()
        assert svc.state is not old_state
        assert isinstance(svc.state, TurnState)


# ===========================================================================
# get_state_summary tests
# ===========================================================================


@pytest.mark.unit
class TestGetStateSummary:
    """Test get_state_summary returns expected dict."""

    def test_summary_default_state(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        summary = svc.get_state_summary()
        assert summary == {
            "turn": 1,
            "phase": "PLANNING",
            "faction": "allied",
            "time": "00:00",
            "max_turns": None,
        }

    def test_summary_includes_all_keys(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        summary = svc.get_state_summary()
        assert set(summary.keys()) == {"turn", "phase", "faction", "time", "max_turns"}

    def test_summary_reflects_advanced_state(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=5)
        svc.state.current_turn = 3
        svc.state.current_phase = GamePhase.COMBAT
        svc.state.current_faction_index = 1
        svc.state.time_elapsed_seconds = 125.0
        summary = svc.get_state_summary()
        assert summary["turn"] == 3
        assert summary["phase"] == "COMBAT"
        assert summary["faction"] == "axis"
        assert summary["time"] == "02:05"
        assert summary["max_turns"] == 5

    def test_summary_phase_is_string_name(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus)
        svc.state.current_phase = GamePhase.RESOLUTION
        summary = svc.get_state_summary()
        assert summary["phase"] == "RESOLUTION"
        assert isinstance(summary["phase"], str)


# ===========================================================================
# Integration: full game flow
# ===========================================================================


@pytest.mark.unit
class TestTurnServiceFullFlow:
    """Integration-style tests covering multiple methods together."""

    def test_full_turn_cycle_publishes_expected_events(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=3)
        svc.start_game()
        bus.published.clear()

        # Complete one full phase cycle (4 advances)
        svc.advance_phase()  # PLANNING -> MOVEMENT
        svc.advance_phase()  # MOVEMENT -> COMBAT
        svc.advance_phase()  # COMBAT -> RESOLUTION
        svc.advance_phase()  # RESOLUTION -> PLANNING (turn advance)

        # 4 GamePhaseChangedEvents + 1 TurnEndedEvent + 1 TurnStartedEvent
        assert len(_phase_changed_events(bus)) == 4
        assert len(_turn_ended_events(bus)) == 1
        assert len(_turn_started_events(bus)) == 1

    def test_game_with_callbacks_full_cycle(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=3)
        phase_calls = []
        start_calls = []
        end_calls = []

        for phase in GamePhase:
            svc.register_phase_callback(phase, lambda p=phase: phase_calls.append(p.name))
        svc.register_turn_start_callback(lambda: start_calls.append("start"))
        svc.register_turn_end_callback(lambda: end_calls.append("end"))

        svc.start_game()
        phase_calls.clear()
        start_calls.clear()
        end_calls.clear()

        for _ in range(4):
            svc.advance_phase()

        # All 4 phase callbacks fire across the cycle
        assert phase_calls == ["MOVEMENT", "COMBAT", "RESOLUTION", "PLANNING"]
        assert start_calls == ["start"]
        assert end_calls == ["end"]

    def test_multiple_turns_progression(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=5)
        svc.start_game()

        # Complete 3 full phase cycles -> turn 4
        for _ in range(3):
            for _ in range(4):
                svc.advance_phase()

        assert svc.state.current_turn == 4
        assert svc.state.current_faction_index == 1  # odd turn -> axis
        assert svc.is_turn_limit_reached is False

    def test_reset_clears_progress(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=5)
        svc.start_game()
        for _ in range(4):
            svc.advance_phase()
        svc.update_time(100.0)
        assert svc.state.current_turn == 2

        svc.reset()
        assert svc.state.current_turn == 1
        assert svc.state.current_phase == GamePhase.PLANNING
        assert svc.state.current_faction_index == 0
        assert svc.state.time_elapsed_seconds == 0.0
        assert svc.state.max_turns == 5

    def test_end_current_turn_at_limit_stops(self):
        bus = StubEventBus()
        svc = TurnService(event_bus=bus, max_turns=1)
        svc.start_game()
        bus.published.clear()

        svc.end_current_turn()

        # max_turns=1 reached; no TurnStartedEvent, no TurnEndedEvent
        started = _turn_started_events(bus)
        ended = _turn_ended_events(bus)
        assert started == []
        assert ended == []
        assert svc.state.current_turn == 2
        assert svc.is_turn_limit_reached is True
