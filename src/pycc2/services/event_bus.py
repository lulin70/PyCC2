"""Event bus implementing publish/subscribe messaging for game events.

Provides typed and named event subscription, queued dispatch, and error
isolation so a single handler failure does not disrupt the event pipeline.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any, Required, TypeVar, get_type_hints, overload

E = TypeVar("E")

logger = logging.getLogger(__name__)


from pycc2.domain.interfaces import IEventPublisher


class EventBus(IEventPublisher):
    """Publish/subscribe event hub with typed and named handler dispatch."""

    _MAX_QUEUE_SIZE = 1000

    def __init__(self) -> None:
        """Initialize the event bus with empty handler registries and queue."""
        self._handlers: dict[type, list[Callable]] = defaultdict(list)
        self._named_handlers: dict[str, list[Callable[[dict], None]]] = defaultdict(list)
        self._queue: deque[tuple[float, dict | object]] = deque()
        self._error_count: int = 0
        self._total_published: int = 0
        self._registered_types: set[type] = set()
        self._handler_error_counts: dict[int, int] = {}

    @overload
    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None: ...

    @overload
    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None: ...

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """Register a handler for events of the given type."""
        self._registered_types.add(event_type)
        self._handlers[event_type].append(handler)

    @overload
    def unsubscribe(self, event_type: type[E], handler: Callable[[E], None]) -> bool: ...

    @overload
    def unsubscribe(self, event_type: type, handler: Callable[[Any], None]) -> bool: ...

    def unsubscribe(self, event_type: type, handler: Callable) -> bool:
        """Remove a previously registered handler; return whether it was removed."""
        try:
            self._handlers[event_type].remove(handler)
            return True
        except (ValueError, KeyError):
            return False

    def subscribe_to(self, event_name: str, handler: Callable[[dict], None]) -> None:
        """Register a handler for named (string-keyed) events."""
        self._named_handlers[event_name].append(handler)

    def unsubscribe_from(self, event_name: str, handler: Callable[[dict], None]) -> bool:
        """Remove a named-event handler; return whether it was removed."""
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
        """Dispatch an event synchronously to all matching typed and named handlers."""
        event_type = type(event)
        if isinstance(event, dict) and self._registered_types:
            matched = self._match_typed_dict(event, self._registered_types)
            if matched is not None:
                event_type = matched
        handlers = self._handlers.get(event_type, [])
        self._total_published += 1

        for handler in list(handlers):
            handler_id = id(handler)
            if self._handler_error_counts.get(handler_id, 0) >= 3:
                continue
            try:
                handler(event)
                self._handler_error_counts.pop(handler_id, None)
            except (ValueError, TypeError, KeyError, RuntimeError, AttributeError) as e:
                self._error_count += 1
                count = self._handler_error_counts.get(handler_id, 0) + 1
                self._handler_error_counts[handler_id] = count
                if count >= 3:
                    logger.warning(
                        "Circuit breaker: unsubscribing failing handler %s for %s (3 consecutive errors)",
                        handler,
                        event_type.__name__,
                    )
                    self.unsubscribe(event_type, handler)
                else:
                    logger.error(
                        "Handler error for %s: %s",
                        event_type.__name__,
                        e,
                        exc_info=True,
                    )

        if event_type is not dict and hasattr(event_type, "__name__"):
            type_name = event_type.__name__
            named = self._named_handlers.get(type_name, [])
            for handler in list(named):
                handler_id = id(handler)
                if self._handler_error_counts.get(handler_id, 0) >= 3:
                    continue
                try:
                    if isinstance(event, dict):
                        handler(event)
                    elif hasattr(event, "__iter__"):
                        handler(dict(event))
                    else:
                        handler({"data": event})
                    self._handler_error_counts.pop(handler_id, None)
                except (ValueError, TypeError, KeyError, RuntimeError, AttributeError) as e:
                    self._error_count += 1
                    count = self._handler_error_counts.get(handler_id, 0) + 1
                    self._handler_error_counts[handler_id] = count
                    if count >= 3:
                        logger.warning(
                            "Circuit breaker: unsubscribing failing named handler %s for %s (3 consecutive errors)",
                            handler,
                            type_name,
                        )
                        self.unsubscribe_from(type_name, handler)
                    else:
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
        """Dispatch a named event to all subscribed named handlers."""
        self._total_published += 1
        named = self._named_handlers.get(event_name, [])
        for handler in list(named):
            handler_id = id(handler)
            if self._handler_error_counts.get(handler_id, 0) >= 3:
                continue
            try:
                handler(data)
                self._handler_error_counts.pop(handler_id, None)
            except (ValueError, TypeError, KeyError, RuntimeError, AttributeError) as e:
                self._error_count += 1
                count = self._handler_error_counts.get(handler_id, 0) + 1
                self._handler_error_counts[handler_id] = count
                if count >= 3:
                    logger.warning(
                        "Circuit breaker: unsubscribing failing named handler %s for %s (3 consecutive errors)",
                        handler,
                        event_name,
                    )
                    self.unsubscribe_from(event_name, handler)
                else:
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
        """Queue an event for later processing without immediate dispatch."""
        if len(self._queue) >= self._MAX_QUEUE_SIZE:
            logger.warning("Event queue overflow (%d), dropping oldest event", len(self._queue))
            self._queue.popleft()
        self._queue.append((time.time(), event))

    def process_queue(self) -> int:
        """Publish all queued events and clear the queue; return count processed."""
        count = len(self._queue)
        for _, event in self._queue:
            self.publish(event)
        self._queue.clear()
        return count

    def clear_queue(self) -> None:
        """Drop all queued events without dispatching them."""
        self._queue.clear()

    @property
    def handler_count(self) -> int:
        """Return the total number of registered typed and named handlers."""
        return sum(len(hs) for hs in self._handlers.values()) + sum(
            len(hs) for hs in self._named_handlers.values()
        )

    @property
    def queue_size(self) -> int:
        """Return the number of events currently queued for dispatch."""
        return len(self._queue)

    @property
    def error_rate(self) -> float:
        """Return the ratio of handler errors to total published events."""
        return self._error_count / max(1, self._total_published)

    def get_handlers_for(self, event_type: type) -> list[Callable]:
        """Return a copy of the handler list registered for the given event type."""
        return list(self._handlers.get(event_type, []))

    def reset_stats(self) -> None:
        """Reset error and publish counters to zero."""
        self._error_count = 0
        self._total_published = 0
