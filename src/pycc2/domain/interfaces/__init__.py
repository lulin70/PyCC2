from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar

E = TypeVar("E")


class IEventPublisher(ABC):
    @abstractmethod
    def publish(self, event: Any) -> None: ...

    @abstractmethod
    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None: ...


class IRandomNumberGenerator(ABC):
    @abstractmethod
    def randint(self, low: int, high: int) -> int: ...

    @abstractmethod
    def uniform(self, low: float = 0.0, high: float = 1.0) -> float: ...

    @abstractmethod
    def choice(self, seq: list) -> Any: ...
