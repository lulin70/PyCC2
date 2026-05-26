"""Reinforcement System - Timed unit arrival mechanics."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class ReinforcementType(Enum):
    """Types of reinforcements."""
    INFANTRY = auto()
    ARMOR = auto()
    SUPPORT = auto()


@dataclass
class ReinforcementEvent:
    """A scheduled reinforcement event."""
    trigger_time: float  # Game time in seconds
    reinforcement_type: ReinforcementType
    unit_count: int = 1
    unit_template: str = "rifle_squad"
    entry_edge: str = "random"  # north/south/east/west/random
    faction: str = "allied"
    spawned: bool = False
    
    def create_units(
        self,
        spawn_pos: tuple[float, float],
    ) -> list[Unit]:
        """Create units for this reinforcement event."""
        units = []
        
        for i in range(self.unit_count):
            unit = self._create_single_unit(spawn_pos, i)
            units.append(unit)
        
        return units
    
    def _create_single_unit(self, pos: tuple[float, float], index: int):
        """Create a single unit (mock implementation)."""
        from unittest.mock import MagicMock
        
        unit = MagicMock()
        unit.name = f"{self.reinforcement_type.value}_{self.faction}_{index}"
        unit.position_component = MagicMock()
        unit.position_component.x = pos[0] + random.uniform(-1, 1)
        unit.position_component.y = pos[1] + random.uniform(-1, 1)
        unit.faction = self.faction
        
        return unit


@dataclass
class ReinforcementSystem:
    """
    Reinforcement arrival management system.
    
    Features:
    - Time-based reinforcement triggers
    - Configurable types/counts/times
    - Edge spawning (map boundaries)
    - Faction-specific reinforcements
    
    CC2 Behavior:
    - Historical accurate reinforcement schedules
    - Units enter from map edges
    - Creates dynamic battle flow changes
    """
    
    reinforcements: list[ReinforcementEvent] = field(default_factory=list)
    _game_time: float = 0.0
    
    def load_reinforcement_schedule(
        self,
        events: list[dict],
    ) -> None:
        """
        Load reinforcement schedule from config.
        
        Args:
            events: List of event dicts with keys:
                   - trigger_time (float)
                   - type (str)
                   - count (int)
                   - faction (str)
        """
        self.reinforcements = []
        
        for evt in events:
            rein = ReinforcementEvent(
                trigger_time=evt.get('trigger_time', 300.0),
                reinforcement_type=ReinforcementType[
                    evt.get('type', 'INFANTRY').upper()
                ],
                unit_count=evt.get('count', 1),
                faction=evt.get('faction', 'allied'),
                entry_edge=evt.get('edge', 'random'),
            )
            self.reinforcements.append(rein)
    
    def update(
        self,
        dt: float,
        map_edges: list[tuple[float, float]],
    ) -> list:
        """
        Check for and trigger reinforcement events.
        
        Args:
            dt: Delta time since last update
            map_edges: List of edge spawn positions
            
        Returns:
            List of newly spawned units
        """
        self._game_time += dt
        spawned_units = []
        
        for rein in self.reinforcements:
            if not rein.spawned and self._game_time >= rein.trigger_time:
                spawn_pos = self._get_spawn_position(rein, map_edges)
                
                new_units = rein.create_units(spawn_pos)
                spawned_units.extend(new_units)
                rein.spawned = True
        
        return spawned_units
    
    def _get_spawn_position(
        self,
        rein: ReinforcementEvent,
        edges: list[tuple[float, float]],
    ) -> tuple[float, float]:
        """Get spawn position based on edge preference."""
        if not edges:
            return (0.0, 0.0)
        
        if rein.entry_edge == "random":
            return random.choice(edges)
        
        edge_map = {
            'north': lambda e: min(e, key=lambda p: p[1]),
            'south': lambda e: max(e, key=lambda p: p[1]),
            'east': lambda e: max(e, key=lambda p: p[0]),
            'west': lambda e: min(e, key=lambda p: p[0]),
        }
        
        if rein.entry_edge in edge_map:
            return edge_map[rein.entry_edge](edges)
        
        return random.choice(edges)
    
    @property
    def pending_reinforcements(self) -> int:
        """Count of untriggered reinforcements."""
        return sum(1 for r in self.reinforcements if not r.spawned)
    
    @property
    def triggered_reinforcements(self) -> int:
        """Count of already triggered reinforcements."""
        return sum(1 for r in self.reinforcements if r.spawned)
    
    def add_reinforcement(
        self,
        trigger_time: float,
        rein_type: ReinforcementType,
        count: int = 1,
        faction: str = "allied",
    ) -> None:
        """Manually add a reinforcement event."""
        rein = ReinforcementEvent(
            trigger_time=trigger_time,
            reinforcement_type=rein_type,
            unit_count=count,
            faction=faction,
        )
        self.reinforcements.append(rein)


@dataclass
class VehicleEvasionAI:
    """
    Vehicle threat assessment and evasion system.
    
    Features:
    - AT threat detection within range
    - Threat level evaluation (0-1)
    - Evasion decision logic
    - Action selection (retreat/evade/sprint/none)
    
    CC2 Behavior:
    - Tanks detect anti-tank threats
    - Smart evasion behavior
    - Prevents easy tank destruction
    """
    
    THREAT_RANGE: float = 10.0  # tiles
    
    def evaluate_threat(
        self,
        vehicle_pos: tuple[float, float],
        enemy_units: list,
    ) -> float:
        """
        Evaluate AT threat level to vehicle.
        
        Returns:
            Threat level 0.0 (safe) to 1.0 (critical)
        """
        at_units = [
            u for u in enemy_units
            if getattr(u, 'has_at_weapon', False)
        ]
        
        if not at_units:
            return 0.0
        
        closest_dist = float('inf')
        
        for enemy in at_units:
            ex = getattr(enemy.position_component, 'x', 0.0) \
                if hasattr(enemy, 'position_component') else 0.0
            ey = getattr(enemy.position_component, 'y', 0.0) \
                if hasattr(enemy, 'position_component') else 0.0
            
            dx = ex - vehicle_pos[0]
            dy = ey - vehicle_pos[1]
            dist = (dx * dx + dy * dy) ** 0.5
            
            closest_dist = min(closest_dist, dist)
        
        if closest_dist > self.THREAT_RANGE:
            return 0.0
        elif closest_dist < 3.0:
            return 1.0
        else:
            return 1.0 - (closest_dist / self.THREAT_RANGE)
    
    def decide_action(self, threat_level: float) -> str:
        """
        Decide evasion action based on threat.
        
        Returns:
            Action string: retreat_fast/evade_turn/sprint_through/none
        """
        if threat_level > 0.8:
            return "retreat_fast"
        elif threat_level > 0.5:
            return "evade_turn"
        elif threat_level > 0.3:
            return "sprint_through"
        else:
            return "none"


@dataclass
class DynamicBGMSystem:
    """
    Dynamic background music system.
    
    Features:
    - Combat intensity sampling
    - Multi-track BGM (calm/tense/intense)
    - Smooth crossfade transitions
    - Automatic intensity detection
    
    CC2 Behavior:
    - Music matches battle intensity
    - Smooth transitions avoid jarring
    - Enhances immersion significantly
    """
    
    CALM_THRESHOLD: float = 0.3
    TENSE_THRESHOLD: float = 0.7
    _current_intensity: float = 0.0
    _current_track: str = "calm"
    _target_track: str | None = None
    _crossfade_progress: float = 0.0
    _crossfading: bool = False
    
    def sample_intensity(
        self,
        combat_events_per_sec: float,
    ) -> float:
        """
        Sample current combat intensity.
        
        Args:
            combat_events_per_sec: Number of combat events per second
            
        Returns:
            Normalized intensity 0.0 to 1.0
        """
        intensity = min(1.0, combat_events_per_sec / 10.0)
        return intensity
    
    def update(self, dt: float, intensity: float) -> None:
        """Update BGM state based on intensity."""
        smooth_factor = 0.1
        self._current_intensity += (intensity - self._current_intensity) * smooth_factor
        
        target = self._determine_target_track()
        
        if target != self._current_track and not self._crossfading:
            self._start_crossfade(target)
        
        if self._crossfading:
            self._update_crossfade(dt)
    
    def _determine_target_track(self) -> str:
        """Determine which track should play."""
        if self._current_intensity < self.CALM_THRESHOLD:
            return "calm"
        elif self._current_intensity < self.TENSE_THRESHOLD:
            return "tense"
        else:
            return "intense"
    
    def _start_crossfade(self, new_track: str) -> None:
        """Begin crossfade to new track."""
        self._target_track = new_track
        self._crossfading = True
        self._crossfade_progress = 0.0
    
    def _update_crossfade(self, dt: float) -> None:
        """Update crossfade progress."""
        fade_duration = 1.0  # seconds
        self._crossfade_progress += dt / fade_duration
        
        if self._crossfade_progress >= 1.0:
            self._current_track = self._target_track or self._current_track
            self._crossfading = False
            self._crossfade_progress = 0.0
            self._target_track = None
    
    @property
    def current_track(self) -> str:
        return self._current_track
    
    @property
    def intensity(self) -> float:
        return self._current_intensity
    
    @property
    is_crossfading: bool
    def get_func():
        return lambda self: self._crossfading
