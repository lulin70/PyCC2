"""Unit tests for ``FogOfWar.reveal_from_observers``.

Covers multi-observer union (a later observer must not erase an earlier one's
tiles), correct newly-revealed bookkeeping, and the three-state transition
visible -> explored -> hidden-never-seen.
"""

from __future__ import annotations

import math

import numpy as np

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.systems.fog_of_war import FogOfWar, TileVisibility
from pycc2.domain.value_objects.tile_coord import TileCoord


def make_map(width: int = 20, height: int = 20) -> GameMap:
    """Open terrain map so rays are limited only by vision range."""
    grid = np.zeros((height, width), dtype=np.int8)
    return GameMap(id="reveal", name="Reveal Map", width=width, height=height, tile_grid=grid)


class TestMultiObserverUnion:
    def test_both_observers_reveal_their_area(self) -> None:
        fow = FogOfWar(20, 20)
        game_map = make_map()
        revealed = fow.reveal_from_observers(
            [
                (TileCoord(3, 3), 4, math.tau, 0.0),
                (TileCoord(16, 16), 4, math.tau, 0.0),
            ],
            game_map,
            0,
        )
        assert fow.is_visible(TileCoord(3, 3))
        assert fow.is_visible(TileCoord(16, 16))
        assert fow.is_visible(TileCoord(6, 3))
        assert TileCoord(3, 3) in revealed
        assert TileCoord(16, 16) in revealed

    def test_second_observer_does_not_erase_first(self) -> None:
        fow = FogOfWar(20, 20)
        game_map = make_map()
        fow.reveal_from_observers(
            [
                (TileCoord(2, 2), 5, math.tau, 0.0),
                (TileCoord(17, 17), 2, math.tau, 0.0),
            ],
            game_map,
            0,
        )
        # Small second cone must not clear the wide first cone.
        assert fow.is_visible(TileCoord(2, 2))
        assert fow.is_visible(TileCoord(5, 2))
        assert fow.is_visible(TileCoord(17, 17))

    def test_far_tiles_stay_hidden(self) -> None:
        fow = FogOfWar(20, 20)
        game_map = make_map()
        fow.reveal_from_observers([(TileCoord(5, 5), 2, math.tau, 0.0)], game_map, 0)
        assert fow.get_visibility(TileCoord(18, 18)) == TileVisibility.HIDDEN


class TestThreeStateTransition:
    def test_visible_to_explored_when_observer_leaves(self) -> None:
        fow = FogOfWar(20, 20)
        game_map = make_map()
        fow.reveal_from_observers([(TileCoord(4, 4), 4, math.tau, 0.0)], game_map, 0)
        assert fow.get_visibility(TileCoord(4, 4)) == TileVisibility.VISIBLE

        fow.reveal_from_observers([(TileCoord(15, 15), 3, math.tau, 0.0)], game_map, 5)
        assert fow.get_visibility(TileCoord(4, 4)) == TileVisibility.EXPLORED
        assert fow.is_explored(TileCoord(4, 4))
        assert not fow.is_visible(TileCoord(4, 4))
        assert fow.get_visibility(TileCoord(15, 15)) == TileVisibility.VISIBLE

    def test_explored_never_returns_to_hidden(self) -> None:
        fow = FogOfWar(20, 20)
        game_map = make_map()
        fow.reveal_from_observers([(TileCoord(4, 4), 4, math.tau, 0.0)], game_map, 0)
        explored = set(fow.get_visible_tiles())
        fow.reveal_from_observers([(TileCoord(18, 18), 1, math.tau, 0.0)], game_map, 5)
        for coord in explored:
            assert not fow.is_hidden(coord)

    def test_newly_revealed_excludes_still_visible_tiles(self) -> None:
        fow = FogOfWar(20, 20)
        game_map = make_map()
        fow.reveal_from_observers([(TileCoord(6, 6), 4, math.tau, 0.0)], game_map, 0)
        revealed_again = fow.reveal_from_observers(
            [(TileCoord(6, 6), 4, math.tau, 0.0)], game_map, 5
        )
        assert revealed_again == set()
