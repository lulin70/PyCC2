"""UI Overlay Protocols — contracts for optional UI overlays used by GameLoop.

These protocols decouple the services layer (game_loop) from concrete
presentation-layer UI classes, allowing GameLoop to interact with overlays
through a small, well-defined surface.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ITutorialOverlay(Protocol):
    """Tutorial overlay shown during gameplay."""

    @property
    def visible(self) -> bool: ...

    def toggle(self) -> None: ...

    def handle_input(self, event: Any) -> str | None: ...

    def update(self) -> None: ...

    def render(self, screen: Any) -> None: ...


@runtime_checkable
class IHintManager(Protocol):
    """Floating hint manager for first-time user guidance."""

    def update(self) -> None: ...

    def render(self, screen: Any) -> None: ...


@runtime_checkable
class ISettingsMenu(Protocol):
    """In-game settings menu overlay."""

    @property
    def visible(self) -> bool: ...

    def toggle(self) -> None: ...

    def handle_input(self, event: Any, mouse_pos: tuple[int, int]) -> str | None: ...

    def apply_to_systems(self, sound_system: Any = None, display_config: Any = None) -> dict | None: ...

    def render(self, screen: Any) -> None: ...


@runtime_checkable
class IWeatherState(Protocol):
    """Runtime weather state exposed to the renderer."""

    @property
    def weather_type(self) -> Any: ...


@runtime_checkable
class IWeatherRenderer(Protocol):
    """Renderer for weather visual effects."""

    def render(self, screen: Any, camera: Any, state: IWeatherState) -> None: ...


@runtime_checkable
class ILightingRenderer(Protocol):
    """Renderer for day/night lighting effects."""

    def render(self, screen: Any, time_of_day: float) -> None: ...
