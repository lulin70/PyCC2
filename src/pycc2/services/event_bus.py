from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any, Required, TypeVar, get_type_hints

E = TypeVar("E")

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Any], list[Callable[[Any], None]]] = defaultdict(list)
        self._queue: list[tuple[float, Any]] = []
        self._error_count: int = 0
        self._total_published: int = 0
        self._registered_types: set[type[Any]] = set()

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        """注册事件处理器"""
        self._registered_types.add(event_type)
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type[E], handler: Callable[[E], None]) -> bool:
        """取消注册，返回是否成功找到"""
        try:
            self._handlers[event_type].remove(handler)
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
        except Exception as e:
            logging.warning(f"TypedDict required keys introspection failed: {e}")
        rk = getattr(typed_dict_cls, "__required_keys__", None)
        return rk if rk is not None else frozenset()

    @staticmethod
    def _match_typed_dict(event: dict[Any, Any], registered: set[type[Any]]) -> type | None:
        best_match: type | None = None
        best_count = -1
        for rt in registered:
            required = EventBus._get_required_keys(rt)
            if required and required.issubset(event.keys()) and len(required) > best_count:
                best_match = rt
                best_count = len(required)
        return best_match

    def publish(self, event: Any) -> None:
        """立即同步发布事件到所有订阅者"""
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
            except Exception as e:
                self._error_count += 1
                logger.error(
                    "Handler error for %s: %s",
                    event_type.__name__,
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

    def enqueue(self, event: Any) -> None:
        """将事件加入队列(延迟处理)，自动附加timestamp"""
        self._queue.append((time.time(), event))

    def process_queue(self) -> int:
        """处理队列中所有事件，返回处理数量"""
        count = len(self._queue)
        for _, event in self._queue:
            self.publish(event)
        self._queue.clear()
        return count

    def clear_queue(self) -> None:
        """清空队列"""
        self._queue.clear()

    @property
    def handler_count(self) -> int:
        """已注册的handler总数"""
        return sum(len(hs) for hs in self._handlers.values())

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def error_rate(self) -> float:
        """异常率 = _error_count / max(1, _total_published)"""
        return self._error_count / max(1, self._total_published)

    def get_handlers_for(self, event_type: type[E]) -> list[Callable[[E], None]]:
        """获取某事件类型的所有handler(用于调试)"""
        return list(self._handlers.get(event_type, []))

    def reset_stats(self) -> None:
        """重置统计计数器"""
        self._error_count = 0
        self._total_published = 0
