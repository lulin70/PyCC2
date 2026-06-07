"""
Combat Mechanics Enhancement for PyCC2 - Phase C1+C2

Implements two critical combat systems that transform the tactical experience:

1. SUPPRESSION SYSTEM (C1):
   - Continuous suppression that accumulates over time
   - Pinned/Panic states that reduce effectiveness
   - Tactical use of covering fire
   - Recovery mechanics between turns

2. CONCEALMENT & VISION SYSTEM (C2):
   - Multi-layer concealment (terrain + stance + movement)
   - Line-of-sight calculations with height advantage
   - Reconnaissance bonuses
   - Stealth gameplay options

These systems work together with Swiss Cheese damage model to create
deep, tactical combat that surpasses original CC2.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)


# ========================================================================
# PHASE C1: SUPPRESSION SYSTEM
# ========================================================================

class SuppressionEffect(Enum):
    """Effects of suppression on unit performance."""
    NONE = auto()           # No effect (suppression < 30)
    LIGHT = auto()          # -10% accuracy, slight morale risk
    MODERATE = auto()       # -25% accuracy, -20% movement, cannot sprint
    HEAVY = auto()          # -50% accuracy, -50% movement, pinned (no offensive actions)
    PINNED = auto()         # -75% accuracy, cannot move or attack (hunkered down)
    PANIC = auto()          # Cannot act, fleeing behavior, potential rout


@dataclass
class SuppressionState:
    """
    Tracks a unit's current suppression level and effects.
    
    Suppression models the psychological and physical impact of being
    under fire. It accumulates from incoming attacks and slowly recovers.
    
    Key Concepts:
    - Suppression Value: 0-100 scale measuring current stress level
    - Thresholds: Different effects trigger at different levels
    - Recovery: Natural decay between turns, faster when not in LOS
    - Stack: Multiple hits increase suppression (tactical value of MGs)
    """
    
    current_suppression: float = 0.0      # Current suppression (0-100)
    max_suppression: float = 100.0        # Maximum possible
    
    # Configuration thresholds
    light_threshold: float = 25.0         # Light effects begin
    moderate_threshold: float = 45.0      # Moderate effects
    heavy_threshold: float = 65.0         # Heavy effects
    pinned_threshold: float = 80.0        # Pinned (cannot act offensively)
    panic_threshold: float = 95.0         # Panic (complete breakdown)
    
    # Recovery parameters
    base_recovery_rate: float = 8.0       # Base recovery per turn phase
    cover_recovery_bonus: float = 4.0     # Extra recovery in good cover
    out_of_los_recovery_mult: float = 1.5 # Faster recovery when hidden
    
    # State tracking
    turns_since_last_hit: int = 0         # For recovery calculation
    is_pinned: bool = False              # Cached state
    is_panicked: bool = False            # Cached state
    
    def apply_suppression(self, amount: float) -> tuple[SuppressionEffect, bool]:
        """
        Apply suppression from incoming attack.
        
        Args:
            amount: Suppression points to add (based on weapon's suppress_ability)
            
        Returns:
            Tuple of (current_effect, state_changed)
        """
        old_effect = self.get_current_effect()
        
        self.current_suppression = min(100.0, self.current_suppression + amount)
        self.turns_since_last_hit = 0
        
        new_effect = self.get_current_effect()
        state_changed = old_effect != new_effect
        
        # Update cached states
        self.is_pinned = (new_effect in [SuppressionEffect.PINNED, SuppressionEffect.PANIC])
        self.is_panicked = (new_effect == SuppressionEffect.PANIC)
        
        return new_effect, state_changed
    
    def recover(self, in_cover: bool = True, out_of_los: bool = False) -> SuppressionEffect:
        """
        Apply recovery for turn phase end.
        
        Args:
            in_cover: Unit is in good cover position
            out_of_los: Unit cannot be seen by enemies
            
        Returns:
            New suppression effect after recovery
        """
        self.turns_since_last_hit += 1
        
        # Calculate recovery amount
        recovery = self.base_recovery_rate
        
        if in_cover:
            recovery += self.cover_recovery_bonus
        
        if out_of_los:
            recovery *= self.out_of_los_recovery_mult
        
        # Diminishing returns on recovery (first points recover faster)
        effective_recovery = recovery * (1.0 - self.current_suppression / 150.0)
        
        self.current_suppression = max(0.0, self.current_suppression - effective_recovery)
        
        # Update cached states
        effect = self.get_current_effect()
        self.is_pinned = (effect in [SuppressionEffect.PINNED, SuppressionEffect.PANIC])
        self.is_panicked = (effect == SuppressionEffect.PANIC)
        
        return effect
    
    def get_current_effect(self) -> SuppressionEffect:
        """Determine current suppression effect based on value."""
        if self.current_suppression >= self.panic_threshold:
            return SuppressionEffect.PANIC
        elif self.current_suppression >= self.pinned_threshold:
            return SuppressionEffect.PINNED
        elif self.current_suppression >= self.heavy_threshold:
            return SuppressionEffect.HEAVY
        elif self.current_suppression >= self.moderate_threshold:
            return SuppressionEffect.MODERATE
        elif self.current_suppression >= self.light_threshold:
            return SuppressionEffect.LIGHT
        else:
            return SuppressionEffect.NONE
    
    def get_accuracy_penalty(self) -> float:
        """Get accuracy multiplier due to suppression."""
        effect = self.get_current_effect()
        penalties = {
            SuppressionEffect.NONE: 1.0,
            SuppressionEffect.LIGHT: 0.90,
            SuppressionEffect.MODERATE: 0.75,
            SuppressionEffect.HEAVY: 0.50,
            SuppressionEffect.PINNED: 0.25,
            SuppressionEffect.PANIC: 0.10,
        }
        return penalties.get(effect, 1.0)
    
    def get_movement_penalty(self) -> float:
        """Get movement speed multiplier due to suppression."""
        effect = self.get_current_effect()
        penalties = {
            SuppressionEffect.NONE: 1.0,
            SuppressionEffect.LIGHT: 0.95,
            SuppressionEffect.MODERATE: 0.80,
            SuppressionEffect.HEAVY: 0.50,
            SuppressionEffect.PINNED: 0.0,   # Cannot move
            SuppressionEffect.PANIC: 1.5,    # Fleeing (uncontrolled)
        }
        return penalties.get(effect, 1.0)
    
    def can_take_offensive_action(self) -> bool:
        """Check if unit can still attack/perform actions."""
        effect = self.get_current_effect()
        return effect not in [SuppressionEffect.PINNED, SuppressionEffect.PANIC]
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize for save/load."""
        return {
            'current': self.current_suppression,
            'pinned': self.is_pinned,
            'panicked': self.is_panicked,
            'turns_since_hit': self.turns_since_last_hit,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SuppressionState':
        """Deserialize from saved data."""
        state = cls(current_suppression=data.get('current', 0.0))
        state.is_pinned = data.get('pinned', False)
        state.is_panicked = data.get('panicked', False)
        state.turns_since_last_hit = data.get('turns_since_hit', 0)
        return state


def calculate_suppression_from_attack(
    weapon_suppress_ability: float,
    hit_success: bool,
    damage_amount: float,
    is_near_miss: bool = False,
    is_explosive: bool = False
) -> float:
    """
    Calculate suppression inflicted by an attack.
    
    Factors:
    - Weapon's inherent suppress ability (MG42 > Rifle)
    - Whether the attack hit (hits cause more suppression)
    - Damage dealt (more damage = more terrifying)
    - Near misses (still scary!)
    - Explosives (area attacks very suppressing)
    
    Returns:
        Suppression points to apply to target
    """
    base = weapon_suppress_ability * 15.0  # Scale to 0-15 range per shot
    
    if hit_success:
        base *= 1.5  # Hits are more suppressing than misses
        base += damage_amount * 0.05  # Damage adds to fear factor
    
    if is_near_miss:
        base *= 0.7  # Near misses still count
    
    if is_explosive:
        base *= 2.0  # Explosives very frightening
    
    return min(25.0, base)  # Cap at 25 per attack instance


# ========================================================================
# PHASE C2: CONCEALMENT & VISION SYSTEM
# ========================================================================

class Stance(Enum):
    """Unit stance affecting visibility and concealment."""
    STANDING = auto()       # Normal (default)
    CROUCHING = auto()      # Slightly harder to see
    PRONE = auto()          # Much harder to see, slower movement
    IN_BUILDING = auto()    # Inside structure (excellent concealment)


class VisibilityLevel(Enum):
    """How visible a unit is to enemies."""
    HIDDEN = auto()         # Cannot be seen at all
    PARTIAL = auto()        # Spotted but hard to target (-accuracy)
    CLEAR = auto()          # Fully visible (normal targeting)
    EXPOSED = auto()        # Highlighted target (+enemy accuracy)


@dataclass
class ConcealmentProfile:
    """
    Calculates and tracks unit concealment factors.
    
    Concealment determines how hard a unit is to detect and hit.
    It stacks multiple sources additively (with diminishing returns).
    
    Sources of Concealment:
    1. Terrain: Forests, buildings, rough ground provide base concealment
    2. Stance: Prone > crouching > standing
    3. Movement: Moving units easier to spot
    4. Firing: Shooting reveals position temporarily
    5. Special: Camo nets, smoke, ghillie suits
    """
    
    # Base concealment from terrain (set by tile properties)
    terrain_concealment: float = 0.0      # 0.0 to 0.6 from EnhancedTile
    
    # Stance modifiers
    stance_modifiers: dict[Stance, float] = field(default_factory=lambda: {
        Stance.STANDING: 0.0,
        Stance.CROUCHING: 0.2,
        Stance.PRONE: 0.4,
        Stance.IN_BUILDING: 0.6,
    })
    current_stance: Stance = Stance.STANDING
    
    # Dynamic modifiers
    movement_penalty: float = -0.2        # Moving reduces concealment
    firing_penalty: float = -0.5          # Recently fired reveals position
    firing_decay_rate: float = 0.3        # How fast firing penalty decays per turn
    
    # Special modifiers
    special_bonus: float = 0.0           # From camo net, smoke, etc.
    
    # State tracking
    is_moving: bool = False
    turns_since_fired: int = 10          # High = penalty fully decayed
    in_smoke: bool = False               # Smoke provides +0.5
    
    def calculate_total_concealment(self) -> float:
        """
        Calculate total concealment factor (0.0 to ~0.95).
        
        Uses diminishing returns formula to prevent stacking abuse.
        """
        total = self.terrain_concealment
        
        # Add stance modifier
        total += self.stance_modifiers.get(self.current_stance, 0.0)
        
        # Apply movement penalty
        if self.is_moving:
            total += self.movement_penalty
        
        # Apply firing penalty (decays over time)
        if self.turns_since_fired < 5:
            firing_mult = max(0, 1.0 - (self.turns_since_fired * self.firing_decay_rate))
            total += self.firing_penalty * firing_mult
        
        # Add special bonuses
        total += self.special_bonus
        
        # Smoke bonus
        if self.in_smoke:
            total += 0.5
        
        # Clamp to valid range with diminishing returns
        # Formula: final = 1 - (1 - raw)^0.7  (soft cap near 0.95)
        raw = max(0.0, min(1.5, total))  # Allow slight overflow before cap
        final = 1.0 - (1.0 - raw) ** 0.7
        
        return max(0.0, min(0.95, final))
    
    def get_visibility_level(self, enemy_distance: int, enemy_has_los: bool) -> VisibilityLevel:
        """
        Determine how visible this unit is to a specific enemy.
        
        Args:
            enemy_distance: Distance in tiles to enemy
            enemy_has_los: Does enemy have line of sight?
            
        Returns:
            Visibility level enum
        """
        concealment = self.calculate_total_concealment()
        
        if not enemy_has_los:
            return VisibilityLevel.HIDDEN
        
        # Distance matters - closer = easier to spot despite concealment
        distance_factor = max(0.3, 1.0 - (enemy_distance * 0.05))
        effective_concealment = concealment * distance_factor
        
        if effective_concealment > 0.7:
            return VisibilityLevel.HIDDEN
        elif effective_concealment > 0.4:
            return VisibilityLevel.PARTIAL
        elif effective_concealment < 0.15:
            return VisibilityLevel.EXPOSED
        else:
            return VisibilityLevel.CLEAR
    
    def record_firing(self) -> None:
        """Call when unit fires (resets firing penalty)."""
        self.turns_since_fired = 0
    
    def advance_turn(self) -> None:
        """Call at turn start to decay temporal effects."""
        self.turns_since_fired += 1
        self.is_moving = False  # Reset until unit actually moves
    
    def set_stance(self, new_stance: Stance) -> None:
        """Change unit stance."""
        self.current_stance = new_stance


@dataclass 
class VisionSystem:
    """
    Handles line-of-sight (LOS) calculations and detection.
    
    Key Features:
    - Height-based LOS (high ground sees further)
    - Terrain blocking (forests, buildings block vision)
    - Vision range variation by unit type
    - Fog of war integration
    - Reconnaissance bonuses
    """
    
    # Base vision ranges (in tiles)
    BASE_VISION_RANGE: int = 6
    INFANTRY_VISION_BONUS: int = 0
    SCOUT_VISION_BONUS: int = 3
    VEHICLE_VISION_PENALTY: int = -1  # Buttoned up = less awareness
    
    # Height advantages
    HEIGHT_VISION_BONUS_PER_LEVEL: int = 1  # Each height level = +1 vision
    MAX_VISION_RANGE: int = 15             # Hard cap
    
    # Detection thresholds
    DETECTION_CHANCE_HIDDEN: float = 0.05   # 5% chance to spot hidden unit (adjacent)
    DETECTION_CHANCE_PARTIAL: float = 0.40  # 40% chance to clearly identify partial
    
    def calculate_vision_range(
        self,
        unit_height: int,
        is_scout: bool = False,
        is_vehicle: bool = False,
        weather_modifier: float = 1.0
    ) -> int:
        """Calculate effective vision range for a unit."""
        vision = self.BASE_VISION_RANGE
        
        # Unit type modifiers
        if is_scout:
            vision += self.SCOUT_VISION_BONUS
        if is_vehicle:
            vision += self.VEHICLE_VISION_PENALTY
        
        # Height bonus
        vision += unit_height * self.HEIGHT_VISION_BONUS_PER_LEVEL
        
        # Weather effects (rain/fog reduce vision)
        vision = int(vision * weather_modifier)
        
        # Clamp to limits
        return max(3, min(self.MAX_VISION_RANGE, vision))
    
    def has_line_of_sight(
        self,
        observer_pos: tuple[int, int],
        observer_height: int,
        target_pos: tuple[int, int],
        target_height: int,
        terrain_grid: list[list[int]],  # Need terrain for blocking checks
        map_width: int,
        map_height: int
    ) -> bool:
        """
        Check if observer has clear LOS to target.
        
        Uses Bresenham's line algorithm with height checking.
        A tile blocks LOS if it's a building/forest AND taller than both endpoints.
        """
        x0, y0 = observer_pos
        x1, y1 = target_pos
        
        # Bresenham's line algorithm
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        x, y = x0, y0
        blocking_terrains = {5, 8}  # Buildings block LOS
        
        while True:
            # Check if current tile blocks (skip start and end tiles)
            if (x, y) != (x0, y0) and (x, y) != (x1, y1):
                if 0 <= x < map_width and 0 <= y < map_height:
                    terrain = terrain_grid[y][x]
                    if terrain in blocking_terrains:
                        # Check height - only blocks if taller than both
                        # (Simplified: buildings always block for now)
                        return False
            
            if x == x1 and y == y1:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        return True
    
    def attempt_detection(
        self,
        concealment: float,
        distance: int,
        observer_is_scout: bool = False,
        in_smoke: bool = False
    ) -> tuple[bool, VisibilityLevel]:
        """
        Attempt to detect a concealed unit.
        
        Returns:
            Tuple of (detected, visibility_level_if_detected)
        """
        if in_smoke and distance > 1:
            return False, VisibilityLevel.HIDDEN
        
        # Base detection chance inversely proportional to concealment
        base_chance = (1.0 - concealment) * 0.8
        
        # Distance modifier (closer = easier to detect)
        distance_mult = max(0.3, 1.0 - (distance * 0.08))
        
        # Scout bonus
        if observer_is_scout:
            distance_mult *= 1.3
        
        final_chance = base_chance * distance_mult
        
        # Roll for detection (in real implementation, use RNG)
        detected = final_chance > 0.5  # Simplified for demo
        
        if detected:
            if concealment > 0.5:
                return True, VisibilityLevel.PARTIAL
            else:
                return True, VisibilityLevel.CLEAR
        else:
            return False, VisibilityLevel.HIDDEN


# ========================================================================
# INTEGRATION HELPERS
# ========================================================================

@dataclass
class CombatState:
    """
    Combines suppression and concealment into unified combat state.
    
    This is what gets attached to each Unit entity.
    """
    suppression: SuppressionState = field(default_factory=SuppressionState)
    concealment: ConcealmentProfile = field(default_factory=ConcealmentProfile)
    vision: VisionSystem = field(default_factory=VisionSystem)
    is_pinned: bool = False
    is_spotted: bool = False
    last_fired_tick: int = -1
    
    def process_attack_received(
        self,
        weapon_suppress_ability: float,
        hit: bool,
        damage: float,
        is_explosive: bool = False
    ) -> dict[str, Any]:
        """
        Process incoming attack - update both systems.
        
        Returns:
            Dict with effects applied
        """
        # Apply suppression
        suppr_effect, suppr_changed = self.suppression.apply_suppression(
            calculate_suppression_from_attack(
                weapon_suppress_ability, hit, damage,
                is_explosive=is_explosive
            )
        )
        
        # Firing reveals position
        # (Note: This is for when THIS unit fires, handled separately)
        
        return {
            'suppression_effect': suppr_effect.name,
            'suppression_changed': suppr_changed,
            'current_suppression': self.suppression.current_suppression,
            'accuracy_penalty': self.suppression.get_accuracy_penalty(),
            'movement_penalty': self.suppression.get_movement_penalty(),
            'can_act': self.suppression.can_take_offensive_action(),
            'concealment': self.concealment.calculate_total_concealment(),
        }
    
    def process_turn_start(self) -> dict[str, Any]:
        """Process start of turn - recovery and decay."""
        # Suppression recovery
        suppr_effect = self.suppression.recover(
            in_cover=True,  # Would check actual cover
            out_of_los=False  # Would check actual LOS
        )
        
        # Concealment decay (firing penalty fades)
        self.concealment.advance_turn()
        
        return {
            'new_suppression_effect': suppr_effect.name,
            'recovered_suppression': self.suppression.current_suppression,
            'current_concealment': self.concealment.calculate_total_concealment(),
        }


def demo_combat_systems():
    """Demonstrate the enhanced combat mechanics."""
    logger.debug("=" * 80)
    logger.debug("⚔️  ENHANCED COMBAT MECHANICS DEMO")
    logger.debug("   Suppression + Concealment Systems")
    logger.debug("=" * 80)
    logger.debug("")
    
    # Create a unit's combat state
    logger.debug("🎖️ Creating Rifle Squad Combat State...")
    state = CombatState()
    
    # Set up initial conditions
    state.concealment.terrain_concealment = 0.2  # In light forest
    state.concealment.set_stance(Stance.PRONE)
    state.suppression.current_suppression = 10.0  # Slightly stressed
    
    logger.debug("\n📊 Initial State:")
    logger.debug("   Suppression: %s/100 (%s)",
                 state.suppression.current_suppression,
                 state.suppression.get_current_effect().name)
    logger.debug("   Concealment: %.2f",
                 state.concealment.calculate_total_concealment())
    logger.debug("   Accuracy Penalty: %.0f%%",
                 (1 - state.suppression.get_accuracy_penalty()) * 100)
    logger.debug("   Movement Penalty: %.0f%%",
                 (1 - state.suppression.get_movement_penalty()) * 100)
    
    # Simulate coming under heavy MG fire
    logger.debug("\n💥 SIMULATION: Under MG42 Fire (High Suppress Weapon)")
    
    mg42_suppress = 0.9  # MG42 has very high suppress ability
    for i in range(4):  # 4 bursts
        result = state.process_attack_received(
            weapon_suppress_ability=mg42_suppress,
            hit=(i % 2 == 0),  # Alternating hits/misses
            damage=25.0 if (i % 2 == 0) else 0,
        )
        logger.debug(
            "   Burst %s: Suppression → %.1f (%s) | Accuracy: %.0f%% | Can Act: %s",
            i + 1, result['current_suppression'], result['suppression_effect'],
            result['accuracy_penalty'] * 100,
            'YES' if result['can_act'] else 'NO - PINNED')
    
    # Simulate recovery
    logger.debug("\n😤 RECOVERY: Turn Ends (In Cover)")
    recovery = state.process_turn_start()
    logger.debug("   After Recovery: %.1f (%s)",
                 recovery['recovered_suppression'],
                 recovery['new_suppression_effect'])
    
    # Show concealment effects
    logger.debug("\n👁️ CONCEALMENT SYSTEM TEST:")
    for stance in Stance:
        state.concealment.set_stance(stance)
        conc = state.concealment.calculate_total_concealment()
        vis = state.vision.attempt_detection(conc, distance=5)[1]
        logger.debug("   %s: Concealment=%.2f | Visibility=%s",
                     stance.name, conc, vis.name)
    
    logger.debug("\n" + "=" * 80)
    logger.debug("✅ Demo Complete - Systems Ready for Integration!")
    logger.debug("=" * 80)


if __name__ == '__main__':
    demo_combat_systems()
