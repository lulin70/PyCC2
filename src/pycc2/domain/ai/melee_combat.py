"""
Melee Combat — CC2-Authentic Close-Quarters Desperation Behavior

When ammunition is depleted or units are ordered to charge, infantry
engage in desperate close-quarters combat. This mirrors the brutal
reality of WWII combat where bayonet charges and hand-to-hand fighting
were rare but devastating last resorts.

Components:
  1. MeleeCombatSystem  — Manages melee attack resolution
  2. MeleeCombatAI      — Evaluates when to initiate melee and issues orders

Melee triggers:
  - Unit is within 1 tile of enemy AND
  - (ammo_ratio < 0.05 OR ordered to charge)

Melee attack properties:
  - Base damage: 15 (bayonet), 10 (butt stroke), 8 (knife/fists)
  - Hit chance: 70% base, modified by:
    - +20% if charging (moving into melee)
    - -20% if exhausted
    - +15% if veteran/elite
    - -15% if wounded
  - Both attacker and defender take damage (melee is risky)
  - Defender gets counter-attack at 50% damage

MeleeCombatAI priority:
  - Very low priority (last resort)
  - Only when no other option
  - Higher for units with bayonets (rifles) vs SMG (no bayonet)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.components.veterancy_component import VeteranRank
from pycc2.domain.entities.unit import UnitType

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_INFANTRY_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.COMMANDER,
    UnitType.SNIPER_TEAM,
    UnitType.MEDIC_TEAM,
    UnitType.MACHINE_GUN_SQUAD,
}

# Units with rifles (bayonet-capable)
_BAYONET_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.COMMANDER,
    UnitType.SNIPER_TEAM,
}

# Melee weapon damage values
BAYONET_DAMAGE: int = 15
BUTT_STROKE_DAMAGE: int = 10
FISTS_DAMAGE: int = 8

BASE_HIT_CHANCE: float = 0.70
CHARGE_BONUS: float = 0.20       # +20% if charging
EXHAUSTED_PENALTY: float = 0.20  # -20% if exhausted
VETERAN_BONUS: float = 0.15      # +15% if veteran/elite
WOUNDED_PENALTY: float = 0.15    # -15% if wounded
COUNTER_ATTACK_RATIO: float = 0.5  # Defender counter-attacks at 50% damage

AMMO_THRESHOLD: float = 0.05     # Below 5% ammo = melee possible
MELEE_RANGE: int = 1             # Must be within 1 tile


# ---------------------------------------------------------------------------
# MeleeWeaponType
# ---------------------------------------------------------------------------

class MeleeWeaponType(Enum):
    """Types of melee weapons available to infantry."""
    BAYONET = auto()      # Rifle with bayonet — highest damage
    BUTT_STROKE = auto()  # Rifle butt / pistol whip — medium damage
    FISTS = auto()        # Bare hands / knife — lowest damage


# ---------------------------------------------------------------------------
# MeleeResult
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MeleeResult:
    """Result of a melee attack."""
    attacker_id: str
    defender_id: str
    attacker_weapon: MeleeWeaponType
    hit: bool
    damage: int
    counter_hit: bool
    counter_damage: int
    attacker_killed: bool = False
    defender_killed: bool = False


# ---------------------------------------------------------------------------
# MeleeCombatSystem
# ---------------------------------------------------------------------------

class MeleeCombatSystem:
    """Manages melee combat resolution between units.

    Responsibilities:
      - Determine melee weapon type for each unit
      - Calculate hit chance with all modifiers
      - Resolve melee attacks and counter-attacks
      - Apply damage to both attacker and defender
    """

    @staticmethod
    def get_melee_weapon(unit: Unit) -> MeleeWeaponType:
        """Determine the melee weapon type for a unit.

        Units with rifles get bayonets, SMG teams get butt strokes,
        everyone else uses fists/knives.
        """
        if unit.unit_type in _BAYONET_TYPES:
            return MeleeWeaponType.BAYONET
        elif unit.unit_type == UnitType.MACHINE_GUN_SQUAD:
            return MeleeWeaponType.BUTT_STROKE
        return MeleeWeaponType.FISTS

    @staticmethod
    def get_weapon_damage(weapon: MeleeWeaponType) -> int:
        """Get base damage for a melee weapon type."""
        damage_map = {
            MeleeWeaponType.BAYONET: BAYONET_DAMAGE,
            MeleeWeaponType.BUTT_STROKE: BUTT_STROKE_DAMAGE,
            MeleeWeaponType.FISTS: FISTS_DAMAGE,
        }
        return damage_map[weapon]

    @staticmethod
    def calculate_hit_chance(
        attacker: Unit,
        is_charging: bool = False,
    ) -> float:
        """Calculate melee hit chance with all modifiers."""
        chance = BASE_HIT_CHANCE

        # Charging bonus
        if is_charging:
            chance += CHARGE_BONUS

        # Fatigue penalty
        fatigue = getattr(attacker, 'fatigue', None)
        if fatigue is not None:
            from pycc2.domain.components.fatigue_component import FatigueLevel
            if fatigue.level in (FatigueLevel.EXHAUSTED, FatigueLevel.SPENT):
                chance -= EXHAUSTED_PENALTY

        # Veterancy bonus
        veterancy = getattr(attacker, 'veterancy', None)
        if veterancy is not None and veterancy.rank in (VeteranRank.VETERAN, VeteranRank.ELITE):
            chance += VETERAN_BONUS

        # Wounded penalty
        if attacker.health.hp_ratio < 0.7:
            chance -= WOUNDED_PENALTY

        return max(0.1, min(0.95, chance))

    @staticmethod
    def resolve_melee(
        attacker: Unit,
        defender: Unit,
        is_charging: bool = False,
    ) -> MeleeResult:
        """Resolve a melee attack between two units.

        Both attacker and defender can take damage.
        Defender gets a counter-attack at 50% damage.
        """
        import random

        weapon = MeleeCombatSystem.get_melee_weapon(attacker)
        base_damage = MeleeCombatSystem.get_weapon_damage(weapon)
        hit_chance = MeleeCombatSystem.calculate_hit_chance(attacker, is_charging)

        # Roll for attacker hit
        hit = random.random() < hit_chance
        damage = 0
        defender_killed = False

        if hit:
            damage = base_damage
            defender.take_damage(damage)
            defender_killed = not defender.is_alive

        # Counter-attack: defender strikes back at reduced damage
        counter_weapon = MeleeCombatSystem.get_melee_weapon(defender)
        counter_base_damage = MeleeCombatSystem.get_weapon_damage(counter_weapon)
        counter_damage_value = int(counter_base_damage * COUNTER_ATTACK_RATIO)

        # Counter-attack hit chance (lower than attacker)
        counter_hit_chance = BASE_HIT_CHANCE * 0.6
        # Wounded defender has reduced counter-attack
        if defender.health.hp_ratio < 0.7:
            counter_hit_chance -= WOUNDED_PENALTY

        counter_hit = not defender_killed and random.random() < counter_hit_chance
        counter_damage = 0
        attacker_killed = False

        if counter_hit:
            counter_damage = counter_damage_value
            attacker.take_damage(counter_damage)
            attacker_killed = not attacker.is_alive

        result = MeleeResult(
            attacker_id=attacker.id,
            defender_id=defender.id,
            attacker_weapon=weapon,
            hit=hit,
            damage=damage,
            counter_hit=counter_hit,
            counter_damage=counter_damage,
            attacker_killed=attacker_killed,
            defender_killed=defender_killed,
        )

        logger.debug(
            f"Melee: {attacker.id} ({weapon.name}) vs {defender.id}: "
            f"hit={hit}, dmg={damage}, counter={counter_hit}, "
            f"counter_dmg={counter_damage}"
        )

        return result

    @staticmethod
    def can_melee(unit: Unit, enemy: Unit) -> bool:
        """Check if a unit can initiate melee against an enemy."""
        if not unit.is_alive or not unit.can_act:
            return False
        if not enemy.is_alive:
            return False
        if unit.unit_type not in _INFANTRY_TYPES:
            return False

        # Must be within melee range
        dist = unit.position.tile_coord.chebyshev_distance(
            enemy.position.tile_coord
        )
        if dist > MELEE_RANGE:
            return False

        # Must be low on ammo or ordered to charge
        # (Ordered-to-charge would be set via blackboard or direct order)
        return unit.weapon.ammo_ratio < AMMO_THRESHOLD


# ---------------------------------------------------------------------------
# MeleeCombatAI
# ---------------------------------------------------------------------------

class MeleeCombatAI(TacticalAIBase):
    """Evaluate when to initiate melee combat and issue MELEE_ATTACK orders.

    CC2 behaviour: Melee is a last-resort behavior. Units only engage
    in hand-to-hand combat when they have no ammunition or are ordered
    to charge. It is extremely risky — both sides take damage.

    Evaluation heuristic:
      - Very low base score (last resort)
      - Higher when ammo is critically low
      - Higher for units with bayonets vs SMG
      - Zero when units have ammo or are not adjacent to enemies
    """

    def evaluate(self, context: TacticalContext) -> float:
        melee_candidates = self._melee_candidates(context)
        if not melee_candidates:
            return 0.0

        # Very low priority — last resort behavior
        score = 0.15

        # Increase if many units are out of ammo
        out_of_ammo = sum(
            1 for u in context.friendly_units
            if u.is_alive and u.weapon.ammo_ratio < AMMO_THRESHOLD
        )
        if out_of_ammo > 0:
            ammo_urgency = min(out_of_ammo / 3.0, 1.0)
            score += 0.3 * ammo_urgency

        # Increase if bayonet-capable units are adjacent to enemies
        bayonet_adjacent = self._bayonet_units_adjacent(context)
        if bayonet_adjacent:
            score += 0.2

        return min(score, 0.5)  # Cap at 0.5 — never high priority

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        melee_candidates = self._melee_candidates(context)
        if not melee_candidates:
            return []

        intents: list[TacticIntent] = []

        for unit, target in melee_candidates:
            # Higher priority for bayonet units
            priority = 4 if unit.unit_type in _BAYONET_TYPES else 2

            intents.append(
                TacticIntent(
                    unit_id=unit.id,
                    tactic_type=TacticType.MELEE_ATTACK,
                    priority=priority,
                    target_position=target.position.tile_coord,
                    target_unit_id=target.id,
                )
            )

        return intents

    # -- helpers --

    @staticmethod
    def _melee_candidates(
        context: TacticalContext,
    ) -> list[tuple[Unit, Unit]]:
        """Find unit-enemy pairs eligible for melee."""
        result: list[tuple[Unit, Unit]] = []

        for u in context.friendly_units:
            if not u.is_alive or not u.can_act:
                continue
            if u.unit_type not in _INFANTRY_TYPES:
                continue

            # Check ammo
            ammo_ratio = u.weapon.ammo_ratio
            if ammo_ratio >= AMMO_THRESHOLD:
                continue

            # Find adjacent enemy
            for e in context.enemy_units:
                if not e.is_alive:
                    continue
                dist = u.position.tile_coord.chebyshev_distance(
                    e.position.tile_coord
                )
                if dist <= MELEE_RANGE:
                    result.append((u, e))
                    break  # One target per unit

        return result

    @staticmethod
    def _bayonet_units_adjacent(context: TacticalContext) -> bool:
        """Check if any bayonet-capable unit is adjacent to an enemy."""
        for u in context.friendly_units:
            if not u.is_alive or not u.can_act:
                continue
            if u.unit_type not in _BAYONET_TYPES:
                continue
            for e in context.enemy_units:
                if not e.is_alive:
                    continue
                dist = u.position.tile_coord.chebyshev_distance(
                    e.position.tile_coord
                )
                if dist <= MELEE_RANGE:
                    return True
        return False
