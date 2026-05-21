"""Weapon-differentiated sound generation system for PyCC2.

Generates distinct procedural sounds for each weapon type using numpy
waveform synthesis. No external sound files are needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import numpy as np


SAMPLE_RATE: int = 44100


@dataclass(slots=True)
class WeaponSoundProfile:
    """Configuration profile that defines how a weapon's sound is synthesized."""

    weapon_id: str
    sound_type: str
    base_frequency: float
    duration: float
    decay_rate: float
    noise_ratio: float
    burst_count: int


WEAPON_SOUND_PROFILES: dict[str, WeaponSoundProfile] = {
    "MG42": WeaponSoundProfile(
        weapon_id="MG42",
        sound_type="mg_heavy",
        base_frequency=200,
        duration=0.5,
        decay_rate=8.0,
        noise_ratio=0.7,
        burst_count=5,
    ),
    "MG34": WeaponSoundProfile(
        weapon_id="MG34",
        sound_type="mg_heavy",
        base_frequency=180,
        duration=0.4,
        decay_rate=7.0,
        noise_ratio=0.65,
        burst_count=4,
    ),
    "BREN": WeaponSoundProfile(
        weapon_id="BREN",
        sound_type="mg_light",
        base_frequency=300,
        duration=0.3,
        decay_rate=10.0,
        noise_ratio=0.5,
        burst_count=3,
    ),
    "Lee-Enfield": WeaponSoundProfile(
        weapon_id="Lee-Enfield",
        sound_type="rifle",
        base_frequency=400,
        duration=0.15,
        decay_rate=15.0,
        noise_ratio=0.3,
        burst_count=1,
    ),
    "Kar98k": WeaponSoundProfile(
        weapon_id="Kar98k",
        sound_type="rifle",
        base_frequency=380,
        duration=0.15,
        decay_rate=14.0,
        noise_ratio=0.3,
        burst_count=1,
    ),
    "M1 Garand": WeaponSoundProfile(
        weapon_id="M1 Garand",
        sound_type="rifle",
        base_frequency=420,
        duration=0.12,
        decay_rate=16.0,
        noise_ratio=0.25,
        burst_count=1,
    ),
    "STEN": WeaponSoundProfile(
        weapon_id="STEN",
        sound_type="smg",
        base_frequency=350,
        duration=0.08,
        decay_rate=20.0,
        noise_ratio=0.4,
        burst_count=1,
    ),
    "MP40": WeaponSoundProfile(
        weapon_id="MP40",
        sound_type="smg",
        base_frequency=320,
        duration=0.08,
        decay_rate=18.0,
        noise_ratio=0.35,
        burst_count=1,
    ),
    "PIAT": WeaponSoundProfile(
        weapon_id="PIAT",
        sound_type="at_weapon",
        base_frequency=100,
        duration=0.3,
        decay_rate=5.0,
        noise_ratio=0.6,
        burst_count=1,
    ),
    "Pak 40": WeaponSoundProfile(
        weapon_id="Pak 40",
        sound_type="tank_gun",
        base_frequency=60,
        duration=0.5,
        decay_rate=3.0,
        noise_ratio=0.7,
        burst_count=1,
    ),
    "Mortar": WeaponSoundProfile(
        weapon_id="Mortar",
        sound_type="mortar",
        base_frequency=50,
        duration=0.8,
        decay_rate=2.0,
        noise_ratio=0.5,
        burst_count=1,
    ),
    "Flammenwerfer": WeaponSoundProfile(
        weapon_id="Flammenwerfer",
        sound_type="flamethrower",
        base_frequency=150,
        duration=1.0,
        decay_rate=1.5,
        noise_ratio=0.8,
        burst_count=1,
    ),
}

# Default profile for weapons not in the dictionary
_DEFAULT_PROFILE = WeaponSoundProfile(
    weapon_id="unknown",
    sound_type="rifle",
    base_frequency=400,
    duration=0.15,
    decay_rate=15.0,
    noise_ratio=0.3,
    burst_count=1,
)


class WeaponSoundGenerator:
    """Generates distinct procedural sounds for different weapon types."""

    SAMPLE_RATE: ClassVar[int] = SAMPLE_RATE

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def generate_weapon_sound(cls, weapon_profile: WeaponSoundProfile) -> np.ndarray:
        """Dispatch to the appropriate generator based on *sound_type*."""
        dispatch = {
            "rifle": cls._generate_rifle_sound,
            "mg_heavy": cls._generate_mg_sound,
            "mg_light": cls._generate_mg_sound,
            "smg": cls._generate_smg_sound,
            "sniper": cls._generate_sniper_sound,
            "at_weapon": cls._generate_at_weapon_sound,
            "mortar": cls._generate_mortar_sound,
            "tank_gun": cls._generate_tank_gun_sound,
            "flamethrower": cls._generate_flamethrower_sound,
            "pistol": cls._generate_pistol_sound,
        }
        generator = dispatch.get(weapon_profile.sound_type, cls._generate_rifle_sound)
        return generator(weapon_profile)

    @classmethod
    def play_weapon_sound(cls, weapon_id: str, volume: float = 0.5) -> None:
        """Generate and play a weapon sound via pygame.mixer if available."""
        profile = WEAPON_SOUND_PROFILES.get(weapon_id, _DEFAULT_PROFILE)
        raw = cls.generate_weapon_sound(profile)
        scaled = cls._apply_volume(raw, volume)

        try:
            from pygame import mixer

            if not mixer.get_init():
                mixer.init(frequency=cls.SAMPLE_RATE, size=-16, channels=1, buffer=512)
            sound = mixer.Sound(array=scaled)
            sound.play()
        except Exception:
            pass  # pygame unavailable – sound was generated but not played

    # ------------------------------------------------------------------
    # Weapon-specific generators
    # ------------------------------------------------------------------

    @classmethod
    def _generate_rifle_sound(cls, weapon_profile: WeaponSoundProfile) -> np.ndarray:
        """Short, sharp crack – high frequency pulse + fast decay."""
        n_samples = int(cls.SAMPLE_RATE * weapon_profile.duration)
        t = np.linspace(0, weapon_profile.duration, n_samples, dtype=np.float64)

        envelope = np.exp(-t * weapon_profile.decay_rate)

        tone = np.sin(2 * np.pi * weapon_profile.base_frequency * t) * envelope
        noise = np.random.uniform(-1, 1, n_samples) * envelope

        wave = (1.0 - weapon_profile.noise_ratio) * tone + weapon_profile.noise_ratio * noise
        return cls._to_int16(wave)

    @classmethod
    def _generate_mg_sound(cls, weapon_profile: WeaponSoundProfile) -> np.ndarray:
        """Rapid bursts – sawtooth + high freq noise for MG42, very distinctive."""
        burst_duration = weapon_profile.duration / weapon_profile.burst_count
        n_per_burst = int(cls.SAMPLE_RATE * burst_duration)
        gap_samples = int(cls.SAMPLE_RATE * burst_duration * 0.15)

        bursts: list[np.ndarray] = []
        for i in range(weapon_profile.burst_count):
            t = np.linspace(0, burst_duration, n_per_burst, dtype=np.float64)
            decay = 1.0 - (i / weapon_profile.burst_count) * 0.3
            envelope = np.exp(-t * weapon_profile.decay_rate) * decay

            # Sawtooth component for the distinctive MG sound
            sawtooth = 2.0 * (weapon_profile.base_frequency * t % 1.0) - 1.0
            tone = sawtooth * envelope

            # High-frequency noise component
            hf_noise = np.random.uniform(-1, 1, n_per_burst) * envelope

            wave = (1.0 - weapon_profile.noise_ratio) * tone + weapon_profile.noise_ratio * hf_noise
            burst = cls._to_int16(wave)

            bursts.append(burst)
            if i < weapon_profile.burst_count - 1:
                bursts.append(np.zeros(gap_samples, dtype=np.int16))

        return np.concatenate(bursts)

    @classmethod
    def _generate_smg_sound(cls, weapon_profile: WeaponSoundProfile) -> np.ndarray:
        """Rapid popping – shorter than rifle, faster repeat."""
        n_samples = int(cls.SAMPLE_RATE * weapon_profile.duration)
        t = np.linspace(0, weapon_profile.duration, n_samples, dtype=np.float64)

        envelope = np.exp(-t * weapon_profile.decay_rate)

        tone = np.sin(2 * np.pi * weapon_profile.base_frequency * t) * envelope
        noise = np.random.uniform(-1, 1, n_samples) * envelope

        # Add a short high-frequency click at the start
        click_len = min(int(cls.SAMPLE_RATE * 0.005), n_samples)
        click = np.zeros(n_samples, dtype=np.float64)
        click[:click_len] = np.sin(2 * np.pi * 2000 * t[:click_len]) * np.exp(
            -t[:click_len] * 80
        )

        wave = (
            (1.0 - weapon_profile.noise_ratio) * tone
            + weapon_profile.noise_ratio * noise
            + click * 0.3
        )
        return cls._to_int16(wave)

    @classmethod
    def _generate_sniper_sound(cls, weapon_profile: WeaponSoundProfile) -> np.ndarray:
        """Loud, echoing crack – longer decay, reverb."""
        n_samples = int(cls.SAMPLE_RATE * weapon_profile.duration)
        t = np.linspace(0, weapon_profile.duration, n_samples, dtype=np.float64)

        envelope = np.exp(-t * weapon_profile.decay_rate)

        tone = np.sin(2 * np.pi * weapon_profile.base_frequency * t) * envelope
        noise = np.random.uniform(-1, 1, n_samples) * envelope

        # Simulate reverb with delayed, attenuated copies
        reverb_delay = int(cls.SAMPLE_RATE * 0.05)
        reverb = np.zeros(n_samples, dtype=np.float64)
        for d, a in [(reverb_delay, 0.4), (reverb_delay * 2, 0.2), (reverb_delay * 3, 0.1)]:
            if d < n_samples:
                shifted = np.zeros(n_samples, dtype=np.float64)
                shifted[d:] = envelope[:-d] * a
                reverb += shifted

        wave = (1.0 - weapon_profile.noise_ratio) * tone + weapon_profile.noise_ratio * noise + reverb * 0.3
        return cls._to_int16(wave)

    @classmethod
    def _generate_at_weapon_sound(cls, weapon_profile: WeaponSoundProfile) -> np.ndarray:
        """Heavy thump + whoosh – low freq + noise."""
        n_samples = int(cls.SAMPLE_RATE * weapon_profile.duration)
        t = np.linspace(0, weapon_profile.duration, n_samples, dtype=np.float64)

        envelope = np.exp(-t * weapon_profile.decay_rate)

        # Low-frequency thump
        thump = np.sin(2 * np.pi * weapon_profile.base_frequency * t) * envelope

        # Whoosh: filtered noise that rises then falls
        whoosh_env = np.sin(np.pi * t / weapon_profile.duration) * np.exp(-t * weapon_profile.decay_rate * 0.5)
        whoosh = np.random.uniform(-1, 1, n_samples) * whoosh_env

        wave = (1.0 - weapon_profile.noise_ratio) * thump + weapon_profile.noise_ratio * whoosh
        return cls._to_int16(wave)

    @classmethod
    def _generate_mortar_sound(cls, weapon_profile: WeaponSoundProfile) -> np.ndarray:
        """Low boom + delayed echo – very low freq + reverb."""
        n_samples = int(cls.SAMPLE_RATE * weapon_profile.duration)
        t = np.linspace(0, weapon_profile.duration, n_samples, dtype=np.float64)

        envelope = np.exp(-t * weapon_profile.decay_rate)

        # Very low frequency boom
        boom = np.sin(2 * np.pi * weapon_profile.base_frequency * t) * envelope
        # Add a sub-harmonic for extra depth
        sub = np.sin(2 * np.pi * weapon_profile.base_frequency * 0.5 * t) * envelope * 0.5

        noise = np.random.uniform(-1, 1, n_samples) * envelope

        # Delayed echo
        echo_delay = int(cls.SAMPLE_RATE * 0.15)
        echo = np.zeros(n_samples, dtype=np.float64)
        if echo_delay < n_samples:
            echo[echo_delay:] = envelope[:-echo_delay] * 0.3

        wave = (
            (1.0 - weapon_profile.noise_ratio) * (boom + sub)
            + weapon_profile.noise_ratio * noise
            + echo
        )
        return cls._to_int16(wave)

    @classmethod
    def _generate_tank_gun_sound(cls, weapon_profile: WeaponSoundProfile) -> np.ndarray:
        """Heavy boom – very low freq + long decay."""
        n_samples = int(cls.SAMPLE_RATE * weapon_profile.duration)
        t = np.linspace(0, weapon_profile.duration, n_samples, dtype=np.float64)

        envelope = np.exp(-t * weapon_profile.decay_rate)

        # Very low frequency
        boom = np.sin(2 * np.pi * weapon_profile.base_frequency * t) * envelope
        # Sub-harmonic for chest-thumping feel
        sub = np.sin(2 * np.pi * weapon_profile.base_frequency * 0.5 * t) * envelope * 0.6

        noise = np.random.uniform(-1, 1, n_samples) * envelope

        wave = (1.0 - weapon_profile.noise_ratio) * (boom + sub) + weapon_profile.noise_ratio * noise
        return cls._to_int16(wave)

    @classmethod
    def _generate_flamethrower_sound(cls, weapon_profile: WeaponSoundProfile) -> np.ndarray:
        """Hissing roar – noise + low freq rumble."""
        n_samples = int(cls.SAMPLE_RATE * weapon_profile.duration)
        t = np.linspace(0, weapon_profile.duration, n_samples, dtype=np.float64)

        # Slow attack, slow decay envelope
        attack = 1.0 - np.exp(-t * 20)
        decay = np.exp(-t * weapon_profile.decay_rate)
        envelope = attack * decay

        # Low freq rumble
        rumble = np.sin(2 * np.pi * weapon_profile.base_frequency * t) * envelope

        # Hissing noise
        noise = np.random.uniform(-1, 1, n_samples) * envelope

        wave = (1.0 - weapon_profile.noise_ratio) * rumble + weapon_profile.noise_ratio * noise
        return cls._to_int16(wave)

    @classmethod
    def _generate_pistol_sound(cls, weapon_profile: WeaponSoundProfile) -> np.ndarray:
        """Short pop – brief pulse."""
        n_samples = int(cls.SAMPLE_RATE * weapon_profile.duration)
        t = np.linspace(0, weapon_profile.duration, n_samples, dtype=np.float64)

        envelope = np.exp(-t * weapon_profile.decay_rate)

        tone = np.sin(2 * np.pi * weapon_profile.base_frequency * t) * envelope
        noise = np.random.uniform(-1, 1, n_samples) * envelope

        wave = (1.0 - weapon_profile.noise_ratio) * tone + weapon_profile.noise_ratio * noise
        return cls._to_int16(wave)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_int16(wave: np.ndarray) -> np.ndarray:
        """Normalise a float64 waveform to int16 range."""
        peak = np.max(np.abs(wave))
        if peak > 0:
            wave = wave / peak
        return (wave * 32767).astype(np.int16)

    @staticmethod
    def _apply_volume(raw: np.ndarray, volume: float) -> np.ndarray:
        """Scale an int16 array by *volume* (0.0 – 1.0)."""
        volume = max(0.0, min(1.0, volume))
        return (raw.astype(np.float64) * volume).astype(np.int16)
