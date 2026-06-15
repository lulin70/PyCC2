"""Combat Director Protocol — interface for combat direction.

Defines the contract that any combat director must satisfy for use by
the services layer. Covers the public API of CombatDirector as consumed
by game_loop.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ICombatDirector(Protocol):
    """Interface for combat direction and attack processing.

    Covers the methods called by services (game_loop, event_dispatcher, etc.)
    on CombatDirector.
    """

    def update(self, units: Any, game_map: Any, dt: float, battle_stats: Any) -> None:
        """Update combat state for the current frame."""
        ...

    def process_effects(self, renderer: Any, camera: Any) -> None:
        """Process and render visual combat effects."""
        ...

    def handle_player_command(self, data: Any, units: Any, game_map: Any) -> None:
        """Handle a player-issued combat command."""
        ...

    def execute_attack(self, attacker: Any, target: Any) -> None:
        """Execute an attack from attacker to target."""
        ...

    def on_unit_attacked(self, data: Any) -> None:
        """Callback when a unit is attacked."""
        ...

    def record_stats(self, data: Any, units: Any, battle_stats: Any) -> None:
        """Record combat statistics."""
        ...

    def initialize(self) -> None:
        """Initialize the combat director."""
        ...
