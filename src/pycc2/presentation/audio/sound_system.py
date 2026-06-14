from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
from pygame import mixer

from pycc2.presentation.audio.sound_effects import SoundEffectsMixin

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.value_objects.vec2 import Vec2


from pycc2.domain.value_objects.audio_enums import SoundType  # noqa: F401 — re-exported for backward compat


@dataclass(slots=True)
class SoundConfig:
    master_volume: float = 0.7
    sfx_volume: float = 1.0
    music_volume: float = 0.5
    enabled: bool = True
    sample_rate: int = 22050


@dataclass(slots=True)
class AudioMixerConfig:
    max_simultaneous_sounds: int = 16
    distance_model: str = "inverse"
    reference_distance: float = 100.0
    max_distance: float = 800.0
    rolloff_factor: float = 1.0
    doppler_enabled: bool = False
    stereo_separation: float = 1.0
    hrtf_approximation: bool = False


class SoundPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


class ProceduralSoundGenerator:
    SAMPLE_RATE = 22050

    @classmethod
    def generate_click(cls, duration_ms: int = 50, frequency: float = 800.0) -> np.ndarray:
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)
        envelope = np.exp(-t * 80)
        wave = np.sin(2 * np.pi * frequency * t) * envelope
        return (wave * 32767).astype(np.int16)

    @classmethod
    def generate_hover(cls, duration_ms: int = 20, frequency: float = 1200.0) -> np.ndarray:
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)
        envelope = np.exp(-t * 120)
        wave = np.sin(2 * np.pi * frequency * t) * envelope
        return (wave * 20000).astype(np.int16)

    @classmethod
    def generate_rifle_shot(cls, duration_ms: int = 150) -> np.ndarray:
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)

        noise_burst = np.random.uniform(-1, 1, n_samples).astype(np.float32)
        attack = np.exp(-t * 40)
        noise_burst *= attack * 3

        boom = np.sin(2 * np.pi * 80 * t) * np.exp(-t * 15) * 0.5

        crack = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 60) * 0.3

        wave = noise_burst + boom + crack
        return (wave * 25000).astype(np.int16)

    @classmethod
    def generate_mg_burst(cls, duration_ms: int = 300, burst_count: int = 3) -> np.ndarray:
        single = cls.generate_rifle_shot(duration_ms // burst_count)
        total_len = len(single) * burst_count
        result = np.zeros(total_len, dtype=np.int16)
        for i in range(burst_count):
            start = i * len(single)
            end = start + len(single)
            decay = 1.0 - (i / burst_count) * 0.4
            result[start:end] = (single.astype(np.float32) * decay).astype(np.int16)
        return result

    @classmethod
    def generate_explosion(cls, duration_ms: int = 500) -> np.ndarray:
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)

        low_freq = np.sin(2 * np.pi * 45 * t) * np.exp(-t * 4) * 1.2
        mid_freq = np.sin(2 * np.pi * 90 * t) * np.exp(-t * 6) * 0.8
        noise = np.random.uniform(-0.3, 0.3, n_samples).astype(np.float32)
        noise *= np.exp(-t * 2)

        wave = low_freq + mid_freq + noise
        return (wave * 28000).astype(np.int16)

    @classmethod
    def generate_hit_confirm(cls, duration_ms: int = 80) -> np.ndarray:
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)
        fundamental = np.sign(np.sin(2 * np.pi * 600 * t)) * np.exp(-t * 30)
        harmonic = np.sin(2 * np.pi * 1200 * t) * np.exp(-t * 50) * 0.3
        return ((fundamental + harmonic) * 28000).astype(np.int16)

    @classmethod
    def generate_death_cry(cls, duration_ms: int = 600) -> np.ndarray:
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)
        freq_start, freq_end = 400.0, 100.0
        freq = freq_start + (freq_end - freq_start) * (t / (duration_ms / 1000))
        phase = 2 * np.pi * np.cumsum(freq) / cls.SAMPLE_RATE
        wave = np.sin(phase) * np.exp(-t * 2)
        wave += np.random.normal(0, 0.08, n_samples).astype(np.float32) * np.exp(-t * 3)
        return (wave * 22000).astype(np.int16)

    @classmethod
    def generate_tank_cannon(cls, duration_ms: int = 800) -> np.ndarray:
        """Low-frequency long pulse with reverb tail."""
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)
        # Deep fundamental with harmonics
        fundamental = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 4) * 0.7
        harmonic = np.sin(2 * np.pi * 110 * t) * np.exp(-t * 6) * 0.3
        # Noise burst for the crack
        noise = np.random.uniform(-1, 1, n_samples).astype(np.float32) * np.exp(-t * 12) * 0.5
        # Reverb tail (delayed echo)
        echo_start = int(0.15 * n_samples)
        echo = np.zeros(n_samples, dtype=np.float32)
        echo_t = t[:n_samples - echo_start]
        echo[echo_start:] = np.sin(2 * np.pi * 50 * echo_t) * np.exp(-echo_t * 3) * 0.25
        wave = fundamental + harmonic + noise + echo
        return (wave * 26000).astype(np.int16)

    @classmethod
    def generate_at_gun(cls, duration_ms: int = 400) -> np.ndarray:
        """Mid-frequency sharp pulse."""
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)
        # Mid-frequency crack
        crack = np.sin(2 * np.pi * 200 * t) * np.exp(-t * 15) * 0.6
        # Higher snap
        snap = np.sin(2 * np.pi * 600 * t) * np.exp(-t * 30) * 0.3
        # Noise
        noise = np.random.uniform(-1, 1, n_samples).astype(np.float32) * np.exp(-t * 10) * 0.4
        wave = crack + snap + noise
        return (wave * 25000).astype(np.int16)

    @classmethod
    def generate_mortar(cls, duration_ms: int = 1200) -> np.ndarray:
        """Low-frequency thump with delayed reverb echo."""
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)
        # Initial thump
        thump = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 8) * 0.8
        # Noise burst
        noise = np.random.uniform(-1, 1, n_samples).astype(np.float32) * np.exp(-t * 15) * 0.3
        # Delayed echo (incoming shell impact)
        echo_start = int(0.6 * n_samples)
        echo = np.zeros(n_samples, dtype=np.float32)
        echo_t = t[:n_samples - echo_start]
        echo[echo_start:] = (
            np.sin(2 * np.pi * 60 * echo_t) * np.exp(-echo_t * 5) * 0.4
            + np.random.uniform(-0.3, 0.3, len(echo_t)).astype(np.float32) * np.exp(-echo_t * 6) * 0.3
        )
        wave = thump + noise + echo
        return (wave * 26000).astype(np.int16)

    @classmethod
    def generate_smg(cls, duration_ms: int = 200) -> np.ndarray:
        """Rapid short pulses (like MG but shorter bursts)."""
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)
        # Multiple rapid bursts
        burst_count = 4
        burst_len = n_samples // burst_count
        wave = np.zeros(n_samples, dtype=np.float32)
        for i in range(burst_count):
            start = i * burst_len
            end = min(start + burst_len, n_samples)
            seg_t = np.linspace(0, (end - start) / cls.SAMPLE_RATE, end - start, dtype=np.float32)
            decay = 1.0 - (i / burst_count) * 0.3
            noise = np.random.uniform(-1, 1, end - start).astype(np.float32) * np.exp(-seg_t * 50) * 0.6
            pop = np.sin(2 * np.pi * 300 * seg_t) * np.exp(-seg_t * 40) * 0.3
            wave[start:end] = (noise + pop) * decay
        return (wave * 22000).astype(np.int16)

    @classmethod
    def generate_sniper(cls, duration_ms: int = 300) -> np.ndarray:
        """High-frequency sharp crack with long decay tail."""
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)
        # High-frequency sharp crack
        crack = np.sin(2 * np.pi * 2500 * t) * np.exp(-t * 50) * 0.4
        # Supersonic snap
        snap = np.sin(2 * np.pi * 4000 * t) * np.exp(-t * 80) * 0.2
        # Long decay tail (echo)
        tail = np.sin(2 * np.pi * 800 * t) * np.exp(-t * 5) * 0.3
        # Noise burst
        noise = np.random.uniform(-1, 1, n_samples).astype(np.float32) * np.exp(-t * 30) * 0.3
        wave = crack + snap + tail + noise
        return (wave * 24000).astype(np.int16)

    @classmethod
    def generate_footstep(cls, surface: str = "grass") -> np.ndarray:
        duration_ms = 100
        n_samples = int(cls.SAMPLE_RATE * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)

        if surface == "grass":
            crunch = np.random.uniform(-0.5, 0.5, n_samples).astype(np.float32)
            crunch *= np.exp(-t * 30)
            thud = np.sin(2 * np.pi * 150 * t) * np.exp(-t * 25) * 0.4
            wave = crunch + thud
        elif surface == "road":
            click = np.sign(np.sin(2 * np.pi * 800 * t)) * np.exp(-t * 35)
            wave = click * 0.7
        else:
            hollow_thunk = np.sin(2 * np.pi * 200 * t) * np.exp(-t * 18) * 0.8
            wave = hollow_thunk

        return (wave * 18000).astype(np.int16)


class SoundSystem(SoundEffectsMixin):
    def __init__(self, config: SoundConfig | None = None, mixer_config: AudioMixerConfig | None = None):
        self._config = config or SoundConfig()
        self._mixer_config = mixer_config or AudioMixerConfig()
        self._cache: dict[str, mixer.Sound] = {}
        self._initialized = False
        self._available = False
        self._channel_count = 8
        self._mixer_channels = 1
        self._active_sounds: dict[int, tuple[SoundType, SoundPriority]] = {}
        self._peak_active_count = 0
        self._dropped_sound_count = 0
        self._category_volumes: dict[str, float] = {
            "ui": 1.0,
            "combat": 1.0,
            "environment": 1.0,
            "music": 1.0,
        }
        self._music_ducked = False
        self._original_music_volume = self._config.music_volume

    def initialize(self) -> None:
        if self._initialized:
            return
        try:
            mixer.init(
                frequency=ProceduralSoundGenerator.SAMPLE_RATE,
                size=-16,
                channels=2,
                buffer=512,
            )
            self._mixer_channels = 2
            self._channel_count = 8
            self._initialized = True
            self._available = True
            logger.info("Initialized stereo mixer (2 channels)")
        except Exception as stereo_err:
            logger.info("Stereo init failed: %s, trying mono fallback...", stereo_err)
            try:
                mixer.quit()
                mixer.init(
                    frequency=ProceduralSoundGenerator.SAMPLE_RATE,
                    size=-16,
                    channels=1,
                    buffer=512,
                )
                self._mixer_channels = 1
                self._channel_count = 4
                self._initialized = True
                self._available = True
                logger.info("Fallback to mono mixer (1 channel)")
            except Exception as mono_err:
                logger.warning("Mono init also failed: %s", mono_err)
                logger.warning("Audio system disabled - game will run without sound")
                self._available = False
                self._config.enabled = False
                return

        if self._initialized:
            try:
                self._pregenerate_common_sounds()
            except Exception as sound_err:
                logger.warning("Warning: Sound pregeneration failed: %s", sound_err)
                logger.info("Individual sounds will be generated on-demand")

    def shutdown(self) -> None:
        if self._initialized:
            mixer.quit()
            self._initialized = False
            self._available = False
            self._cache.clear()

    def _make_sound(self, raw: np.ndarray) -> mixer.Sound:
        """Create a pygame Sound from a mono int16 array, converting to stereo if needed."""
        if self._mixer_channels == 2 and raw.ndim == 1:
            stereo = np.column_stack((raw, raw))
            return mixer.Sound(array=stereo)
        return mixer.Sound(array=raw)

    def _pregenerate_common_sounds(self) -> None:
        common = [
            (SoundType.UI_CLICK, lambda: ProceduralSoundGenerator.generate_click()),
            (SoundType.UI_HOVER, lambda: ProceduralSoundGenerator.generate_hover()),
            (SoundType.UI_COMMAND, lambda: ProceduralSoundGenerator.generate_click(frequency=600)),
            (SoundType.UI_SELECT, lambda: ProceduralSoundGenerator.generate_click(frequency=1000)),
            (SoundType.RIFLE_SHOT, lambda: ProceduralSoundGenerator.generate_rifle_shot()),
            (SoundType.MG_BURST, lambda: ProceduralSoundGenerator.generate_mg_burst()),
            (SoundType.EXPLOSION, lambda: ProceduralSoundGenerator.generate_explosion()),
            (SoundType.HIT_CONFIRM, lambda: ProceduralSoundGenerator.generate_hit_confirm()),
            (
                SoundType.HIT_CRITICAL,
                lambda: ProceduralSoundGenerator.generate_hit_confirm(duration_ms=120),
            ),
            (SoundType.UNIT_DEATH, lambda: ProceduralSoundGenerator.generate_death_cry()),
            (SoundType.FOOTSTEP_GRASS, lambda: ProceduralSoundGenerator.generate_footstep("grass")),
            (SoundType.FOOTSTEP_ROAD, lambda: ProceduralSoundGenerator.generate_footstep("road")),
            (SoundType.TANK_CANNON, lambda: ProceduralSoundGenerator.generate_tank_cannon()),
            (SoundType.AT_GUN, lambda: ProceduralSoundGenerator.generate_at_gun()),
            (SoundType.MORTAR, lambda: ProceduralSoundGenerator.generate_mortar()),
            (SoundType.SMG, lambda: ProceduralSoundGenerator.generate_smg()),
            (SoundType.SNIPER, lambda: ProceduralSoundGenerator.generate_sniper()),
        ]
        for sound_type, generator in common:
            raw = generator()
            sound = self._make_sound(raw)
            sound.set_volume(self._config.sfx_volume)
            self._cache[sound_type.name] = sound

    def play(self, sound_type: SoundType, volume: float | None = None) -> bool:
        if not self._available or not self._config.enabled:
            return False

        name = sound_type.name
        sound = self._cache.get(name)
        if sound is None:
            generators = {
                SoundType.UI_CANCEL: lambda: ProceduralSoundGenerator.generate_click(frequency=400),
                SoundType.UI_ERROR: lambda: ProceduralSoundGenerator.generate_click(frequency=300),
                SoundType.UI_SUCCESS: lambda: ProceduralSoundGenerator.generate_click(
                    frequency=1000, duration_ms=80
                ),
                SoundType.RICOCHET: lambda: ProceduralSoundGenerator.generate_hit_confirm(
                    duration_ms=40
                ),
                SoundType.UNIT_MOVE: lambda: ProceduralSoundGenerator.generate_footstep(),
                SoundType.UNIT_PANIC: lambda: ProceduralSoundGenerator.generate_hover(
                    frequency=500, duration_ms=100
                ),
                SoundType.UNIT_SUPPRESSED: lambda: ProceduralSoundGenerator.generate_hover(
                    frequency=350, duration_ms=80
                ),
                SoundType.PISTOL_SHOT: lambda: ProceduralSoundGenerator.generate_rifle_shot(
                    duration_ms=80
                ),
                SoundType.AMBIENT_WIND: lambda: np.zeros(1000, dtype=np.int16),
                SoundType.AMBIENT_BIRD: lambda: np.zeros(2000, dtype=np.int16),
                SoundType.FOOTSTEP_WOOD: lambda: ProceduralSoundGenerator.generate_footstep("wood"),
                SoundType.TANK_CANNON: lambda: ProceduralSoundGenerator.generate_tank_cannon(),
                SoundType.AT_GUN: lambda: ProceduralSoundGenerator.generate_at_gun(),
                SoundType.MORTAR: lambda: ProceduralSoundGenerator.generate_mortar(),
                SoundType.SMG: lambda: ProceduralSoundGenerator.generate_smg(),
                SoundType.SNIPER: lambda: ProceduralSoundGenerator.generate_sniper(),
            }
            gen = generators.get(sound_type)
            if gen:
                raw = gen()
                sound = self._make_sound(raw)
                self._cache[name] = sound

        if sound is None:
            return False

        vol = volume if volume is not None else self._config.sfx_volume
        final_vol = vol * self._config.master_volume
        sound.set_volume(max(0.0, min(1.0, final_vol)))

        ch = mixer.find_channel(True)
        if ch is None:
            ch = mixer.Channel(0)
        ch.play(sound)
        return True

    def play_sound_with_distance(
        self,
        sound_id: str,
        source_position: Vec2,
        camera_position: Vec2,
        max_distance: float = 500.0,
    ) -> None:
        """Play a cached sound with volume attenuated by distance to camera."""
        if not self._available or not self._config.enabled:
            return

        distance = source_position.distance_to(camera_position)
        if distance >= max_distance:
            return

        volume = 1.0 - (distance / max_distance)

        sound = self._cache.get(sound_id)
        if sound is None:
            return

        final_vol = volume * self._config.sfx_volume * self._config.master_volume
        sound.set_volume(max(0.0, min(1.0, final_vol)))

        ch = mixer.find_channel(True)
        if ch is None:
            ch = mixer.Channel(0)
        ch.play(sound)

    @property
    def config(self) -> SoundConfig:
        return self._config

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def available(self) -> bool:
        return self._available

    def set_master_volume(self, vol: float) -> None:
        self._config.master_volume = max(0.0, min(1.0, vol))

    def set_sfx_volume(self, vol: float) -> None:
        self._config.sfx_volume = max(0.0, min(1.0, vol))

    def toggle(self) -> bool:
        self._config.enabled = not self._config.enabled
        return self._config.enabled

    def _calculate_distance_attenuation(self, distance: float) -> float:
        if distance <= 0:
            return 1.0
        if distance >= self._mixer_config.max_distance:
            return 0.0
        model = self._mixer_config.distance_model
        ref_dist = self._mixer_config.reference_distance
        rolloff = self._mixer_config.rolloff_factor
        max_dist = self._mixer_config.max_distance

        if model == "inverse":
            if distance <= ref_dist:
                return 1.0
            return ref_dist / (ref_dist + rolloff * (distance - ref_dist))
        elif model == "linear":
            return max(0.0, 1.0 - (distance / max_dist))
        elif model == "exponential":
            if distance <= ref_dist:
                return 1.0
            ratio = distance / ref_dist
            return ratio ** (-rolloff)
        else:
            return max(0.0, 1.0 - (distance / max_dist))

    def calculate_stereo_pan(
        self,
        source_pos: Vec2,
        listener_pos: Vec2,
        listener_facing: float = 0.0,
    ) -> tuple[float, float]:
        dx = source_pos.x - listener_pos.x
        dy = source_pos.y - listener_pos.y
        source_angle = np.arctan2(dy, dx)
        relative_angle = source_angle - listener_facing

        while relative_angle > np.pi:
            relative_angle -= 2 * np.pi
        while relative_angle < -np.pi:
            relative_angle += 2 * np.pi

        sep = self._mixer_config.stereo_separation
        cos_a = np.cos(relative_angle)

        left_vol = 1.0 + cos_a * sep * 0.5
        right_vol = 1.0 - cos_a * sep * 0.5

        back_factor = 0.8 if abs(relative_angle) > np.pi / 2 else 1.0
        left_vol *= back_factor
        right_vol *= back_factor

        if self._mixer_config.hrtf_approximation:
            freq_boost = 1.0 + 0.15 * abs(np.sin(relative_angle))
            left_vol *= freq_boost
            right_vol *= freq_boost

        return (
            max(0.0, min(1.0, left_vol)),
            max(0.0, min(1.0, right_vol)),
        )

    def play_3d_sound(
        self,
        sound_type: SoundType,
        source_pos: Vec2,
        listener_pos: Vec2,
        listener_facing: float = 0.0,
        volume: float | None = None,
    ) -> bool:
        if not self._available or not self._config.enabled:
            return False

        distance = source_pos.distance_to(listener_pos)
        if distance >= self._mixer_config.max_distance:
            return False

        attenuated_volume = self._calculate_distance_attenuation(distance)
        if attenuated_volume <= 0.0:
            return False

        left_pan, right_pan = self.calculate_stereo_pan(
            source_pos, listener_pos, listener_facing
        )
        avg_pan = (left_pan + right_pan) / 2.0
        final_volume = attenuated_volume * avg_pan

        if volume is not None:
            final_volume *= volume

        priority = self._get_sound_priority(sound_type)
        return self.play_with_priority(sound_type, final_volume, priority)

    def _get_sound_priority(self, sound_type: SoundType) -> SoundPriority:
        priority_map = {
            SoundType.UI_CLICK: SoundPriority.CRITICAL,
            SoundType.UI_HOVER: SoundPriority.CRITICAL,
            SoundType.UI_COMMAND: SoundPriority.CRITICAL,
            SoundType.UI_SELECT: SoundPriority.CRITICAL,
            SoundType.UI_CANCEL: SoundPriority.CRITICAL,
            SoundType.UI_ERROR: SoundPriority.CRITICAL,
            SoundType.UI_SUCCESS: SoundPriority.CRITICAL,
            SoundType.RIFLE_SHOT: SoundPriority.HIGH,
            SoundType.MG_BURST: SoundPriority.HIGH,
            SoundType.PISTOL_SHOT: SoundPriority.HIGH,
            SoundType.EXPLOSION: SoundPriority.HIGH,
            SoundType.TANK_CANNON: SoundPriority.HIGH,
            SoundType.AT_GUN: SoundPriority.HIGH,
            SoundType.MORTAR: SoundPriority.HIGH,
            SoundType.SMG: SoundPriority.HIGH,
            SoundType.SNIPER: SoundPriority.HIGH,
            SoundType.HIT_CONFIRM: SoundPriority.HIGH,
            SoundType.HIT_CRITICAL: SoundPriority.CRITICAL,
            SoundType.RICOCHET: SoundPriority.MEDIUM,
            SoundType.UNIT_MOVE: SoundPriority.LOW,
            SoundType.UNIT_DEATH: SoundPriority.HIGH,
            SoundType.UNIT_PANIC: SoundPriority.MEDIUM,
            SoundType.UNIT_SUPPRESSED: SoundPriority.MEDIUM,
            SoundType.AMBIENT_BIRD: SoundPriority.BACKGROUND,
            SoundType.AMBIENT_WIND: SoundPriority.BACKGROUND,
            SoundType.FOOTSTEP_GRASS: SoundPriority.LOW,
            SoundType.FOOTSTEP_ROAD: SoundPriority.LOW,
            SoundType.FOOTSTEP_WOOD: SoundPriority.LOW,
        }
        return priority_map.get(sound_type, SoundPriority.MEDIUM)

    def play_with_priority(
        self,
        sound_type: SoundType,
        volume: float | None = None,
        priority: SoundPriority = SoundPriority.MEDIUM,
    ) -> bool:
        active_count = len(self._active_sounds)
        max_sounds = self._mixer_config.max_simultaneous_sounds

        if active_count >= max_sounds and priority != SoundPriority.CRITICAL:
            lowest_priority_channel = self._find_lowest_priority_channel()
            if lowest_priority_channel is not None:
                _, existing_priority = self._active_sounds[lowest_priority_channel]
                if priority.value < existing_priority.value:
                    try:
                        ch = mixer.Channel(lowest_priority_channel)
                        ch.stop()
                        del self._active_sounds[lowest_priority_channel]
                    except Exception as e:
                        logger.warning("Channel stop failed: %s", e)
                else:
                    self._dropped_sound_count += 1
                    return False
            else:
                self._dropped_sound_count += 1
                return False

        result = self.play(sound_type, volume)
        if result:
            ch = mixer.find_channel(False)
            if ch:
                self._active_sounds[ch.get_id()] = (sound_type, priority)
                current_count = len(self._active_sounds)
                if current_count > self._peak_active_count:
                    self._peak_active_count = current_count
        return result

    def _find_lowest_priority_channel(self) -> int | None:
        if not self._active_sounds:
            return None
        lowest_channel = None
        lowest_priority_value = -1
        for channel_id, (_, priority) in self._active_sounds.items():
            if priority.value > lowest_priority_value:
                lowest_priority_value = priority.value
                lowest_channel = channel_id
        return lowest_channel

    @property
    def active_sound_count(self) -> int:
        return len(self._active_sounds)

    @property
    def peak_active_count(self) -> int:
        return self._peak_active_count

    @property
    def dropped_sound_count(self) -> int:
        return self._dropped_sound_count

    def set_category_volume(self, category: str, volume: float) -> None:
        if category in self._category_volumes:
            self._category_volumes[category] = max(0.0, min(1.0, volume))

    def get_category_volume(self, category: str) -> float:
        return self._category_volumes.get(category, 1.0)

    def duck_music(self, duck_volume: float = 0.2, duration_ms: int = 500) -> None:
        if self._music_ducked:
            return
        self._original_music_volume = self._config.music_volume
        target_volume = duck_volume * self._category_volumes["music"]
        steps = max(1, duration_ms // 50)
        step_size = (self._config.music_volume - target_volume) / steps
        for i in range(steps):
            self._config.music_volume -= step_size
        self._config.music_volume = target_volume
        self._music_ducked = True

    def restore_music(self, fade_ms: int = 1000) -> None:
        if not self._music_ducked:
            return
        target_volume = self._original_music_volume
        steps = max(1, fade_ms // 50)
        step_size = (target_volume - self._config.music_volume) / steps
        for i in range(steps):
            self._config.music_volume += step_size
        self._config.music_volume = target_volume
        self._music_ducked = False


class MusicPlayer:
    def __init__(self, sound_system: SoundSystem):
        self._sys = sound_system
        self._playing = False

    def play_ambient(self) -> None:
        if not self._sys._available or not self._sys.config.enabled:
            return

    def stop(self) -> None:
        if not self._sys._available:
            return
        with contextlib.suppress(Exception):
            mixer.music.stop()
        self._playing = False
