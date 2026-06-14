"""Background music and ambient sound system for PyCC2.

Generates procedural music and ambient sounds using numpy waveform synthesis.
No external audio files are needed.
"""
from __future__ import annotations

from enum import Enum, auto
from typing import ClassVar

import numpy as np

SAMPLE_RATE: int = 44100


class MusicMood(Enum):
    """Musical moods for different game states."""

    MENU = auto()
    BATTLE_LIGHT = auto()
    BATTLE_INTENSE = auto()
    VICTORY = auto()
    DEFEAT = auto()
    AMBIENT = auto()


# Musical note frequencies (Hz) for melody generation
_NOTE_FREQS: dict[str, float] = {
    "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61,
    "G3": 196.00, "A3": 220.00, "B3": 246.94,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23,
    "G4": 392.00, "A4": 440.00, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "E5": 659.25,
}

# Chord progressions (root notes per bar) for each mood
_CHORD_PROGRESSIONS: dict[MusicMood, list[list[str]]] = {
    MusicMood.MENU: [["C4", "E4", "G4"], ["F4", "A4", "C5"], ["G4", "B4", "D5"], ["C4", "E4", "G4"]],
    MusicMood.BATTLE_LIGHT: [["A3", "C4", "E4"], ["F3", "A3", "C4"], ["D3", "F3", "A3"], ["E3", "G3", "B3"]],
    MusicMood.BATTLE_INTENSE: [["A3", "C4", "E4"], ["B3", "D4", "F4"], ["C4", "E4", "G4"], ["A3", "C4", "E4"]],
    MusicMood.VICTORY: [["C4", "E4", "G4"], ["F4", "A4", "C5"], ["G4", "B4", "D5"], ["C4", "E4", "G4"]],
    MusicMood.DEFEAT: [["A3", "C4", "E4"], ["F3", "A3", "C4"], ["D3", "F3", "A3"], ["A3", "C4", "E4"]],
}

# BPM and parameters per mood
_MOOD_PARAMS: dict[MusicMood, dict] = {
    MusicMood.MENU: {"bpm": 100, "key": "major"},
    MusicMood.BATTLE_LIGHT: {"bpm": 120, "key": "minor"},
    MusicMood.BATTLE_INTENSE: {"bpm": 140, "key": "dissonant"},
    MusicMood.VICTORY: {"bpm": 110, "key": "major"},
    MusicMood.DEFEAT: {"bpm": 60, "key": "minor"},
    MusicMood.AMBIENT: {"bpm": 0, "key": "none"},
}


class BGMGenerator:
    """Generates procedural background music for different game moods."""

    SAMPLE_RATE: ClassVar[int] = SAMPLE_RATE

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def generate_mood_music(cls, mood: MusicMood, duration: float = 30.0) -> np.ndarray:
        """Generate background music for a given mood.

        Parameters
        ----------
        mood:
            The musical mood to generate.
        duration:
            Length of the generated music in seconds.

        Returns
        -------
        np.ndarray
            int16 mono waveform at 44100 Hz.
        """
        if mood == MusicMood.AMBIENT:
            return AmbientSoundGenerator.generate_wind(intensity=0.3, duration=duration)

        n_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, dtype=np.float64)

        params = _MOOD_PARAMS[mood]
        bpm = params["bpm"]
        beat_duration = 60.0 / bpm
        beats_total = int(duration / beat_duration)

        wave = np.zeros(n_samples, dtype=np.float64)

        # Bass line
        wave += cls._generate_bass(mood, t, beat_duration, beats_total, duration)

        # Drum pattern
        wave += cls._generate_drums(mood, t, beat_duration, beats_total, duration)

        # Melody
        wave += cls._generate_melody(mood, t, beat_duration, beats_total, duration)

        # Normalise and convert
        return cls._to_int16(wave)

    # ------------------------------------------------------------------
    # Bass
    # ------------------------------------------------------------------

    @classmethod
    def _generate_bass(
        cls,
        mood: MusicMood,
        t: np.ndarray,
        beat_duration: float,
        beats_total: int,
        duration: float,
    ) -> np.ndarray:
        """Generate a bass line following the chord progression."""
        n_samples = len(t)
        wave = np.zeros(n_samples, dtype=np.float64)
        chords = _CHORD_PROGRESSIONS[mood]
        beat_duration * 4  # 4 beats per bar

        for beat in range(beats_total):
            bar_idx = (beat // 4) % len(chords)
            root_note = chords[bar_idx][0]
            freq = _NOTE_FREQS.get(root_note, 130.81) / 2  # One octave down for bass

            beat_start_sample = int(beat * beat_duration * cls.SAMPLE_RATE)
            beat_end_sample = min(int((beat + 1) * beat_duration * cls.SAMPLE_RATE), n_samples)
            if beat_start_sample >= n_samples:
                break

            seg_len = beat_end_sample - beat_start_sample
            seg_t = np.linspace(0, beat_duration, seg_len, dtype=np.float64)

            # Bass envelope: attack-decay per beat
            envelope = np.exp(-seg_t * 3.0) * 0.4

            # Sine bass with slight overtone
            bass = np.sin(2 * np.pi * freq * seg_t) * envelope
            bass += np.sin(2 * np.pi * freq * 2 * seg_t) * envelope * 0.2

            wave[beat_start_sample:beat_end_sample] += bass

        return wave

    # ------------------------------------------------------------------
    # Drums
    # ------------------------------------------------------------------

    @classmethod
    def _generate_drums(
        cls,
        mood: MusicMood,
        t: np.ndarray,
        beat_duration: float,
        beats_total: int,
        duration: float,
    ) -> np.ndarray:
        """Generate a drum pattern appropriate for the mood."""
        n_samples = len(t)
        wave = np.zeros(n_samples, dtype=np.float64)
        _MOOD_PARAMS[mood]["bpm"]

        for beat in range(beats_total):
            beat_start_sample = int(beat * beat_duration * cls.SAMPLE_RATE)
            if beat_start_sample >= n_samples:
                break

            # Kick on beats 0, 2 (every other beat)
            if beat % 2 == 0:
                kick = cls._make_kick(beat_duration * 0.15)
                end = min(beat_start_sample + len(kick), n_samples)
                wave[beat_start_sample:end] += kick[: end - beat_start_sample]

            # Snare on beats 1, 3
            if beat % 2 == 1 and mood in (MusicMood.BATTLE_LIGHT, MusicMood.BATTLE_INTENSE):
                snare = cls._make_snare(beat_duration * 0.1)
                end = min(beat_start_sample + len(snare), n_samples)
                wave[beat_start_sample:end] += snare[: end - beat_start_sample]

            # Hi-hat on every beat for intense, every other for light
            if mood == MusicMood.BATTLE_INTENSE or (mood == MusicMood.BATTLE_LIGHT and beat % 2 == 0):
                hihat = cls._make_hihat(beat_duration * 0.05)
                end = min(beat_start_sample + len(hihat), n_samples)
                wave[beat_start_sample:end] += hihat[: end - beat_start_sample]

        return wave

    @classmethod
    def _make_kick(cls, dur: float) -> np.ndarray:
        """Low-frequency kick drum pulse."""
        n = int(cls.SAMPLE_RATE * dur)
        t = np.linspace(0, dur, n, dtype=np.float64)
        freq_sweep = 150 * np.exp(-t * 30) + 40
        phase = 2 * np.pi * np.cumsum(freq_sweep) / cls.SAMPLE_RATE
        envelope = np.exp(-t * 15)
        return np.sin(phase) * envelope * 0.5

    @classmethod
    def _make_snare(cls, dur: float) -> np.ndarray:
        """Noise-based snare hit."""
        n = int(cls.SAMPLE_RATE * dur)
        t = np.linspace(0, dur, n, dtype=np.float64)
        envelope = np.exp(-t * 20)
        noise = np.random.uniform(-1, 1, n) * envelope
        tone = np.sin(2 * np.pi * 200 * t) * envelope * 0.3
        return (noise * 0.5 + tone) * 0.4

    @classmethod
    def _make_hihat(cls, dur: float) -> np.ndarray:
        """Short high-frequency noise burst for hi-hat."""
        n = int(cls.SAMPLE_RATE * dur)
        t = np.linspace(0, dur, n, dtype=np.float64)
        envelope = np.exp(-t * 50)
        noise = np.random.uniform(-1, 1, n) * envelope
        return noise * 0.15

    # ------------------------------------------------------------------
    # Melody
    # ------------------------------------------------------------------

    @classmethod
    def _generate_melody(
        cls,
        mood: MusicMood,
        t: np.ndarray,
        beat_duration: float,
        beats_total: int,
        duration: float,
    ) -> np.ndarray:
        """Generate a simple melody line following the chord progression."""
        n_samples = len(t)
        wave = np.zeros(n_samples, dtype=np.float64)
        chords = _CHORD_PROGRESSIONS[mood]
        beat_duration * 4

        # Play chord tones as melody notes, one per beat
        for beat in range(beats_total):
            bar_idx = (beat // 4) % len(chords)
            chord = chords[bar_idx]
            note_idx = beat % len(chord)
            note_name = chord[note_idx]
            freq = _NOTE_FREQS.get(note_name, 261.63)

            # For defeat, slow it down – only play on beats 0 and 2
            if mood == MusicMood.DEFEAT and beat % 2 != 0:
                continue

            beat_start_sample = int(beat * beat_duration * cls.SAMPLE_RATE)
            beat_end_sample = min(int((beat + 1) * beat_duration * cls.SAMPLE_RATE), n_samples)
            if beat_start_sample >= n_samples:
                break

            seg_len = beat_end_sample - beat_start_sample
            seg_t = np.linspace(0, beat_duration, seg_len, dtype=np.float64)

            # Melody envelope: soft attack, medium decay
            attack = 1.0 - np.exp(-seg_t * 10)
            decay = np.exp(-seg_t * 2.0)
            envelope = attack * decay * 0.25

            # Sine melody with harmonics
            tone = np.sin(2 * np.pi * freq * seg_t)
            tone += np.sin(2 * np.pi * freq * 2 * seg_t) * 0.3
            tone += np.sin(2 * np.pi * freq * 3 * seg_t) * 0.1

            wave[beat_start_sample:beat_end_sample] += tone * envelope

        return wave

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


class AmbientSoundGenerator:
    """Generates procedural ambient sounds (wind, rain, distant gunfire)."""

    SAMPLE_RATE: ClassVar[int] = SAMPLE_RATE

    @classmethod
    def generate_wind(cls, intensity: float = 0.5, duration: float = 10.0) -> np.ndarray:
        """Generate wind sound via low-pass filtered noise.

        Parameters
        ----------
        intensity:
            Wind strength in [0.0, 1.0]. Higher values increase volume
            and widen the passband.
        duration:
            Length in seconds.

        Returns
        -------
        np.ndarray
            int16 mono waveform at 44100 Hz.
        """
        intensity = max(0.0, min(1.0, intensity))
        n_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, dtype=np.float64)

        # White noise source
        noise = np.random.uniform(-1, 1, n_samples)

        # Simple low-pass filter via moving average (window size scales with intensity)
        window_size = max(1, int(50 * (1.0 - intensity * 0.7)))
        kernel = np.ones(window_size) / window_size
        filtered = np.convolve(noise, kernel, mode="same")

        # Amplitude modulation for gusting effect
        gust_freq = 0.3 + intensity * 0.5
        gust = 0.5 + 0.5 * np.sin(2 * np.pi * gust_freq * t)

        # Fade in/out at edges
        fade_len = min(int(cls.SAMPLE_RATE * 0.1), n_samples // 4)
        fade_in = np.linspace(0, 1, fade_len)
        fade_out = np.linspace(1, 0, fade_len)
        envelope = np.ones(n_samples)
        envelope[:fade_len] = fade_in
        envelope[-fade_len:] = fade_out

        wave = filtered * gust * envelope * intensity * 0.6
        return cls._to_int16(wave)

    @classmethod
    def generate_rain(cls, intensity: float = 0.5, duration: float = 10.0) -> np.ndarray:
        """Generate rain sound via band-pass filtered noise with random drops.

        Parameters
        ----------
        intensity:
            Rain strength in [0.0, 1.0].
        duration:
            Length in seconds.

        Returns
        -------
        np.ndarray
            int16 mono waveform at 44100 Hz.
        """
        intensity = max(0.0, min(1.0, intensity))
        n_samples = int(cls.SAMPLE_RATE * duration)
        np.linspace(0, duration, n_samples, dtype=np.float64)

        # Band-pass filtered noise for continuous rain sound
        noise = np.random.uniform(-1, 1, n_samples)

        # Low-pass first
        lp_window = max(1, int(20 * (1.0 - intensity * 0.5)))
        lp_kernel = np.ones(lp_window) / lp_window
        low_passed = np.convolve(noise, lp_kernel, mode="same")

        # High-pass via subtracting a further low-passed version
        hp_window = max(1, int(200 * (1.0 - intensity * 0.3)))
        hp_kernel = np.ones(hp_window) / hp_window
        very_low = np.convolve(noise, hp_kernel, mode="same")
        band_passed = low_passed - very_low

        # Random raindrop impulses
        drop_count = int(intensity * duration * 50)
        rng = np.random.default_rng(42)
        drop_positions = rng.integers(0, n_samples, size=drop_count)
        drops = np.zeros(n_samples, dtype=np.float64)
        for pos in drop_positions:
            drop_dur = int(cls.SAMPLE_RATE * 0.005)
            end = min(pos + drop_dur, n_samples)
            dt = np.linspace(0, 0.005, end - pos)
            drops[pos:end] += np.exp(-dt * 300) * 0.3

        # Fade in/out
        fade_len = min(int(cls.SAMPLE_RATE * 0.1), n_samples // 4)
        envelope = np.ones(n_samples)
        envelope[:fade_len] = np.linspace(0, 1, fade_len)
        envelope[-fade_len:] = np.linspace(1, 0, fade_len)

        wave = (band_passed * 0.4 + drops) * envelope * intensity * 0.5
        return cls._to_int16(wave)

    @classmethod
    def generate_distant_gunfire(cls, duration: float = 10.0) -> np.ndarray:
        """Generate distant gunfire sounds at irregular intervals.

        Parameters
        ----------
        duration:
            Length in seconds.

        Returns
        -------
        np.ndarray
            int16 mono waveform at 44100 Hz.
        """
        n_samples = int(cls.SAMPLE_RATE * duration)
        wave = np.zeros(n_samples, dtype=np.float64)

        # Random number of shots (3-8 in the duration)
        rng = np.random.default_rng(123)
        shot_count = rng.integers(3, 9)
        shot_positions = sorted(rng.integers(0, n_samples, size=shot_count))

        for pos in shot_positions:
            shot_dur = 0.08  # Short, muffled pop
            shot_samples = int(cls.SAMPLE_RATE * shot_dur)
            end = min(pos + shot_samples, n_samples)
            seg_len = end - pos
            st = np.linspace(0, shot_dur, seg_len, dtype=np.float64)

            # Low-frequency thump (distant)
            thump = np.sin(2 * np.pi * 80 * st) * np.exp(-st * 25) * 0.3
            # Muffled noise
            noise = np.random.uniform(-1, 1, seg_len) * np.exp(-st * 30) * 0.15

            wave[pos:end] += thump + noise

        # Fade in/out
        fade_len = min(int(cls.SAMPLE_RATE * 0.05), n_samples // 4)
        envelope = np.ones(n_samples)
        envelope[:fade_len] = np.linspace(0, 1, fade_len)
        envelope[-fade_len:] = np.linspace(1, 0, fade_len)

        wave *= envelope
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
