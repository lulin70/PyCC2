"""
Ammo Pickup & Weapon Scavenging System — CC2-Authentic AI Behavior

Implements the P0-priority AI behavior for ammunition resupply through
battlefield scavenging.  In CC2, units that run low on ammo will seek
nearby fallen comrades or enemy corpses to resupply, with appropriate
penalties for using captured enemy weapons.

Components:
  1. FallenUnitCache  — Tracks dead units as scavenge sources
  2. AmmoPickupSystem — Handles the pickup mechanics and penalties
  3. WeaponScavengeAI — Tactical AI that evaluates & issues scavenge orders

Design principles (from CC2 fidelity analysis):
  - Friendly corpses: 5-tile range, 50% ammo transfer, same weapon preferred
  - Enemy corpses: 3-tile range, full weapon + ammo but with penalties
  - Pickup takes 2 ticks (not instant — unit is vulnerable while scavenging)
  - Unit must be PRONE or CROUCHING to pick up
  - Cannot pick up while suppressed (suppression > MODERATE)
  - Captured weapons: -20% accuracy, +50% reload time
  - Caches expire after 300 ticks (bodies removed from battlefield)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import Faction
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.systems.combat_mechanics_enhanced import Stance

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ammo source type
# ---------------------------------------------------------------------------


class AmmoSourceType(Enum):
    """Type of ammo source on the battlefield."""

    FALLEN_COMRADE = auto()  # Same faction — partial ammo, same weapon type
    ENEMY_CORPSE = auto()  # Enemy faction — weapon + ammo with penalties
    SUPPLY_CACHE = auto()  # Pre-placed supply point (future extension)


# ---------------------------------------------------------------------------
# 1. FallenUnitCache
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class FallenUnitEntry:
    """A single dead unit registered as a scavenge source."""

    unit_id: str
    position: TileCoord
    faction: Faction
    weapon_type: str
    ammo_remaining: int
    max_ammo: int
    death_tick: int
    source_type: AmmoSourceType
    ammo_claimed: int = 0  # Track how much ammo has been taken
    weapon_claimed: bool = False


@dataclass
class FallenUnitCache:
    """When a unit dies, register its position, faction, weapon_type,
    and ammo_remaining.  Friendly and enemy caches are tracked separately.
    Caches expire after 300 ticks (bodies removed from battlefield).

    Usage::

        cache = FallenUnitCache()
        cache.register(unit, current_tick=150)
        ...
        sources = cache.find_sources_near(
            position=unit.position.tile_coord,
            seeker_faction=Faction.ALLIES,
            current_tick=200,
        )
    """

    CACHE_EXPIRY_TICKS: int = 300
    FRIENDLY_RANGE: int = 5
    ENEMY_RANGE: int = 3

    _entries: list[FallenUnitEntry] = field(default_factory=list)

    def register(self, unit: Unit, current_tick: int) -> None:
        """Register a dead unit as a scavenge source.

        Determines source type based on the unit's faction relative to
        the caller — but we store the raw faction so any seeker can
        determine friend vs foe at query time.
        """
        entry = FallenUnitEntry(
            unit_id=unit.id,
            position=unit.position.tile_coord,
            faction=unit.faction,
            weapon_type=unit.weapon.primary_weapon_id,
            ammo_remaining=unit.weapon.ammo_remaining,
            max_ammo=unit.weapon.max_ammo,
            death_tick=current_tick,
            source_type=AmmoSourceType.FALLEN_COMRADE,  # Set at query time
        )
        self._entries.append(entry)
        logger.debug(
            f"Registered fallen unit {unit.id} at "
            f"({unit.position.tile_coord.x}, {unit.position.tile_coord.y}) "
            f"with {unit.weapon.ammo_remaining} ammo"
        )

    def find_sources_near(
        self,
        position: TileCoord,
        seeker_faction: Faction,
        current_tick: int,
    ) -> list[FallenUnitEntry]:
        """Find all valid ammo sources within range of *position*.

        Friendly corpses have a 5-tile range; enemy corpses have a 3-tile
        range.  Expired entries are pruned before searching.
        """
        self._prune_expired(current_tick)

        results: list[FallenUnitEntry] = []
        for entry in self._entries:
            # Determine if this is friendly or enemy relative to seeker
            is_friendly = entry.faction == seeker_faction
            max_range = self.FRIENDLY_RANGE if is_friendly else self.ENEMY_RANGE

            dist = position.chebyshev_distance(entry.position)
            if dist > max_range:
                continue

            # Check if there's anything left to scavenge
            remaining_ammo = entry.ammo_remaining - entry.ammo_claimed
            if remaining_ammo <= 0 and not entry.weapon_claimed:
                continue

            # Set the correct source type for the seeker
            entry_copy = FallenUnitEntry(
                unit_id=entry.unit_id,
                position=entry.position,
                faction=entry.faction,
                weapon_type=entry.weapon_type,
                ammo_remaining=entry.ammo_remaining,
                max_ammo=entry.max_ammo,
                death_tick=entry.death_tick,
                source_type=(
                    AmmoSourceType.FALLEN_COMRADE if is_friendly else AmmoSourceType.ENEMY_CORPSE
                ),
                ammo_claimed=entry.ammo_claimed,
                weapon_claimed=entry.weapon_claimed,
            )
            results.append(entry_copy)

        # Sort by distance (nearest first)
        results.sort(key=lambda e: position.chebyshev_distance(e.position))
        return results

    def claim_ammo(self, unit_id: str, amount: int) -> None:
        """Mark *amount* ammo as claimed from the fallen unit *unit_id*."""
        for entry in self._entries:
            if entry.unit_id == unit_id:
                entry.ammo_claimed += amount
                logger.debug(
                    f"Claimed {amount} ammo from {unit_id} "
                    f"(remaining: {entry.ammo_remaining - entry.ammo_claimed})"
                )
                return

    def claim_weapon(self, unit_id: str) -> None:
        """Mark the weapon of fallen unit *unit_id* as claimed."""
        for entry in self._entries:
            if entry.unit_id == unit_id:
                entry.weapon_claimed = True
                logger.debug(f"Weapon claimed from {unit_id}")
                return

    def _prune_expired(self, current_tick: int) -> None:
        """Remove entries older than CACHE_EXPIRY_TICKS."""
        before = len(self._entries)
        self._entries = [
            e for e in self._entries if current_tick - e.death_tick < self.CACHE_EXPIRY_TICKS
        ]
        pruned = before - len(self._entries)
        if pruned > 0:
            logger.debug(f"Pruned {pruned} expired fallen unit entries")

    @property
    def entry_count(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# 2. AmmoPickupSystem
# ---------------------------------------------------------------------------


class PickupResult(Enum):
    """Result of an ammo pickup attempt."""

    SUCCESS = auto()
    WRONG_STANCE = auto()  # Unit not PRONE or CROUCHING
    SUPPRESSED = auto()  # Unit suppression > MODERATE
    NO_SOURCE = auto()  # No valid ammo source nearby
    ALREADY_PICKING_UP = auto()  # Unit already in pickup state
    COMPLETED = auto()  # Pickup finished this tick


@dataclass(slots=True)
class PickupState:
    """Tracks an in-progress ammo pickup."""

    unit_id: str
    source_id: str
    source_type: AmmoSourceType
    ticks_remaining: int
    target_position: TileCoord


@dataclass
class AmmoPickupSystem:
    """Handles the mechanics of picking up ammo from fallen units.

    Rules:
      - Unit must be in PRONE or CROUCHING stance to pick up
      - Cannot pick up while suppressed (suppression > MODERATE)
      - Pickup takes 2 ticks (not instant)
      - From fallen comrade: get 50% of their remaining ammo,
        same weapon type preferred
      - From enemy corpse: get weapon + ammo but with penalties:
          - Accuracy penalty: -20% (unfamiliar weapon)
          - Slower reload: +50% reload time
          - Weapon marked as "captured" in unit's weapon component

    Usage::

        pickup_system = AmmoPickupSystem(fallen_cache=cache)
        ...
        result = pickup_system.start_pickup(unit, source_entry, current_tick)
        ...
        # Each tick:
        completed = pickup_system.tick(current_tick)
    """

    PICKUP_DURATION_TICKS: int = 2
    FRIENDLY_AMMO_TRANSFER_RATIO: float = 0.5
    CAPTURED_ACCURACY_PENALTY: float = 0.20  # -20% accuracy
    CAPTURED_RELOAD_PENALTY: float = 0.50  # +50% reload time

    fallen_cache: FallenUnitCache = field(default_factory=FallenUnitCache)
    _active_pickups: dict[str, PickupState] = field(default_factory=dict)

    def can_pickup(self, unit: Unit) -> bool:
        """Check if a unit is eligible to start picking up ammo.

        Requirements:
          1. Unit is alive and can act
          2. Unit is in PRONE or CROUCHING stance
          3. Unit is not suppressed beyond MODERATE
          4. Unit is not already picking up
        """
        if not unit.is_alive or not unit.can_act:
            return False

        # Check stance — must be PRONE or CROUCHING
        from pycc2.domain.systems.combat_mechanics_enhanced import Stance

        stance = self._get_unit_stance(unit)
        if stance not in (Stance.PRONE, Stance.CROUCHING):
            return False

        # Check suppression — cannot pick up while suppressed > MODERATE
        if self._is_suppressed_moderate(unit):
            return False

        # Not already picking up
        return unit.id not in self._active_pickups

    def start_pickup(
        self,
        unit: Unit,
        source: FallenUnitEntry,
        current_tick: int,
    ) -> PickupResult:
        """Start a pickup action for *unit* from *source*.

        Returns a PickupResult indicating whether the pickup started
        successfully or why it was rejected.
        """
        # Validate eligibility
        if unit.id in self._active_pickups:
            return PickupResult.ALREADY_PICKING_UP

        from pycc2.domain.systems.combat_mechanics_enhanced import Stance

        stance = self._get_unit_stance(unit)
        if stance not in (Stance.PRONE, Stance.CROUCHING):
            return PickupResult.WRONG_STANCE

        if self._is_suppressed_moderate(unit):
            return PickupResult.SUPPRESSED

        # Validate source is within range
        dist = unit.position.tile_coord.chebyshev_distance(source.position)
        is_friendly = source.faction == unit.faction
        max_range = (
            self.fallen_cache.FRIENDLY_RANGE if is_friendly else self.fallen_cache.ENEMY_RANGE
        )
        if dist > max_range:
            return PickupResult.NO_SOURCE

        # Start the pickup
        self._active_pickups[unit.id] = PickupState(
            unit_id=unit.id,
            source_id=source.unit_id,
            source_type=source.source_type,
            ticks_remaining=self.PICKUP_DURATION_TICKS,
            target_position=source.position,
        )
        logger.debug(
            f"Unit {unit.id} started picking up from {source.unit_id} "
            f"(type={source.source_type.name}, ticks={self.PICKUP_DURATION_TICKS})"
        )
        return PickupResult.SUCCESS

    def tick(self, current_tick: int) -> list[PickupState]:
        """Advance all active pickups by one tick.

        Returns a list of PickupState entries that completed this tick.
        The caller should apply the pickup effects for completed entries.
        """
        completed: list[PickupState] = []

        for unit_id, state in list(self._active_pickups.items()):
            state.ticks_remaining -= 1
            if state.ticks_remaining <= 0:
                completed.append(state)
                del self._active_pickups[unit_id]
                logger.debug(f"Pickup completed for unit {unit_id} from {state.source_id}")

        return completed

    def apply_pickup(
        self,
        unit: Unit,
        pickup: PickupState,
        source: FallenUnitEntry,
    ) -> None:
        """Apply the effects of a completed pickup to *unit*.

        For fallen comrades:
          - Transfer 50% of remaining ammo (same weapon type preferred)
        For enemy corpses:
          - Transfer weapon + ammo
          - Apply accuracy penalty (-20%) and reload penalty (+50%)
          - Mark weapon as "captured"
        """
        if pickup.source_type == AmmoSourceType.FALLEN_COMRADE:
            self._apply_friendly_pickup(unit, source)
        elif pickup.source_type == AmmoSourceType.ENEMY_CORPSE:
            self._apply_enemy_pickup(unit, source)

    def _apply_friendly_pickup(self, unit: Unit, source: FallenUnitEntry) -> None:
        """Transfer 50% of remaining ammo from a fallen comrade.

        Same weapon type is preferred — if the weapon types match,
        the full transfer ratio applies.  Otherwise, only 25% is
        transferred (incompatible ammo).
        """
        available = source.ammo_remaining - source.ammo_claimed
        if available <= 0:
            return

        # Same weapon type gets full transfer; different type gets half
        if source.weapon_type == unit.weapon.primary_weapon_id:
            transfer = max(1, int(available * self.FRIENDLY_AMMO_TRANSFER_RATIO))
        else:
            transfer = max(1, int(available * self.FRIENDLY_AMMO_TRANSFER_RATIO * 0.5))

        # Cap at unit's max ammo
        space = unit.weapon.max_ammo - unit.weapon.ammo_remaining
        transfer = min(transfer, space)

        if transfer > 0:
            unit.weapon.ammo_remaining += transfer
            self.fallen_cache.claim_ammo(source.unit_id, transfer)
            # Update weapon state if it was out of ammo
            if unit.weapon.state.value == "OUT_OF_AMMO" and unit.weapon.ammo_remaining > 0:
                unit.weapon.state = unit.weapon.state.__class__.READY
                unit.weapon._update_state()
            logger.debug(
                f"Unit {unit.id} picked up {transfer} ammo from fallen comrade {source.unit_id}"
            )

    def _apply_enemy_pickup(self, unit: Unit, source: FallenUnitEntry) -> None:
        """Transfer weapon + ammo from an enemy corpse with penalties.

        Penalties:
          - Accuracy: -20% (unfamiliar weapon)
          - Reload time: +50% (unfamiliar mechanism)
          - Weapon marked as "captured" in unit's weapon component
        """
        available = source.ammo_remaining - source.ammo_claimed
        if available <= 0:
            return

        # Transfer all remaining ammo (capped at unit's max)
        space = unit.weapon.max_ammo - unit.weapon.ammo_remaining
        transfer = min(available, space)

        if transfer > 0:
            unit.weapon.ammo_remaining += transfer
            self.fallen_cache.claim_ammo(source.unit_id, transfer)
            self.fallen_cache.claim_weapon(source.unit_id)
            # Update weapon state
            if unit.weapon.state.value == "OUT_OF_AMMO" and unit.weapon.ammo_remaining > 0:
                unit.weapon.state = unit.weapon.state.__class__.READY
                unit.weapon._update_state()
            logger.debug(
                f"Unit {unit.id} picked up {transfer} ammo from enemy corpse {source.unit_id}"
            )

        # Mark weapon as captured — store in combat_state or weapon metadata
        self._mark_weapon_captured(unit)

    def _mark_weapon_captured(self, unit: Unit) -> None:
        """Mark the unit's weapon as captured, applying penalties.

        Stores captured weapon info in the unit's combat_state if available,
        otherwise tracks it via a simple attribute.
        """
        if unit.combat_state is not None:
            # Store captured weapon penalties in combat state
            unit.combat_state.captured_weapon = True
            unit.combat_state.captured_accuracy_penalty = self.CAPTURED_ACCURACY_PENALTY
            unit.combat_state.captured_reload_penalty = self.CAPTURED_RELOAD_PENALTY
        else:
            # Fallback: set attribute directly on weapon component
            unit.weapon.captured = True
            unit.weapon.captured_accuracy_penalty = self.CAPTURED_ACCURACY_PENALTY
            unit.weapon.captured_reload_penalty = self.CAPTURED_RELOAD_PENALTY

        logger.debug(
            f"Unit {unit.id} weapon marked as captured "
            f"(accuracy -{self.CAPTURED_ACCURACY_PENALTY:.0%}, "
            f"reload +{self.CAPTURED_RELOAD_PENALTY:.0%})"
        )

    @staticmethod
    def _get_unit_stance(unit: Unit) -> Stance:
        """Get the unit's current stance from its combat_state."""
        from pycc2.domain.systems.combat_mechanics_enhanced import Stance

        if unit.combat_state is not None:
            return unit.combat_state.concealment.current_stance
        return Stance.STANDING

    @staticmethod
    def _is_suppressed_moderate(unit: Unit) -> bool:
        """Check if unit's suppression is above MODERATE level."""
        from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect

        effect = unit.suppression_level
        return effect in (
            SuppressionEffect.MODERATE,
            SuppressionEffect.HEAVY,
            SuppressionEffect.PINNED,
            SuppressionEffect.PANIC,
        )

    @property
    def active_pickup_count(self) -> int:
        return len(self._active_pickups)

    def get_pickup_state(self, unit_id: str) -> PickupState | None:
        return self._active_pickups.get(unit_id)


# ---------------------------------------------------------------------------
# 3. WeaponScavengeAI
# ---------------------------------------------------------------------------


class WeaponScavengeAI(TacticalAIBase):
    """Tactical AI that evaluates whether units should scavenge for ammo.

    Evaluation heuristic:
      - Score based on ammo_ratio of unit (lower = higher score)
      - Units with ammo_ratio < 0.1 get highest priority
      - Units with ammo_ratio < 0.2 are candidates
      - Zero score when no ammo sources are available

    Execution:
      - Find nearest ammo source for each eligible unit
      - Issue SCAVENGE_AMMO intent to move to source and pick up
      - After pickup, resume previous tactic
    """

    AMMO_LOW_THRESHOLD: float = 0.2  # Below 20% → seek ammo
    AMMO_CRITICAL_THRESHOLD: float = 0.1  # Below 10% → highest priority

    def __init__(self, fallen_cache: FallenUnitCache) -> None:
        self._fallen_cache = fallen_cache

    def evaluate(self, context: TacticalContext) -> float:
        """Return a priority score in [0.0, 1.0].

        Score is driven by how many friendly units are low on ammo
        and whether there are ammo sources available.
        """
        low_ammo_units = self._low_ammo_units(context)
        if not low_ammo_units:
            return 0.0

        # Check if any ammo sources exist
        has_sources = False
        for unit in low_ammo_units:
            sources = self._fallen_cache.find_sources_near(
                position=unit.position.tile_coord,
                seeker_faction=unit.faction,
                current_tick=context.current_tick,
            )
            if sources:
                has_sources = True
                break

        if not has_sources:
            return 0.0

        # Score based on how many units are low and how low they are
        critical_count = sum(
            1 for u in low_ammo_units if u.weapon.ammo_ratio < self.AMMO_CRITICAL_THRESHOLD
        )
        low_count = len(low_ammo_units)

        critical_weight = min(critical_count / 2.0, 1.0)
        low_weight = min(low_count / 4.0, 1.0)

        score = 0.6 * critical_weight + 0.4 * low_weight
        return min(score, 1.0)

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Return SCAVENGE_AMMO intents for units that need ammo.

        For each eligible unit, find the nearest ammo source and issue
        a SCAVENGE_AMMO intent targeting that source's position.
        """
        low_ammo_units = self._low_ammo_units(context)
        if not low_ammo_units:
            return []

        intents: list[TacticIntent] = []
        assigned_sources: set[str] = set()

        for unit in low_ammo_units:
            sources = self._fallen_cache.find_sources_near(
                position=unit.position.tile_coord,
                seeker_faction=unit.faction,
                current_tick=context.current_tick,
            )

            # Filter out already-assigned sources
            available_sources = [s for s in sources if s.unit_id not in assigned_sources]
            if not available_sources:
                continue

            # Pick nearest source
            source = available_sources[0]
            assigned_sources.add(source.unit_id)

            # Priority: critical ammo → 10, low ammo → 7
            priority = 10 if unit.weapon.ammo_ratio < self.AMMO_CRITICAL_THRESHOLD else 7

            intents.append(
                TacticIntent(
                    unit_id=unit.id,
                    tactic_type=TacticType.SCAVENGE_AMMO,
                    priority=priority,
                    target_position=source.position,
                    target_unit_id=source.unit_id,
                )
            )

        return intents

    @staticmethod
    def _low_ammo_units(context: TacticalContext) -> list[Unit]:
        """Return friendly units with ammo_ratio below the low threshold."""
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.weapon.ammo_ratio < WeaponScavengeAI.AMMO_LOW_THRESHOLD
            and u.morale.is_combat_effective
        ]
