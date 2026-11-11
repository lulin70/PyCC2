"""A* pathfinding over tile-based game maps.

Provides PathFinder, which computes optimal tile paths accounting for
octile movement cost and map passability constraints.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap


@dataclass(order=True)
class _Node:
    f_score: float = field(compare=True)
    g_score: float = field(compare=False)
    coord: TileCoord = field(compare=False)

    def __hash__(self) -> int:
        return hash((self.coord.x, self.coord.y))


@dataclass
class PathFinder:
    """Computes optimal paths between tiles using the A* algorithm."""

    OCTILE_COST: float = math.sqrt(2) - 1.0

    def find_path(
        self,
        start: TileCoord,
        goal: TileCoord,
        game_map: GameMap,
        max_iterations: int = 10000,
        unit: object | None = None,
    ) -> list[TileCoord] | None:
        """Find the lowest-cost tile path from start to goal using A*.

        Pass *unit* to make water passable for amphibious units.
        """
        if not game_map.is_within_bounds(start) or not game_map.is_within_bounds(goal):
            return None
        if not self._passable(start, game_map, unit) or not self._passable(goal, game_map, unit):
            return None
        if start == goal:
            return [start]

        open_list: list[_Node] = []
        closed_set: set[tuple[int, int]] = set()
        g_scores: dict[tuple[int, int], float] = {(start.x, start.y): 0.0}
        came_from: dict[tuple[int, int], tuple[int, int]] = {}

        h_start = self.octile_heuristic(start, goal)
        heapq.heappush(open_list, _Node(f_score=h_start, g_score=0.0, coord=start))

        iterations = 0
        while open_list and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_list)

            if current.coord == goal:
                path: list[TileCoord] = [goal]
                key = (goal.x, goal.y)
                while key in came_from:
                    key = came_from[key]
                    path.append(TileCoord(key[0], key[1]))
                path.reverse()
                return path

            cur_key = (current.coord.x, current.coord.y)
            if cur_key in closed_set:
                continue
            closed_set.add(cur_key)

            for neighbor in current.coord.neighbors_8:
                n_key = (neighbor.x, neighbor.y)
                if not game_map.is_within_bounds(neighbor):
                    continue
                if not self._passable(neighbor, game_map, unit):
                    continue
                if n_key in closed_set:
                    continue

                move_cost = self._get_movement_cost(current.coord, neighbor, game_map, unit)
                tentative_g = current.g_score + move_cost

                if n_key not in g_scores or tentative_g < g_scores[n_key]:
                    g_scores[n_key] = tentative_g
                    came_from[n_key] = cur_key
                    h = self.octile_heuristic(neighbor, goal)
                    f = tentative_g + h
                    heapq.heappush(open_list, _Node(f_score=f, g_score=tentative_g, coord=neighbor))

        return None

    @staticmethod
    def octile_heuristic(a: TileCoord, b: TileCoord) -> float:
        """Return the octile distance heuristic between two tiles."""
        dx = abs(a.x - b.x)
        dy = abs(a.y - b.y)
        sqrt2 = math.sqrt(2)
        return float(max(dx, dy) + (sqrt2 - 1.0) * min(dx, dy))

    def get_reachable_tiles(
        self,
        start: TileCoord,
        max_cost: float,
        game_map: GameMap,
        unit: object | None = None,
    ) -> set[TileCoord]:
        """Return all tiles reachable from start within the given movement cost budget."""
        reachable: set[TileCoord] = set()
        if not game_map.is_within_bounds(start) or not self._passable(start, game_map, unit):
            return reachable

        counter = 0
        open_list: list[tuple[float, int, TileCoord]] = [(0.0, counter, start)]
        visited: set[tuple[int, int]] = set()
        costs: dict[tuple[int, int], float] = {(start.x, start.y): 0.0}

        while open_list:
            current_cost, _, current = heapq.heappop(open_list)
            cur_key = (current.x, current.y)

            if cur_key in visited:
                continue
            visited.add(cur_key)
            reachable.add(current)

            for neighbor in current.neighbors_8:
                n_key = (neighbor.x, neighbor.y)
                if n_key in visited:
                    continue
                if not game_map.is_within_bounds(neighbor):
                    continue
                if not self._passable(neighbor, game_map, unit):
                    continue

                move_cost = self._get_movement_cost(current, neighbor, game_map, unit)
                new_cost = current_cost + move_cost

                if new_cost <= max_cost and (n_key not in costs or new_cost < costs[n_key]):
                    costs[n_key] = new_cost
                    counter += 1
                    heapq.heappush(open_list, (new_cost, counter, neighbor))

        return reachable

    def _get_movement_cost(
        self,
        from_coord: TileCoord,
        to_coord: TileCoord,
        game_map: GameMap,
        unit: object | None = None,
    ) -> float:
        terrain = game_map.get_terrain(to_coord)
        base_cost: float = terrain.movement_cost
        if base_cost == float("inf"):
            if not self._can_cross_water(to_coord, game_map, unit):
                return float("inf")
            base_cost = 2.0
        dx = abs(to_coord.x - from_coord.x)
        dy = abs(to_coord.y - from_coord.y)
        if dx + dy == 2:
            return base_cost * math.sqrt(2)
        return base_cost

    @staticmethod
    def _passable(coord: TileCoord, game_map: GameMap, unit: object | None) -> bool:
        """Return True when the unit may enter the tile."""
        checker = getattr(game_map, "is_passable_for", None)
        if checker is not None and unit is not None:
            return bool(checker(coord, unit))
        return bool(game_map.is_passable(coord))

    @staticmethod
    def _can_cross_water(coord: TileCoord, game_map: GameMap, unit: object | None) -> bool:
        """Return True for an amphibious unit on an amphibious-crossing map."""
        if unit is None or not getattr(unit, "is_amphibious", False):
            return False
        if not getattr(game_map, "amphibious_passable", False):
            return False
        return game_map.get_terrain(coord) == TerrainType.WATER
