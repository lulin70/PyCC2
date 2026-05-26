from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class VictoryConditionType(Enum):
    ELIMINATE_ENEMY_COMMANDER = auto()
    ELIMINATE_ALL_ENEMIES = auto()
    OCCUPY_OBJECTIVE = auto()
    TIME_LIMIT = auto()
    MORALE_COLLAPSE = auto()


class GameResult(Enum):
    ONGOING = auto()
    ALLIES_VICTORY = auto()
    AXIS_VICTORY = auto()
    DRAW = auto()
    TIME_OUT = auto()


@dataclass(slots=True)
class Objective:
    id: str
    name: str
    position: tuple[int, int]
    radius: int = 1
    required_ticks: int = 0
    owner: str | None = None


@dataclass
class BattleStats:
    allies_kills: int = 0
    axis_kills: int = 0
    allies_damage_dealt: float = 0.0
    axis_damage_dealt: float = 0.0
    allies_units_lost: int = 0
    axis_units_lost: int = 0
    shots_fired_allies: int = 0
    shots_fired_axis: int = 0
    shots_hit_allies: int = 0
    shots_hit_axis: int = 0
    ticks_elapsed: int = 0
    start_time: float = field(default_factory=float)

    def record_kill(self, killer_faction: str) -> None:
        if killer_faction == "allies":
            self.allies_kills += 1
        else:
            self.axis_kills += 1

    def record_damage(self, attacker_faction: str, damage: float) -> None:
        if attacker_faction == "allies":
            self.allies_damage_dealt += damage
        else:
            self.axis_damage_dealt += damage

    def record_shot(self, faction: str, hit: bool) -> None:
        if faction == "allies":
            self.shots_fired_allies += 1
            if hit:
                self.shots_hit_allies += 1
        else:
            self.shots_fired_axis += 1
            if hit:
                self.shots_hit_axis += 1

    def record_unit_lost(self, faction: str) -> None:
        if faction == "allies":
            self.allies_units_lost += 1
        else:
            self.axis_units_lost += 1

    @property
    def allies_accuracy(self) -> float:
        if self.shots_fired_allies == 0:
            return 0.0
        return self.shots_hit_allies / self.shots_fired_allies

    @property
    def axis_accuracy(self) -> float:
        if self.shots_fired_axis == 0:
            return 0.0
        return self.shots_hit_axis / self.shots_fired_axis

    @property
    def kill_ratio(self) -> float:
        if self.axis_kills == 0:
            return float(self.allies_kills) if self.allies_kills > 0 else 0.0
        return self.allies_kills / self.axis_kills

    def summary_dict(self) -> dict:
        return {
            "allies_kills": self.allies_kills,
            "axis_kills": self.axis_kills,
            "allies_damage_dealt": self.allies_damage_dealt,
            "axis_damage_dealt": self.axis_damage_dealt,
            "allies_units_lost": self.allies_units_lost,
            "axis_units_lost": self.axis_units_lost,
            "shots_fired_allies": self.shots_fired_allies,
            "shots_fired_axis": self.shots_fired_axis,
            "shots_hit_allies": self.shots_hit_allies,
            "shots_hit_axis": self.shots_hit_axis,
            "ticks_elapsed": self.ticks_elapsed,
            "allies_accuracy": self.allies_accuracy,
            "axis_accuracy": self.axis_accuracy,
            "kill_ratio": self.kill_ratio,
        }


class VictoryConditionEvaluator:
    def __init__(
        self,
        conditions: list[VictoryConditionType] | None = None,
        objectives: list[Objective] | None = None,
        time_limit_ticks: int = 0,
        morale_threshold: int = 10,
    ):
        self.conditions = conditions or [
            VictoryConditionType.ELIMINATE_ENEMY_COMMANDER,
            VictoryConditionType.ELIMINATE_ALL_ENEMIES,
        ]
        self.objectives = objectives or []
        self.time_limit_ticks = time_limit_ticks
        self.morale_threshold = morale_threshold
        self._objective_occupancy: dict[str, tuple[str, int]] = {}

    def evaluate(
        self,
        units: list[Unit],
        tick: int,
        stats: BattleStats | None = None,
    ) -> tuple[GameResult, str]:
        allies_alive = [u for u in units if u.faction.name == "ALLIES" and u.is_alive]
        axis_alive = [u for u in units if u.faction.name == "AXIS" and u.is_alive]

        # Safety check: don't declare victory if either side has no units at all
        # (handles deployment edge cases where AI units may not be in list yet)
        if not allies_alive and not axis_alive:
            return (GameResult.ONGOING, "")

        allies_commanders = [u for u in allies_alive if u.unit_type.name == "COMMANDER"]
        axis_commanders = [u for u in axis_alive if u.unit_type.name == "COMMANDER"]

        reasons = []

        if VictoryConditionType.ELIMINATE_ENEMY_COMMANDER in self.conditions:
            if not axis_commanders and any(
                u.unit_type.name == "COMMANDER" for u in units if u.faction.name == "ALLIES"
            ):
                return (GameResult.ALLIES_VICTORY, "Enemy commander eliminated")
            if not allies_commanders and any(
                u.unit_type.name == "COMMANDER" for u in units if u.faction.name == "AXIS"
            ):
                return (GameResult.AXIS_VICTORY, "Your commander has fallen")

        if VictoryConditionType.ELIMINATE_ALL_ENEMIES in self.conditions:
            # Only declare victory if BOTH sides had units at some point
            # (prevents false victory when AI units haven't spawned yet)
            if not axis_alive and allies_alive and tick >= 600:
                return (GameResult.ALLIES_VICTORY, "All enemy forces destroyed")
            if not allies_alive and axis_alive and tick >= 600:
                return (GameResult.AXIS_VICTORY, "All allied forces destroyed")

        if VictoryConditionType.MORALE_COLLAPSE in self.conditions:
            avg_allies_morale = sum(u.morale.value for u in allies_alive) / max(
                len(allies_alive), 1
            )
            avg_axis_morale = sum(u.morale.value for u in axis_alive) / max(len(axis_alive), 1)
            if avg_axis_morale <= self.morale_threshold and allies_alive:
                return (
                    GameResult.ALLIES_VICTORY,
                    f"Enemy morale collapsed ({avg_axis_morale:.0f})",
                )
            if avg_allies_morale <= self.morale_threshold and axis_alive:
                return (
                    GameResult.AXIS_VICTORY,
                    f"Allied morale collapsed ({avg_allies_morale:.0f})",
                )

        for obj in self.objectives:
            allies_near = sum(1 for u in allies_alive if self._is_in_radius(u, obj))
            axis_near = sum(1 for u in axis_alive if self._is_in_radius(u, obj))

            occupant = None
            if allies_near > axis_near and allies_near > 0:
                occupant = "allies"
            elif axis_near > allies_near and axis_near > 0:
                occupant = "axis"

            if occupant:
                prev_faction, prev_ticks = self._objective_occupancy.get(obj.id, (occupant, 0))
                if prev_faction == occupant:
                    new_ticks = prev_ticks + 1
                else:
                    new_ticks = 1
                self._objective_occupancy[obj.id] = (occupant, new_ticks)

                # Minimum 300 ticks (10 seconds) to capture an objective
                effective_required = max(obj.required_ticks, 300)
                if effective_required == 0 or new_ticks >= effective_required:
                    if occupant == "allies":
                        return (
                            GameResult.ALLIES_VICTORY,
                            f"Objective '{obj.name}' captured",
                        )
                    else:
                        return (
                            GameResult.AXIS_VICTORY,
                            f"Objective '{obj.name}' lost",
                        )
            elif obj.id in self._objective_occupancy:
                self._objective_occupancy[obj.id] = (
                    self._objective_occupancy[obj.id][0],
                    0,
                )

        if self.time_limit_ticks > 0 and tick >= self.time_limit_ticks:
            # CC2-style: time expired, count VLs held by each side
            allies_vls = 0
            axis_vls = 0
            for obj in self.objectives:
                occ = self._objective_occupancy.get(obj.id)
                if occ:
                    faction, ticks = occ
                    if faction == "allies" and ticks >= max(obj.required_ticks, 300):
                        allies_vls += 1
                    elif faction == "axis" and ticks >= max(obj.required_ticks, 300):
                        axis_vls += 1

            if allies_vls > axis_vls:
                return (
                    GameResult.ALLIES_VICTORY,
                    f"Time expired — Allies hold {allies_vls} VL(s) vs Axis {axis_vls}",
                )
            elif axis_vls > allies_vls:
                return (
                    GameResult.AXIS_VICTORY,
                    f"Time expired — Axis hold {axis_vls} VL(s) vs Allies {allies_vls}",
                )
            elif allies_vls > 0 or axis_vls > 0:
                return (GameResult.DRAW, "Time expired — VLs tied")
            else:
                # No VLs captured, decide by unit count
                if len(allies_alive) > len(axis_alive):
                    return (GameResult.ALLIES_VICTORY, "Time expired — Allies hold advantage")
                elif len(axis_alive) > len(allies_alive):
                    return (GameResult.AXIS_VICTORY, "Time expired — Axis holds advantage")
                else:
                    return (GameResult.DRAW, "Time expired — Stalemate")

        return (GameResult.ONGOING, "")

    def _is_in_radius(self, unit: Unit, objective: Objective) -> bool:
        dx = abs(unit.position.tile_coord.x - objective.position[0])
        dy = abs(unit.position.tile_coord.y - objective.position[1])
        return max(dx, dy) <= objective.radius

    def reset(self) -> None:
        self._objective_occupancy.clear()
