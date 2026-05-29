"""Terrain-related domain systems: DestructibleTerrain (C8), RiverCrossingSystem (C10), RoadSystem (C11)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DestructibleTerrain:
    """
    Destructible terrain system.

    Buildings/structures have HP.
    When HP depleted -> becomes rubble tile.
    Rubble provides less cover (-50%).
    """

    _terrain_hp: dict[tuple[int, int], int] = field(init=False)
    _max_hp_defaults: dict[str, int] = field(init=False)
    _rubble_tiles: set[tuple[int, int]] = field(init=False)

    def __post_init__(self):
        self._terrain_hp = {}
        self._max_hp_defaults = {
            'building': 100,
            'bridge': 150,
            'wall': 30,
            'tree': 15,
        }
        self._rubble_tiles = set()

    def initialize_terrain(
        self,
        position: tuple[int, int],
        terrain_type: str,
    ) -> None:
        """Initialize terrain HP based on type."""
        max_hp = self._max_hp_defaults.get(terrain_type, 50)
        self._terrain_hp[position] = max_hp

    def apply_damage(
        self,
        position: tuple[int, int],
        damage: int,
    ) -> bool:
        """
        Apply damage to terrain.

        Returns:
            True if terrain destroyed
        """
        if position not in self._terrain_hp:
            return False

        self._terrain_hp[position] -= damage

        if self._terrain_hp[position] <= 0:
            self._rubble_tiles.add(position)
            del self._terrain_hp[position]
            return True

        return False

    def is_rubble(self, position: tuple[int, int]) -> bool:
        """Check if tile is rubble."""
        return position in self._rubble_tiles

    def get_terrain_hp(self, position: tuple[int, int]) -> int:
        """Get remaining HP (0 if destroyed/rubble)."""
        return self._terrain_hp.get(position, 0)


@dataclass
class RiverCrossingSystem:
    """
    River crossing mechanics.

    Water tiles: movement_cost = 2.5x
    Crossing increases exposure (+30%).
    Some shallow points: cost = 1.5x
    """

    WATER_MOVEMENT_MULTIPLIER: float = 2.5
    SHALLOW_MULTIPLIER: float = 1.5
    EXPOSURE_BONUS: float = 0.3  # +30% exposure when in water

    _water_tiles: set[tuple[int, int]] = field(init=False)
    _shallow_points: set[tuple[int, int]] = field(init=False)

    def __post_init__(self):
        self._water_tiles = set()
        self._shallow_points = set()

    def add_water_tile(self, pos: tuple[int, int], is_shallow: bool = False) -> None:
        """Register a water tile."""
        self._water_tiles.add(pos)
        if is_shallow:
            self._shallow_points.add(pos)

    def get_movement_cost(self, pos: tuple[int, int], base_cost: float) -> float:
        """Get modified movement cost for water tiles."""
        if pos in self._water_tiles:
            if pos in self._shallow_points:
                return base_cost * self.SHALLOW_MULTIPLIER
            return base_cost * self.WATER_MOVEMENT_MULTIPLIER
        return base_cost

    def is_water(self, pos: tuple[int, int]) -> bool:
        """Check if position is water."""
        return pos in self._water_tiles

    def get_exposure_modifier(self, pos: tuple[int, int]) -> float:
        """Get exposure bonus/penalty."""
        if pos in self._water_tiles:
            return self.EXPOSURE_BONUS
        return 0.0


@dataclass
class RoadSystem:
    """
    Road movement bonus system.

    Road tiles: speed x1.3, visibility x1.2
    Muddy roads (after rain): bonuses cancelled/reversed
    """

    SPEED_MULTIPLIER: float = 1.3
    VISIBILITY_MULTIPLIER: float = 1.2
    MUDDY_PENALTY: float = 0.7  # Only 70% speed in mud

    _road_tiles: set[tuple[int, int]] = field(init=False)
    _muddy_road_tiles: set[tuple[int, int]] = field(init=False)

    def __post_init__(self):
        self._road_tiles = set()
        self._muddy_road_tiles = set()

    def add_road(self, pos: tuple[int, int]) -> None:
        """Register a road tile."""
        self._road_tiles.add(pos)

    def set_muddy(self, pos: tuple[int, int], muddy: bool = True) -> None:
        """Set road as muddy/clear."""
        if muddy:
            self._muddy_road_tiles.add(pos)
        else:
            self._muddy_road_tiles.discard(pos)

    def is_road(self, pos: tuple[int, int]) -> bool:
        """Check if position has road."""
        return pos in self._road_tiles

    def get_speed_modifier(self, pos: tuple[int, int]) -> float:
        """Get movement speed modifier."""
        if pos not in self._road_tiles:
            return 1.0

        if pos in self._muddy_road_tiles:
            return self.MUDDY_PENALTY

        return self.SPEED_MULTIPLIER

    def get_visibility_modifier(self, pos: tuple[int, int]) -> float:
        """Get visibility range modifier."""
        if pos not in self._road_tiles or pos in self._muddy_road_tiles:
            return 1.0
        return self.VISIBILITY_MULTIPLIER
