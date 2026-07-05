"""Combat Sound Event enumeration - shared contract for audio modules.

Extracted from enhanced_sound_bridge.py (TD-072) to break circular dependency
between EnhancedSoundSystem (bridge) and ProceduralSoundSynthesizer (synth).
Both modules import CombatSoundEvent from here.
"""

from __future__ import annotations

from enum import Enum, auto


class CombatSoundEvent(Enum):
    """Sound events triggered by combat actions."""

    RIFLE_FIRE = auto()
    MG_FIRE = auto()
    PISTOL_FIRE = auto()
    CANNON_FIRE = auto()
    MORTAR_FIRE = auto()
    EXPLOSION = auto()
    GRENADE_EXPLOSION = auto()
    HIT_RICOCHET = auto()
    HIT_CONFIRM = auto()
    HIT_CRITICAL = auto()
    UNIT_DEATH = auto()
    VEHICLE_DESTROYED = auto()
    WEAPON_RELOAD = auto()
    WEAPON_SWITCH = auto()
    SMOKE_DEPLOY = auto()
    NEAR_MISS = auto()

    TANK_CANNON_FIRE = auto()
    AT_ROCKET_FIRE = auto()
    MORTAR_LAUNCH = auto()
    GRENADE_THROW = auto()
    GRENADE_EXPLOSION_SHORT = auto()
    AIRSTRIKE_BOMB = auto()
    VEHICLE_ENGINE_START = auto()
    VEHICLE_ENGINE_IDLE = auto()
    VEHICLE_MOVE = auto()
    ARMOR_PENETRATE = auto()
    RICOCHET_BOUNCE = auto()
    NEAR_MISS_WHIZZ = auto()
    SMOKE_DEPLOY_HISS = auto()
    SUPPRESSION_FIRE = auto()
