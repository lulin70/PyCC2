from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar, overload

from .ai_service_protocol import IAIService
from .bottom_panel_protocol import IBottomPanel
from .deployment_ui_protocol import IDeploymentUI
from .display_config import DisplayConfig
from .minimap_protocol import IMinimap
from .sound_system_protocol import ISoundSystem

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
