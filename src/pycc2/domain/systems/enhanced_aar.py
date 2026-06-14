"""
Enhanced AAR (After Action Report) Statistics.

A "beyond CC2" feature: the original Close Combat 2 only showed basic
kills/casualties.  This module collects per-unit, per-weapon, and
position-based statistics during battle, then generates a detailed
report with MVP scoring and heatmap data.
"""

# PLANNED: Not yet wired into game loop — reserved for future feature

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from pycc2.domain.systems.battle_result import BattleOutcome, BattleResult

# ========================================================================
# Data classes
# ========================================================================


@dataclass
class BasicStats:
    kills_allied: int = 0
    kills_axis: int = 0
    casualties_allied: int = 0
    casualties_axis: int = 0
    outcome: BattleOutcome = BattleOutcome.DRAW


@dataclass
class UnitAARStats:
    unit_id: str
    unit_name: str
    kills: int = 0
    shots_fired: int = 0
    shots_hit: int = 0
    accuracy: float = 0.0
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    distance_moved: float = 0.0
    time_suppressed: int = 0  # ticks
    time_in_combat: int = 0  # ticks
    ammo_consumed: int = 0
    enemies_spotted: int = 0
    mvp_score: float = 0.0

    def calculate_accuracy(self) -> float:
        if self.shots_fired == 0:
            self.accuracy = 0.0
        else:
            self.accuracy = self.shots_hit / self.shots_fired
        return self.accuracy

    def calculate_mvp_score(self) -> float:
        """Composite MVP score: weighted sum of combat contributions."""
        score = (
            self.kills * 30.0
            + self.damage_dealt * 0.5
            + self.accuracy * 20.0
            + self.enemies_spotted * 5.0
            - self.time_suppressed * 0.1
            - self.damage_taken * 0.3
        )
        # Bonus for efficiency (high impact per shot)
        if self.shots_fired > 0:
            score += (self.kills / self.shots_fired) * 15.0
        self.mvp_score = max(0.0, score)
        return self.mvp_score


@dataclass
class WeaponAARStats:
    weapon_type: str
    shots_fired: int = 0
    shots_hit: int = 0
    kills: int = 0
    suppression_caused: float = 0.0
    accuracy: float = 0.0

    def calculate_accuracy(self) -> float:
        if self.shots_fired == 0:
            self.accuracy = 0.0
        else:
            self.accuracy = self.shots_hit / self.shots_fired
        return self.accuracy


@dataclass
class HeatmapData:
    shots_fired_map: dict[tuple[int, int], int] = field(default_factory=dict)
    kills_map: dict[tuple[int, int], int] = field(default_factory=dict)
    movement_map: dict[tuple[int, int], int] = field(default_factory=dict)
    suppression_map: dict[tuple[int, int], float] = field(default_factory=dict)


@dataclass
class AARTimelineEvent:
    tick: int
    event: str
    description: str


@dataclass
class EnhancedAARStats:
    basic: BasicStats = field(default_factory=BasicStats)
    unit_stats: dict[str, UnitAARStats] = field(default_factory=dict)
    weapon_stats: dict[str, WeaponAARStats] = field(default_factory=dict)
    timeline: list[AARTimelineEvent] = field(default_factory=list)
    heatmap_data: HeatmapData = field(default_factory=HeatmapData)

    def to_dict(self) -> dict[str, Any]:
        return {
            "basic": {
                "kills_allied": self.basic.kills_allied,
                "kills_axis": self.basic.kills_axis,
                "casualties_allied": self.basic.casualties_allied,
                "casualties_axis": self.basic.casualties_axis,
                "outcome": self.basic.outcome.name,
            },
            "unit_count": len(self.unit_stats),
            "weapon_count": len(self.weapon_stats),
            "timeline_events": len(self.timeline),
            "mvp": max(self.unit_stats.values(), key=lambda u: u.mvp_score).unit_name
            if self.unit_stats
            else None,
        }


# ========================================================================
# EnhancedAARCollector
# ========================================================================


class EnhancedAARCollector:
    """Collects detailed battle statistics during combat.

    Hook into combat events via the record_* methods.  After the
    battle, call generate_report() to produce the full AAR.
    """

    def __init__(self) -> None:
        self._unit_stats: dict[str, UnitAARStats] = {}
        self._weapon_stats: dict[str, WeaponAARStats] = {}
        self._heatmap = HeatmapData()
        self._timeline: list[AARTimelineEvent] = []

        # Tracking state
        self._unit_positions: dict[str, tuple[int, int]] = {}
        self._unit_suppressed_since: dict[str, int] = {}
        self._unit_in_combat_since: dict[str, int] = {}

        # Basic counters
        self._kills_allied: int = 0
        self._kills_axis: int = 0
        self._casualties_allied: int = 0
        self._casualties_axis: int = 0

    # ------------------------------------------------------------------
    # Event recording methods
    # ------------------------------------------------------------------

    def ensure_unit(self, unit_id: str, unit_name: str) -> None:
        """Register a unit if not already tracked."""
        if unit_id not in self._unit_stats:
            self._unit_stats[unit_id] = UnitAARStats(
                unit_id=unit_id,
                unit_name=unit_name,
            )

    def record_shot(
        self,
        unit_id: str,
        unit_name: str,
        position: tuple[int, int],
        weapon_type: str,
        hit: bool,
    ) -> None:
        self.ensure_unit(unit_id, unit_name)
        u = self._unit_stats[unit_id]
        u.shots_fired += 1
        u.ammo_consumed += 1
        if hit:
            u.shots_hit += 1

        # Weapon stats
        if weapon_type not in self._weapon_stats:
            self._weapon_stats[weapon_type] = WeaponAARStats(weapon_type=weapon_type)
        w = self._weapon_stats[weapon_type]
        w.shots_fired += 1
        if hit:
            w.shots_hit += 1

        # Heatmap
        self._heatmap.shots_fired_map[position] = self._heatmap.shots_fired_map.get(position, 0) + 1

    def record_hit(
        self,
        source_id: str,
        source_name: str,
        target_id: str,
        target_name: str,
        position: tuple[int, int],
        damage: float,
        weapon_type: str,
    ) -> None:
        self.ensure_unit(source_id, source_name)
        self.ensure_unit(target_id, target_name)

        self._unit_stats[source_id].damage_dealt += damage
        self._unit_stats[target_id].damage_taken += damage

        if weapon_type in self._weapon_stats:
            self._weapon_stats[weapon_type].suppression_caused += damage * 0.1

    def record_kill(
        self,
        killer_id: str,
        killer_name: str,
        killer_faction: str,
        victim_id: str,
        victim_name: str,
        victim_faction: str,
        position: tuple[int, int],
        weapon_type: str,
        tick: int,
    ) -> None:
        self.ensure_unit(killer_id, killer_name)
        self.ensure_unit(victim_id, victim_name)

        self._unit_stats[killer_id].kills += 1
        if weapon_type in self._weapon_stats:
            self._weapon_stats[weapon_type].kills += 1

        if killer_faction in ("allies", "ALLIES"):
            self._kills_allied += 1
            self._casualties_axis += 1
        else:
            self._kills_axis += 1
            self._casualties_allied += 1

        self._heatmap.kills_map[position] = self._heatmap.kills_map.get(position, 0) + 1

        self._timeline.append(
            AARTimelineEvent(
                tick=tick,
                event="KILL",
                description=f"{killer_name} killed {victim_name}",
            )
        )

    def record_movement(
        self,
        unit_id: str,
        unit_name: str,
        from_pos: tuple[int, int],
        to_pos: tuple[int, int],
    ) -> None:
        self.ensure_unit(unit_id, unit_name)
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        dist = math.sqrt(dx * dx + dy * dy)
        self._unit_stats[unit_id].distance_moved += dist

        self._heatmap.movement_map[to_pos] = self._heatmap.movement_map.get(to_pos, 0) + 1
        self._unit_positions[unit_id] = to_pos

    def record_suppression(
        self,
        unit_id: str,
        unit_name: str,
        position: tuple[int, int],
        amount: float,
        tick: int,
    ) -> None:
        self.ensure_unit(unit_id, unit_name)

        self._heatmap.suppression_map[position] = (
            self._heatmap.suppression_map.get(position, 0.0) + amount
        )

        if unit_id not in self._unit_suppressed_since:
            self._unit_suppressed_since[unit_id] = tick

    def record_suppression_end(self, unit_id: str, tick: int) -> None:
        if unit_id in self._unit_suppressed_since:
            start = self._unit_suppressed_since.pop(unit_id)
            if unit_id in self._unit_stats:
                self._unit_stats[unit_id].time_suppressed += tick - start

    def record_combat_start(self, unit_id: str, tick: int) -> None:
        if unit_id not in self._unit_in_combat_since:
            self._unit_in_combat_since[unit_id] = tick

    def record_combat_end(self, unit_id: str, tick: int) -> None:
        if unit_id in self._unit_in_combat_since:
            start = self._unit_in_combat_since.pop(unit_id)
            if unit_id in self._unit_stats:
                self._unit_stats[unit_id].time_in_combat += tick - start

    def record_spot(
        self,
        spotter_id: str,
        spotter_name: str,
    ) -> None:
        self.ensure_unit(spotter_id, spotter_name)
        self._unit_stats[spotter_id].enemies_spotted += 1

    def record_timeline_event(self, tick: int, event: str, description: str) -> None:
        self._timeline.append(
            AARTimelineEvent(
                tick=tick,
                event=event,
                description=description,
            )
        )

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def generate_report(
        self,
        outcome: BattleOutcome = BattleOutcome.DRAW,
    ) -> EnhancedAARStats:
        """Finalize all calculations and return the complete report."""
        # Finalize suppressed / combat timers
        for uid, _start in self._unit_suppressed_since.items():
            if uid in self._unit_stats:
                self._unit_stats[uid].time_suppressed += 0  # still active
        for uid, _start in self._unit_in_combat_since.items():
            if uid in self._unit_stats:
                self._unit_stats[uid].time_in_combat += 0

        # Calculate derived stats
        for u in self._unit_stats.values():
            u.calculate_accuracy()
            u.calculate_mvp_score()

        for w in self._weapon_stats.values():
            w.calculate_accuracy()

        # Sort timeline by tick
        self._timeline.sort(key=lambda e: e.tick)

        basic = BasicStats(
            kills_allied=self._kills_allied,
            kills_axis=self._kills_axis,
            casualties_allied=self._casualties_allied,
            casualties_axis=self._casualties_axis,
            outcome=outcome,
        )

        return EnhancedAARStats(
            basic=basic,
            unit_stats=dict(self._unit_stats),
            weapon_stats=dict(self._weapon_stats),
            timeline=list(self._timeline),
            heatmap_data=self._heatmap,
        )

    def generate_report_from_battle_result(
        self,
        result: BattleResult,
    ) -> EnhancedAARStats:
        """Generate an enhanced AAR from an existing BattleResult.

        Useful when only the basic BattleResult is available (e.g. from
        a saved game) and we want to wrap it in the enhanced structure.
        """
        basic = BasicStats(
            kills_allied=result.axis_killed,
            kills_axis=result.allies_killed,
            casualties_allied=result.allies_killed + result.allies_routed,
            casualties_axis=result.axis_killed + result.axis_routed,
            outcome=result.outcome,
        )

        unit_stats: dict[str, UnitAARStats] = {}
        for rec in result.unit_records:
            s = UnitAARStats(
                unit_id=rec.unit_id,
                unit_name=rec.unit_type,
                kills=rec.kills,
                shots_fired=rec.shots_fired,
                shots_hit=rec.shots_hit,
                damage_dealt=rec.damage_dealt,
                damage_taken=float(rec.damage_taken),
            )
            s.calculate_accuracy()
            s.calculate_mvp_score()
            unit_stats[rec.unit_id] = s

        return EnhancedAARStats(
            basic=basic,
            unit_stats=unit_stats,
        )

    # ------------------------------------------------------------------
    # Convenience queries
    # ------------------------------------------------------------------

    def get_mvp(self) -> UnitAARStats:
        """Return the unit with the highest MVP score."""
        if not self._unit_stats:
            return UnitAARStats(unit_id="", unit_name="")
        return max(self._unit_stats.values(), key=lambda u: u.mvp_score)

    def get_heatmap(self, heatmap_type: str) -> dict[tuple[int, int], float]:
        """Return a specific heatmap by name.

        heatmap_type: 'shots_fired' | 'kills' | 'movement' | 'suppression'
        """
        if heatmap_type == "shots_fired":
            return {k: float(v) for k, v in self._heatmap.shots_fired_map.items()}
        if heatmap_type == "kills":
            return {k: float(v) for k, v in self._heatmap.kills_map.items()}
        if heatmap_type == "movement":
            return {k: float(v) for k, v in self._heatmap.movement_map.items()}
        if heatmap_type == "suppression":
            return dict(self._heatmap.suppression_map)
        return {}
