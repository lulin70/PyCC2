"""Renderer Protocol — interface for game renderers.

Defines the contract that any renderer must satisfy for use by the services layer.
Covers the public API of EnhancedRenderer and RenderPipeline as consumed by
game_loop, hud_manager, and event_dispatcher.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IRenderer(Protocol):
    """Interface for game renderers.

    Covers the methods called by services (game_loop, hud_manager, etc.)
    on EnhancedRenderer and RenderPipeline.
    """

    def render(
        self,
        game_map: Any,
        units: list[Any],
        camera: Any,
        alpha: float = 1.0,
        selected_unit_ids: set[str] | None = None,
        debug_mode: bool = False,
    ) -> None: ...

    def initialize(self, screen: Any) -> None: ...

    def resize(self, width: int, height: int) -> None: ...
