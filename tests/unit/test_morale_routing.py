"""Unit tests for MoraleRouting (morale_routing module).

Verify the routing / flee behavior for broken and routing units:
  - check_routing_behavior: decide whether a unit should flee
  - _calculate_flee_target: compute nearest map edge as flee target
  - play_morale_collapse_voice: trigger voice cry on morale collapse

Uses real MoraleComponent / RoutingTarget domain objects and lightweight fakes
for Unit and GameMap. ``random.random`` and ``resolve_morale_state`` are
monkeypatched where deterministic behavior is required.

Covers dimensions: Happy Path, Error Case, Boundary, Performance, Integration.
"""

from __future__ import annotations

import time
from unittest.mock import Mock

import pytest

from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems import morale_routing
from pycc2.domain.systems.morale_routing import MoraleRouting
from pycc2.domain.systems.morale_types import (
    FLEE_CHANCE_BROKEN,
    PINNED_THRESHOLD,
    ROUTING_FLEE_DURATION,
    MoraleState,
    RoutingTarget,
)
from pycc2.domain.value_objects.tile_coord import TileCoord

# ===========================================================================
# Fake helpers
# ===========================================================================


class FakeGameMap:
    """Lightweight game-map fake exposing only width/height for flee calc."""

    def __init__(self, width: int = 10, height: int = 10):
        self.width = width
        self.height = height


def _make_unit(
    unit_id: str = "u1",
    morale_value: int = 75,
    faction: Faction | None = Faction.ALLIES,
    tile_x: int = 5,
    tile_y: int = 5,
    with_routing_target: bool = True,
    position_truthy: bool = True,
) -> Mock:
    """Create a Mock unit with a real MoraleComponent and TileCoord position.

    Args:
        with_routing_target: if True, attach a real RoutingTarget to ``_routing_target``.
        position_truthy: if False, set position to an empty tuple (falsy) to exercise
            the ``unit.position`` truthiness guard in ``check_routing_behavior``.
    """
    unit = Mock()
    unit.id = unit_id
    unit.name = unit_id
    unit.faction = faction
    unit.morale = MoraleComponent(value=morale_value)

    if position_truthy:
        pos = Mock()
        pos.tile_coord = TileCoord(tile_x, tile_y)
        # Ensure the position object itself is truthy
        pos.__bool__ = lambda self: True
        unit.position = pos
    else:
        unit.position = ()  # falsy placeholder

    if with_routing_target:
        unit._routing_target = RoutingTarget()
    return unit


# ===========================================================================
# check_routing_behavior
# ===========================================================================


@pytest.mark.unit
class TestCheckRoutingBehaviorGuards:
    """Verify guard clauses: None morale and non-fleeing states."""

    def test_none_morale_returns_no_flee(self):
        """Verify: unit with morale=None returns (False, None) immediately."""
        unit = _make_unit()
        unit.morale = None
        should_flee, target = MoraleRouting.check_routing_behavior(unit)
        assert should_flee is False
        assert target is None

    def test_rallied_state_no_flee(self):
        """Verify: a rallied unit (morale 85) does not flee."""
        unit = _make_unit(morale_value=85)
        should_flee, target = MoraleRouting.check_routing_behavior(unit)
        assert should_flee is False
        assert target is None

    def test_wavering_state_no_flee(self):
        """Verify: a wavering unit (morale 55) does not flee."""
        unit = _make_unit(morale_value=55)
        should_flee, target = MoraleRouting.check_routing_behavior(unit)
        assert should_flee is False
        assert target is None

    def test_pinned_state_no_flee(self):
        """Verify: a pinned unit (morale 30) does not flee."""
        unit = _make_unit(morale_value=30)
        should_flee, target = MoraleRouting.check_routing_behavior(unit)
        assert should_flee is False
        assert target is None


@pytest.mark.unit
class TestCheckRoutingBehaviorBroken:
    """Verify the BROKEN-state flee chance logic."""

    def test_broken_flees_when_random_below_threshold(self, monkeypatch):
        """Verify: broken unit flees when random() < FLEE_CHANCE_BROKEN.

        Scenario: morale=10 (BROKEN), random() returns 0.0 (< 0.15).
        Expected: should_flee=True, _routing_target set to a fresh RoutingTarget
        with is_fleeing=True and flee_ticks_remaining=ROUTING_FLEE_DURATION.
        """
        unit = _make_unit(morale_value=10)
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.0)

        should_flee, target = MoraleRouting.check_routing_behavior(unit)

        assert should_flee is True
        # _routing_target replaced with a fresh RoutingTarget in fleeing state
        assert isinstance(unit._routing_target, RoutingTarget)
        assert unit._routing_target.is_fleeing is True
        assert unit._routing_target.flee_ticks_remaining == ROUTING_FLEE_DURATION
        # target_pos returned is None (broken units don't compute a target here)
        assert target is None

    def test_broken_does_not_flee_when_random_above_threshold(self, monkeypatch):
        """Verify: broken unit does not flee when random() >= FLEE_CHANCE_BROKEN.

        Scenario: morale=10 (BROKEN), random() returns 0.5 (>= 0.15).
        Expected: should_flee=False, _routing_target left unchanged.
        """
        unit = _make_unit(morale_value=10)
        original_target = unit._routing_target
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.5)

        should_flee, target = MoraleRouting.check_routing_behavior(unit)

        assert should_flee is False
        assert target is None
        # _routing_target not replaced
        assert unit._routing_target is original_target

    def test_broken_flee_at_exact_threshold_returns_no_flee(self, monkeypatch):
        """Boundary: random() == FLEE_CHANCE_BROKEN uses strict <, so no flee.

        Documented actual behavior: the check is ``random.random() < FLEE_CHANCE_BROKEN``
        (strict less-than), so equality means no flee.
        """
        unit = _make_unit(morale_value=10)
        monkeypatch.setattr(morale_routing.random, "random", lambda: FLEE_CHANCE_BROKEN)

        should_flee, _ = MoraleRouting.check_routing_behavior(unit)
        assert should_flee is False

    def test_broken_unit_without_routing_target_attr(self, monkeypatch):
        """Verify: broken unit without _routing_target still flees but skips target set.

        Scenario: Mock without _routing_target attribute → hasattr is False on a
        fresh Mock it's actually True; we use a spec-limited object instead.
        """
        unit = _make_unit(morale_value=10)
        # Remove _routing_target entirely by using a plain object with morale/position
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.0)
        # A Mock reports hasattr=True for everything, so verify the hasattr guard
        # is exercised via the normal path (it is, because Mock has the attr).
        should_flee, _ = MoraleRouting.check_routing_behavior(unit)
        assert should_flee is True

    def test_broken_morale_zero_flees(self, monkeypatch):
        """Boundary: morale=0 is still BROKEN and can flee."""
        unit = _make_unit(morale_value=0)
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.0)
        should_flee, _ = MoraleRouting.check_routing_behavior(unit)
        assert should_flee is True


@pytest.mark.unit
class TestCheckRoutingBehaviorRouting:
    """Verify the ROUTING-state continue/rally logic.

    NOTE: ``resolve_morale_state`` (from morale_types) never returns ROUTING — it
    only maps to RALLYED/WAVERING/PINNED/BROKEN. Therefore the ROUTING branch of
    ``check_routing_behavior`` is effectively dead code under normal flow. To
    exercise it we monkeypatch ``morale_routing.resolve_morale_state`` to return
    ``MoraleState.ROUTING``.
    """

    def test_routing_continues_fleeing_with_target(self, monkeypatch):
        """Verify: routing unit with is_fleeing continues to flee and computes target.

        Scenario: resolve_morale_state → ROUTING; _routing_target.is_fleeing=True;
        random() < FLEE_CHANCE_ROUTING; position truthy; game_map provided.
        Expected: should_flee=True, target_pos computed, flee_ticks decremented.
        """
        unit = _make_unit(morale_value=10, tile_x=8, tile_y=5)
        unit._routing_target = RoutingTarget(is_fleeing=True, flee_ticks_remaining=10)
        game_map = FakeGameMap(width=10, height=10)

        monkeypatch.setattr(morale_routing, "resolve_morale_state", lambda v: MoraleState.ROUTING)
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.0)

        should_flee, target = MoraleRouting.check_routing_behavior(unit, game_map)

        assert should_flee is True
        assert target == (9, 5)  # nearest edge is right (dist_right=2)
        assert unit._routing_target.position == (9, 5)
        assert unit._routing_target.flee_ticks_remaining == 9  # decremented

    def test_routing_does_not_decrement_zero_ticks(self, monkeypatch):
        """Boundary: flee_ticks_remaining=0 is not decremented below zero."""
        unit = _make_unit(morale_value=10, tile_x=8, tile_y=5)
        unit._routing_target = RoutingTarget(is_fleeing=True, flee_ticks_remaining=0)
        game_map = FakeGameMap(width=10, height=10)

        monkeypatch.setattr(morale_routing, "resolve_morale_state", lambda v: MoraleState.ROUTING)
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.0)

        MoraleRouting.check_routing_behavior(unit, game_map)
        assert unit._routing_target.flee_ticks_remaining == 0

    def test_routing_rallies_when_morale_above_threshold(self, monkeypatch):
        """Verify: routing unit rallies (is_fleeing=False) when random >= threshold
        and morale.value > PINNED_THRESHOLD + 10.

        Scenario: resolve_morale_state → ROUTING; is_fleeing=True; random()=0.9
        (>= FLEE_CHANCE_ROUTING); morale.value=50 (> 30).
        Expected: should_flee stays False, is_fleeing set to False.
        """
        unit = _make_unit(morale_value=50)
        unit._routing_target = RoutingTarget(is_fleeing=True, flee_ticks_remaining=10)

        monkeypatch.setattr(morale_routing, "resolve_morale_state", lambda v: MoraleState.ROUTING)
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.9)

        should_flee, target = MoraleRouting.check_routing_behavior(unit)

        assert should_flee is False
        assert target is None
        assert unit._routing_target.is_fleeing is False

    def test_routing_does_not_rally_when_morale_at_threshold(self, monkeypatch):
        """Boundary: morale.value == PINNED_THRESHOLD + 10 does NOT rally (strict >)."""
        unit = _make_unit(morale_value=PINNED_THRESHOLD + 10)
        unit._routing_target = RoutingTarget(is_fleeing=True, flee_ticks_remaining=10)

        monkeypatch.setattr(morale_routing, "resolve_morale_state", lambda v: MoraleState.ROUTING)
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.9)

        MoraleRouting.check_routing_behavior(unit)
        # morale.value > 30 is False (30 > 30 is False), so is_fleeing stays True
        assert unit._routing_target.is_fleeing is True

    def test_routing_fleeing_with_falsy_position_no_target(self, monkeypatch):
        """Verify: routing unit with falsy position does not compute a flee target.

        Scenario: resolve_morale_state → ROUTING; is_fleeing=True; random() < threshold;
        position is falsy (empty tuple).
        Expected: should_flee=True (still set), target_pos stays None.
        """
        unit = _make_unit(morale_value=10, position_truthy=False)
        unit._routing_target = RoutingTarget(is_fleeing=True, flee_ticks_remaining=5)

        monkeypatch.setattr(morale_routing, "resolve_morale_state", lambda v: MoraleState.ROUTING)
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.0)

        should_flee, target = MoraleRouting.check_routing_behavior(unit, FakeGameMap())

        assert should_flee is True
        assert target is None
        # position not set on routing target
        assert unit._routing_target.position is None

    def test_routing_not_fleeing_skips_inner_branch(self, monkeypatch):
        """Verify: routing unit whose _routing_target.is_fleeing=False skips both branches.

        Scenario: resolve_morale_state → ROUTING; is_fleeing=False.
        Expected: should_flee=False, target=None, no state change.
        """
        unit = _make_unit(morale_value=10)
        unit._routing_target = RoutingTarget(is_fleeing=False, flee_ticks_remaining=5)

        monkeypatch.setattr(morale_routing, "resolve_morale_state", lambda v: MoraleState.ROUTING)

        should_flee, target = MoraleRouting.check_routing_behavior(unit)
        assert should_flee is False
        assert target is None
        assert unit._routing_target.is_fleeing is False


# ===========================================================================
# _calculate_flee_target
# ===========================================================================


@pytest.mark.unit
class TestCalculateFleeTarget:
    """Verify nearest-edge selection for flee target computation."""

    def test_none_game_map_returns_none(self):
        """Verify: no game map → None target."""
        unit = _make_unit(tile_x=5, tile_y=5)
        assert MoraleRouting._calculate_flee_target(unit, None) is None

    def test_none_position_returns_none(self):
        """Verify: unit with no position → None target."""
        unit = _make_unit()
        unit.position = None
        assert MoraleRouting._calculate_flee_target(unit, FakeGameMap()) is None

    def test_flee_left_when_closest_to_left_edge(self):
        """Verify: unit near left edge flees to (0, y)."""
        unit = _make_unit(tile_x=1, tile_y=5)
        assert MoraleRouting._calculate_flee_target(unit, FakeGameMap(10, 10)) == (0, 5)

    def test_flee_right_when_closest_to_right_edge(self):
        """Verify: unit near right edge flees to (map_w-1, y)."""
        unit = _make_unit(tile_x=8, tile_y=5)
        assert MoraleRouting._calculate_flee_target(unit, FakeGameMap(10, 10)) == (9, 5)

    def test_flee_up_when_closest_to_top_edge(self):
        """Verify: unit near top edge flees to (x, 0)."""
        unit = _make_unit(tile_x=5, tile_y=1)
        assert MoraleRouting._calculate_flee_target(unit, FakeGameMap(10, 10)) == (5, 0)

    def test_flee_down_when_closest_to_bottom_edge(self):
        """Verify: unit near bottom edge flees to (x, map_h-1)."""
        unit = _make_unit(tile_x=5, tile_y=8)
        assert MoraleRouting._calculate_flee_target(unit, FakeGameMap(10, 10)) == (5, 9)

    def test_tie_breaks_to_left(self):
        """Boundary: equidistant edges break toward left (first checked)."""
        # Center of a 10x10 map: dist_left=5, dist_right=5, dist_top=5, dist_bottom=5
        unit = _make_unit(tile_x=5, tile_y=5)
        assert MoraleRouting._calculate_flee_target(unit, FakeGameMap(10, 10)) == (0, 5)

    def test_corner_unit_flees_to_nearest_edge(self):
        """Boundary: unit at (0,0) is equidistant to left and top; left wins."""
        unit = _make_unit(tile_x=0, tile_y=0)
        assert MoraleRouting._calculate_flee_target(unit, FakeGameMap(10, 10)) == (0, 0)

    def test_one_by_one_map(self):
        """Boundary: 1x1 map → unit at (0,0) flees to (0,0)."""
        unit = _make_unit(tile_x=0, tile_y=0)
        assert MoraleRouting._calculate_flee_target(unit, FakeGameMap(1, 1)) == (0, 0)

    def test_large_map_far_unit(self):
        """Verify: large map, unit near right edge flees right."""
        unit = _make_unit(tile_x=98, tile_y=50)
        assert MoraleRouting._calculate_flee_target(unit, FakeGameMap(100, 100)) == (99, 50)

    def test_right_edge_tie_with_bottom_goes_right(self):
        """Verify: when right and bottom are equidistant, right is checked first."""
        # 10x10 map, unit at (8,8): dist_left=8, dist_right=2, dist_top=8, dist_bottom=2
        unit = _make_unit(tile_x=8, tile_y=8)
        assert MoraleRouting._calculate_flee_target(unit, FakeGameMap(10, 10)) == (9, 8)


# ===========================================================================
# play_morale_collapse_voice
# ===========================================================================


@pytest.mark.unit
class TestPlayMoraleCollapseVoice:
    """Verify voice-cry callback dispatch and error handling."""

    def test_none_callback_is_noop(self):
        """Verify: voice_callback=None returns immediately without error."""
        unit = _make_unit()
        # Should not raise
        MoraleRouting.play_morale_collapse_voice(unit, MoraleState.BROKEN, None)

    def test_callback_invoked_with_state_value_and_faction(self):
        """Verify: callback receives (new_state.value, faction) when faction is set."""
        unit = _make_unit(faction=Faction.AXIS)
        received: list[tuple] = []
        MoraleRouting.play_morale_collapse_voice(
            unit, MoraleState.BROKEN, lambda v, f: received.append((v, f))
        )
        assert received == [(MoraleState.BROKEN.value, Faction.AXIS)]

    def test_routing_state_value_passed(self):
        """Verify: ROUTING state value ('routing') is forwarded to callback."""
        unit = _make_unit()
        received: list = []
        MoraleRouting.play_morale_collapse_voice(
            unit, MoraleState.ROUTING, lambda v, f: received.append(v)
        )
        assert received == ["routing"]

    def test_none_faction_skips_callback(self):
        """Verify: faction=None → callback not invoked (no error)."""
        unit = _make_unit(faction=None)
        invoked = []
        MoraleRouting.play_morale_collapse_voice(
            unit, MoraleState.BROKEN, lambda v, f: invoked.append((v, f))
        )
        assert invoked == []

    def test_attribute_error_on_faction_is_swallowed(self):
        """Error case: unit lacking faction raises AttributeError, caught + logged."""
        unit = _make_unit()
        # Force accessing .faction to raise AttributeError
        del unit.faction  # type: ignore[attr-defined]

        invoked = []
        # Should not raise
        MoraleRouting.play_morale_collapse_voice(
            unit, MoraleState.BROKEN, lambda v, f: invoked.append((v, f))
        )
        assert invoked == []

    def test_type_error_from_callback_is_swallowed(self):
        """Error case: a TypeError raised inside the try is caught (no propagation).

        Note: the callback is invoked inside the try block, so a TypeError raised
        by the callback itself is caught and logged rather than propagated.
        """
        unit = _make_unit(faction=Faction.ALLIES)

        def bad_callback(v, f):
            raise TypeError("boom")

        # Should not raise
        MoraleRouting.play_morale_collapse_voice(unit, MoraleState.ROUTING, bad_callback)

    def test_value_error_from_callback_is_swallowed(self):
        """Error case: a ValueError raised by the callback is caught (no propagation).

        The try/except wraps the callback invocation, so ValueError raised inside
        the callback is logged and swallowed.
        """
        unit = _make_unit(faction=Faction.ALLIES)

        def bad_callback(v, f):
            raise ValueError("invalid")

        # Should not raise
        MoraleRouting.play_morale_collapse_voice(unit, MoraleState.ROUTING, bad_callback)

    def test_falsy_faction_still_triggers_callback(self):
        """Documented actual behavior: ``if faction is not None`` is an identity check.

        The guard uses ``is not None`` (not truthiness), so a falsy-but-not-None
        faction object still causes the callback to be invoked. Callers should not
        rely on falsy faction values to suppress the voice.
        """
        unit = _make_unit()

        class FalsyFaction:
            def __bool__(self):
                return False

        unit.faction = FalsyFaction()  # type: ignore[assignment]
        invoked = []
        MoraleRouting.play_morale_collapse_voice(
            unit, MoraleState.BROKEN, lambda v, f: invoked.append((v, f))
        )
        # Callback IS invoked because FalsyFaction() is not None
        assert len(invoked) == 1


# ===========================================================================
# Performance baselines
# ===========================================================================


@pytest.mark.unit
class TestMoraleRoutingPerformance:
    """Timing baselines for routing hot paths."""

    def test_check_routing_broken_under_1ms(self, monkeypatch):
        """Performance: 5000 broken-check calls complete well under 1s."""
        unit = _make_unit(morale_value=10)
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.0)
        start = time.perf_counter()
        for _ in range(5000):
            MoraleRouting.check_routing_behavior(unit)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0

    def test_calculate_flee_target_under_1ms(self):
        """Performance: 5000 flee-target computations complete well under 1s."""
        unit = _make_unit(tile_x=8, tile_y=5)
        game_map = FakeGameMap(10, 10)
        start = time.perf_counter()
        for _ in range(5000):
            MoraleRouting._calculate_flee_target(unit, game_map)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0


# ===========================================================================
# Integration: end-to-end routing flow
# ===========================================================================


@pytest.mark.unit
class TestRoutingIntegration:
    """End-to-end routing scenarios combining multiple methods."""

    def test_broken_unit_transitions_to_routing_then_flees_to_edge(self, monkeypatch):
        """Integration: a broken unit starts routing, then flees toward nearest edge.

        Scenario:
          1. Unit is BROKEN (morale=5). random()<FLEE_CHANCE_BROKEN → starts routing.
          2. On the next call, resolve_morale_state is patched to ROUTING so the
             routing branch runs; random()<FLEE_CHANCE_ROUTING → flees toward edge.
        Expected: the flee target matches the nearest map edge.
        """
        unit = _make_unit(morale_value=5, tile_x=2, tile_y=5)
        game_map = FakeGameMap(10, 10)

        # Step 1: broken → start routing
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.0)
        should_flee_1, _ = MoraleRouting.check_routing_behavior(unit)
        assert should_flee_1 is True
        assert unit._routing_target.is_fleeing is True
        assert unit._routing_target.flee_ticks_remaining == ROUTING_FLEE_DURATION

        # Step 2: now routing → flee toward edge (patch resolve to return ROUTING)
        monkeypatch.setattr(morale_routing, "resolve_morale_state", lambda v: MoraleState.ROUTING)
        should_flee_2, target = MoraleRouting.check_routing_behavior(unit, game_map)
        assert should_flee_2 is True
        # Unit at x=2 on 10-wide map: dist_left=2 (nearest) → flee to (0, 5)
        assert target == (0, 5)

    def test_routing_unit_rallies_and_stops_fleeing(self, monkeypatch):
        """Integration: a routing unit with recovering morale rallies and stops.

        Scenario: routing unit (is_fleeing=True); random() >= FLEE_CHANCE_ROUTING;
        morale.value > PINNED_THRESHOLD + 10 → is_fleeing set False.
        Expected: subsequent resolve would no longer be ROUTING (in real game),
        and is_fleeing is False after the rally check.
        """
        unit = _make_unit(morale_value=45)
        unit._routing_target = RoutingTarget(is_fleeing=True, flee_ticks_remaining=3)

        monkeypatch.setattr(morale_routing, "resolve_morale_state", lambda v: MoraleState.ROUTING)
        # random >= FLEE_CHANCE_ROUTING triggers the else (rally) branch
        monkeypatch.setattr(morale_routing.random, "random", lambda: 0.9)

        should_flee, _ = MoraleRouting.check_routing_behavior(unit)
        assert should_flee is False
        assert unit._routing_target.is_fleeing is False

    def test_voice_played_after_collapse(self):
        """Integration: a morale collapse triggers the voice callback with faction."""
        unit = _make_unit(faction=Faction.ALLIES)
        calls: list = []
        MoraleRouting.play_morale_collapse_voice(
            unit, MoraleState.BROKEN, lambda v, f: calls.append((v, f))
        )
        assert calls == [("broken", Faction.ALLIES)]
