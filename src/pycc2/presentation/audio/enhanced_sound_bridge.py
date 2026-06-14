"""Enhanced Sound Bridge - Connects real audio files to combat events.

Bridges the gap between file-based sounds (WAV) and the procedural sound system.
Provides unified interface for combat event sound triggering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

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
            logger.info("Initialized with real file support")

            # Pre-load available sound files
            self._preload_sounds()

            return True

        except Exception as e:
            logger.warning("Init failed: %s", e)
            try:
                mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
                self._initialized = True
                logger.info("Fallback to mono")
                return True
            except Exception as e2:
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
                except Exception as e:
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
                except Exception as e:
                    logger.warning("Failed to load %s: %s", mapping.file_path, e)

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
        except Exception as e:
            logging.info(f"Sound file load failed: {e}")
            return None

    def _generate_cc2_combat_fallback(
        self,
        event: CombatSoundEvent,
    ) -> mixer.Sound | None:
        """Generate CC2-specific combat sounds procedurally."""
        try:

            generators = {
                CombatSoundEvent.TANK_CANNON_FIRE: self._gen_tank_cannon_fire,
                CombatSoundEvent.AT_ROCKET_FIRE: self._gen_at_rocket_fire,
                CombatSoundEvent.MORTAR_LAUNCH: self._gen_mortar_launch,
                CombatSoundEvent.GRENADE_EXPLOSION_SHORT: self._gen_grenade_explosion_short,
                CombatSoundEvent.AIRSTRIKE_BOMB: self._gen_airstrike_bomb,
                CombatSoundEvent.VEHICLE_ENGINE_START: lambda: self._gen_vehicle_engine("start"),
                CombatSoundEvent.VEHICLE_ENGINE_IDLE: lambda: self._gen_vehicle_engine("idle"),
                CombatSoundEvent.VEHICLE_MOVE: lambda: self._gen_vehicle_engine("move"),
                CombatSoundEvent.ARMOR_PENETRATE: self._gen_armor_penetrate,
                CombatSoundEvent.RICOCHET_BOUNCE: self._gen_ricochet_bounce,
                CombatSoundEvent.NEAR_MISS_WHIZZ: self._gen_near_miss_whizz,
                CombatSoundEvent.SMOKE_DEPLOY_HISS: self._gen_smoke_deploy_hiss,
                CombatSoundEvent.SUPPRESSION_FIRE: self._gen_suppression_fire,
            }

            generator = generators.get(event)
            if generator:
                raw_audio = generator()
                if raw_audio is not None:
                    sound = mixer.Sound(buffer=raw_audio.tobytes())
                    sound.set_volume(self._sfx_volume)
                    self._cache_sound(event.name, sound)
                    return sound

        except Exception as e:
            logger.warning("CC2 combat fallback failed for %s: %s", event.name, e)

        return None

    def _gen_tank_cannon_fire(self) -> np.ndarray | None:
        """Generate tank main gun fire - deep boom with reverb tail."""
        import numpy as np

        duration_ms = 800
        samples = int(44100 * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples)

        attack = int(samples * 0.02)
        decay = int(samples * 0.15)
        envelope = np.ones(samples)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack:attack + decay] = np.exp(-3 * np.arange(decay) / decay)
        envelope[attack + decay:] *= np.exp(-1.5 * np.arange(samples - attack - decay) / (samples - attack - decay))

        base_freq = 60
        fundamental = np.sin(2 * np.pi * base_freq * t) * 0.6
        harmonic2 = np.sin(2 * np.pi * base_freq * 2.3 * t) * 0.25
        harmonic3 = np.sin(2 * np.pi * base_freq * 4.7 * t) * 0.15

        noise = np.random.uniform(-1, 1, samples) * 0.3
        noise_envelope = np.exp(-8 * t / (duration_ms / 1000))
        noise *= noise_envelope

        signal = (fundamental + harmonic2 + harmonic3 + noise) * envelope
        signal = np.clip(signal, -1, 1)

        return (signal * 32767).astype(np.int16)

    def _gen_at_rocket_fire(self) -> np.ndarray | None:
        """Generate anti-tank rocket launch - whoosh + explosion."""
        import numpy as np

        duration_ms = 1200
        samples = int(44100 * duration_ms / 1000)
        np.linspace(0, duration_ms / 1000, samples)

        launch_duration = int(samples * 0.4)
        explosion_start = int(samples * 0.35)

        envelope = np.zeros(samples)
        envelope[:launch_duration] = np.exp(-2 * np.arange(launch_duration) / launch_duration) * 0.7
        if explosion_start < samples:
            exp_length = samples - explosion_start
            envelope[explosion_start:] = np.exp(-3 * np.arange(exp_length) / exp_length) * 1.0

        freq_sweep = np.linspace(200, 80, launch_duration)
        whoosh = np.sin(2 * np.pi * np.cumsum(freq_sweep) / 44100)[:launch_duration] * 0.5
        whoosh += np.random.uniform(-0.3, 0.3, launch_duration)

        explosion = np.zeros(samples)
        if explosion_start < samples:
            exp_samples = samples - explosion_start
            exp_t = np.linspace(0, exp_samples / 44100, exp_samples)
            explosion[explosion_start:] = (
                np.random.uniform(-1, 1, exp_samples) * 0.8 *
                np.exp(-4 * exp_t / (exp_samples / 44100)) +
                np.sin(2 * np.pi * 45 * exp_t) * 0.4 *
                np.exp(-5 * exp_t / (exp_samples / 44100))
            )

        signal = np.zeros(samples)
        signal[:launch_duration] = whoosh
        signal += explosion
        signal *= envelope
        signal = np.clip(signal, -1, 1)

        return (signal * 32767).astype(np.int16)

    def _gen_mortar_launch(self) -> np.ndarray | None:
        """Generate mortar launch with distinctive whistle."""
        import numpy as np

        duration_ms = 1500
        samples = int(44100 * duration_ms / 1000)
        np.linspace(0, duration_ms / 1000, samples)

        thump_samples = int(0.05 * 44100)
        whistle_start = int(0.08 * 44100)

        thump = np.zeros(samples)
        thump[:thump_samples] = (
            np.sin(2 * np.pi * 80 * np.linspace(0, 0.05, thump_samples)) * 0.7 +
            np.random.uniform(-0.4, 0.4, thump_samples)
        ) * np.exp(-8 * np.arange(thump_samples) / thump_samples)

        whistle = np.zeros(samples)
        if whistle_start < samples:
            whistle_samples = samples - whistle_start
            whistle_t = np.linspace(0, whistle_samples / 44100, whistle_samples)
            freq = np.linspace(400, 150, whistle_samples)
            phase = np.cumsum(2 * np.pi * freq / 44100)
            whistle[whistle_start:] = (
                np.sin(phase) * 0.4 +
                np.sin(phase * 1.5) * 0.2
            ) * np.exp(-1.2 * whistle_t / (duration_ms / 1000))

        impact = np.zeros(samples)
        impact_start = int(0.85 * samples)
        if impact_start < samples:
            impact_samples = samples - impact_start
            impact_t = np.linspace(0, impact_samples / 44100, impact_samples)
            impact[impact_start:] = (
                np.random.uniform(-1, 1, impact_samples) * 0.6 *
                np.exp(-6 * impact_t / (impact_samples / 44100))
            )

        signal = thump + whistle + impact
        signal = np.clip(signal, -1, 1)

        return (signal * 32767).astype(np.int16)

    def _gen_grenade_explosion_short(self) -> np.ndarray | None:
        """Generate short grenade explosion - higher frequency, shorter duration."""
        import numpy as np

        duration_ms = 200
        samples = int(44100 * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples)

        attack = int(samples * 0.01)
        envelope = np.ones(samples)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack:] *= np.exp(-12 * np.arange(samples - attack) / (samples - attack))

        base_freq = 150
        signal = (
            np.sin(2 * np.pi * base_freq * t) * 0.5 +
            np.sin(2 * np.pi * base_freq * 2.1 * t) * 0.3 +
            np.sin(2 * np.pi * base_freq * 3.5 * t) * 0.2 +
            np.random.uniform(-1, 1, samples) * 0.6
        ) * envelope

        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_airstrike_bomb(self) -> np.ndarray | None:
        """Generate airstrike bomb - multiple explosions in sequence."""
        import numpy as np

        total_duration_ms = 1500
        total_samples = int(44100 * total_duration_ms / 1000)
        signal = np.zeros(total_samples)

        explosion_intervals = [0, 150, 300]
        explosion_duration_ms = 400

        for offset_ms in explosion_intervals:
            start_sample = int(offset_ms / 1000 * 44100)
            exp_samples = int(44100 * explosion_duration_ms / 1000)
            end_sample = min(start_sample + exp_samples, total_samples)

            if start_sample >= total_samples:
                break

            actual_samples = end_sample - start_sample
            t = np.linspace(0, actual_samples / 44100, actual_samples)

            attack = min(int(actual_samples * 0.02), actual_samples)
            envelope = np.ones(actual_samples)
            envelope[:attack] = np.linspace(0, 1, attack)
            envelope[attack:] *= np.exp(-5 * np.arange(actual_samples - attack) / (actual_samples - attack))

            explosion = (
                np.random.uniform(-1, 1, actual_samples) * 0.9 *
                envelope +
                np.sin(2 * np.pi * 55 * t) * 0.4 * envelope
            )

            volume_factor = 1.0 - (offset_ms / 600) * 0.3
            signal[start_sample:end_sample] += explosion * volume_factor

        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_vehicle_engine(self, state: str) -> np.ndarray | None:
        """Generate vehicle engine sounds based on state."""
        import numpy as np

        if state == "start":
            duration_ms = 2000
            samples = int(44100 * duration_ms / 1000)
            t = np.linspace(0, duration_ms / 1000, samples)

            crank_duration = int(0.4 * 44100)
            envelope = np.zeros(samples)
            envelope[:crank_duration] = 0.3
            envelope[crank_duration:] = np.linspace(0.3, 0.8, samples - crank_duration)

            crank = np.zeros(samples)
            crank[:crank_duration] = (
                np.sin(2 * np.pi * 8 * np.linspace(0, 0.4, crank_duration)) * 0.5 +
                np.random.uniform(-0.3, 0.3, crank_duration)
            ) * np.repeat(np.linspace(1, 0.6, crank_duration), 1)

            engine_rpm = np.linspace(400, 700, samples)
            engine = np.sin(2 * np.pi * np.cumsum(engine_rpm) / 44100) * 0.6
            engine += np.sin(2 * np.pi * np.cumsum(engine_rpm * 2) / 44100) * 0.3
            pulse = 0.1 * np.sin(2 * np.pi * 15 * t)

            signal = (crank + engine + pulse) * envelope
            signal = np.clip(signal, -1, 1)
            return (signal * 32767).astype(np.int16)

        elif state == "idle":
            duration_ms = 1500
            samples = int(44100 * duration_ms / 1000)
            t = np.linspace(0, duration_ms / 1000, samples)

            base_rpm = 500
            engine = (
                np.sin(2 * np.pi * base_rpm * t) * 0.4 +
                np.sin(2 * np.pi * base_rpm * 2 * t) * 0.2 +
                np.sin(2 * np.pi * base_rpm * 0.5 * t) * 0.3
            )
            pulse = 0.15 * np.sin(2 * np.pi * 12 * t)
            rumble = np.random.uniform(-0.1, 0.1, samples) * 0.5

            signal = engine + pulse + rumble
            fade = np.linspace(0.8, 0.8, samples)
            signal *= fade
            signal = np.clip(signal, -1, 1)
            return (signal * 32767).astype(np.int16)

        elif state == "move":
            duration_ms = 1200
            samples = int(44100 * duration_ms / 1000)
            t = np.linspace(0, duration_ms / 1000, samples)

            base_rpm = np.linspace(550, 650, samples)
            engine = np.sin(2 * np.pi * np.cumsum(base_rpm) / 44100) * 0.5
            engine += np.sin(2 * np.pi * np.cumsum(base_rpm * 2.5) / 44100) * 0.25

            track_clatter = np.zeros(samples)
            clatter_interval = int(44100 / 30)
            for i in range(0, samples - 50, clatter_interval):
                end = min(i + 50, samples)
                track_clatter[i:end] = np.random.uniform(-0.2, 0.2, end - i) * np.exp(-0.5 * np.arange(end - i) / 50)

            signal = engine + track_clatter
            signal = np.clip(signal, -1, 1)
            return (signal * 32767).astype(np.int16)

        return None

    def _gen_armor_penetrate(self) -> np.ndarray | None:
        """Generate armor penetration hit - high-pitched metal piercing."""
        import numpy as np

        duration_ms = 350
        samples = int(44100 * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples)

        attack = int(samples * 0.005)
        envelope = np.ones(samples)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack:] *= np.exp(-8 * np.arange(samples - attack) / (samples - attack))

        metal_strike = (
            np.sin(2 * np.pi * 2500 * t) * 0.5 +
            np.sin(2 * np.pi * 3200 * t) * 0.3 +
            np.sin(2 * np.pi * 4100 * t) * 0.2
        )
        screech = np.sin(2 * np.pi * 6000 * t) * 0.3 * np.exp(-15 * t / (duration_ms / 1000))

        ring_decay = np.zeros(samples)
        ring_start = int(samples * 0.03)
        if ring_start < samples:
            ring_samples = samples - ring_start
            ring_t = np.linspace(0, ring_samples / 44100, ring_samples)
            ring_freq = 1800
            ring_decay[ring_start:] = (
                np.sin(2 * np.pi * ring_freq * ring_t) * 0.25 *
                np.exp(-3 * ring_t / (ring_samples / 44100))
            )

        signal = (metal_strike + screech + ring_decay) * envelope
        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_ricochet_bounce(self) -> np.ndarray | None:
        """Generate ricochet bounce - mid-frequency bounce with echo decay."""
        import numpy as np

        duration_ms = 450
        samples = int(44100 * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples)

        initial_hit = int(samples * 0.08)
        bounce1_start = int(samples * 0.18)
        bounce2_start = int(samples * 0.38)

        signal = np.zeros(samples)

        hit_t = np.linspace(0, initial_hit / 44100, initial_hit)
        signal[:initial_hit] = (
            np.sin(2 * np.pi * 1200 * hit_t) * 0.6 +
            np.random.uniform(-0.3, 0.3, initial_hit)
        ) * np.exp(-10 * np.arange(initial_hit) / initial_hit)

        for bounce_start in [bounce1_start, bounce2_start]:
            if bounce_start < samples:
                bounce_len = min(int(samples * 0.1), samples - bounce_start)
                bounce_t = np.linspace(0, bounce_len / 44100, bounce_len)
                freq = 900 if bounce_start == bounce1_start else 650
                amplitude = 0.35 if bounce_start == bounce1_start else 0.2
                signal[bounce_start:bounce_start + bounce_len] += (
                    np.sin(2 * np.pi * freq * bounce_t) * amplitude +
                    np.random.uniform(-0.15, 0.15, bounce_len) * amplitude
                ) * np.exp(-8 * np.arange(bounce_len) / bounce_len)

        echo_decay = np.exp(-2 * t / (duration_ms / 1000))
        signal *= echo_decay
        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_near_miss_whizz(self) -> np.ndarray | None:
        """Generate near miss bullet whizz - fast frequency sweep from high to low."""
        import numpy as np

        duration_ms = 180
        samples = int(44100 * duration_ms / 1000)

        freq_start = 6000
        freq_end = 800
        freq_sweep = np.linspace(freq_start, freq_end, samples)

        phase = np.cumsum(2 * np.pi * freq_sweep / 44100)
        tone = np.sin(phase) * 0.7

        noise_floor = np.random.uniform(-0.15, 0.15, samples)

        envelope = np.ones(samples)
        rise = int(samples * 0.15)
        fall_start = int(samples * 0.6)
        envelope[:rise] = np.linspace(0, 1, rise)
        envelope[fall_start:] *= np.linspace(1, 0.1, samples - fall_start)

        signal = (tone + noise_floor) * envelope
        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_smoke_deploy_hiss(self) -> np.ndarray | None:
        """Generate smoke grenade deploy - filtered white noise with slow decay."""
        import numpy as np

        duration_ms = 2000
        samples = int(44100 * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples)

        raw_noise = np.random.uniform(-1, 1, samples)

        hiss_start = int(0.02 * 44100)
        burst = np.zeros(samples)
        burst[:hiss_start] = raw_noise[:hiss_start] * 0.8 * np.exp(-20 * np.arange(hiss_start) / hiss_start)

        sustained = raw_noise * 0.4 * np.exp(-0.8 * t / (duration_ms / 1000))

        signal = burst + sustained
        low_pass = 0.95
        for i in range(1, samples):
            signal[i] = low_pass * signal[i - 1] + (1 - low_pass) * signal[i]

        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_suppression_fire(self, duration_ms: int = 1500) -> np.ndarray | None:
        """Generate suppression fire - sustained machine gun bursts."""
        import numpy as np

        samples = int(44100 * duration_ms / 1000)
        np.linspace(0, duration_ms / 1000, samples)
        signal = np.zeros(samples)

        burst_count = int(duration_ms / 120)
        for i in range(burst_count):
            burst_start = int(i * 120 / 1000 * 44100)
            burst_len = min(int(60 / 1000 * 44100), samples - burst_start)

            if burst_start >= samples or burst_len <= 0:
                break

            burst_t = np.linspace(0, burst_len / 44100, burst_len)
            burst_env = np.exp(-15 * np.arange(burst_len) / burst_len)

            shot = (
                np.sin(2 * np.pi * 180 * burst_t) * 0.5 * burst_env +
                np.random.uniform(-0.4, 0.4, burst_len) * burst_env
            )

            signal[burst_start:burst_start + burst_len] += shot

        overall_envelope = np.ones(samples)
        fade_out = int(samples * 0.85)
        overall_envelope[fade_out:] = np.linspace(1, 0.3, samples - fade_out)

        signal *= overall_envelope * 0.7
        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _generate_procedural_fallback(
        self,
        event: CombatSoundEvent,
    ) -> mixer.Sound | None:
        """Generate procedural sound when file not available."""
        cc2_result = self._generate_cc2_combat_fallback(event)
        if cc2_result is not None:
            return cc2_result

        try:
            from pycc2.presentation.audio.sound_system import (
                ProceduralSoundGenerator,
            )

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
            logger.warning("Procedural fallback failed for %s: %s", event.name, e)

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
        """
        Play vehicle engine sound.

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
        """
        Play sustained suppression fire.

        Args:
            duration_ms: Duration of suppression fire in milliseconds
        """
        if not self._initialized:
            return False

        try:
            raw_audio = self._gen_suppression_fire(duration_ms)
            if raw_audio is not None:
                sound = mixer.Sound(buffer=raw_audio.tobytes())
                final_vol = self._sfx_volume * self._master_volume
                sound.set_volume(max(0.0, min(1.0, final_vol)))
                channel = mixer.find_channel(True)
                if channel is None:
                    channel = mixer.Channel(0)
                channel.play(sound)
                return True
        except Exception as e:
            logger.warning("Suppression fire failed: %s", e)

        return False

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