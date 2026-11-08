"""Unit tests for SoundEffectManager.

All tests run with the SDL dummy audio driver, so no real sound card is
required. Waveform generation is pure numpy, and the resulting
``pygame.mixer.Sound`` objects are inspected structurally.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import MagicMock

import numpy as np
import pygame
import pytest

from pycc2.infrastructure.audio.sound_effect_manager import (
    SAMPLE_RATE,
    SoundEffectManager,
    SoundEffectType,
)

ALL_EFFECTS = list(SoundEffectType)


@pytest.fixture()
def manager() -> SoundEffectManager:
    """Return a fresh manager (mixer is already initialized by the ctor)."""
    return SoundEffectManager()


# ===========================================================================
# Enum / construction
# ===========================================================================


@pytest.mark.unit
class TestSoundEffectType:
    def test_contains_all_category_effects(self):
        assert len(SoundEffectType) == 16
        assert SoundEffectType.UI_CLICK in SoundEffectType
        assert SoundEffectType.BUILDING_CONSTRUCT in SoundEffectType
        assert SoundEffectType.EXPLOSION_LARGE in SoundEffectType


@pytest.mark.unit
class TestInit:
    def test_default_state(self, manager):
        assert manager._sound_cache == {}
        assert manager._volume == pytest.approx(0.7)

    def test_module_sample_rate_exposed_as_class_constant(self, manager):
        assert SAMPLE_RATE == 44100
        assert manager.SAMPLE_RATE == SAMPLE_RATE


# ===========================================================================
# Volume handling
# ===========================================================================


@pytest.mark.unit
class TestSetVolume:
    def test_sets_valid_volume(self, manager):
        manager.set_volume(0.25)
        assert manager._volume == pytest.approx(0.25)

    @pytest.mark.parametrize("value", [0.0, 1.0])
    def test_volume_boundaries_accepted(self, manager, value):
        manager.set_volume(value)
        assert manager._volume == pytest.approx(value)

    def test_clamps_above_one(self, manager):
        manager.set_volume(4.5)
        assert manager._volume == pytest.approx(1.0)

    def test_clamps_below_zero(self, manager):
        manager.set_volume(-3.0)
        assert manager._volume == pytest.approx(0.0)


# ===========================================================================
# play_effect
# ===========================================================================


@pytest.mark.unit
class TestPlayEffect:
    def test_generates_and_caches_sound(self, manager):
        manager.play_effect(SoundEffectType.UI_CLICK)
        cached = manager._sound_cache[SoundEffectType.UI_CLICK]
        assert isinstance(cached, pygame.mixer.Sound)

        manager.play_effect(SoundEffectType.UI_CLICK)
        assert manager._sound_cache[SoundEffectType.UI_CLICK] is cached
        assert len(manager._sound_cache) == 1

    def test_reuses_cache_across_different_effects(self, manager):
        manager.play_effect(SoundEffectType.UI_CLICK)
        manager.play_effect(SoundEffectType.UI_HOVER)
        assert set(manager._sound_cache) == {
            SoundEffectType.UI_CLICK,
            SoundEffectType.UI_HOVER,
        }

    def test_applies_current_volume_and_plays(self, manager):
        mock_sound = MagicMock()
        manager._sound_cache[SoundEffectType.UNIT_SELECT] = mock_sound
        manager.set_volume(0.25)

        manager.play_effect(SoundEffectType.UNIT_SELECT)

        mock_sound.set_volume.assert_called_once_with(0.25)
        mock_sound.play.assert_called_once_with()

    def test_cached_sound_gets_updated_volume(self, manager):
        manager.set_volume(0.5)
        manager.play_effect(SoundEffectType.UI_CONFIRM)
        sound = manager._sound_cache[SoundEffectType.UI_CONFIRM]

        manager.set_volume(0.1)
        manager.play_effect(SoundEffectType.UI_CONFIRM)

        assert sound.get_volume() == pytest.approx(0.1, abs=0.01)


# ===========================================================================
# Effect generation dispatch
# ===========================================================================


@pytest.mark.unit
class TestGenerateEffect:
    @pytest.mark.parametrize("effect_type", ALL_EFFECTS)
    def test_every_effect_produces_non_empty_sound(self, manager, effect_type):
        sound = manager._generate_effect(effect_type)
        assert isinstance(sound, pygame.mixer.Sound)
        assert sound.get_length() > 0.0

    def test_unknown_effect_falls_back_to_click(self, manager):
        fallback = manager._generate_effect(object())
        reference = manager._generate_effect(SoundEffectType.UI_CLICK)
        assert isinstance(fallback, pygame.mixer.Sound)
        assert fallback.get_length() == pytest.approx(reference.get_length())

    @pytest.mark.parametrize("effect_type", ALL_EFFECTS)
    def test_generated_wave_is_stereo_full_scale(self, manager, effect_type):
        sound = manager._generate_effect(effect_type)
        samples = pygame.sndarray.array(sound)
        assert samples.shape[1] == 2
        assert samples.max() <= 32767
        assert samples.min() >= -32768


# ===========================================================================
# _to_sound
# ===========================================================================


@pytest.mark.unit
class TestToSound:
    def test_normalizes_peak_to_int16_max(self, manager):
        wave = np.array([0.5, -0.5, 0.25], dtype=np.float64)
        samples = pygame.sndarray.array(manager._to_sound(wave))

        assert samples.shape == (3, 2)
        assert samples.max() == 32767
        assert samples.min() == -32767

    def test_duplicates_mono_into_both_channels(self, manager):
        wave = np.array([0.2, -0.4], dtype=np.float64)
        samples = pygame.sndarray.array(manager._to_sound(wave))

        np.testing.assert_array_equal(samples[:, 0], samples[:, 1])

    def test_all_zero_wave_does_not_divide_by_zero(self, manager):
        samples = pygame.sndarray.array(manager._to_sound(np.zeros(10)))
        assert samples.shape == (10, 2)
        assert not np.any(samples)
