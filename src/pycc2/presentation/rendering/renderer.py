"""
IRenderer Protocol

Abstract interface defining the contract for all renderers.
Follows dependency inversion principle - domain layer knows this protocol,
but not specific implementations.
"""

from typing import Protocol

from pygame import Surface


class IRenderer(Protocol):
    """Protocol defining renderer interface."""

    def initialize(self, width: int, height: int) -> None:
        """Initialize the renderer with given dimensions."""
        ...

    def clear(self) -> None:
        """Clear the screen/buffer."""
        ...

    def draw_tile(
        self,
        surface: Surface,
        x: int,
        y: int,
        color: tuple[int, int, int],
        size: int = 32,
    ) -> None:
        """Draw a single tile at grid position (x, y)."""
        ...

    def draw_unit(
        self,
        surface: Surface,
        x: int,
        y: int,
        unit_type: str,
        faction: str,
        selected: bool = False,
        size: int = 32,
    ) -> None:
        """Draw a unit at grid position (x, y)."""
        ...

    def draw_projectile(
        self,
        surface: Surface,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        hit: bool = False,
    ) -> None:
        """Draw a projectile trajectory from start to end position."""
        ...

    def draw_selection_box(
        self,
        surface: Surface,
        x: int,
        y: int,
        width: int = 1,
        height: int = 1,
    ) -> None:
        """Draw selection box around tiles."""
        ...

    def draw_fog_of_war(
        self,
        surface: Surface,
        fog_grid: list[list[bool]],
        tile_size: int = 32,
    ) -> None:
        """Draw fog of war overlay based on visibility grid."""
        ...

    def present(self) -> None:
        """Present/double-buffer swap to show rendered frame."""
        ...

    def shutdown(self) -> None:
        """Clean up renderer resources."""
        ...
