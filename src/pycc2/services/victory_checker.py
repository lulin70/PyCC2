"""
Victory Condition Checker

Evaluates whether victory conditions have been met.
Supports multiple victory condition types and combinations.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from pycc2.services.event_bus import EventBus
from pycc2.services.event_protocol import GameOverEvent, VictoryConditionMetEvent


class VictoryConditionType(Enum):
    """Types of victory conditions."""

    ELIMINATE_ALL_ENEMIES = auto()
    CAPTURE_OBJECTIVE = auto()
    REACH_POSITION = auto()
    SURVIVE_TURNS = auto()
    SCORE_THRESHOLD = auto()


@dataclass
class VictoryCondition:
    """Definition of a single victory condition."""

    id: str
    condition_type: VictoryConditionType
    description: str
    required_for: list[str]  # Faction(s) this applies to
    parameters: dict = None
    priority: int = 0

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class VictoryCheckResult:
    """Result of checking victory conditions."""

    victory_achieved: bool
    winning_faction: str | None
    conditions_met: list[str]
    conditions_remaining: list[str]
    message: str


class VictoryChecker:
    """
    Evaluates victory conditions and determines game outcome.

    Can check multiple condition types and combine results according
    to configured logic (AND/OR).
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._conditions: list[VictoryCondition] = []
        self._condition_evaluators: dict[VictoryConditionType, Callable] = {}
        self._logger = logging.getLogger("pycc2.victory_checker")
        self._register_default_evaluators()

    def add_condition(self, condition: VictoryCondition) -> None:
        """Add a victory condition to check."""
        self._conditions.append(condition)
        self._logger.info(
            f"Added victory condition: {condition.id} ({condition.condition_type.name})"
        )

    def remove_condition(self, condition_id: str) -> None:
        """Remove a victory condition by ID."""
        self._conditions = [c for c in self._conditions if c.id != condition_id]

    def clear_conditions(self) -> None:
        """Remove all victory conditions."""
        self._conditions.clear()

    def register_evaluator(
        self,
        condition_type: VictoryConditionType,
        evaluator: Callable[[VictoryCondition, dict], bool],
    ) -> None:
        """
        Register custom evaluator for a condition type.

        Args:
            condition_type: Type this evaluator handles
            evaluator: Function that takes condition + game state, returns bool
        """
        self._condition_evaluators[condition_type] = evaluator

    def check_victory(self, game_state: dict) -> VictoryCheckResult:
        """
        Check all victory conditions against current game state.

        Args:
            game_state: Current game state dictionary containing units, objectives, etc.

        Returns:
            VictoryCheckResult with detailed outcome information
        """
        conditions_met = []
        conditions_remaining = []
        faction_wins: dict[str, int] = {}

        for condition in self._conditions:
            is_met = self._evaluate_condition(condition, game_state)

            if is_met:
                conditions_met.append(condition.id)
                for faction in condition.required_for:
                    faction_wins[faction] = faction_wins.get(faction, 0) + 1

                self.event_bus.publish(
                    VictoryConditionMetEvent(
                        winning_faction=condition.required_for[0]
                        if condition.required_for
                        else None,
                        condition_type=condition.condition_type.name,
                        timestamp=time.time(),
                    )
                )
            else:
                conditions_remaining.append(condition.id)

        if conditions_met:
            winning_faction = max(faction_wins.items(), key=lambda x: x[1])[0]
            result = VictoryCheckResult(
                victory_achieved=True,
                winning_faction=winning_faction,
                conditions_met=conditions_met,
                conditions_remaining=conditions_remaining,
                message=f"Victory! {winning_faction.upper()} achieves victory via: {', '.join(conditions_met)}",
            )

            self.event_bus.publish(
                GameOverEvent(
                    winner=winning_faction,
                    reason=result.message,
                    final_turn=game_state.get("current_turn", 0),
                    timestamp=time.time(),
                )
            )

            self._logger.info(f"VICTORY: {result.message}")
            return result

        return VictoryCheckResult(
            victory_achieved=False,
            winning_faction=None,
            conditions_met=[],
            conditions_remaining=conditions_remaining,
            message=f"Victory conditions not yet met. Remaining: {len(conditions_remaining)}",
        )

    def _evaluate_condition(self, condition: VictoryCondition, game_state: dict) -> bool:
        """Evaluate a single condition using registered evaluator."""
        evaluator = self._condition_evaluators.get(condition.condition_type)

        if evaluator:
            return evaluator(condition, game_state)

        self._logger.warning(f"No evaluator for condition type: {condition.condition_type.name}")
        return False

    def _register_default_evaluators(self) -> None:
        """Register built-in evaluators for standard condition types."""

        def evaluate_eliminate(condition: VictoryCondition, state: dict) -> bool:
            enemy_factions = [f for f in condition.required_for]
            units = state.get("units", [])
            enemy_units = [u for u in units if u.faction in enemy_factions and u.is_alive()]
            return len(enemy_units) == 0

        def evaluate_capture(condition: VictoryCondition, state: dict) -> bool:
            objective_id = condition.parameters.get("objective_id")
            captured = state.get("captured_objectives", [])
            return objective_id in captured

        def evaluate_survive(condition: VictoryCondition, state: dict) -> bool:
            required_turns = condition.parameters.get("turns", 10)
            current_turn = state.get("current_turn", 0)
            return current_turn >= required_turns

        self._condition_evaluators[VictoryConditionType.ELIMINATE_ALL_ENEMIES] = evaluate_eliminate
        self._condition_evaluators[VictoryConditionType.CAPTURE_OBJECTIVE] = evaluate_capture
        self._condition_evaluators[VictoryConditionType.SURVIVE_TURNS] = evaluate_survive

    @property
    def condition_count(self) -> int:
        """Get number of registered victory conditions."""
        return len(self._conditions)

    def get_conditions_summary(self) -> list[dict]:
        """Get summary of all registered conditions."""
        return [
            {
                "id": c.id,
                "type": c.condition_type.name,
                "description": c.description,
                "for_factions": c.required_for,
            }
            for c in self._conditions
        ]

    def reset(self) -> None:
        """Clear all conditions and state."""
        self._conditions.clear()
        self._logger.info("Victory checker reset")


import time
