"""Enhanced Sound Bridge - Connects real audio files to combat events.

Bridges the gap between file-based sounds (WAV) and the procedural sound system.
Provides unified interface for combat event sound triggering.

TD-072: Procedural waveform synthesis has been extracted to
``procedural_sound_synthesizer.py``. This module now focuses solely on audio
bridging: file loading, caching, playback dispatch, and volume mixing. The
``CombatSoundEvent`` enum was extracted to ``combat_sound_events.py`` to break
the circular dependency between this module and the synthesizer.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pygame
from pygame import mixer

from pycc2.presentation.audio.combat_sound_events import CombatSoundEvent
from pycc2.presentation.audio.procedural_sound_synthesizer import (
    ProceduralSoundSynthesizer,
)

logger = logging.getLogger(__name__)

__all__ = [
    "CombatSoundEvent",
    "SoundFileMapping",
    "DEFAULT_SOUND_MAPPINGS",
    "EnhancedSoundSystem",
    "get_enhanced_sound_system",
]


@dataclass(slots=True)
class SoundFileMapping:
    """Maps combat events to actual audio file paths."""

    event: CombatSoundEvent
    file_path: str
    volume: float = 1.0
    fallback_generator: Callable | None = None


# Default sound file mappings (relative to project root)
DEFAULT_SOUND_MAPPINGS: list[SoundFileMapping] = [
    SoundFileMapping(
        event=CombatSoundEvent.EXPLOSION,
        file_path="data/sounds/weapons/explosion.wav",
        volume=0.9,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.RIFLE_FIRE,
        file_path="data/sounds/weapons/rifle_shot.wav",
        volume=0.8,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.TANK_CANNON_FIRE,
        file_path="data/sounds/weapons/tank_cannon.wav",
        volume=1.0,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.AT_ROCKET_FIRE,
        file_path="data/sounds/weapons/at_gun.wav",
        volume=0.9,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.MORTAR_LAUNCH,
        file_path="data/sounds/weapons/mortar.wav",
        volume=0.85,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.GRENADE_EXPLOSION_SHORT,
        file_path="",
        volume=0.8,
        fallback_generator=lambda: None,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.AIRSTRIKE_BOMB,
        file_path="",
        volume=1.0,
        fallback_generator=lambda: None,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.VEHICLE_ENGINE_START,
        file_path="",
        volume=0.7,
        fallback_generator=lambda: None,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.VEHICLE_ENGINE_IDLE,
        file_path="",
        volume=0.5,
        fallback_generator=lambda: None,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.VEHICLE_MOVE,
        file_path="",
        volume=0.6,
        fallback_generator=lambda: None,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.ARMOR_PENETRATE,
        file_path="",
        volume=0.9,
        fallback_generator=lambda: None,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.RICOCHET_BOUNCE,
        file_path="",
        volume=0.75,
        fallback_generator=lambda: None,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.NEAR_MISS_WHIZZ,
        file_path="",
        volume=0.65,
        fallback_generator=lambda: None,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.SMOKE_DEPLOY_HISS,
        file_path="",
        volume=0.6,
        fallback_generator=lambda: None,
    ),
    SoundFileMapping(
        event=CombatSoundEvent.SUPPRESSION_FIRE,
        file_path="",
        volume=0.85,
        fallback_generator=lambda: None,
    ),
]


@dataclass
class EnhancedSoundSystem:
    """Enhanced sound system that combines file-based and procedural sounds.

    Features:
    - Priority: Real WAV files > Procedural generation > Silence
    - 3D positional audio support (future)
    - Combat event integration
    - Volume mixing and ducking
    - Performance-optimized caching
    """

    def __init__(self):
        """初始化增强声音系统的缓存、音量与默认事件映射。"""
        self._sound_cache: dict[str, mixer.Sound] = {}
        self._event_mappings: dict[CombatSoundEvent, SoundFileMapping] = {}
        self._initialized = False
        self._master_volume: float = 0.8
        self._sfx_volume: float = 1.0
        self._base_path: Path = Path.cwd()
        self._synth: ProceduralSoundSynthesizer = ProceduralSoundSynthesizer(
            self._sfx_volume
        )

        self._initialize_default_mappings()

    def _initialize_default_mappings(self) -> None:
        """Set up default sound file mappings."""
        for mapping in DEFAULT_SOUND_MAPPINGS:
            self._event_mappings[mapping.event] = mapping

    def initialize(self) -> bool:
        """Initialize the audio system.

        Returns:
            True if initialization successful

        """
        if self._initialized:
            return True

        try:
            mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._initialized = True
            logger.info("Initialized with real file support")

            # Pre-load available sound files
            self._preload_sounds()

            return True

        except (pygame.error, RuntimeError) as e:
            logger.warning("Init failed: %s", e)
            try:
                mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
                self._initialized = True
                logger.info("Fallback to mono")
                return True
            except (pygame.error, RuntimeError) as e2:
                logger.warning("Mono also failed: %s", e2)
                return False

    def _preload_sounds(self) -> None:
        """Pre-load all mapped sound files into cache."""
        for event, mapping in self._event_mappings.items():
            full_path = self._base_path / mapping.file_path

            if full_path.exists():
                try:
                    sound = mixer.Sound(str(full_path))
                    sound.set_volume(mapping.volume * self._sfx_volume)
                    self._cache_sound(event.name, sound)
                    logger.info("Loaded: %s", mapping.file_path)
                except (pygame.error, FileNotFoundError, ValueError) as e:
                    logger.warning("Failed to load %s: %s", mapping.file_path, e)

    def _cache_sound(self, key: str, sound: mixer.Sound) -> None:
        self._sound_cache[key] = sound

    def _get_cached_sound(self, key: str) -> mixer.Sound | None:
        return self._sound_cache.get(key)

    def register_sound_mapping(self, mapping: SoundFileMapping) -> None:
        """Register a new sound file mapping."""
        self._event_mappings[mapping.event] = mapping

        # Try to load immediately if initialized
        if self._initialized:
            full_path = self._base_path / mapping.file_path
            if full_path.exists():
                try:
                    sound = mixer.Sound(str(full_path))
                    sound.set_volume(mapping.volume * self._sfx_volume)
                    self._cache_sound(mapping.event.name, sound)
                except (pygame.error, FileNotFoundError, ValueError) as e:
                    logger.warning("Failed to load %s: %s", mapping.file_path, e)

    def play_combat_event(
        self,
        event: CombatSoundEvent,
        volume: float | None = None,
        position: tuple[float, float, float] | None = None,
    ) -> bool:
        """Play sound for a combat event.

        Args:
            event: Combat sound event to play
            volume: Optional volume override (0.0-1.0)
            position: Optional 3D position for spatial audio (x, y, z)

        Returns:
            True if sound was played successfully

        """
        if not self._initialized:
            return False

        # Try cached sound first
        sound = self._get_cached_sound(event.name)

        if sound is None:
            # Try loading from mapping
            mapping = self._event_mappings.get(event)
            if mapping and mapping.file_path:
                sound = self._load_sound_from_file(mapping)

            if sound is None:
                # Fall back to procedural generator
                sound = self._generate_procedural_fallback(event)

        if sound is None:
            return False

        # Apply volume
        final_vol = volume if volume is not None else self._sfx_volume
        final_vol *= self._master_volume
        final_vol = max(0.0, min(1.0, final_vol))
        sound.set_volume(final_vol)

        # Play on available channel
        channel = mixer.find_channel(True)
        if channel is None:
            channel = mixer.Channel(0)

        channel.play(sound)
        return True

    def _load_sound_from_file(
        self,
        mapping: SoundFileMapping,
    ) -> mixer.Sound | None:
        """Attempt to load sound from file path."""
        full_path = self._base_path / mapping.file_path

        if not full_path.exists():
            return None

        try:
            sound = mixer.Sound(str(full_path))
            self._cache_sound(mapping.event.name, sound)
            return sound
        except (pygame.error, FileNotFoundError, ValueError) as e:
            logging.info(f"Sound file load failed: {e}")
            return None

    def _generate_cc2_combat_fallback(
        self,
        event: CombatSoundEvent,
    ) -> mixer.Sound | None:
        """Generate CC2-specific combat sounds via ProceduralSoundSynthesizer.

        Delegates waveform synthesis to the synthesizer; this method only
        wraps the resulting ndarray into a ``mixer.Sound`` and caches it.
        """
        try:
            raw_audio = self._synth.generate_cc2_combat(event)
            if raw_audio is not None:
                sound = mixer.Sound(buffer=raw_audio.tobytes())
                sound.set_volume(self._sfx_volume)
                self._cache_sound(event.name, sound)
                return sound
        except (pygame.error, RuntimeError, ValueError) as e:
            logger.warning("CC2 combat fallback failed for %s: %s", event.name, e)

        return None

    def _generate_procedural_fallback(
        self,
        event: CombatSoundEvent,
    ) -> mixer.Sound | None:
        """Generate procedural sound when file not available.

        Tries CC2-specific generators first, then falls back to the generic
        ``sound_system.ProceduralSoundGenerator`` dispatch. Both paths are
        delegated to ``ProceduralSoundSynthesizer``.
        """
        cc2_result = self._generate_cc2_combat_fallback(event)
        if cc2_result is not None:
            return cc2_result

        try:
            raw = self._synth.generate_via_sound_system(event)
            if raw is not None:
                sound = mixer.Sound(array=raw)
                self._cache_sound(event.name, sound)
                return sound
        except (pygame.error, RuntimeError, ValueError, ImportError) as e:
            logger.warning("Procedural fallback failed for %s: %s", event.name, e)

        return None

    # Convenience methods for common combat events
    def play_rifle_fire(self) -> bool:
        """Play the rifle fire sound."""
        return self.play_combat_event(CombatSoundEvent.RIFLE_FIRE)

    def play_mg_fire(self) -> bool:
        """Play the mg fire sound."""
        return self.play_combat_event(CombatSoundEvent.MG_FIRE)

    def play_explosion(self) -> bool:
        """Play the explosion sound."""
        return self.play_combat_event(CombatSoundEvent.EXPLOSION)

    def play_unit_death(self) -> bool:
        """Play the unit death sound."""
        return self.play_combat_event(CombatSoundEvent.UNIT_DEATH)

    def play_hit_confirmation(self, is_critical: bool = False) -> bool:
        """Play the hit confirmation sound."""
        event = CombatSoundEvent.HIT_CRITICAL if is_critical else CombatSoundEvent.HIT_CONFIRM
        return self.play_combat_event(event)

    def play_weapon_reload(self) -> bool:
        """Play the weapon reload sound."""
        return self.play_combat_event(CombatSoundEvent.WEAPON_RELOAD)

    def play_weapon_switch_sound(self) -> bool:
        """Play the weapon switch sound sound."""
        return self.play_combat_event(CombatSoundEvent.WEAPON_SWITCH)

    # CC2-specific combat convenience methods
    def play_tank_fire(self) -> bool:
        """Play tank main cannon fire sound."""
        return self.play_combat_event(CombatSoundEvent.TANK_CANNON_FIRE)

    def play_at_rocket_fire(self) -> bool:
        """Play anti-tank rocket launch (Bazooka/Panzerschreck)."""
        return self.play_combat_event(CombatSoundEvent.AT_ROCKET_FIRE)

    def play_mortar_launch(self) -> bool:
        """Play mortar launch with whistle."""
        return self.play_combat_event(CombatSoundEvent.MORTAR_LAUNCH)

    def play_grenade_explosion(self) -> bool:
        """Play short grenade explosion."""
        return self.play_combat_event(CombatSoundEvent.GRENADE_EXPLOSION_SHORT)

    def play_airstrike_bomb(self) -> bool:
        """Play airstrike bomb sequence."""
        return self.play_combat_event(CombatSoundEvent.AIRSTRIKE_BOMB)

    def play_vehicle_engine(self, state: str = "idle") -> bool:
        """Play vehicle engine sound.

        Args:
            state: Engine state - "start", "idle", or "move"

        """
        state_map = {
            "start": CombatSoundEvent.VEHICLE_ENGINE_START,
            "idle": CombatSoundEvent.VEHICLE_ENGINE_IDLE,
            "move": CombatSoundEvent.VEHICLE_MOVE,
        }
        event = state_map.get(state.lower(), CombatSoundEvent.VEHICLE_ENGINE_IDLE)
        return self.play_combat_event(event)

    def play_armor_penetrate(self) -> bool:
        """Play armor penetration hit sound."""
        return self.play_combat_event(CombatSoundEvent.ARMOR_PENETRATE)

    def play_ricochet(self) -> bool:
        """Play ricochet bounce sound."""
        return self.play_combat_event(CombatSoundEvent.RICOCHET_BOUNCE)

    def play_near_miss(self) -> bool:
        """Play near miss bullet whizz."""
        return self.play_combat_event(CombatSoundEvent.NEAR_MISS_WHIZZ)

    def play_suppression_fire(self, duration_ms: int = 1500) -> bool:
        """Play sustained suppression fire.

        Args:
            duration_ms: Duration of suppression fire in milliseconds

        """
        if not self._initialized:
            return False

        try:
            raw_audio = self._synth.generate_suppression_fire(duration_ms)
            if raw_audio is not None:
                sound = mixer.Sound(buffer=raw_audio.tobytes())
                final_vol = self._sfx_volume * self._master_volume
                sound.set_volume(max(0.0, min(1.0, final_vol)))
                channel = mixer.find_channel(True)
                if channel is None:
                    channel = mixer.Channel(0)
                channel.play(sound)
                return True
        except (pygame.error, RuntimeError, ValueError) as e:
            logger.warning("Suppression fire failed: %s", e)

        return False

    @property
    def master_volume(self) -> float:
        """Get the master volume."""
        return self._master_volume

    @master_volume.setter
    def master_volume(self, value: float) -> None:
        self._master_volume = max(0.0, min(1.0, value))

    @property
    def sfx_volume(self) -> float:
        """Get the sfx volume."""
        return self._sfx_volume

    @sfx_volume.setter
    def sfx_volume(self, value: float) -> None:
        self._sfx_volume = max(0.0, min(1.0, value))
        self._synth.sfx_volume = self._sfx_volume

    def shutdown(self) -> None:
        """Shutdown audio system and free resources."""
        if self._initialized:
            mixer.quit()
            self._sound_cache.clear()
            self._initialized = False


# Global singleton instance
_enhanced_sound_instance: EnhancedSoundSystem | None = None


def get_enhanced_sound_system() -> EnhancedSoundSystem:
    """Get or create the global enhanced sound system instance."""
    global _enhanced_sound_instance

    if _enhanced_sound_instance is None:
        _enhanced_sound_instance = EnhancedSoundSystem()

    return _enhanced_sound_instance
