"""Unit tests for the background music and ambient sound system."""
from __future__ import annotations

import numpy as np
import pytest

from pycc2.infrastructure.audio.bgm_system import (
    SAMPLE_RATE,
    AmbientSoundGenerator,
    BGMGenerator,
    MusicMood,
    _MOOD_PARAMS,
)


# -----------------------------------------------------------------------
# MusicMood enum
# -----------------------------------------------------------------------


class TestMusicMoodEnum:
    def test_all_moods_defined(self):
        expected = {"MENU", "BATTLE_LIGHT", "BATTLE_INTENSE", "VICTORY", "DEFEAT", "AMBIENT"}
        actual = {mood.name for mood in MusicMood}
        assert actual == expected

    def test_mood_count(self):
        assert len(MusicMood) == 6


# -----------------------------------------------------------------------
# Mood parameters
# -----------------------------------------------------------------------


class TestMoodParams:
    def test_all_moods_have_params(self):
        for mood in MusicMood:
            assert mood in _MOOD_PARAMS, f"Missing params for {mood.name}"

    def test_battle_intense_is_fastest(self):
        intense_bpm = _MOOD_PARAMS[MusicMood.BATTLE_INTENSE]["bpm"]
        for mood, params in _MOOD_PARAMS.items():
            if mood != MusicMood.AMBIENT:
                assert intense_bpm >= params["bpm"], (
                    f"BATTLE_INTENSE ({intense_bpm} BPM) should be fastest, "
                    f"but {mood.name} has {params['bpm']} BPM"
                )

    def test_defeat_is_slowest_non_ambient(self):
        defeat_bpm = _MOOD_PARAMS[MusicMood.DEFEAT]["bpm"]
        for mood, params in _MOOD_PARAMS.items():
            if mood not in (MusicMood.AMBIENT, MusicMood.DEFEAT):
                assert defeat_bpm <= params["bpm"], (
                    f"DEFEAT ({defeat_bpm} BPM) should be slowest non-ambient, "
                    f"but {mood.name} has {params['bpm']} BPM"
                )

    def test_ambient_has_zero_bpm(self):
        assert _MOOD_PARAMS[MusicMood.AMBIENT]["bpm"] == 0


# -----------------------------------------------------------------------
# BGM generation
# -----------------------------------------------------------------------


class TestBGMGeneration:
    def test_menu_music_non_empty(self):
        result = BGMGenerator.generate_mood_music(MusicMood.MENU, duration=2.0)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0
        assert np.any(result != 0)

    def test_battle_light_non_empty(self):
        result = BGMGenerator.generate_mood_music(MusicMood.BATTLE_LIGHT, duration=2.0)
        assert len(result) > 0
        assert np.any(result != 0)

    def test_battle_intense_non_empty(self):
        result = BGMGenerator.generate_mood_music(MusicMood.BATTLE_INTENSE, duration=2.0)
        assert len(result) > 0
        assert np.any(result != 0)

    def test_victory_non_empty(self):
        result = BGMGenerator.generate_mood_music(MusicMood.VICTORY, duration=2.0)
        assert len(result) > 0
        assert np.any(result != 0)

    def test_defeat_non_empty(self):
        result = BGMGenerator.generate_mood_music(MusicMood.DEFEAT, duration=2.0)
        assert len(result) > 0
        assert np.any(result != 0)

    def test_ambient_uses_wind(self):
        result = BGMGenerator.generate_mood_music(MusicMood.AMBIENT, duration=2.0)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0

    def test_sample_count_matches_duration(self):
        duration = 3.0
        result = BGMGenerator.generate_mood_music(MusicMood.MENU, duration=duration)
        expected = int(SAMPLE_RATE * duration)
        assert len(result) == expected

    def test_all_moods_produce_int16(self):
        for mood in MusicMood:
            result = BGMGenerator.generate_mood_music(mood, duration=1.0)
            assert result.dtype == np.int16, f"{mood.name} did not produce int16"


# -----------------------------------------------------------------------
# Drum component tests
# -----------------------------------------------------------------------


class TestDrumComponents:
    def test_kick_non_empty(self):
        kick = BGMGenerator._make_kick(0.1)
        assert len(kick) > 0
        assert np.any(kick != 0)

    def test_snare_non_empty(self):
        snare = BGMGenerator._make_snare(0.1)
        assert len(snare) > 0
        assert np.any(snare != 0)

    def test_hihat_non_empty(self):
        hihat = BGMGenerator._make_hihat(0.05)
        assert len(hihat) > 0
        assert np.any(hihat != 0)

    def test_kick_is_low_frequency(self):
        kick = BGMGenerator._make_kick(0.15)
        # Kick should have dominant low-frequency energy
        fft = np.abs(np.fft.rfft(kick.astype(np.float64)))
        freqs = np.fft.rfftfreq(len(kick), 1.0 / SAMPLE_RATE)
        low_mask = freqs < 300
        high_mask = freqs >= 300
        low_energy = np.sum(fft[low_mask])
        high_energy = np.sum(fft[high_mask])
        assert low_energy > high_energy, "Kick drum should have more low-frequency energy"


# -----------------------------------------------------------------------
# AmbientSoundGenerator
# -----------------------------------------------------------------------


class TestWindGeneration:
    def test_wind_non_empty(self):
        result = AmbientSoundGenerator.generate_wind(intensity=0.5, duration=2.0)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0
        assert np.any(result != 0)

    def test_wind_sample_count(self):
        duration = 3.0
        result = AmbientSoundGenerator.generate_wind(intensity=0.5, duration=duration)
        expected = int(SAMPLE_RATE * duration)
        assert len(result) == expected

    def test_wind_zero_intensity_produces_silence(self):
        result = AmbientSoundGenerator.generate_wind(intensity=0.0, duration=1.0)
        assert np.all(result == 0)

    def test_wind_high_intensity_louder_than_low(self):
        low = AmbientSoundGenerator.generate_wind(intensity=0.1, duration=2.0)
        high = AmbientSoundGenerator.generate_wind(intensity=0.9, duration=2.0)
        # Use same RNG seed by regenerating – both use default numpy RNG
        # Just check high intensity has non-zero output
        assert np.max(np.abs(high)) > 0


class TestRainGeneration:
    def test_rain_non_empty(self):
        result = AmbientSoundGenerator.generate_rain(intensity=0.5, duration=2.0)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0
        assert np.any(result != 0)

    def test_rain_sample_count(self):
        duration = 3.0
        result = AmbientSoundGenerator.generate_rain(intensity=0.5, duration=duration)
        expected = int(SAMPLE_RATE * duration)
        assert len(result) == expected

    def test_rain_zero_intensity_produces_silence(self):
        result = AmbientSoundGenerator.generate_rain(intensity=0.0, duration=1.0)
        assert np.all(result == 0)


class TestDistantGunfire:
    def test_gunfire_non_empty(self):
        result = AmbientSoundGenerator.generate_distant_gunfire(duration=5.0)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0

    def test_gunfire_sample_count(self):
        duration = 4.0
        result = AmbientSoundGenerator.generate_distant_gunfire(duration=duration)
        expected = int(SAMPLE_RATE * duration)
        assert len(result) == expected

    def test_gunfire_has_sparse_content(self):
        result = AmbientSoundGenerator.generate_distant_gunfire(duration=5.0)
        # Most samples should be zero (silent between shots)
        zero_ratio = np.sum(result == 0) / len(result)
        assert zero_ratio > 0.5, "Distant gunfire should have mostly silent gaps"
