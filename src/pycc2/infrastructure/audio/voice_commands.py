"""Voice command system for PyCC2 using numpy waveform synthesis.

Generates procedural voice-like sounds for military commands, with
faction-dependent language selection (English for Allies/Polish, German for Axis).
No external audio files are needed.
"""
from __future__ import annotations

from enum import Enum
from typing import ClassVar

import numpy as np

from pycc2.domain.entities.unit import Faction

SAMPLE_RATE: int = 44100


class VoiceCommand(Enum):
    """Military voice commands available in the game."""

    MOVE_OUT = "Move out!"
    FIRE = "Fire!"
    TAKE_COVER = "Take cover!"
    RETREAT = "Retreat!"
    ENEMY_SPOTTED = "Enemy spotted!"
    FLANK_LEFT = "Flank left!"
    FLANK_RIGHT = "Flank right!"
    SUPPRESS = "Suppress them!"
    HOLD_POSITION = "Hold position!"
    DEMOLISH = "Blow the bridge!"

    # Morale collapse voice commands
    WAVERING = "We're taking heavy fire!"
    PINNED = "We can't move!"
    BROKEN = "Fall back! Fall back!"
    ROUTING = "Run! Every man for himself!"


# German equivalents for Axis faction
_GERMAN_COMMANDS: dict[VoiceCommand, str] = {
    VoiceCommand.MOVE_OUT: "Marsch!",
    VoiceCommand.FIRE: "Feuer!",
    VoiceCommand.TAKE_COVER: "Deckung!",
    VoiceCommand.RETREAT: "Zurück!",
    VoiceCommand.ENEMY_SPOTTED: "Feind gesichtet!",
    VoiceCommand.FLANK_LEFT: "Umgehung links!",
    VoiceCommand.FLANK_RIGHT: "Umgehung rechts!",
    VoiceCommand.SUPPRESS: "Niederhalten!",
    VoiceCommand.HOLD_POSITION: "Halten Sie!",
    VoiceCommand.DEMOLISH: "Sprengen!",
    VoiceCommand.WAVERING: "Wir werden beschossen!",
    VoiceCommand.PINNED: "Wir können nicht vorwärts!",
    VoiceCommand.BROKEN: "Zurück! Zurück!",
    VoiceCommand.ROUTING: "Rennen! Jeder für sich!",
}

# Approximate formant frequencies (Hz) for vowel-like synthesis
# (F1, F2) pairs for common vowel sounds
_FORMANTS: dict[str, tuple[float, float]] = {
    "a": (730, 1090),
    "e": (530, 1840),
    "i": (270, 2290),
    "o": (570, 840),
    "u": (300, 870),
}

# Syllable rhythm: approximate duration per character in seconds
_SYLLABLE_DURATION: float = 0.06


class VoiceCommandGenerator:
    """Generates procedural voice-like sounds for military commands."""

    SAMPLE_RATE: ClassVar[int] = SAMPLE_RATE

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def generate_command(
        cls,
        command: VoiceCommand,
        faction: Faction,
        volume: float = 0.5,
    ) -> np.ndarray:
        """Generate a voice command waveform.

        Parameters
        ----------
        command:
            The military command to vocalise.
        faction:
            Determines language – Allies/Polish → English, Axis → German.
        volume:
            Output volume in the range [0.0, 1.0].

        Returns
        -------
        np.ndarray
            int16 mono waveform at 44100 Hz.
        """
        text = cls._get_command_text(command, faction)
        duration = cls._compute_duration(text)
        wave = cls._synthesize_voice(text, duration)
        # Morale collapse commands sound more urgent
        if command in (VoiceCommand.BROKEN, VoiceCommand.ROUTING):
            wave = cls._add_urgency(wave)
        scaled = cls._apply_volume(wave, volume)
        return scaled

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_command_text(command: VoiceCommand, faction: Faction) -> str:
        """Return the command text in the appropriate language."""
        if faction == Faction.AXIS:
            return _GERMAN_COMMANDS[command]
        return command.value

    @staticmethod
    def _compute_duration(text: str) -> float:
        """Compute duration in seconds based on text length.

        Clamped to [0.3, 0.8] seconds.
        """
        char_count = len(text.replace(" ", ""))
        raw = char_count * _SYLLABLE_DURATION
        return max(0.3, min(0.8, raw))

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    @classmethod
    def _synthesize_voice(cls, text: str, duration: float) -> np.ndarray:
        """Synthesise a voice-like waveform using FM synthesis.

        The approach:
        1. A base carrier in the male voice range (120-180 Hz).
        2. Formant resonances layered on top for vowel colour.
        3. Amplitude modulation to simulate syllable rhythm.
        """
        n_samples = int(cls.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n_samples, dtype=np.float64)

        # Base frequency – pick within male voice range based on text hash
        base_freq = 120.0 + (hash(text) % 60)

        # Carrier with slight vibrato
        vibrato = 1.0 + 0.02 * np.sin(2 * np.pi * 5.0 * t)
        carrier = np.sin(2 * np.pi * base_freq * np.cumsum(vibrato) / cls.SAMPLE_RATE)

        # Layer formant resonances based on vowels in the text
        formant_wave = np.zeros(n_samples, dtype=np.float64)
        vowels_in_text = [c for c in text.lower() if c in _FORMANTS]
        if vowels_in_text:
            segment_len = n_samples // len(vowels_in_text)
            for idx, vowel in enumerate(vowels_in_text):
                f1, f2 = _FORMANTS[vowel]
                start = idx * segment_len
                end = min(start + segment_len, n_samples)
                seg_t = t[start:end]
                f1_wave = np.sin(2 * np.pi * f1 * seg_t) * 0.3
                f2_wave = np.sin(2 * np.pi * f2 * seg_t) * 0.15
                formant_wave[start:end] += f1_wave + f2_wave
        else:
            # Fallback: generic formant
            formant_wave = (
                np.sin(2 * np.pi * 730 * t) * 0.3 + np.sin(2 * np.pi * 1090 * t) * 0.15
            )

        # Amplitude modulation for syllable rhythm
        syllable_count = max(1, len(text.split()))
        syllable_freq = syllable_count / duration
        am = 0.5 + 0.5 * np.sin(2 * np.pi * syllable_freq * t - np.pi / 2)

        # Envelope: quick attack, gradual decay
        attack = 1.0 - np.exp(-t * 50)
        decay = np.exp(-t * 3.0)
        envelope = attack * decay

        # Combine carrier + formants with amplitude modulation
        wave = (carrier * 0.4 + formant_wave * 0.6) * am * envelope

        # Add a small amount of breath noise
        noise = np.random.uniform(-0.05, 0.05, n_samples) * envelope
        wave += noise

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

    @classmethod
    def _add_urgency(cls, wave: np.ndarray) -> np.ndarray:
        """Add urgency to a voice waveform for morale collapse.

        Increases pitch slightly and adds distortion to convey panic.
        """
        n = len(wave)
        if n == 0:
            return wave
        # Pitch shift up by ~20% (resample at lower rate then truncate)
        shift = 1.2
        indices = np.arange(n) / shift
        indices = indices[indices < n].astype(int)
        shifted = wave[indices]
        # Pad back to original length
        if len(shifted) < n:
            shifted = np.pad(shifted, (0, n - len(shifted)))
        else:
            shifted = shifted[:n]
        # Add slight distortion (clipping)
        shifted = np.clip(shifted.astype(np.float64) * 1.3, -32767, 32767).astype(np.int16)
        return shifted


def play_command(command: VoiceCommand, faction: Faction, volume: float = 0.5) -> None:
    """Generate and play a voice command via pygame.mixer if available."""
    raw = VoiceCommandGenerator.generate_command(command, faction, volume)

    try:
        from pygame import mixer

        if not mixer.get_init():
            mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
        sound = mixer.Sound(array=raw)
        sound.play()
    except Exception:
        pass  # pygame unavailable – sound was generated but not played


# Morale state to VoiceCommand mapping
_MORALE_VOICE_MAP: dict[str, VoiceCommand] = {
    "wavering": VoiceCommand.WAVERING,
    "pinned": VoiceCommand.PINNED,
    "broken": VoiceCommand.BROKEN,
    "routing": VoiceCommand.ROUTING,
}


def play_morale_collapse(morale_state: str, faction: Faction, volume: float = 0.6) -> None:
    """Play a morale collapse voice cry when unit morale drops.

    Parameters
    ----------
    morale_state:
        One of "wavering", "pinned", "broken", "routing".
    faction:
        The faction of the unit (determines language).
    volume:
        Output volume (slightly louder than normal commands).
    """
    command = _MORALE_VOICE_MAP.get(morale_state.lower())
    if command is None:
        return
    play_command(command, faction, volume)
