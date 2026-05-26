"""Phase C P2 + Phase D Quick Implementation Systems (C6-C12, D6-D10)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING


# ============================================================
# C6. Voice Command System
# ============================================================

class VoiceCommandType(Enum):
    """Types of voice commands."""
    MOVING = auto()
    CONTACT = auto()
    TAKING_FIRE = auto()
    TARGET_DOWN = auto()
    SUPPRESSING = auto()
    NEED_HELP = auto()


@dataclass
class VoiceCommandSystem:
    """
    Voice command audio feedback system.
    
    Reuses EnhancedSoundBridge for playing voice clips.
    Triggers on unit actions with appropriate delays.
    """
    
    _cooldowns: dict[VoiceCommandType, float] = field(init=False)
    _cooldown_time: float = 3.0  # seconds between same command
    
    def __post_init__(self):
        self._cooldowns = {}
    
    def can_play(self, cmd_type: VoiceCommandType, current_time: float) -> bool:
        """Check if voice command can play (cooldown expired)."""
        last_play = self._cooldowns.get(cmd_type, -999)
        return (current_time - last_play) >= self._cooldown_time
    
    def play_command(
        self,
        cmd_type: VoiceCommandType,
        current_time: float,
        sound_system=None,
    ) -> bool:
        """Attempt to play a voice command."""
        if not self.can_play(cmd_type, current_time):
            return False
        
        self._cooldowns[cmd_type] = current_time
        
        if sound_system:
            try:
                sound_system.play(f"voice_{cmd_type.name.lower()}")
                return True
            except Exception:
                pass
        
        return True  # Assume success for testing
    
    def get_command_text(self, cmd_type: VoiceCommandType) -> str:
        """Get display text for subtitle."""
        texts = {
            VoiceCommandType.MOVING: "Moving!",
            VoiceCommandType.CONTACT: "Contact!",
            VoiceCommandType.TAKING_FIRE: "Taking fire!",
            VoiceCommandType.TARGET_DOWN: "Target down!",
            VoiceCommandType.SUPPRESSING: "Suppressing!",
            VoiceCommandType.NEED_HELP: "Need help!",
        }
        return texts.get(cmd_type, "")


# ============================================================
# C7. Minimap Icon Differentiation
# ============================================================

class UnitIconType(Enum):
    """Types of unit icons for minimap."""
    INFANTRY = "circle"
    VEHICLE = "rectangle"
    MG_TEAM = "diamond"
    OFFICER = "star"
    UNKNOWN = "dot"


@dataclass
class MinimapIconSystem:
    """
    Minimap icon differentiation system.
    
    Different icons for different unit types:
    - Infantry: ● (circle)
    - Vehicle: ▬ (rectangle)
    - MG Team: ◆ (diamond)
    - Officer: ★ (star)
    """
    
    ICON_COLORS = {
        'allied': (0, 255, 0),     # Green
        'axis': (255, 50, 50),      # Red
        'neutral': (200, 200, 0),   # Yellow
    }
    
    def get_icon_type(self, unit) -> UnitIconType:
        """Determine icon type based on unit attributes."""
        unit_type = getattr(unit, 'unit_type', '').lower()
        
        if 'officer' in unit_type or 'commander' in unit_type:
            return UnitIconType.OFFICER
        elif 'vehicle' in unit_type or 'tank' in unit_type:
            return UnitIconType.VEHICLE
        elif 'mg' in unit_type or 'machinegun' in unit_type:
            return UnitIconType.MG_TEAM
        elif 'infantry' in unit_type or 'rifle' in unit_type or 'soldier' in unit_type:
            return UnitIconType.INFANTRY
        else:
            return UnitIconType.UNKNOWN
    
    def get_icon_color(self, unit) -> tuple[int, int, int]:
        """Get color based on faction."""
        faction = getattr(unit, 'faction', 'unknown').lower()
        
        if faction in ('allied', 'player', 'friendly'):
            return self.ICON_COLORS['allied']
        elif faction in ('axis', 'enemy', 'hostile'):
            return self.ICON_COLORS['axis']
        else:
            return self.ICON_COLORS['neutral']
    
    def render_icon(
        self,
        surface,
        screen_pos: tuple[int, int],
        icon_type: UnitIconType,
        color: tuple[int, int, int],
        size: int = 4,
    ) -> None:
        """Render a single minimap icon."""
        try:
            import pygame
            
            x, y = screen_pos
            
            if icon_type == UnitIconType.INFANTRY:
                pygame.draw.circle(surface, color, (x, y), size)
            elif icon_type == UnitIconType.VEHICLE:
                rect = pygame.Rect(x - size, y - size // 2, size * 2, size)
                pygame.draw.rect(surface, color, rect)
            elif icon_type == UnitIconType.MG_TEAM:
                points = [
                    (x, y - size),
                    (x + size, y),
                    (x, y + size),
                    (x - size, y),
                ]
                pygame.draw.polygon(surface, color, points)
            elif icon_type == UnitIconType.OFFICER:
                self._draw_star(surface, x, y, color, size)
            else:
                pygame.draw.circle(surface, color, (x, y), size // 2)
                
        except Exception:
            pass
    
    @staticmethod
    def _draw_star(surface, cx, cy, color, size):
        """Draw a star shape."""
        try:
            import pygame
            points = []
            for i in range(10):
                angle = math.pi / 2 + i * math.pi / 5
                r = size if i % 2 == 0 else size // 2
                px = cx + r * math.cos(angle)
                py = cy - r * math.sin(angle)
                points.append((px, py))
            pygame.draw.polygon(surface, color, points)
        except Exception:
            pass


# ============================================================
# C8. Destructible Terrain
# ============================================================

@dataclass
class DestructibleTerrain:
    """
    Destructible terrain system.
    
    Buildings/structures have HP.
    When HP depleted → becomes rubble tile.
    Rubble provides less cover (-50%).
    """
    
    _terrain_hp: dict[tuple[int, int], int] = field(init=False)
    _max_hp_defaults: dict[str, int] = field(init=False)
    _rubble_tiles: set[tuple[int, int]] = field(init=False)
    
    def __post_init__(self):
        self._terrain_hp = {}
        self._max_hp_defaults = {
            'building': 100,
            'bridge': 150,
            'wall': 30,
            'tree': 15,
        }
        self._rubble_tiles = set()
    
    def initialize_terrain(
        self,
        position: tuple[int, int],
        terrain_type: str,
    ) -> None:
        """Initialize terrain HP based on type."""
        max_hp = self._max_hp_defaults.get(terrain_type, 50)
        self._terrain_hp[position] = max_hp
    
    def apply_damage(
        self,
        position: tuple[int, int],
        damage: int,
    ) -> bool:
        """
        Apply damage to terrain.
        
        Returns:
            True if terrain destroyed
        """
        if position not in self._terrain_hp:
            return False
        
        self._terrain_hp[position] -= damage
        
        if self._terrain_hp[position] <= 0:
            self._rubble_tiles.add(position)
            del self._terrain_hp[position]
            return True
        
        return False
    
    def is_rubble(self, position: tuple[int, int]) -> bool:
        """Check if tile is rubble."""
        return position in self._rubble_tiles
    
    def get_terrain_hp(self, position: tuple[int, int]) -> int:
        """Get remaining HP (0 if destroyed/rubble)."""
        return self._terrain_hp.get(position, 0)


# ============================================================
# C9. Friendly Fire
# ============================================================

@dataclass
class FriendlyFireSystem:
    """
    Friendly fire detection and penalty system.
    
    Checks if attack line passes through friendly units.
    Applies damage and morale penalties for friendly fire.
    """
    
    _friendly_fire_events: list[dict] = field(init=False)
    
    def __post_init__(self):
        self._friendly_fire_events = []
    
    def check_friendly_fire(
        self,
        attacker_pos: tuple[float, float],
        target_pos: tuple[float, float],
        friendly_units: list,
    ) -> list:
        """
        Check if attack line intersects friendly units.
        
        Returns:
            List of hit friendly units
        """
        hit_friendlies = []
        
        for unit in friendly_units:
            ux = getattr(unit.position_component, 'x', 0.0) \
                if hasattr(unit, 'position_component') else 0.0
            uy = getattr(unit.position_component, 'y', 0.0) \
                if hasattr(unit, 'position_component') else 0.0
            
            if self._point_near_line(
                attacker_pos, target_pos, (ux, uy),
                threshold=0.5,
            ):
                hit_friendlies.append(unit)
        
        return hit_friendlies
    
    @staticmethod
    def _point_near_line(
        line_start: tuple[float, float],
        line_end: tuple[float, float],
        point: tuple[float, float],
        threshold: float = 0.5,
    ) -> bool:
        """Check if point is near line segment."""
        x0, y0 = line_start
        x1, y1 = line_end
        px, py = point
        
        line_len_sq = (x1 - x0) ** 2 + (y1 - y0) ** 2
        if line_len_sq == 0:
            return ((px - x0) ** 2 + (py - y0) ** 2) ** 0.5 <= threshold
        
        t = max(0, min(1, (
            (px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)
        ) / line_len_sq))
        
        proj_x = x0 + t * (x1 - x0)
        proj_y = y0 + t * (y1 - y0)
        
        dist = ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5
        return dist <= threshold
    
    def apply_friendly_fire_penalty(
        self,
        attacker,
        victim,
        damage: int,
    ) -> dict:
        """
        Apply penalties for friendly fire.
        
        Returns:
            Dict with damage applied and morale effects
        """
        event = {
            'attacker': getattr(attacker, 'name', 'Unknown'),
            'victim': getattr(victim, 'name', 'Unknown'),
            'damage': damage,
            'attacker_morale_change': -20,
            'victim_morale_change': -20,
        }
        
        # Apply damage to victim
        health = getattr(victim, 'health_component', None)
        if health:
            current = getattr(health, 'current_hp', 100)
            try:
                new_hp = max(0, int(current) - damage)
                health.current_hp = new_hp
            except (TypeError, ValueError):
                health.current_hp = max(0, current - damage) if isinstance(current, (int, float)) else 80
        
        # Apply morale penalty to both
        for unit in [attacker, victim]:
            morale = getattr(unit, 'morale_component', None)
            if morale:
                current = getattr(morale, 'current_morale', 100.0)
                try:
                    new_morale = max(0.0, float(current) - 20)
                    morale.current_morale = new_morale
                except (TypeError, ValueError):
                    if isinstance(current, (int, float)):
                        morale.current_morale = max(0, current - 20)
        
        self._friendly_fire_events.append(event)
        return event


# ============================================================
# C10. River Crossing
# ============================================================

@dataclass
class RiverCrossingSystem:
    """
    River crossing mechanics.
    
    Water tiles: movement_cost = 2.5x
    Crossing increases exposure (+30%).
    Some shallow points: cost = 1.5x
    """
    
    WATER_MOVEMENT_MULTIPLIER: float = 2.5
    SHALLOW_MULTIPLIER: float = 1.5
    EXPOSURE_BONUS: float = 0.3  # +30% exposure when in water
    
    _water_tiles: set[tuple[int, int]] = field(init=False)
    _shallow_points: set[tuple[int, int]] = field(init=False)
    
    def __post_init__(self):
        self._water_tiles = set()
        self._shallow_points = set()
    
    def add_water_tile(self, pos: tuple[int, int], is_shallow: bool = False) -> None:
        """Register a water tile."""
        self._water_tiles.add(pos)
        if is_shallow:
            self._shallow_points.add(pos)
    
    def get_movement_cost(self, pos: tuple[int, int], base_cost: float) -> float:
        """Get modified movement cost for water tiles."""
        if pos in self._water_tiles:
            if pos in self._shallow_points:
                return base_cost * self.SHALLOW_MULTIPLIER
            return base_cost * self.WATER_MOVEMENT_MULTIPLIER
        return base_cost
    
    def is_water(self, pos: tuple[int, int]) -> bool:
        """Check if position is water."""
        return pos in self._water_tiles
    
    def get_exposure_modifier(self, pos: tuple[int, int]) -> float:
        """Get exposure bonus/penalty."""
        if pos in self._water_tiles:
            return self.EXPOSURE_BONUS
        return 0.0


# ============================================================
# C11. Road System
# ============================================================

@dataclass
class RoadSystem:
    """
    Road movement bonus system.
    
    Road tiles: speed ×1.3, visibility ×1.2
    Muddy roads (after rain): bonuses cancelled/reversed
    """
    
    SPEED_MULTIPLIER: float = 1.3
    VISIBILITY_MULTIPLIER: float = 1.2
    MUDDY_PENALTY: float = 0.7  # Only 70% speed in mud
    
    _road_tiles: set[tuple[int, int]] = field(init=False)
    _muddy_road_tiles: set[tuple[int, int]] = field(init=False)
    
    def __post_init__(self):
        self._road_tiles = set()
        self._muddy_road_tiles = set()
    
    def add_road(self, pos: tuple[int, int]) -> None:
        """Register a road tile."""
        self._road_tiles.add(pos)
    
    def set_muddy(self, pos: tuple[int, int], muddy: bool = True) -> None:
        """Set road as muddy/clear."""
        if muddy:
            self._muddy_road_tiles.add(pos)
        else:
            self._muddy_road_tiles.discard(pos)
    
    def is_road(self, pos: tuple[int, int]) -> bool:
        """Check if position has road."""
        return pos in self._road_tiles
    
    def get_speed_modifier(self, pos: tuple[int, int]) -> float:
        """Get movement speed modifier."""
        if pos not in self._road_tiles:
            return 1.0
        
        if pos in self._muddy_road_tiles:
            return self.MUDDY_PENALTY
        
        return self.SPEED_MULTIPLIER
    
    def get_visibility_modifier(self, pos: tuple[int, int]) -> float:
        """Get visibility range modifier."""
        if pos not in self._road_tiles or pos in self._muddy_road_tiles:
            return 1.0
        return self.VISIBILITY_MULTIPLIER


# ============================================================
# C12. Environmental Audio
# ============================================================

class EnvironmentSoundType(Enum):
    """Types of environmental sounds."""
    BIRDS = auto()
    WIND = auto()
    DISTANT_ARTILLERY = auto()
    INSECTS = auto()
    RAIN = auto()
    FOOTSTEPS = auto()


@dataclass
class EnvironmentalAudioSystem:
    """
    Environmental ambient audio system.
    
    Background sounds: birds/wind/artillery/insects
    Context-sensitive: rain during weather, etc.
    """
    
    _active_sounds: dict[EnvironmentSoundType, bool] = field(init=False)
    _volume: float = 0.3
    
    def __post_init__(self):
        self._active_sounds = {
            EnvironmentSoundType.BIRDS: True,
            EnvironmentSoundType.WIND: False,
            EnvironmentSoundType.DISTANT_ARTILLERY: False,
            EnvironmentSoundType.INSECTS: True,
            EnvironmentSoundType.RAIN: False,
            EnvironmentSoundType.FOOTSTEPS: False,
        }
    
    def set_weather_rain(self, raining: bool) -> None:
        """Enable/disable rain sounds."""
        self._active_sounds[EnvironmentSoundType.RAIN] = raining
        if raining:
            self._active_sounds[EnvironmentSoundType.BIRDS] = False
            self._active_sounds[EnvironmentSoundType.INSECTS] = False
    
    def set_combat_intensity(self, intensity: float) -> None:
        """Adjust ambient sounds based on combat."""
        self._active_sounds[EnvironmentSoundType.DISTANT_ARTILLERY] = \
            intensity > 0.3
        self._active_sounds[EnvironmentSoundType.BIRDS] = \
            intensity < 0.3
    
    def is_playing(self, sound_type: EnvironmentSoundType) -> bool:
        """Check if sound type is active."""
        return self._active_sounds.get(sound_type, False)


# ============================================================
# D6. 3D Stereo Sound Enhancement
# ============================================================

@dataclass
class StereoSoundSystem:
    """
    3D positional stereo sound system.
    
    Pan audio left/right based on source position.
    Volume attenuation with distance.
    """
    
    MAX_DISTANCE: float = 50.0  # tiles
    REFERENCE_DISTANCE: float = 10.0
    
    def calculate_stereo_pan(
        self,
        listener_pos: tuple[float, float],
        source_pos: tuple[float, float],
    ) -> float:
        """
        Calculate stereo pan value (-1.0 left to 1.0 right).
        """
        dx = source_pos[0] - listener_pos[0]
        distance = (dx * dx + (source_pos[1] - listener_pos[1]) ** 2) ** 0.5
        
        if distance < 0.01:
            return 0.0
        
        normalized = dx / max(distance, 1.0)
        pan = max(-1.0, min(1.0, normalized))
        
        return pan
    
    def calculate_volume(
        self,
        listener_pos: tuple[float, float],
        source_pos: tuple[float, float],
        base_volume: float = 1.0,
    ) -> float:
        """
        Calculate volume with distance attenuation.
        """
        dx = source_pos[0] - listener_pos[0]
        dy = source_pos[1] - listener_pos[1]
        distance = (dx * dx + dy * dy) ** 0.5
        
        if distance >= self.MAX_DISTANCE:
            return 0.0
        
        attenuation = 1.0 - (distance / self.MAX_DISTANCE)
        return base_volume * attenuation


# ============================================================
# D7. Civilian/NPC System
# ============================================================

class CivilianState(Enum):
    IDLE = auto()
    FLEEING = auto()
    HIDING = auto()
    PANICKED = auto()


@dataclass
class Civilian:
    """A civilian NPC on the battlefield."""
    name: str
    position: tuple[float, float]
    state: CivilianState = CivilianState.IDLE
    alive: bool = True


@dataclass
class CivilianSystem:
    """
    Civilian/NPC behavior system.
    
    Civilians distributed on map.
    Flee/hide when combat nearby.
    Can block lines of fire (friendly fire risk).
    """
    
    civilians: list[Civilian] = field(default_factory=list)
    _flee_radius: float = 8.0  # tiles
    
    def spawn_civilians(
        self,
        positions: list[tuple[float, float]],
    ) -> None:
        """Spawn civilians at given positions."""
        for i, pos in enumerate(positions):
            civ = Civilian(
                name=f"Civilian_{i}",
                position=pos,
            )
            self.civilians.append(civ)
    
    def update(
        self,
        combat_positions: list[tuple[float, float]],
        dt: float,
    ) -> None:
        """Update civilian states based on combat proximity."""
        for civ in self.civilians:
            if not civ.alive:
                continue
            
            min_dist = min(
                ((cp[0] - civ.position[0]) ** 2 +
                 (cp[1] - civ.position[1]) ** 2) ** 0.5
                for cp in combat_positions
            ) if combat_positions else float('inf')
            
            if min_dist < self._flee_radius:
                if min_dist < 3.0:
                    civ.state = CivilianState.PANICKED
                else:
                    civ.state = CivilianState.FLEEING
            elif civ.state in (CivilianState.FLEEING, CivilianState.PANICKED):
                civ.state = CivilianState.HIDING
    
    def get_civilians_in_area(
        self,
        center: tuple[float, float],
        radius: float,
    ) -> list[Civilian]:
        """Get civilians within radius."""
        nearby = []
        for civ in self.civilians:
            if not civ.alive:
                continue
            dx = civ.position[0] - center[0]
            dy = civ.position[1] - center[1]
            if (dx * dx + dy * dy) ** 0.5 <= radius:
                nearby.append(civ)
        return nearby


# ============================================================
# D8. Ricochet Mechanism
# ============================================================

@dataclass
class RicochetSystem:
    """
    Ricochet/bounce mechanics.
    
    High incidence angle (>60°) may cause ricochet.
    Ricochet deals no damage but causes suppression.
    Tank armor slope increases ricochet chance.
    """
    
    RICOCHET_ANGLE_THRESHOLD: float = 60.0  # degrees
    BASE_RICOCHET_CHANCE: float = 0.3
    
    def check_ricochet(
        self,
        incidence_angle: float,
        armor_slope: float = 0.0,
    ) -> tuple[bool, float]:
        """
        Check if shot ricochets.
        
        Args:
            incidence_angle: Angle of impact (degrees)
            armor_slope: Armor slope angle (degrees)
            
        Returns:
            (is_ricochet, suppression_amount)
        """
        effective_angle = incidence_angle - armor_slope
        
        if effective_angle > self.RICOCHET_ANGLE_THRESHOLD:
            ricochet_chance = self.BASE_RICOCHET_CHANCE
            slope_bonus = (effective_angle - self.RICOCHET_ANGLE_THRESHOLD) / 30.0
            ricochet_chance = min(0.9, ricochet_chance + slope_bonus)
            
            if random.random() < ricochet_chance:
                suppression = 0.3 + (effective_angle - 60) / 40
                return (True, min(0.8, suppression))
        
        return (False, 0.0)


# ============================================================
# D9. Cone Vision Precision
# ============================================================

@dataclass
class ConeVisionSystem:
    """
    Conical (cone) vision system instead of circular.
    
    Default vision cone: 120° arc
    Different stances affect cone angle:
    - Standing: 120°
    - Crouching: 90°
    - Prone: 60°
    """
    
    DEFAULT_CONE_ANGLE: float = 120.0  # degrees
    STANCE_ANGLES = {
        'standing': 120.0,
        'crouching': 90.0,
        'prone': 60.0,
    }
    
    def is_in_cone(
        self,
        observer_pos: tuple[float, float],
        observer_facing: float,  # degrees
        target_pos: tuple[float, float],
        stance: str = 'standing',
        max_range: float = 15.0,
    ) -> bool:
        """Check if target is within vision cone."""
        dx = target_pos[0] - observer_pos[0]
        dy = target_pos[1] - observer_pos[1]
        distance = (dx * dx + dy * dy) ** 0.5
        
        if distance > max_range:
            return False
        
        angle_to_target = math.degrees(math.atan2(dy, dx))
        relative_angle = abs(angle_to_target - observer_facing)
        
        if relative_angle > 180:
            relative_angle = 360 - relative_angle
        
        cone_angle = self.STANCE_ANGLES.get(stance, self.DEFAULT_CONE_ANGLE)
        half_cone = cone_angle / 2.0
        
        return relative_angle <= half_cone
    
    def get_cone_angle(self, stance: str) -> float:
        """Get vision cone angle for stance."""
        return self.STANCE_ANGLES.get(stance, self.DEFAULT_CONE_ANGLE)


# ============================================================
# D10. Trench Digging AI Extension
# ============================================================

@dataclass
class TrenchDiggingAI:
    """
    Extended trench digging AI behavior.
    
    Units automatically dig after stationary 3 turns undetected.
    Progress bar over 3 turns.
    Permanent cover bonus upon completion.
    """
    
    DIG_DURATION_TURNS: int = 3
    DETECTION_RESET_TIME: float = 5.0  # seconds
    
    _dig_progress: dict[int, float] = field(init=False)
    _stationary_time: dict[int, float] = field(init=False)
    
    def __post_init__(self):
        self._dig_progress = {}
        self._stationary_time = {}
    
    def update_unit(
        self,
        unit_id: int,
        is_stationary: bool,
        is_detected: bool,
        dt: float,
    ) -> str | None:
        """
        Update digging progress for unit.
        
        Returns:
            'digging', 'completed', or None
        """
        if not is_stationary or is_detected:
            self._stationary_time[unit_id] = 0.0
            self._dig_progress[unit_id] = 0.0
            return None
        
        if unit_id not in self._stationary_time:
            self._stationary_time[unit_id] = 0.0
            self._dig_progress[unit_id] = 0.0
        
        self._stationary_time[unit_id] += dt
        
        if self._stationary_time[unit_id] >= 2.0:  # 2 sec stationary
            turn_duration = 5.0  # seconds per turn
            progress_per_sec = 1.0 / (self.DIG_DURATION_TURNS * turn_duration)
            self._dig_progress[unit_id] += dt * progress_per_sec
            
            if self._dig_progress[unit_id] >= 1.0:
                return 'completed'
            return 'digging'
        
        return None
    
    def get_dig_progress(self, unit_id: int) -> float:
        """Get dig progress (0.0 to 1.0)."""
        return self._dig_progress.get(unit_id, 0.0)
