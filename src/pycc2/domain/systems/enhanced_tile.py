"""
Enhanced Tile System for PyCC2 - Phase A2

Implements multi-layer terrain data structure that transforms flat tile grids
into rich, detailed battlefields with height, decorations, and visual variation.

Architecture:
- EnhancedTile: Core data structure replacing simple integer terrain IDs
- DecorationType: Enum defining all placeable decorations (30+ types)
- DecorationLibrary: Sprite/metadata definitions for each decoration
- TileConverter: Backward-compatible converter from legacy format
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class DecorationType(Enum):
    """
    Comprehensive decoration catalog for tactical maps.
    
    Organized into thematic layers that stack to create visual richness.
    Total: 35+ decoration types covering vegetation, geology, man-made,
    combat damage, and atmospheric elements.
    """
    
    # === VEGETATION LAYER (Flora) ===
    BUSH_SMALL = auto()           # Small shrub, provides light cover
    BUSH_DENSE = auto()           # Dense bush, good concealment
    TREE_OAK = auto()             # Deciduous tree (summer)
    TREE_PINE = auto()            # Coniferous tree (blocks LOS)
    TREE_BURNED = auto()          # Charred tree (battle damage)
    GRASS_TUFT = auto()           # Tall grass clump (visual only)
    CROPS_WHEAT = auto()          # Wheat field (seasonal)
    HEDGE_ROW = auto()            # Thick hedge (strong cover)
    FLOWER_PATCH = auto()         # Wildflowers (visual variety)
    
    # === GEOLOGY LAYER (Natural features) ===
    ROCK_LARGE = auto()           # Boulder, provides heavy cover
    ROCK_SMALL = auto()           # Small rock cluster
    RUBBLE_PILE = auto()          # Debris from destroyed building
    SAND_PATCH = auto()           # Sandy area (affects movement)
    MUD_PATCH = auto()            # Muddy ground (slows movement)
    PUDDLE = auto()               # Water puddle (after rain)
    
    # === MAN-MADE LAYER (Structures) ===
    FENCE_WOOD = auto()           # Wooden fence (light obstacle)
    FENCE_WIRE = auto()           # Barbed wire (infantry obstacle)
    TRENCH_SECTION = auto()       # Trench segment (excellent cover)
    SANDBAG_WALL = auto()         # Sandbag position (engineered cover)
    SIGN_POST = auto()             # Road sign (landmark/cover)
    ROAD_BLOCK = auto()            # Barricade/roadblock
    CRATE_STACK = auto()           # Supply crates (light cover)
    
    # === COMBAT DAMAGE LAYER (Battle scars) ===
    CRATER_SMALL = auto()          # Small shell crater (mortar)
    CRATER_LARGE = auto()          # Large bomb crater (air strike)
    BURN_MARK = auto()             # Scorch mark (fire/explosion)
    WRECKAGE_VEHICLE = auto()      # Destroyed vehicle hull (heavy cover + obstacle)
    WRECKAGE_GUN = auto()           # Destroyed gun emplacement
    BUILDING_RUIN = auto()         # Ruined building structure (partial cover + LOS block)
    SHELL_HOLE = auto()            # Artillery impact point
    
    # === ATMOSPHERE/DETAIL LAYER (Ambient) ===
    PATH_DIRT = auto()             # Dirt path (visual guide)
    GRAVE_MARKER = auto()          # Grave (atmospheric/historical)
    SUPPLY_BOX = auto()            # Ammunition/ supply box (pickupable?)
    FLAG_POLE = auto()             # Flag marker (objective indicator)
    CAMPFIRE = auto()              # Extinguished campfire (night missions)
    ANIMAL_CORPSE = auto()         # Dead horse/cow (grim realism)
    
    # === SPECIAL/TACTICAL LAYER ===
    MINE_MARKER = auto()           # Visible mine field marker (friendly)
    TRIP_FLARE = auto()            # Trip flare (alarm system)
    CAMOUFLAGE_NET = auto()        # Camo netting (concealment bonus)
    OBSERVATION_POST = auto()      # Elevated observation position
    MEDIC_STATION = auto()         # Medical supplies (healing point)


@dataclass
class DecorationInstance:
    """Single placed decoration on a tile."""
    decoration_type: DecorationType
    offset_x: float = 0.0          # Sub-tile X position (-0.5 to 0.5)
    offset_y: float = 0.0          # Sub-tile Y position (-0.5 to 0.5)
    scale: float = 1.0             # Size variation (0.8 to 1.2)
    rotation: int = 0              # Rotation in degrees (0, 90, 180, 270)
    variant: int = 0               # Visual variant (for variety)
    
    def get_tactical_properties(self) -> dict[str, Any]:
        """Return tactical effects of this decoration."""
        props = {
            'cover_bonus': 0,      # Adds to cover value (-1 to +3)
            'concealment_bonus': 0, # Adds to concealment (0.0 to 0.4)
            'movement_cost': 1.0,   # Movement multiplier (0.5 to 2.0)
            'blocks_los': False,    # Completely blocks line of sight
            'destructible': True,   # Can be destroyed by explosives
            'height_override': None # Overrides tile height if set
        }
        
        # Apply type-specific properties
        type_props = {
            DecorationType.TREE_OAK: {'cover_bonus': 2, 'concealment_bonus': 0.3, 'blocks_los': True},
            DecorationType.TREE_PINE: {'cover_bonus': 2, 'concealment_bonus': 0.35, 'blocks_los': True},
            DecorationType.ROCK_LARGE: {'cover_bonus': 3, 'concealment_bonus': 0.1, 'movement_cost': 1.5},
            DecorationType.TRENCH_SECTION: {'cover_bonus': 3, 'concealment_bonus': 0.4, 'movement_cost': 0.8},
            DecorationType.SANDBAG_WALL: {'cover_bonus': 3, 'concealment_bonus': 0.3},
            DecorationType.WRECKAGE_VEHICLE: {'cover_bonus': 3, 'blocks_los': True, 'movement_cost': 2.0},
            DecorationType.CRATER_LARGE: {'cover_bonus': 1, 'concealment_bonus': 0.15, 'movement_cost': 1.8},
            DecorationType.BUSH_DENSE: {'cover_bonus': 1, 'concealment_bonus': 0.25},
            DecorationType.HEDGE_ROW: {'cover_bonus': 2, 'concealment_bonus': 0.3, 'movement_cost': 1.3},
            DecorationType.FENCE_WIRE: {'movement_cost': 1.5, 'destructible': False},
            DecorationType.CAMOUFLAGE_NET: {'concealment_bonus': 0.4},
            DecorationType.BUILDING_RUIN: {'cover_bonus': 2, 'concealment_bonus': 0.2, 'blocks_los': True},
        }
        
        if self.decoration_type in type_props:
            props.update(type_props[self.decoration_type])
        
        return props


@dataclass 
class EnhancedTile:
    """
    Multi-layer terrain tile - the heart of the enhanced map system.
    
    Replaces simple integer terrain ID with rich data structure supporting:
    - Height variation (elevation affects LOS, movement, combat)
    - Multiple decorations per tile (stacked visual elements)
    - Visual variation (prevents repetitive appearance)
    - Tactical metadata (derived from decorations)
    
    Backward Compatible: Can be initialized from legacy integer terrain ID.
    """
    
    # === CORE TERRAIN DATA ===
    base_terrain: int              # Legacy terrain type (0-11) for compatibility
    height: int = 0                # Elevation level (-3 to +3, relative to map baseline)
    
    # === VISUAL VARIATION ===
    variation: int = 0             # Appearance variant (0-7) for same terrain type
    transition_edges: dict[str, int] = field(default_factory=dict)  # Blending with neighbors
    
    # === DECORATION LAYER ===
    decorations: list[DecorationInstance] = field(default_factory=list)
    max_decorations: int = 4       # Performance limit per tile
    
    # === DERIVED TACTICAL PROPERTIES (cached) ===
    _cached_cover: int | None = None
    _cached_concealment: float | None = None
    _cached_movement_cost: float | None = None
    
    def add_decoration(self, deco: DecorationInstance) -> bool:
        """Add decoration to tile if under limit."""
        if len(self.decorations) < self.max_decorations:
            self.decorations.append(deco)
            self._invalidate_cache()
            return True
        return False
    
    def remove_decoration(self, deco_type: DecorationType) -> bool:
        """Remove first decoration of given type."""
        for i, d in enumerate(self.decorations):
            if d.decoration_type == deco_type:
                self.decorations.pop(i)
                self._invalidate_cache()
                return True
        return False
    
    @property
    def total_cover_bonus(self) -> int:
        """Calculate total cover bonus from terrain + decorations."""
        if self._cached_cover is not None:
            return self._cached_cover
        
        # Base cover from terrain type
        terrain_cover = {
            0: 0, 1: 0, 2: 0,       # Open ground: no cover
            3: 1,                    # Forest: light cover
            4: 2,                    # Rock: medium cover
            5: 3, 8: 2,             # Building/urban: heavy/medium cover
            6: 0, 10: 0,            # Water: no cover
            7: 2,                    # Trench/dirt: medium cover
            9: 1, 11: 0,            # Rough/open: light/no cover
        }
        base = terrain_cover.get(self.base_terrain, 0)
        
        # Add decoration bonuses
        for deco in self.decorations:
            props = deco.get_tactical_properties()
            base += props['cover_bonus']
        
        self._cached_cover = max(-1, min(3, base))  # Clamp to [-1, 3]
        return self._cached_cover
    
    @property
    def total_concealment(self) -> float:
        """Calculate total concealment factor (0.0 to 1.0)."""
        if self._cached_concealment is not None:
            return self._cached_concealment
        
        # Base concealment from terrain
        terrain_conc = {
            0: 0.0, 1: 0.0, 2: 0.0,  # Open: none
            3: 0.2,                   # Forest: moderate
            4: 0.1,                   # Rock: slight
            5: 0.3, 8: 0.25,         # Building: good
            6: 0.0, 10: 0.0,         # Water: none
            7: 0.25,                  # Trench: good
            9: 0.15, 11: 0.05,       # Rough: some
        }
        base = terrain_conc.get(self.base_terrain, 0.0)
        
        # Stack decoration concealment (diminishing returns)
        for deco in self.decorations:
            props = deco.get_tactical_properties()
            bonus = props['concealment_bonus']
            base += bonus * (1.0 - base)  # Diminishing returns
        
        self._cached_concealment = min(0.95, max(0.0, base))
        return self._cached_concealment
    
    @property
    def effective_movement_cost(self) -> float:
        """Calculate movement cost multiplier for this tile."""
        if self._cached_movement_cost is not None:
            return self._cached_movement_cost
        
        # Base cost from terrain
        terrain_cost = {
            0: 1.0, 1: 0.7, 2: 1.0,  # Normal/road/grass
            3: 2.0,                   # Forest: slow
            4: 1.5,                   # Rock: slower
            5: 1.5, 8: 1.5,          # Building: slower inside
            6: 999.0, 10: 2.0,       # Water: impassable/slow
            7: 1.0,                   # Trench: normal
            9: 1.3, 11: 1.2,         # Rough: slightly slow
        }
        base = terrain_cost.get(self.base_terrain, 1.0)
        
        # Apply worst decoration modifier
        for deco in self.decorations:
            props = deco.get_tactical_properties()
            if props['movement_cost'] > base:
                base = props['movement_cost']
        
        # Height penalty (going uphill costs more)
        if self.height > 0:
            base *= (1.0 + self.height * 0.2)
        
        self._cached_movement_cost = base
        return self._cached_movement_cost
    
    def blocks_line_of_sight(self) -> bool:
        """Check if this tile completely blocks LOS."""
        # Buildings always block
        if self.base_terrain in [5, 8]:
            return True
        # Dense vegetation can block
        blocking_types = {
            DecorationType.TREE_OAK,
            DecorationType.TREE_PINE,
            DecorationType.WRECKAGE_VEHICLE,
            DecorationType.BUILDING_RUIN,
        }
        return any(d.decoration_type in blocking_types for d in self.decorations)
    
    def _invalidate_cache(self) -> None:
        """Clear cached derived values."""
        self._cached_cover = None
        self._cached_concealment = None
        self._cached_movement_cost = None
    
    def to_legacy_int(self) -> int:
        """Convert back to legacy integer format (for backward compatibility)."""
        return self.base_terrain
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            'base_terrain': self.base_terrain,
            'height': self.height,
            'variation': self.variation,
            'decorations': [
                {
                    'type': d.decoration_type.name,
                    'offset_x': d.offset_x,
                    'offset_y': d.offset_y,
                    'scale': d.scale,
                    'rotation': d.rotation,
                    'variant': d.variant,
                }
                for d in self.decorations
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'EnhancedTile':
        """Deserialize from dictionary."""
        tile = cls(
            base_terrain=data['base_terrain'],
            height=data.get('height', 0),
            variation=data.get('variation', 0),
        )
        
        for deco_data in data.get('decorations', []):
            deco = DecorationInstance(
                decoration_type=DecorationType[deco_data['type']],
                offset_x=deco_data.get('offset_x', 0.0),
                offset_y=deco_data.get('offset_y', 0.0),
                scale=deco_data.get('scale', 1.0),
                rotation=deco_data.get('rotation', 0),
                variant=deco_data.get('variant', 0),
            )
            tile.add_decoration(deco)
        
        return tile
    
    @classmethod
    def from_legacy(cls, terrain_id: int) -> 'EnhancedTile':
        """Create EnhancedTile from legacy integer terrain ID."""
        return cls(base_terrain=terrain_id)


@dataclass
class DecorationLibrary:
    """
    Metadata and rendering hints for all decoration types.
    
    Provides sprite information, placement rules, and tactical defaults.
    """
    
    definitions: dict[DecorationType, dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize default decoration definitions."""
        self.definitions = {
            # VEGETATION
            DecorationType.BUSH_SMALL: {
                'sprite_sheet': 'vegetation.png',
                'sprite_region': (0, 0, 16, 16),
                'draw_layer': 'ground_detail',
                'placement_rules': {'biomes': ['grassland', 'forest_edge'], 'density': 0.15},
                'size_range': (0.6, 1.0),
                'variants': 3,
            },
            DecorationType.BUSH_DENSE: {
                'sprite_sheet': 'vegetation.png',
                'sprite_region': (16, 0, 24, 24),
                'draw_layer': 'ground_detail',
                'placement_rules': {'biomes': ['grassland', 'forest'], 'density': 0.08},
                'size_range': (0.8, 1.2),
                'variants': 2,
            },
            DecorationType.TREE_OAK: {
                'sprite_sheet': 'trees.png',
                'sprite_region': (0, 0, 32, 48),
                'draw_layer': 'above_units',
                'placement_rules': {'biomes': ['grassland', 'forest'], 'density': 0.05, 'min_distance': 2},
                'size_range': (0.9, 1.1),
                'variants': 4,
                'shadow_size': (40, 20),  # Casts shadow on ground
            },
            DecorationType.TREE_PINE: {
                'sprite_sheet': 'trees.png',
                'sprite_region': (32, 0, 24, 56),
                'draw_layer': 'above_units',
                'placement_rules': {'biomes': ['forest', 'mountain'], 'density': 0.06, 'min_distance': 2},
                'size_range': (0.85, 1.15),
                'variants': 3,
                'shadow_size': (32, 18),
            },
            
            # GEOLOGY
            DecorationType.ROCK_LARGE: {
                'sprite_sheet': 'geology.png',
                'sprite_region': (0, 0, 28, 24),
                'draw_layer': 'ground_detail',
                'placement_rules': {'biomes': ['rocky', 'mountain'], 'density': 0.04},
                'size_range': (0.9, 1.2),
                'variants': 2,
            },
            DecorationType.RUBBLE_PILE: {
                'sprite_sheet': 'damage.png',
                'sprite_region': (0, 0, 32, 20),
                'draw_layer': 'ground_detail',
                'placement_rules': {'near_buildings': True, 'density': 0.12},
                'size_range': (0.7, 1.3),
                'variants': 5,
            },
            
            # COMBAT DAMAGE
            DecorationType.CRATER_SMALL: {
                'sprite_sheet': 'damage.png',
                'sprite_region': (32, 0, 20, 16),
                'draw_layer': 'ground_detail',
                'placement_rules': {'combat_zones': True, 'density': 0.08},
                'size_range': (0.8, 1.2),
                'variants': 3,
            },
            DecorationType.CRATER_LARGE: {
                'sprite_sheet': 'damage.png',
                'sprite_region': (0, 16, 40, 28),
                'draw_layer': 'ground_detail',
                'placement_rules': {'combat_zones': True, 'density': 0.03},
                'size_range': (0.9, 1.1),
                'variants': 2,
            },
            DecorationType.WRECKAGE_VEHICLE: {
                'sprite_sheet': 'damage.png',
                'sprite_region': (40, 16, 48, 32),
                'draw_layer': 'above_units',
                'placement_rules': {'roads': True, 'near_combat': True, 'density': 0.02},
                'size_range': (1.0, 1.0),
                'variants': 6,  # Different vehicle types
            },
            
            # MAN-MADE
            DecorationType.TRENCH_SECTION: {
                'sprite_sheet': 'fortifications.png',
                'sprite_region': (0, 0, 32, 16),
                'draw_layer': 'ground_detail',
                'placement_rules': {'player_placeable': True, 'connects_linear': True},
                'size_range': (1.0, 1.0),
                'variants': 2,  # Straight, corner
            },
            DecorationType.SANDBAG_WALL: {
                'sprite_sheet': 'fortifications.png',
                'sprite_region': (0, 16, 32, 12),
                'draw_layer': 'ground_detail',
                'placement_rules': {'player_placeable': True},
                'size_range': (1.0, 1.0),
                'variants': 1,
            },
            DecorationType.FENCE_WIRE: {
                'sprite_sheet': 'fortifications.png',
                'sprite_region': (32, 0, 32, 8),
                'draw_layer': 'ground_detail',
                'placement_rules': {'connects_linear': True, 'perimeter_only': True},
                'size_range': (1.0, 1.0),
                'variants': 1,
            },
        }
    
    def get_definition(self, deco_type: DecorationType) -> dict[str, Any]:
        """Get definition for a decoration type."""
        return self.definitions.get(deco_type, {
            'sprite_sheet': 'default.png',
            'sprite_region': (0, 0, 16, 16),
            'draw_layer': 'ground_detail',
            'placement_rules': {},
            'size_range': (1.0, 1.0),
            'variants': 1,
        })


class TileConverter:
    """
    Converts between legacy and enhanced tile formats.
    
    Ensures backward compatibility while enabling new features.
    """
    
    @staticmethod
    def convert_grid_to_enhanced(legacy_grid: list[list[int]]) -> list[list[EnhancedTile]]:
        """Convert entire legacy grid to enhanced format."""
        enhanced_grid = []
        for row in legacy_grid:
            enhanced_row = [EnhancedTile.from_legacy(tile_id) for tile_id in row]
            enhanced_grid.append(enhanced_row)
        return enhanced_grid
    
    @staticmethod
    def convert_grid_to_legacy(enhanced_grid: list[list[EnhancedTile]]) -> list[list[int]]:
        """Convert enhanced grid back to legacy format (data loss)."""
        return [[tile.to_legacy_int() for tile in row] for row in enhanced_grid]
    
    @staticmethod
    def convert_map_data(map_data: dict[str, Any]) -> dict[str, Any]:
        """
        Convert full map data dictionary to enhanced format.
        
        Preserves all original keys and adds enhanced tiles structure.
        """
        if 'tiles' not in map_data:
            raise ValueError("Map data must contain 'tiles' key")
        
        # Convert tiles
        legacy_tiles = map_data['tiles']
        enhanced_tiles = TileConverter.convert_grid_to_enhanced(legacy_tiles)
        
        # Build new map data
        new_data = {**map_data}
        new_data['tiles_enhanced'] = [
            [tile.to_dict() for tile in row]
            for row in enhanced_tiles
        ]
        new_data['_format_version'] = 'enhanced_v1'
        
        return new_data


# Convenience function for quick conversion
def enhance_map(map_path: str, output_path: str | None = None) -> dict[str, Any]:
    """
    Quick utility to convert a legacy map file to enhanced format.
    
    Args:
        map_path: Path to legacy map JSON file
        output_path: Output path (defaults to overwriting input)
        
    Returns:
        Enhanced map data dictionary
    """
    import json
    from pathlib import Path
    
    map_file = Path(map_path)
    with open(map_file, 'r') as f:
        legacy_data = json.load(f)
    
    enhanced_data = TileConverter.convert_map_data(legacy_data)
    
    out_path = output_path or str(map_file)
    with open(out_path, 'w') as f:
        json.dump(enhanced_data, f, indent=2)
    
    print(f"✅ Enhanced map saved: {out_path}")
    print(f"   Size: {legacy_data['width']}×{legacy_data['height']} → "
          f"{enhanced_data['width']}×{enhanced_data['height']}")
    print(f"   Format: legacy → enhanced_v1")
    
    return enhanced_data


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python enhanced_tile.py <map_file.json> [output_file.json]")
        sys.exit(1)
    
    enhance_map(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
