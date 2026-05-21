"""
AI Service

Orchestrates AI decision-making for all AI-controlled units.
Manages behavior tree execution and tactical intent generation.
Integrates DifficultySystem, CommanderAI, SquadCoordinator, and CombatEngagement.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pycc2.domain.ai.behavior_tree import BTNode, NodeStatus
from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.perception_system import PerceptionSystem
from pycc2.domain.ai.tactic_executor import TacticExecutor
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import (
    FlankingAI,
    InfantryTankCoordAI,
    SuppressionAI,
    TacticalContext,
    TacticalOrchestrator,
    VictoryPointAI,
)
from pycc2.domain.ai.retreat_ai import RetreatDecisionAI
from pycc2.domain.ai.at_ambush_ai import ATAmbushAI
from pycc2.domain.ai.tick_scheduler import AITickScheduler
from pycc2.domain.entities.unit import Unit
from pycc2.services.event_bus import EventBus

if TYPE_CHECKING:
    from pycc2.domain.ai.combat_engagement import CombatEngagement
    from pycc2.domain.ai.commander_ai import CommanderAI
    from pycc2.domain.ai.difficulty_system import DifficultyLevel, DifficultySystem
    from pycc2.domain.ai.squad_coordinator import SquadCoordinator
    from pycc2.domain.systems.ballistic import BallisticEngine
    from pycc2.domain.systems.pathfinder import PathFinder


class AIService:
    """
    AI decision-making service.

    Manages AI-controlled units' behavior trees, generates tactical
    intents, and executes decided actions through the tactic executor.
    """

    def __init__(
        self,
        event_bus: EventBus,
        pathfinder: PathFinder | None = None,
        ballistic_engine: BallisticEngine | None = None,
        difficulty_system: DifficultySystem | None = None,
        squad_coordinator: SquadCoordinator | None = None,
        combat_engagement: CombatEngagement | None = None,
    ) -> None:
        self.event_bus = event_bus
        self._pathfinder = pathfinder
        self._ballistic_engine = ballistic_engine
        self._difficulty_system = difficulty_system
        self._squad_coordinator = squad_coordinator
        self._combat_engagement = combat_engagement
        self._commander: CommanderAI | None = None
        self._unit_trees: dict[str, BTNode] = {}
        self._blackboards: dict[str, Blackboard] = {}
        self._unit_entities: dict[str, Unit] = {}
        self._executor = TacticExecutor(
            event_bus=event_bus,
            pathfinder=pathfinder,
            ballistic_engine=ballistic_engine,
        )
        self._perception = PerceptionSystem()
        self._tactical_orchestrator = TacticalOrchestrator()
        self._tactical_orchestrator.register(FlankingAI())
        self._tactical_orchestrator.register(SuppressionAI())
        self._tactical_orchestrator.register(InfantryTankCoordAI())
        self._tactical_orchestrator.register(VictoryPointAI())
        self._tactical_orchestrator.register(RetreatDecisionAI())
        self._tactical_orchestrator.register(ATAmbushAI())
        self._tick_scheduler = AITickScheduler()
        self._current_tick: int = 0
        self._logger = logging.getLogger("pycc2.ai.service")

    def register_ai_unit(self, unit: Unit, behavior_tree: BTNode) -> None:
        """
        Register an AI-controlled unit with its behavior tree.

        Args:
            unit: The AI-controlled unit
            behavior_tree: Behavior tree defining unit's decision logic
        """
        self._unit_trees[unit.id] = behavior_tree
        self._blackboards[unit.id] = Blackboard()
        self._unit_entities[unit.id] = unit
        self._executor.register_unit(unit)
        self._logger.debug(f"Registered AI unit: {unit.name} [{unit.id}]")

    def unregister_ai_unit(self, unit_id: str) -> None:
        """Remove an AI unit from management."""
        if unit_id in self._unit_trees:
            del self._unit_trees[unit_id]
        if unit_id in self._blackboards:
            del self._blackboards[unit_id]
        if unit_id in self._unit_entities:
            del self._unit_entities[unit_id]
        self._executor.unregister_unit(unit_id)
        self._logger.debug(f"Unregistered AI unit: {unit_id}")

    @property
    def commander(self) -> CommanderAI | None:
        """Get the commander AI instance, if set."""
        return self._commander

    def set_commander(self, commander: CommanderAI) -> None:
        """
        Set the commander AI for this service.

        Args:
            commander: The commander AI instance
        """
        self._commander = commander
        self._logger.debug(f"Set commander: {commander.commander.name} [{commander.commander.id}]")

    def has_commander(self) -> bool:
        """Check if a commander AI is set."""
        return self._commander is not None

    def set_difficulty(self, level: DifficultyLevel) -> None:
        """
        Set the AI difficulty level.

        Args:
            level: The difficulty level to set
        """
        from pycc2.domain.ai.difficulty_system import DifficultySystem

        self._difficulty_system = DifficultySystem(level)
        self._logger.info(f"AI difficulty set to {level.name}")

    def get_battlefield_picture(self):
        """
        Get the commander's battlefield picture.

        Returns:
            BattlefieldPicture if commander is set, None otherwise
        """
        if self._commander:
            return self._commander.picture
        return None

    def tick(
        self,
        dt: float,
        game_map=None,
        all_units: list[Unit] | None = None,
        fog_of_war: dict[tuple[int, int], bool] | None = None,
    ) -> list[TacticIntent]:
        """
        Update all registered AI units and collect their decisions.

        Integrates difficulty system, combat engagement rules, commander AI,
        and squad coordination into the decision-making pipeline.

        Args:
            dt: Delta time since last update
            game_map: Game map for line-of-sight checks
            all_units: All units on the battlefield
            fog_of_war: Fog of war visibility dictionary

        Returns:
            List of tactic intents from all AI units
        """
        intents: list[TacticIntent] = []

        for unit_id, tree in self._unit_trees.items():
            blackboard = self._blackboards.get(unit_id)
            unit = self._unit_entities.get(unit_id)
            if blackboard is None or unit is None:
                continue

            # Use AITickScheduler to determine if this unit should decide this tick
            if not self._tick_scheduler.should_tick(unit, self._current_tick):
                continue

            self._perception.update_blackboard(
                blackboard=blackboard,
                unit=unit,
                game_map=game_map,
                all_units=all_units,
                fog_of_war=fog_of_war,
            )

            status = tree.tick(blackboard)

            if status == NodeStatus.SUCCESS:
                intent = blackboard.get_current_intent()
                if intent is not None and isinstance(intent, TacticIntent):
                    # Apply difficulty system modifications
                    if self._difficulty_system is not None:
                        modified_intent = self._difficulty_system.modify_ai_decision(
                            intent, blackboard
                        )
                        if modified_intent is None:
                            continue  # Delayed decision, skip this tick
                        intent = modified_intent

                    # Apply combat engagement rules if intent has a target
                    if intent.has_target and self._combat_engagement is not None:
                        target_unit = self._find_unit(intent.target_unit_id, all_units or [])
                        if unit and target_unit:
                            distance = unit.position.tile_coord.chebyshev_distance(
                                target_unit.position.tile_coord
                            )
                            engagement_result = self._combat_engagement.evaluate_engagement(
                                unit=unit,
                                target=target_unit,
                                distance=distance,
                                blackboard=blackboard,
                                difficulty_config=self._difficulty_system.config
                                if self._difficulty_system
                                else None,
                            )

                            from pycc2.domain.ai.combat_engagement import EngagementDecision

                            if engagement_result.decision == EngagementDecision.RETREAT:
                                intent = TacticIntent(
                                    unit_id=unit_id,
                                    tactic_type=TacticType.RETREAT,
                                    priority=intent.priority + 1,
                                )
                            elif engagement_result.decision == EngagementDecision.TAKE_COVER:
                                intent = TacticIntent(
                                    unit_id=unit_id,
                                    tactic_type=TacticType.TAKE_COVER,
                                    priority=intent.priority + 1,
                                )

                    if intent:
                        intents.append(intent)
                        self._log_ai_decision(unit_id, intent)
                        blackboard.remove("current_intent")

            elif status == NodeStatus.FAILURE:
                self._logger.debug(f"AI unit {unit_id} behavior tree failed")

        # Inject commander orders (higher priority than autonomous decisions)
        if self._commander is not None and all_units is not None:
            commander_orders = self._commander.generate_orders(
                managed_unit_ids=self.managed_unit_ids,
                all_units=all_units,
                squad_coordinator=self._squad_coordinator,
                difficulty_config=self._difficulty_system.config
                if self._difficulty_system
                else None,
            )
            commander_intents = self._commander.convert_to_unit_intents(commander_orders)

            # Commander orders override autonomous decisions for those units
            cmd_ids = {ci.unit_id for ci in commander_intents}
            intents = [i for i in intents if i.unit_id not in cmd_ids] + commander_intents

        # Apply squad coordination tactics if enabled by difficulty
        if (
            self._squad_coordinator is not None
            and self._difficulty_system
            and self._difficulty_system.should_coordinate()
        ):
            squad_intents = []
            for squad_id in self._squad_coordinator.active_squads:
                squad_blackboards = {
                    uid: self._blackboards[uid]
                    for uid in self._squad_coordinator.get_squad_units(squad_id)
                    if uid in self._blackboards
                }
                if squad_blackboards:
                    order = self._squad_coordinator.evaluate_squad_tactics(
                        squad_id, squad_blackboards, all_units or [], game_map
                    )
                    if order:
                        distributed = self._squad_coordinator.distribute_squad_order(order)
                        squad_intents.extend(distributed)
            intents.extend(squad_intents)

        # Run tactical orchestrator for higher-level tactical decisions
        if all_units and game_map is not None:
            tactical_intents = self._run_tactical_orchestrator(all_units, game_map)
            # Tactical intents override lower-priority autonomous decisions
            tactical_unit_ids = {ti.unit_id for ti in tactical_intents}
            intents = [i for i in intents if i.unit_id not in tactical_unit_ids] + tactical_intents
            # Execute tactical intents via TacticExecutor
            self.execute_intents(tactical_intents)

        self._current_tick += 1
        return intents

    def update_all(self, dt: float, context: dict) -> list[TacticIntent]:
        """Legacy interface - delegates to tick with context as perception data."""
        intents = []
        for unit_id, tree in self._unit_trees.items():
            blackboard = self._blackboards.get(unit_id)
            if blackboard is None:
                continue

            blackboard.update_context(context)
            status = tree.tick(blackboard)

            if status == NodeStatus.SUCCESS:
                intent = blackboard.get_current_intent()
                if intent is not None and isinstance(intent, TacticIntent):
                    intents.append(intent)
                    self._log_ai_decision(unit_id, intent)
                    blackboard.remove("current_intent")

            elif status == NodeStatus.FAILURE:
                self._logger.debug(f"AI unit {unit_id} behavior tree failed")

        return intents

    def update_single(self, unit_id: str, dt: float, context: dict) -> TacticIntent | None:
        """
        Update a single AI unit.

        Args:
            unit_id: ID of unit to update
            dt: Delta time
            context: Game state context

        Returns:
            Tactic intent if decision made, None otherwise
        """
        tree = self._unit_trees.get(unit_id)
        blackboard = self._blackboards.get(unit_id)

        if not tree or not blackboard:
            return None

        blackboard.update_context(context)
        status = tree.tick(blackboard)

        if status == NodeStatus.SUCCESS:
            intent = blackboard.get_current_intent()
            if intent is not None and isinstance(intent, TacticIntent):
                self._log_ai_decision(unit_id, intent)
                blackboard.remove("current_intent")
            return intent

        return None

    def execute_intents(self, intents: list[TacticIntent]) -> dict[str, bool]:
        """
        Execute a list of tactic intents.

        Args:
            intents: List of intents to execute

        Returns:
            Dictionary mapping unit IDs to execution success
        """
        results = {}
        for intent in intents:
            success = self._executor.execute(intent)
            results[intent.unit_id] = success
            if not success:
                self._logger.warning(
                    f"Failed to execute intent for {intent.unit_id}: {intent.tactic_type.value}"
                )
        return results

    def get_blackboard(self, unit_id: str) -> Blackboard | None:
        """Get the blackboard for a specific unit."""
        return self._blackboards.get(unit_id)

    def get_unit_tree(self, unit_id: str) -> BTNode | None:
        """Get the behavior tree for a specific unit."""
        return self._unit_trees.get(unit_id)

    def set_blackboard_value(self, unit_id: str, key: str, value) -> None:
        """Set a value on a unit's blackboard."""
        blackboard = self._blackboards.get(unit_id)
        if blackboard:
            blackboard.set(key, value)

    @property
    def managed_unit_count(self) -> int:
        """Get number of AI-managed units."""
        return len(self._unit_trees)

    @property
    def managed_unit_ids(self) -> list[str]:
        """Get list of all managed unit IDs."""
        return list(self._unit_trees.keys())

    def shutdown(self) -> None:
        """Clean up all AI state."""
        self._unit_trees.clear()
        self._blackboards.clear()
        self._unit_entities.clear()
        self._logger.info("AI service shut down")

    def _run_tactical_orchestrator(
        self, all_units: list[Unit], game_map
    ) -> list[TacticIntent]:
        """Build a TacticalContext and run the TacticalOrchestrator.

        Args:
            all_units: All units on the battlefield
            game_map: The current game map

        Returns:
            List of TacticIntent from the tactical orchestrator
        """
        managed_ids = set(self._unit_trees.keys())
        friendly_units = [u for u in all_units if u.id in managed_ids and u.is_alive]
        enemy_units = [u for u in all_units if u.id not in managed_ids and u.is_alive]

        context = TacticalContext(
            friendly_units=friendly_units,
            enemy_units=enemy_units,
            game_map=game_map,
            current_tick=self._current_tick,
            blackboards=self._blackboards,
            difficulty_config=self._difficulty_system.config
            if self._difficulty_system
            else None,
        )

        return self._tactical_orchestrator.tick(context)

    def get_tactical_summary(self) -> dict:
        """Return the current tactical AI state for debugging.

        Returns:
            Dict with registered AIs, last evaluation scores, and last orders
        """
        return {
            "registered_ais": self._tactical_orchestrator.registered_ais,
            "last_scores": self._tactical_orchestrator.last_scores,
            "last_order_count": len(self._tactical_orchestrator.last_orders),
            "current_tick": self._current_tick,
        }

    def _log_ai_decision(self, unit_id: str, intent: TacticIntent) -> None:
        """Log an AI decision for debugging."""
        self._logger.debug(
            f"AI Decision | Unit: {unit_id} | "
            f"Action: {intent.tactic_type.name} | "
            f"Target: {intent.target_position or intent.target_unit_id}"
        )

    def _find_unit(self, unit_id: str | None, all_units: list[Unit]) -> Unit | None:
        """
        Find a unit by ID from a list of units.

        Args:
            unit_id: The unit ID to find
            all_units: List of units to search

        Returns:
            Unit if found, None otherwise
        """
        if unit_id is None:
            return None
        for unit in all_units:
            if unit.id == unit_id:
                return unit
        return None
