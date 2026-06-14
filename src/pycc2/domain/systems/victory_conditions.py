from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class VictoryConditionType(Enum):
    ELIMINATE_ALL_ENEMIES = auto()
    OCCUPY_OBJECTIVE = auto()
    TIME_LIMIT = auto()
    FORCE_MORALE_COLLAPSE = auto()


class GameResult(Enum):
    ONGOING = auto()
    ALLIES_VICTORY = auto()
    AXIS_VICTORY = auto()
    DRAW = auto()
    TIME_OUT = auto()


@dataclass(slots=True)
class Objective:
    """A Victory Location (VL) on the map.

    In CC2, VLs have different point values. A unit entering the VL radius
    instantly captures it — no hold-time required. The enemy must push
    the unit out to recapture.
    """

    id: str
    name: str
    position: tuple[int, int]
    radius: int = 3
    points: int = 100  # CC2: VLs have different point values
    owner: str | None = None  # "allies" / "axis" / None (uncontested)


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
    """CC2-authentic victory condition evaluator.

    CC2 victory rules:
    1. Capture ALL VLs → Decisive Victory (immediate)
    2. One side eliminated → other side wins
    3. Force Morale collapses → other side wins
    4. Time expires → score VLs by point values, majority wins
    5. VL capture is INSTANT — unit enters radius, flag changes color.
       No hold-time required. Enemy must push you out to recapture.
    """

    def __init__(
        self,
        conditions: list[VictoryConditionType] | None = None,
        objectives: list[Objective] | None = None,
        time_limit_ticks: int = 0,
        force_morale_threshold: int = 0,
    ):
        self.conditions = conditions or [
            VictoryConditionType.ELIMINATE_ALL_ENEMIES,
        ]
        self.objectives = objectives or []
        self.time_limit_ticks = time_limit_ticks
        self.force_morale_threshold = force_morale_threshold
        # Track current owner of each VL (instant capture, no ticks)
        self._vl_owner: dict[str, str | None] = {}

    def evaluate(
        self,
        units: list[Unit],
        tick: int,
        stats: BattleStats | None = None,
    ) -> tuple[GameResult, str]:
        allies_alive = [u for u in units if u.faction.name == "ALLIES" and u.is_alive]
        axis_alive = [u for u in units if u.faction.name == "AXIS" and u.is_alive]

        # Safety: don't declare victory if neither side has units
        if not allies_alive and not axis_alive:
            return (GameResult.ONGOING, "")

        # --- CC2 Rule 1: Update VL ownership (instant capture) ---
        if VictoryConditionType.OCCUPY_OBJECTIVE in self.conditions:
            self._update_vl_ownership(allies_alive, axis_alive)

            # Check for decisive victory: one side holds ALL VLs
            allies_held = sum(1 for o in self._vl_owner.values() if o == "allies")
            axis_held = sum(1 for o in self._vl_owner.values() if o == "axis")
            total_vls = len(self.objectives)

            if total_vls > 0 and allies_held == total_vls:
                return (GameResult.ALLIES_VICTORY, "Decisive Victory — All VLs captured")
            if total_vls > 0 and axis_held == total_vls:
                return (GameResult.AXIS_VICTORY, "Decisive Victory — All VLs captured")

        # --- CC2 Rule 2: One side eliminated ---
        if VictoryConditionType.ELIMINATE_ALL_ENEMIES in self.conditions:
            if not axis_alive and allies_alive and tick >= 600:
                return (GameResult.ALLIES_VICTORY, "All enemy forces destroyed")
            if not allies_alive and axis_alive and tick >= 600:
                return (GameResult.AXIS_VICTORY, "All allied forces destroyed")

        # --- CC2 Rule 3: Force Morale collapse ---
        if VictoryConditionType.FORCE_MORALE_COLLAPSE in self.conditions:
            # CC2 uses army-wide Force Morale, not per-unit morale.
            # Approximate: if average morale of all living units is at threshold,
            # the force is broken.
            if allies_alive:
                avg_allies_morale = sum(u.morale.value for u in allies_alive) / len(allies_alive)
            else:
                avg_allies_morale = 0
            if axis_alive:
                avg_axis_morale = sum(u.morale.value for u in axis_alive) / len(axis_alive)
            else:
                avg_axis_morale = 0

            if avg_axis_morale <= self.force_morale_threshold and allies_alive:
                return (
                    GameResult.ALLIES_VICTORY,
                    f"Enemy force morale collapsed ({avg_axis_morale:.0f})",
                )
            if avg_allies_morale <= self.force_morale_threshold and axis_alive:
                return (
                    GameResult.AXIS_VICTORY,
                    f"Allied force morale collapsed ({avg_allies_morale:.0f})",
                )

        # --- CC2 Rule 4: Time limit — score VLs by point values ---
        if self.time_limit_ticks > 0 and tick >= self.time_limit_ticks:
            allies_score = 0
            axis_score = 0
            for obj in self.objectives:
                owner = self._vl_owner.get(obj.id)
                if owner == "allies":
                    allies_score += obj.points
                elif owner == "axis":
                    axis_score += obj.points

            if allies_score > axis_score:
                return (
                    GameResult.ALLIES_VICTORY,
                    f"Time expired — Allies {allies_score} pts vs Axis {axis_score} pts",
                )
            elif axis_score > allies_score:
                return (
                    GameResult.AXIS_VICTORY,
                    f"Time expired — Axis {axis_score} pts vs Allies {allies_score} pts",
                )
            elif allies_score > 0 or axis_score > 0:
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

    def _update_vl_ownership(self, allies_alive: list, axis_alive: list) -> None:
        """Update VL ownership — CC2 instant capture model.

        Unit enters VL radius → flag changes color immediately.
        If both sides have units in radius, ownership doesn't change (contested).
        If no units in radius, ownership stays with last holder.
        """
        for obj in self.objectives:
            allies_near = sum(1 for u in allies_alive if self._is_in_radius(u, obj))
            axis_near = sum(1 for u in axis_alive if self._is_in_radius(u, obj))

            if allies_near > 0 and axis_near == 0:
                # Allies alone in VL → instant capture
                self._vl_owner[obj.id] = "allies"
                obj.owner = "allies"
            elif axis_near > 0 and allies_near == 0:
                # Axis alone in VL → instant capture
                self._vl_owner[obj.id] = "axis"
                obj.owner = "axis"
            # If both sides present (contested) or neither present, ownership unchanged

    def _is_in_radius(self, unit: Unit, objective: Objective) -> bool:
        dx = abs(unit.position.tile_coord.x - objective.position[0])
        dy = abs(unit.position.tile_coord.y - objective.position[1])
        return max(dx, dy) <= objective.radius

    def reset(self) -> None:
        self._vl_owner.clear()
        for obj in self.objectives:
            obj.owner = None
