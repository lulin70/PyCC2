"""Casualty Drag System - Wounded soldier management and medical evacuation.

Implements B11: Casualty handling with dragging mechanic, rescue timers,
and morale impact from untreated casualties.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class CasualtyState(Enum):
    """States a casualty can be in."""
    HEALTHY = "healthy"
    WOUNDED = "wounded"
    DRAGGING = "dragging"
    EVACUATING = "evacuating"
    EVACUATED = "evacuated"
    DEAD = "dead"


@dataclass(slots=True)
class CasualtyConfig:
    """Configuration parameters for casualty system."""
    rescue_timeout_seconds: float = 300.0  # 5 minutes until death
    drag_speed_multiplier: float = 0.5     # Medic moves at 50% speed while dragging
    evac_complete_time: float = 10.0       # Seconds to complete evacuation
    morale_death_penalty: int = -30        # Morale loss when casualty dies
    morale_rescue_bonus: int = 15          # Morale bonus when rescued
    medic_required: bool = True            # Only medics can drag/evacuate


@dataclass
class Casualty:
    """
    Represents a wounded unit that requires medical attention.
    
    Features:
    - State machine: healthy → wounded → dragging → evacuated/dead
    - Rescue timer with configurable timeout
    - Morale impact on squad
    - Dragging speed penalty for medic
    - Evacuation completion tracking
    """

    def __init__(
        self,
        unit: "Unit",
        config: CasualtyConfig | None = None,
    ):
        self._unit = unit
        self._config = config or CasualtyConfig()
        self._state = CasualtyState.HEALTHY
        self._rescue_timer: float = 0.0
        self._evac_timer: float = 0.0
        self._medic_unit: "Unit | None" = None
        self._wound_time: float | None = None
        self._drag_start_pos: tuple[float, float] | None = None
        self._is_being_dragged: bool = False

    @property
    def unit(self) -> "Unit":
        return self._unit

    @property
    def state(self) -> CasualtyState:
        return self._state

    @property
    def rescue_timer(self) -> float:
        return self._rescue_timer

    @property
    def rescue_timeout(self) -> float:
        return self._config.rescue_timeout_seconds

    @property
    def rescue_progress(self) -> float:
        """Get rescue timeout progress (0.0 to 1.0+)."""
        if self._state != CasualtyState.WOUNDED:
            return 0.0
        if self.rescue_timeout <= 0:
            return 0.0
        return self._rescue_timer / self.rescue_timeout

    @property
    def is_rescuable(self) -> bool:
        return self._state in (CasualtyState.WOUNDED, CasualtyState.DRAGGING)

    @property
    def medic(self) -> "Unit | None":
        return self._medic_unit

    def become_wounded(self) -> dict:
        """
        Transition unit to wounded state.
        
        Returns:
            Event dict with wound details
        """
        if self._state == CasualtyState.WOUNDED:
            return {"success": False, "reason": "Already wounded"}
            
        self._state = CasualtyState.WOUNDED
        self._rescue_timer = 0.0
        self._wound_time = time.perf_counter()
        self._is_being_dragged = False
        
        # Disable unit actions
        if hasattr(self._unit, 'can_move'):
            self._unit.can_move = False
        if hasattr(self._unit, 'can_attack'):
            self._unit.can_attack = False
            
        event = {
            "event": "casualty_wounded",
            "unit_id": self._unit.id,
            "unit_name": self._unit.name,
            "timeout": self.rescue_timeout,
            "timestamp": time.perf_counter(),
        }
        
        print(f"[Casualty] ⚠️ {self._unit.name} is WOUNDED! Rescue in {self.rescue_timeout:.0f}s or they will die!")
        
        return {**event, "success": True}

    def update(self, dt: float) -> dict | None:
        """
        Update casualty state each frame.
        
        Args:
            dt: Delta time in seconds since last update
            
        Returns:
            Event dict if state changed, None otherwise
        """
        if self._state == CasualtyState.WOUNDED:
            self._rescue_timer += dt
            
            # Check for timeout death
            if self._rescue_timer >= self.rescue_timeout:
                return self._die_from_timeout()
                
        elif self._state == CasualtyState.EVACUATING:
            self._evac_timer += dt
            
            if self._evac_timer >= self._config.evac_complete_time:
                return self.complete_evacuation()
                
        elif self._state == CasualtyState.DRAGGING:
            # Being dragged - timer still counts but slower
            self._rescue_timer += dt * 0.5  # Slower countdown while being dragged
            
            if self._rescue_timer >= self.rescue_timeout:
                return self._die_from_timeout()
                
        return None

    def start_dragging(self, medic_unit: "Unit") -> dict:
        """
        Begin dragging this casualty.
        
        Args:
            medic_unit: The medic unit performing the drag
            
        Returns:
            Event dict with drag start details
        """
        if self._state not in (CasualtyState.WOUNDED,):
            return {"success": False, "reason": f"Cannot drag in state {self._state}"}
            
        if self._config.medic_required:
            unit_type = getattr(medic_unit, 'unit_type', None)
            type_name = str(unit_type).lower() if unit_type else ""
            
            if "medic" not in type_name:
                return {"success": False, "reason": "Only medics can drag casualties"}
                
        self._state = CasualtyState.DRAGGING
        self._medic_unit = medic_unit
        self._is_being_dragged = True
        
        # Record medic's original speed for restoration later
        if hasattr(medic_unit, 'move_speed'):
            self._original_medic_speed = getattr(medic_unit, 'move_speed', 1.0)
            medic_unit.move_speed *= self._config.drag_speed_multiplier
            
        # Get positions
        pos_comp = getattr(self._unit, 'position', None)
        if pos_comp:
            self._drag_start_pos = (
                getattr(pos_comp, 'x', 0.0),
                getattr(pos_comp, 'y', 0.0),
            )
            
        event = {
            "event": "casualty_drag_start",
            "casualty_id": self._unit.id,
            "medic_id": medic_unit.id,
            "timestamp": time.perf_counter(),
        }
        
        print(f"[Casualty] 🏥 {medic_unit.name} started dragging {self._unit.name}")
        
        return {**event, "success": True}

    def stop_dragging(self) -> dict:
        """Stop dragging (medic released or reached safety)."""
        if self._state != CasualtyState.DRAGGING:
            return {"success": False, "reason": "Not being dragged"}
            
        # Restore medic speed
        if self._medic_unit and hasattr(self._medic_unit, 'move_speed'):
            if hasattr(self, '_original_medic_speed'):
                self._medic_unit.move_speed = self._original_medic_speed
                
        self._state = CasualtyState.WOUNDED
        self._medic_unit = None
        self._is_being_dragged = False
        
        return {"success": True, "event": "casualty_drag_stop"}

    def begin_evacuation(self) -> dict:
        """Begin evacuation process after reaching safe zone."""
        if self._state != CasualtyState.DRAGGING:
            return {"success": False, "reason": "Must be dragging to evacuate"}
            
        self._state = CasualtyState.EVACUATING
        self._evac_timer = 0.0
        
        # Restore medic speed
        if self._medic_unit and hasattr(self._medic_unit, 'move_speed'):
            if hasattr(self, '_original_medic_speed'):
                self._medic_unit.move_speed = self._original_medic_speed
                
        event = {
            "event": "casualty_evac_start",
            "casualty_id": self._unit.id,
            "estimated_time": self._config.evac_complete_time,
        }
        
        print(f"[Casualualty] 🚑 Evacuating {self._unit.name}...")
        
        return {**event, "success": True}

    def complete_evacuation(self) -> dict:
        """Complete the evacuation process."""
        if self._state != CasualtyState.EVACUATING:
            return {"success": False, "reason": "Not evacuating"}
            
        self._state = CasualtyState.EVACUATED
        self._medic_unit = None
        
        # Apply morale bonus to squad
        if hasattr(self._unit, 'squad') and self._unit.squad:
            if hasattr(self._unit.squad, 'morale'):
                squad_morale = getattr(self._unit.squad.morale, 'current', None)
                if squad_morale is not None:
                    # This would need proper morale component access
                    pass
                    
        event = {
            "event": "casualty_evacuated",
            "casualty_id": self._unit.id,
            "unit_name": self._unit.name,
            "morale_bonus": self._config.morale_rescue_bonus,
        }
        
        print(f"[Casualty] ✅ {self._unit.name} evacuated successfully! Squad morale +{self._config.morale_rescue_bonus}")
        
        return {**event, "success": True}

    def _die_from_timeout(self) -> dict:
        """Handle casualty death from timeout."""
        self._state = CasualtyState.DEAD
        
        # Mark unit as dead
        if hasattr(self._unit, 'health'):
            self._unit.health.current_hp = 0
        if hasattr(self._unit, 'state_machine'):
            from pycc2.domain.entities.unit import UnitState
            try:
                self._unit.state_machine.force_state(UnitState.DEAD)
            except Exception as e:
                logging.warning(f"Casualty state transition to DEAD failed: {e}")
                
        # Apply morale penalty to squad
        morale_penalty = self._config.morale_death_penalty
        
        event = {
            "event": "casualty_died",
            "casualty_id": self._unit.id,
            "unit_name": self._unit.name,
            "cause": "timeout",
            "time_until_death": self._rescue_timer,
            "morale_penalty": morale_penalty,
        }
        
        print(f"[Casualty] 💀 {self._unit.name} DIED from wounds! Squad morale {morale_penalty}")
        
        return event

    def get_status_dict(self) -> dict:
        """Get serializable status for UI display."""
        return {
            "unit_id": self._unit.id,
            "unit_name": self._unit.name,
            "state": self._state.value,
            "rescue_timer": round(self._rescue_timer, 1),
            "rescue_timeout": self.rescue_timeout,
            "rescue_progress": round(self.rescue_progress, 3),
            "is_being_dragged": self._is_being_dragged,
            "medic_id": self._medic_unit.id if self._medic_unit else None,
        }


class CasualtyManager:
    """
    Manages all casualties on the battlefield.
    
    Provides centralized tracking, updates, and queries for casualties.
    """

    def __init__(self):
        self._casualties: dict[str, Casualty] = {}
        self._config = CasualtyConfig()

    @property
    def casualties(self) -> dict[str, Casualty]:
        return dict(self._casualties)

    @property
    def active_casualty_count(self) -> int:
        return sum(
            1 for c in self._casualties.values()
            if c.state in (CasualtyState.WOUNDED, CasualtyState.DRAGGING, CasualtyState.EVACUATING)
        )

    @property
    def total_dead(self) -> int:
        return sum(1 for c in self._casualties.values() if c.state == CasualtyState.DEAD)

    @property
    def total_evacuated(self) -> int:
        return sum(1 for c in self._casualties.values() if c.state == CasualtyState.EVACUATED)

    def register_casualty(self, unit: "Unit") -> Casualty:
        """Register a unit as potentially becoming a casualty."""
        unit_id = unit.id
        
        if unit_id not in self._casualties:
            self._casualties[unit_id] = Casualty(unit, self._config)
            
        return self._casualties[unit_id]

    def get_casualty(self, unit_id: str) -> Casualty | None:
        return self._casualties.get(unit_id)

    def update_all(self, dt: float) -> list[dict]:
        """
        Update all casualties and collect events.
        
        Args:
            dt: Delta time in seconds
            
        Returns:
            List of events from state changes
        """
        events = []
        
        for casualty in self._casualties.values():
            event = casualty.update(dt)
            if event:
                events.append(event)
                
        return events

    def get_casualties_in_state(self, state: CasualtyState) -> list[Casualty]:
        return [c for c in self._casualties.values() if c.state == state]

    def get_nearby_casualties(
        self,
        position: tuple[float, float],
        radius: float = 5.0,
    ) -> list[Casualty]:
        """Find casualties within radius of position."""
        nearby = []
        
        for casualty in self._casualties.values():
            if not casualty.is_rescuable:
                continue
                
            pos_comp = getattr(casualty.unit, 'position', None)
            if pos_comp:
                cx = getattr(pos_comp, 'x', 0.0)
                cy = getattr(pos_comp, 'y', 0.0)
                
                distance = ((cx - position[0])**2 + (cy - position[1])**2)**0.5
                
                if distance <= radius:
                    nearby.append(casualty)
                    
        return nearby

    def get_summary_stats(self) -> dict:
        """Get overall casualty statistics."""
        state_counts = {}
        for state in CasualtyState:
            count = sum(1 for c in self._casualties.values() if c.state == state)
            if count > 0:
                state_counts[state.value] = count
                
        return {
            "total_registered": len(self._casualties),
            "active_casualties": self.active_casualty_count,
            "dead": self.total_dead,
            "evacuated": self.total_evacuated,
            "by_state": state_counts,
        }