"""Render Pipeline Protocol — interface for the render pipeline.

Defines the contract that any render pipeline must satisfy for use by
the services layer. Covers the public API of RenderPipeline as consumed
by game_loop.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IRenderPipeline(Protocol):
    """Interface for the main render pipeline.

    Covers the methods called by services (game_loop, etc.)
    on RenderPipeline.
    """

    def render(
        self,
        game_map: Any,
        units: Any,
        camera: Any,
        alpha: float,
        selected_unit_ids: Any,
        debug_mode: bool,
        paused: bool,
        tick: int,
        show_post_battle: bool,
        game_result: Any,
        battle_stats: Any,
    ) -> None:
        """Render a complete frame with all layers."""
        ...

    def update_fps(self, fps: float) -> None:
        """Update the FPS display value."""
        ...

    hud_manager: Any | None
    command_bar: Any | None
    unit_panel: Any | None
    minimap: Any | None
