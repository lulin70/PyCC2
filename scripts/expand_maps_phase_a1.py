#!/usr/bin/env python3
"""
Map Expander for PyCC2 - Phase A1 Implementation

Aggressively expands all tactical maps to CC2-standard sizes while preserving
core terrain features and adding tactically meaningful border regions.

Target Sizes (matching/surpassing original CC2):
- Tutorial:       16×16 → 24×20   (+87% area)
- Bridge Assault: 20×20 → 32×28   (+124% area)
- Defense Line:   20×20 → 30×26  (+95% area)
- Night Map:      20×20 → 28×24  (+68% area)
- Road Ambush:    18×18 → 28×24  (+111% area)
- Son Bridge:     22×20 → 34×30  (+132% area)
- Veghel:         24×22 → 36×32  (+118% area)
- Grave:          26×24 → 38×34  (+104% area)
- Nijmegen:       28×24 → 40×35  (+102% area)
- Arnhem:         30×26 → 50×42  (+170% area) ← FLAGSHIP MAP
"""

import json
import math
import random
from pathlib import Path
from typing import Any


class TerrainNoiseGenerator:
    """Generates natural-looking terrain transitions using value noise.

    Known issues (TD-007):
        - noise2d uses Python's built-in hash() for non-(0,0) lattice points.
          Since Python 3 enables PYTHONHASHSEED by default, hash() values
          differ across runs, making the noise output non-reproducible even
          with the same seed.  Consider replacing hash() with a deterministic
          hash (e.g. xxhash, or a simple FNV-1a implementation).
    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def _smoothstep(self, t: float) -> float:
        """Smooth interpolation function."""
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)

    def _lerp(self, a: float, b: float, t: float) -> float:
        """Linear interpolation."""
        return a + (b - a) * self._smoothstep(t)

    def noise2d(self, x: float, y: float, scale: float = 0.1) -> float:
        """2D value noise at given coordinates."""
        xi = int(x * scale)
        yi = int(y * scale)
        xf = (x * scale) - xi
        yf = (y * scale) - yi
        
        n00 = self.rng.uniform(0, 1) if (xi, yi) == (0, 0) else hash((xi, yi)) % 1000 / 1000.0
        n10 = self.rng.uniform(0, 1) if (xi+1, yi) == (0, 0) else hash((xi+1, yi)) % 1000 / 1000.0
        n01 = self.rng.uniform(0, 1) if (xi, yi+1) == (0, 0) else hash((xi, yi+1)) % 1000 / 1000.0
        n11 = self.rng.uniform(0, 1) if (xi+1, yi+1) == (0, 0) else hash((xi+1, yi+1)) % 1000 / 1000.0
        
        ix0 = self._lerp(n00, n10, xf)
        ix1 = self._lerp(n01, n11, xf)
        return self._lerp(ix0, ix1, yf)


class MapExpander:
    """
    Intelligently expands maps while preserving tactical integrity.
    
    Strategy:
    1. Keep core region (original map) intact in center
    2. Add transition zones with blended terrain
    3. Generate natural border regions using noise
    4. Ensure new areas are tactically interesting (cover, variation)

    Known issues (TD-007):
        - _weighted_random, _add_tree_lines, _add_rough_patches, and
          _add_outbuildings all call random.seed() which resets the global
          RNG state.  This causes cross-contamination between methods and
          makes the output order-dependent.  Should use a local Random
          instance instead of the global module-level RNG.
        - _analyze_edge_terrain only considers the single most-common
          terrain type per edge.  If an edge is heterogeneous (e.g. water
          AND buildings), the minority terrain is ignored, leading to
          incorrect border context selection.  Should consider top-N or
          weighted analysis.
        - _scale_objectives uses int() truncation (int(ox * new_w / old_w))
          which systematically shifts objective positions toward the top-left
          corner.  Should use round() for more accurate placement.
    """

    TERRAIN_CATEGORIES = {
        'open': [0, 1, 2],           # Grass, dirt, road
        'vegetation': [3, 9],        # Forest, rough
        'urban': [5, 8],             # Building, urban
        'water': [6, 10],            # River, shallow water
        'special': [4, 7, 11]        # Rock, trench, beach
    }

    BORDER_TERRAIN_WEIGHTS = {
        'grassland': {2: 60, 3: 25, 1: 10, 9: 5},
        'forest_edge': {3: 50, 2: 30, 9: 15, 4: 5},
        'urban_fringe': {5: 40, 2: 30, 8: 15, 4: 10, 7: 5},
        'waterfront': {6: 45, 10: 25, 2: 20, 9: 7, 7: 3},
        'rough': {9: 40, 4: 30, 2: 20, 3: 7, 5: 3},
    }

    def __init__(self, seed: int | None = None):
        self.noise = TerrainNoiseGenerator(seed)
        self.seed = seed or 42

    def expand_map(self, map_data: dict[str, Any], target_width: int, target_height: int) -> dict[str, Any]:
        """
        Expand map to target dimensions.
        
        Args:
            map_data: Original map JSON data
            target_width: New width in tiles
            target_height: New height in tiles
            
        Returns:
            Expanded map data with preserved objectives and spawn points adjusted
        """
        orig_width = map_data['width']
        orig_height = map_data['height']
        orig_tiles = map_data['tiles']

        print(f"📐 Expanding {map_data['id']}: {orig_width}×{orig_height} → {target_width}×{target_height} "
              f"({((target_width*target_height)/(orig_width*orig_height)-1)*100:.0f}% larger)")

        # Create expanded tile grid
        new_tiles = self._create_expanded_grid(
            orig_tiles, orig_width, orig_height,
            target_width, target_height,
            map_id=map_data['id']
        )

        # Adjust objective positions (scale to new coordinate system)
        new_objectives = self._scale_objectives(
            map_data.get('objectives', []),
            orig_width, orig_height,
            target_width, target_height
        )

        # Adjust spawn points
        new_spawn_points = self._scale_spawn_points(
            map_data.get('spawn_points', []),
            orig_width, orig_height,
            target_width, target_height
        )

        # Build new map data
        new_map = {
            **map_data,
            'width': target_width,
            'height': target_height,
            'tiles': new_tiles,
            'objectives': new_objectives,
            'spawn_points': new_spawn_points,
            '_expanded': True,
            '_original_size': [orig_width, orig_height],
            '_expansion_version': '1.0'
        }

        return new_map

    def _create_expanded_grid(
        self,
        orig_tiles: list[list[int]],
        orig_w: int, orig_h: int,
        new_w: int, new_h: int,
        map_id: str = ""
    ) -> list[list[int]]:
        """
        Create expanded grid with intelligent terrain generation.
        
        Layout strategy:
        - Original map centered
        - Transition zone (3-5 tiles) with blended terrain
        - Outer border with varied terrain based on map context
        """
        # Initialize with default grass (terrain 2)
        grid = [[2 for _ in range(new_w)] for _ in range(new_h)]

        # Calculate offsets to center original map
        offset_x = (new_w - orig_w) // 2
        offset_y = (new_h - orig_h) // 2

        # Copy original tiles to center
        for y in range(orig_h):
            for x in range(orig_w):
                grid[offset_y + y][offset_x + x] = orig_tiles[y][x]

        # Analyze edge terrain of original map for context-aware expansion
        edge_terrain = self._analyze_edge_terrain(orig_tiles, orig_w, orig_h)

        # Generate transition zones and borders
        self._generate_transitions(grid, orig_w, orig_h, offset_x, offset_y, new_w, new_h, edge_terrain, map_id)
        
        # Add tactical features to border areas (variation prevents boredom)
        self._add_tactical_features(grid, orig_w, orig_h, offset_x, offset_y, new_w, new_h)

        return grid

    def _analyze_edge_terrain(self, tiles: list[list[int]], w: int, h: int) -> dict[str, int]:
        """Analyze what terrain types are on the edges of the original map."""
        edges = {
            'top': [],
            'bottom': [],
            'left': [],
            'right': []
        }
        
        # Top edge
        for x in range(w):
            edges['top'].append(tiles[0][x])
        # Bottom edge
        for x in range(w):
            edges['bottom'].append(tiles[h-1][x])
        # Left edge
        for y in range(h):
            edges['left'].append(tiles[y][0])
        # Right edge
        for y in range(h):
            edges['right'].append(tiles[y][w-1])

        # Find most common terrain per edge
        result = {}
        for edge_name, terrain_list in edges.items():
            if terrain_list:
                from collections import Counter
                counter = Counter(terrain_list)
                result[edge_name] = counter.most_common(1)[0][0]

        return result

    def _generate_transitions(
        self,
        grid: list[list[int]],
        orig_w: int, orig_h: int,
        off_x: int, off_y: int,
        new_w: int, new_h: int,
        edge_terrain: dict[str, int],
        map_id: str
    ) -> None:
        """Generate smooth terrain transitions from original map to borders."""

        # Transition zone width (in tiles)
        trans_width = 4

        for y in range(new_h):
            for x in range(new_w):
                # Skip if inside original map area
                if off_x <= x < off_x + orig_w and off_y <= y < off_y + orig_h:
                    continue

                # Calculate distance to original map boundary
                dist_to_orig = self._distance_to_original(x, y, off_x, off_y, orig_w, orig_h)

                if dist_to_orig <= trans_width:
                    # Transition zone: blend with nearest original terrain
                    nearest_orig_terrain = self._get_nearest_original_terrain(
                        x, y, off_x, off_y, orig_w, orig_h, grid
                    )
                    blend_factor = dist_to_orig / trans_width
                    
                    # Get border terrain type based on direction
                    border_type = self._determine_border_context(x, y, off_x, off_y, orig_w, orig_h, edge_terrain)
                    
                    # Blend between original and border terrain
                    if self.noise.noise2d(x, y, 0.3) > blend_factor:
                        grid[y][x] = nearest_orig_terrain
                    else:
                        weights = self.BORDER_TERRAIN_WEIGHTS.get(border_type, self.BORDER_TERRAIN_WEIGHTS['grassland'])
                        grid[y][x] = self._weighted_random(weights, seed=(x * 17 + y * 31 + self.seed))
                else:
                    # Far border: use pure border terrain with noise variation
                    border_type = self._determine_border_context(x, y, off_x, off_y, orig_w, orig_h, edge_terrain)
                    weights = self.BORDER_TERRAIN_WEIGHTS.get(border_type, self.BORDER_TERRAIN_WEIGHTS['grassland'])
                    
                    # Add noise-based variation
                    noise_val = self.noise.noise2d(x, y, 0.15)
                    if noise_val > 0.7:
                        # Occasional feature (forest cluster, rocky outcrop, etc.)
                        feature_weights = {3: 40, 4: 30, 9: 20, 5: 10}
                        grid[y][x] = self._weighted_random(feature_weights, seed=(x * 13 + y * 7 + self.seed))
                    elif noise_val < 0.2:
                        # Clearings in dense areas
                        grid[y][x] = 2  # Grass
                    else:
                        grid[y][x] = self._weighted_random(weights, seed=(x * 23 + y * 29 + self.seed))

    def _distance_to_original(self, x: int, y: int, ox: int, oy: int, ow: int, oh: int) -> float:
        """Calculate distance from point to original map rectangle."""
        if ox <= x < ox + ow and oy <= y < oy + oh:
            return 0.0
        
        # Distance to nearest edge of original rectangle
        dx = max(ox - x, 0, x - (ox + ow - 1))
        dy = max(oy - y, 0, y - (oy + oh - 1))
        return math.sqrt(dx*dx + dy*dy)

    def _get_nearest_original_terrain(self, x: int, y: int, ox: int, oy: int, ow: int, oh: int, grid: list[list[int]]) -> int:
        """Get terrain type from nearest cell in original map area."""
        # Clamp to original map bounds
        nx = max(ox, min(x, ox + ow - 1))
        ny = max(oy, min(y, oy + oh - 1))
        return grid[ny][nx]

    def _determine_border_context(
        self, x: int, y: int, ox: int, oy: int, ow: int, oh: int, edge_terrain: dict[str, int]
    ) -> str:
        """Determine what type of border terrain to use based on position and edge analysis."""
        
        # Determine which side(s) we're on
        is_top = y < oy
        is_bottom = y >= oy + oh
        is_left = x < ox
        is_right = x >= ox + ow

        # Check proximity to water (rivers/lakes often expand outward)
        near_water_top = is_top and edge_terrain.get('top', 2) in [6, 10]
        near_water_bottom = is_bottom and edge_terrain.get('bottom', 2) in [6, 10]
        near_water_left = is_left and edge_terrain.get('left', 2) in [6, 10]
        near_water_right = is_right and edge_terrain.get('right', 2) in [6, 10]

        if near_water_top or near_water_bottom or near_water_left or near_water_right:
            return 'waterfront'

        # Check proximity to urban areas
        near_urban_top = is_top and edge_terrain.get('top', 2) in [5, 8]
        near_urban_bottom = is_bottom and edge_terrain.get('bottom', 2) in [5, 8]
        near_urban_left = is_left and edge_terrain.get('left', 2) in [5, 8]
        near_urban_right = is_right and edge_terrain.get('right', 2) in [5, 8]

        if near_urban_top or near_urban_bottom or near_urban_left or near_urban_right:
            return 'urban_fringe'

        # Check proximity to forest
        near_forest_top = is_top and edge_terrain.get('top', 2) == 3
        near_forest_bottom = is_bottom and edge_terrain.get('bottom', 2) == 3
        near_forest_left = is_left and edge_terrain.get('left', 2) == 3
        near_forest_right = is_right and edge_terrain.get('right', 2) == 3

        if near_forest_top or near_forest_bottom or near_forest_left or near_forest_right:
            return 'forest_edge'

        # Default to rough/grassland mix
        if is_top or is_bottom:
            return 'rough' if self.noise.noise2d(x, y, 0.1) > 0.5 else 'grassland'
        else:
            return 'grassland'

    def _add_tactical_features(
        self, grid: list[list[int]], orig_w: int, orig_h: int,
        off_x: int, off_y: int, new_w: int, new_h: int
    ) -> None:
        """Add tactically interesting features to border areas to prevent empty feeling."""
        
        # Add scattered tree lines (provide cover and concealment)
        self._add_tree_lines(grid, off_x, off_y, orig_w, orig_h, new_w, new_h)
        
        # Add occasional rough terrain (affects movement)
        self._add_rough_patches(grid, new_w, new_h, density=0.03)
        
        # Add small buildings in urban-fringe areas
        self._add_outbuildings(grid, new_w, new_h, density=0.01)
        
        # Ensure roads connect where appropriate
        self._extend_roads(grid, off_x, off_y, orig_w, orig_h, new_w, new_h)

    def _add_tree_lines(self, grid: list[list[int]], ox: int, oy: int, ow: int, oh: int, nw: int, nh: int) -> None:
        """Add natural-looking tree lines along borders."""
        random.seed(self.seed + 100)
        
        # Add horizontal tree lines above and below original map
        if oy > 3:
            y_line = oy - 2
            start_x = max(0, ox - 3)
            end_x = min(nw, ox + ow + 3)
            for x in range(start_x, end_x):
                if random.random() < 0.6:  # 60% chance of tree
                    if grid[y_line][x] == 2:  # Only on grass
                        grid[y_line][x] = 3  # Forest

        if oy + oh < nh - 3:
            y_line = oy + oh + 1
            start_x = max(0, ox - 3)
            end_x = min(nw, ox + ow + 3)
            for x in range(start_x, end_x):
                if random.random() < 0.6:
                    if grid[y_line][x] == 2:
                        grid[y_line][x] = 3

        # Add vertical tree lines left and right
        if ox > 3:
            x_line = ox - 2
            start_y = max(0, oy - 3)
            end_y = min(nh, oy + oh + 3)
            for y in range(start_y, end_y):
                if random.random() < 0.6:
                    if grid[y][x_line] == 2:
                        grid[y][x_line] = 3

        if ox + ow < nw - 3:
            x_line = ox + ow + 1
            start_y = max(0, oy - 3)
            end_y = min(nh, oy + oh + 3)
            for y in range(start_y, end_y):
                if random.random() < 0.6:
                    if grid[y][x_line] == 2:
                        grid[y][x_line] = 3

    def _add_rough_patches(self, grid: list[list[int]], w: int, h: int, density: float) -> None:
        """Add small patches of rough terrain."""
        random.seed(self.seed + 200)
        num_patches = int(w * h * density)
        
        for _ in range(num_patches):
            px = random.randint(0, w - 1)
            py = random.randint(0, h - 1)
            size = random.randint(1, 3)
            
            # Create small patch
            for dy in range(size):
                for dx in range(size):
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        if grid[ny][nx] == 2:  # Only on grass
                            grid[ny][nx] = 9  # Rough ground

    def _add_outbuildings(self, grid: list[list[int]], w: int, h: int, density: float) -> None:
        """Add occasional small buildings."""
        random.seed(self.seed + 300)
        num_buildings = int(w * h * density)
        
        for _ in range(num_buildings):
            bx = random.randint(2, w - 3)
            by = random.randint(2, h - 3)
            
            # Only place on open ground
            if grid[by][bx] in [0, 1, 2]:
                # Small 2x2 or 1x2 building
                bw, bh = random.choice([(2, 2), (1, 2), (2, 1)])
                
                can_place = True
                for dy in range(bh):
                    for dx in range(bw):
                        if not (0 <= bx+dx < w and 0 <= by+dy < h):
                            can_place = False
                            break
                        if grid[by+dy][bx+dx] not in [0, 1, 2]:
                            can_place = False
                            break
                    if not can_place:
                        break
                
                if can_place:
                    for dy in range(bh):
                        for dx in range(bw):
                            grid[by+dy][bx+dx] = 5  # Building

    def _extend_roads(self, grid: list[list[int]], ox: int, oy: int, ow: int, oh: int, nw: int, nh: int) -> None:
        """Extend existing roads into border areas where logical."""
        # Find road edges on original map boundaries
        # Top edge
        if oy > 0:
            for x in range(ox, ox + ow):
                if grid[oy][x] == 1:  # Road
                    # Extend upward
                    for y in range(oy - 1, max(0, oy - 6), -1):
                        if grid[y][x] == 2:
                            grid[y][x] = 1
                        else:
                            break

        # Bottom edge
        if oy + oh < nh:
            for x in range(ox, ox + ow):
                if grid[oy + oh - 1][x] == 1:
                    # Extend downward
                    for y in range(oy + oh, min(nh, oy + oh + 6)):
                        if grid[y][x] == 2:
                            grid[y][x] = 1
                        else:
                            break

        # Left edge
        if ox > 0:
            for y in range(oy, oy + oh):
                if grid[y][ox] == 1:
                    # Extend leftward
                    for x in range(ox - 1, max(0, ox - 6), -1):
                        if grid[y][x] == 2:
                            grid[y][x] = 1
                        else:
                            break

        # Right edge
        if ox + ow < nw:
            for y in range(oy, oy + oh):
                if grid[y][ox + ow - 1] == 1:
                    # Extend rightward
                    for x in range(ox + ow, min(nw, ox + ow + 6)):
                        if grid[y][x] == 2:
                            grid[y][x] = 1
                        else:
                            break

    def _weighted_random(self, weights: dict[int, int], seed: int) -> int:
        """Random selection based on weights."""
        random.seed(seed)
        total = sum(weights.values())
        r = random.randint(1, total)
        cumulative = 0
        for item, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                return item
        return list(weights.keys())[0]

    def _scale_objectives(
        self, objectives: list[dict], old_w: int, old_h: int, new_w: int, new_h: int
    ) -> list[dict]:
        """Scale objective positions to new coordinate system."""
        scaled = []
        for obj in objectives:
            new_obj = obj.copy()
            if 'position' in obj:
                ox, oy = obj['position']
                # Scale position (keep relative location)
                new_x = int(ox * new_w / old_w)
                new_y = int(oy * new_h / old_h)
                new_obj['position'] = [new_x, new_y]
                
                # Scale radius if present
                if 'radius' in obj:
                    new_obj['radius'] = max(2, int(obj['radius'] * max(new_w/old_w, new_h/old_h)))
            
            scaled.append(new_obj)
        return scaled

    def _scale_spawn_points(
        self, spawn_points: list[dict], old_w: int, old_h: int, new_w: int, new_h: int
    ) -> list[dict]:
        """Scale spawn point positions to new coordinate system."""
        scaled = []
        for sp in spawn_points:
            new_sp = sp.copy()
            if 'position' in sp:
                px, py = sp['position']
                new_x = int(px * new_w / old_w)
                new_y = int(py * new_h / old_h)
                new_sp['position'] = [new_x, new_y]
                
                # Increase unit capacity for larger maps
                if 'units_max' in sp:
                    new_sp['units_max'] = int(sp['units_max'] * (new_w * new_h) / (old_w * old_h))
            
            scaled.append(new_sp)
        return scaled


def main():
    """Main execution function."""
    base_path = Path('/Users/lin/trae_projects/PyCC2/data/maps')
    
    # Define expansion targets for each map
    expansion_targets = {
        'tutorial': (24, 20),
        'bridge_assault': (32, 28),
        'defense_line': (30, 26),
        'night_map': (28, 24),
        'road_ambush': (48, 28),  # Wide ambush map - expand proportionally
        'son_bridge': (34, 30),
        'veghel': (36, 32),
        'grave': (38, 34),
        'nijmegen': (40, 35),
        'arnhem': (50, 42),  # ⭐ FLAGSHIP - Largest battle
    }

    expander = MapExpander(seed=42)

    print("=" * 80)
    print("🗺️  PYCC2 MAP EXPANSION - PHASE A1")
    print("   Aggressively expanding all maps to CC2-standard sizes")
    print("=" * 80)
    print()

    success_count = 0
    fail_count = 0

    for map_file in sorted(base_path.glob('*.json')):
        if map_file.name.startswith('_'):
            continue  # Skip schema files

        try:
            with open(map_file, 'r') as f:
                map_data = json.load(f)

            map_id = map_data['id']

            if map_id not in expansion_targets:
                print(f"⚠️  Skipping {map_id}: No expansion target defined")
                continue

            target_w, target_h = expansion_targets[map_id]

            # Expand the map
            expanded_map = expander.expand_map(map_data, target_w, target_h)

            # Backup original file
            backup_path = map_file.with_suffix('.json.backup')
            if not backup_path.exists():
                import shutil
                shutil.copy2(map_file, backup_path)
                print(f"💾 Backed up: {backup_path.name}")

            # Write expanded map
            with open(map_file, 'w') as f:
                json.dump(expanded_map, f, indent=2)

            orig_area = map_data['width'] * map_data['height']
            new_area = target_w * target_h
            increase_pct = ((new_area / orig_area) - 1) * 100

            print(f"✅ {map_id:20s}: {map_data['width']:2d}×{map_data['height']:2d} → "
                  f"{target_w:2d}×{target_h:2d} ({increase_pct:+.0f}% area)")
            success_count += 1

        except Exception as e:
            print(f"❌ Error processing {map_file.name}: {e}")
            fail_count += 1

    print()
    print("=" * 80)
    print(f"🎉 EXPANSION COMPLETE: {success_count} maps expanded, {fail_count} failed")
    print("=" * 80)
    
    print("\n📊 SUMMARY OF CHANGES:")
    print("-" * 80)
    total_orig = 0
    total_new = 0
    for map_id, (tw, th) in sorted(expansion_targets.items()):
        orig_file = base_path / f"{map_id}.json"
        if orig_file.exists():
            with open(orig_file, 'r') as f:
                data = json.load(f)
            orig_size = data.get('_original_size', '?')
            print(f"  {map_id:20s}: original={str(orig_size):>10s} → current={data['width']:2d}×{data['height']:2d}")
            if isinstance(orig_size, list):
                total_orig += orig_size[0] * orig_size[1]
            total_new += tw * th
    
    if total_orig > 0:
        print(f"\n  {'TOTAL':20s}: {total_orig:>10,d} tiles → {total_new:>10,d} tiles "
              f"({((total_new/total_orig)-1)*100:.0f}% increase)")


if __name__ == '__main__':
    main()
