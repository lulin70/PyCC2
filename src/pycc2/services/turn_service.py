"""Turn/Time Management Service

Manages game time progression, turn phases, and timing-related game rules.
Handles turn order, phase transitions, and time-based events.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.infrastructure.events.event_protocol import (
    GamePhaseChangedEvent,
    TurnEndedEvent,
    TurnStartedEvent,
)


class GamePhase(Enum):
    """Phases of a game turn."""

    PLANNING = auto()
    MOVEMENT = auto()
    COMBAT = auto()
    RESOLUTION = auto()


@dataclass
class TurnState:
    """Current state of the turn system."""

    current_turn: int = 1
    current_phase: GamePhase = GamePhase.PLANNING
    turn_order: list[str] = field(default_factory=list)
    current_faction_index: int = 0
    max_turns: int | None = None
    time_elapsed_seconds: float = 0.0

    def __post_init__(self):
        if not self.turn_order:
            self.turn_order = ["allied", "axis"]


class TurnService:
    """Manages turn-based gameplay flow.

    Handles turn progression, phase management, and time tracking.
    Publishes events for turn/phase changes.
    """

    def __init__(self, event_bus: EventBus, max_turns: int | None = None):
        """Initialize the turn service with event bus and optional turn limit."""
        self.event_bus = event_bus
        self.state = TurnState(max_turns=max_turns)
        self._logger = logging.getLogger("pycc2.turn_service")
        self._phase_callbacks: dict[GamePhase, Callable] = {}
        self._turn_start_callbacks: list[Callable] = []
        self._turn_end_callbacks: list[Callable] = []

    def register_phase_callback(self, phase: GamePhase, callback: Callable) -> None:
        """Register a callback to be called when a phase starts."""
        self._phase_callbacks[phase] = callback

    def register_turn_start_callback(self, callback: Callable) -> None:
        """Register callback called at start of each turn."""
        self._turn_start_callbacks.append(callback)

    def register_turn_end_callback(self, callback: Callable) -> None:
        """Register callback called at end of each turn."""
        self._turn_end_callbacks.append(callback)

    def start_game(self) -> None:
        """Initialize and start the game from turn 1."""
        self.state.current_turn = 1
        self.state.current_phase = GamePhase.PLANNING
        self.state.current_faction_index = 0
        self.state.time_elapsed_seconds = 0.0

        self.event_bus.publish(
            TurnStartedEvent(
                turn_number=1,
                faction=self.state.turn_order[0],
            )
        )
        self._logger.info(f"Game started | Turn {self.state.current_turn}")

    def advance_phase(self) -> GamePhase:
        """Advance to next phase in current turn.

        Returns:
            The new current phase

        """
        phases = list(GamePhase)
        current_idx = phases.index(self.state.current_phase)
        next_idx = (current_idx + 1) % len(phases)
        old_phase = self.state.current_phase
        self.state.current_phase = phases[next_idx]

        self.event_bus.publish(
            GamePhaseChangedEvent(
                old_phase=old_phase.name,
                new_phase=self.state.current_phase.name,
                turn_number=self.state.current_turn,
            )
        )

        callback = self._phase_callbacks.get(self.state.current_phase)
        if callback:
            callback()

        self._logger.debug(f"Phase advanced: {old_phase.name} -> {self.state.current_phase.name}")

        if self.state.current_phase == GamePhase.PLANNING:
            self._advance_turn()

        return self.state.current_phase

    def _advance_turn(self) -> None:
        """Advance to the next turn number."""
        self.state.current_turn += 1

        for callback in self._turn_end_callbacks:
            callback()

        if self.state.max_turns and self.state.current_turn > self.state.max_turns:
            self._logger.info(f"Turn limit reached: {self.state.max_turns}")
            return

        self.event_bus.publish(
            TurnEndedEvent(
                turn_number=self.state.current_turn - 1,
            )
        )

        self.state.current_faction_index = (self.state.current_faction_index + 1) % len(
            self.state.turn_order
        )
        current_faction = self.state.turn_order[self.state.current_faction_index]

        self.event_bus.publish(
            TurnStartedEvent(
                turn_number=self.state.current_turn,
                faction=current_faction,
            )
        )

        for callback in self._turn_start_callbacks:
            callback()

        self._logger.info(
            f"Turn {self.state.current_turn} started | Active faction: {current_faction}"
        )

    def end_current_turn(self) -> None:
        """Force-end current turn and move to next."""
        self.state.current_phase = GamePhase.RESOLUTION
        self.advance_phase()

    def update_time(self, dt: float) -> None:
        """Update elapsed game time."""
        self.state.time_elapsed_seconds += dt

    def get_current_faction(self) -> str:
        """Get the faction whose turn it currently is."""
        return self.state.turn_order[self.state.current_faction_index]

    def is_player_turn(self, player_faction: str) -> bool:
        """Check if it's a specific player's turn."""
        return self.get_current_faction() == player_faction

    @property
    def is_turn_limit_reached(self) -> bool:
        """Check if maximum turns have been reached."""
        if self.state.max_turns is None:
            return False
        return self.state.current_turn > self.state.max_turns

    @property
    def formatted_time(self) -> str:
        """Get elapsed time as MM:SS string."""
        total_seconds = int(self.state.time_elapsed_seconds)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def reset(self) -> None:
        """Reset turn state to initial values."""
        self.state = TurnState(max_turns=self.state.max_turns)
        self._logger.info("Turn service reset")

    def get_state_summary(self) -> dict:
        """Get summary of current turn state."""
        return {
            "turn": self.state.current_turn,
            "phase": self.state.current_phase.name,
            "faction": self.get_current_faction(),
            "time": self.formatted_time,
            "max_turns": self.state.max_turns,
        }
