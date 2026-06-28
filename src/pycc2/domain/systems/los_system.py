"""Line of Sight (LOS) System - Bresenham ray casting with height blocking."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit


class LosStatus(Enum):
    """Line of sight status between two points."""

    CLEAR = auto()  # No obstacles
    BLOCKED_TERRAIN = auto()  # Blocked by terrain (wall, building)
    BLOCKED_HEIGHT = auto()  # Blocked by elevation difference (hill, building)
    PARTIAL = auto()  # Partially blocked (soft cover)
    OUT_OF_RANGE = auto()  # Beyond visual range


@dataclass(slots=True)
class LosResult:
    """Result of a LOS check."""

    status: LosStatus
    can_see: bool
    blocking_coord: TileCoord | None = None
    blocking_reason: str = ""
    distance_tiles: float = 0.0


class LOSSystem:
    """Line of Sight detection system using Bresenham's algorithm.

    Features:
    - Bresenham ray casting for precise line checking
    - Height-aware blocking (buildings block more than ground)
    - Elevation advantage (higher ground sees further)
    - Integration with AttackLineSystem for green/red display

    CC2 LOS Rules:
    - Buildings always block LOS (height 1-3)
    - Hills can block if significantly taller
    - Walls and hedges block infantry LOS
    - Units on higher elevation have +range bonus
    """

    DEFAULT_VISUAL_RANGE: int = 15  # tiles
    HEIGHT_BLOCK_THRESHOLD: float = 1.5  # height diff to block
    ELEVATION_BONUS_PER_LEVEL: float = 2.0  # extra range per elevation level

    def __init__(self, game_map: GameMap) -> None:
        """Initialize the LOS system bound to the given game map."""
        self._map = game_map
        self._cache: dict[tuple[int, int, int, int], LosResult] = {}
        self._cache_max_size: int = 1000

    def can_see(
        self,
        unit_a: Unit,
        unit_b: Unit,
        max_range: int | None = None,
    ) -> tuple[bool, LosResult]:
        """Check if unit_a can see unit_b.

        Args:
            unit_a: Observer unit
            unit_b: Target unit
            max_range: Maximum sight range in tiles (default from unit vision)

        Returns:
            Tuple of (can_see_bool, LosResult with details)

        """
        pos_a = TileCoord(
            int(unit_a.position.tile_coord.x),
            int(unit_a.position.tile_coord.y),
        )
        pos_b = TileCoord(
            int(unit_b.position.tile_coord.x),
            int(unit_b.position.tile_coord.y),
        )

        return self.check_los(pos_a, pos_b, max_range)

    def check_los(
        self,
        from_coord: TileCoord,
        to_coord: TileCoord,
        max_range: int | None = None,
    ) -> tuple[bool, LosResult]:
        """Check line of sight between two tile coordinates.

        Args:
            from_coord: Starting position
            to_coord: Target position
            max_range: Maximum distance (tiles)

        Returns:
            Tuple of (can_see, LosResult)

        """
        cache_key = (
            from_coord.x,
            from_coord.y,
            to_coord.x,
            to_coord.y,
        )

        cached = self._cache.get(cache_key)
        if cached:
            return cached.can_see, cached

        result = self._calculate_los(from_coord, to_coord, max_range)

        if len(self._cache) >= self._cache_max_size:
            self._cache.clear()

        self._cache[cache_key] = result
        return result.can_see, result

    def _calculate_los(
        self,
        from_coord: TileCoord,
        to_coord: TileCoord,
        max_range: int | None,
    ) -> LosResult:
        """Core LOS calculation using enhanced Bresenham algorithm."""
        dx = abs(to_coord.x - from_coord.x)
        dy = abs(to_coord.y - from_coord.y)
        distance = (dx * dx + dy * dy) ** 0.5

        effective_range: float = max_range or self.DEFAULT_VISUAL_RANGE

        from_elev = self._get_elevation(from_coord)
        to_elev = self._get_elevation(to_coord)
        elev_bonus = (from_elev - to_elev) * self.ELEVATION_BONUS_PER_LEVEL
        effective_range += max(0, elev_bonus)

        # Building floor bonus: higher floors provide better visibility
        building_bonus = self.get_building_visibility_bonus(
            from_coord.x,
            from_coord.y,
            self._map,
        )
        if building_bonus > 1.0:
            effective_range *= building_bonus

        if distance > effective_range:
            return LosResult(
                status=LosStatus.OUT_OF_RANGE,
                can_see=False,
                distance_tiles=distance,
                blocking_reason=f"Out of range ({distance:.1f} > {effective_range:.1f})",
            )

        # Window firing arc check: if shooter is inside a building, verify
        # the firing angle passes through a window
        from_terrain = self._map.get_terrain(from_coord)
        if from_terrain.name == "building_enterable":
            enhanced = self._map.get_enhanced_tile(from_coord.x, from_coord.y)
            building_type = ""
            if enhanced and "building_type" in enhanced:
                building_type = enhanced["building_type"]
            if not self.check_window_firing_arc(
                float(from_coord.x),
                float(from_coord.y),
                float(to_coord.x),
                float(to_coord.y),
                building_type,
                from_coord.x,
                from_coord.y,
            ):
                return LosResult(
                    status=LosStatus.BLOCKED_TERRAIN,
                    can_see=False,
                    blocking_coord=from_coord,
                    distance_tiles=distance,
                    blocking_reason="No window faces target direction",
                )

        line = self._bresenham_line_enhanced(from_coord, to_coord)
        from_height = self._get_total_height(from_coord)

        for i, coord in enumerate(line[1:-1], start=1):
            if not self._map.is_within_bounds(coord):
                continue

            terrain = self._map.get_terrain(coord)
            coord_height = self._get_total_height(coord)
            height_diff = coord_height - from_height

            if terrain.blocks_los:
                fraction_along = i / len(line) if len(line) > 1 else 0
                if fraction_along < 0.95:
                    return LosResult(
                        status=LosStatus.BLOCKED_TERRAIN,
                        can_see=False,
                        blocking_coord=coord,
                        distance_tiles=distance,
                        blocking_reason=f"Blocked by {terrain.name} at {coord}",
                    )

            if height_diff > self.HEIGHT_BLOCK_THRESHOLD:
                fraction_along = i / len(line) if len(line) > 1 else 0
                if fraction_along < 0.9:
                    return LosResult(
                        status=LosStatus.BLOCKED_HEIGHT,
                        can_see=False,
                        blocking_coord=coord,
                        distance_tiles=distance,
                        blocking_reason=f"Height blocked (+{height_diff:.1f} at {coord})",
                    )

            # Soft cover: hedges and dense vegetation reduce visibility
            # without completely blocking (e.g., Normandy bocage)
            _name = getattr(terrain, "name", "")
            if terrain is TerrainType.HEDGE or _name.lower() == "hedge":
                fraction_along = i / len(line) if len(line) > 1 else 0
                if fraction_along < 0.95:
                    return LosResult(
                        status=LosStatus.PARTIAL,
                        can_see=True,
                        blocking_coord=coord,
                        distance_tiles=distance,
                        blocking_reason=f"Partial cover ({terrain.name})",
                    )

        return LosResult(
            status=LosStatus.CLEAR,
            can_see=True,
            distance_tiles=distance,
        )

    @staticmethod
    def _bresenham_line_enhanced(
        from_coord: TileCoord,
        to_coord: TileCoord,
    ) -> list[TileCoord]:
        """Enhanced Supercover Bresenham's line algorithm.

        Returns all tile coordinates along the line from
        from_coord to to_coord, inclusive.

        Uses supercover variant to ensure all tiles touched by
        the line are included (prevents seeing through diagonal gaps).
        """
        x0, y0 = from_coord.x, from_coord.y
        x1, y1 = to_coord.x, to_coord.y
        points: list[TileCoord] = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0

        while True:
            points.append(TileCoord(x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            # Supercover: add intermediate tile on diagonal steps
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
            # Add extra point when moving diagonally to cover both tiles
            if x != x1 or y != y1:
                prev_point = points[-1]
                current_point = TileCoord(x, y)
                if prev_point.x != current_point.x and prev_point.y != current_point.y:
                    # Diagonal move: ensure we include the intermediate tile
                    inter_x = prev_point.x
                    inter_y = prev_point.y
                    inter_point = TileCoord(
                        inter_x + sx if abs(x1 - x0) >= abs(y1 - y0) else inter_x,
                        inter_y + sy if abs(y1 - y0) > abs(x1 - x0) else inter_y,
                    )
                    if inter_point != current_point and inter_point != prev_point:
                        points.append(inter_point)

        return points

    def _get_elevation(self, coord: TileCoord) -> float:
        """Get terrain elevation for coordinate from the map's elevation grid.

        Reads ``GameMap.elevation_grid`` (terrain altitude, 0-5 levels) rather
        than the legacy per-tile ``enhanced["elevation"]`` dict field, which is
        absent from real CC2-style maps.
        """
        if not self._map.is_within_bounds(coord):
            return 0.0
        return float(self._map.get_elevation(coord))

    def _get_building_height(self, coord: TileCoord) -> float:
        """Get building height for coordinate from the map's height grid.

        Reads ``GameMap.height_grid`` (building floors, 0-3) rather than the
        legacy per-tile ``enhanced["building_height"]`` dict field.
        """
        if not self._map.is_within_bounds(coord):
            return 0.0
        return float(self._map.get_building_height(coord))

    def _get_total_height(self, coord: TileCoord) -> float:
        """Total height = elevation + building height."""
        return self._get_elevation(coord) + self._get_building_height(coord)

    def get_blocking_terrain(
        self,
        from_coord: TileCoord,
        to_coord: TileCoord,
    ) -> list[TileCoord]:
        """Get list of coordinates that block LOS.

        Useful for visualization (showing why attack is red).
        """
        _, result = self.check_los(from_coord, to_coord)
        if result.blocking_coord:
            return [result.blocking_coord]
        return []

    def clear_cache(self) -> None:
        """Clear LOS calculation cache."""
        self._cache.clear()

    def integrate_to_attack_line_status(
        self,
        los_result: LosResult,
    ) -> str:
        """Convert LosResult to AttackLineStatus string.

        For integration with AttackLineSystem.
        """
        status_map = {
            LosStatus.CLEAR: "CAN_ATTACK",
            LosStatus.PARTIAL: "CAN_ATTACK",
            LosStatus.BLOCKED_TERRAIN: "BLOCKED",
            LosStatus.BLOCKED_HEIGHT: "BLOCKED",
            LosStatus.OUT_OF_RANGE: "OUT_OF_RANGE",
        }
        return status_map.get(los_result.status, "NO_TARGET")

    @staticmethod
    def get_building_visibility_bonus(tile_x: int, tile_y: int, game_map: GameMap) -> float:
        """Return LOS range multiplier for units inside a building.

        Higher buildings provide better visibility/LOS bonus for garrisoned units.

        Args:
            tile_x: X coordinate of the building tile
            tile_y: Y coordinate of the building tile
            game_map: Game map instance to query enhanced tile data

        Returns:
            LOS range multiplier based on floor count:
            - 1 floor = 1.0x (no bonus, but good cover)
            - 2 floors = 1.25x
            - 3 floors = 1.5x
            - 4 floors = 1.7x
            - 5+ floors = 2.0x

        """
        enhanced = game_map.get_enhanced_tile(tile_x, tile_y)
        if not enhanced or "building_floors" not in enhanced:
            return 1.0

        floors = int(enhanced["building_floors"])

        bonus_map = {
            1: 1.0,
            2: 1.25,
            3: 1.5,
            4: 1.7,
        }

        if floors >= 5:
            return 2.0
        return bonus_map.get(floors, 1.0)

    def check_window_firing_arc(
        self,
        shooter_x: float,
        shooter_y: float,
        target_x: float,
        target_y: float,
        building_type: str,
        tile_x: int,
        tile_y: int,
    ) -> bool:
        """Check if a unit inside a building can fire through a window toward the target.

        In CC2, units inside buildings can only fire through windows. The window
        positions define the firing arcs. If no window faces the target direction,
        the shot is blocked.

        Args:
            shooter_x, shooter_y: Shooter world position (pixels or tiles).
            target_x, target_y: Target world position.
            building_type: Building type string (e.g., 'normandy_farmhouse').
            tile_x, tile_y: Building tile coordinates.

        Returns:
            True if the firing angle passes through a window.

        """
        from pycc2.domain.value_objects.building_data import (
            BUILDING_WINDOWS,
            CC2BuildingType,
        )

        # Calculate firing angle from building center to target
        angle = math.atan2(target_y - shooter_y, target_x - shooter_x)

        # Look up building type enum from string
        bt = None
        for btype in CC2BuildingType:
            if btype.value == building_type:
                bt = btype
                break

        if bt is None:
            # Unknown building type: allow firing (no window restriction)
            return True

        windows = BUILDING_WINDOWS.get(bt, [])
        if not windows:
            # No windows defined: allow firing
            return True

        # Check if any window faces the target direction
        # Wall directions map to angle ranges (standard math convention):
        #   east  = 0 rad (right)
        #   north = -pi/2 rad (up in screen coords, but math-wise positive y is up)
        # Using screen coordinates where y increases downward:
        #   east  = 0, north = -pi/2, west = pi/-pi, south = pi/2
        for window in windows:
            wall = window["wall"]
            half_arc = math.pi / 4  # 45-degree arc per wall face

            if (
                wall == "east"
                and abs(self._angle_diff(angle, 0.0)) < half_arc
                or wall == "south"
                and abs(self._angle_diff(angle, math.pi / 2)) < half_arc
                or wall == "west"
                and abs(self._angle_diff(angle, math.pi)) < half_arc
                or wall == "north"
                and abs(self._angle_diff(angle, -math.pi / 2)) < half_arc
            ):
                return True

        return False  # No window faces the target direction

    @staticmethod
    def _angle_diff(a: float, b: float) -> float:
        """Compute the shortest angular difference between two angles."""
        diff = a - b
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        return diff
