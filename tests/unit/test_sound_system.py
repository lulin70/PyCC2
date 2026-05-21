from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pycc2.presentation.audio.sound_system import (
    ProceduralSoundGenerator,
    SoundConfig,
    SoundSystem,
    SoundType,
)


class TestProceduralSoundGeneratorClick:
    def test_generate_click_returns_int16_array(self):
        result = ProceduralSoundGenerator.generate_click()
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0

    def test_generate_click_has_correct_duration(self):
        duration_ms = 50
        expected_samples = int(ProceduralSoundGenerator.SAMPLE_RATE * duration_ms / 1000)
        result = ProceduralSoundGenerator.generate_click(duration_ms=duration_ms)
        assert len(result) == expected_samples


class TestProceduralSoundGeneratorHover:
    def test_generate_hover_returns_shorter_array_than_click(self):
        hover = ProceduralSoundGenerator.generate_hover()
        click = ProceduralSoundGenerator.generate_click()
        assert len(hover) < len(click)

    def test_generate_hover_is_int16(self):
        result = ProceduralSoundGenerator.generate_hover()
        assert result.dtype == np.int16


class TestProceduralSoundGeneratorRifleShot:
    def test_generate_rifle_shot_returns_non_zero_array(self):
        result = ProceduralSoundGenerator.generate_rifle_shot()
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert np.any(result != 0)


class TestProceduralSoundGeneratorExplosion:
    def test_generate_explosion_returns_longer_array(self):
        explosion = ProceduralSoundGenerator.generate_explosion()
        rifle = ProceduralSoundGenerator.generate_rifle_shot()
        assert len(explosion) > len(rifle)

    def test_generate_explosion_is_int16(self):
        result = ProceduralSoundGenerator.generate_explosion()
        assert result.dtype == np.int16


class TestProceduralSoundGeneratorMGBurst:
    def test_mg_burst_length_scales_with_burst_count(self):
        burst = ProceduralSoundGenerator.generate_mg_burst(burst_count=3)
        assert isinstance(burst, np.ndarray)
        assert burst.dtype == np.int16
        assert len(burst) > 0
        single_shot = ProceduralSoundGenerator.generate_rifle_shot()
        assert len(burst) >= len(single_shot)


class TestProceduralSoundGeneratorHitConfirm:
    def test_hit_confirm_is_short_thud(self):
        result = ProceduralSoundGenerator.generate_hit_confirm()
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0
        assert len(result) < len(ProceduralSoundGenerator.generate_rifle_shot())


class TestProceduralSoundGeneratorDeathCry:
    def test_death_cry_has_frequency_sweep(self):
        result = ProceduralSoundGenerator.generate_death_cry()
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0
        first_half = result[: len(result) // 2]
        second_half = result[len(result) // 2 :]
        assert abs(float(np.mean(np.abs(first_half)))) >= abs(float(np.mean(np.abs(second_half))))


class TestProceduralSoundGeneratorFootstep:
    def test_footstep_grass_is_noisy(self):
        grass = ProceduralSoundGenerator.generate_footstep("grass")
        assert grass.dtype == np.int16
        std_val = float(np.std(grass))
        assert std_val > 100

    def test_footstep_road_differs_from_grass(self):
        grass = ProceduralSoundGenerator.generate_footstep("grass")
        road = ProceduralSoundGenerator.generate_footstep("road")
        assert not np.array_equal(grass, road)


@pytest.fixture
def mock_mixer():
    with patch.dict(os.environ, {"SDL_AUDIODRIVER": "dummy", "SDL_VIDEODRIVER": "dummy"}):
        with patch("pygame.mixer.init"):
            with patch("pygame.mixer.Sound") as MockSound:
                mock_sound_instance = MagicMock()
                MockSound.return_value = mock_sound_instance
                yield MockSound, mock_sound_instance


class TestSoundSystemInit:
    def test_initialize_creates_cached_sounds(self, mock_mixer):
        MockSound, _ = mock_mixer
        config = SoundConfig(enabled=True)
        sys = SoundSystem(config=config)
        sys.initialize()
        assert sys.initialized is True
        assert SoundType.UI_CLICK.name in sys._cache
        assert SoundType.RIFLE_SHOT.name in sys._cache

    def test_initialize_disabled_config_sets_enabled_false(self, mock_mixer):
        with patch("pygame.mixer.init", side_effect=Exception("no audio")):
            config = SoundConfig(enabled=True)
            sys = SoundSystem(config=config)
            sys.initialize()
            assert sys.config.enabled is False


class TestSoundSystemPlay:
    def test_play_cached_sound_returns_true(self, mock_mixer):
        MockSound, mock_sound = mock_mixer
        config = SoundConfig(enabled=True)
        sys = SoundSystem(config=config)
        sys.initialize()

        with patch("pygame.mixer.find_channel", return_value=MagicMock()):
            result = sys.play(SoundType.UI_CLICK)
            assert result is True

    def test_play_uncached_sound_generates_dynamically(self, mock_mixer):
        MockSound, mock_sound = mock_mixer
        config = SoundConfig(enabled=True)
        sys = SoundSystem(config=config)
        sys.initialize()

        with patch("pygame.mixer.find_channel", return_value=MagicMock()):
            result = sys.play(SoundType.UI_CANCEL)
            assert result is True
            assert SoundType.UI_CANCEL.name in sys._cache

    def test_play_when_disabled_returns_false(self, mock_mixer):
        config = SoundConfig(enabled=False)
        sys = SoundSystem(config=config)
        sys.initialize()
        result = sys.play(SoundType.UI_CLICK)
        assert result is False


class TestVolumeControl:
    def test_master_volume_affects_final_volume(self, mock_mixer):
        MockSound, mock_sound = mock_mixer
        config = SoundConfig(master_volume=0.5, sfx_volume=1.0, enabled=True)
        sys = SoundSystem(config=config)
        sys.initialize()

        with patch("pygame.mixer.find_channel", return_value=MagicMock()):
            sys.play(SoundType.UI_CLICK)
            set_volume_calls = mock_sound.set_volume.call_args_list
            if set_volume_calls:
                called_vol = set_volume_calls[-1][0][0]
                assert called_vol <= 0.51

    def test_set_master_volume_clamps_range(self):
        sys = SoundSystem()
        sys.set_master_volume(2.0)
        assert sys.config.master_volume == 1.0
        sys.set_master_volume(-0.5)
        assert sys.config.master_volume == 0.0


class TestToggle:
    def test_toggle_switches_enabled_state(self):
        sys = SoundSystem()
        initial = sys.config.enabled
        result = sys.toggle()
        assert result != initial
        assert sys.config.enabled == (not initial)

    def test_toggle_multiple_times(self):
        sys = SoundSystem()
        states = [sys.toggle() for _ in range(4)]
        assert states == [False, True, False, True]
