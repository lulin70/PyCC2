"""Civilian/NPC behavior domain system (D7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class CivilianState(Enum):
    IDLE = auto()
    FLEEING = auto()
    HIDING = auto()
    PANICKED = auto()


@dataclass
class Civilian:
    """A civilian NPC on the battlefield."""

    name: str
    position: tuple[float, float]
    state: CivilianState = CivilianState.IDLE
    alive: bool = True


@dataclass
class CivilianSystem:
    """
    Civilian/NPC behavior system.

    Civilians distributed on map.
    Flee/hide when combat nearby.
    Can block lines of fire (friendly fire risk).
    """

    civilians: list[Civilian] = field(default_factory=list)
    _flee_radius: float = 8.0  # tiles

    def spawn_civilians(
        self,
        positions: list[tuple[float, float]],
    ) -> None:
        """Spawn civilians at given positions."""
        for i, pos in enumerate(positions):
            civ = Civilian(
                name=f"Civilian_{i}",
                position=pos,
            )
            self.civilians.append(civ)

    def update(
        self,
        combat_positions: list[tuple[float, float]],
        dt: float,
    ) -> None:
        """Update civilian states based on combat proximity."""
        for civ in self.civilians:
            if not civ.alive:
                continue

            min_dist = (
                min(
                    ((cp[0] - civ.position[0]) ** 2 + (cp[1] - civ.position[1]) ** 2) ** 0.5
                    for cp in combat_positions
                )
                if combat_positions
                else float("inf")
            )

            if min_dist < self._flee_radius:
                if min_dist < 3.0:
                    civ.state = CivilianState.PANICKED
                else:
                    civ.state = CivilianState.FLEEING
            elif civ.state in (CivilianState.FLEEING, CivilianState.PANICKED):
                civ.state = CivilianState.HIDING

    def get_civilians_in_area(
        self,
        center: tuple[float, float],
        radius: float,
    ) -> list[Civilian]:
        """Get civilians within radius."""
        nearby = []
        for civ in self.civilians:
            if not civ.alive:
                continue
            dx = civ.position[0] - center[0]
            dy = civ.position[1] - center[1]
            if (dx * dx + dy * dy) ** 0.5 <= radius:
                nearby.append(civ)
        return nearby
