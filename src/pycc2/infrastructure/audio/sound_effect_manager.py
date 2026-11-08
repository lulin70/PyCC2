"""Sound Effect Manager - Central hub for game UI and gameplay sound effects.

This manager handles:
- UI interaction sounds (clicks, hovers, confirmations)
- Building construction sounds
- Unit training sounds
- Resource collection sounds
- Combat impact sounds

All sounds are procedurally generated using pygame.mixer and numpy synthesis.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import ClassVar

import numpy as np
import pygame.mixer

SAMPLE_RATE: int = 44100


class SoundEffectType(Enum):
    """Types of sound effects in the game."""

    # UI Sounds
    UI_CLICK = auto()
    UI_HOVER = auto()
    UI_CONFIRM = auto()
    UI_CANCEL = auto()
    UI_ERROR = auto()

    # Building Sounds
    BUILDING_PLACE = auto()
    BUILDING_CONSTRUCT = auto()
    BUILDING_COMPLETE = auto()

    # Unit Sounds
    UNIT_TRAIN_START = auto()
    UNIT_TRAIN_COMPLETE = auto()
    UNIT_SELECT = auto()

    # Resource Sounds
    RESOURCE_COLLECT = auto()
    RESOURCE_DEPOSIT = auto()

    # Combat Sounds
    EXPLOSION_SMALL = auto()
    EXPLOSION_LARGE = auto()
    IMPACT_HIT = auto()


class SoundEffectManager:
    """Manages and plays procedurally generated sound effects."""

    SAMPLE_RATE: ClassVar[int] = SAMPLE_RATE

    def __init__(self) -> None:
        """Initialize sound effect manager."""
        pygame.mixer.init(frequency=self.SAMPLE_RATE, channels=2, buffer=512)
        self._sound_cache: dict[SoundEffectType, pygame.mixer.Sound] = {}
        self._volume = 0.7

    def play_effect(self, effect_type: SoundEffectType) -> None:
        """Play a sound effect.

        Args:
            effect_type: Type of sound effect to play
        """
        if effect_type not in self._sound_cache:
            self._sound_cache[effect_type] = self._generate_effect(effect_type)

        sound = self._sound_cache[effect_type]
        sound.set_volume(self._volume)
        sound.play()

    def set_volume(self, volume: float) -> None:
        """Set global volume for sound effects (0.0-1.0)."""
        self._volume = max(0.0, min(1.0, volume))

    # -------------------------------------------------------------------------
    # Sound Generation Methods
    # -------------------------------------------------------------------------

    def _generate_effect(self, effect_type: SoundEffectType) -> pygame.mixer.Sound:
        """Generate waveform for a sound effect type."""
        if effect_type == SoundEffectType.UI_CLICK:
            return self._make_ui_click()
        elif effect_type == SoundEffectType.UI_HOVER:
            return self._make_ui_hover()
        elif effect_type == SoundEffectType.UI_CONFIRM:
            return self._make_ui_confirm()
        elif effect_type == SoundEffectType.UI_CANCEL:
            return self._make_ui_cancel()
        elif effect_type == SoundEffectType.UI_ERROR:
            return self._make_ui_error()
        elif effect_type == SoundEffectType.BUILDING_PLACE:
            return self._make_building_place()
        elif effect_type == SoundEffectType.BUILDING_CONSTRUCT:
            return self._make_building_construct()
        elif effect_type == SoundEffectType.BUILDING_COMPLETE:
            return self._make_building_complete()
        elif effect_type == SoundEffectType.UNIT_TRAIN_START:
            return self._make_unit_train_start()
        elif effect_type == SoundEffectType.UNIT_TRAIN_COMPLETE:
            return self._make_unit_train_complete()
        elif effect_type == SoundEffectType.UNIT_SELECT:
            return self._make_unit_select()
        elif effect_type == SoundEffectType.RESOURCE_COLLECT:
            return self._make_resource_collect()
        elif effect_type == SoundEffectType.RESOURCE_DEPOSIT:
            return self._make_resource_deposit()
        elif effect_type == SoundEffectType.EXPLOSION_SMALL:
            return self._make_explosion_small()
        elif effect_type == SoundEffectType.EXPLOSION_LARGE:
            return self._make_explosion_large()
        elif effect_type == SoundEffectType.IMPACT_HIT:
            return self._make_impact_hit()
        else:
            return self._make_ui_click()  # Fallback

    # -------------------------------------------------------------------------
    # UI Sounds
    # -------------------------------------------------------------------------

    def _make_ui_click(self) -> pygame.mixer.Sound:
        """Short sharp click sound."""
        duration = 0.05
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        # High-frequency beep with fast decay
        freq = 1200
        wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * 50)
        return self._to_sound(wave)

    def _make_ui_hover(self) -> pygame.mixer.Sound:
        """Soft hover sound."""
        duration = 0.03
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        freq = 800
        wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * 80) * 0.3
        return self._to_sound(wave)

    def _make_ui_confirm(self) -> pygame.mixer.Sound:
        """Rising confirmation tone."""
        duration = 0.15
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        freq_start, freq_end = 600, 1200
        freq = np.linspace(freq_start, freq_end, n)
        phase = 2 * np.pi * np.cumsum(freq) / self.SAMPLE_RATE
        wave = np.sin(phase) * np.exp(-t * 8) * 0.5
        return self._to_sound(wave)

    def _make_ui_cancel(self) -> pygame.mixer.Sound:
        """Falling cancel tone."""
        duration = 0.12
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        freq_start, freq_end = 800, 300
        freq = np.linspace(freq_start, freq_end, n)
        phase = 2 * np.pi * np.cumsum(freq) / self.SAMPLE_RATE
        wave = np.sin(phase) * np.exp(-t * 12) * 0.4
        return self._to_sound(wave)

    def _make_ui_error(self) -> pygame.mixer.Sound:
        """Harsh error buzz."""
        duration = 0.2
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        # Dissonant dual tone
        wave = np.sin(2 * np.pi * 200 * t) + np.sin(2 * np.pi * 250 * t)
        wave *= np.exp(-t * 6) * 0.3
        return self._to_sound(wave)

    # -------------------------------------------------------------------------
    # Building Sounds
    # -------------------------------------------------------------------------

    def _make_building_place(self) -> pygame.mixer.Sound:
        """Metallic clang for placing building."""
        duration = 0.3
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        # Multiple metallic harmonics
        wave = np.sin(2 * np.pi * 400 * t) * 0.5
        wave += np.sin(2 * np.pi * 600 * t) * 0.3
        wave += np.sin(2 * np.pi * 800 * t) * 0.2
        wave *= np.exp(-t * 10)
        return self._to_sound(wave)

    def _make_building_construct(self) -> pygame.mixer.Sound:
        """Hammering/construction sound."""
        duration = 0.2
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        # Short percussive hit
        wave = np.sin(2 * np.pi * 300 * t) * np.exp(-t * 30)
        # Add noise for texture
        noise = np.random.uniform(-0.1, 0.1, n) * np.exp(-t * 25)
        wave += noise
        return self._to_sound(wave * 0.6)

    def _make_building_complete(self) -> pygame.mixer.Sound:
        """Triumphant building completion sound."""
        duration = 0.4
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        # Ascending chord
        wave = np.sin(2 * np.pi * 400 * t) * 0.4
        wave += np.sin(2 * np.pi * 500 * t) * 0.3
        wave += np.sin(2 * np.pi * 600 * t) * 0.3
        wave *= np.exp(-t * 4)
        return self._to_sound(wave)

    # -------------------------------------------------------------------------
    # Unit Sounds
    # -------------------------------------------------------------------------

    def _make_unit_train_start(self) -> pygame.mixer.Sound:
        """Unit training start sound."""
        duration = 0.25
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        freq_sweep = np.linspace(400, 600, n)
        phase = 2 * np.pi * np.cumsum(freq_sweep) / self.SAMPLE_RATE
        wave = np.sin(phase) * np.exp(-t * 6) * 0.5
        return self._to_sound(wave)

    def _make_unit_train_complete(self) -> pygame.mixer.Sound:
        """Unit training complete sound."""
        duration = 0.35
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        # Bright fanfare
        wave = np.sin(2 * np.pi * 600 * t) * 0.4
        wave += np.sin(2 * np.pi * 750 * t) * 0.3
        wave *= np.exp(-t * 5)
        return self._to_sound(wave)

    def _make_unit_select(self) -> pygame.mixer.Sound:
        """Short unit selection beep."""
        duration = 0.04
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        wave = np.sin(2 * np.pi * 900 * t) * np.exp(-t * 70) * 0.4
        return self._to_sound(wave)

    # -------------------------------------------------------------------------
    # Resource Sounds
    # -------------------------------------------------------------------------

    def _make_resource_collect(self) -> pygame.mixer.Sound:
        """Coin/resource collection sound."""
        duration = 0.15
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        # Bright chime
        wave = np.sin(2 * np.pi * 1200 * t) * 0.4
        wave += np.sin(2 * np.pi * 1800 * t) * 0.2
        wave *= np.exp(-t * 15)
        return self._to_sound(wave)

    def _make_resource_deposit(self) -> pygame.mixer.Sound:
        """Resource deposit sound."""
        duration = 0.18
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        # Lower chime (deposit = drop off)
        wave = np.sin(2 * np.pi * 800 * t) * 0.4
        wave += np.sin(2 * np.pi * 600 * t) * 0.3
        wave *= np.exp(-t * 12)
        return self._to_sound(wave)

    # -------------------------------------------------------------------------
    # Combat Sounds
    # -------------------------------------------------------------------------

    def _make_explosion_small(self) -> pygame.mixer.Sound:
        """Small explosion sound."""
        duration = 0.5
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        # Low boom + noise
        wave = np.sin(2 * np.pi * 80 * t) * np.exp(-t * 8) * 0.6
        noise = np.random.uniform(-0.3, 0.3, n) * np.exp(-t * 10)
        wave += noise
        return self._to_sound(wave * 0.8)

    def _make_explosion_large(self) -> pygame.mixer.Sound:
        """Large explosion sound."""
        duration = 1.0
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        # Very low boom + sustained noise
        wave = np.sin(2 * np.pi * 50 * t) * np.exp(-t * 4) * 0.7
        wave += np.sin(2 * np.pi * 100 * t) * np.exp(-t * 6) * 0.4
        noise = np.random.uniform(-0.4, 0.4, n) * np.exp(-t * 3)
        wave += noise
        return self._to_sound(wave)

    def _make_impact_hit(self) -> pygame.mixer.Sound:
        """Impact/hit sound."""
        duration = 0.1
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n)
        # Sharp thud
        wave = np.sin(2 * np.pi * 150 * t) * np.exp(-t * 30) * 0.5
        noise = np.random.uniform(-0.2, 0.2, n) * np.exp(-t * 40)
        wave += noise
        return self._to_sound(wave)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _to_sound(self, wave: np.ndarray) -> pygame.mixer.Sound:
        """Convert numpy array to pygame Sound object."""
        # Normalize
        peak = np.max(np.abs(wave))
        if peak > 0:
            wave = wave / peak
        # Convert to int16
        wave_int16 = (wave * 32767).astype(np.int16)
        # Create stereo (duplicate mono to both channels)
        stereo = np.column_stack((wave_int16, wave_int16))
        return pygame.mixer.Sound(stereo)
