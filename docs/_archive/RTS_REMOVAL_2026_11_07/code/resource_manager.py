"""Resource Management System - Sprint 2 Day 8 FUNC-04.

Singleton managing game resources (gold, wood, power) with thread-safe operations.
Supports resource collection, consumption, and validation for building/training.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class ResourceManager:
    """Singleton resource manager for gold, wood, and power.
    
    Thread-safe operations for collecting, consuming, and querying resources.
    Used by harvesters, builders, and UI rendering.
    
    Attributes:
        gold: Current gold amount
        wood: Current wood amount  
        power: Current power capacity (consumed by buildings)
        max_power: Maximum power capacity (increased by power plants)
    """
    
    gold: float = 0.0
    wood: float = 0.0
    power: int = 0
    max_power: int = 100
    _lock: Lock = field(default_factory=Lock, repr=False)
    _instance: ResourceManager | None = field(default=None, init=False, repr=False)
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern: ensure only one ResourceManager exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def add_gold(self, amount: float) -> None:
        """Add gold (from harvester drop-off).
        
        Args:
            amount: Gold amount to add (must be >= 0)
        
        Raises:
            ValueError: If amount is negative
        """
        if amount < 0:
            raise ValueError(f"Cannot add negative gold: {amount}")
        
        with self._lock:
            self.gold += amount
            logger.debug(f"Added {amount} gold. Total: {self.gold}")
    
    def add_wood(self, amount: float) -> None:
        """Add wood (from lumberjack drop-off).
        
        Args:
            amount: Wood amount to add (must be >= 0)
        
        Raises:
            ValueError: If amount is negative
        """
        if amount < 0:
            raise ValueError(f"Cannot add negative wood: {amount}")
        
        with self._lock:
            self.wood += amount
            logger.debug(f"Added {amount} wood. Total: {self.wood}")
    
    def consume_gold(self, amount: float) -> bool:
        """Consume gold for building/training.
        
        Args:
            amount: Gold amount to consume
        
        Returns:
            True if consumption successful (enough gold), False otherwise
        """
        with self._lock:
            if self.gold >= amount:
                self.gold -= amount
                logger.debug(f"Consumed {amount} gold. Remaining: {self.gold}")
                return True
            logger.warning(f"Not enough gold: {self.gold} < {amount}")
            return False
    
    def consume_wood(self, amount: float) -> bool:
        """Consume wood for building/training.
        
        Args:
            amount: Wood amount to consume
        
        Returns:
            True if consumption successful (enough wood), False otherwise
        """
        with self._lock:
            if self.wood >= amount:
                self.wood -= amount
                logger.debug(f"Consumed {amount} wood. Remaining: {self.wood}")
                return True
            logger.warning(f"Not enough wood: {self.wood} < {amount}")
            return False
    
    def consume_power(self, amount: int) -> bool:
        """Allocate power for building.
        
        Args:
            amount: Power amount to allocate
        
        Returns:
            True if allocation successful (power available), False otherwise
        """
        with self._lock:
            if self.power + amount <= self.max_power:
                self.power += amount
                logger.debug(f"Allocated {amount} power. Used: {self.power}/{self.max_power}")
                return True
            logger.warning(f"Not enough power: {self.power}+{amount} > {self.max_power}")
            return False
    
    def can_afford(self, gold_cost: float = 0.0, wood_cost: float = 0.0, power_cost: int = 0) -> bool:
        """Check if player can afford the cost.
        
        Args:
            gold_cost: Gold required
            wood_cost: Wood required
            power_cost: Power required
        
        Returns:
            True if all resources are sufficient, False otherwise
        """
        with self._lock:
            return (
                self.gold >= gold_cost
                and self.wood >= wood_cost
                and self.power + power_cost <= self.max_power
            )
    
    def get_resources(self) -> Dict[str, float]:
        """Get current resource amounts (thread-safe snapshot).
        
        Returns:
            Dict with keys: 'gold', 'wood', 'power', 'max_power'
        """
        with self._lock:
            return {
                "gold": self.gold,
                "wood": self.wood,
                "power": self.power,
                "max_power": self.max_power,
            }
    
    def reset(self) -> None:
        """Reset all resources to 0 (for testing/new game)."""
        with self._lock:
            self.gold = 0.0
            self.wood = 0.0
            self.power = 0
            self.max_power = 100
            logger.info("ResourceManager reset")
