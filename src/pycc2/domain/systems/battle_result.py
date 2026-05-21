"""
Battle Result — records detailed statistics after each battle.
Used for AAR (After Action Report) and campaign persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


# VP calculation weights
VP_VICTORY_BASE = 100
VP_OBJECTIVE_COMPLETE = 25
VP_AXIS_KILL = 15
VP_ALLY_KILL = -20
VP_AXIS_ROUTED = -10
VP_ALLY_ROUTED = -15
VP_HIGH_SURVIVAL_BONUS = 30
VP_MEDIUM_SURVIVAL_BONUS = 10

# Thresholds
HIGH_SURVIVAL_THRESHOLD = 0.8
MEDIUM_SURVIVAL_THRESHOLD = 0.5

# HP loss per casualty type
HP_LOSS_KIA = 1.0
HP_LOSS_WIA = 0.5
HP_LOSS_PINNED = 0.25


class BattleOutcome(Enum):
    VICTORY = auto()
    DEFEAT = auto()
    DRAW = auto()
    TIME_OUT_VICTORY = auto()
    TIME_OUT_DEFEAT = auto()


@dataclass
class UnitBattleRecord:
    unit_id: str
    unit_type: str
    faction: str
    survived: bool
    hp_start: int
    hp_end: int
    damage_dealt: float
    damage_taken: int
    kills: int
    shots_fired: int
    shots_hit: int
    xp_gained: int = 0

    @property
    def efficiency(self) -> float:
        if self.shots_fired == 0:
            return 0.0
        return self.shots_hit / self.shots_fired


@dataclass
class BattleResult:
    mission_id: str
    mission_name: str
    outcome: BattleOutcome
    ticks_elapsed: int
    date_in_campaign: int = 1

    allies_killed: int = 0
    allies_routed: int = 0
    axis_killed: int = 0
    axis_routed: int = 0

    total_shots_fired_allies: int = 0
    total_shots_hit_allies: int = 0
    total_shots_fired_axis: int = 0
    total_shots_hit_axis: int = 0
    total_damage_dealt_allies: float = 0.0
    total_damage_dealt_axis: float = 0.0

    objectives_completed: int = 0
    objectives_total: int = 0

    unit_records: list[UnitBattleRecord] = field(default_factory=list)

    victory_points: int = 0

    @property
    def allies_accuracy(self) -> float:
        if self.total_shots_fired_allies == 0:
            return 0.0
        return self.total_shots_hit_allies / self.total_shots_fired_allies

    @property
    def axis_accuracy(self) -> float:
        if self.total_shots_fired_axis == 0:
            return 0.0
        return self.total_shots_hit_axis / self.total_shots_fired_axis

    @property
    def is_victory(self) -> bool:
        return self.outcome in (
            BattleOutcome.VICTORY,
            BattleOutcome.TIME_OUT_VICTORY,
        )

    @property
    def survival_rate_allies(self) -> float:
        ally_units = [r for r in self.unit_records if r.faction == "allies"]
        if not ally_units:
            return 0.0
        survived = sum(1 for r in ally_units if r.survived)
        return survived / len(ally_units)

    def calculate_vp(self) -> int:
        vp = 0
        if self.is_victory:
            vp += VP_VICTORY_BASE
            vp += self.objectives_completed * VP_OBJECTIVE_COMPLETE

        vp += self.axis_killed * VP_AXIS_KILL
        vp += self.axis_routed * VP_AXIS_ROUTED
        vp += self.allies_killed * abs(VP_ALLY_KILL)
        vp -= self.allies_routed * abs(VP_ALLY_ROUTED)

        if self.survival_rate_allies >= HIGH_SURVIVAL_THRESHOLD:
            vp += VP_HIGH_SURVIVAL_BONUS
        elif self.survival_rate_allies >= MEDIUM_SURVIVAL_THRESHOLD:
            vp += VP_MEDIUM_SURVIVAL_BONUS

        self.victory_points = max(0, vp)
        return self.victory_points

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "outcome": self.outcome.name,
            "ticks_elapsed": self.ticks_elapsed,
            "date_in_campaign": self.date_in_campaign,
            "allies_killed": self.allies_killed,
            "axis_killed": self.axis_killed,
            "allies_routed": self.allies_routed,
            "axis_routed": self.axis_routed,
            "victory_points": self.victory_points,
            "unit_records": [r.__dict__ for r in self.unit_records],
        }

    @classmethod
    def from_dict(cls, data: dict) -> BattleResult:
        records = [
            UnitBattleRecord(**r) for r in data.get("unit_records", [])
        ]
        return cls(
            mission_id=data["mission_id"],
            mission_name=data.get("mission_name", ""),
            outcome=BattleOutcome[data["outcome"]],
            ticks_elapsed=data["ticks_elapsed"],
            date_in_campaign=data.get("date_in_campaign", 1),
            allies_killed=data.get("allies_killed", 0),
            axis_killed=data.get("axis_killed", 0),
            allies_routed=data.get("allies_routed", 0),
            axis_routed=data.get("axis_routed", 0),
            victory_points=data.get("victory_points", 0),
            unit_records=records,
        )
