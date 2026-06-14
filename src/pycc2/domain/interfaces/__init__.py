from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar, overload

from .ai_service_protocol import IAIService as IAIService
from .bottom_panel_protocol import IBottomPanel as IBottomPanel
from .camera_protocol import ICamera as ICamera
from .deployment_ui_protocol import IDeploymentUI as IDeploymentUI
from .display_config import DisplayConfig as DisplayConfig
from .input_handler_protocol import IInputHandler as IInputHandler
from .interaction_controller_protocol import IInteractionController as IInteractionController
from .minimap_protocol import IMinimap as IMinimap
from .renderer_protocol import IRenderer as IRenderer
from .sound_system_protocol import ISoundSystem as ISoundSystem
from .window_manager_protocol import IWindowManager as IWindowManager

E = TypeVar("E")


class IEventPublisher(ABC):
    @overload
    @abstractmethod
    def publish(self, event: dict) -> None: ...

    @overload
    @abstractmethod
    def publish(self, event: object) -> None: ...

    @abstractmethod
    def publish(self, event: dict | object) -> None: ...

    @overload
    @abstractmethod
    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None: ...

    @overload
    @abstractmethod
    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None: ...

    @abstractmethod
    def subscribe(self, event_type: type, handler: Callable) -> None: ...

    @abstractmethod
    def subscribe_to(self, event_name: str, handler: Callable[[dict], None]) -> None: ...

    @abstractmethod
    def publish_named(self, event_name: str, data: dict) -> None: ...


class IRandomNumberGenerator(ABC):
    @abstractmethod
    def randint(self, low: int, high: int) -> int: ...

    @abstractmethod
    def uniform(self, low: float = 0.0, high: float = 1.0) -> float: ...

    @abstractmethod
    def choice(self, seq: list) -> Any: ...
