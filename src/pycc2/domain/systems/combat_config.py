"""
Combat configuration parameters for PyCC2.
Based on OpenCombat (buxx/OpenCombat) battle-tested values and CC2 original mechanics.
Reference: https://github.com/buxx/OpenCombat
"""

from dataclasses import dataclass, field
from enum import Enum, auto


class Stance(Enum):
    """Unit stance affecting visibility and vulnerability."""
    STANDING = auto()
    CROUCHING = auto()
    PRONE = auto()
    IN_BUILDING = auto()


# === FIRE ACCURACY ===

@dataclass(frozen=True)
class AccuracyConfig:
    """Fire accuracy and dispersion parameters."""
    # Core dispersion: spread radius = distance_meters * factor
    inaccurate_fire_factor_by_meter: float = 0.075

    # Additional dispersion from visibility obstruction
    target_alteration_by_opacity_factor: float = 8.0

    # Visibility threshold: total_opacity < this = visible
    visible_starts_at: float = 0.5

    # Number of initial tiles checked for first contact
    visibility_first_tiles: int = 6

    # Body surface area for hit detection (mm)
    body_surface_standing: int = 1000
    body_surface_crouched: int = 700
    body_surface_prone: int = 600

    # Proximity bullet range for suppression (meters)
    proximity_bullet_range: float = 30.0


# === SUPPRESSION ===

@dataclass(frozen=True)
class SuppressionConfig:
    """Suppression/under-fire parameters from OpenCombat."""
    # UnderFire value range
    under_fire_max: float = 200.0
    under_fire_danger: float = 150.0    # Forces prone/sneak
    under_fire_warning: float = 100.0   # Forces crouch/slow

    # Recovery
    under_fire_tick_decrease: float = 10.0  # Decrease per tick
    decrease_freq_seconds: float = 1.0      # Tick frequency

    # Bullet proximity suppression values
    bullet_proximity_close_range: float = 3.0    # meters
    bullet_proximity_close_value: float = 100.0
    bullet_proximity_mid_range: float = 10.0     # meters
    bullet_proximity_mid_value: float = 35.0
    bullet_proximity_far_value: float = 1.0

    # Blast/explosion suppression
    blast_close_range: float = 5.0
    blast_close_value: float = 150.0
    blast_mid_range: float = 10.0
    blast_mid_value: float = 100.0
    blast_far_value: float = 50.0

    # Posture recovery after being shot at
    can_crouch_after_seconds: float = 300.0   # 5 minutes
    can_standup_after_seconds: float = 600.0   # 10 minutes


# === MORALE ===

@dataclass(frozen=True)
class MoraleConfig:
    """Morale system parameters."""
    # Squad morale = alive_conscious / total
    end_morale: float = 0.2          # Below this = broken
    update_freq_seconds: float = 5.0

    # Morale modifiers
    casualty_morale_loss: float = 0.15      # Per KIA
    leader_killed_morale_loss: float = 0.3  # Extra loss when leader dies
    victory_morale_gain: float = 0.1        # Per VL captured
    enemy_routed_morale_gain: float = 0.2   # When enemy squad breaks


# === MOVEMENT ===

@dataclass(frozen=True)
class MovementConfig:
    """Movement speed and pathfinding parameters."""
    # Speeds (tiles per second at normal game speed)
    move_velocity: float = 5.0        # Walk
    move_fast_velocity: float = 10.0   # Run
    sneak_velocity: float = 1.5        # Crawl

    # Pathfinding
    cover_search_distance: int = 6     # Tiles to search for cover
    hide_max_range: float = 50.0       # Max shooting range when hiding
    pathfinding_heuristic_coeff: float = 10.0

    # Terrain movement costs (multiplier on base time)
    terrain_cost_open: float = 1.0
    terrain_cost_road: float = 0.8
    terrain_cost_grass: float = 1.2
    terrain_cost_woods: float = 2.0
    terrain_cost_building: float = 1.5
    terrain_cost_shallow: float = 3.0
    terrain_cost_hedge: float = 2.5
    terrain_cost_rough: float = 1.8
    terrain_cost_crater: float = 2.5
    terrain_cost_swamp: float = 4.0


# === VISIBILITY ===

@dataclass(frozen=True)
class VisibilityConfig:
    """Visibility and concealment parameters."""
    # Behavior visibility modifiers (added to base visibility)
    visibility_standing: float = 0.5
    visibility_crouched: float = 0.5
    visibility_prone: float = -0.9
    visibility_moving: float = 1.0
    visibility_running: float = 2.0
    visibility_sneaking: float = -0.9
    visibility_defending: float = -0.9
    visibility_hiding: float = -0.9
    visibility_firing: float = 0.5

    # Terrain opacity values (cumulative along line of sight)
    opacity_short_grass: float = 0.0
    opacity_tall_grass: float = 0.1
    opacity_bush: float = 0.015
    opacity_hedge: float = 0.25
    opacity_tree_trunk: float = 0.2
    opacity_log: float = 0.15
    opacity_rock: float = 0.15
    opacity_brick_wall: float = 1.0

    # Post-firing visibility boost duration
    visibility_by_last_shot_seconds: float = 15.0

    # Terrain coverage values (probability of blocking a hit)
    # Format: (standing_coverage, prone_coverage)
    coverage_brick_wall: tuple = (0.8, 0.8)
    coverage_tree_trunk: tuple = (0.9, 0.7)
    coverage_log: tuple = (0.2, 0.7)
    coverage_hedge: tuple = (0.15, 0.15)
    coverage_rock: tuple = (0.2, 0.75)
    coverage_dirt_prone: tuple = (0.0, 0.3)


# === WEAPON FIRE PARAMETERS ===

@dataclass(frozen=True)
class WeaponFireConfig:
    """Weapon firing parameters per weapon type."""
    weapon_name: str
    aim_frames: int          # Frames to aim (at 60fps)
    fire_frames: int         # Frames between shots
    reload_frames: int       # Frames to reload
    burst_offset_frames: int # Frames between burst shots (0=single)
    spread_coefficient: float # Multiplier on base spread
    magazine_capacity: int
    standard_magazines: int  # Number of spare magazines

    @property
    def aim_seconds(self) -> float:
        return self.aim_frames / 60.0

    @property
    def fire_seconds(self) -> float:
        return self.fire_frames / 60.0

    @property
    def reload_seconds(self) -> float:
        return self.reload_frames / 60.0


# Pre-configured weapon fire parameters (from OpenCombat)
WEAPON_FIRE_PARAMS = {
    # Rifles
    'Lee_Enfield_No4': WeaponFireConfig('Lee-Enfield No.4', 30, 12, 60, 0, 1.0, 10, 5),
    'M1_Garand': WeaponFireConfig('M1 Garand', 30, 12, 60, 0, 1.0, 8, 5),
    'Kar98k': WeaponFireConfig('Kar98k', 30, 12, 60, 0, 1.0, 5, 5),
    'Mauser_G41': WeaponFireConfig('Mauser G41', 30, 12, 60, 0, 1.0, 5, 5),

    # Submachine guns
    'Thompson': WeaponFireConfig('Thompson M1A1', 20, 6, 60, 4, 1.1, 20, 4),
    'Sten_Gun': WeaponFireConfig('Sten Gun MkV', 20, 6, 60, 4, 1.1, 32, 4),
    'MP40': WeaponFireConfig('MP40', 20, 6, 60, 4, 1.1, 32, 4),

    # Light machine guns
    'BREN_Gun': WeaponFireConfig('BREN Mk2', 60, 60, 180, 7, 1.05, 30, 4),
    'MG34': WeaponFireConfig('MG34', 60, 60, 180, 5, 1.045, 50, 4),
    'MG42': WeaponFireConfig('MG42', 45, 45, 180, 3, 1.03, 50, 4),
    'M1919_30Cal': WeaponFireConfig('M1919 .30 Cal', 60, 60, 180, 6, 1.05, 50, 4),

    # Anti-tank weapons
    'Bazooka_M1A1': WeaponFireConfig('Bazooka M1A1', 90, 1, 300, 0, 1.5, 1, 2),
    'PIAT': WeaponFireConfig('PIAT', 90, 1, 300, 0, 1.5, 1, 2),
    'Panzerschreck': WeaponFireConfig('Panzerschreck', 90, 1, 300, 0, 1.4, 1, 2),

    # Mortars
    'Mortar_2inch': WeaponFireConfig('2-inch Mortar', 120, 1, 180, 0, 2.0, 1, 6),
    'Mortar_3inch': WeaponFireConfig('3-inch Mortar', 150, 1, 240, 0, 2.5, 1, 6),
    'Mortar_60mm': WeaponFireConfig('60mm Mortar', 120, 1, 180, 0, 2.0, 1, 6),
    'Mortar_81mm': WeaponFireConfig('81mm GrW 34', 150, 1, 240, 0, 2.5, 1, 6),

    # Flamethrower
    'Flamethrower': WeaponFireConfig('Flamethrower', 30, 30, 120, 0, 0.8, 5, 1),

    # Tank guns
    '75mm_M3': WeaponFireConfig('75mm M3 (Sherman)', 120, 1, 300, 0, 1.2, 1, 8),
    '17pdr': WeaponFireConfig('17-pounder (Firefly)', 120, 1, 300, 0, 1.1, 1, 6),
    '75mm_KwK40': WeaponFireConfig('75mm KwK 40 (PzIV)', 120, 1, 300, 0, 1.1, 1, 8),
    '75mm_KwK42': WeaponFireConfig('75mm KwK 42 (Panther)', 120, 1, 300, 0, 1.0, 1, 6),
    '88mm_KwK36': WeaponFireConfig('88mm KwK 36 (Tiger)', 150, 1, 360, 0, 0.9, 1, 6),
    '88mm_PaK43': WeaponFireConfig('88mm PaK 43 (Jagdpanther)', 150, 1, 360, 0, 0.9, 1, 5),
    '75mm_StuK40': WeaponFireConfig('75mm StuK 40 (StuG)', 120, 1, 300, 0, 1.1, 1, 7),

    # AT Guns
    '6pdr_AT': WeaponFireConfig('6-pounder AT', 120, 1, 300, 0, 1.2, 1, 6),
    '17pdr_AT': WeaponFireConfig('17-pounder AT', 120, 1, 300, 0, 1.1, 1, 5),
    'PaK40': WeaponFireConfig('7.5cm PaK 40', 120, 1, 300, 0, 1.1, 1, 6),
    'FlaK88': WeaponFireConfig('8.8cm FlaK 36', 150, 1, 360, 0, 0.9, 1, 8),
    'M1_57mm_AT': WeaponFireConfig('M1 57mm AT', 120, 1, 300, 0, 1.2, 1, 6),
}


# === MG BURST SHOT COUNT ===
# Number of shots per burst based on visible enemy count

@dataclass(frozen=True)
class MGBurstConfig:
    """Machine gun burst shot count based on target count."""
    # enemy_count: (min_shots, max_shots) per burst
    no_enemies: tuple = (1, 3)
    few_enemies: tuple = (1, 5)     # 1-2 enemies
    some_enemies: tuple = (1, 10)   # 3-4 enemies
    many_enemies: tuple = (1, 16)   # 5+ enemies

    def get_burst_range(self, enemy_count: int) -> tuple:
        if enemy_count == 0:
            return self.no_enemies
        elif enemy_count <= 2:
            return self.few_enemies
        elif enemy_count <= 4:
            return self.some_enemies
        else:
            return self.many_enemies


# === EXPLOSION PARAMETERS ===

@dataclass(frozen=True)
class ExplosionConfig:
    """Explosion damage parameters."""
    # Direct kill radius (meters)
    direct_kill_radius: float = 1.0
    # Regressive kill radius
    regressive_kill_radius: float = 3.0
    # Regressive injure radius
    regressive_injure_radius: float = 6.0

    def kill_probability(self, distance_meters: float) -> float:
        if distance_meters <= self.direct_kill_radius:
            return 1.0
        elif distance_meters <= self.regressive_kill_radius:
            return 1.0 - (distance_meters / self.regressive_kill_radius)
        return 0.0

    def injure_probability(self, distance_meters: float) -> float:
        if distance_meters <= self.direct_kill_radius:
            return 1.0
        elif distance_meters <= self.regressive_injure_radius:
            return 1.0 - (distance_meters / self.regressive_injure_radius)
        return 0.0


# === UPDATE FREQUENCIES ===

@dataclass(frozen=True)
class UpdateFrequencyConfig:
    """Game simulation update frequencies (seconds between updates)."""
    soldier_position: float = 1/60      # Every frame
    soldier_behavior: float = 1/3       # 333ms
    visibility: float = 1.0             # 1 second
    suppression_decay: float = 1.0      # 1 second
    flag_status: float = 2.0            # 2 seconds
    squad_leader_ai: float = 2.0        # 2 seconds
    morale: float = 5.0                 # 5 seconds
    victory_check: float = 5.0          # 5 seconds


# === DEFAULT CONFIG INSTANCE ===

DEFAULT_ACCURACY = AccuracyConfig()
DEFAULT_SUPPRESSION = SuppressionConfig()
DEFAULT_MORALE = MoraleConfig()
DEFAULT_MOVEMENT = MovementConfig()
DEFAULT_VISIBILITY = VisibilityConfig()
DEFAULT_MG_BURST = MGBurstConfig()
DEFAULT_EXPLOSION = ExplosionConfig()
DEFAULT_UPDATE_FREQ = UpdateFrequencyConfig()
