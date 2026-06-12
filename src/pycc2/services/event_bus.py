from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any, Required, TypeVar, get_type_hints, overload

E = TypeVar("E")

logger = logging.getLogger(__name__)


from pycc2.domain.interfaces import IEventPublisher


class EventBus(IEventPublisher):
    _MAX_QUEUE_SIZE = 1000

    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable]] = defaultdict(list)
        self._named_handlers: dict[str, list[Callable[[dict], None]]] = defaultdict(list)
        self._queue: list[tuple[float, dict | object]] = []
        self._error_count: int = 0
        self._total_published: int = 0
        self._registered_types: set[type] = set()

    @overload
    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None: ...

    @overload
    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None: ...

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._registered_types.add(event_type)
        self._handlers[event_type].append(handler)

    @overload
    def unsubscribe(self, event_type: type[E], handler: Callable[[E], None]) -> bool: ...

    @overload
    def unsubscribe(self, event_type: type, handler: Callable[[Any], None]) -> bool: ...

    def unsubscribe(self, event_type: type, handler: Callable) -> bool:
        try:
            self._handlers[event_type].remove(handler)
            return True
        except (ValueError, KeyError):
            return False

    def subscribe_to(self, event_name: str, handler: Callable[[dict], None]) -> None:
        self._named_handlers[event_name].append(handler)

    def unsubscribe_from(self, event_name: str, handler: Callable[[dict], None]) -> bool:
        try:
            self._named_handlers[event_name].remove(handler)
            return True
        except (ValueError, KeyError):
            return False

    @staticmethod
    def _get_required_keys(typed_dict_cls: type) -> frozenset:
        try:
            hints = get_type_hints(typed_dict_cls, include_extras=True)
            required = frozenset(
                k for k, v in hints.items() if getattr(v, "__origin__", None) is Required
            )
            if required:
                return required
        except (ValueError, TypeError, KeyError) as e:
            logging.warning(f"TypedDict required keys introspection failed: {e}")
        rk = getattr(typed_dict_cls, "__required_keys__", None)
        return rk if rk is not None else frozenset()

    @staticmethod
    def _match_typed_dict(event: dict, registered: set[type]) -> type | None:
        best_match: type | None = None
        best_count = -1
        for rt in registered:
            required = EventBus._get_required_keys(rt)
            if required and required.issubset(event.keys()) and len(required) > best_count:
                best_match = rt
                best_count = len(required)
        return best_match

    @overload
    def publish(self, event: dict) -> None: ...

    @overload
    def publish(self, event: object) -> None: ...

    def publish(self, event: dict | object) -> None:
        event_type = type(event)
        if event_type is dict and self._registered_types:
            matched = self._match_typed_dict(event, self._registered_types)
            if matched is not None:
                event_type = matched
        handlers = self._handlers.get(event_type, [])
        self._total_published += 1

        for handler in handlers:
            try:
                handler(event)
            except (ValueError, TypeError, KeyError, RuntimeError, AttributeError) as e:
                self._error_count += 1
                logger.error(
                    "Handler error for %s: %s",
                    event_type.__name__,
                    e,
                    exc_info=True,
                )

        if event_type is not dict and hasattr(event_type, "__name__"):
            type_name = event_type.__name__
            named = self._named_handlers.get(type_name, [])
            for handler in named:
                try:
                    if isinstance(event, dict):
                        handler(event)
                    elif hasattr(event, "__iter__"):
                        handler(dict(event))
                    else:
                        handler({"data": event})
                except (ValueError, TypeError, KeyError, RuntimeError, AttributeError) as e:
                    self._error_count += 1
                    logger.error(
                        "Named handler error for %s: %s",
                        type_name,
                        e,
                        exc_info=True,
                    )

        if self._total_published > 0 and self._error_count / self._total_published > 0.05:
            logger.warning(
                "EventBus error rate %.2f%% (%d/%d)",
                self.error_rate * 100,
                self._error_count,
                self._total_published,
            )

    def publish_named(self, event_name: str, data: dict) -> None:
        self._total_published += 1
        named = self._named_handlers.get(event_name, [])
        for handler in named:
            try:
                handler(data)
            except (ValueError, TypeError, KeyError, RuntimeError, AttributeError) as e:
                self._error_count += 1
                logger.error(
                    "Named handler error for %s: %s",
                    event_name,
                    e,
                    exc_info=True,
                )

    @overload
    def enqueue(self, event: dict) -> None: ...

    @overload
    def enqueue(self, event: object) -> None: ...

    def enqueue(self, event: dict | object) -> None:
        if len(self._queue) >= self._MAX_QUEUE_SIZE:
            logger.warning("Event queue overflow (%d), dropping oldest event", len(self._queue))
            self._queue.pop(0)
        self._queue.append((time.time(), event))

    def process_queue(self) -> int:
        count = len(self._queue)
        for _, event in self._queue:
            self.publish(event)
        self._queue.clear()
        return count

    def clear_queue(self) -> None:
        self._queue.clear()

    @property
    def handler_count(self) -> int:
        return sum(len(hs) for hs in self._handlers.values()) + sum(len(hs) for hs in self._named_handlers.values())

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def error_rate(self) -> float:
        return self._error_count / max(1, self._total_published)

    def get_handlers_for(self, event_type: type) -> list[Callable]:
        return list(self._handlers.get(event_type, []))

    def reset_stats(self) -> None:
        self._error_count = 0
        self._total_published = 0
