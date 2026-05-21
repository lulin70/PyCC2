"""Unit tests for the weapon-differentiated sound system."""
from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from pycc2.infrastructure.audio.weapon_sounds import (
    SAMPLE_RATE,
    WEAPON_SOUND_PROFILES,
    WeaponSoundGenerator,
    WeaponSoundProfile,
)


# -----------------------------------------------------------------------
# WeaponSoundProfile creation and validation
# -----------------------------------------------------------------------


class TestWeaponSoundProfile:
    def test_create_profile(self):
        profile = WeaponSoundProfile(
            weapon_id="TestRifle",
            sound_type="rifle",
            base_frequency=400.0,
            duration=0.15,
            decay_rate=15.0,
            noise_ratio=0.3,
            burst_count=1,
        )
        assert profile.weapon_id == "TestRifle"
        assert profile.sound_type == "rifle"
        assert profile.base_frequency == 400.0
        assert profile.duration == 0.15
        assert profile.decay_rate == 15.0
        assert profile.noise_ratio == 0.3
        assert profile.burst_count == 1

    def test_noise_ratio_bounds(self):
        profile = WeaponSoundProfile(
            weapon_id="Test",
            sound_type="rifle",
            base_frequency=400.0,
            duration=0.1,
            decay_rate=10.0,
            noise_ratio=0.0,
            burst_count=1,
        )
        assert profile.noise_ratio == 0.0

        profile2 = WeaponSoundProfile(
            weapon_id="Test2",
            sound_type="rifle",
            base_frequency=400.0,
            duration=0.1,
            decay_rate=10.0,
            noise_ratio=1.0,
            burst_count=1,
        )
        assert profile2.noise_ratio == 1.0


# -----------------------------------------------------------------------
# WEAPON_SOUND_PROFILES dictionary
# -----------------------------------------------------------------------


class TestWeaponSoundProfilesDict:
    def test_profiles_has_key_weapons(self):
        for key in ("MG42", "MG34", "BREN", "Lee-Enfield", "Kar98k", "M1 Garand",
                     "STEN", "MP40", "PIAT", "Pak 40", "Mortar", "Flammenwerfer"):
            assert key in WEAPON_SOUND_PROFILES, f"Missing profile for {key}"

    def test_mg42_profile_values(self):
        p = WEAPON_SOUND_PROFILES["MG42"]
        assert p.sound_type == "mg_heavy"
        assert p.base_frequency == 200
        assert p.duration == 0.5
        assert p.decay_rate == 8.0
        assert p.noise_ratio == 0.7
        assert p.burst_count == 5

    def test_mortar_has_lowest_base_frequency(self):
        mortar_freq = WEAPON_SOUND_PROFILES["Mortar"].base_frequency
        for name, p in WEAPON_SOUND_PROFILES.items():
            if name != "Mortar":
                assert mortar_freq <= p.base_frequency, (
                    f"Mortar ({mortar_freq}) should have lowest freq, but {name} has {p.base_frequency}"
                )


# -----------------------------------------------------------------------
# Sound generation – non-empty arrays
# -----------------------------------------------------------------------


class TestSoundGenerationNonEmpty:
    @pytest.fixture()
    def rifle_profile(self):
        return WEAPON_SOUND_PROFILES["Lee-Enfield"]

    @pytest.fixture()
    def mg_profile(self):
        return WEAPON_SOUND_PROFILES["MG42"]

    def test_rifle_sound_non_empty(self, rifle_profile):
        result = WeaponSoundGenerator.generate_weapon_sound(rifle_profile)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0
        assert np.any(result != 0)

    def test_mg_sound_non_empty(self, mg_profile):
        result = WeaponSoundGenerator.generate_weapon_sound(mg_profile)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0
        assert np.any(result != 0)

    def test_smg_sound_non_empty(self):
        profile = WEAPON_SOUND_PROFILES["STEN"]
        result = WeaponSoundGenerator.generate_weapon_sound(profile)
        assert len(result) > 0
        assert np.any(result != 0)

    def test_at_weapon_sound_non_empty(self):
        profile = WEAPON_SOUND_PROFILES["PIAT"]
        result = WeaponSoundGenerator.generate_weapon_sound(profile)
        assert len(result) > 0
        assert np.any(result != 0)

    def test_mortar_sound_non_empty(self):
        profile = WEAPON_SOUND_PROFILES["Mortar"]
        result = WeaponSoundGenerator.generate_weapon_sound(profile)
        assert len(result) > 0
        assert np.any(result != 0)

    def test_tank_gun_sound_non_empty(self):
        profile = WEAPON_SOUND_PROFILES["Pak 40"]
        result = WeaponSoundGenerator.generate_weapon_sound(profile)
        assert len(result) > 0
        assert np.any(result != 0)

    def test_flamethrower_sound_non_empty(self):
        profile = WEAPON_SOUND_PROFILES["Flammenwerfer"]
        result = WeaponSoundGenerator.generate_weapon_sound(profile)
        assert len(result) > 0
        assert np.any(result != 0)

    def test_pistol_sound_non_empty(self):
        profile = WeaponSoundProfile(
            weapon_id="Pistol",
            sound_type="pistol",
            base_frequency=500,
            duration=0.05,
            decay_rate=25.0,
            noise_ratio=0.3,
            burst_count=1,
        )
        result = WeaponSoundGenerator.generate_weapon_sound(profile)
        assert len(result) > 0
        assert np.any(result != 0)

    def test_sniper_sound_non_empty(self):
        profile = WeaponSoundProfile(
            weapon_id="Sniper",
            sound_type="sniper",
            base_frequency=450,
            duration=0.3,
            decay_rate=6.0,
            noise_ratio=0.3,
            burst_count=1,
        )
        result = WeaponSoundGenerator.generate_weapon_sound(profile)
        assert len(result) > 0
        assert np.any(result != 0)


# -----------------------------------------------------------------------
# Sound differentiation
# -----------------------------------------------------------------------


class TestSoundDifferentiation:
    def test_mg42_longer_than_rifle(self):
        mg = WeaponSoundGenerator.generate_weapon_sound(WEAPON_SOUND_PROFILES["MG42"])
        rifle = WeaponSoundGenerator.generate_weapon_sound(WEAPON_SOUND_PROFILES["Lee-Enfield"])
        assert len(mg) > len(rifle), "MG42 sound should be longer than rifle"

    def test_mg42_more_noisy_than_rifle(self):
        mg_profile = WEAPON_SOUND_PROFILES["MG42"]
        rifle_profile = WEAPON_SOUND_PROFILES["Lee-Enfield"]
        assert mg_profile.noise_ratio > rifle_profile.noise_ratio
        assert mg_profile.duration > rifle_profile.duration

    def test_tank_gun_lower_frequency_than_rifle(self):
        tank = WEAPON_SOUND_PROFILES["Pak 40"]
        rifle = WEAPON_SOUND_PROFILES["Lee-Enfield"]
        assert tank.base_frequency < rifle.base_frequency


# -----------------------------------------------------------------------
# Sample rate correctness
# -----------------------------------------------------------------------


class TestSampleRate:
    def test_rifle_sample_count_matches_duration(self):
        profile = WEAPON_SOUND_PROFILES["Lee-Enfield"]
        result = WeaponSoundGenerator.generate_weapon_sound(profile)
        expected = int(SAMPLE_RATE * profile.duration)
        assert len(result) == expected

    def test_flamethrower_sample_count_matches_duration(self):
        profile = WEAPON_SOUND_PROFILES["Flammenwerfer"]
        result = WeaponSoundGenerator.generate_weapon_sound(profile)
        expected = int(SAMPLE_RATE * profile.duration)
        assert len(result) == expected


# -----------------------------------------------------------------------
# Burst count affects sound duration
# -----------------------------------------------------------------------


class TestBurstCount:
    def test_mg42_longer_than_mg34_due_to_bursts(self):
        mg42 = WeaponSoundGenerator.generate_weapon_sound(WEAPON_SOUND_PROFILES["MG42"])
        mg34 = WeaponSoundGenerator.generate_weapon_sound(WEAPON_SOUND_PROFILES["MG34"])
        # MG42 has 5 bursts with duration 0.5; MG34 has 4 bursts with duration 0.4
        assert len(mg42) > len(mg34)

    def test_mg_burst_count_affects_length(self):
        base_profile = WEAPON_SOUND_PROFILES["MG42"]
        result_5 = WeaponSoundGenerator.generate_weapon_sound(base_profile)

        profile_3 = WeaponSoundProfile(
            weapon_id="MG42_short",
            sound_type="mg_heavy",
            base_frequency=base_profile.base_frequency,
            duration=base_profile.duration,
            decay_rate=base_profile.decay_rate,
            noise_ratio=base_profile.noise_ratio,
            burst_count=3,
        )
        result_3 = WeaponSoundGenerator.generate_weapon_sound(profile_3)
        # More bursts → more gap samples → longer total
        assert len(result_5) > len(result_3)


# -----------------------------------------------------------------------
# Volume scaling
# -----------------------------------------------------------------------


class TestVolumeScaling:
    def test_apply_volume_reduces_amplitude(self):
        profile = WEAPON_SOUND_PROFILES["Lee-Enfield"]
        raw = WeaponSoundGenerator.generate_weapon_sound(profile)
        quiet = WeaponSoundGenerator._apply_volume(raw, 0.1)
        assert np.max(np.abs(quiet)) <= np.max(np.abs(raw))

    def test_apply_volume_zero_produces_silence(self):
        profile = WEAPON_SOUND_PROFILES["Lee-Enfield"]
        raw = WeaponSoundGenerator.generate_weapon_sound(profile)
        silent = WeaponSoundGenerator._apply_volume(raw, 0.0)
        assert np.all(silent == 0)

    def test_apply_volume_one_preserves(self):
        profile = WEAPON_SOUND_PROFILES["Lee-Enfield"]
        raw = WeaponSoundGenerator.generate_weapon_sound(profile)
        same = WeaponSoundGenerator._apply_volume(raw, 1.0)
        np.testing.assert_array_equal(same, raw)


# -----------------------------------------------------------------------
# play_weapon_sound (mocked pygame)
# -----------------------------------------------------------------------


class TestPlayWeaponSound:
    def test_play_weapon_sound_with_mocked_pygame(self):
        with patch("pycc2.infrastructure.audio.weapon_sounds.WeaponSoundGenerator.generate_weapon_sound") as mock_gen:
            mock_gen.return_value = np.zeros(1000, dtype=np.int16)
            with patch("pygame.mixer.init"):
                with patch("pygame.mixer.get_init", return_value=True):
                    with patch("pygame.mixer.Sound") as mock_sound_cls:
                        mock_instance = mock_sound_cls.return_value
                        WeaponSoundGenerator.play_weapon_sound("MG42", volume=0.5)
                        mock_instance.play.assert_called_once()
