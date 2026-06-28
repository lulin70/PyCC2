"""Combat engagement rules and decision evaluation for unit targeting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.ai.blackboard import Blackboard
    from pycc2.domain.ai.difficulty_system import DifficultyConfig
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.tile_coord import TileCoord


@dataclass(slots=True)
class EngagementRule:
    """Tunable thresholds governing when to engage, hold, or break contact."""

    min_engagement_distance: float = 1.0
    optimal_engagement_distance: float = 6.0
    max_engagement_distance: float = 12.0
    hold_fire_if_civilians_nearby: bool = True
    cease_fire_threshold: float = 0.2
    break_contact_distance: float = 15.0
    ammo_reserve_threshold: float = 0.2
    reload_preference: str = "safe"


class EngagementDecision(Enum):
    """Possible engagement outcomes returned by the combat evaluator."""

    ENGAGE = auto()
    HOLD_POSITION = auto()
    CLOSE_DISTANCE = auto()
    RETREAT = auto()
    TAKE_COVER = auto()
    RELOAD = auto()


@dataclass(slots=True)
class EngagementResult:
    """Outcome of an engagement evaluation with decision, reason, and confidence."""

    decision: EngagementDecision
    reason: str
    target_position: TileCoord | None = None
    confidence: float = 1.0


class CombatEngagement:
    """Evaluates targeting decisions against a configured engagement rule set."""

    def __init__(self, rule: EngagementRule | None = None) -> None:
        """Initialize the evaluator with optional custom engagement rules."""
        self._rule = rule or EngagementRule()

    @property
    def rule(self) -> EngagementRule:
        """Return the engagement rule used by this evaluator."""
        return self._rule

    def evaluate_engagement(
        self,
        unit: Unit,
        target: Unit,
        distance: float,
        blackboard: Blackboard | None = None,
        difficulty_config: DifficultyConfig | None = None,
    ) -> EngagementResult:
        """Evaluate whether and how a unit should engage a target at the given distance."""
        if distance < self._rule.min_engagement_distance:
            return EngagementResult(
                decision=EngagementDecision.CLOSE_DISTANCE,
                reason="Too close to target",
                target_position=target.position.tile_coord,
            )

        if distance > self._rule.max_engagement_distance:
            return EngagementResult(
                decision=EngagementDecision.CLOSE_DISTANCE,
                reason="Target out of range",
                target_position=target.position.tile_coord,
            )

        if unit.weapon.ammo_ratio < self._rule.ammo_reserve_threshold:
            if self._rule.reload_preference == "immediate":
                return EngagementResult(
                    decision=EngagementDecision.RELOAD,
                    reason="Low ammo, reloading immediately",
                )
            return EngagementResult(
                decision=EngagementDecision.HOLD_POSITION,
                reason="Low ammo, conserving",
            )

        if unit.weapon.state.name in ("RELOADING", "JAMMED"):
            return EngagementResult(
                decision=EngagementDecision.HOLD_POSITION,
                reason=f"Weapon {unit.weapon.state.name.lower()}",
            )

        if target.health.hp_ratio < self._rule.cease_fire_threshold and target.health.hp > 0:
            return EngagementResult(
                decision=EngagementDecision.HOLD_POSITION,
                reason="Target nearly neutralized (cease fire)",
            )

        if unit.morale.state.name == "WAVERING":
            return EngagementResult(
                decision=EngagementDecision.TAKE_COVER,
                reason="Unit wavering, seeking cover",
            )
        if unit.morale.state.name in ("PINNED", "BROKEN", "ROUTING"):
            return EngagementResult(
                decision=EngagementDecision.RETREAT,
                reason=f"Unit {unit.morale.state.name.lower()}, breaking contact",
            )

        has_cover = blackboard.get("has_cover", False) if blackboard else False
        in_open = not has_cover
        if in_open and distance <= self._rule.optimal_engagement_distance * 0.6:
            return EngagementResult(
                decision=EngagementDecision.TAKE_COVER,
                reason="Exposed at close range, need cover",
                confidence=0.8,
            )

        within_optimal = (
            self._rule.optimal_engagement_distance * 0.5
            <= distance
            <= self._rule.optimal_engagement_distance * 1.3
        )
        if within_optimal:
            decision = EngagementDecision.ENGAGE
            reason = "Within optimal engagement range"
        else:
            decision = EngagementDecision.CLOSE_DISTANCE
            reason = "Adjusting to optimal range"

        if difficulty_config is not None and (
            decision == EngagementDecision.ENGAGE
            and distance > self._rule.optimal_engagement_distance
            and random.random() > difficulty_config.aggressiveness
        ):
            decision = EngagementDecision.HOLD_POSITION
            reason = "Holding position (difficulty: conservative at long range)"

        return EngagementResult(
            decision=decision,
            reason=reason,
            target_position=target.position.tile_coord
            if decision == EngagementDecision.CLOSE_DISTANCE
            else None,
        )

    def select_best_target(
        self,
        unit: Unit,
        visible_enemies: list[Unit],
        blackboard: Blackboard | None = None,
    ) -> Unit | None:
        """Select the highest-priority target from visible enemies in firing range."""
        if not visible_enemies:
            return None

        in_range = [
            e
            for e in visible_enemies
            if 0
            < unit.position.tile_coord.chebyshev_distance(e.position.tile_coord)
            <= self._rule.max_engagement_distance
        ]
        candidates = in_range if in_range else visible_enemies

        allies_under_attack: set[str] = set()
        if blackboard:
            allies_under_attack = set(blackboard.get("allies_under_attack", []))

        def _score(enemy: Unit) -> tuple[float, ...]:
            dist = unit.position.tile_coord.chebyshev_distance(enemy.position.tile_coord)
            hp_score = 1.0 - enemy.health.hp_ratio
            threat_map = {
                "MACHINE_GUN_SQUAD": 3.0,
                "AT_GUN_TEAM": 2.5,
                "COMMANDER": 2.0,
                "MORTAR_TEAM": 1.8,
                "INFANTRY_SQUAD": 1.0,
            }
            threat = threat_map.get(enemy.unit_type.name, 1.0)
            attacking_ally = 1.5 if enemy.id in allies_under_attack else 0.0
            return (-dist, hp_score, threat, attacking_ally)

        candidates.sort(key=_score, reverse=True)
        return candidates[0]

    def determine_fire_mode(
        self,
        unit: Unit,
        target: Unit,
        distance: float,
        difficulty_config: DifficultyConfig | None = None,
    ) -> str:
        """Choose a fire mode (single, burst, auto, suppress) based on unit and distance."""
        is_mg = unit.unit_type.name == "MACHINE_GUN_SQUAD"
        low_ammo = unit.weapon.ammo_ratio < 0.25

        if is_mg:
            return "suppress"

        if low_ammo:
            return "single"

        far = distance > self._rule.optimal_engagement_distance * 1.2
        close = distance <= self._rule.optimal_engagement_distance * 0.5

        if difficulty_config is not None:
            if far:
                return "burst" if difficulty_config.base_hit_chance >= 0.65 else "single"
            if close:
                return "auto" if difficulty_config.aggressiveness >= 0.75 else "burst"

        if far:
            return "single"
        if close:
            return "burst"
        return "burst"

    def should_reload_now(
        self,
        unit: Unit,
        in_combat: bool,
        has_cover: bool,
        difficulty_config: DifficultyConfig | None = None,
    ) -> bool:
        """Return whether the unit should reload now based on ammo, combat, and cover."""
        if unit.weapon.ammo_remaining == unit.weapon.max_ammo:
            return False

        if unit.weapon.state.name == "OUT_OF_AMMO":
            return True

        ratio = unit.weapon.ammo_ratio
        threshold = self._rule.ammo_reserve_threshold

        if difficulty_config is not None:
            threshold *= 1.5 - difficulty_config.ammo_conservation

        critical = ratio < threshold * 0.5
        low = ratio < threshold

        if self._rule.reload_preference == "immediate" and critical:
            return True

        if has_cover and low:
            return True

        if not in_combat and low:
            return True

        return bool(critical and in_combat and has_cover)


import random
