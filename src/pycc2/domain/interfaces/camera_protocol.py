"""Camera Protocol — interface for game camera.

Defines the contract that any camera must satisfy for use by the services layer.
Covers the public properties and methods of Camera as consumed by renderers,
input handlers, and interaction controllers.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ICamera(Protocol):
    """Interface for game camera.

    Covers the properties and methods called by services and presentation
    layers on the Camera dataclass.
    """

    @property
    def position(self) -> Any: ...

    @position.setter
    def position(self, value: Any) -> None: ...

    @property
    def zoom(self) -> float: ...

    @zoom.setter
    def zoom(self, value: float) -> None: ...

    @property
    def viewport_width(self) -> int: ...

    @viewport_width.setter
    def viewport_width(self, value: int) -> None: ...

    @property
    def viewport_height(self) -> int: ...

    @viewport_height.setter
    def viewport_height(self, value: int) -> None: ...

    @property
    def projection(self) -> Any: ...

    def world_to_screen(self, world_pos: Any) -> tuple[float, float]: ...

    def screen_to_world(self, screen_pos: tuple[float, float]) -> Any: ...

    def move(self, dx: float, dy: float) -> None: ...

    def set_position(self, pos: Any) -> None: ...

    def constrain_to_map(self, map_width: float, map_height: float) -> None: ...

    def update_shake(self, dt: float) -> None: ...

    def adjust_zoom(
        self,
        factor: float,
        anchor: tuple[float, float] | None = None,
    ) -> None: ...
