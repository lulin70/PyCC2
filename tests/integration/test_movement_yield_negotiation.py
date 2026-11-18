"""MC2-05 integration tests: yield negotiation over simulated movement ticks.

Uses real Unit entities + real GameMap and drives CombatDirector.process_movements
with directly constructed _move_orders (same convention as the unit layer):
- head-on swap: both units yield, then the timeout valve lets both arrive
  (no deadlock, no permanent stall);
- static blocker: the follower yields behind it, then forces through;
- two movers that are not swapping pass through each other (CC2 semantics).
"""

from __future__ import annotations

import os
from collections import deque

import numpy as np
import pytest

# Headless pygame (must precede any pygame import)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.services.combat_director import CombatDirector

TILE_CENTER = Vec2(24.0, 24.0)


def _make_unit(unit_id: str, faction: Faction, tile_x: int, tile_y: int) -> Unit:
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y), pixel_offset=Vec2.zero()),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def game_map() -> GameMap:
    grid = np.zeros((16, 16), dtype=np.int8)
    return GameMap(id="yield_test", name="Yield Test Map", width=16, height=16, tile_grid=grid)


@pytest.fixture
def director() -> CombatDirector:
    return CombatDirector(event_bus=object(), display_config=object())  # type: ignore[arg-type]


def _place_at_tile_center(unit: Unit, tile_x: int, tile_y: int) -> None:
    unit.position.tile_coord = TileCoord(tile_x, tile_y)
    unit.position.set_pixel_offset(Vec2(24.0, 24.0))


class TestHeadOnSwapYields:
    """Two units swapping target tiles: yield → timeout → both arrive."""

    def test_swap_yields_then_both_arrive(self, director, game_map):
        ally = _make_unit("ally_1", Faction.ALLIES, 5, 5)
        axis = _make_unit("axis_1", Faction.AXIS, 6, 5)
        _place_at_tile_center(ally, 5, 5)
        _place_at_tile_center(axis, 6, 5)

        director._move_orders["ally_1"] = {
            "path": deque([TileCoord(6, 5)]),
            "from_tile": (5, 5),
        }
        director._move_orders["axis_1"] = {
            "path": deque([TileCoord(5, 5)]),
            "from_tile": (6, 5),
        }

        units = [ally, axis]
        for _tick in range(12):
            director.process_movements(units, game_map)

        # Negotiation active: both sides are yielding, neither has committed.
        assert director._move_orders["ally_1"]["yield_ticks"] >= 1
        assert director._move_orders["axis_1"]["yield_ticks"] >= 1
        assert list(director._move_orders["ally_1"]["path"]) == [TileCoord(6, 5)]
        assert list(director._move_orders["axis_1"]["path"]) == [TileCoord(5, 5)]

        # The 90-tick valve releases the deadlock: both arrive, orders clear.
        for _tick in range(200):
            director.process_movements(units, game_map)
        assert "ally_1" not in director._move_orders
        assert "axis_1" not in director._move_orders
        assert ally.position.tile_coord == TileCoord(6, 5)
        assert axis.position.tile_coord == TileCoord(5, 5)


class TestStaticBlockerYield:
    """A stationary unit blocks tile entry; the follower yields then passes."""

    def test_follower_yields_behind_static_unit(self, director, game_map):
        mover = _make_unit("mover_1", Faction.ALLIES, 5, 5)
        sentry = _make_unit("sentry_1", Faction.AXIS, 6, 5)
        _place_at_tile_center(mover, 5, 5)
        _place_at_tile_center(sentry, 6, 5)

        director._move_orders["mover_1"] = {
            "path": deque([TileCoord(6, 5), TileCoord(7, 5)]),
            "from_tile": (5, 5),
        }

        units = [mover, sentry]
        for _tick in range(20):
            director.process_movements(units, game_map)

        # Yielding in front of the sentry: no segment committed yet. Note the
        # interpolated tile_coord follows the body across the tile boundary,
        # so "not committed" is proven by the untouched two-tile path and by
        # the pixel position freezing short of the target tile center.
        order = director._move_orders["mover_1"]
        assert order["yield_ticks"] >= 10
        assert list(order["path"]) == [TileCoord(6, 5), TileCoord(7, 5)]
        assert mover.position.pixel_offset.x < 24.0

        # Timeout valve forces passage; the full path still completes.
        for _tick in range(200):
            director.process_movements(units, game_map)
        assert "mover_1" not in director._move_orders
        assert mover.position.tile_coord == TileCoord(7, 5)
        assert sentry.position.tile_coord == TileCoord(6, 5)


class TestMoversPassThrough:
    """CC2 crossing semantics: non-swap movers never block each other."""

    def test_following_movers_arrive_without_stall(self, director, game_map):
        leader = _make_unit("leader_1", Faction.ALLIES, 5, 5)
        follower = _make_unit("follower_1", Faction.ALLIES, 6, 5)
        _place_at_tile_center(leader, 5, 5)
        _place_at_tile_center(follower, 6, 5)

        director._move_orders["leader_1"] = {
            "path": deque([TileCoord(6, 5)]),
            "from_tile": (5, 5),
        }
        director._move_orders["follower_1"] = {
            "path": deque([TileCoord(7, 5)]),
            "from_tile": (6, 5),
        }

        units = [leader, follower]
        for _tick in range(20):
            director.process_movements(units, game_map)

        # Both arrive within a few ticks — no 90-tick yield stall.
        assert "leader_1" not in director._move_orders
        assert "follower_1" not in director._move_orders
        assert leader.position.tile_coord == TileCoord(6, 5)
        assert follower.position.tile_coord == TileCoord(7, 5)
