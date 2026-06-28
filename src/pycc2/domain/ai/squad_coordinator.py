"""Squad coordinator that assigns tactics and dispatches orders to squads."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.ai.blackboard import Blackboard
    from pycc2.domain.ai.squad_degradation import SquadDegradationManager
    from pycc2.domain.ai.tactic_intent import TacticIntent
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.tile_coord import TileCoord


class SquadTactic(Enum):
    """Named squad-level tactics that can be assigned to a SquadOrder."""

    FIRE_CONCENTRATION = auto()
    BOUNDING_OVERWATCH = auto()
    CROSSFIRE = auto()
    DEFENSIVE_LINE = auto()
    FLANKING = auto()


@dataclass(slots=True)
class SquadOrder:
    """Pending order carrying a tactic, target, and assigned unit ids for a squad."""

    squad_id: str
    tactic: SquadTactic
    target_unit_id: str | None = None
    target_position: TileCoord | None = None
    assigned_units: list[str] = field(default_factory=list)
    priority: int = 5


class SquadCoordinator:
    """Evaluates and dispatches squad-level tactics based on the tactical situation."""

    def __init__(self, degradation_manager: SquadDegradationManager | None = None) -> None:
        """Initialize the coordinator with optional squad degradation tracking."""
        self._squad_tactics: dict[str, SquadTactic] = {}
        self._pending_orders: list[SquadOrder] = []
        self._unit_squad_map: dict[str, str] = {}
        self._cooldowns: dict[str, int] = {}
        self._bounding_phase: dict[str, bool] = {}
        self._degradation_manager = degradation_manager

    def register_squad(self, squad_id: str, unit_ids: list[str]) -> None:
        """Map each unit id to the squad and initialize its default tactic."""
        for uid in unit_ids:
            self._unit_squad_map[uid] = squad_id
        if squad_id not in self._squad_tactics:
            self._squad_tactics[squad_id] = SquadTactic.FIRE_CONCENTRATION

    def unregister_squad(self, squad_id: str) -> None:
        """Remove a squad and clear all unit mappings and state for it."""
        to_remove = [uid for uid, sid in self._unit_squad_map.items() if sid == squad_id]
        for uid in to_remove:
            del self._unit_squad_map[uid]
        self._squad_tactics.pop(squad_id, None)
        self._cooldowns.pop(squad_id, None)
        self._bounding_phase.pop(squad_id, None)

    def evaluate_squad_tactics(
        self,
        squad_id: str,
        unit_blackboards: dict[str, Blackboard],
        all_units: list[Unit],
        game_map: GameMap,
    ) -> SquadOrder | None:
        """Evaluate and return the best squad order for the given squad, or None."""
        if squad_id not in self._squad_tactics:
            return None
        if self._cooldowns.get(squad_id, 0) > 0:
            return None

        squad_units = self._get_squad_units(squad_id, all_units)
        alive_units = [u for u in squad_units if u.is_alive]
        if len(alive_units) < 2:
            return None

        available_tactics = self._get_available_tactics(squad_id)

        visible_enemies = self._get_visible_enemies(unit_blackboards, alive_units, all_units)
        if len(visible_enemies) >= 2 and len(alive_units) >= 3:
            if "CROSSFIRE" in available_tactics and self._should_crossfire(
                visible_enemies, alive_units
            ):
                order = self._create_crossfire_order(squad_id, visible_enemies, alive_units)
                if order:
                    return order
            order = self._create_fire_concentration_order(squad_id, visible_enemies, alive_units)
            if order:
                return order

        if "BOUNDING_OVERWATCH" in available_tactics and self._should_bounding_overwatch(
            unit_blackboards, alive_units, game_map
        ):
            order = self._create_bounding_overwatch_order(squad_id, alive_units, game_map)
            if order:
                return order

        if self._should_defensive_line(alive_units, game_map):
            order = self._create_defensive_line_order(squad_id, alive_units, game_map)
            if order:
                return order

        if visible_enemies and len(alive_units) >= 2:
            if "FLANKING" in available_tactics and self._should_flank(visible_enemies, alive_units):
                order = self._create_flanking_order(squad_id, visible_enemies, alive_units)
                if order:
                    return order
            if len(visible_enemies) == 1 or len(alive_units) < 3:
                order = self._create_fire_concentration_order(
                    squad_id, visible_enemies, alive_units
                )
                if order:
                    return order

        return None

    def distribute_squad_order(self, order: SquadOrder) -> list[TacticIntent]:
        """Translate a squad order into per-unit tactic intents based on its tactic type."""
        intents: list[TacticIntent] = []
        units = order.assigned_units

        if not units:
            return intents

        match order.tactic:
            case SquadTactic.FIRE_CONCENTRATION:
                intents = self._distribute_fire_concentration(order, units)
            case SquadTactic.BOUNDING_OVERWATCH:
                intents = self._distribute_bounding_overwatch(order, units)
            case SquadTactic.CROSSFIRE:
                intents = self._distribute_crossfire(order, units)
            case SquadTactic.DEFENSIVE_LINE:
                intents = self._distribute_defensive_line(order, units)
            case SquadTactic.FLANKING:
                intents = self._distribute_flanking(order, units)

        return intents

    def get_squad_for_unit(self, unit_id: str) -> str | None:
        """Return the squad id for a unit, or None if not registered."""
        return self._unit_squad_map.get(unit_id)

    @property
    def active_squads(self) -> list[str]:
        """Return a list of all currently registered squad ids."""
        return list(self._squad_tactics.keys())

    def tick(self) -> None:
        """Decrement cooldowns for all squads each tick."""
        expired = [sid for sid, cd in self._cooldowns.items() if cd > 0]
        for sid in expired:
            self._cooldowns[sid] -= 1

    def get_squad_units(self, squad_id: str, all_units: list[Unit]) -> list[Unit]:
        """Return all units belonging to the given squad."""
        return self._get_squad_units(squad_id, all_units)

    def _get_squad_units(self, squad_id: str, all_units: list[Unit]) -> list[Unit]:
        return [u for u in all_units if u.squad_id == squad_id]

    def _get_visible_enemies(
        self,
        unit_blackboards: dict[str, Blackboard],
        friendly_units: list[Unit],
        all_units: list[Unit],
    ) -> list[Unit]:
        enemy_list: list[Unit] = []
        seen_ids: set[str] = set()

        if not friendly_units:
            return enemy_list

        faction = friendly_units[0].faction
        for unit in friendly_units:
            bb = unit_blackboards.get(unit.id)
            if not bb:
                continue
            visible = bb.get("visible_enemies", [])
            for enemy_id in visible:
                if enemy_id in seen_ids:
                    continue
                seen_ids.add(enemy_id)
                for u in all_units:
                    if u.id == enemy_id and u.is_alive and u.faction != faction:
                        enemy_list.append(u)
                        break
        return enemy_list

    def _select_primary_target(self, enemies: list[Unit]) -> Unit | None:
        if not enemies:
            return None
        return max(enemies, key=lambda e: e.health.hp)

    def _should_crossfire(self, enemies: list[Unit], friendly_units: list[Unit]) -> bool:
        return len(enemies) >= 2 and len(friendly_units) >= 3

    def _should_bounding_overwatch(
        self,
        unit_blackboards: dict[str, Blackboard],
        friendly_units: list[Unit],
        game_map: GameMap,
    ) -> bool:
        for unit in friendly_units:
            bb = unit_blackboards.get(unit.id)
            if bb and bb.get("has_unknown_ahead"):
                return True
        return False

    def _should_defensive_line(self, friendly_units: list[Unit], game_map: GameMap) -> bool:
        for obj in game_map.objectives:
            if obj.owner is None or obj.owner != friendly_units[0].faction.name.lower():
                for unit in friendly_units:
                    if unit.position.tile_coord.chebyshev_distance(obj.position) <= 5:
                        return True
        return False

    def _should_flank(self, enemies: list[Unit], friendly_units: list[Unit]) -> bool:
        if len(friendly_units) < 2 or not enemies:
            return False
        target = enemies[0]
        friends_in_front = sum(
            1
            for u in friendly_units
            if abs(u.position.tile_coord.x - target.position.tile_coord.x) < 3
        )
        return friends_in_front >= len(friendly_units) // 2

    def _create_fire_concentration_order(
        self,
        squad_id: str,
        enemies: list[Unit],
        friendly_units: list[Unit],
    ) -> SquadOrder | None:
        target = self._select_primary_target(enemies)
        if not target:
            return None
        return SquadOrder(
            squad_id=squad_id,
            tactic=SquadTactic.FIRE_CONCENTRATION,
            target_unit_id=target.id,
            assigned_units=[u.id for u in friendly_units],
            priority=7,
        )

    def _create_crossfire_order(
        self,
        squad_id: str,
        enemies: list[Unit],
        friendly_units: list[Unit],
    ) -> SquadOrder | None:
        target = self._select_primary_target(enemies)
        if not target:
            return None
        return SquadOrder(
            squad_id=squad_id,
            tactic=SquadTactic.CROSSFIRE,
            target_unit_id=target.id,
            target_position=target.position.tile_coord,
            assigned_units=[u.id for u in friendly_units],
            priority=7,
        )

    def _create_bounding_overwatch_order(
        self,
        squad_id: str,
        friendly_units: list[Unit],
        game_map: GameMap,
    ) -> SquadOrder | None:
        if not friendly_units:
            return None
        center_x = sum(u.position.tile_coord.x for u in friendly_units) // len(friendly_units)
        center_y = sum(u.position.tile_coord.y + 2 for u in friendly_units) // len(friendly_units)
        from pycc2.domain.value_objects.tile_coord import TileCoord

        target_pos = TileCoord(center_x, center_y)
        return SquadOrder(
            squad_id=squad_id,
            tactic=SquadTactic.BOUNDING_OVERWATCH,
            target_position=target_pos,
            assigned_units=[u.id for u in friendly_units],
            priority=6,
        )

    def _create_defensive_line_order(
        self,
        squad_id: str,
        friendly_units: list[Unit],
        game_map: GameMap,
    ) -> SquadOrder | None:
        if not friendly_units:
            return None
        for obj in game_map.objectives:
            if obj.owner is None or obj.owner != friendly_units[0].faction.name.lower():
                return SquadOrder(
                    squad_id=squad_id,
                    tactic=SquadTactic.DEFENSIVE_LINE,
                    target_position=obj.position,
                    assigned_units=[u.id for u in friendly_units],
                    priority=6,
                )
        return None

    def _create_flanking_order(
        self,
        squad_id: str,
        enemies: list[Unit],
        friendly_units: list[Unit],
    ) -> SquadOrder | None:
        target = enemies[0] if enemies else None
        if not target:
            return None
        return SquadOrder(
            squad_id=squad_id,
            tactic=SquadTactic.FLANKING,
            target_unit_id=target.id,
            target_position=target.position.tile_coord,
            assigned_units=[u.id for u in friendly_units],
            priority=7,
        )

    def _distribute_fire_concentration(
        self,
        order: SquadOrder,
        units: list[str],
    ) -> list[TacticIntent]:
        from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType

        intents: list[TacticIntent] = []
        if len(units) < 2:
            return intents

        attack_count = max(2, (len(units) * 2) // 3)
        for _i, unit_id in enumerate(units[:attack_count]):
            intents.append(
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.ATTACK,
                    priority=order.priority,
                    target_unit_id=order.target_unit_id,
                )
            )

        for unit_id in units[attack_count:]:
            intents.append(
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.SUPPRESS_FIRE,
                    priority=order.priority - 1,
                    target_unit_id=order.target_unit_id,
                )
            )

        return intents

    def _distribute_bounding_overwatch(
        self,
        order: SquadOrder,
        units: list[str],
    ) -> list[TacticIntent]:
        from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType

        intents: list[TacticIntent] = []
        mid = len(units) // 2
        alpha_group = units[:mid] if mid > 0 else units[:1]
        beta_group = units[mid:] if mid > 0 else []

        if not alpha_group:
            return intents

        is_alpha_moving = self._bounding_phase.get(order.squad_id, True)

        if is_alpha_moving:
            for unit_id in alpha_group:
                intents.append(
                    TacticIntent(
                        unit_id=unit_id,
                        tactic_type=TacticType.MOVE_TO,
                        priority=order.priority,
                        target_position=order.target_position,
                    )
                )
            for unit_id in beta_group:
                intents.append(
                    TacticIntent(
                        unit_id=unit_id,
                        tactic_type=TacticType.HOLD_POSITION,
                        priority=order.priority,
                    )
                )
                intents.append(
                    TacticIntent(
                        unit_id=unit_id,
                        tactic_type=TacticType.SUPPRESS_FIRE,
                        priority=order.priority - 1,
                    )
                )
        else:
            for unit_id in alpha_group:
                intents.append(
                    TacticIntent(
                        unit_id=unit_id,
                        tactic_type=TacticType.HOLD_POSITION,
                        priority=order.priority,
                    )
                )
            for unit_id in beta_group:
                intents.append(
                    TacticIntent(
                        unit_id=unit_id,
                        tactic_type=TacticType.MOVE_TO,
                        priority=order.priority,
                        target_position=order.target_position,
                    )
                )

        self._bounding_phase[order.squad_id] = not is_alpha_moving
        return intents

    def _distribute_crossfire(
        self,
        order: SquadOrder,
        units: list[str],
    ) -> list[TacticIntent]:
        from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
        from pycc2.domain.value_objects.tile_coord import TileCoord

        intents: list[TacticIntent] = []
        if not order.target_position or len(units) < 2:
            return intents

        tx, ty = order.target_position.x, order.target_position.y
        positions = [
            TileCoord(tx - 3, ty),
            TileCoord(tx + 3, ty),
            TileCoord(tx, ty - 3),
            TileCoord(tx, ty + 3),
        ]

        half = len(units) // 2
        for i, unit_id in enumerate(units[:half]):
            pos = positions[i % len(positions)]
            intents.append(
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.MOVE_TO,
                    priority=order.priority,
                    target_position=pos,
                )
            )

        for unit_id in units[half:]:
            intents.append(
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.ATTACK,
                    priority=order.priority,
                    target_unit_id=order.target_unit_id,
                )
            )

        return intents

    def _distribute_defensive_line(
        self,
        order: SquadOrder,
        units: list[str],
    ) -> list[TacticIntent]:
        from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
        from pycc2.domain.value_objects.tile_coord import TileCoord

        intents: list[TacticIntent] = []
        if not order.target_position:
            return intents

        base_x, base_y = order.target_position.x, order.target_position.y
        spacing = max(2, 8 // max(len(units), 1))

        for i, unit_id in enumerate(units):
            offset = (i - len(units) // 2) * spacing
            pos = TileCoord(base_x + offset, base_y)
            intents.append(
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.MOVE_TO,
                    priority=order.priority,
                    target_position=pos,
                )
            )
            intents.append(
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.DEFEND,
                    priority=order.priority - 1,
                )
            )

        return intents

    def _distribute_flanking(
        self,
        order: SquadOrder,
        units: list[str],
    ) -> list[TacticIntent]:
        from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
        from pycc2.domain.value_objects.tile_coord import TileCoord

        intents: list[TacticIntent] = []
        if len(units) < 2 or not order.target_position:
            return intents

        tx, ty = order.target_position.x, order.target_position.y
        flank_pos = TileCoord(tx + 4, ty)

        main_force_count = max(1, len(units) - 1)
        for unit_id in units[:main_force_count]:
            intents.append(
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.SUPPRESS_FIRE,
                    priority=order.priority,
                    target_unit_id=order.target_unit_id,
                )
            )

        for unit_id in units[main_force_count:]:
            intents.append(
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.MOVE_TO,
                    priority=order.priority,
                    target_position=flank_pos,
                )
            )
            intents.append(
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.ATTACK,
                    priority=order.priority + 1,
                    target_unit_id=order.target_unit_id,
                )
            )

        return intents

    def _get_available_tactics(self, squad_id: str) -> set[str]:
        if self._degradation_manager is None:
            return {
                "BOUNDING_OVERWATCH",
                "CROSSFIRE",
                "FLANKING",
                "FIRE_CONCENTRATION",
                "DEFENSIVE_LINE",
            }
        tactics = self._degradation_manager.get_available_tactics(squad_id)
        return set(tactics)
