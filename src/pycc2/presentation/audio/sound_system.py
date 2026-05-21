from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

import numpy as np
from pygame import mixer

if TYPE_CHECKING:
    pass


class SoundType(Enum):
    UI_CLICK = auto()
    UI_HOVER = auto()
    UI_COMMAND = auto()
    UI_SELECT = auto()
    UI_CANCEL = auto()
    UI_ERROR = auto()
    UI_SUCCESS = auto()

    RIFLE_SHOT = auto()
    MG_BURST = auto()
    PISTOL_SHOT = auto()
    EXPLOSION = auto()
    HIT_CONFIRM = auto()
    HIT_CRITICAL = auto()
    RICOCHET = auto()

    UNIT_MOVE = auto()
    UNIT_DEATH = auto()
    UNIT_PANIC = auto()
    UNIT_SUPPRESSED = auto()

    AMBIENT_BIRD = auto()
    AMBIENT_WIND = auto()
    FOOTSTEP_GRASS = auto()
    FOOTSTEP_ROAD = auto()
    FOOTSTEP_WOOD = auto()


@dataclass(slots=True)
class SoundConfig:
    master_volume: float = 0.7
    sfx_volume: float = 1.0
    music_volume: float = 0.5
    enabled: bool = True
    sample_rate: int = 22050


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


class SoundSystem:
    def __init__(self, config: SoundConfig | None = None):
        self._config = config or SoundConfig()
        self._cache: dict[str, mixer.Sound] = {}
        self._initialized = False
        self._channel_count = 8

    def initialize(self) -> None:
        if self._initialized:
            return
        try:
            mixer.init(
                frequency=ProceduralSoundGenerator.SAMPLE_RATE, size=-16, channels=1, buffer=512
            )
            self._initialized = True
            self._pregenerate_common_sounds()
        except Exception as e:
            print(f"[Audio] Warning: Could not initialize audio: {e}")
            self._config.enabled = False

    def shutdown(self) -> None:
        if self._initialized:
            mixer.quit()
            self._initialized = False
            self._cache.clear()

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
        ]
        for sound_type, generator in common:
            raw = generator()
            sound = mixer.Sound(array=raw)
            sound.set_volume(self._config.sfx_volume)
            self._cache[sound_type.name] = sound

    def play(self, sound_type: SoundType, volume: float | None = None) -> bool:
        if not self._config.enabled or not self._initialized:
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
            }
            gen = generators.get(sound_type)
            if gen:
                raw = gen()
                sound = mixer.Sound(array=raw)
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

    def play_ui_click(self) -> None:
        self.play(SoundType.UI_CLICK)

    def play_ui_command(self) -> None:
        self.play(SoundType.UI_COMMAND if hasattr(SoundType, 'UI_COMMAND') else SoundType.UI_CLICK)

    def play_ui_hover(self) -> None:
        self.play(SoundType.UI_HOVER)

    def play_shot(self, weapon_type: str = "rifle") -> None:
        if weapon_type == "mg":
            self.play(SoundType.MG_BURST)
        elif weapon_type == "pistol":
            self.play(SoundType.PISTOL_SHOT)
        else:
            self.play(SoundType.RIFLE_SHOT)

    def play_hit(self, is_critical: bool = False) -> None:
        self.play(SoundType.HIT_CRITICAL if is_critical else SoundType.HIT_CONFIRM)

    def play_explosion(self) -> None:
        self.play(SoundType.EXPLOSION)

    def play_death(self) -> None:
        self.play(SoundType.UNIT_DEATH)

    def play_footstep(self, terrain: str = "grass") -> None:
        mapping = {
            "grass": SoundType.FOOTSTEP_GRASS,
            "road": SoundType.FOOTSTEP_ROAD,
            "wood": SoundType.FOOTSTEP_WOOD,
        }
        st = mapping.get(terrain, SoundType.FOOTSTEP_GRASS)
        self.play(st)

    @property
    def config(self) -> SoundConfig:
        return self._config

    @property
    def initialized(self) -> bool:
        return self._initialized

    def set_master_volume(self, vol: float) -> None:
        self._config.master_volume = max(0.0, min(1.0, vol))

    def set_sfx_volume(self, vol: float) -> None:
        self._config.sfx_volume = max(0.0, min(1.0, vol))

    def toggle(self) -> bool:
        self._config.enabled = not self._config.enabled
        return self._config.enabled


class MusicPlayer:
    def __init__(self, sound_system: SoundSystem):
        self._sys = sound_system
        self._playing = False

    def play_ambient(self) -> None:
        if not self._sys.config.enabled:
            return

    def stop(self) -> None:
        mixer.music.stop()
        self._playing = False
