from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap


class TileVisibility(IntEnum):
    HIDDEN = 0
    EXPLORED = 1
    VISIBLE = 2


@dataclass
class FogOfWar:
    RAY_COUNT: int = 36
    UPDATE_INTERVAL_TICKS: int = 5

    def __init__(self, map_width: int, map_height: int) -> None:
        self.width = map_width
        self.height = map_height
        self.visibility_grid: list[list[int]] = [
            [TileVisibility.HIDDEN] * map_width for _ in range(map_height)
        ]

    def update_visibility(
        self,
        observer_pos: TileCoord,
        vision_range: int,
        vision_angle: float,
        facing_direction: float,
        game_map: GameMap,
        current_tick: int = 0,
        environment=None,
    ) -> set[TileCoord]:
        effective_range = vision_range
        if environment is not None:
            effective_range = max(1, int(vision_range * environment.get_vision_multiplier()))
            ox, oy = observer_pos.x, observer_pos.y
            if environment.is_tile_illuminated(ox, oy):
                effective_range = max(effective_range, vision_range)

        cleared = self.clear_current_visibility()
        newly_revealed: set[TileCoord] = set()

        if effective_range <= 0:
            self._set_visible(observer_pos)
            if observer_pos not in cleared:
                newly_revealed.add(observer_pos)
            return newly_revealed

        start_angle = facing_direction - vision_angle / 2
        end_angle = facing_direction + vision_angle / 2

        for i in range(self.RAY_COUNT):
            if self.RAY_COUNT == 1:
                ray_angle = facing_direction
            else:
                t = i / (self.RAY_COUNT - 1)
                ray_angle = start_angle + t * (end_angle - start_angle)

            ray_tiles = self._cast_ray(
                origin=observer_pos,
                direction_rad=ray_angle,
                max_range=effective_range,
                game_map=game_map,
            )

            for tile in ray_tiles:
                self._set_visible(tile)
                if tile not in cleared:
                    newly_revealed.add(tile)

        return newly_revealed

    def _cast_ray(
        self,
        origin: TileCoord,
        direction_rad: float,
        max_range: int,
        game_map: GameMap,
    ) -> list[TileCoord]:
        tiles: list[TileCoord] = []

        dx = math.cos(direction_rad)
        dy = math.sin(direction_rad)

        step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
        step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)

        t_delta_x = abs(1 / dx) if abs(dx) > 1e-10 else float("inf")

        t_delta_y = abs(1 / dy) if abs(dy) > 1e-10 else float("inf")

        x = float(origin.x)
        y = float(origin.y)

        if step_x > 0:
            t_max_x = (
                (math.floor(x) + 1 - x) * t_delta_x if t_delta_x != float("inf") else float("inf")
            )
        elif step_x < 0:
            t_max_x = (x - math.floor(x)) * t_delta_x if t_delta_x != float("inf") else float("inf")
        else:
            t_max_x = float("inf")

        if step_y > 0:
            t_max_y = (
                (math.floor(y) + 1 - y) * t_delta_y if t_delta_y != float("inf") else float("inf")
            )
        elif step_y < 0:
            t_max_y = (y - math.floor(y)) * t_delta_y if t_delta_y != float("inf") else float("inf")
        else:
            t_max_y = float("inf")

        cx, cy = origin.x, origin.y
        tiles.append(TileCoord(cx, cy))

        for _ in range(max_range):
            if t_max_x < t_max_y:
                t_max_x += t_delta_x
                cx += step_x
            else:
                t_max_y += t_delta_y
                cy += step_y

            coord = TileCoord(cx, cy)

            if not game_map.is_within_bounds(coord):
                break

            tiles.append(coord)

            terrain = game_map.get_terrain(coord)
            if terrain.blocks_los:
                break

        return tiles

    def is_visible(self, coord: TileCoord) -> bool:
        return (
            0 <= coord.x < self.width
            and 0 <= coord.y < self.height
            and self.visibility_grid[coord.y][coord.x] == TileVisibility.VISIBLE
        )

    def is_explored(self, coord: TileCoord) -> bool:
        return (
            0 <= coord.x < self.width
            and 0 <= coord.y < self.height
            and self.visibility_grid[coord.y][coord.x] >= TileVisibility.EXPLORED
        )

    def is_hidden(self, coord: TileCoord) -> bool:
        return (
            0 <= coord.x < self.width
            and 0 <= coord.y < self.height
            and self.visibility_grid[coord.y][coord.x] == TileVisibility.HIDDEN
        )

    def get_visibility(self, coord: TileCoord) -> TileVisibility:
        if 0 <= coord.x < self.width and 0 <= coord.y < self.height:
            return TileVisibility(self.visibility_grid[coord.y][coord.x])
        return TileVisibility.HIDDEN

    def reset(self) -> None:
        self.visibility_grid = [[TileVisibility.HIDDEN] * self.width for _ in range(self.height)]

    def clear_current_visibility(self) -> set[TileCoord]:
        cleared: set[TileCoord] = set()
        for y in range(self.height):
            for x in range(self.width):
                if self.visibility_grid[y][x] == TileVisibility.VISIBLE:
                    self.visibility_grid[y][x] = TileVisibility.EXPLORED
                    cleared.add(TileCoord(x, y))
        return cleared

    def get_visible_tiles(self) -> set[TileCoord]:
        visible: set[TileCoord] = set()
        for y in range(self.height):
            for x in range(self.width):
                if self.visibility_grid[y][x] == TileVisibility.VISIBLE:
                    visible.add(TileCoord(x, y))
        return visible

    def get_explored_count(self) -> int:
        count = 0
        for y in range(self.height):
            for x in range(self.width):
                if self.visibility_grid[y][x] >= TileVisibility.EXPLORED:
                    count += 1
        return count

    def get_hidden_count(self) -> int:
        count = 0
        for y in range(self.height):
            for x in range(self.width):
                if self.visibility_grid[y][x] == TileVisibility.HIDDEN:
                    count += 1
        return count

    def _set_visible(self, coord: TileCoord) -> None:
        if 0 <= coord.x < self.width and 0 <= coord.y < self.height:
            self.visibility_grid[coord.y][coord.x] = TileVisibility.VISIBLE
