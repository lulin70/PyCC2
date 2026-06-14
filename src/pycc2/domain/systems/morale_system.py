"""
Morale System — CC2-Authentic State Machine

Implements the 5-state morale model from Close Combat 2:
- RALLYED (>70): Full combat effectiveness, slight accuracy bonus near commander
- WAVERING (40-70): Slightly degraded response, normal operation
- PINNED (20-40): Cannot move, reduced fire accuracy, yellow warning icon
- BROKEN (<20): May refuse orders, attempts to flee, red panic icon
- ROUTING: Actively fleeing toward map edge, cannot be controlled

This system integrates with:
- MoraleComponent (domain/components/morale_component.py)
- SuppressionState (domain/systems/combat_mechanics_enhanced.py)
- Unit entity (domain/entities/unit.py)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Tuple

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.ai.squad_degradation import SquadDegradationManager
    from pycc2.domain.components.morale_component import MoraleComponent
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.vec2 import Vec2


class MoraleEvent(Enum):
    """Events that can affect unit morale."""
    ALLY_KILLED = auto()
    LEADER_KILLED = auto()
    UNDER_HEAVY_FIRE = auto()
    NEAR_EXPLOSION = auto()
    KILL_CONFIRMED = auto()
    RALLY = auto()
    IN_COVER = auto()
    COMMANDER_NEARBY = auto()
    PANIC_CONTAGION = auto()


class MoraleState(Enum):
    """CC2 morale states with behavioral effects."""
    RALLYED = "rallyed"      # >70: Full combat effectiveness
    WAVERING = "wavering"    # 40-70: Slightly degraded
    PINNED = "pinned"        # 20-40: Cannot move, reduced fire
    BROKEN = "broken"        # <20: May flee, refuses orders
    ROUTING = "routing"      # Actively fleeing


@dataclass
class RoutingTarget:
    """Target position for routing/fleeing unit."""
    position: Vec2 | None = None
    is_fleeing: bool = False
    flee_ticks_remaining: int = 0


@dataclass(slots=True)
class MoraleCalculationResult:
    """Result of a morale event calculation."""
    morale_delta: int
    suppression_delta: int
    state_changed: bool
    old_state: str | None
    new_state: str | None
    contagion_targets: list[str] = field(default_factory=list)


@dataclass
class MoraleCalculator:
    """Event-driven morale calculator with configurable weights.

    Calculates morale changes from discrete events (ally killed, leader
    killed, etc.) and provides panic contagion / natural recovery helpers.
    """
    EVENT_WEIGHTS: dict[MoraleEvent, int] = field(
        default_factory=lambda: {
            MoraleEvent.ALLY_KILLED: -15,
            MoraleEvent.LEADER_KILLED: -25,
            MoraleEvent.UNDER_HEAVY_FIRE: -5,
            MoraleEvent.NEAR_EXPLOSION: -20,
            MoraleEvent.KILL_CONFIRMED: 8,
            MoraleEvent.RALLY: 3,
            MoraleEvent.IN_COVER: 5,
            MoraleEvent.COMMANDER_NEARBY: 10,
            MoraleEvent.PANIC_CONTAGION: -10,
        }
    )
    degradation_manager: SquadDegradationManager | None = field(default=None)

    def calculate_event_effect(
        self,
        unit_morale: MoraleComponent,
        event: MoraleEvent,
        context: dict | None = None,
    ) -> MoraleCalculationResult:
        delta = self.EVENT_WEIGHTS.get(event, 0)
        old_value = unit_morale.value
        new_value = max(0, min(100, old_value + delta))
        old_state_name = unit_morale.state.name
        new_state_name = self.predict_state(new_value, 0)
        state_changed = old_state_name != new_state_name
        contagion_targets: list[str] = []
        if new_state_name in ("BROKEN", "ROUTING") and state_changed:
            contagion_targets = (context or {}).get("contagion_targets", [])
        return MoraleCalculationResult(
            morale_delta=delta,
            suppression_delta=0,
            state_changed=state_changed,
            old_state=old_state_name if state_changed else None,
            new_state=new_state_name if state_changed else None,
            contagion_targets=contagion_targets,
        )

    def calculate_natural_recovery(self, current_value: int, ticks_since_combat: int) -> int:
        if ticks_since_combat >= 30:
            return min(100, current_value + 5)
        return current_value

    def calculate_panic_contagion(
        self,
        squad_units: list[tuple[str, MoraleComponent]],
        panicked_unit_id: str,
    ) -> dict[str, int]:
        result: dict[str, int] = {}
        for unit_id, mc in squad_units:
            if unit_id == panicked_unit_id:
                continue
            if mc.state.name in ("BROKEN", "ROUTING"):
                continue
            result[unit_id] = -10
        return result

    def should_panic_contagion(self, unit: MoraleComponent) -> bool:
        return unit.state.name in ("BROKEN", "ROUTING")

    def notify_leader_killed(self, killed_unit: Unit, squad_units: list[Unit]) -> None:
        if self.degradation_manager is not None:
            self.degradation_manager.on_leader_killed(killed_unit, squad_units)

    @staticmethod
    def predict_state(
        current_value: int,
        delta: int,
        panic_thr: int = 30,
        rout_thr: int = 10,
    ) -> str:
        new_val = max(0, min(100, current_value + delta))
        if new_val > 70:
            return "RALLIED"
        elif new_val > 40:
            return "WAVERING"
        elif new_val > 20:
            return "PINNED"
        else:
            return "BROKEN"


class MoraleSystem:
    """
    Static utility class for morale state management.

    Provides CC2-authentic morale mechanics including:
    - State mapping from numeric values
    - Suppression application with morale impact
    - Passive recovery when not under fire
    - Routing/flight behavior detection
    """

    # Threshold constants (CC2 authentic)
    RALLYED_THRESHOLD: int = 70
    WAVERING_THRESHOLD: int = 40
    PINNED_THRESHOLD: int = 20
    BROKEN_THRESHOLD: int = 20  # Same as pinned upper bound

    # Recovery rates
    BASE_RECOVERY_RATE: float = 0.5       # Morale points per second
    COMMANDER_BONUS_MULTIPLIER: float = 2.0  # Near commander recovery bonus
    COVER_BONUS: float = 0.3              # In cover recovery bonus

    # Suppression impact on morale
    SUPPRESSION_TO_MORALE_RATIO: float = 0.3  # 30% of suppression affects morale

    # Routing behavior
    ROUTING_CHECK_INTERVAL: int = 30      # Check every 30 ticks
    ROUTING_FLEE_DURATION: int = 180      # 3 seconds at 60 FPS
    FLEE_CHANCE_BROKEN: float = 0.15      # 15% chance per check when broken
    FLEE_CHANCE_ROUTING: float = 0.4      # 40% chance when already routing

    @staticmethod
    def get_state(morale_value: int) -> MoraleState:
        """
        Map numeric morale value to state enum.

        Args:
            morale_value: Current morale (0-100)

        Returns:
            Corresponding MoraleState enum value
        """
        if morale_value > MoraleSystem.RALLYED_THRESHOLD:
            return MoraleState.RALLYED
        elif morale_value > MoraleSystem.WAVERING_THRESHOLD:
            return MoraleState.WAVERING
        elif morale_value > MoraleSystem.PINNED_THRESHOLD:
            return MoraleState.PINNED
        else:
            return MoraleState.BROKEN

    @staticmethod
    def _play_morale_collapse_voice(
        unit: "Unit",
        new_state: MoraleState,
        voice_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        """Play a morale collapse voice cry for the unit's faction.

        Args:
            unit: The unit whose morale collapsed
            new_state: The new morale state (BROKEN or ROUTING)
            voice_callback: Optional callback(state_value, faction) for voice playback.
                           If None, voice playback is skipped.
        """
        if voice_callback is None:
            return
        try:
            faction = unit.faction if hasattr(unit, 'faction') else None
            if faction is not None:
                voice_callback(new_state.value, faction)
        except Exception as e:
            logging.info(f"Morale collapse voice playback error: {e}")

    @staticmethod
    def apply_suppression(unit: Unit, amount: float, dt: float) -> dict:
        """
        Apply enemy fire suppression to unit's morale.

        Suppression from incoming fire reduces morale over time.
        Heavy suppression can push units into pinned/broken states.

        Args:
            unit: Target unit
            amount: Suppression points to apply
            dt: Delta time in seconds

        Returns:
            Dict with effects applied:
            - morale_delta: Change in morale value
            - state_changed: Whether state changed
            - new_state: New morale state (if changed)
            - current_morale: Updated morale value
        """
        if not hasattr(unit, 'morale') or unit.morale is None:
            return {
                'morale_delta': 0,
                'state_changed': False,
                'new_state': None,
                'current_morale': 0,
            }

        old_state = MoraleSystem.get_state(unit.morale.value)

        # Calculate morale reduction from suppression
        # Scale by delta time for frame-rate independence
        morale_reduction = int(amount * MoraleSystem.SUPPRESSION_TO_MORALE_RATIO * dt * 60)

        # Apply to morale component
        unit.morale.apply_delta(-morale_reduction)

        # Also add to suppression tracker if available
        if hasattr(unit.morale, 'add_suppression'):
            suppr_amount = int(amount * dt * 60)
            unit.morale.add_suppression(suppr_amount)

        new_state = MoraleSystem.get_state(unit.morale.value)
        state_changed = old_state != new_state

        result = {
            'morale_delta': -morale_reduction,
            'state_changed': state_changed,
            'new_state': new_state if state_changed else None,
            'current_morale': unit.morale.value,
        }

        # Log significant state changes
        if state_changed:
            logger.warning(
                f"[MORALE] {unit.name or unit.id} state change: "
                f"{old_state.value} -> {new_state.value} "
                f"(morale={unit.morale.value})"
            )

            # Trigger morale collapse voice when entering BROKEN/ROUTING
            if new_state in (MoraleState.BROKEN, MoraleState.ROUTING):
                MoraleSystem._play_morale_collapse_voice(unit, new_state)

        return result

    @staticmethod
    def update_morale_recovery(
        unit: Unit,
        dt: float,
        near_commander: bool = False,
        in_cover: bool = True
    ) -> dict:
        """
        Passive morale recovery when not under fire.

        Units naturally recover morale over time, faster when:
        - Near commander (leadership bonus)
        - In good cover (safety feeling)
        - Not recently taking damage

        Args:
            unit: Unit to recover
            dt: Delta time in seconds
            near_commander: Whether commander is nearby
            in_cover: Whether unit is in good cover

        Returns:
            Dict with recovery info:
            - recovered: Amount recovered
            - current_morale: Updated morale
            - state_changed: Whether state improved
        """
        if not hasattr(unit, 'morale') or unit.morale is None:
            return {'recovered': 0, 'current_morale': 0, 'state_changed': False}

        # Don't recover if currently routing or broken below threshold
        current_state = MoraleSystem.get_state(unit.morale.value)
        if current_state in (MoraleState.ROUTING, MoraleState.BROKEN):
            if unit.morale.value < MoraleSystem.PINNED_THRESHOLD:
                return {'recovered': 0, 'current_morale': unit.morale.value, 'state_changed': False}

        old_state = current_state

        # Calculate base recovery
        recovery = MoraleSystem.BASE_RECOVERY_RATE * dt

        # Apply bonuses
        if near_commander:
            recovery *= MoraleSystem.COMMANDER_BONUS_MULTIPLIER

        if in_cover:
            recovery += MoraleSystem.COVER_BONUS * dt

        # Faster recovery from low suppression
        if hasattr(unit.morale, 'suppression') and unit.morale.suppression == 0:
            recovery *= 1.5  # Bonus when fully recovered from suppression

        # Apply recovery (use natural_recovery if available for fractional tracking)
        if hasattr(unit.morale, 'natural_recovery'):
            unit.morale.natural_recovery()
            recovered_int = 1 if recovery >= 1.0 else 0
        else:
            recovered_int = int(recovery)
            if recovered_int > 0:
                unit.morale.apply_delta(recovered_int)

        # Decay suppression
        if hasattr(unit.morale, 'decay_suppression'):
            decay_amount = int(5 * dt * 60)  # 5 points per second at 60 FPS
            unit.morale.decay_suppression(decay_amount)

        new_state = MoraleSystem.get_state(unit.morale.value)

        return {
            'recovered': recovered_int,
            'current_morale': unit.morale.value,
            'state_changed': old_state != new_state and new_state.value > old_state.value,
        }

    @staticmethod
    def check_routing_behavior(unit: Unit, game_map: "GameMap" = None) -> Tuple[bool, object]:
        """
        Check if unit should attempt to flee.

        Broken units may refuse orders and try to flee toward map edge.
        Already routing units continue fleeing until they reach safety or rally.

        Args:
            unit: Unit to check

        Returns:
            Tuple of (should_flee, flee_target_position_or_None)

        Behavior:
        - BROKEN state: 15% chance per check interval to start routing
        - ROUTING state: 40% chance to continue fleeing
        - Returns target position (map edge direction) if fleeing
        """

        if not hasattr(unit, 'morale') or unit.morale is None:
            return (False, None)

        current_state = MoraleSystem.get_state(unit.morale.value)

        # Only check for broken/routing units
        if current_state not in (MoraleState.BROKEN, MoraleState.ROUTING):
            return (False, None)

        # Import random for chance calculation
        import random

        should_flee = False
        target_pos = None

        if current_state == MoraleState.BROKEN:
            # Chance to start routing
            if random.random() < MoraleSystem.FLEE_CHANCE_BROKEN:
                should_flee = True
                # Set routing state
                if hasattr(unit, '_routing_target'):
                    unit._routing_target = RoutingTarget(
                        is_fleeing=True,
                        flee_ticks_remaining=MoraleSystem.ROUTING_FLEE_DURATION
                    )

        elif current_state == MoraleState.ROUTING:
            # Continue routing or rally check
            if hasattr(unit, '_routing_target') and unit._routing_target.is_fleeing:
                if random.random() < MoraleSystem.FLEE_CHANCE_ROUTING:
                    should_flee = True
                    # Calculate flee direction (toward nearest map edge)
                    if hasattr(unit, 'position') and unit.position:
                        target_pos = MoraleSystem._calculate_flee_target(unit, game_map)
                        unit._routing_target.position = target_pos

                        # Decrease remaining ticks
                        if unit._routing_target.flee_ticks_remaining > 0:
                            unit._routing_target.flee_ticks_remaining -= 1
                else:
                    # Chance to stop routing (rally attempt)
                    if unit.morale.value > MoraleSystem.PINNED_THRESHOLD + 10:
                        unit._routing_target.is_fleeing = False

        return (should_flee, target_pos)

    @staticmethod
    def _calculate_flee_target(unit: "Unit", game_map: "GameMap" = None) -> tuple[int, int] | None:
        """
        Calculate target position for fleeing unit.

        Units flee toward the nearest map edge, away from known enemies.

        Args:
            unit: The fleeing unit
            game_map: The game map (needed for edge calculation)

        Returns:
            Target tile coordinates as (x, y) tuple, or None if map unavailable
        """
        if game_map is None:
            # Fallback: try to get map from unit's position
            return None

        if not hasattr(unit, 'position') or unit.position is None:
            return None

        ux = unit.position.tile_coord.x
        uy = unit.position.tile_coord.y

        map_w = game_map.width
        map_h = game_map.height

        # Calculate distance to each edge
        dist_left = ux
        dist_right = map_w - ux
        dist_top = uy
        dist_bottom = map_h - uy

        # Find nearest edge
        min_dist = min(dist_left, dist_right, dist_top, dist_bottom)

        if min_dist == dist_left:
            return (0, uy)  # Flee left
        elif min_dist == dist_right:
            return (map_w - 1, uy)  # Flee right
        elif min_dist == dist_top:
            return (ux, 0)  # Flee up
        else:
            return (ux, map_h - 1)  # Flee down

    @staticmethod
    def get_accuracy_modifier(morale_state: MoraleState) -> float:
        """
        Get accuracy modifier based on morale state.

        Args:
            morale_state: Current morale state

        Returns:
            Accuracy multiplier (1.0 = normal, <1.0 = penalty, >1.0 = bonus)
        """
        modifiers = {
            MoraleState.RALLYED: 1.05,   # Slight bonus
            MoraleState.WAVERING: 0.95,   # Slight penalty
            MoraleState.PINNED: 0.60,     # Major penalty (can still fire)
            MoraleState.BROKEN: 0.30,     # Severe penalty
            MoraleState.ROUTING: 0.10,    # Minimal (fleeing)
        }
        return modifiers.get(morale_state, 1.0)

    @staticmethod
    def get_movement_modifier(morale_state: MoraleState) -> float:
        """
        Get movement speed modifier based on morale state.

        Args:
            morale_state: Current morale state

        Returns:
            Speed multiplier (0.0 = cannot move, 1.5 = fleeing speed)
        """
        modifiers = {
            MoraleState.RALLYED: 1.0,     # Normal
            MoraleState.WAVERING: 0.85,   # Slower response
            MoraleState.PINNED: 0.0,      # Cannot move!
            MoraleState.BROKEN: 0.50,     # Reluctant movement
            MoraleState.ROUTING: 1.5,     # Running away fast
        }
        return modifiers.get(morale_state, 1.0)

    @staticmethod
    def can_move(unit: Unit) -> bool:
        """
        Check if unit is capable of moving.

        Pinned units cannot move at all.
        Broken units may refuse movement orders.

        Args:
            unit: Unit to check

        Returns:
            True if unit can move, False otherwise
        """
        if not hasattr(unit, 'morale') or unit.morale is None:
            return True  # No morale system = can always move

        current_state = MoraleSystem.get_state(unit.morale.value)

        if current_state == MoraleState.PINNED:
            return False  # Definitely cannot move

        if current_state == MoraleState.BROKEN:
            # 70% chance to refuse orders
            import random
            return random.random() > 0.7

        return True

    @staticmethod
    def can_accept_orders(unit: Unit) -> bool:
        """
        Check if unit will accept player/AI orders.

        Broken and routing units may ignore commands.

        Args:
            unit: Unit to check

        Returns:
            True if unit accepts orders, False if refusing
        """
        if not hasattr(unit, 'morale') or unit.morale is None:
            return True

        current_state = MoraleSystem.get_state(unit.morale.value)

        if current_state == MoraleState.ROUTING:
            return False  # Completely uncontrollable

        if current_state == MoraleState.BROKEN:
            # High chance to refuse
            import random
            return random.random() > 0.6

        return True

    @staticmethod
    def apply_panic_contagion(unit: "Unit", all_units: list["Unit"]) -> None:
        """Apply morale penalty to nearby friendly units when this unit breaks.

        When a squad member enters BROKEN or ROUTING state, nearby friendly
        units (within 10 tiles) suffer a morale penalty of -5.
        """
        if not hasattr(unit, 'morale') or unit.morale is None:
            return

        # Only apply if this unit is in BROKEN or ROUTING state
        state = MoraleSystem.get_state(unit.morale.value)
        if state not in (MoraleState.BROKEN, MoraleState.ROUTING):
            return

        ux = unit.position.tile_coord.x
        uy = unit.position.tile_coord.y

        for other in all_units:
            if other.id == unit.id:
                continue
            if other.faction != unit.faction:
                continue
            if not hasattr(other, 'morale') or other.morale is None:
                continue

            ox = other.position.tile_coord.x
            oy = other.position.tile_coord.y
            dist = ((ux - ox) ** 2 + (uy - oy) ** 2) ** 0.5

            if dist <= 10:  # Within 10 tiles
                other.morale.apply_delta(-5)

    @staticmethod
    def apply_nco_rally(all_units: list["Unit"]) -> None:
        """Apply NCO rally bonus to nearby friendly units.

        When a COMMANDER or officer-type unit is within 5 tiles of a
        broken/wavering unit, that unit gets +15 morale per tick.
        """
        from pycc2.domain.entities.unit import UnitType

        # Find all NCO/commander units
        ncos = [u for u in all_units
                if u.is_alive and u.unit_type == UnitType.COMMANDER
                and hasattr(u, 'morale') and u.morale is not None]

        for nco in ncos:
            nx = nco.position.tile_coord.x
            ny = nco.position.tile_coord.y

            for unit in all_units:
                if unit.id == nco.id:
                    continue
                if unit.faction != nco.faction:
                    continue
                if not unit.is_alive:
                    continue
                if not hasattr(unit, 'morale') or unit.morale is None:
                    continue

                ux = unit.position.tile_coord.x
                uy = unit.position.tile_coord.y
                dist = ((nx - ux) ** 2 + (ny - uy) ** 2) ** 0.5

                if dist <= 5:  # Within 5 tiles
                    state = MoraleSystem.get_state(unit.morale.value)
                    if state in (MoraleState.WAVERING, MoraleState.BROKEN):
                        unit.morale.apply_delta(15)


def demo_morale_system():
    """Demonstrate the morale system functionality."""
    logger.info("=" * 80)
    logger.info("🎖️  MORALE SYSTEM DEMO — CC2 Authentic State Machine")
    logger.info("=" * 80)

    # Test state mapping
    logger.info("📊 State Mapping Tests:")
    test_values = [85, 72, 55, 30, 15]
    for val in test_values:
        state = MoraleSystem.get_state(val)
        acc_mod = MoraleSystem.get_accuracy_modifier(state)
        move_mod = MoraleSystem.get_movement_modifier(state)
        logger.info("   Morale %3d → %-10s | Accuracy: %.2fx | Movement: %.2fx",
                    val, state.value, acc_mod, move_mod)

    logger.info("✅ Morale System Ready for Integration!")


if __name__ == '__main__':
    demo_morale_system()
