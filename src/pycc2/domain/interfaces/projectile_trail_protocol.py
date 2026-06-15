"""Projectile Trail Protocol — interface for projectile trail rendering.

Defines the contract that any projectile trail system must satisfy for
use by the services layer. Covers the public API of ProjectileTrailSystem
as consumed by game_loop and combat systems.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IProjectileTrailSystem(Protocol):
    """Interface for projectile trail visual effects.

    Covers the methods called by services (combat_director, game_loop, etc.)
    on ProjectileTrailSystem.
    """

    def update(self, dt: float) -> None:
        """Update all active trails by the given delta time."""
        ...

    def add_bullet_trail(self, sx: float, sy: float, ex: float, ey: float) -> None:
        """Add a bullet trail from start to end position."""
        ...

    def add_shell_trail(self, sx: float, sy: float, ex: float, ey: float) -> None:
        """Add an artillery shell trail from start to end position."""
        ...

    def add_rocket_trail(self, sx: float, sy: float, ex: float, ey: float) -> None:
        """Add a rocket trail from start to end position."""
        ...

    def add_mortar_trail(self, sx: float, sy: float, ex: float, ey: float) -> None:
        """Add a mortar trail from start to end position."""
        ...
