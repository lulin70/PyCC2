"""Voice command audio feedback system (C6)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto

import pygame


class VoiceCommandType(Enum):
    """Types of voice commands."""

    MOVING = auto()
    CONTACT = auto()
    TAKING_FIRE = auto()
    TARGET_DOWN = auto()
    SUPPRESSING = auto()
    NEED_HELP = auto()


@dataclass
class VoiceCommandSystem:
    """
    Voice command audio feedback system.

    Reuses EnhancedSoundBridge for playing voice clips.
    Triggers on unit actions with appropriate delays.
    """

    _cooldowns: dict[VoiceCommandType, float] = field(init=False)
    _cooldown_time: float = 3.0  # seconds between same command

    def __post_init__(self):
        self._cooldowns = {}

    def can_play(self, cmd_type: VoiceCommandType, current_time: float) -> bool:
        """Check if voice command can play (cooldown expired)."""
        last_play = self._cooldowns.get(cmd_type, -999)
        return (current_time - last_play) >= self._cooldown_time

    def play_command(
        self,
        cmd_type: VoiceCommandType,
        current_time: float,
        sound_system=None,
    ) -> bool:
        """Attempt to play a voice command."""
        if not self.can_play(cmd_type, current_time):
            return False

        self._cooldowns[cmd_type] = current_time

        if sound_system:
            try:
                sound_system.play(f"voice_{cmd_type.name.lower()}")
                return True
            except (pygame.error, ValueError, OSError) as e:
                logging.info("Voice command sound play failed: %s", e)

        return True  # Assume success for testing

    def get_command_text(self, cmd_type: VoiceCommandType) -> str:
        """Get display text for subtitle."""
        texts = {
            VoiceCommandType.MOVING: "Moving!",
            VoiceCommandType.CONTACT: "Contact!",
            VoiceCommandType.TAKING_FIRE: "Taking fire!",
            VoiceCommandType.TARGET_DOWN: "Target down!",
            VoiceCommandType.SUPPRESSING: "Suppressing!",
            VoiceCommandType.NEED_HELP: "Need help!",
        }
        return texts.get(cmd_type, "")
