"""Squad Group Manager - Unit grouping and quick selection system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


@dataclass
class SquadGroup:
    """A group of units assigned to a number key."""
    group_number: int
    units: list[Unit] = field(default_factory=list)
    
    def add_units(self, units: list[Unit]) -> None:
        """Add units to this group."""
        self.units = units.copy()
    
    def clear(self) -> None:
        """Clear all units from group."""
        self.units = []
    
    @property
    def is_empty(self) -> bool:
        return len(self.units) == 0
    
    @property
    def bounds(self) -> tuple[int, int, int, int] | None:
        """Get bounding box (min_x, min_y, max_x, max_y) for minimap display."""
        if not self.units:
            return None
        
        xs = [int(u.position_component.x) for u in self.units]
        ys = [int(u.position_component.y) for u in self.units]
        
        return (min(xs), min(ys), max(xs), max(ys))


@dataclass
class SquadGroupManager:
    """
    Unit squad grouping and quick selection system.
    
    Features:
    - Ctrl+1~9: Create/update squad group
    - 1~9: Quick select all units in group
    - Visual feedback on minimap with bounding boxes
    - Persistent groups during battle
    
    CC2 Behavior:
    - Allows players to manage multiple squads efficiently
    - Groups shown on minimap as colored rectangles
    - Quick selection for rapid unit management
    """
    
    MAX_GROUPS: int = 9
    _groups: dict[int, SquadGroup] = field(init=False)
    
    def __post_init__(self):
        self._groups = {i: SquadGroup(group_number=i) for i in range(1, self.MAX_GROUPS + 1)}
    
    def create_group(
        self,
        group_num: int,
        units: list[Unit],
    ) -> bool:
        """
        Create or update a squad group.
        
        Args:
            group_num: Group number (1-9)
            units: List of units to assign
            
        Returns:
            True if successful, False if invalid group number
        """
        if not 1 <= group_num <= self.MAX_GROUPS:
            return False
        
        self._groups[group_num].add_units(units)
        return True
    
    def select_group(self, group_num: int) -> list[Unit]:
        """
        Select all units in a group.
        
        Args:
            group_num: Group number (1-9)
            
        Returns:
            List of units in the group (empty if invalid/empty)
        """
        if not 1 <= group_num <= self.MAX_GROUPS:
            return []
        
        return self._groups[group_num].units.copy()
    
    def get_group(self, group_num: int) -> SquadGroup | None:
        """Get group object by number."""
        return self._groups.get(group_num)
    
    def get_group_bounds(self, group_num: int) -> tuple[int, int, int, int] | None:
        """Get bounding box for minimap display."""
        group = self._groups.get(group_num)
        if group:
            return group.bounds
        return None
    
    def clear_group(self, group_num: int) -> bool:
        """Clear a specific group."""
        if not 1 <= group_num <= self.MAX_GROUPS:
            return False
        
        self._groups[group_num].clear()
        return True
    
    def clear_all_groups(self) -> None:
        """Clear all groups."""
        for group in self._groups.values():
            group.clear()
    
    @property
    def total_units_in_groups(self) -> int:
        """Total count of units across all groups."""
        return sum(len(g.units) for g in self._groups.values())
    
    @property
    def active_group_numbers(self) -> list[int]:
        """List of group numbers that have units assigned."""
        return [num for num, group in self._groups.items() if not group.is_empty]
    
    def remove_unit_from_all_groups(self, unit: Unit) -> None:
        """Remove a specific unit from all groups."""
        for group in self._groups.values():
            if unit in group.units:
                group.units.remove(unit)
    
    def add_unit_to_group(self, group_num: int, unit: Unit) -> bool:
        """Add single unit to existing group."""
        if not 1 <= group_num <= self.MAX_GROUPS:
            return False
        
        if unit not in self._groups[group_num].units:
            self._groups[group_num].units.append(unit)
        return True
