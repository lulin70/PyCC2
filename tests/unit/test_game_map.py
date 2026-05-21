from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MAPS_DIR = PROJECT_ROOT / "data" / "maps"
TUTORIAL_JSON = MAPS_DIR / "tutorial.json"


def _make_test_map(width: int = 10, height: int = 10, fill: int = 0) -> GameMap:
    grid = np.full((height, width), fill, dtype=np.int8)
    return GameMap(id="test", name="Test", width=width, height=height, tile_grid=grid)


class TestBresenhamLine:
    def test_horizontal_line(self):
        line = GameMap._bresenham_line(TileCoord(0, 0), TileCoord(5, 0))
        assert len(line) == 6
        assert [c.x for c in line] == [0, 1, 2, 3, 4, 5]
        assert all(c.y == 0 for c in line)

    def test_vertical_line(self):
        line = GameMap._bresenham_line(TileCoord(0, 0), TileCoord(0, 5))
        assert len(line) == 6
        assert all(c.x == 0 for c in line)
        assert [c.y for c in line] == [0, 1, 2, 3, 4, 5]

    def test_diagonal_line(self):
        line = GameMap._bresenham_line(TileCoord(0, 0), TileCoord(5, 5))
        assert len(line) == 6
        assert [(c.x, c.y) for c in line] == [(i, i) for i in range(6)]

    def test_anti_diagonal_line(self):
        line = GameMap._bresenham_line(TileCoord(0, 5), TileCoord(5, 0))
        assert len(line) == 6
        assert [(c.x, c.y) for c in line] == [(i, 5 - i) for i in range(6)]

    def test_single_point(self):
        line = GameMap._bresenham_line(TileCoord(0, 0), TileCoord(0, 0))
        assert len(line) == 1
        assert line[0] == TileCoord(0, 0)

    def test_general_slope(self):
        line = GameMap._bresenham_line(TileCoord(0, 0), TileCoord(7, 3))
        assert len(line) >= 4
        assert line[0] == TileCoord(0, 0)
        assert line[-1] == TileCoord(7, 3)

    def test_contains_both_endpoints(self):
        a, b = TileCoord(2, 3), TileCoord(8, 9)
        line = GameMap._bresenham_line(a, b)
        assert line[0] == a
        assert line[-1] == b

    def test_symmetry(self):
        a, b = TileCoord(1, 2), TileCoord(7, 8)
        ab = GameMap._bresenham_line(a, b)
        ba = GameMap._bresenham_line(b, a)
        assert set((c.x, c.y) for c in ab) == set((c.x, c.y) for c in ba)


class TestLineOfSight:
    def test_clear_los_open_terrain(self):
        m = _make_test_map(10, 10, TerrainType.OPEN.value)
        assert m.has_line_of_sight(TileCoord(0, 0), TileCoord(9, 9)) is True

    def test_blocked_by_wall(self):
        m = _make_test_map(10, 10, TerrainType.OPEN.value)
        m.set_terrain(TileCoord(5, 5), TerrainType.WALL)
        assert m.has_line_of_sight(TileCoord(0, 0), TileCoord(9, 9)) is False

    def test_blocked_by_woods(self):
        m = _make_test_map(10, 10, TerrainType.OPEN.value)
        m.set_terrain(TileCoord(3, 2), TerrainType.WOODS)
        assert m.has_line_of_sight(TileCoord(0, 0), TileCoord(6, 4)) is False

    def test_adjacent_tiles_always_true(self):
        m = _make_test_map(10, 10, TerrainType.WALL.value)
        assert m.has_line_of_sight(TileCoord(3, 3), TileCoord(3, 4)) is True

    def test_blocking_at_endpoint_adjacent_is_true(self):
        m = _make_test_map(10, 10, TerrainType.OPEN.value)
        m.set_terrain(TileCoord(5, 5), TerrainType.BUILDING_SOLID)
        assert m.has_line_of_sight(TileCoord(4, 5), TileCoord(5, 5)) is True

    def test_out_of_bounds_returns_false(self):
        m = _make_test_map(5, 5, TerrainType.OPEN.value)
        assert m.has_line_of_sight(TileCoord(0, 0), TileCoord(10, 10)) is False

    def test_same_coord_returns_true(self):
        m = _make_test_map(10, 10, TerrainType.WALL.value)
        assert m.has_line_of_sight(TileCoord(3, 3), TileCoord(3, 3)) is True


class TestMapLoading:
    def test_from_json_loads_successfully(self):
        m = GameMap.from_json(TUTORIAL_JSON)
        assert isinstance(m, GameMap)
        assert m.id == "tutorial"

    def test_dimensions_correct(self):
        m = GameMap.from_json(TUTORIAL_JSON)
        # Updated for Phase A1 map expansion (16x16 → 24x20)
        assert m.width == 24
        assert m.height == 20
        assert m.tile_grid.shape == (20, 24)

    def test_objectives_count(self):
        m = GameMap.from_json(TUTORIAL_JSON)
        assert len(m.objectives) == 1
        obj = m.objectives[0]
        assert obj.id == "obj1"
        assert obj.name == "Bridge"
        # Updated for Phase A1 map expansion (coordinates scaled from 16x16 to 24x20)
        assert obj.position == TileCoord(12, 10)

    def test_spawn_points_correct(self):
        m = GameMap.from_json(TUTORIAL_JSON)
        assert len(m.spawn_points) == 2
        allies = m.get_spawn_point("allies")
        axis = m.get_spawn_point("axis")
        assert allies is not None
        # Updated for Phase A1 map expansion (coordinates scaled)
        assert allies.position == TileCoord(3, 10)
        assert axis is not None
        assert axis.position == TileCoord(21, 10)


class TestTerrainAccess:
    def test_get_terrain_returns_correct_type(self):
        m = _make_test_map()
        m.set_terrain(TileCoord(3, 3), TerrainType.WOODS)
        assert m.get_terrain(TileCoord(3, 3)) == TerrainType.WOODS

    def test_set_terrain_modifies_grid(self):
        m = _make_test_map(fill=TerrainType.GRASS.value)
        m.set_terrain(TileCoord(0, 0), TerrainType.ROAD)
        assert m.get_terrain(TileCoord(0, 0)) == TerrainType.ROAD

    def test_is_passable_varies_by_terrain(self):
        m = _make_test_map()
        m.set_terrain(TileCoord(1, 1), TerrainType.OPEN)
        m.set_terrain(TileCoord(2, 2), TerrainType.WATER)
        m.set_terrain(TileCoord(3, 3), TerrainType.BUILDING_SOLID)
        assert m.is_passable(TileCoord(1, 1)) is True
        assert m.is_passable(TileCoord(2, 2)) is False
        assert m.is_passable(TileCoord(3, 3)) is False

    def test_is_within_bounds(self):
        m = _make_test_map(8, 6)
        assert m.is_within_bounds(TileCoord(0, 0)) is True
        assert m.is_within_bounds(TileCoord(7, 5)) is True
        assert m.is_within_bounds(TileCoord(-1, 0)) is False
        assert m.is_within_bounds(TileCoord(8, 0)) is False
        assert m.is_within_bounds(TileCoord(0, 6)) is False

    def test_get_terrain_after_json_load(self):
        m = GameMap.from_json(TUTORIAL_JSON)
        # Test center of original map area (accounting for expansion offset)
        # Original 16x16 map centered in new 24x20: offset is (4, 2)
        t = m.get_terrain(TileCoord(4, 2))  # Approximate original (0,0) position
        assert isinstance(t, TerrainType)
        # After expansion, this should still be a valid terrain type
        assert t in [TerrainType.GRASS, TerrainType.WOODS, TerrainType.ROUGH]

    def test_invalid_coord_graceful_handling(self):
        m = _make_test_map(5, 5)
        with pytest.raises(IndexError):
            _ = m.get_terrain(TileCoord(10, 10))
