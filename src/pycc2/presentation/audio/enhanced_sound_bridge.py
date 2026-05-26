"""Enhanced Sound Bridge - Connects real audio files to combat events.

Bridges the gap between file-based sounds (WAV) and the procedural sound system.
Provides unified interface for combat event sound triggering.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable

from pygame import mixer


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
]


@dataclass
class EnhancedSoundSystem:
    """
    Enhanced sound system that combines file-based and procedural sounds.
    
    Features:
    - Priority: Real WAV files > Procedural generation > Silence
    - 3D positional audio support (future)
    - Combat event integration
    - Volume mixing and ducking
    - Performance-optimized caching
    """

    def __init__(self):
        self._sound_cache: dict[str, mixer.Sound] = {}
        self._event_mappings: dict[CombatSoundEvent, SoundFileMapping] = {}
        self._initialized = False
        self._master_volume: float = 0.8
        self._sfx_volume: float = 1.0
        self._base_path: Path = Path.cwd()

        self._initialize_default_mappings()

    def _initialize_default_mappings(self) -> None:
        """Set up default sound file mappings."""
        for mapping in DEFAULT_SOUND_MAPPINGS:
            self._event_mappings[mapping.event] = mapping

    def initialize(self) -> bool:
        """
        Initialize the audio system.
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True

        try:
            mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._initialized = True
            print("[EnhancedAudio] Initialized with real file support")
            
            # Pre-load available sound files
            self._preload_sounds()
            
            return True
            
        except Exception as e:
            print(f"[EnhancedAudio] Init failed: {e}")
            try:
                mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
                self._initialized = True
                print("[EnhancedAudio] Fallback to mono")
                return True
            except Exception as e2:
                print(f"[EnhancedAudio] Mono also failed: {e2}")
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
                    print(f"[EnhancedAudio] Loaded: {mapping.file_path}")
                except Exception as e:
                    print(f"[EnhancedAudio] Failed to load {mapping.file_path}: {e}")

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
                except Exception as e:
                    print(f"[EnhancedAudio] Failed to load {mapping.file_path}: {e}")

    def play_combat_event(
        self,
        event: CombatSoundEvent,
        volume: float | None = None,
        position: tuple[float, float, float] | None = None,
    ) -> bool:
        """
        Play sound for a combat event.
        
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
        except Exception:
            return None

    def _generate_procedural_fallback(
        self,
        event: CombatSoundEvent,
    ) -> mixer.Sound | None:
        """Generate procedural sound when file not available."""
        try:
            from pycc2.presentation.audio.sound_system import (
                ProceduralSoundGenerator,
                SoundType,
            )
            import numpy as np

            generators = {
                CombatSoundEvent.RIFLE_FIRE: lambda: ProceduralSoundGenerator.generate_rifle_shot(),
                CombatSoundEvent.MG_FIRE: lambda: ProceduralSoundGenerator.generate_mg_burst(),
                CombatSoundEvent.PISTOL_FIRE: lambda: ProceduralSoundGenerator.generate_rifle_shot(duration_ms=80),
                CombatSoundEvent.EXPLOSION: lambda: ProceduralSoundGenerator.generate_explosion(),
                CombatSoundEvent.HIT_CONFIRM: lambda: ProceduralSoundGenerator.generate_hit_confirm(),
                CombatSoundEvent.HIT_CRITICAL: lambda: ProceduralSoundGenerator.generate_hit_confirm(duration_ms=120),
                CombatSoundEvent.UNIT_DEATH: lambda: ProceduralSoundGenerator.generate_death_cry(),
                CombatSoundEvent.WEAPON_RELOAD: lambda: ProceduralSoundGenerator.click(duration_ms=50, frequency=400),
            }

            generator = generators.get(event)
            if generator:
                raw = generator()
                sound = mixer.Sound(array=raw)
                self._cache_sound(event.name, sound)
                return sound
                
        except Exception as e:
            print(f"[EnhancedAudio] Procedural fallback failed for {event.name}: {e}")
            
        return None

    # Convenience methods for common combat events
    def play_rifle_fire(self) -> bool:
        return self.play_combat_event(CombatSoundEvent.RIFLE_FIRE)

    def play_mg_fire(self) -> bool:
        return self.play_combat_event(CombatSoundEvent.MG_FIRE)

    def play_explosion(self) -> bool:
        return self.play_combat_event(CombatSoundEvent.EXPLOSION)

    def play_unit_death(self) -> bool:
        return self.play_combat_event(CombatSoundEvent.UNIT_DEATH)

    def play_hit_confirmation(self, is_critical: bool = False) -> bool:
        event = CombatSoundEvent.HIT_CRITICAL if is_critical else CombatSoundEvent.HIT_CONFIRM
        return self.play_combat_event(event)

    def play_weapon_reload(self) -> bool:
        return self.play_combat_event(CombatSoundEvent.WEAPON_RELOAD)

    def play_weapon_switch_sound(self) -> bool:
        return self.play_combat_event(CombatSoundEvent.WEAPON_SWITCH)

    @property
    def master_volume(self) -> float:
        return self._master_volume

    @master_volume.setter
    def master_volume(self, value: float) -> None:
        self._master_volume = max(0.0, min(1.0, value))

    @property
    def sfx_volume(self) -> float:
        return self._sfx_volume

    @sfx_volume.setter
    def sfx_volume(self, value: float) -> None:
        self._sfx_volume = max(0.0, min(1.0, value))

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