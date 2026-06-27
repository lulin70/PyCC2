"""Weapon Jam System — CC2-Authentic Weapon Reliability

Implements the P0-priority AI behavior for weapon jamming, a critical
element of CC2 fidelity.  The Sten gun was notoriously unreliable —
this system models per-weapon jam probability and clearing mechanics.

Jam probability per shot:
  - Rifle: 0.1% (very reliable)
  - SMG (Sten): 1.5% (notoriously unreliable)
  - LMG/MG: 0.3%
  - Pistol: 0.5%
  - AT weapon (PIAT/Bazooka): 0.8%
  - Captured enemy weapon: +1% penalty (unfamiliar maintenance)

When jam occurs:
  - Weapon state changes to JAMMED
  - Unit must spend ticks clearing the jam:
    - Rifle: 3 ticks
    - SMG: 5 ticks
    - MG: 8 ticks (more complex mechanism)
    - AT weapon: 6 ticks
    - Captured weapon: +50% clear time
  - During clearing, unit cannot fire or move fast

Jam clear is automatic — the unit clears the jam over time.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pycc2.domain.components.weapon_component import WeaponState

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JamConfig — per-weapon-type jam parameters
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class JamConfig:
    """Jam parameters for a specific weapon type."""

    weapon_type: str
    jam_probability: float  # 0.0-1.0 per shot
    jam_clear_ticks: int


# ---------------------------------------------------------------------------
# Default jam configurations for all weapon types
# ---------------------------------------------------------------------------

WEAPON_JAM_CONFIGS: dict[str, JamConfig] = {
    "rifle": JamConfig(weapon_type="rifle", jam_probability=0.001, jam_clear_ticks=3),
    "lee_enfield": JamConfig(weapon_type="lee_enfield", jam_probability=0.001, jam_clear_ticks=3),
    "kar98k": JamConfig(weapon_type="kar98k", jam_probability=0.001, jam_clear_ticks=3),
    "m1_garand": JamConfig(weapon_type="m1_garand", jam_probability=0.001, jam_clear_ticks=3),
    "m1_carbine": JamConfig(weapon_type="m1_carbine", jam_probability=0.001, jam_clear_ticks=3),
    "sniper_rifle": JamConfig(
        weapon_type="sniper_rifle", jam_probability=0.0008, jam_clear_ticks=3
    ),
    # SMGs — Sten is notoriously unreliable
    "sten": JamConfig(weapon_type="sten", jam_probability=0.015, jam_clear_ticks=5),
    "thompson": JamConfig(weapon_type="thompson", jam_probability=0.005, jam_clear_ticks=4),
    "mp40": JamConfig(weapon_type="mp40", jam_probability=0.006, jam_clear_ticks=4),
    "m3_grease_gun": JamConfig(
        weapon_type="m3_grease_gun", jam_probability=0.008, jam_clear_ticks=5
    ),
    # LMG/MG
    "mg42": JamConfig(weapon_type="mg42", jam_probability=0.003, jam_clear_ticks=8),
    "mg34": JamConfig(weapon_type="mg34", jam_probability=0.003, jam_clear_ticks=8),
    "m1919a4": JamConfig(weapon_type="m1919a4", jam_probability=0.003, jam_clear_ticks=8),
    "m1919": JamConfig(weapon_type="m1919", jam_probability=0.003, jam_clear_ticks=8),
    "bren": JamConfig(weapon_type="bren", jam_probability=0.003, jam_clear_ticks=7),
    "bar": JamConfig(weapon_type="bar", jam_probability=0.003, jam_clear_ticks=7),
    # Pistols
    "pistol": JamConfig(weapon_type="pistol", jam_probability=0.005, jam_clear_ticks=2),
    "webley": JamConfig(weapon_type="webley", jam_probability=0.005, jam_clear_ticks=2),
    "luger": JamConfig(weapon_type="luger", jam_probability=0.005, jam_clear_ticks=2),
    "walther": JamConfig(weapon_type="walther", jam_probability=0.005, jam_clear_ticks=2),
    # AT weapons
    "piat": JamConfig(weapon_type="piat", jam_probability=0.008, jam_clear_ticks=6),
    "bazooka": JamConfig(weapon_type="bazooka", jam_probability=0.008, jam_clear_ticks=6),
    "panzerschreck": JamConfig(
        weapon_type="panzerschreck", jam_probability=0.008, jam_clear_ticks=6
    ),
    "panzerfaust": JamConfig(weapon_type="panzerfaust", jam_probability=0.008, jam_clear_ticks=6),
    "at_gun": JamConfig(weapon_type="at_gun", jam_probability=0.008, jam_clear_ticks=6),
    "pak40": JamConfig(weapon_type="pak40", jam_probability=0.008, jam_clear_ticks=6),
    # Mortars
    "mortar": JamConfig(weapon_type="mortar", jam_probability=0.004, jam_clear_ticks=5),
    "60mm_mortar": JamConfig(weapon_type="60mm_mortar", jam_probability=0.004, jam_clear_ticks=5),
    "81mm_mortar": JamConfig(weapon_type="81mm_mortar", jam_probability=0.004, jam_clear_ticks=5),
    # Tank cannons
    "tank_cannon": JamConfig(weapon_type="tank_cannon", jam_probability=0.002, jam_clear_ticks=8),
    "kwk40_75mm": JamConfig(weapon_type="kwk40_75mm", jam_probability=0.002, jam_clear_ticks=8),
    "m3_75mm_m4": JamConfig(weapon_type="m3_75mm_m4", jam_probability=0.002, jam_clear_ticks=8),
    "17pdr": JamConfig(weapon_type="17pdr", jam_probability=0.002, jam_clear_ticks=8),
    # Flamethrowers
    "flamethrower_m2": JamConfig(
        weapon_type="flamethrower_m2", jam_probability=0.010, jam_clear_ticks=6
    ),
    "flammenwerfer": JamConfig(
        weapon_type="flammenwerfer", jam_probability=0.010, jam_clear_ticks=6
    ),
    # Coaxial MG
    "coax_mg34": JamConfig(weapon_type="coax_mg34", jam_probability=0.003, jam_clear_ticks=8),
}

CAPTURED_WEAPON_JAM_PENALTY: float = 0.01
CAPTURED_WEAPON_CLEAR_MULTIPLIER: float = 1.5


# ---------------------------------------------------------------------------
# WeaponJamSystem
# ---------------------------------------------------------------------------


class WeaponJamSystem:
    """Evaluate and process weapon jams each tick.

    Usage::

        jam_system = WeaponJamSystem()
        # On each shot:
        jam_system.check_jam_on_fire(unit)
        # Each tick:
        jam_system.tick(unit)
    """

    def __init__(
        self,
        jam_configs: dict[str, JamConfig] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._configs = jam_configs or WEAPON_JAM_CONFIGS
        self._rng = rng or random.Random()
        self._jam_clear_remaining: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_jam_on_fire(self, unit: Unit) -> bool:
        """Check if a jam occurs when *unit* fires its weapon.

        Call this immediately after a unit fires.  Returns True if the
        weapon jammed.
        """
        weapon_id = unit.weapon.primary_weapon_id
        config = self._get_config(weapon_id)

        if config is None:
            return False

        # Base jam probability
        jam_prob = config.jam_probability

        # Captured weapon penalty
        if self._is_captured_weapon(unit, weapon_id):
            jam_prob += CAPTURED_WEAPON_JAM_PENALTY

        if self._rng.random() < jam_prob:
            self._apply_jam(unit, config)
            return True

        return False

    def tick(self, unit: Unit) -> None:
        """Process jam-clearing progress for *unit* each tick.

        If the unit's weapon is JAMMED, decrement the clear timer.
        When the timer reaches zero, the jam is cleared automatically.
        """
        if unit.weapon.state != WeaponState.JAMMED:
            return

        remaining = self._jam_clear_remaining.get(unit.id, 0)
        if remaining <= 0:
            # Jam cleared
            unit.weapon.clear_jam()
            self._jam_clear_remaining.pop(unit.id, None)
            logger.debug(f"Unit {unit.id} cleared weapon jam")
            return

        self._jam_clear_remaining[unit.id] = remaining - 1

    def get_jam_clear_remaining(self, unit_id: str) -> int:
        """Return the number of ticks remaining to clear the jam."""
        return self._jam_clear_remaining.get(unit_id, 0)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_jam(self, unit: Unit, config: JamConfig) -> None:
        """Apply a jam to the unit's weapon."""
        clear_ticks = config.jam_clear_ticks

        # Captured weapon: +50% clear time
        if self._is_captured_weapon(unit, unit.weapon.primary_weapon_id):
            clear_ticks = int(clear_ticks * CAPTURED_WEAPON_CLEAR_MULTIPLIER)

        unit.weapon.state = WeaponState.JAMMED
        self._jam_clear_remaining[unit.id] = clear_ticks

        logger.info(
            f"Unit {unit.id} weapon {unit.weapon.primary_weapon_id} jammed "
            f"(clear in {clear_ticks} ticks)"
        )

    def _get_config(self, weapon_id: str) -> JamConfig | None:
        """Look up jam config for a weapon ID."""
        return self._configs.get(weapon_id)

    @staticmethod
    def _is_captured_weapon(unit: Unit, weapon_id: str) -> bool:
        """Determine if the weapon is a captured enemy weapon.

        A weapon is considered captured if its origin faction differs
        from the unit's faction.  This is determined by weapon ID prefix.
        """
        faction_prefixes: dict[str, set[str]] = {
            "ALLIES": {"us_", "uk_", "pl_"},
            "AXIS": {"de_"},
        }

        unit_faction_name = unit.faction.name
        unit_prefixes = faction_prefixes.get(unit_faction_name, set())

        if not unit_prefixes:
            return False

        # If the weapon ID starts with a prefix from a different faction,
        # it's a captured weapon
        for faction_name, prefixes in faction_prefixes.items():
            if faction_name == unit_faction_name:
                continue
            for prefix in prefixes:
                if weapon_id.startswith(prefix):
                    return True

        return False
