"""Battle Result — records detailed statistics after each battle.
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
    """Possible outcomes of a completed battle."""

    VICTORY = auto()
    DEFEAT = auto()
    DRAW = auto()
    TIME_OUT_VICTORY = auto()
    TIME_OUT_DEFEAT = auto()


@dataclass
class UnitBattleRecord:
    """Per-unit combat statistics recorded during a single battle."""

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
        """Return the unit's hit efficiency as shots_hit / shots_fired."""
        if self.shots_fired == 0:
            return 0.0
        return self.shots_hit / self.shots_fired


@dataclass(frozen=True, slots=True)
class BattleEvent:
    """V-03 (Wave C5): Strongly-typed battle event for post-battle timeline.

    Replaces loose dict usage in BattleEventTracker.get_narrative_data().
    Used by PostBattleReportRenderer._render_event_timeline().

    Reference: docs/VISUAL_POLISH_PLAN.md V-03 章节 (v2.1, Wave B-rev)
    """

    event_type: str  # "unit_killed" / "building_destroyed" / "bridge_destroyed" / "morale_break" / "vl_capture"
    timestamp: float  # seconds since battle start
    unit_id: str | None = None
    faction: str | None = None
    description: str = ""


@dataclass
class BattleResult:
    """Aggregated statistics and outcome of a completed battle."""

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

    # V-03 (Wave C5): Enhanced post-battle report fields.
    # Both fields default to empty/None for backward compatibility with
    # existing save files (from_dict handles missing keys gracefully).
    events: list[BattleEvent] = field(default_factory=list)
    mvp_unit_id: str | None = None

    @property
    def allies_accuracy(self) -> float:
        """Return the allies' hit-to-shot ratio, or 0.0 if no shots were fired."""
        if self.total_shots_fired_allies == 0:
            return 0.0
        return self.total_shots_hit_allies / self.total_shots_fired_allies

    @property
    def axis_accuracy(self) -> float:
        """Return the axis' hit-to-shot ratio, or 0.0 if no shots were fired."""
        if self.total_shots_fired_axis == 0:
            return 0.0
        return self.total_shots_hit_axis / self.total_shots_fired_axis

    @property
    def is_victory(self) -> bool:
        """Return True if the battle outcome is any kind of victory."""
        return self.outcome in (
            BattleOutcome.VICTORY,
            BattleOutcome.TIME_OUT_VICTORY,
        )

    @property
    def survival_rate_allies(self) -> float:
        """Return the fraction of allied units that survived the battle."""
        ally_units = [r for r in self.unit_records if r.faction == "allies"]
        if not ally_units:
            return 0.0
        survived = sum(1 for r in ally_units if r.survived)
        return survived / len(ally_units)

    def calculate_vp(self) -> int:
        """Compute and store the victory points earned from this battle."""
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
        """Serialize the battle result into a plain dictionary for persistence.

        V-03 (Wave C5): Includes events and mvp_unit_id for enhanced report.
        Backward compatible: old readers ignore extra keys.
        """
        return {
            "mission_id": self.mission_id,
            "mission_name": self.mission_name,
            "outcome": self.outcome.name,
            "ticks_elapsed": self.ticks_elapsed,
            "date_in_campaign": self.date_in_campaign,
            "allies_killed": self.allies_killed,
            "axis_killed": self.axis_killed,
            "allies_routed": self.allies_routed,
            "axis_routed": self.axis_routed,
            "total_shots_fired_allies": self.total_shots_fired_allies,
            "total_shots_hit_allies": self.total_shots_hit_allies,
            "total_shots_fired_axis": self.total_shots_fired_axis,
            "total_shots_hit_axis": self.total_shots_hit_axis,
            "total_damage_dealt_allies": self.total_damage_dealt_allies,
            "total_damage_dealt_axis": self.total_damage_dealt_axis,
            "objectives_completed": self.objectives_completed,
            "objectives_total": self.objectives_total,
            "victory_points": self.victory_points,
            "unit_records": [r.__dict__ for r in self.unit_records],
            # V-03 (Wave C5): new fields
            "events": [
                {
                    "event_type": e.event_type,
                    "timestamp": e.timestamp,
                    "unit_id": e.unit_id,
                    "faction": e.faction,
                    "description": e.description,
                }
                for e in self.events
            ],
            "mvp_unit_id": self.mvp_unit_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BattleResult:
        """Reconstruct a BattleResult instance from a serialized dictionary.

        V-03 (Wave C5): Backward compatible — old save files without
        events/mvp_unit_id keys will use defaults (empty list / None).
        """
        records = [UnitBattleRecord(**r) for r in data.get("unit_records", [])]
        events = [
            BattleEvent(
                event_type=e.get("event_type", "unknown"),
                timestamp=float(e.get("timestamp", 0.0)),
                unit_id=e.get("unit_id"),
                faction=e.get("faction"),
                description=e.get("description", ""),
            )
            for e in data.get("events", [])
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
            total_shots_fired_allies=data.get("total_shots_fired_allies", 0),
            total_shots_hit_allies=data.get("total_shots_hit_allies", 0),
            total_shots_fired_axis=data.get("total_shots_fired_axis", 0),
            total_shots_hit_axis=data.get("total_shots_hit_axis", 0),
            total_damage_dealt_allies=data.get("total_damage_dealt_allies", 0.0),
            total_damage_dealt_axis=data.get("total_damage_dealt_axis", 0.0),
            objectives_completed=data.get("objectives_completed", 0),
            objectives_total=data.get("objectives_total", 0),
            victory_points=data.get("victory_points", 0),
            unit_records=records,
            events=events,
            mvp_unit_id=data.get("mvp_unit_id"),
        )


class BattleEventTracker:
    """Tracks key events during battle for narrative post-battle reports.

    Records first kills, morale breaks, VL captures, last stands,
    and heroic actions to generate a compelling narrative.
    """

    def __init__(self) -> None:
        """Initialize the battle event tracker with empty event buffers."""
        self._key_events: list[str] = []
        self._allied_kia: list[str] = []
        self._heroic_actions: list[str] = []
        self._first_kill_recorded: bool = False
        self._first_morale_break_recorded: bool = False

    def record_first_kill(self, killer_name: str, victim_name: str, tick: int) -> None:
        """Record the first kill of the battle."""
        if not self._first_kill_recorded:
            self._first_kill_recorded = True
            time_sec = tick / 60
            self._key_events.append(
                f"[{time_sec:.0f}s] First blood: {killer_name} killed {victim_name}"
            )

    def record_kill(self, killer_name: str, victim_name: str, tick: int) -> None:
        """Record any kill during battle."""
        self.record_first_kill(killer_name, victim_name, tick)

    def record_morale_break(self, unit_name: str, new_state: str, tick: int) -> None:
        """Record a morale collapse event."""
        time_sec = tick / 60
        if not self._first_morale_break_recorded and new_state in ("broken", "routing"):
            self._first_morale_break_recorded = True
            self._key_events.append(
                f"[{time_sec:.0f}s] {unit_name}'s morale collapsed — {new_state.upper()}!"
            )
        elif new_state == "routing":
            self._key_events.append(f"[{time_sec:.0f}s] {unit_name} is routing!")

    def record_vl_capture(self, unit_name: str, vl_name: str, tick: int) -> None:
        """Record a victory location capture."""
        time_sec = tick / 60
        self._key_events.append(f"[{time_sec:.0f}s] {unit_name} captured {vl_name}")

    def record_allied_kia(self, soldier_name: str) -> None:
        """Record an allied soldier killed in action."""
        self._allied_kia.append(soldier_name)

    def record_heroic_action(self, description: str) -> None:
        """Record a heroic/commendable action."""
        self._heroic_actions.append(description)

    def record_last_stand(self, unit_name: str, tick: int) -> None:
        """Record a last stand event."""
        time_sec = tick / 60
        self._key_events.append(f"[{time_sec:.0f}s] {unit_name} made a last stand!")
        self._heroic_actions.append(f"{unit_name} held the line to the last man")

    def get_narrative_data(self) -> dict:
        """Return collected narrative data for the post-battle report."""
        return {
            "key_events": self._key_events,
            "allied_kia": self._allied_kia,
            "heroic_actions": self._heroic_actions,
        }
