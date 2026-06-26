"""Environmental ambient audio system (C12).

Generates procedural environmental sounds for immersive battlefield ambiance.
Supports dynamic weather, time-of-day, location type, and combat intensity.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, ClassVar

logger = logging.getLogger(__name__)

import numpy as np

if TYPE_CHECKING:
    import pygame


class EnvironmentSoundType(Enum):
    """Types of environmental sounds."""

    BIRDS = auto()
    WIND = auto()
    DISTANT_ARTILLERY = auto()
    INSECTS = auto()
    RAIN = auto()
    FOOTSTEPS = auto()
    THUNDER = auto()
    CROWD_CHATTER = auto()
    VEHICLE_AMBIENT = auto()
    FIRE_CRACKLE = auto()
    RADIO_STATIC = auto()


class EnvironmentalSoundGenerator:
    """Generates procedural environmental sounds using numpy waveform synthesis."""

    SAMPLE_RATE: ClassVar[int] = 22050

    @classmethod
    def generate_bird_chirp(cls, variant: int = 0) -> np.ndarray:
        """鸟叫 - 2-4kHz短促正弦波扫频，不同variant不同音调

        Args:
            variant: 0=麻雀(高频短促), 1=乌鸦(低频粗哑), 2=啄木鸟(规律敲击)
        """
        duration = 2.0
        n_samples = int(cls.SAMPLE_RATE * duration)
        np.linspace(0, duration, n_samples, dtype=np.float64)

        if variant == 0:
            freq_start, freq_end = 3000, 4000
            chirp_duration = 0.08
            n_chirps = np.random.randint(8, 15)
            wave = np.zeros(n_samples, dtype=np.float64)

            for _i in range(n_chirps):
                start_sample = int(
                    np.random.uniform(0, duration - chirp_duration) * cls.SAMPLE_RATE
                )
                n_chirp = int(cls.SAMPLE_RATE * chirp_duration)
                t_chirp = np.linspace(0, chirp_duration, n_chirp, dtype=np.float64)
                freq = freq_start + (freq_end - freq_start) * t_chirp / chirp_duration
                phase = 2 * np.pi * np.cumsum(freq) / cls.SAMPLE_RATE
                envelope = np.exp(-t_chirp * 30) * np.sin(np.pi * t_chirp / chirp_duration)
                chirp_wave = np.sin(phase) * envelope * 0.7

                end = min(start_sample + n_chirp, n_samples)
                actual_len = end - start_sample
                wave[start_sample:end] += chirp_wave[:actual_len]

        elif variant == 1:
            freq_base = 800
            caw_duration = 0.3
            n_caws = np.random.randint(3, 6)
            wave = np.zeros(n_samples, dtype=np.float64)

            for _i in range(n_caws):
                start_sample = int(
                    np.random.uniform(0.3, duration - caw_duration) * cls.SAMPLE_RATE
                )
                n_caw = int(cls.SAMPLE_RATE * caw_duration)
                t_caw = np.linspace(0, caw_duration, n_caw, dtype=np.float64)
                envelope = np.exp(-t_caw * 5) * (1.0 + 0.3 * np.sin(2 * np.pi * 15 * t_caw))
                tone = np.sin(2 * np.pi * freq_base * t_caw) * envelope
                noise = np.random.uniform(-0.3, 0.3, n_caw) * envelope
                caw_wave = (tone + noise) * 0.6

                end = min(start_sample + n_caw, n_samples)
                actual_len = end - start_sample
                wave[start_sample:end] += caw_wave[:actual_len]

        else:
            tap_freq = 1200
            tap_duration = 0.05
            pattern_interval = 0.2
            n_taps = int(duration / pattern_interval)
            wave = np.zeros(n_samples, dtype=np.float64)

            for i in range(n_taps):
                start_sample = int(i * pattern_interval * cls.SAMPLE_RATE)
                if start_sample + int(cls.SAMPLE_RATE * tap_duration) > n_samples:
                    break
                n_tap = int(cls.SAMPLE_RATE * tap_duration)
                t_tap = np.linspace(0, tap_duration, n_tap, dtype=np.float64)
                envelope = np.exp(-t_tap * 60)
                tap_wave = np.sin(2 * np.pi * tap_freq * t_tap) * envelope * 0.5

                end = start_sample + n_tap
                wave[start_sample:end] += tap_wave

        return cls._to_int16(wave)

    @classmethod
    def generate_wind_gust(cls, intensity: float = 0.5) -> np.ndarray:
        """风声 - 过滤后的白噪声，intensity控制音量和频率成分

        Args:
            intensity: 0.0-1.0 控制风力和频率成分
        """
        duration = 3.0
        n_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, dtype=np.float64)

        base_noise = np.random.uniform(-1, 1, n_samples).astype(np.float64)

        cutoff_freq = 200 + intensity * 800
        filtered = cls._lowpass_filter(base_noise, cutoff_freq, cls.SAMPLE_RATE)

        gust_period = np.random.uniform(1.5, 3.0)
        gust_envelope = 0.5 + 0.5 * np.sin(2 * np.pi * t / gust_period)
        gust_envelope *= 0.3 + 0.7 * intensity

        random_modulation = 1.0 + 0.3 * np.sin(2 * np.pi * np.random.uniform(0.1, 0.5) * t)
        gust_envelope *= random_modulation

        wave = filtered * gust_envelope * intensity
        return cls._to_int16(wave)

    @classmethod
    def generate_distant_artillery(cls, distance_factor: float = 1.0) -> np.ndarray:
        """远距离炮声 - 低频滚雷声，delayed echo

        Args:
            distance_factor: >1.0更远(更安静，更长延迟)
        """
        duration = 2.0 * distance_factor
        n_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, dtype=np.float64)

        base_freq = 30
        volume = 1.0 / distance_factor

        boom = np.sin(2 * np.pi * base_freq * t)
        sub_boom = np.sin(2 * np.pi * base_freq * 0.5 * t) * 0.6

        attack = 1.0 - np.exp(-t * 20)
        decay = np.exp(-t * (2.0 / distance_factor))
        envelope = attack * decay * volume

        wave = (boom + sub_boom) * envelope

        if distance_factor < 2.0:
            echo_delay = int(cls.SAMPLE_RATE * 0.3 * distance_factor)
            echo_volume = 0.4 / distance_factor
            if echo_delay < n_samples:
                echo = np.zeros(n_samples, dtype=np.float64)
                echo[echo_delay:] = (
                    (boom[:-echo_delay] + sub_boom[:-echo_delay])
                    * np.exp(-np.linspace(0, duration, n_samples - echo_delay) * 3)
                    * echo_volume
                )
                wave += echo

        noise = np.random.uniform(-0.1, 0.1, n_samples) * envelope
        wave += noise

        return cls._to_int16(wave)

    @classmethod
    def generate_rain(cls, intensity: float = 0.7) -> np.ndarray:
        """雨声 - 高频白噪声+偶尔水滴声

        Args:
            intensity: 0.0-1.0 雨量强度
        """
        duration = 3.0
        n_samples = int(cls.SAMPLE_RATE * duration)
        np.linspace(0, duration, n_samples, dtype=np.float64)

        base_noise = np.random.uniform(-1, 1, n_samples).astype(np.float64)
        filtered = cls._highpass_filter(base_noise, 2000, cls.SAMPLE_RATE)

        rain_envelope = 0.5 + 0.5 * intensity
        wave = filtered * rain_envelope * intensity

        n_drops = int(20 * intensity)
        for _ in range(n_drops):
            drop_pos = int(np.random.uniform(0, duration) * cls.SAMPLE_RATE)
            drop_duration = 0.02
            n_drop = int(cls.SAMPLE_RATE * drop_duration)

            if drop_pos + n_drop < n_samples:
                t_drop = np.linspace(0, drop_duration, n_drop, dtype=np.float64)
                drop_envelope = np.exp(-t_drop * 100)
                drop_wave = np.sin(2 * np.pi * 4000 * t_drop) * drop_envelope * 0.8
                wave[drop_pos : drop_pos + n_drop] += drop_wave

        return cls._to_int16(wave)

    @classmethod
    def generate_thunder(cls) -> np.ndarray:
        """雷声 - 超低频脉冲+长衰减"""
        duration = 5.0
        n_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, dtype=np.float64)

        crack_duration = 0.1
        n_crack = int(cls.SAMPLE_RATE * crack_duration)
        t_crack = np.linspace(0, crack_duration, n_crack, dtype=np.float64)

        crack_noise = np.random.uniform(-1, 1, n_crack)
        crack_envelope = np.exp(-t_crack * 30)
        crack = crack_noise * crack_envelope * 1.0

        rumble_freq = 25
        rumble = np.sin(2 * np.pi * rumble_freq * t)
        sub_rumble = np.sin(2 * np.pi * rumble_freq * 0.5 * t) * 0.5

        rumble_envelope = np.exp(-t * 0.8) * 0.7
        rumble_wave = (rumble + sub_rumble) * rumble_envelope

        wave = np.zeros(n_samples, dtype=np.float64)
        wave[:n_crack] += crack
        wave += rumble_wave

        echo_delay = int(cls.SAMPLE_RATE * 0.5)
        if echo_delay < n_samples:
            echo = np.zeros(n_samples, dtype=np.float64)
            echo[echo_delay:] = rumble_wave[:-echo_delay] * 0.4
            wave += echo

        return cls._to_int16(wave)

    @classmethod
    def generate_insect_chirp(cls, insect_type: str = "cricket") -> np.ndarray:
        """昆虫声 - cricket/cicada

        Args:
            insect_type: "cricket"(蟋蟀) 或 "cicada"(蝉)
        """
        duration = 3.0
        n_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, dtype=np.float64)
        wave = np.zeros(n_samples, dtype=np.float64)

        if insect_type == "cricket":
            chirp_freq = 5000
            chirp_duration = 0.03
            interval = 0.5
            n_chirps = int(duration / interval)

            for _i in range(n_chirps):
                pos = int(_i * interval * cls.SAMPLE_RATE)
                n_chirp = int(cls.SAMPLE_RATE * chirp_duration)

                if pos + n_chirp < n_samples:
                    t_chirp = np.linspace(0, chirp_duration, n_chirp, dtype=np.float64)
                    envelope = np.exp(-t_chirp * 80)
                    chirp = np.sin(2 * np.pi * chirp_freq * t_chirp) * envelope * 0.6
                    wave[pos : pos + n_chirp] += chirp

        else:
            base_freq = 4500
            mod_freq = 80
            tone = np.sin(2 * np.pi * base_freq * t)
            modulation = 1.0 + 0.5 * np.sin(2 * np.pi * mod_freq * t)
            envelope = 0.3 + 0.7 * np.abs(np.sin(2 * np.pi * 0.3 * t))
            wave = tone * modulation * envelope * 0.5

        return cls._to_int16(wave)

    @classmethod
    def generate_footstep_ambient(cls, surface: str = "mixed") -> np.ndarray:
        """环境脚步声 - 多人混合脚步

        Args:
            surface: "mixed"/"gravel"/"mud"/"concrete"
        """
        duration = 4.0
        n_samples = int(cls.SAMPLE_RATE * duration)
        np.linspace(0, duration, n_samples, dtype=np.float64)
        wave = np.zeros(n_samples, dtype=np.float64)

        surface_configs = {
            "mixed": {"freq": 1500, "decay": 40, "n_steps": 12},
            "gravel": {"freq": 2500, "decay": 25, "n_steps": 15},
            "mud": {"freq": 600, "decay": 15, "n_steps": 10},
            "concrete": {"freq": 2000, "decay": 60, "n_steps": 14},
        }

        config = surface_configs.get(surface, surface_configs["mixed"])

        for _i in range(config["n_steps"]):
            step_pos = int(np.random.uniform(0.2, duration - 0.1) * cls.SAMPLE_RATE)
            step_duration = 0.05
            n_step = int(cls.SAMPLE_RATE * step_duration)

            if step_pos + n_step < n_samples:
                t_step = np.linspace(0, step_duration, n_step, dtype=np.float64)
                envelope = np.exp(-t_step * config["decay"])
                step_tone = np.sin(2 * np.pi * config["freq"] * t_step) * envelope * 0.4
                step_noise = np.random.uniform(-0.2, 0.2, n_step) * envelope
                step_wave = (step_tone + step_noise) * np.random.uniform(0.5, 1.0)
                wave[step_pos : step_pos + n_step] += step_wave

        return cls._to_int16(wave)

    @classmethod
    def generate_fire_crackle(cls) -> np.ndarray:
        """火焰噼啪声 - 爆裂性噪声+低频隆隆"""
        duration = 3.0
        n_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, dtype=np.float64)

        n_crackles = np.random.randint(15, 25)
        crackle_wave = np.zeros(n_samples, dtype=np.float64)

        for _ in range(n_crackles):
            pos = int(np.random.uniform(0, duration) * cls.SAMPLE_RATE)
            crackle_dur = np.random.uniform(0.01, 0.04)
            n_crackle = int(cls.SAMPLE_RATE * crackle_dur)

            if pos + n_crackle < n_samples:
                t_c = np.linspace(0, crackle_dur, n_crackle, dtype=np.float64)
                envelope = np.exp(-t_c * 150)
                noise = np.random.uniform(-1, 1, n_crackle)
                crackle = noise * envelope * np.random.uniform(0.5, 1.0)
                crackle_wave[pos : pos + n_crackle] += crackle

        rumble_freq = 60
        rumble = np.sin(2 * np.pi * rumble_freq * t) * 0.3
        rumble_envelope = 0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 0.5 * t))
        rumble_wave = rumble * rumble_envelope

        wave = crackle_wave * 0.7 + rumble_wave
        return cls._to_int16(wave)

    @classmethod
    def generate_radio_static(cls) -> np.ndarray:
        """无线电杂音 - 带通滤波噪声+偶尔语音片段"""
        duration = 4.0
        n_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, dtype=np.float64)

        noise = np.random.uniform(-1, 1, n_samples).astype(np.float64)
        bandpassed = cls._bandpass_filter(noise, 300, 3000, cls.SAMPLE_RATE)

        static_envelope = 0.6 + 0.4 * np.sin(2 * np.pi * 2 * t)
        wave = bandpassed * static_envelope * 0.5

        n_interference = np.random.randint(2, 5)
        for _ in range(n_interference):
            int_pos = int(np.random.uniform(0.5, duration - 0.3) * cls.SAMPLE_RATE)
            int_dur = np.random.uniform(0.1, 0.3)
            n_int = int(cls.SAMPLE_RATE * int_dur)

            if int_pos + n_int < n_samples:
                t_int = np.linspace(0, int_dur, n_int, dtype=np.float64)
                am_mod = 1.0 + 0.8 * np.sin(2 * np.pi * np.random.uniform(20, 50) * t_int)
                interference = np.random.uniform(-1, 1, n_int) * am_mod * 0.4
                wave[int_pos : int_pos + n_int] += interference

        return cls._to_int16(wave)

    @classmethod
    def generate_crowd_chatter(cls) -> np.ndarray:
        """人群嘈杂声 - 多层语音频段噪声"""
        duration = 4.0
        n_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, dtype=np.float64)

        wave = np.zeros(n_samples, dtype=np.float64)

        for _ in range(8):
            voice_noise = np.random.uniform(-1, 1, n_samples).astype(np.float64)
            filtered = cls._bandpass_filter(voice_noise, 200, 2800, cls.SAMPLE_RATE)
            wave += filtered * 0.15

        modulation = 0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * t)
        wave *= modulation

        return cls._to_int16(wave)

    @classmethod
    def generate_vehicle_ambient(cls) -> np.ndarray:
        """远处车辆声 - 低频引擎+轮胎噪音"""
        duration = 3.0
        n_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, dtype=np.float64)

        engine_freq = 80
        engine_harmonic = engine_freq * 2
        engine = np.sin(2 * np.pi * engine_freq * t) * 0.4
        harmonic = np.sin(2 * np.pi * engine_harmonic * t) * 0.2

        rpm_modulation = 1.0 + 0.1 * np.sin(2 * np.pi * 0.5 * t)
        engine_envelope = 0.3 * rpm_modulation

        tire_noise = np.random.uniform(-1, 1, n_samples).astype(np.float64)
        tire_filtered = cls._highpass_filter(tire_noise, 500, cls.SAMPLE_RATE) * 0.15

        wave = (engine + harmonic) * engine_envelope + tire_filtered
        return cls._to_int16(wave)

    # ------------------------------------------------------------------
    # Filter helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _lowpass_filter(
        signal: np.ndarray, cutoff: float, sample_rate: int, order: int = 5
    ) -> np.ndarray:
        """Simple lowpass filter using moving average approximation."""
        from scipy.signal import butter, filtfilt

        nyquist = 0.5 * sample_rate
        normal_cutoff = cutoff / nyquist
        b, a = butter(order, normal_cutoff, btype="low", analog=False)
        return filtfilt(b, a, signal)

    @staticmethod
    def _highpass_filter(
        signal: np.ndarray, cutoff: float, sample_rate: int, order: int = 5
    ) -> np.ndarray:
        """Simple highpass filter."""
        from scipy.signal import butter, filtfilt

        nyquist = 0.5 * sample_rate
        normal_cutoff = cutoff / nyquist
        b, a = butter(order, normal_cutoff, btype="high", analog=False)
        return filtfilt(b, a, signal)

    @staticmethod
    def _bandpass_filter(
        signal: np.ndarray, lowcut: float, highcut: float, sample_rate: int, order: int = 5
    ) -> np.ndarray:
        """Bandpass filter."""
        from scipy.signal import butter, filtfilt

        nyquist = 0.5 * sample_rate
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = butter(order, [low, high], btype="band", analog=False)
        return filtfilt(b, a, signal)

    # ------------------------------------------------------------------
    # Common helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_int16(wave: np.ndarray) -> np.ndarray:
        """Normalise a float64 waveform to int16 range."""
        peak = np.max(np.abs(wave))
        if peak > 0:
            wave = wave / peak
        return (wave * 32767).astype(np.int16)


class EnvironmentalAudioSystem:
    """Environmental ambient audio system with caching and loop support.

    Background sounds: birds/wind/artillery/insects/rain/thunder/crowd/vehicles/fire/radio
    Context-sensitive: weather, time of day, location type, combat intensity.
    """

    def __init__(self):
        self._mixer: Any | None = None
        self._sound_cache: dict[EnvironmentSoundType, pygame.mixer.Sound] = {}
        self._loop_channels: dict[EnvironmentSoundType, pygame.mixer.Channel] = {}
        self._active_sounds: dict[EnvironmentSoundType, bool] = {
            EnvironmentSoundType.BIRDS: True,
            EnvironmentSoundType.WIND: False,
            EnvironmentSoundType.DISTANT_ARTILLERY: False,
            EnvironmentSoundType.INSECTS: True,
            EnvironmentSoundType.RAIN: False,
            EnvironmentSoundType.FOOTSTEPS: False,
            EnvironmentSoundType.THUNDER: False,
            EnvironmentSoundType.CROWD_CHATTER: False,
            EnvironmentSoundType.VEHICLE_AMBIENT: False,
            EnvironmentSoundType.FIRE_CRACKLE: False,
            EnvironmentSoundType.RADIO_STATIC: False,
        }
        self._volume: float = 0.3
        self._time_of_day: int = 12
        self._location_type: str = "open_field"
        self._combat_intensity: float = 0.0
        self._is_raining: bool = False
        self._initialized: bool = False

    def initialize(self, mixer: Any) -> None:
        """Initialize with pygame.mixer instance.

        Args:
            mixer: pygame.mixer module or compatible interface
        """
        self._mixer = mixer
        if not mixer.get_init():
            mixer.init(
                frequency=EnvironmentalSoundGenerator.SAMPLE_RATE, size=-16, channels=1, buffer=512
            )
        self._initialized = True
        logger.info("EnvironmentalAudioSystem initialized")

    def _generate_sound(self, sound_type: EnvironmentSoundType) -> pygame.mixer.Sound | None:
        """Generate and cache a sound.

        Args:
            sound_type: Type of environmental sound to generate
        """
        if sound_type in self._sound_cache:
            return self._sound_cache[sound_type]

        generators = {
            EnvironmentSoundType.BIRDS: lambda: EnvironmentalSoundGenerator.generate_bird_chirp(
                variant=np.random.randint(0, 3)
            ),
            EnvironmentSoundType.WIND: lambda: EnvironmentalSoundGenerator.generate_wind_gust(
                intensity=self._get_wind_intensity()
            ),
            EnvironmentSoundType.DISTANT_ARTILLERY: lambda: (
                EnvironmentalSoundGenerator.generate_distant_artillery(
                    distance_factor=max(0.5, 2.0 - self._combat_intensity)
                )
            ),
            EnvironmentSoundType.INSECTS: lambda: EnvironmentalSoundGenerator.generate_insect_chirp(
                insect_type="cricket" if np.random.random() > 0.5 else "cicada"
            ),
            EnvironmentSoundType.RAIN: lambda: EnvironmentalSoundGenerator.generate_rain(
                intensity=0.8
            ),
            EnvironmentSoundType.FOOTSTEPS: lambda: (
                EnvironmentalSoundGenerator.generate_footstep_ambient(surface="mixed")
            ),
            EnvironmentSoundType.THUNDER: lambda: EnvironmentalSoundGenerator.generate_thunder(),
            EnvironmentSoundType.CROWD_CHATTER: lambda: (
                EnvironmentalSoundGenerator.generate_crowd_chatter()
            ),
            EnvironmentSoundType.VEHICLE_AMBIENT: lambda: (
                EnvironmentalSoundGenerator.generate_vehicle_ambient()
            ),
            EnvironmentSoundType.FIRE_CRACKLE: lambda: (
                EnvironmentalSoundGenerator.generate_fire_crackle()
            ),
            EnvironmentSoundType.RADIO_STATIC: lambda: (
                EnvironmentalSoundGenerator.generate_radio_static()
            ),
        }

        generator = generators.get(sound_type)
        if not generator:
            logger.warning(f"No generator for sound type: {sound_type}")
            return None

        if self._mixer is None:
            return None
        raw_audio = generator()
        sound = self._mixer.Sound(array=raw_audio)
        sound.set_volume(self._volume)
        self._sound_cache[sound_type] = sound
        return sound

    def start_ambient_loop(self, sound_type: EnvironmentSoundType) -> bool:
        """Start looping an ambient sound.

        Args:
            sound_type: Type of sound to loop

        Returns:
            True if successfully started, False otherwise
        """
        if not self._initialized:
            logger.warning("AudioSystem not initialized")
            return False

        if not self._should_play_sound(sound_type):
            return False

        sound = self._generate_sound(sound_type)
        if not sound:
            return False

        channel = sound.play(loops=-1)
        if channel:
            self._loop_channels[sound_type] = channel
            self._active_sounds[sound_type] = True
            logger.debug(f"Started ambient loop: {sound_type.name}")
            return True
        return False

    def stop_ambient_loop(self, sound_type: EnvironmentSoundType) -> None:
        """Stop a looping ambient sound.

        Args:
            sound_type: Type of sound to stop
        """
        if sound_type in self._loop_channels:
            channel = self._loop_channels[sound_type]
            channel.stop()
            del self._loop_channels[sound_type]

        self._active_sounds[sound_type] = False
        logger.debug(f"Stopped ambient loop: {sound_type.name}")

    def update(self, dt: float) -> None:
        """Update audio state each frame.

        Args:
            dt: Delta time since last update in seconds
        """
        if not self._initialized:
            return

        self._update_dynamic_sounds()

    def set_time_of_day(self, hour: int) -> None:
        """Set time of day (affects bird/insect activity).

        Args:
            hour: 0-23 hour of day
        """
        self._time_of_day = max(0, min(23, hour))
        self._adjust_activity_by_time()

    def set_location_type(self, location: str) -> None:
        """Set location type (affects available ambient sounds).

        Args:
            location: "village"/"city"/"forest"/"open_field"
        """
        valid_locations = ["village", "city", "forest", "open_field"]
        if location in valid_locations:
            self._location_type = location
            self._adjust_activity_by_location()

    def set_weather_rain(self, raining: bool) -> None:
        """Enable/disable rain sounds and adjust related effects.

        Args:
            raining: Whether it is currently raining
        """
        self._is_raining = raining
        self._active_sounds[EnvironmentSoundType.RAIN] = raining

        if raining:
            self.stop_ambient_loop(EnvironmentSoundType.BIRDS)
            self.stop_ambient_loop(EnvironmentSoundType.INSECTS)
            self.start_ambient_loop(EnvironmentSoundType.THUNDER)
        else:
            self.stop_ambient_loop(EnvironmentSoundType.RAIN)
            self.stop_ambient_loop(EnvironmentSoundType.THUNDER)
            self._adjust_activity_by_time()

    def set_combat_intensity(self, intensity: float) -> None:
        """Adjust ambient sounds based on combat intensity.

        Args:
            intensity: 0.0-1.0 combat intensity level
        """
        self._combat_intensity = max(0.0, min(1.0, intensity))

        if self._combat_intensity > 0.3:
            if not self._active_sounds[EnvironmentSoundType.DISTANT_ARTILLERY]:
                self.start_ambient_loop(EnvironmentSoundType.DISTANT_ARTILLERY)
            if self._combat_intensity > 0.6:
                self.start_ambient_loop(EnvironmentSoundType.FIRE_CRACKLE)
                self.start_ambient_loop(EnvironmentSoundType.RADIO_STATIC)
        else:
            self.stop_ambient_loop(EnvironmentSoundType.DISTANT_ARTILLERY)
            self.stop_ambient_loop(EnvironmentSoundType.FIRE_CRACKLE)
            self.stop_ambient_loop(EnvironmentSoundType.RADIO_STATIC)

        if self._combat_intensity < 0.3 and not self._is_raining:
            self._adjust_activity_by_time()

    def is_playing(self, sound_type: EnvironmentSoundType) -> bool:
        """Check if sound type is active.

        Args:
            sound_type: Type to check

        Returns:
            True if sound is playing
        """
        return self._active_sounds.get(sound_type, False)

    def set_master_volume(self, volume: float) -> None:
        """Set master volume for all environmental sounds.

        Args:
            volume: 0.0-1.0 volume level
        """
        self._volume = max(0.0, min(1.0, volume))
        for sound in self._sound_cache.values():
            sound.set_volume(self._volume)

    def stop_all(self) -> None:
        """Stop all ambient loops."""
        for sound_type in list(self._loop_channels.keys()):
            self.stop_ambient_loop(sound_type)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _should_play_sound(self, sound_type: EnvironmentSoundType) -> bool:
        """Determine if a sound should play based on current context."""
        if sound_type == EnvironmentSoundType.BIRDS:
            return (
                6 <= self._time_of_day <= 19
                and not self._is_raining
                and self._combat_intensity < 0.3
            )
        elif sound_type == EnvironmentSoundType.INSECTS:
            return (
                self._location_type in ["forest", "open_field"]
                and 5 <= self._time_of_day <= 21
                and not self._is_raining
            )
        elif sound_type == EnvironmentSoundType.CROWD_CHATTER:
            return self._location_type in ["village", "city"]
        elif sound_type == EnvironmentSoundType.VEHICLE_AMBIENT:
            return self._location_type in ["village", "city"] and self._combat_intensity < 0.5
        return True

    def _get_wind_intensity(self) -> float:
        """Get current wind intensity based on conditions."""
        base_wind = 0.3
        if self._is_raining:
            base_wind += 0.3
        if self._location_type == "open_field":
            base_wind += 0.2
        return min(1.0, base_wind)

    def _update_dynamic_sounds(self) -> None:
        """Update which sounds should be playing based on current state."""
        for sound_type in EnvironmentSoundType:
            should_play = self._should_play_sound(sound_type)
            is_playing = sound_type in self._loop_channels

            if should_play and not is_playing:
                if self._active_sounds.get(sound_type, False):
                    self.start_ambient_loop(sound_type)
            elif not should_play and is_playing:
                self.stop_ambient_loop(sound_type)

    def _adjust_activity_by_time(self) -> None:
        """Adjust bird/insect activity based on time of day."""
        is_daytime = 6 <= self._time_of_day <= 19

        if is_daytime and not self._is_raining:
            if self._location_type in ["forest", "open_field"]:
                self._active_sounds[EnvironmentSoundType.BIRDS] = True
                self._active_sounds[EnvironmentSoundType.INSECTS] = True
            elif self._combat_intensity < 0.3:
                self._active_sounds[EnvironmentSoundType.BIRDS] = True
        else:
            self._active_sounds[EnvironmentSoundType.BIRDS] = False
            self._active_sounds[EnvironmentSoundType.INSECTS] = False

    def _adjust_activity_by_location(self) -> None:
        """Adjust ambient sounds based on location type."""
        location_sounds = {
            "village": [EnvironmentSoundType.CROWD_CHATTER, EnvironmentSoundType.VEHICLE_AMBIENT],
            "city": [EnvironmentSoundType.CROWD_CHATTER, EnvironmentSoundType.VEHICLE_AMBIENT],
            "forest": [
                EnvironmentSoundType.BIRDS,
                EnvironmentSoundType.INSECTS,
                EnvironmentSoundType.WIND,
            ],
            "open_field": [EnvironmentSoundType.WIND, EnvironmentSoundType.BIRDS],
        }

        for loc_type, sounds in location_sounds.items():
            if loc_type == self._location_type:
                for sound in sounds:
                    if self._should_play_sound(sound):
                        self._active_sounds[sound] = True
            else:
                for sound in sounds:
                    if sound not in location_sounds.get(self._location_type, []):
                        self._active_sounds[sound] = False
