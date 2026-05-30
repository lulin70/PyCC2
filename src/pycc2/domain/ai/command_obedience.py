"""
Command Obedience System — CC2-Authentic Morale-Based Order Compliance

CC2 core feature: units with low morale may refuse or delay orders.
This mirrors the real-world phenomenon where terrified soldiers
disobey, freeze, or flee rather than follow suicidal commands.

Obedience levels based on morale state:
  - NORMAL:    100% obey, 0 tick delay
  - SUPPRESSED: 80% obey, 1-3 tick delay
  - PANIC:      30% obey, 5-10 tick delay
  - ROUTING:     5% obey, refuses most orders (only retreat/cover)

When an order is refused:
  - Unit stays in place or continues current action
  - If under fire, seeks cover instead
  - Player/AI commander gets "order refused" feedback

Self-preservation: units won't execute suicidal orders
(charging MG in open, AT rifle vs tank frontal armor)

Integration: modify TacticExecutor to check obedience before executing
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.components.morale_component import MoraleState
from pycc2.domain.entities.unit import UnitType

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Obedience probability and delay by morale state
OBEDIENCE_TABLE: dict[MoraleState, tuple[float, tuple[int, int]]] = {
    MoraleState.RALLIED:   (1.00, (0, 0)),    # 100% obey, no delay
    MoraleState.WAVERING:  (0.80, (1, 3)),    # 80% obey, 1-3 tick delay
    MoraleState.PINNED:    (0.50, (3, 6)),    # 50% obey, 3-6 tick delay
    MoraleState.BROKEN:    (0.30, (5, 10)),   # 30% obey, 5-10 tick delay
    MoraleState.ROUTING:   (0.05, (5, 10)),   # 5% obey, 5-10 tick delay
}

# Orders that routing units will still accept
ROUTING_ALLOWED_ORDERS: set[TacticType] = {
    TacticType.RETREAT,
    TacticType.TAKE_COVER,
}

# Orders considered suicidal in certain contexts
_SUICIDAL_ATTACK_TYPES: set[UnitType] = {
    UnitType.MACHINE_GUN_SQUAD,
    UnitType.TANK,
}


# ---------------------------------------------------------------------------
# Obedience result
# ---------------------------------------------------------------------------

class ObedienceResult(Enum):
    OBEY = auto()            # Unit will execute the order
    DELAYED = auto()         # Unit will execute after a delay
    REFUSED = auto()         # Unit refuses the order
    SUICIDAL = auto()        # Order is suicidal, unit refuses


@dataclass(slots=True)
class ObedienceCheck:
    """Result of checking whether a unit will obey an order."""
    result: ObedienceResult
    delay_ticks: int = 0
    reason: str = ""


@dataclass(slots=True)
class DelayedOrder:
    """An order that has been delayed due to low morale."""
    intent: TacticIntent
    ticks_remaining: int


# ---------------------------------------------------------------------------
# CommandObedienceSystem
# ---------------------------------------------------------------------------

class CommandObedienceSystem:
    """Determines whether a unit will obey a given order based on morale.

    Usage::

        obedience = CommandObedienceSystem(event_bus=event_bus)
        # Before executing an order:
        check = obedience.check_obedience(unit, intent, context_units)
        if check.result == ObedienceResult.OBEY:
            executor.execute(intent)
        elif check.result == ObedienceResult.DELAYED:
            obedience.delay_order(intent, check.delay_ticks)
        else:
            # Order refused — unit stays or seeks cover
            ...
        # Each tick:
        obedience.tick()
    """

    def __init__(self, event_bus: IEventPublisher) -> None:
        self.event_bus = event_bus
        self._delayed_orders: dict[str, DelayedOrder] = {}
        self._logger = logging.getLogger("pycc2.ai.command_obedience")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_obedience(
        self,
        unit: Unit,
        intent: TacticIntent,
        context_units: list[Unit] | None = None,
    ) -> ObedienceCheck:
        """Check whether *unit* will obey *intent*.

        Returns an ObedienceCheck with:
          - result: OBEY, DELAYED, REFUSED, or SUICIDAL
          - delay_ticks: number of ticks to wait (if DELAYED)
          - reason: human-readable explanation

        The check considers:
          1. Morale state → obedience probability and delay
          2. Self-preservation → suicidal order detection
          3. Routing restriction → only retreat/cover allowed
        """
        morale_state = unit.morale.state

        # Step 1: Check for suicidal orders
        if self._is_suicidal_order(unit, intent, context_units):
            self._publish_refused_event(unit, intent, "suicidal_order")
            return ObedienceCheck(
                result=ObedienceResult.SUICIDAL,
                reason=f"Unit refuses suicidal order: {intent.tactic_type.name}",
            )

        # Step 2: Routing units only accept retreat/cover
        if morale_state == MoraleState.ROUTING and intent.tactic_type not in ROUTING_ALLOWED_ORDERS:
            self._publish_refused_event(unit, intent, "routing")
            return ObedienceCheck(
                result=ObedienceResult.REFUSED,
                reason=f"Routing unit refuses: {intent.tactic_type.name}",
            )

        # Step 3: Roll for obedience based on morale state
        obey_chance, (min_delay, max_delay) = OBEDIENCE_TABLE[morale_state]

        if random.random() > obey_chance:
            # Order refused
            self._publish_refused_event(unit, intent, morale_state.name)
            return ObedienceCheck(
                result=ObedienceResult.REFUSED,
                reason=f"Unit refuses order (morale: {morale_state.name})",
            )

        # Step 4: Calculate delay
        delay = 0
        if min_delay > 0:
            delay = random.randint(min_delay, max_delay)

        if delay > 0:
            return ObedienceCheck(
                result=ObedienceResult.DELAYED,
                delay_ticks=delay,
                reason=f"Order delayed {delay} ticks (morale: {morale_state.name})",
            )

        return ObedienceCheck(
            result=ObedienceResult.OBEY,
            reason="Unit obeys order",
        )

    def delay_order(self, intent: TacticIntent, delay_ticks: int) -> None:
        """Register an order as delayed for a unit."""
        self._delayed_orders[intent.unit_id] = DelayedOrder(
            intent=intent,
            ticks_remaining=delay_ticks,
        )
        self._logger.debug(
            f"Order {intent.tactic_type.name} for {intent.unit_id} "
            f"delayed by {delay_ticks} ticks"
        )

    def tick(self) -> list[TacticIntent]:
        """Advance all delayed orders by one tick.

        Returns a list of TacticIntents whose delay has expired and
        are now ready for execution.
        """
        ready: list[TacticIntent] = []

        for unit_id, delayed in list(self._delayed_orders.items()):
            delayed.ticks_remaining -= 1
            if delayed.ticks_remaining <= 0:
                ready.append(delayed.intent)
                del self._delayed_orders[unit_id]
                self._logger.debug(
                    f"Delayed order {delayed.intent.tactic_type.name} "
                    f"for {unit_id} is now ready"
                )

        return ready

    def get_delayed_order(self, unit_id: str) -> DelayedOrder | None:
        """Return the delayed order for a unit, if any."""
        return self._delayed_orders.get(unit_id)

    def has_delayed_order(self, unit_id: str) -> bool:
        return unit_id in self._delayed_orders

    @property
    def delayed_order_count(self) -> int:
        return len(self._delayed_orders)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _is_suicidal_order(
        self,
        unit: Unit,
        intent: TacticIntent,
        context_units: list[Unit] | None,
    ) -> bool:
        """Detect suicidal orders that a self-preserving unit would refuse.

        A suicidal order is one where:
          - Charging an MG in open terrain (ATTACK/MOVE_TO toward MG with no cover)
          - AT rifle vs tank frontal armor at close range
          - Attacking while critically wounded (hp_ratio < 0.15)
        """
        if intent.tactic_type not in (
            TacticType.ATTACK,
            TacticType.MOVE_TO,
            TacticType.COORDINATED_ADVANCE,
            TacticType.FLANKING,
        ):
            return False

        # Critically wounded units refuse attack orders
        if unit.health.hp_ratio < 0.15 and intent.tactic_type == TacticType.ATTACK:
            return True

        if context_units is None:
            return False

        # Find the target unit if specified
        target_id = intent.target_unit_id
        if target_id is None:
            return False

        target = None
        for u in context_units:
            if u.id == target_id:
                target = u
                break

        if target is None:
            return False

        # Charging MG in open terrain
        if target.unit_type == UnitType.MACHINE_GUN_SQUAD and intent.tactic_type == TacticType.ATTACK:
            # Check if unit is in open terrain (no cover)
            concealment = unit.concealment_level
            if concealment < 0.1:
                return True

        # AT rifle vs tank frontal armor at close range
        if target.unit_type == UnitType.TANK and unit.weapon.primary_weapon_id in ("at_gun", "piat", "bazooka", "panzerschreck"):
            dist = unit.position.tile_coord.chebyshev_distance(
                target.position.tile_coord
            )
            # AT vs tank at very close range is suicidal
            if dist <= 3:
                return True

        return False

    def _publish_refused_event(
        self,
        unit: Unit,
        intent: TacticIntent,
        reason: str,
    ) -> None:
        """Publish an event when a unit refuses an order."""
        self.event_bus.publish({
            "action": "order_refused",
            "unit_id": unit.id,
            "tactic_type": intent.tactic_type.name,
            "reason": reason,
        })
        self._logger.info(
            f"Unit {unit.id} refused order {intent.tactic_type.name}: {reason}"
        )
