"""Combat tactics mixin — extracted from tactic_executor.py (D11 SRP split).

Contains combat-related tactic execution methods used by the TacticExecutor
facade:
  - ``_execute_attack``: publishes PlayerCommand "attack" to event bus
  - ``_execute_suppress_fire``: 3x ballistic_engine.calculate_shot + events
  - ``_execute_clear_building``: approach + grenade + breach + clear
  - ``_execute_call_artillery``: ArtilleryManager fire mission (reads
    ``self._environment`` for weather scatter — pre-existing dead code,
    preserved verbatim)
  - ``_execute_melee_attack``: MeleeCombatSystem.resolve_melee + event
  - ``_execute_assault_fortified``: EngineerAssaultAI assault phases
  - ``_execute_counter_attack``: delegates to _execute_attack with priority+5
  - ``_execute_flanking``: delegates to _execute_move_to
  - ``_execute_set_ambush``: sets unit movement_mode to "sneak"
  - ``_execute_break_ambush``: restores "normal" + delegates to _execute_attack

This is a mixin — do not instantiate directly. The TacticExecutor facade
inherits this mixin and provides all required attributes via its __init__.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from pycc2.domain.ai.artillery_callin import ArtilleryManager
from pycc2.domain.ai.building_clearing import BuildingClearingAI
from pycc2.domain.ai.engineer_assault import EngineerAssaultAI
from pycc2.domain.ai.melee_combat import MeleeCombatSystem
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher
    from pycc2.domain.systems.ballistic import BallisticEngine
    from pycc2.domain.systems.pathfinder import PathFinder

__all__ = ["CombatTacticsMixin"]


class CombatTacticsMixin:
    """Combat tactic execution methods. Inherited by the TacticExecutor facade,
    not instantiated directly."""

    # -- Facade attributes used by combat methods (no defaults; set by TacticExecutor.__init__) --
    event_bus: IEventPublisher
    pathfinder: PathFinder | None
    ballistic_engine: BallisticEngine | None
    game_map: GameMap | None
    _unit_registry: dict[str, Unit]
    _engineer_assault_ai: EngineerAssaultAI
    _artillery_manager: ArtilleryManager
    # _environment is dead code: set to None in __init__ with no setter; read by
    # _execute_call_artillery for weather scatter. Preserved verbatim (pre-existing bug).
    _environment: None
    _logger: logging.Logger

    if TYPE_CHECKING:
        # -- Cross-mixin methods provided by other mixins / the facade --
        # Declared as TYPE_CHECKING-only stubs so mypy can verify combat
        # methods without runtime shadowing (facade is first in MRO; real
        # methods come from MovementTacticsMixin / TacticExecutor).
        def _get_unit(self, unit_id: str) -> Unit | None: ...
        def _execute_move_to(self, intent: TacticIntent) -> bool: ...

    def _execute_attack(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        target = self._get_unit(intent.target_unit_id or "") if intent.target_unit_id else None
        if unit is None or target is None:
            return False
        # Publish typed PlayerCommand so CombatDirector handles the full
        # attack pipeline (ballistics, damage, ammo, visual effects).
        from pycc2.domain.interfaces.event_types import PlayerCommand

        event: PlayerCommand = {
            "command": "attack",
            "unit_ids": [intent.unit_id],
        }
        if intent.target_unit_id is not None:
            event["target_id"] = intent.target_unit_id
        self.event_bus.publish(event)
        self._logger.debug(
            f"Unit {intent.unit_id} attack command issued -> {intent.target_unit_id}"
        )
        return True

    def _execute_suppress_fire(self, intent: TacticIntent) -> bool:
        unit = self._get_unit(intent.unit_id)
        target = self._get_unit(intent.target_unit_id or "") if intent.target_unit_id else None
        if unit is None or target is None:
            return False
        if self.ballistic_engine is None:
            self._logger.warning("No ballistic engine available for suppress fire")
            return False
        for _ in range(3):
            result = self.ballistic_engine.calculate_shot(
                attacker=unit, target=target, game_map=self.game_map
            )
            event = {
                "attacker_id": intent.unit_id,
                "target_id": intent.target_unit_id,
                "is_hit": result.hit,
                "damage": result.damage_dealt,
                "timestamp": time.time(),
            }
            self.event_bus.publish(event)
        self._logger.debug(f"Unit {intent.unit_id} suppressing fire on {intent.target_unit_id}")
        return True

    def _execute_clear_building(self, intent: TacticIntent) -> bool:
        """Execute a CLEAR_BUILDING intent.

        Moves the unit toward the building, then initiates the clearing
        process: approach, grenade, stack, breach, and clear.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        if self.game_map is None:
            self._logger.warning("No game map available for building clearing")
            return False

        if intent.target_position is None:
            self._logger.warning(f"CLEAR_BUILDING for {intent.unit_id} has no target_position")
            return False

        target_pos = intent.target_position
        unit_pos = unit.position.tile_coord

        # Check if unit is adjacent to the building
        dist = unit_pos.chebyshev_distance(target_pos)
        if dist > 1:
            # Move toward the building
            approach_pos = BuildingClearingAI.find_adjacent_approach_pos(
                target_pos, unit_pos, self.game_map
            )
            if approach_pos is None:
                self._logger.debug(f"Unit {intent.unit_id} cannot find approach to building")
                return False
            move_intent = TacticIntent(
                unit_id=intent.unit_id,
                tactic_type=TacticType.MOVE_TO,
                target_position=approach_pos,
                priority=intent.priority,
            )
            return self._execute_move_to(move_intent)

        # Unit is adjacent — apply grenade effects to defenders

        # Find all enemy units in the building
        defenders = [
            u
            for u in self._unit_registry.values()
            if u.is_alive
            and u.position.tile_coord == target_pos
            and u.id != intent.unit_id
            and u.faction != unit.faction
        ]

        # Apply grenade effects
        effects = BuildingClearingAI.apply_grenade_effects(target_pos, self.game_map, defenders)

        # Apply defender penalty
        for defender in defenders:
            BuildingClearingAI.apply_defender_penalty(defender)

        # Apply surprise bonus to attacker
        BuildingClearingAI.apply_surprise_bonus(unit)

        # Move unit into the building
        unit.move_to_tile(target_pos)

        # Publish event
        event = {
            "unit_id": intent.unit_id,
            "action": "clear_building",
            "building_pos": (target_pos.x, target_pos.y),
            "grenade_effects": len(effects),
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)

        self._logger.info(
            f"Unit {intent.unit_id} cleared building at "
            f"({target_pos.x}, {target_pos.y}), "
            f"{len(effects)} defenders hit by grenade"
        )
        return True

    def _execute_call_artillery(self, intent: TacticIntent) -> bool:
        """Execute a CALL_ARTILLERY intent.

        Initiates an artillery fire mission through the ArtilleryManager.
        The mission proceeds through phases: CALLING -> INCOMING -> IMPACT.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        if intent.target_position is None:
            self._logger.warning(f"CALL_ARTILLERY for {intent.unit_id} has no target_position")
            return False

        # Check if a new mission can be started
        if not self._artillery_manager.can_call_mission(intent.unit_id):
            self._logger.debug(
                f"Unit {intent.unit_id} cannot call artillery "
                f"(no missions remaining or already active)"
            )
            return False

        # Calculate weather scatter
        env = self._environment
        scatter = ArtilleryManager.calculate_weather_scatter(env)

        # Start the mission
        mission = self._artillery_manager.start_mission(
            observer_id=intent.unit_id,
            target_pos=intent.target_position,
            scatter=scatter,
        )
        if mission is None:
            return False

        # Publish event
        event = {
            "unit_id": intent.unit_id,
            "action": "call_artillery",
            "target_pos": (
                intent.target_position.x,
                intent.target_position.y,
            ),
            "scatter": scatter,
            "missions_remaining": self._artillery_manager.missions_remaining,
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)

        self._logger.info(
            f"Unit {intent.unit_id} called artillery on "
            f"({intent.target_position.x}, {intent.target_position.y}), "
            f"scatter={scatter}, "
            f"{self._artillery_manager.missions_remaining} missions remaining"
        )
        return True

    def _execute_melee_attack(self, intent: TacticIntent) -> bool:
        """Execute a MELEE_ATTACK intent.

        Resolves close-quarters combat between the attacker and defender.
        Both units can take damage (melee is risky).
        """
        unit = self._get_unit(intent.unit_id)
        target = self._get_unit(intent.target_unit_id or "") if intent.target_unit_id else None
        if unit is None or target is None:
            return False

        # Verify melee conditions
        if not MeleeCombatSystem.can_melee(unit, target):
            self._logger.debug(f"Unit {intent.unit_id} cannot melee target {intent.target_unit_id}")
            return False

        # Determine if charging (moving into melee)
        is_charging = unit.state_machine.current and unit.state_machine.current.name == "MOVING"

        # Resolve melee
        result = MeleeCombatSystem.resolve_melee(unit, target, is_charging)

        # Publish event
        event = {
            "attacker_id": intent.unit_id,
            "defender_id": intent.target_unit_id,
            "action": "melee_attack",
            "weapon": result.attacker_weapon.name,
            "hit": result.hit,
            "damage": result.damage,
            "counter_hit": result.counter_hit,
            "counter_damage": result.counter_damage,
            "attacker_killed": result.attacker_killed,
            "defender_killed": result.defender_killed,
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)

        self._logger.info(
            f"Melee: {intent.unit_id} vs {intent.target_unit_id}: "
            f"hit={result.hit}, dmg={result.damage}, "
            f"counter={result.counter_hit}, counter_dmg={result.counter_damage}"
        )
        return True

    def _execute_assault_fortified(self, intent: TacticIntent) -> bool:
        """Execute an ASSAULT_FORTIFIED intent.

        Engineer assault team attacks a fortified position using
        demo charges, flamethrowers, or bangalore torpedoes.
        The engineer assault AI manages the assault phases.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False

        if self.game_map is None:
            self._logger.warning("No game map available for engineer assault")
            return False

        if intent.target_position is None:
            self._logger.warning(f"ASSAULT_FORTIFIED for {intent.unit_id} has no target_position")
            return False

        # Check if unit has an active assault
        assault = self._engineer_assault_ai._assaults.get(intent.unit_id)

        if assault is None:
            # Start a new assault — move toward target
            dist = unit.position.tile_coord.chebyshev_distance(intent.target_position)
            if dist > 1:
                move_intent = TacticIntent(
                    unit_id=intent.unit_id,
                    tactic_type=TacticType.MOVE_TO,
                    target_position=intent.target_position,
                    priority=intent.priority,
                )
                return self._execute_move_to(move_intent)

        # Publish assault event
        event = {
            "unit_id": intent.unit_id,
            "action": "assault_fortified",
            "target_position": (
                intent.target_position.x,
                intent.target_position.y,
            ),
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)
        self._logger.info(
            f"Unit {intent.unit_id} assaulting fortified position at "
            f"({intent.target_position.x}, {intent.target_position.y})"
        )
        return True

    def _execute_counter_attack(self, intent: TacticIntent) -> bool:
        """Execute a COUNTER_ATTACK intent.

        A strategic counterattack is routed through the standard ATTACK
        pipeline (ballistics, damage, ammo, visual effects) but at a
        higher priority to reflect the committed, coordinated nature of
        the assault.
        """
        attack_intent = TacticIntent(
            unit_id=intent.unit_id,
            tactic_type=TacticType.ATTACK,
            priority=intent.priority + 5,
            target_unit_id=intent.target_unit_id,
            target_position=intent.target_position,
            path=intent.path,
        )
        return self._execute_attack(attack_intent)

    def _execute_flanking(self, intent: TacticIntent) -> bool:
        """Execute flanking maneuver by moving unit along a lateral path."""
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        if intent.target_position is not None:
            move_intent = TacticIntent(
                unit_id=intent.unit_id,
                tactic_type=TacticType.MOVE_TO,
                target_position=intent.target_position,
                priority=intent.priority,
                path=intent.path,
            )
            return self._execute_move_to(move_intent)
        self._logger.debug(f"Unit {intent.unit_id} flanking without destination")
        return True

    def _execute_set_ambush(self, intent: TacticIntent) -> bool:
        """Execute a SET_AMBUSH intent.

        Switches the unit into sneak movement mode so it stays concealed
        while waiting for the enemy to enter the kill zone.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        unit.set_movement_mode("sneak")
        self._logger.debug(f"Unit {intent.unit_id} set ambush (sneak mode)")
        return True

    def _execute_break_ambush(self, intent: TacticIntent) -> bool:
        """Execute a BREAK_AMBUSH intent.

        Triggers the ambush by transitioning to an ATTACK on the target
        enemy unit (reuses the standard ATTACK pipeline).
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        # Restore normal movement before assaulting
        unit.set_movement_mode("normal")
        attack_intent = TacticIntent(
            unit_id=intent.unit_id,
            tactic_type=TacticType.ATTACK,
            priority=intent.priority,
            target_unit_id=intent.target_unit_id,
            target_position=intent.target_position,
            path=intent.path,
        )
        return self._execute_attack(attack_intent)
