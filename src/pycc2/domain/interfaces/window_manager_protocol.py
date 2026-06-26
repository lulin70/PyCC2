"""Window Manager Protocol — interface for window management.

Defines the contract that any window manager must satisfy for use by the
services layer. Covers the public methods of WindowManager as consumed by
game_loop, event_dispatcher, and hud_manager.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IWindowManager(Protocol):
    """Interface for window management.

    Covers the methods called by services on WindowManager.
    """

    def initialize(self) -> Any: ...

    def initialize_with_config(self, display_config: Any) -> Any: ...

    def get_screen(self) -> Any: ...

    def get_actual_size(self) -> tuple[int, int]: ...

    def resize(self, width: int, height: int) -> None: ...

    def toggle_fullscreen(self) -> None: ...

    def handle_event(self, event: Any) -> bool: ...

    @property
    def fps(self) -> float: ...

    def tick(self, target_fps: int = 60) -> int: ...

    def shutdown(self) -> None: ...
