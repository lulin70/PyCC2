"""
Squad Entity - Unit Grouping
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from pycc2.domain.entities.unit import Faction


class FormationType(Enum):
    LINE = auto()
    COLUMN = auto()
    WEDGE = auto()
    DISPERSIONED = auto()


@dataclass(slots=True)
class Squad:
    id: str
    name: str
    side: Faction
    unit_ids: list[str]
    commander_unit_id: str | None = None
    formation_type: FormationType = FormationType.LINE

    @property
    def is_alive(self) -> bool:
        return len(self.unit_ids) > 0

    @property
    def unit_count(self) -> int:
        return len(self.unit_ids)

    @property
    def average_morale(self) -> float:
        return 50.0

    def add_unit(self, unit_id: str) -> None:
        if unit_id not in self.unit_ids:
            self.unit_ids.append(unit_id)
            if self.commander_unit_id is None:
                self.commander_unit_id = unit_id

    def remove_unit(self, unit_id: str) -> None:
        if unit_id in self.unit_ids:
            self.unit_ids.remove(unit_id)
            if unit_id == self.commander_unit_id:
                self.commander_unit_id = self.unit_ids[0] if self.unit_ids else None

    def set_commander(self, unit_id: str) -> None:
        if unit_id in self.unit_ids:
            self.commander_unit_id = unit_id
