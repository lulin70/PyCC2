#!/usr/bin/env python3
"""
PyCC2 Visual Verification Script - Generate key scene screenshots for CC2 comparison analysis.

Generated content:
1. Terrain texture samples (grass/road/river/hedgerow)
2. Infantry sprites (8 directions + standing/prone)
3. Tank sprites (Sherman/Panther/Tiger I with armor seams)
4. Building sprites (Normandy farmhouse/barn - TOP-DOWN VIEW!)
5. Complete UI panel screenshot
6. Faction color comparison
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pygame
pygame.init()

from pycc2.presentation.rendering.pixel_artist_3d import (
    PixelArtist3D, Direction, Faction, InfantryType, TankType
)
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
from pycc2.presentation.rendering.cc2_building_renderer import (
    CC2BuildingType, DamageLevel, render_cc2_building
)
from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel

OUTPUT_DIR = "visual_verification"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_sprite_sheet(sprites_dict, filename, title, cell_size=(48, 48)):
    """Create sprite comparison sheet with English labels only."""
    max_cols = 8
    num_sprites = len(sprites_dict)
    cols = min(max_cols, num_sprites)
    rows = (num_sprites + cols - 1) // cols

    w = cols * cell_size[0] + (cols-1) * 4
    h = rows * cell_size[1] + (rows-1) * 4 + 30

    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    surface.fill((40, 44, 52))

    font = pygame.font.SysFont('arial', 14, bold=True)
    title_surf = font.render(title, True, (255, 255, 100))
    surface.blit(title_surf, (10, 5))

    for idx, (name, sprite) in enumerate(sprites_dict.items()):
        col = idx % cols
        row = idx // cols
        x = col * (cell_size[0] + 4) + 2
        y = row * (cell_size[1] + 4) + 32

        if sprite:
            surface.blit(sprite, (x, y))

        label_font = pygame.font.SysFont('arial', 9)
        display_name = name[:15] if len(name) > 15 else name
        label = label_font.render(display_name, True, (200, 200, 200))
        surface.blit(label, (x, y + cell_size[1] + 1))

    path = os.path.join(OUTPUT_DIR, filename)
    pygame.image.save(surface, path)
    print(f"[OK] Saved: {path}")
    return surface

def generate_infantry_comparison():
    """Generate infantry sprite comparison (8-dir standing + 4-dir prone)."""
    print("\n[1/6] Generating infantry sprites...")

    sprites = {}

    # Standing pose - 8 directions
    for dir_idx, direction in enumerate(Direction):
        sprite = PixelArtist3D.create_infantry_sprite(
            direction=direction,
            faction=Faction.ALLIES,
            state="idle",
            infantry_type=InfantryType.RIFLEMAN,
        )
        sprites[f"N{dir_idx}_{direction.name}"] = sprite

    # Prone pose - 4 main directions (single soldier prone down, CC2 standard)
    prone_directions = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
    for direction in prone_directions:
        sprite = PixelArtist3D.create_infantry_sprite(
            direction=direction,
            faction=Faction.ALLIES,
            state="defend",  # Single prone (CC2: defend/crawl = single soldier prone)
            infantry_type=InfantryType.RIFLEMAN,
        )
        sprites[f"PRONE_{direction.name}"] = sprite

    create_sprite_sheet(sprites, "01_infantry_8dir_prone.png",
                        "Infantry: 8-Dir Standing + 4-Dir Prone (Single Soldier)", (28, 28))

def generate_tank_comparison():
    """Generate tank sprite comparison (with armor panel seams)."""
    print("\n[2/6] Generating tank sprites (with armor seams)...")

    sprites = {}

    tank_types = [
        (TankType.SHERMAN_M4, "US", "Sherman_M4"),
        (TankType.PANTHER_AUSFG, "DE", "Panther_G"),
        (TankType.TIGER_I, "DE", "Tiger_I"),
    ]

    for tank_type, faction_name, tank_name in tank_types:
        faction = Faction.ALLIES if faction_name == "US" else Faction.AXIS

        # North direction
        sprite_n = PixelArtist3D.create_tank_sprite(
            direction=Direction.NORTH,
            faction=faction,
            tank_type=tank_type,
        )
        sprites[f"{tank_name}_N"] = sprite_n

        # East direction (shows side profile)
        sprite_e = PixelArtist3D.create_tank_sprite(
            direction=Direction.EAST,
            faction=faction,
            tank_type=tank_type,
        )
        sprites[f"{tank_name}_E"] = sprite_e

    create_sprite_sheet(sprites, "02_tanks_with_seams.png",
                        "Tanks: Sherman/Panther/Tiger (Size Diff + Armor Seams)", (50, 50))

def generate_terrain_textures():
    """Generate terrain texture samples."""
    print("\n[3/6] Generating terrain textures (high-density)...")

    renderer = EnhancedRenderer()

    terrain_configs = [
        (0, "GRASS", 0),
        (1, "ROAD", 0),
        (6, "WATER", 0),
        (7, "HEDGE", 0),
        (9, "DIRT", 0),
        (13, "TRENCH", 0),
    ]

    sprites = {}

    for tid, name, bitmask in terrain_configs:
        try:
            tile_surface = renderer._generate_cc2_style_tile(tid, 0, 0, bitmask=bitmask)
            if tile_surface:
                sprites[name] = tile_surface
                tile_connected = renderer._generate_cc2_style_tile(tid, 0, 0, bitmask=15)
                if tile_connected:
                    sprites[f"{name}_conn"] = tile_connected
        except Exception as e:
            print(f"  [WARN] Failed to generate {name}: {e}")

    if len(sprites) > 0:
        create_sprite_sheet(sprites, "03_terrain_textures.png",
                            f"Terrain: High-Density ({len(sprites)} samples)", (52, 52))
    else:
        print("  [FAIL] No terrain textures generated")

def generate_buildings():
    """Generate building sprites (Normandy style - TOP-DOWN VIEW + INTERIOR!)."""
    print("\n[4/6] Generating buildings (TOP-DOWN + INTERIOR views)...")

    sprites = {}

    building_types = [
        (CC2BuildingType.SMALL_HOUSE, "Small_House"),
        (CC2BuildingType.MEDIUM_HOUSE, "Medium_House"),
        (CC2BuildingType.NORMANDY_FARMHOUSE, "Normandy_Farm"),
        (CC2BuildingType.NORMANDY_BARN, "Normandy_Barn"),
        (CC2BuildingType.CHURCH, "Church"),
    ]

    for bt, name in building_types:
        # Intact state (roof view)
        sprite_intact = render_cc2_building(
            building_type=bt,
            damage=DamageLevel.INTACT,
            show_number=True,
            number="2",
        )
        sprites[f"{name}_Roof"] = sprite_intact

        # *** NEW: Interior view (floor + windows!) ***
        sprite_interior = render_cc2_building(
            building_type=bt,
            damage=DamageLevel.INTACT,
            interior_mode=True,
            occupant_positions=[(24, 24), (40, 32)],  # Sample occupant positions
        )
        sprites[f"{name}_Floor"] = sprite_interior

        # Light damage (interior with cracks)
        sprite_dmg_int = render_cc2_building(
            building_type=bt,
            damage=DamageLevel.LIGHT_DAMAGE,
            interior_mode=True,
        )
        sprites[f"{name}_DmgFlr"] = sprite_dmg_int

    create_sprite_sheet(sprites, "04_buildings_normandy.png",
                        "Buildings: Roof + INTERIOR Floor + Windows", (52, 52))

def generate_ui_panel():
    """Generate UI panel screenshot."""
    print("\n[5/6] Generating UI panel...")

    panel = CC2BottomPanel()
    panel.initialize()

    w, h = 1024, 130
    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    surface.fill((30, 33, 38))

    from pycc2.domain.entities.game_map import GameMap
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.minimap import Minimap

    camera = Camera(position=None, viewport_width=w, viewport_height=h*2)
    minimap = Minimap()

    panel.render(surface, camera, None, minimap, time_remaining=245)

    path = os.path.join(OUTPUT_DIR, "05_ui_panel_timer.png")
    pygame.image.save(surface, path)
    print(f"[OK] Saved: {path}")

def generate_faction_colors():
    """Generate faction color comparison."""
    print("\n[6/6] Generating faction uniform colors...")

    sprites = {}

    # Allied uniforms
    for dir_idx, direction in enumerate([Direction.NORTH, Direction.EAST, Direction.SOUTH]):
        sprite_allies = PixelArtist3D.create_infantry_sprite(
            direction=direction,
            faction=Faction.ALLIES,
            state="idle",
            infantry_type=InfantryType.RIFLEMAN,
        )
        sprites[f"US_OD_{direction.name}"] = sprite_allies

    # Axis uniforms
    for dir_idx, direction in enumerate([Direction.NORTH, Direction.EAST, Direction.SOUTH]):
        sprite_axis = PixelArtist3D.create_infantry_sprite(
            direction=direction,
            faction=Faction.AXIS,
            state="idle",
            infantry_type=InfantryType.RIFLEMAN,
        )
        sprites[f"DE_FG_{direction.name}"] = sprite_axis

    create_sprite_sheet(sprites, "06_faction_uniforms.png",
                        "Factions: US Olive Drab vs German Feldgrau (Historical)", (28, 28))

def main():
    """Main function."""
    print("=" * 60)
    print("PyCC2 Visual Verification System")
    print("Generate screenshots for CC2 original comparison")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}/")

    try:
        generate_infantry_comparison()
        generate_tank_comparison()
        generate_terrain_textures()
        generate_buildings()
        generate_ui_panel()
        generate_faction_colors()

        print("\n" + "=" * 60)
        print("[DONE] Visual verification complete!")
        print("=" * 60)
        print(f"\nCheck {OUTPUT_DIR}/ for 6 comparison images:")
        print("  01_infantry_8dir_prone.png  - Infantry 8-dir + prone")
        print("  02_tanks_with_seams.png     - Tanks (size diff + seams)")
        print("  03_terrain_textures.png     - High-density terrain")
        print("  04_buildings_normandy.png    - Buildings (TOP-DOWN view)")
        print("  05_ui_panel_timer.png       - UI Panel (TIMER)")
        print("  06_faction_uniforms.png     - Faction uniforms")
        print("\nKey checks:")
        print("  - Prone: elongated shape (16x5px)? Direction clear?")
        print("  - Tanks: 1px armor seams? Size differentiated?")
        print("  - Hedgerows: thick enough (10-16px)? Irregular edges?")
        print("  - Uniforms: US=(112,108,76) OD green, NOT bright green")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
