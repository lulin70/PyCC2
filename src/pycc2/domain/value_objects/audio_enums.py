"""Domain-level audio enums.

SoundType is a pure value object with no presentation dependency.
Services reference this instead of importing from presentation.audio.
"""

from __future__ import annotations

from enum import Enum, auto


class SoundType(Enum):
    """Sound effect identifiers used across domain and services layers."""

    # UI sounds
    UI_CLICK = auto()
    UI_HOVER = auto()
    UI_COMMAND = auto()
    UI_SELECT = auto()
    UI_CANCEL = auto()
    UI_ERROR = auto()
    UI_SUCCESS = auto()

    # Combat sounds
    RIFLE_SHOT = auto()
    MG_BURST = auto()
    PISTOL_SHOT = auto()
    EXPLOSION = auto()
    HIT_CONFIRM = auto()
    HIT_CRITICAL = auto()
    RICOCHET = auto()

    # Unit sounds
    UNIT_MOVE = auto()
    UNIT_DEATH = auto()
    UNIT_PANIC = auto()
    UNIT_SUPPRESSED = auto()

    # Ambient / environment
    AMBIENT_BIRD = auto()
    AMBIENT_WIND = auto()
    FOOTSTEP_GRASS = auto()
    FOOTSTEP_ROAD = auto()
    FOOTSTEP_WOOD = auto()


class InteractionMode(Enum):
    """User interaction mode for map input handling."""

    SELECT = auto()
    MOVE = auto()
    ATTACK = auto()
    PAN_ONLY = auto()
