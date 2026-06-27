"""Shared blackboard store for behavior tree node communication."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Blackboard:
    """Key-value store shared between behavior tree nodes and AI systems."""

    _data: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def has(self, key: str) -> bool:
        return key in self._data

    def remove(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    def clear(self) -> None:
        self._data.clear()

    @property
    def keys(self) -> list[str]:
        return list(self._data.keys())

    def copy_snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    def update_context(self, context: dict[str, Any]) -> None:
        self._data.update(context)

    def get_current_intent(self) -> Any:
        return self._data.get("current_intent")
