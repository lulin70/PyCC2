"""Environmental ambient audio system (C12)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class EnvironmentSoundType(Enum):
    """Types of environmental sounds."""
    BIRDS = auto()
    WIND = auto()
    DISTANT_ARTILLERY = auto()
    INSECTS = auto()
    RAIN = auto()
    FOOTSTEPS = auto()


@dataclass
class EnvironmentalAudioSystem:
    """
    Environmental ambient audio system.

    Background sounds: birds/wind/artillery/insects
    Context-sensitive: rain during weather, etc.
    """

    _active_sounds: dict[EnvironmentSoundType, bool] = field(init=False)
    _volume: float = 0.3

    def __post_init__(self):
        self._active_sounds = {
            EnvironmentSoundType.BIRDS: True,
            EnvironmentSoundType.WIND: False,
            EnvironmentSoundType.DISTANT_ARTILLERY: False,
            EnvironmentSoundType.INSECTS: True,
            EnvironmentSoundType.RAIN: False,
            EnvironmentSoundType.FOOTSTEPS: False,
        }

    def set_weather_rain(self, raining: bool) -> None:
        """Enable/disable rain sounds."""
        self._active_sounds[EnvironmentSoundType.RAIN] = raining
        if raining:
            self._active_sounds[EnvironmentSoundType.BIRDS] = False
            self._active_sounds[EnvironmentSoundType.INSECTS] = False

    def set_combat_intensity(self, intensity: float) -> None:
        """Adjust ambient sounds based on combat."""
        self._active_sounds[EnvironmentSoundType.DISTANT_ARTILLERY] = \
            intensity > 0.3
        self._active_sounds[EnvironmentSoundType.BIRDS] = \
            intensity < 0.3

    def is_playing(self, sound_type: EnvironmentSoundType) -> bool:
        """Check if sound type is active."""
        return self._active_sounds.get(sound_type, False)
