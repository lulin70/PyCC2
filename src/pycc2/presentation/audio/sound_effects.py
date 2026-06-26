"""
Sound effect convenience methods extracted from SoundSystem as a mixin.

Provides play_shot, play_hit, play_explosion, play_death, play_footstep,
play_morale_change, play_command_confirm, play_unit_select, play_unit_died,
play_victory, play_defeat, and UI sound helpers.
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING

import numpy as np
import pygame
from pygame import mixer

if TYPE_CHECKING:
    from pycc2.presentation.audio.sound_system import SoundConfig, SoundType

logger = logging.getLogger(__name__)


class SoundEffectsMixin:
    """Mixin providing high-level sound-effect convenience methods.

    Expects the host class to provide:
    - self._available: bool
    - self.play(sound_type, volume): callable
    - self._config: SoundConfig
    - self._make_sound(raw): callable
    """

    _available: bool
    _config: "SoundConfig"

    @abstractmethod
    def play(self, sound_type: "SoundType", volume: float | None = None) -> bool:
        """Play a sound effect. Implemented by the host class."""
        ...

    @abstractmethod
    def _make_sound(self, raw: np.ndarray) -> mixer.Sound:
        """Create a mixer.Sound from raw audio data. Implemented by the host class."""
        ...

    # ---- UI sounds ----

    def play_ui_click(self) -> None:
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return
        self.play(SoundType.UI_CLICK)

    def play_ui_command(self) -> None:
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return
        self.play(SoundType.UI_COMMAND if hasattr(SoundType, "UI_COMMAND") else SoundType.UI_CLICK)

    def play_ui_hover(self) -> None:
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return
        self.play(SoundType.UI_HOVER)

    # ---- Combat sounds ----

    def play_shot(self, weapon_type: str = "rifle") -> None:
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return
        weapon_map = {
            "mg": SoundType.MG_BURST,
            "pistol": SoundType.PISTOL_SHOT,
            "tank_cannon": SoundType.TANK_CANNON,
            "at_gun": SoundType.AT_GUN,
            "mortar": SoundType.MORTAR,
            "smg": SoundType.SMG,
            "sniper": SoundType.SNIPER,
        }
        st = weapon_map.get(weapon_type, SoundType.RIFLE_SHOT)
        self.play(st)

    def play_hit(self, is_critical: bool = False) -> None:
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return
        self.play(SoundType.HIT_CRITICAL if is_critical else SoundType.HIT_CONFIRM)

    def play_explosion(self) -> None:
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return
        self.play(SoundType.EXPLOSION)

    def play_death(self) -> None:
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return
        self.play(SoundType.UNIT_DEATH)

    def play_footstep(self, terrain: str = "grass") -> None:
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return
        mapping = {
            "grass": SoundType.FOOTSTEP_GRASS,
            "road": SoundType.FOOTSTEP_ROAD,
            "wood": SoundType.FOOTSTEP_WOOD,
        }
        st = mapping.get(terrain, SoundType.FOOTSTEP_GRASS)
        self.play(st)

    # ---- Morale / unit state sounds ----

    def play_morale_change(self, old_state: str, new_state: str) -> None:
        """Play sound effect for morale state changes."""
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return

        warning_states = {"pinned", "suppressed", "shaken"}
        panic_states = {"broken", "routing", "fleeing"}

        if new_state.lower() in panic_states:
            self.play(SoundType.UNIT_PANIC)
        elif new_state.lower() in warning_states:
            self.play(SoundType.UNIT_SUPPRESSED)
        elif old_state and new_state == "normal" or new_state == "steady":
            self.play(SoundType.UI_SUCCESS)

    def play_command_confirm(self, command_type: str = "move") -> None:
        """Play command confirmation sound based on command type."""
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return
        self.play(SoundType.UI_COMMAND)

    def play_unit_select(self) -> None:
        """Play unit selection sound."""
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return
        self.play(SoundType.UI_SELECT)

    def play_unit_died(self) -> None:
        """Play unit death sound effect."""
        from pycc2.presentation.audio.sound_system import SoundType

        if not self._available:
            return
        self.play(SoundType.UNIT_DEATH)

    # ---- Victory / defeat ----

    def play_victory(self) -> None:
        """Play victory fanfare."""
        from pycc2.presentation.audio.sound_system import ProceduralSoundGenerator

        if not self._available:
            return
        try:
            n_samples = int(ProceduralSoundGenerator.SAMPLE_RATE * 0.8)
            t = np.linspace(0, 0.8, n_samples, dtype=np.float32)

            freqs = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
            wave = np.zeros(n_samples, dtype=np.float32)

            for i, freq in enumerate(freqs):
                start = int(i * n_samples / len(freqs))
                end = min(start + int(n_samples / len(freqs)), n_samples)
                segment = t[start:end] - t[start]
                envelope = np.exp(-segment * 3)
                wave[start:end] += np.sin(2 * np.pi * freq * segment) * envelope * 0.3

            wave = (wave / max(np.abs(wave).max(), 1) * 28000).astype(np.int16)
            sound = self._make_sound(wave)
            sound.set_volume(self._config.sfx_volume * self._config.master_volume)
            ch = mixer.find_channel(True)
            if ch:
                ch.play(sound)
        except (pygame.error, ValueError, OSError) as e:
            from pycc2.presentation.audio.sound_system import SoundType

            logger.warning("Victory sound generation failed: %s", e)
            self.play(SoundType.UI_SUCCESS)

    def play_defeat(self) -> None:
        """Play defeat sound effect."""
        from pycc2.presentation.audio.sound_system import ProceduralSoundGenerator

        if not self._available:
            return
        try:
            n_samples = int(ProceduralSoundGenerator.SAMPLE_RATE * 1.0)
            t = np.linspace(0, 1.0, n_samples, dtype=np.float32)

            freqs = [440.00, 349.23, 293.66, 220.00]  # A4, F4, D4, A3
            wave = np.zeros(n_samples, dtype=np.float32)

            for i, freq in enumerate(freqs):
                start = int(i * n_samples / len(freqs))
                end = min(start + int(n_samples / len(freqs)), n_samples)
                segment = t[start:end] - t[start]
                envelope = np.exp(-segment * 2.5)
                wave[start:end] += np.sin(2 * np.pi * freq * segment) * envelope * 0.25

            wave = (wave / max(np.abs(wave).max(), 1) * 25000).astype(np.int16)
            sound = self._make_sound(wave)
            sound.set_volume(self._config.sfx_volume * self._config.master_volume)
            ch = mixer.find_channel(True)
            if ch:
                ch.play(sound)
        except (pygame.error, ValueError, OSError) as e:
            from pycc2.presentation.audio.sound_system import SoundType

            logger.warning("Defeat sound generation failed: %s", e)
            self.play(SoundType.UI_ERROR)
