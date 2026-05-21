"""Unit tests for the voice command system."""
from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from pycc2.domain.entities.unit import Faction
from pycc2.infrastructure.audio.voice_commands import (
    SAMPLE_RATE,
    VoiceCommand,
    VoiceCommandGenerator,
    _GERMAN_COMMANDS,
    play_command,
)


# -----------------------------------------------------------------------
# VoiceCommand enum
# -----------------------------------------------------------------------


class TestVoiceCommandEnum:
    def test_all_commands_defined(self):
        expected = {
            "MOVE_OUT", "FIRE", "TAKE_COVER", "RETREAT",
            "ENEMY_SPOTTED", "FLANK_LEFT", "FLANK_RIGHT",
            "SUPPRESS", "HOLD_POSITION", "DEMOLISH",
        }
        actual = {cmd.name for cmd in VoiceCommand}
        assert actual == expected

    def test_command_values_are_strings(self):
        for cmd in VoiceCommand:
            assert isinstance(cmd.value, str)
            assert len(cmd.value) > 0

    def test_fire_command_value(self):
        assert VoiceCommand.FIRE.value == "Fire!"

    def test_demolish_command_value(self):
        assert VoiceCommand.DEMOLISH.value == "Blow the bridge!"


# -----------------------------------------------------------------------
# German command mapping
# -----------------------------------------------------------------------


class TestGermanCommands:
    def test_all_commands_have_german_equivalent(self):
        for cmd in VoiceCommand:
            assert cmd in _GERMAN_COMMANDS, f"Missing German translation for {cmd.name}"

    def test_german_fire(self):
        assert _GERMAN_COMMANDS[VoiceCommand.FIRE] == "Feuer!"

    def test_german_retreat(self):
        assert _GERMAN_COMMANDS[VoiceCommand.RETREAT] == "Zurück!"

    def test_german_demolish(self):
        assert _GERMAN_COMMANDS[VoiceCommand.DEMOLISH] == "Sprengen!"


# -----------------------------------------------------------------------
# Text and duration helpers
# -----------------------------------------------------------------------


class TestCommandTextSelection:
    def test_allies_get_english(self):
        text = VoiceCommandGenerator._get_command_text(VoiceCommand.FIRE, Faction.ALLIES)
        assert text == "Fire!"

    def test_polish_get_english(self):
        text = VoiceCommandGenerator._get_command_text(VoiceCommand.FIRE, Faction.POLISH)
        assert text == "Fire!"

    def test_axis_get_german(self):
        text = VoiceCommandGenerator._get_command_text(VoiceCommand.FIRE, Faction.AXIS)
        assert text == "Feuer!"


class TestDurationComputation:
    def test_duration_clamped_minimum(self):
        # Short text like "Fire!" has 4 non-space chars → 0.24 → clamped to 0.3
        dur = VoiceCommandGenerator._compute_duration("Fire!")
        assert dur == 0.3

    def test_duration_clamped_maximum(self):
        # Very long text → clamped to 0.8
        dur = VoiceCommandGenerator._compute_duration("A" * 50)
        assert dur == 0.8

    def test_duration_in_range(self):
        for cmd in VoiceCommand:
            dur = VoiceCommandGenerator._compute_duration(cmd.value)
            assert 0.3 <= dur <= 0.8, f"{cmd.name} duration {dur} out of range"


# -----------------------------------------------------------------------
# Sound generation
# -----------------------------------------------------------------------


class TestSoundGeneration:
    def test_generate_command_returns_int16(self):
        result = VoiceCommandGenerator.generate_command(
            VoiceCommand.FIRE, Faction.ALLIES
        )
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16

    def test_generate_command_non_empty(self):
        result = VoiceCommandGenerator.generate_command(
            VoiceCommand.MOVE_OUT, Faction.ALLIES
        )
        assert len(result) > 0
        assert np.any(result != 0)

    def test_generate_command_sample_count(self):
        text = VoiceCommand.FIRE.value
        dur = VoiceCommandGenerator._compute_duration(text)
        result = VoiceCommandGenerator.generate_command(
            VoiceCommand.FIRE, Faction.ALLIES
        )
        expected = int(SAMPLE_RATE * dur)
        assert len(result) == expected

    def test_axis_command_different_from_allies(self):
        allies = VoiceCommandGenerator.generate_command(
            VoiceCommand.FIRE, Faction.ALLIES
        )
        axis = VoiceCommandGenerator.generate_command(
            VoiceCommand.FIRE, Faction.AXIS
        )
        # Different text → different duration or different waveform
        assert not np.array_equal(allies, axis)


# -----------------------------------------------------------------------
# Volume scaling
# -----------------------------------------------------------------------


class TestVolumeScaling:
    def test_volume_zero_produces_silence(self):
        result = VoiceCommandGenerator.generate_command(
            VoiceCommand.FIRE, Faction.ALLIES, volume=0.0
        )
        assert np.all(result == 0)

    def test_volume_half_reduces_amplitude(self):
        full = VoiceCommandGenerator.generate_command(
            VoiceCommand.FIRE, Faction.ALLIES, volume=1.0
        )
        half = VoiceCommandGenerator.generate_command(
            VoiceCommand.FIRE, Faction.ALLIES, volume=0.5
        )
        assert np.max(np.abs(half)) <= np.max(np.abs(full))

    def test_volume_one_non_silent(self):
        result = VoiceCommandGenerator.generate_command(
            VoiceCommand.FIRE, Faction.ALLIES, volume=1.0
        )
        assert np.any(result != 0)


# -----------------------------------------------------------------------
# play_command (mocked pygame)
# -----------------------------------------------------------------------


class TestPlayCommand:
    def test_play_command_with_mocked_pygame(self):
        with patch("pycc2.infrastructure.audio.voice_commands.VoiceCommandGenerator.generate_command") as mock_gen:
            mock_gen.return_value = np.zeros(1000, dtype=np.int16)
            with patch("pygame.mixer.init"):
                with patch("pygame.mixer.get_init", return_value=True):
                    with patch("pygame.mixer.Sound") as mock_sound_cls:
                        mock_instance = mock_sound_cls.return_value
                        play_command(VoiceCommand.FIRE, Faction.ALLIES, volume=0.5)
                        mock_instance.play.assert_called_once()

    def test_play_command_graceful_without_pygame(self):
        # Should not raise even if pygame is unavailable
        with patch("pycc2.infrastructure.audio.voice_commands.VoiceCommandGenerator.generate_command") as mock_gen:
            mock_gen.return_value = np.zeros(1000, dtype=np.int16)
            with patch.dict("sys.modules", {"pygame": None}):
                # This will trigger the except branch in play_command
                play_command(VoiceCommand.FIRE, Faction.ALLIES, volume=0.5)
