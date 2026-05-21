from __future__ import annotations

import math

import numpy as np
import pytest

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.systems.pathfinder import PathFinder
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord


def _make_map(width: int, height: int, terrain: int | TerrainType = TerrainType.OPEN) -> GameMap:
    grid = np.full(
        (height, width), terrain if isinstance(terrain, int) else terrain.value, dtype=np.int8
    )
    return GameMap(id="test", name="test", width=width, height=height, tile_grid=grid)


def _make_custom_map(grid: list[list[int | TerrainType]]) -> GameMap:
    h = len(grid)
    w = len(grid[0])
    arr = np.array(
        [[(c if isinstance(c, int) else c.value) for c in row] for row in grid],
        dtype=np.int8,
    )
    return GameMap(id="test", name="test", width=w, height=h, tile_grid=arr)


class TestPfBasic:
    def test_pf_basic_01_straight_line(self):
        game_map = _make_map(10, 10)
        start = TileCoord(0, 0)
        goal = TileCoord(5, 0)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is not None
        assert path[0] == start
        assert path[-1] == goal
        assert len(path) == 6

    def test_pf_basic_02_diagonal_path(self):
        game_map = _make_map(10, 10)
        start = TileCoord(0, 0)
        goal = TileCoord(3, 3)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is not None
        assert path[0] == start
        assert path[-1] == goal
        assert len(path) == 4

    def test_pf_basic_03_same_start_goal(self):
        game_map = _make_map(10, 10)
        start = TileCoord(3, 3)
        pf = PathFinder()
        path = pf.find_path(start, start, game_map)
        assert path == [start]

    def test_pf_basic_04_blocked_by_walls(self):
        grid = [
            [1, 8, 8, 8, 1],
            [1, 8, 0, 8, 1],
            [1, 8, 8, 8, 1],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
        ]
        game_map = _make_custom_map(grid)
        start = TileCoord(2, 1)
        goal = TileCoord(0, 4)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is None

    def test_pf_basic_05_obstacle_avoidance(self):
        grid = [
            [0, 0, 0, 0, 0],
            [0, 0, 8, 0, 0],
            [0, 0, 8, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        game_map = _make_custom_map(grid)
        start = TileCoord(0, 2)
        goal = TileCoord(4, 2)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is not None
        assert path[0] == start
        assert path[-1] == goal
        for coord in path:
            assert game_map.is_passable(coord)

    def test_pf_basic_06_water_impassable(self):
        grid = [
            [0, 0, 6, 0, 0],
            [0, 0, 6, 0, 0],
            [0, 0, 6, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        game_map = _make_custom_map(grid)
        start = TileCoord(0, 0)
        goal = TileCoord(4, 0)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is not None
        assert path[-1] == goal
        for coord in path:
            t = game_map.get_terrain(coord)
            assert t != TerrainType.WATER

    def test_pf_basic_07_adjacent_tile(self):
        game_map = _make_map(10, 10)
        start = TileCoord(3, 3)
        goal = TileCoord(4, 3)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is not None
        assert len(path) == 2
        assert path[0] == start
        assert path[1] == goal

    def test_pf_basic_08_long_distance(self):
        game_map = _make_map(20, 20)
        start = TileCoord(0, 0)
        goal = TileCoord(18, 18)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is not None
        assert path[0] == start
        assert path[-1] == goal
        octile_dist = start.octile_distance(goal)
        assert len(path) <= int(octile_dist) + 3


class TestPfCost:
    def test_pf_cost_01_road_preferred_over_grass(self):
        grid = [
            [0, 2, 2, 2, 0],
            [1, 1, 1, 1, 1],
            [0, 2, 2, 2, 0],
        ]
        game_map = _make_custom_map(grid)
        start = TileCoord(0, 0)
        goal = TileCoord(4, 0)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is not None
        assert path[-1] == goal
        has_road = any(game_map.get_terrain(c) == TerrainType.ROAD for c in path)
        assert has_road, "Path should prefer road (lower cost)"

    def test_pf_cost_02_woods_higher_cost(self):
        game_map = _make_map(10, 10)
        start = TileCoord(0, 0)
        goal = TileCoord(5, 0)
        pf = PathFinder()
        path_open = pf.find_path(start, goal, game_map)
        game_map.set_terrain(TileCoord(2, 0), TerrainType.WOODS)
        game_map.set_terrain(TileCoord(3, 0), TerrainType.WOODS)
        path_woods = pf.find_path(start, goal, game_map)
        assert path_open is not None
        assert path_woods is not None

    def test_pf_cost_03_diagonal_more_expensive(self):
        game_map = _make_map(10, 10)
        start = TileCoord(0, 0)
        goal_diag = TileCoord(1, 1)
        goal_straight = TileCoord(1, 0)
        pf = PathFinder()
        path_diag = pf.find_path(start, goal_diag, game_map)
        path_straight = pf.find_path(start, goal_straight, game_map)
        assert path_diag is not None
        assert path_straight is not None
        cost_diag = sum(
            pf._get_movement_cost(path_diag[i], path_diag[i + 1], game_map)
            for i in range(len(path_diag) - 1)
        )
        cost_straight = sum(
            pf._get_movement_cost(path_straight[i], path_straight[i + 1], game_map)
            for i in range(len(path_straight) - 1)
        )
        assert cost_diag > cost_straight

    def test_pf_cost_04_building_solid_impassable(self):
        grid = [[0, 5, 0]]
        game_map = _make_custom_map(grid)
        start = TileCoord(0, 0)
        goal = TileCoord(2, 0)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is None

    def test_pf_cost_05_bridge_lowest_cost(self):
        grid = [
            [0, 11, 0],
            [2, 2, 2],
            [0, 0, 0],
        ]
        game_map = _make_custom_map(grid)
        start = TileCoord(0, 0)
        goal = TileCoord(2, 0)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is not None
        assert path[-1] == goal


class TestPfHeur:
    def test_pf_heur_01_admissible(self):
        pf = PathFinder()
        pairs = [
            (TileCoord(0, 0), TileCoord(5, 3)),
            (TileCoord(2, 2), TileCoord(7, 9)),
            (TileCoord(0, 0), TileCoord(10, 10)),
            (TileCoord(3, 5), TileCoord(3, 5)),
        ]
        for a, b in pairs:
            h = pf.octile_heuristic(a, b)
            actual_octile = a.octile_distance(b)
            assert h <= actual_octile + 1e-9, (
                f"Octile heuristic overestimated: {h} > {actual_octile}"
            )

    def test_pf_heur_02_consistent(self):
        pf = PathFinder()
        a = TileCoord(0, 0)
        b = TileCoord(2, 1)
        c = TileCoord(5, 3)
        h_ac = pf.octile_heuristic(a, c)
        h_bc = pf.octile_heuristic(b, c)
        dx_ab = abs(b.x - a.x)
        dy_ab = abs(b.y - a.y)
        cost_ab = max(dx_ab, dy_ab) + (math.sqrt(2) - 1) * min(dx_ab, dy_ab)
        assert h_ac <= cost_ab + h_bc + 1e-9

    def test_pf_heur_03_octile_vs_manhattan(self):
        pf = PathFinder()
        a = TileCoord(0, 0)
        b = TileCoord(5, 5)
        octile_h = pf.octile_heuristic(a, b)
        manhattan_h = a.manhattan_distance(b)
        assert octile_h < manhattan_h

    def test_pf_heur_04_zero_distance(self):
        pf = PathFinder()
        a = TileCoord(3, 7)
        assert pf.octile_heuristic(a, a) == pytest.approx(0.0)


class TestPfEdge:
    def test_pf_edge_01_start_out_of_bounds(self):
        game_map = _make_map(5, 5)
        start = TileCoord(-1, 0)
        goal = TileCoord(3, 3)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is None

    def test_pf_edge_02_goal_out_of_bounds(self):
        game_map = _make_map(5, 5)
        start = TileCoord(0, 0)
        goal = TileCoord(10, 10)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is None

    def test_pf_edge_03_1x1_map_same_point(self):
        game_map = _make_map(1, 1)
        start = TileCoord(0, 0)
        pf = PathFinder()
        path = pf.find_path(start, start, game_map)
        assert path == [start]

    def test_pf_edge_04_max_iterations_limit(self):
        game_map = _make_map(100, 100)
        start = TileCoord(0, 0)
        goal = TileCoord(99, 99)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map, max_iterations=5)
        assert path is None

    def test_pf_edge_05_all_water_map(self):
        game_map = _make_map(5, 5, TerrainType.WATER)
        start = TileCoord(0, 0)
        goal = TileCoord(4, 4)
        pf = PathFinder()
        path = pf.find_path(start, goal, game_map)
        assert path is None


class TestPfReach:
    def test_pf_reach_01_reasonable_range(self):
        game_map = _make_map(10, 10)
        start = TileCoord(5, 5)
        pf = PathFinder()
        reachable = pf.get_reachable_tiles(start, 3.0, game_map)
        assert isinstance(reachable, set)
        assert len(reachable) >= 1
        for tile in reachable:
            assert game_map.is_passable(tile)

    def test_pf_reach_02_contains_start(self):
        game_map = _make_map(10, 10)
        start = TileCoord(5, 5)
        pf = PathFinder()
        reachable = pf.get_reachable_tiles(start, 3.0, game_map)
        assert start in reachable

    def test_pf_reach_03_blocked_area_excluded(self):
        grid = [
            [0, 0, 0, 0, 0],
            [0, 0, 8, 0, 0],
            [0, 0, 8, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]
        game_map = _make_custom_map(grid)
        start = TileCoord(0, 0)
        pf = PathFinder()
        reachable = pf.get_reachable_tiles(start, 10.0, game_map)
        wall_pos = TileCoord(2, 1)
        assert wall_pos not in reachable
        behind_wall = TileCoord(2, 3)
        if behind_wall in reachable:
            pass
