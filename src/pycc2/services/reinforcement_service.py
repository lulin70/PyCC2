"""Scenario reinforcement scheduler (CC2 parity P0-2).

Scenarios declare timed reinforcements under ``forces.<side>.reinforcements``:

    {"template_id": "uk_sherman_v", "arrival_turn": 6, "from_direction": "west"}

The service converts battle ticks to turns, spawns each entry once at a map
edge, and returns the new units to the game loop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)

# One scenario turn equals 30 seconds of real time at 30 Hz.
TICKS_PER_TURN: int = 900


@dataclass
class ReinforcementService:
    """Spawns scenario reinforcements when their arrival turn is reached."""

    schedule: list[dict] = field(default_factory=list)
    _spawned: set[tuple[str, int]] = field(init=False, default_factory=set)
    _counter: int = field(init=False, default=1000)

    @classmethod
    def from_scenario(cls, map_data: dict) -> ReinforcementService:
        """Build a service from scenario JSON data."""
        schedule: list[dict] = []
        forces = map_data.get("forces", {}) if isinstance(map_data, dict) else {}
        for side in ("allies", "axis"):
            entries = forces.get(side, {}).get("reinforcements", []) or []
            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    continue
                template_id = entry.get("template_id")
                arrival_turn = entry.get("arrival_turn")
                if not template_id or not isinstance(arrival_turn, int):
                    continue
                schedule.append(
                    {
                        "side": side,
                        "index": index,
                        "template_id": template_id,
                        "arrival_turn": arrival_turn,
                        "from_direction": str(entry.get("from_direction", "west")).lower(),
                    }
                )
        return cls(schedule=schedule)

    @staticmethod
    def current_turn(tick: int) -> int:
        """Convert elapsed battle ticks to a 1-based scenario turn."""
        return int(tick) // TICKS_PER_TURN + 1

    def due_entries(self, tick: int) -> list[dict]:
        """Return reinforcement entries that are due and not yet spawned."""
        turn = self.current_turn(tick)
        due: list[dict] = []
        for entry in self.schedule:
            key = (entry["side"], entry["index"])
            if key in self._spawned:
                continue
            if turn >= entry["arrival_turn"]:
                due.append(entry)
        return due

    def update(
        self,
        tick: int,
        units: list[Unit],
        game_map: GameMap,
        factory,
        allowed_sides: set[str] | None = None,
        max_per_side: int | None = None,
    ) -> list[tuple[Unit, str]]:
        """Spawn due reinforcements. Returns ``(unit, side)`` pairs.

        Args:
            allowed_sides: PF-12 gate (``lz_must_hold_for_reinforcements``).
                ``None`` allows all sides.
            max_per_side: PF-12 cap (``limited_reinforcements``).

        """
        spawned: list[tuple[Unit, str]] = []
        per_side: dict[str, int] = {}
        for side, _index in self._spawned:
            per_side[side] = per_side.get(side, 0) + 1

        for entry in self.due_entries(tick):
            side = entry["side"]
            if allowed_sides is not None and side not in allowed_sides:
                continue
            if max_per_side is not None and per_side.get(side, 0) >= max_per_side:
                continue
            direction = entry["from_direction"]
            position = self._find_spawn_position(game_map, units, direction)
            if position is None:
                logger.warning(
                    "No spawn position for reinforcement %s from %s",
                    entry["template_id"],
                    direction,
                )
                continue

            faction = _faction_for_side(entry["side"])
            self._counter += 1
            unit = factory(entry["template_id"], faction, position, self._counter)
            if unit is None:
                logger.warning("Failed to create reinforcement %s", entry["template_id"])
                continue

            self._spawned.add((side, entry["index"]))
            per_side[side] = per_side.get(side, 0) + 1
            units.append(unit)
            spawned.append((unit, entry["side"]))
            logger.info(
                "Reinforcement arrived: %s (%s) at %s",
                entry["template_id"],
                entry["side"],
                position,
            )
        return spawned

    @staticmethod
    def _find_spawn_position(
        game_map: GameMap,
        units: list[Unit],
        direction: str,
        edge_depth: int = 3,
    ) -> tuple[int, int] | None:
        """Find a passable, unoccupied tile along the requested map edge."""
        occupied = {
            (unit.position.tile_coord.x, unit.position.tile_coord.y)
            for unit in units
            if getattr(unit, "is_alive", False)
        }
        width = int(game_map.width)
        height = int(game_map.height)

        if direction == "east":
            coords = (
                (x, y)
                for x in range(max(0, width - edge_depth), width)
                for y in range(height)
            )
        elif direction == "north":
            coords = (
                (x, y)
                for y in range(0, min(edge_depth, height))
                for x in range(width)
            )
        elif direction == "south":
            coords = (
                (x, y)
                for y in range(max(0, height - edge_depth), height)
                for x in range(width)
            )
        else:  # west
            coords = (
                (x, y)
                for x in range(0, min(edge_depth, width))
                for y in range(height)
            )

        for x, y in coords:
            if (x, y) in occupied:
                continue
            coord = TileCoord(x, y)
            if game_map.is_passable(coord):
                return (x, y)
        return None


def _faction_for_side(side: str):
    """Map a scenario side name to a Faction enum value."""
    from pycc2.domain.entities.unit import Faction

    return Faction.ALLIES if side == "allies" else Faction.AXIS
