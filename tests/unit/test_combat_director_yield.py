"""MC2-05 unit tests: yield negotiation in CombatDirector.process_movements.

Covers the design §4 unit layer:
- occupancy snapshot decision function (_movement_blocked):
  static blocker → yield; head-on swap → yield; two movers non-swap → pass;
  yield timeout → force pass; boundary at YIELD_TIMEOUT_TICKS.
- process_movements behavior with directly constructed _move_orders:
  yield increments + facing update, reset on tile commit, timeout valve,
  pass-through crossing semantics, dead units never block.
"""

from __future__ import annotations

import os
from collections import deque
from unittest.mock import Mock

import pytest

# Headless pygame (must precede any pygame import)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.entities.unit import Faction, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.services.combat_director import YIELD_TIMEOUT_TICKS, CombatDirector


class StubEventBus:
    def __init__(self):
        self.published = []

    def subscribe(self, event_type, handler):
        pass

    def publish(self, event):
        self.published.append(event)

    def publish_named(self, name, data):
        self.published.append({"name": name, "data": data})


class StubDisplayConfig:
    pass


def _make_director():
    bus = StubEventBus()
    return CombatDirector(event_bus=bus, display_config=StubDisplayConfig())


def _make_unit_with_real_position(unit_id, faction, tile_x, tile_y, pixel_offset=None, alive=True):
    """Create a mock unit with a real PositionComponent for accurate pixel math."""
    unit = Mock()
    unit.id = unit_id
    unit.name = unit_id
    unit.faction = faction
    unit.is_alive = alive
    unit.unit_type = UnitType.INFANTRY_SQUAD
    unit.movement_mode = "normal"

    pos = PositionComponent(tile_coord=TileCoord(tile_x, tile_y))
    if pixel_offset is not None:
        pos.set_pixel_offset(pixel_offset)
    unit.position = pos

    unit.update_garrison_status = Mock()
    unit.weapon = Mock()
    state_mock = Mock()
    state_mock.name = "READY"
    unit.weapon.state = state_mock
    return unit


def _make_game_map(width=30, height=30):
    game_map = Mock()
    game_map.width = width
    game_map.height = height
    game_map.tile_grid = Mock()
    game_map.tile_grid.__getitem__ = Mock(return_value=0)
    game_map.objectives = []
    return game_map


# A unit sitting 4 px before its target tile center (tile already switched by
# interpolation) is inside the "about to enter" arrival branch (move 4.8 px/tick).
APPROACH_OFFSET = Vec2(20.0, 24.0)
CENTER_OFFSET = Vec2(24.0, 24.0)


# ===========================================================================
# _movement_blocked decision function (occupancy snapshot consumer)
# ===========================================================================


@pytest.mark.unit
class TestMovementBlockedDecision:
    """Test the tile-entry blocking decision against constructed snapshots."""

    EMPTY_MOVING: dict = {}
    EMPTY_STATIC: dict = {}
    EMPTY_ORIGINS: dict = {}

    def _unit_at(self, tile_x, tile_y, yield_ticks=0):
        unit = _make_unit_with_real_position("u1", Faction.ALLIES, tile_x, tile_y)
        unit_order = {
            "path": deque([TileCoord(tile_x, tile_y)]),
            "from_tile": (tile_x - 1, tile_y),
        }
        if yield_ticks:
            unit_order["yield_ticks"] = yield_ticks
        dc = _make_director()
        dc._move_orders["u1"] = unit_order
        return dc, unit

    def test_static_occupant_blocks(self):
        dc, unit = self._unit_at(6, 5)
        blocked = dc._movement_blocked(
            unit,
            TileCoord(6, 5),
            self.EMPTY_MOVING,
            {(6, 5): "sentry"},
            self.EMPTY_ORIGINS,
        )
        assert blocked is True

    def test_head_on_swap_blocks(self):
        dc, unit = self._unit_at(6, 5)
        # Another mover departs from our target tile heading for our origin.
        blocked = dc._movement_blocked(
            unit,
            TileCoord(6, 5),
            {(6, 5): "u2"},
            {},
            {(6, 5): ("u2", (5, 5))},
        )
        assert blocked is True

    def test_swap_requires_mutual_origin_match(self):
        dc, unit = self._unit_at(6, 5)
        # Mover departs from our target but heads elsewhere (crossing) → pass.
        blocked = dc._movement_blocked(
            unit,
            TileCoord(6, 5),
            {(6, 5): "u2"},
            {},
            {(6, 5): ("u2", (9, 9))},
        )
        assert blocked is False

    def test_two_movers_never_block_each_other(self):
        dc, unit = self._unit_at(6, 5)
        blocked = dc._movement_blocked(
            unit,
            TileCoord(6, 5),
            {(6, 5): "u2"},
            {},
            {(7, 7): ("u2", (8, 8))},
        )
        assert blocked is False

    def test_timeout_forces_passage_past_static_block(self):
        dc, unit = self._unit_at(6, 5, yield_ticks=YIELD_TIMEOUT_TICKS + 1)
        blocked = dc._movement_blocked(
            unit,
            TileCoord(6, 5),
            self.EMPTY_MOVING,
            {(6, 5): "sentry"},
            self.EMPTY_ORIGINS,
        )
        assert blocked is False

    def test_timeout_boundary_still_blocks(self):
        dc, unit = self._unit_at(6, 5, yield_ticks=YIELD_TIMEOUT_TICKS)
        blocked = dc._movement_blocked(
            unit,
            TileCoord(6, 5),
            self.EMPTY_MOVING,
            {(6, 5): "sentry"},
            self.EMPTY_ORIGINS,
        )
        assert blocked is True


# ===========================================================================
# process_movements yield behavior
# ===========================================================================


@pytest.mark.unit
class TestProcessMovementsYield:
    """Test yield state transitions inside process_movements."""

    def test_yield_increments_and_keeps_facing_target(self):
        dc = _make_director()
        mover = _make_unit_with_real_position("m1", Faction.ALLIES, 6, 5, APPROACH_OFFSET)
        mover.position.facing_rad = 1.0  # non-default to prove re-aiming
        sentry = _make_unit_with_real_position("s1", Faction.AXIS, 6, 5)
        dc._move_orders["m1"] = {"path": deque([TileCoord(6, 5)]), "from_tile": (5, 5)}

        dc.process_movements([mover, sentry], _make_game_map())

        assert dc._move_orders["m1"]["yield_ticks"] == 1
        # Tile not committed: order survives with the path untouched.
        assert "m1" in dc._move_orders
        assert list(dc._move_orders["m1"]["path"]) == [TileCoord(6, 5)]
        assert mover.position.facing_rad != 1.0  # re-aimed toward the target
        mover.update_garrison_status.assert_not_called()

    def test_yield_resets_on_tile_commit(self):
        dc = _make_director()
        mover = _make_unit_with_real_position("m1", Faction.ALLIES, 6, 5, APPROACH_OFFSET)
        dc._move_orders["m1"] = {
            "path": deque([TileCoord(6, 5), TileCoord(7, 5)]),
            "yield_ticks": 5,
            "from_tile": (5, 5),
        }

        dc.process_movements([mover], _make_game_map())

        assert dc._move_orders["m1"]["yield_ticks"] == 0
        assert list(dc._move_orders["m1"]["path"]) == [TileCoord(7, 5)]
        # The committed tile becomes the next segment origin.
        assert dc._move_orders["m1"]["from_tile"] == (6, 5)
        assert mover.position.tile_coord == TileCoord(6, 5)

    def test_timeout_forces_entry_and_clears_yield(self):
        dc = _make_director()
        mover = _make_unit_with_real_position("m1", Faction.ALLIES, 6, 5, APPROACH_OFFSET)
        sentry = _make_unit_with_real_position("s1", Faction.AXIS, 6, 5)
        dc._move_orders["m1"] = {
            "path": deque([TileCoord(6, 5)]),
            "yield_ticks": YIELD_TIMEOUT_TICKS + 1,
        }

        dc.process_movements([mover, sentry], _make_game_map())

        assert "m1" not in dc._move_orders  # committed and path exhausted
        mover.update_garrison_status.assert_called_once()

    def test_dead_units_never_block(self):
        dc = _make_director()
        mover = _make_unit_with_real_position("m1", Faction.ALLIES, 6, 5, APPROACH_OFFSET)
        corpse = _make_unit_with_real_position("s1", Faction.AXIS, 6, 5, alive=False)
        dc._move_orders["m1"] = {"path": deque([TileCoord(6, 5)])}

        dc.process_movements([mover, corpse], _make_game_map())

        assert "m1" not in dc._move_orders

    def test_moving_units_pass_through_each_other(self):
        """CC2 crossing semantics: two movers are never mutually blocked."""
        dc = _make_director()
        # m1 about to enter (6,5); m2 already heading out toward (7,5).
        m1 = _make_unit_with_real_position("m1", Faction.ALLIES, 6, 5, APPROACH_OFFSET)
        m2 = _make_unit_with_real_position("m2", Faction.AXIS, 6, 5, Vec2(0.0, 24.0))
        dc._move_orders["m1"] = {"path": deque([TileCoord(6, 5)]), "from_tile": (5, 5)}
        dc._move_orders["m2"] = {"path": deque([TileCoord(7, 5)]), "from_tile": (6, 5)}

        dc.process_movements([m1, m2], _make_game_map())

        # m1 commits despite m2's body overlapping the target tile.
        assert "m1" not in dc._move_orders
        assert "m2" in dc._move_orders
