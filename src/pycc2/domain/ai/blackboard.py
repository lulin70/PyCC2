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
        """Return the stored value for key, or default when missing."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Store value under key, overwriting any existing entry."""
        self._data[key] = value

    def has(self, key: str) -> bool:
        """Return whether key is present in the store."""
        return key in self._data

    def remove(self, key: str) -> bool:
        """Remove key from the store, returning whether it existed."""
        if key in self._data:
            del self._data[key]
            return True
        return False

    def clear(self) -> None:
        """Remove all entries from the store."""
        self._data.clear()

    @property
    def keys(self) -> list[str]:
        """Return a list of all keys currently in the store."""
        return list(self._data.keys())

    def copy_snapshot(self) -> dict[str, Any]:
        """Return a deep copy of the current store contents."""
        return copy.deepcopy(self._data)

    def update_context(self, context: dict[str, Any]) -> None:
        """Merge context mapping into the store, overwriting existing keys."""
        self._data.update(context)

    def get_current_intent(self) -> Any:
        """Return the most recent intent stored under 'current_intent'."""
        return self._data.get("current_intent")
