from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IAIService(Protocol):
    @property
    def managed_unit_count(self) -> int: ...

    @property
    def managed_unit_ids(self) -> list[str]: ...

    def get_blackboard(self, unit_id: str) -> object | None: ...
