"""Airdrop Supply System - C-47 supply drop mechanics."""

# PLANNED: Not yet wired into game loop — reserved for future feature

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class SupplyType(Enum):
    """Types of supply crates."""
    AMMO = auto()
    MEDIKIT = auto()
    RATIONS = auto()


@dataclass
class SupplyCrate:
    """A supply crate dropped by C-47."""
    position: tuple[float, float]
    supply_type: SupplyType
    quantity: int = 10
    picked_up: bool = False
    crate_id: str = ""
    
    def __post_init__(self):
        if not self.crate_id:
            self.crate_id = f"supply_{id(self)}_{random.randint(1000, 9999)}"
    
    def can_pickup(self, unit_pos: tuple[float, float], pickup_range: float = 1.0) -> bool:
        """Check if unit is within pickup range."""
        if self.picked_up:
            return False
        
        dx = unit_pos[0] - self.position[0]
        dy = unit_pos[1] - self.position[1]
        distance = (dx * dx + dy * dy) ** 0.5
        
        return distance <= pickup_range


@dataclass
class AirdropSupplySystem:
    """
    Airdrop supply delivery system.
    
    Features:
    - C-47 airdrop animation trigger
    - LZ (Landing Zone) supply crate spawning
    - Unit pickup mechanic
    - Multiple supply types (ammo/medkit/rations)
    
    CC2 Behavior:
    - Supplies air-dropped at designated LZs
    - Units must move to LZ to collect
    - Critical for prolonged battles
    - Visual parachute/crate animation
    """
    
    supplies: list[SupplyCrate] = field(default_factory=list)
    _active_drops: list[dict] = field(default_factory=list)
    _drop_counter: int = 0
    
    def spawn_supply_drop(
        self,
        lz_position: tuple[float, float],
        supply_type: SupplyType | None = None,
        quantity: int | None = None,
    ) -> SupplyCrate:
        """
        Spawn a new supply crate at LZ position.
        
        Args:
            lz_position: Landing zone coordinates
            supply_type: Type of supply (random if None)
            quantity: Amount of supply (random if None)
            
        Returns:
            The created SupplyCrate
        """
        if supply_type is None:
            supply_type = random.choice(list(SupplyType))
        
        if quantity is None:
            quantity = random.randint(5, 15)
        
        crate = SupplyCrate(
            position=lz_position,
            supply_type=supply_type,
            quantity=quantity,
        )
        
        self.supplies.append(crate)
        self._drop_counter += 1
        
        return crate
    
    def check_pickup(
        self,
        unit: Unit,
        pickup_range: float = 1.0,
    ) -> SupplyCrate | None:
        """
        Check if unit can pick up any nearby supply.
        
        Args:
            unit: The unit attempting pickup
            pickup_range: Maximum distance for pickup
            
        Returns:
            SupplyCrate if one is available, None otherwise
        """
        unit_pos = (
            getattr(unit.position_component, 'x', 0.0),
            getattr(unit.position_component, 'y', 0.0),
        )
        
        for supply in self.supplies:
            if supply.can_pickup(unit_pos, pickup_range):
                return supply
        
        return None
    
    def apply_supply(self, unit: Unit, crate: SupplyCrate) -> bool:
        """
        Apply supply effects to unit.
        
        Args:
            unit: Unit receiving supply
            crate: The supply crate being used
            
        Returns:
            True if successfully applied
        """
        if crate.picked_up:
            return False
        
        if crate.supply_type == SupplyType.AMMO:
            weapon = getattr(unit, 'weapon_component', None)
            if weapon:
                current = getattr(weapon, 'current_ammo', 0)
                max_ammo = getattr(weapon, 'max_ammo', 10)
                weapon.current_ammo = min(max_ammo, current + crate.quantity)
        
        elif crate.supply_type == SupplyType.MEDIKIT:
            health = getattr(unit, 'health_component', None)
            if health:
                current = getattr(health, 'current_hp', 0)
                max_hp = getattr(health, 'max_hp', 100)
                health.current_hp = min(max_hp, current + 20)
        
        elif crate.supply_type == SupplyType.RATIONS:
            morale = getattr(unit, 'morale_component', None)
            if morale:
                current = getattr(morale, 'current_morale', 50.0)
                morale.current_morale = min(100.0, current + 15.0)
        
        crate.picked_up = True
        return True
    
    def get_supplies_in_range(
        self,
        position: tuple[float, float],
        radius: float = 5.0,
    ) -> list[SupplyCrate]:
        """Get all supplies within range of a position."""
        nearby = []
        
        for supply in self.supplies:
            if supply.picked_up:
                continue
            
            dx = supply.position[0] - position[0]
            dy = supply.position[1] - position[1]
            distance = (dx * dx + dy * dy) ** 0.5
            
            if distance <= radius:
                nearby.append(supply)
        
        return nearby
    
    def remove_picked_up_supplies(self) -> int:
        """Remove all picked up supplies. Returns count removed."""
        before = len(self.supplies)
        self.supplies = [s for s in self.supplies if not s.picked_up]
        return before - len(self.supplies)
    
    def clear_all_supplies(self) -> None:
        """Remove all supplies."""
        self.supplies = []
    
    @property
    def active_supply_count(self) -> int:
        """Count of available (not picked up) supplies."""
        return sum(1 for s in self.supplies if not s.picked_up)
    
    @property
    def total_drops(self) -> int:
        return self._drop_counter
    
    def spawn_scenario_supplies(
        self,
        lz_positions: list[tuple[float, float]],
        supplies_per_lz: int = 2,
    ) -> list[SupplyCrate]:
        """
        Spawn multiple supplies for a scenario.
        
        Args:
            lz_positions: List of landing zone positions
            supplies_per_lz: Number of crates per LZ
            
        Returns:
            List of created crates
        """
        crates = []
        
        for lz_pos in lz_positions:
            for _ in range(supplies_per_lz):
                offset_x = random.uniform(-2, 2)
                offset_y = random.uniform(-2, 2)
                pos = (lz_pos[0] + offset_x, lz_pos[1] + offset_y)
                
                crate = self.spawn_supply_drop(pos)
                crates.append(crate)
        
        return crates
