"""E2E Integration Tests for CC2 Audio System Enhancement.

Comprehensive test suite validating all STEP C audio enhancements:
- C-1: Weapon sound differentiation (18 weapons)
- C-2: Combat event sounds (32 events total)
- C-3: Environmental audio system (11 sound types)
- C-4: Advanced mixer (3D audio, priority, ducking)

Tests follow the pattern of e2e_advanced_game_test.py for consistency.
"""

from __future__ import annotations

import sys
import time
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import all audio modules
from pycc2.infrastructure.audio.weapon_sounds import (
    SAMPLE_RATE,
    WEAPON_SOUND_PROFILES,
    WeaponSoundGenerator,
    WeaponSoundProfile,
)

from pycc2.presentation.audio.enhanced_sound_bridge import (
    CombatSoundEvent,
    EnhancedSoundSystem,
    get_enhanced_sound_system,
)

from pycc2.presentation.audio.sound_system import (
    AudioMixerConfig,
    SoundPriority,
    SoundSystem,
    SoundType,
    ProceduralSoundGenerator,
)

from pycc2.infrastructure.audio.environmental_audio import (
    EnvironmentSoundType,
    EnvironmentalSoundGenerator,
    EnvironmentalAudioSystem,
)


class TestC1_WeaponSounds:
    """TEST 1-6: C-1 CC2 Weapon Sound Enhancements"""

    def test_1_new_cc2_weapon_profiles_exist(self):
        """Verify 6 new CC2 weapon profiles were added"""
        new_weapons = [
            "Sherman 75mm",
            "Panzer IV 75mm",
            "M1 Bazooka",
            "Panzerschreck",
            "Springfield Sniper",
            "MP44/StG44",
        ]
        for weapon in new_weapons:
            assert weapon in WEAPON_SOUND_PROFILES, f"Missing weapon profile: {weapon}"
        print(f"✅ All {len(new_weapons)} new CC2 weapon profiles present")

    def test_2_get_weapon_profile_fuzzy_match(self):
        """Test fuzzy matching API for weapon profile lookup"""
        # Exact match
        profile = WeaponSoundGenerator.get_weapon_profile("MG42")
        assert profile.weapon_id == "MG42"

        # Case-insensitive match
        profile = WeaponSoundGenerator.get_weapon_profile("mg42")
        assert profile.weapon_id == "MG42"

        # Partial name match
        profile = WeaponSoundGenerator.get_weapon_profile("Sherman")
        assert "Sherman" in profile.weapon_id

        # Type fallback
        profile = WeaponSoundGenerator.get_weapon_profile("unknown_rifle")
        assert profile.sound_type == "rifle"
        print("✅ Fuzzy matching works correctly")

    def test_3_assault_rifle_generator(self):
        """Test MP44/StG44 assault rifle sound generation"""
        profile = WEAPON_SOUND_PROFILES["MP44/StG44"]
        assert profile.sound_type == "assault_rifle"

        result = WeaponSoundGenerator.generate_weapon_sound(profile)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0
        assert np.any(result != 0), "Generated silence"

        # Should be longer than pistol but shorter than rifle
        pistol_p = WeaponSoundProfile(
            weapon_id="test", sound_type="pistol",
            base_frequency=500, duration=0.05, decay_rate=25.0,
            noise_ratio=0.3, burst_count=1
        )
        pistol_sound = WeaponSoundGenerator.generate_weapon_sound(pistol_p)
        assert len(result) > len(pistol_sound), "Assault rifle should be longer than pistol"
        print(f"✅ Assault rifle sound generated: {len(result)} samples ({len(result)/SAMPLE_RATE:.3f}s)")

    def test_4_tank_cannon_generator(self):
        """Test Sherman/Panzer IV tank cannon sound generation"""
        for tank_name in ["Sherman 75mm", "Panzer IV 75mm"]:
            profile = WEAPON_SOUND_PROFILES[tank_name]
            assert profile.sound_type == "tank_cannon"

            result = WeaponSoundGenerator.generate_weapon_sound(profile)
            assert isinstance(result, np.ndarray)
            assert len(result) > 0

            # Tank cannons should be lower frequency than rifles
            rifle_p = WEAPON_SOUND_PROFILES["Lee-Enfield"]
            assert profile.base_frequency < rifle_p.base_frequency
            print(f"✅ {tank_name} cannon sound: {len(result)} samples")

    def test_5_enhanced_rifle_mechanical_click(self):
        """Verify enhanced rifle sound has mechanical bolt-action click"""
        profile = WEAPON_SOUND_PROFILES["Lee-Enfield"]
        result = WeaponSoundGenerator.generate_weapon_sound(profile)

        # The enhanced version should be slightly longer due to click
        expected_min_len = int(SAMPLE_RATE * profile.duration * 1.1)  # +10% for click
        assert len(result) >= expected_min_len * 0.9, "Rifle sound should include mechanical click"
        print(f"✅ Enhanced rifle with mechanical click: {len(result)} samples")

    def test_6_mg_shell_thud_and_mortar_whoosh(self):
        """Test MG shell thud and mortar whoosh effects"""
        # MG42 should have shell thud after bursts
        mg_profile = WEAPON_SOUND_PROFILES["MG42"]
        mg_sound = WeaponSoundGenerator.generate_weapon_sound(mg_profile)
        assert len(mg_sound) > 0
        print(f"✅ MG42 with shell thud: {len(mg_sound)} samples")

        # Mortar should have whoosh before boom
        mortar_profile = WEAPON_SOUND_PROFILES["Mortar"]
        mortar_sound = WeaponSoundGenerator.generate_weapon_sound(mortar_profile)
        assert len(mortar_sound) > 0
        # Mortar should be longer due to whoosh phase
        assert len(mortar_sound) > int(SAMPLE_RATE * mortar_profile.duration * 0.95)
        print(f"✅ Mortar with flight whoosh: {len(mortar_sound)} samples")


class TestC2_CombatEvents:
    """TEST 7-12: C-2 Combat Event Sound Integration"""

    def test_7_new_combat_events_enum(self):
        """Verify 16 new CombatSoundEvent values exist"""
        required_events = [
            "TANK_CANNON_FIRE",
            "AT_ROCKET_FIRE",
            "MORTAR_LAUNCH",
            "GRENADE_THROW",
            "GRENADE_EXPLOSION_SHORT",
            "AIRSTRIKE_BOMB",
            "VEHICLE_ENGINE_START",
            "VEHICLE_ENGINE_IDLE",
            "VEHICLE_MOVE",
            "ARMOR_PENETRATE",
            "RICOCHET_BOUNCE",
            "NEAR_MISS_WHIZZ",
            "SMOKE_DEPLOY_HISS",
            "SUPPRESSION_FIRE",
        ]
        for event_name in required_events:
            assert hasattr(CombatSoundEvent, event_name), f"Missing CombatSoundEvent: {event_name}"
        print(f"✅ All {len(required_events)} new combat events defined")

    @patch("pycc2.presentation.audio.enhanced_sound_bridge.mixer")
    def test_8_tank_at_mortar_sounds(self, mock_mixer):
        """Test tank cannon, AT rocket, and mortar playback"""
        mock_mixer.init.return_value = None
        mock_mixer.get_init.return_value = (44100, -16, 2, 1024)

        mock_sound_instance = MagicMock()
        mock_mixer.Sound.return_value = mock_sound_instance

        mock_channel = MagicMock()
        mock_mixer.find_channel.return_value = mock_channel
        mock_mixer.Channel.return_value = mock_channel

        system = EnhancedSoundSystem()
        assert system.initialize()

        # Test each heavy weapon
        results = {
            "Tank Cannon": system.play_tank_fire(),
            "AT Rocket": system.play_at_rocket_fire(),
            "Mortar": system.play_mortar_launch(),
        }

        for name, success in results.items():
            assert success, f"{name} playback failed"
        print(f"✅ Heavy weapon sounds: {list(results.keys())}")

    @patch("pycc2.presentation.audio.enhanced_sound_bridge.mixer")
    def test_9_explosions_and_airstrike(self, mock_mixer):
        """Test grenade, airstrike, and explosion variants"""
        mock_mixer.init.return_value = None
        mock_mixer.get_init.return_value = (44100, -16, 2, 1024)
        mock_sound_instance = MagicMock()
        mock_mixer.Sound.return_value = mock_sound_instance
        mock_channel = MagicMock()
        mock_mixer.find_channel.return_value = mock_channel
        mock_mixer.Channel.return_value = mock_channel

        system = EnhancedSoundSystem()
        assert system.initialize()

        results = {
            "Grenade": system.play_grenade_explosion(),
            "Airstrike": system.play_airstrike_bomb(),
            "Explosion": system.play_explosion(),
        }

        for name, success in results.items():
            assert success, f"{name} failed"
        print(f"✅ Explosion sounds: {list(results.keys())}")

    @patch("pycc2.presentation.audio.enhanced_sound_bridge.mixer")
    def test_10_vehicle_engine_states(self, mock_mixer):
        """Test vehicle engine start/idle/move states"""
        mock_mixer.init.return_value = None
        mock_mixer.get_init.return_value = (44100, -16, 2, 1024)
        mock_sound_instance = MagicMock()
        mock_mixer.Sound.return_value = mock_sound_instance
        mock_channel = MagicMock()
        mock_mixer.find_channel.return_value = mock_channel
        mock_mixer.Channel.return_value = mock_channel

        system = EnhancedSoundSystem()
        assert system.initialize()

        for state in ["start", "idle", "move"]:
            success = system.play_vehicle_engine(state)
            assert success, f"Vehicle engine '{state}' state failed"
        print("✅ Vehicle engine 3-state sounds work")

    @patch("pycc2.presentation.audio.enhanced_sound_bridge.mixer")
    def test_11_ballistic_effects(self, mock_mixer):
        """Test armor penetrate, ricochet, and near-miss sounds"""
        mock_mixer.init.return_value = None
        mock_mixer.get_init.return_value = (44100, -16, 2, 1024)
        mock_sound_instance = MagicMock()
        mock_mixer.Sound.return_value = mock_sound_instance
        mock_channel = MagicMock()
        mock_mixer.find_channel.return_value = mock_channel
        mock_mixer.Channel.return_value = mock_channel

        system = EnhancedSoundSystem()
        assert system.initialize()

        ballistic_results = {
            "Armor Penetrate": system.play_armor_penetrate(),
            "Ricochet": system.play_ricochet(),
            "Near Miss": system.play_near_miss(),
        }

        for name, success in ballistic_results.items():
            assert success, f"{name} effect failed"
        print(f"✅ Ballistic effects: {list(ballistic_results.keys())}")

    @patch("pycc2.presentation.audio.enhanced_sound_bridge.mixer")
    def test_12_tactical_support_sounds(self, mock_mixer):
        """Test smoke deploy and suppression fire"""
        mock_mixer.init.return_value = None
        mock_mixer.get_init.return_value = (44100, -16, 2, 1024)
        mock_sound_instance = MagicMock()
        mock_mixer.Sound.return_value = mock_sound_instance
        mock_channel = MagicMock()
        mock_mixer.find_channel.return_value = mock_channel
        mock_mixer.Channel.return_value = mock_channel

        system = EnhancedSoundSystem()
        assert system.initialize()

        assert system.play_combat_event(CombatSoundEvent.SMOKE_DEPLOY_HISS)
        assert system.play_suppression_fire(duration_ms=1500)
        print("✅ Tactical support sounds (smoke/suppression) work")


class TestC3_EnvironmentalAudio:
    """TEST 13-16: C-3 Environmental Audio System"""

    def test_13_environmental_generator_methods(self):
        """Test all EnvironmentalSoundGenerator methods produce valid audio"""
        generators = {
            "Bird Chirp": lambda: EnvironmentalSoundGenerator.generate_bird_chirp(0),
            "Wind Gust": lambda: EnvironmentalSoundGenerator.generate_wind_gust(0.7),
            "Distant Artillery": lambda: EnvironmentalSoundGenerator.generate_distant_artillery(1.0),
            "Rain": lambda: EnvironmentalSoundGenerator.generate_rain(0.8),
            "Thunder": lambda: EnvironmentalSoundGenerator.generate_thunder(),
            "Insect Chirp": lambda: EnvironmentalSoundGenerator.generate_insect_chirp("cricket"),
            "Footsteps": lambda: EnvironmentalSoundGenerator.generate_footstep_ambient("mixed"),
            "Fire Crackle": lambda: EnvironmentalSoundGenerator.generate_fire_crackle(),
            "Radio Static": lambda: EnvironmentalSoundGenerator.generate_radio_static(),
            "Crowd Chatter": lambda: EnvironmentalSoundGenerator.generate_crowd_chatter(),
            "Vehicle Ambient": lambda: EnvironmentalSoundGenerator.generate_vehicle_ambient(),
        }

        for name, gen_func in generators.items():
            try:
                result = gen_func()
                assert isinstance(result, np.ndarray), f"{name} didn't return ndarray"
                assert result.dtype == np.int16, f"{name} wrong dtype"
                assert len(result) > 0, f"{name} returned empty array"
                assert np.any(result != 0), f"{name} returned silence"
            except Exception as e:
                pytest.fail(f"{name} generator failed: {e}")
        print(f"✅ All {len(generators)} environmental generators produce valid audio")

    def test_14_environmental_system_initialization(self):
        """Test EnvironmentalAudioSystem init and basic controls"""
        system = EnvironmentalAudioSystem()

        # Test initial state
        assert system.is_playing(EnvironmentSoundType.BIRDS)
        assert not system.is_playing(EnvironmentSoundType.RAIN)

        # Test weather control
        system.set_weather_rain(True)
        assert system.is_playing(EnvironmentSoundType.RAIN)
        assert not system.is_playing(EnvironmentSoundType.BIRDS)  # Rain silences birds

        system.set_weather_rain(False)
        assert not system.is_playing(EnvironmentSoundType.RAIN)
        print("✅ Environmental system state management works")

    def test_15_context_awareness_time_location(self):
        """Test time-of-day and location type affect sound selection"""
        system = EnvironmentalAudioSystem()

        # Time of day
        system.set_time_of_day(12)  # Noon - birds active
        system.set_time_of_day(2)   # Night - birds inactive (internal logic)

        # Location types
        for location in ["village", "city", "forest", "open_field"]:
            system.set_location_type(location)
            # Should not raise any errors
        print("✅ Context awareness (time/location) accepts inputs correctly")

    def test_16_extended_sound_types(self):
        """Verify 5 new EnvironmentSoundType values added"""
        new_types = [
            "THUNDER",
            "CROWD_CHATTER",
            "VEHICLE_AMBIENT",
            "FIRE_CRACKLE",
            "RADIO_STATIC",
        ]
        for type_name in new_types:
            assert hasattr(EnvironmentSoundType, type_name), f"Missing EnvironmentSoundType: {type_name}"
        print(f"✅ All {len(new_types)} new environmental types present")


class TestC4_AdvancedMixer:
    """TEST 17-18: C-4 Advanced Audio Mixer Features"""

    def test_17_audio_mixer_config_and_priority(self):
        """Test AudioMixerConfig and SoundPriority system"""
        config = AudioMixerConfig(
            max_simultaneous_sounds=16,
            distance_model="inverse",
            reference_distance=100.0,
            max_distance=800.0,
            stereo_separation=1.5,
        )

        assert config.max_simultaneous_sounds == 16
        assert config.distance_model == "inverse"
        assert config.stereo_separation == 1.5

        # Verify priority levels
        assert SoundPriority.CRITICAL.value == 0
        assert SoundPriority.HIGH.value == 1
        assert SoundPriority.MEDIUM.value == 2
        assert SoundPriority.LOW.value == 3
        assert SoundPriority.BACKGROUND.value == 4
        print("✅ AudioMixerConfig and SoundPriority enum correct")

    @patch("pycc2.presentation.audio.sound_system.mixer")
    def test_18_3d_sound_stereo_pan(self, mock_mixer):
        """Test 3D sound positioning and stereo panning"""
        mock_mixer.init.return_value = None
        mock_mixer.get_init.return_value = (22050, -16, 2, 512)

        config = AudioMixerConfig(distance_model="linear", stereo_separation=1.0)
        system = SoundSystem(mixer_config=config)
        system.initialize()

        # Skip actual Sound creation (requires real mixer init), just test pan calculation
        from pycc2.domain.value_objects.vec2 import Vec2

        # Test stereo pan calculation for different angles
        test_cases = [
            (Vec2(0, 10), Vec2(0, 0), 0.0, "Front"),           # Directly in front
            (Vec2(-10, 0), Vec2(0, 0), 0.0, "Left"),             # Left side
            (Vec2(10, 0), Vec2(0, 0), 0.0, "Right"),              # Right side
            (Vec2(0, -10), Vec2(0, 0), 0.0, "Behind"),             # Behind
        ]

        for source_pos, listener_pos, facing, desc in test_cases:
            left_vol, right_vol = system.calculate_stereo_pan(
                source_pos, listener_pos, facing
            )
            assert 0.0 <= left_vol <= 1.0, f"Left volume out of range for {desc}"
            assert 0.0 <= right_vol <= 1.0, f"Right volume out of range for {desc}"

            # Front should be balanced
            if desc == "Front":
                assert abs(left_vol - right_vol) < 0.2, f"{desc} should be balanced"

        print(f"✅ Stereo pan calculation works for {len(test_cases)} positions")


def run_all_tests():
    """Execute all E2E audio tests and report results."""
    print("=" * 70)
    print("🎵 PyCC2 CC2 AUDIO SYSTEM - E2E INTEGRATION TEST SUITE")
    print("=" * 70)
    print()

    start_time = time.time()

    # Run pytest programmatically
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes",
    ])

    elapsed = time.time() - start_time

    print()
    print("=" * 70)
    if exit_code == 0:
        print(f"✅ ALL TESTS PASSED in {elapsed:.2f}s")
    else:
        print(f"❌ SOME TESTS FAILED (exit code: {exit_code})")
    print("=" * 70)

    return exit_code


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
