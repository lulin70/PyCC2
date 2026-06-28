"""Tank Riders — CC2-Authentic Tank Riding Behavior

Infantry can ride on friendly tanks for rapid transport, mirroring
the real WWII practice where infantry hitched rides on armor to
keep pace with rapid advances.

Components:
  1. TankRiderSystem  — Manages mount/dismount state and rider effects
  2. TankRiderAI      — Evaluates when infantry should ride tanks

Mount conditions:
  - Infantry within 2 tiles of friendly tank
  - Tank is stationary or moving slowly
  - Not in combat (no enemies within 10 tiles)
  - Tank has capacity (max 4 riders per tank)

Mount/dismount:
  - Mount takes 3 ticks
  - Dismount takes 1 tick (can dismount instantly when under fire)
  - Auto-dismount when tank takes hit (riders thrown off, 10% injury chance)

While riding:
  - Infantry moves with tank speed
  - Infantry is EXPOSED (no cover, +50% damage from HE)
  - Infantry can fire from tank (but -30% accuracy, moving platform)
  - Riders visible to enemy (no concealment)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import UnitType

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MOUNT_RANGE: int = 2  # Max tiles to mount a tank
MOUNT_TICKS: int = 3  # Ticks to complete mounting
DISMOUNT_TICKS: int = 1  # Ticks to complete dismounting
MAX_RIDERS_PER_TANK: int = 4  # Maximum riders per tank
COMBAT_FREE_RADIUS: int = 10  # No enemies within this range to mount
AUTO_DISMOUNT_ENEMY_RADIUS: int = 8  # Auto-dismount when enemy this close
INJURY_CHANCE_ON_THROWN: float = 0.10  # 10% injury when thrown off
HE_DAMAGE_BONUS: float = 0.50  # +50% HE damage to riders
ACCURACY_PENALTY: float = 0.30  # -30% accuracy while riding

_INFANTRY_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.COMMANDER,
    UnitType.SNIPER_TEAM,
    UnitType.MEDIC_TEAM,
}


# ---------------------------------------------------------------------------
# Rider state
# ---------------------------------------------------------------------------


class RiderStatus(Enum):
    """Lifecycle states of an infantry unit riding on a tank."""

    APPROACHING = auto()  # Moving toward tank
    MOUNTING = auto()  # Mounting in progress
    RIDING = auto()  # Actively riding
    DISMOUNTING = auto()  # Dismounting in progress
    DISMOUNTED = auto()  # Just dismounted


@dataclass(slots=True)
class RiderSlot:
    """Tracks a single infantry unit riding (or mounting) a tank."""

    rider_id: str
    tank_id: str
    status: RiderStatus = RiderStatus.APPROACHING
    mount_progress: int = 0  # 0 to MOUNT_TICKS
    dismount_progress: int = 0  # 0 to DISMOUNT_TICKS


@dataclass(slots=True)
class TankRiderManifest:
    """Tracks all riders for a single tank."""

    tank_id: str
    riders: list[RiderSlot] = field(default_factory=list)

    @property
    def active_rider_count(self) -> int:
        """Return the number of riders currently mounting or riding the tank."""
        return sum(1 for r in self.riders if r.status in (RiderStatus.MOUNTING, RiderStatus.RIDING))

    @property
    def has_capacity(self) -> bool:
        """Return whether the tank can accept additional riders."""
        return self.active_rider_count < MAX_RIDERS_PER_TANK


# ---------------------------------------------------------------------------
# TankRiderSystem
# ---------------------------------------------------------------------------


class TankRiderSystem:
    """Manages the tank riding process for all infantry-tank pairs.

    Responsibilities:
      - Track rider manifests per tank
      - Handle mount/dismount progress
      - Apply riding effects (exposure, accuracy penalty)
      - Handle auto-dismount events (tank hit, enemy spotted)
    """

    def __init__(self) -> None:
        """Initialize the tank rider system with empty manifests and rider mappings."""
        self._manifests: dict[str, TankRiderManifest] = {}
        self._rider_to_tank: dict[str, str] = {}  # rider_id -> tank_id

    @property
    def active_manifests(self) -> list[TankRiderManifest]:
        """Return a list of all rider manifests currently tracked."""
        return list(self._manifests.values())

    def can_mount(
        self,
        rider: Unit,
        tank: Unit,
        all_units: list[Unit],
    ) -> bool:
        """Check if an infantry unit can mount a friendly tank."""
        # Must be alive infantry
        if not rider.is_alive or not rider.can_act:
            return False
        if rider.unit_type not in _INFANTRY_TYPES:
            return False

        # Tank must be alive
        if not tank.is_alive or tank.unit_type != UnitType.TANK:
            return False

        # Must be same faction
        if rider.faction != tank.faction:
            return False

        # Must be within mount range
        dist = rider.position.tile_coord.chebyshev_distance(tank.position.tile_coord)
        if dist > MOUNT_RANGE:
            return False

        # Tank must have capacity
        manifest = self._manifests.get(tank.id)
        if manifest is not None and not manifest.has_capacity:
            return False

        # Must not be in combat (no enemies within radius)
        if self._enemies_nearby(rider, all_units, COMBAT_FREE_RADIUS):
            return False

        # Must not already be riding
        return rider.id not in self._rider_to_tank

    def start_mount(self, rider: Unit, tank: Unit) -> bool:
        """Start the mounting process for a rider onto a tank."""
        if rider.id in self._rider_to_tank:
            return False

        manifest = self._manifests.get(tank.id)
        if manifest is None:
            manifest = TankRiderManifest(tank_id=tank.id)
            self._manifests[tank.id] = manifest

        if not manifest.has_capacity:
            return False

        slot = RiderSlot(
            rider_id=rider.id,
            tank_id=tank.id,
            status=RiderStatus.MOUNTING,
            mount_progress=0,
        )
        manifest.riders.append(slot)
        self._rider_to_tank[rider.id] = tank.id

        logger.debug(f"Unit {rider.id} started mounting tank {tank.id}")
        return True

    def start_dismount(self, rider_id: str, instant: bool = False) -> bool:
        """Start the dismounting process for a rider.

        If instant=True, the rider dismounts immediately (e.g., under fire).
        """
        tank_id = self._rider_to_tank.get(rider_id)
        if tank_id is None:
            return False

        manifest = self._manifests.get(tank_id)
        if manifest is None:
            return False

        slot = self._find_slot(manifest, rider_id)
        if slot is None:
            return False

        if instant:
            self._complete_dismount(manifest, slot)
            return True

        slot.status = RiderStatus.DISMOUNTING
        slot.dismount_progress = 0
        logger.debug(f"Unit {rider_id} started dismounting from tank {tank_id}")
        return True

    def tick(self, all_units: list[Unit]) -> list[RiderSlot]:
        """Advance all mount/dismount progress by one tick.

        Returns list of RiderSlots that completed a state transition this tick.
        """
        completed: list[RiderSlot] = []

        for tank_id, manifest in list(self._manifests.items()):
            tank = self._find_unit(tank_id, all_units)

            for slot in list(manifest.riders):
                rider = self._find_unit(slot.rider_id, all_units)

                # Clean up dead/invalid riders
                if rider is None or not rider.is_alive or tank is None or not tank.is_alive:
                    self._remove_rider(manifest, slot)
                    continue

                if slot.status == RiderStatus.MOUNTING:
                    slot.mount_progress += 1
                    if slot.mount_progress >= MOUNT_TICKS:
                        slot.status = RiderStatus.RIDING
                        slot.mount_progress = MOUNT_TICKS
                        completed.append(slot)
                        logger.debug(f"Unit {slot.rider_id} mounted tank {tank_id}")

                elif slot.status == RiderStatus.RIDING:
                    # Move rider with tank
                    rider.move_to_tile(tank.position.tile_coord)

                    # Check auto-dismount conditions
                    if self._enemies_nearby(rider, all_units, AUTO_DISMOUNT_ENEMY_RADIUS):
                        self.start_dismount(slot.rider_id, instant=True)
                        completed.append(slot)

                elif slot.status == RiderStatus.DISMOUNTING:
                    slot.dismount_progress += 1
                    if slot.dismount_progress >= DISMOUNT_TICKS:
                        self._complete_dismount(manifest, slot)
                        completed.append(slot)

            # Clean up empty manifests
            if not manifest.riders:
                self._manifests.pop(tank_id, None)

        return completed

    def handle_tank_hit(self, tank_id: str, all_units: list[Unit]) -> list[str]:
        """Handle a tank being hit — all riders are thrown off.

        Returns list of rider IDs that were thrown off.
        Each rider has a 10% chance of injury.
        """
        manifest = self._manifests.get(tank_id)
        if manifest is None:
            return []

        thrown: list[str] = []
        import random

        for slot in list(manifest.riders):
            if slot.status in (RiderStatus.MOUNTING, RiderStatus.RIDING):
                rider = self._find_unit(slot.rider_id, all_units)
                if (
                    rider is not None
                    and rider.is_alive
                    and random.random() < INJURY_CHANCE_ON_THROWN
                ):
                    # 10% injury chance
                    rider.take_damage(5)
                    logger.info(f"Rider {slot.rider_id} injured when thrown from tank {tank_id}")

                self._remove_rider(manifest, slot)
                thrown.append(slot.rider_id)

        if not manifest.riders:
            self._manifests.pop(tank_id, None)

        return thrown

    def is_riding(self, rider_id: str) -> bool:
        """Check if a unit is currently riding a tank."""
        tank_id = self._rider_to_tank.get(rider_id)
        if tank_id is None:
            return False
        manifest = self._manifests.get(tank_id)
        if manifest is None:
            return False
        slot = self._find_slot(manifest, rider_id)
        return slot is not None and slot.status == RiderStatus.RIDING

    def get_rider_tank(self, rider_id: str) -> str | None:
        """Get the tank ID a rider is associated with, if any."""
        return self._rider_to_tank.get(rider_id)

    def get_tank_riders(self, tank_id: str) -> list[str]:
        """Get list of rider IDs currently on a tank."""
        manifest = self._manifests.get(tank_id)
        if manifest is None:
            return []
        return [
            s.rider_id
            for s in manifest.riders
            if s.status in (RiderStatus.MOUNTING, RiderStatus.RIDING)
        ]

    # -- internal helpers --

    @staticmethod
    def _enemies_nearby(unit: Unit, all_units: list[Unit], radius: int) -> bool:
        """Check if any enemy unit is within radius of the given unit."""
        pos = unit.position.tile_coord
        for u in all_units:
            if (
                u.is_alive
                and u.faction != unit.faction
                and pos.chebyshev_distance(u.position.tile_coord) <= radius
            ):
                return True
        return False

    @staticmethod
    def _find_unit(unit_id: str, all_units: list[Unit]) -> Unit | None:
        for u in all_units:
            if u.id == unit_id:
                return u
        return None

    @staticmethod
    def _find_slot(manifest: TankRiderManifest, rider_id: str) -> RiderSlot | None:
        for s in manifest.riders:
            if s.rider_id == rider_id:
                return s
        return None

    def _remove_rider(self, manifest: TankRiderManifest, slot: RiderSlot) -> None:
        """Remove a rider slot and clean up the mapping."""
        self._rider_to_tank.pop(slot.rider_id, None)
        if slot in manifest.riders:
            manifest.riders.remove(slot)

    def _complete_dismount(self, manifest: TankRiderManifest, slot: RiderSlot) -> None:
        """Complete the dismount process for a rider."""
        slot.status = RiderStatus.DISMOUNTED
        self._rider_to_tank.pop(slot.rider_id, None)
        if slot in manifest.riders:
            manifest.riders.remove(slot)
        logger.debug(f"Unit {slot.rider_id} dismounted from tank {slot.tank_id}")


# ---------------------------------------------------------------------------
# TankRiderAI
# ---------------------------------------------------------------------------


class TankRiderAI(TacticalAIBase):
    """Evaluate when infantry should ride tanks and issue MOUNT_TANK orders.

    CC2 behaviour: Infantry hitch rides on friendly tanks for rapid
    transport to the front line. This is most useful when:
      - Infantry needs to reach a distant VL quickly
      - Tanks are available and not in combat
      - The route is relatively safe

    Evaluation heuristic:
      - Higher score when distant VLs need capturing
      - Higher score when tanks are available and idle
      - Lower score when enemies are nearby
      - Zero when no tanks or no infantry available
    """

    def __init__(self, rider_system: TankRiderSystem | None = None) -> None:
        """Initialize the tank rider AI evaluator with an optional shared rider system."""
        self._system = rider_system or TankRiderSystem()
        self._logger = logging.getLogger("pycc2.ai.tank_rider")

    @property
    def system(self) -> TankRiderSystem:
        """Return the backing tank rider system instance."""
        return self._system

    def evaluate(self, context: TacticalContext) -> float:
        """Return tank-riding priority based on transport need and enemy pressure."""
        tanks = self._find_tanks(context)
        infantry = self._find_available_infantry(context)

        if not tanks or not infantry:
            return 0.0

        # Need for rapid transport: distant VLs increase score
        transport_need = self._transport_need(context)

        # Tank availability
        tank_ratio = min(len(tanks) / 2.0, 1.0)

        # Safety: lower score if enemies are close
        enemy_pressure = self._enemy_pressure(context)

        score = 0.4 * transport_need + 0.3 * tank_ratio - 0.3 * enemy_pressure
        return max(0.0, min(score, 1.0))

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Generate MOUNT_TANK intents pairing available infantry with tanks."""
        tanks = self._find_tanks(context)
        infantry = self._find_available_infantry(context)

        if not tanks or not infantry:
            return []

        intents: list[TacticIntent] = []
        assigned_infantry: set[str] = set()

        for tank in tanks:
            # Check tank capacity
            manifest = self._system._manifests.get(tank.id)
            if manifest is not None and not manifest.has_capacity:
                continue

            # Find nearby infantry that could mount
            nearby_inf = [
                i
                for i in infantry
                if i.id not in assigned_infantry
                and i.position.tile_coord.chebyshev_distance(tank.position.tile_coord)
                <= MOUNT_RANGE
            ]

            for inf in nearby_inf[:MAX_RIDERS_PER_TANK]:
                assigned_infantry.add(inf.id)
                intents.append(
                    TacticIntent(
                        unit_id=inf.id,
                        tactic_type=TacticType.MOUNT_TANK,
                        priority=5,
                        target_unit_id=tank.id,
                        target_position=tank.position.tile_coord,
                    )
                )

        # Also issue MOVE_TO intents for infantry that need to reach a tank
        for inf in infantry:
            if inf.id in assigned_infantry:
                continue

            # Find nearest tank with capacity
            best_tank = None
            best_dist = float("inf")
            for tank in tanks:
                manifest = self._system._manifests.get(tank.id)
                if manifest is not None and not manifest.has_capacity:
                    continue
                dist = inf.position.tile_coord.chebyshev_distance(tank.position.tile_coord)
                if dist < best_dist:
                    best_dist = dist
                    best_tank = tank

            if best_tank is not None and best_dist > MOUNT_RANGE:
                assigned_infantry.add(inf.id)
                intents.append(
                    TacticIntent(
                        unit_id=inf.id,
                        tactic_type=TacticType.MOVE_TO,
                        priority=4,
                        target_unit_id=best_tank.id,
                        target_position=best_tank.position.tile_coord,
                    )
                )

        return intents

    # -- helpers --

    @staticmethod
    def _find_tanks(context: TacticalContext) -> list[Unit]:
        return [
            u
            for u in context.friendly_units
            if u.is_alive and u.can_act and u.unit_type == UnitType.TANK
        ]

    @staticmethod
    def _find_available_infantry(context: TacticalContext) -> list[Unit]:
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.unit_type in _INFANTRY_TYPES
            and u.morale.is_combat_effective
        ]

    @staticmethod
    def _transport_need(context: TacticalContext) -> float:
        """Score based on distance to VLs — farther VLs mean more need."""
        if not context.vl_positions:
            return 0.3  # Default moderate need

        friendlies = [u for u in context.friendly_units if u.is_alive]
        if not friendlies:
            return 0.0

        # Average distance from infantry to nearest uncontrolled VL
        faction_name = context.friendly_faction.name if context.friendly_faction else None
        uncontrolled = [v for v in context.vl_positions if v[1] is None or v[1] != faction_name]
        if not uncontrolled:
            return 0.0

        infantry = [u for u in friendlies if u.unit_type in _INFANTRY_TYPES]
        if not infantry:
            return 0.0

        avg_dist = 0.0
        for inf in infantry:
            min_dist = min(inf.position.tile_coord.chebyshev_distance(v[0]) for v in uncontrolled)
            avg_dist += min_dist
        avg_dist /= len(infantry)

        # Normalize: 0 tiles = 0.0, 30+ tiles = 1.0
        return min(avg_dist / 30.0, 1.0)

    @staticmethod
    def _enemy_pressure(context: TacticalContext) -> float:
        """Measure how close enemy forces are."""
        enemies = [e for e in context.enemy_units if e.is_alive]
        if not enemies:
            return 0.0
        friendlies = [u for u in context.friendly_units if u.is_alive]
        if not friendlies:
            return 1.0

        min_dist = float("inf")
        for f in friendlies[:5]:
            for e in enemies[:5]:
                d = f.position.tile_coord.chebyshev_distance(e.position.tile_coord)
                min_dist = min(min_dist, d)

        if min_dist <= 5:
            return 1.0
        elif min_dist <= 10:
            return 0.5
        elif min_dist <= 20:
            return 0.2
        return 0.0
