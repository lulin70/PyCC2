"""Smoke test: capture screenshots of actual game rendering."""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pygame

from pycc2.domain.value_objects.building_data import CC2BuildingType
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.presentation.rendering.cc2_building_renderer import (
    DamageLevel,
    render_cc2_building,
)
from pycc2.presentation.rendering.pixel_artist import (
    create_terrain_tile,
)
from pycc2.presentation.rendering.pixel_artist_3d import (
    Direction,
    Faction,
    InfantryType,
    PixelArtist3D,
    TankType,
)

OUT = os.path.join(os.path.dirname(__file__), "..", "screenshots", "smoke_test")
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(OUT, "terrain"), exist_ok=True)
os.makedirs(os.path.join(OUT, "units"), exist_ok=True)
os.makedirs(os.path.join(OUT, "buildings"), exist_ok=True)

pygame.init()
screen = pygame.display.set_mode((1280, 720))

# 1. Terrain tiles at 4x zoom
print("=== Terrain Tiles ===")
for tt in TerrainType:
    try:
        canvas = create_terrain_tile(tt.value, size=48)
        tile = canvas.to_surface()
        scaled = pygame.transform.scale(tile, (tile.get_width() * 4, tile.get_height() * 4))
        pygame.image.save(scaled, os.path.join(OUT, "terrain", f"{tt.name}.png"))
        print(f"  OK: {tt.name}")
    except Exception as e:
        print(f"  ERROR: {tt.name}: {e}")

# 2. Unit sprites at 4x zoom
print("\n=== Infantry Sprites ===")
for itype in InfantryType:
    for direction in Direction:
        try:
            sprite = PixelArtist3D.create_infantry_sprite(
                direction=direction,
                faction=Faction.ALLIES,
                state="idle",
                frame=0,
                infantry_type=itype,
            )
            if sprite:
                scaled = pygame.transform.scale(
                    sprite, (sprite.get_width() * 4, sprite.get_height() * 4)
                )
                pygame.image.save(
                    scaled,
                    os.path.join(OUT, "units", f"infantry_{itype.value}_{direction.name}.png"),
                )
        except Exception as e:
            print(f"  ERROR: infantry {itype.value} {direction.name}: {e}")
    print(f"  OK: infantry_{itype.value} (8 directions)")

# Axis infantry (one type, all directions)
print("\n=== Axis Infantry (Rifleman) ===")
for direction in Direction:
    try:
        sprite = PixelArtist3D.create_infantry_sprite(
            direction=direction,
            faction=Faction.AXIS,
            state="idle",
            frame=0,
            infantry_type=InfantryType.RIFLEMAN,
        )
        if sprite:
            scaled = pygame.transform.scale(
                sprite, (sprite.get_width() * 4, sprite.get_height() * 4)
            )
            pygame.image.save(
                scaled, os.path.join(OUT, "units", f"axis_rifleman_{direction.name}.png")
            )
    except Exception as e:
        print(f"  ERROR: axis rifleman {direction.name}: {e}")
print("  OK: axis_rifleman (8 directions)")

# Tank sprites
print("\n=== Tank Sprites ===")
for tank_type in TankType:
    for faction in Faction:
        try:
            sprite = PixelArtist3D.create_tank_sprite(
                direction=Direction.NORTH,
                faction=faction,
                state="idle",
                frame=0,
                tank_type=tank_type,
            )
            if sprite:
                scaled = pygame.transform.scale(
                    sprite, (sprite.get_width() * 3, sprite.get_height() * 3)
                )
                pygame.image.save(
                    scaled,
                    os.path.join(
                        OUT, "units", f"tank_{tank_type.value}_{faction.name.lower()}.png"
                    ),
                )
                print(f"  OK: tank_{tank_type.value}_{faction.name.lower()}")
        except Exception as e:
            print(f"  ERROR: tank {tank_type.value} {faction.name.lower()}: {e}")

# Halftrack
print("\n=== Halftrack Sprite ===")
try:
    ht = PixelArtist3D.create_halftrack_sprite(
        direction=Direction.NORTH,
        faction=Faction.ALLIES,
        state="idle",
        frame=0,
    )
    if ht:
        scaled = pygame.transform.scale(ht, (ht.get_width() * 3, ht.get_height() * 3))
        pygame.image.save(scaled, os.path.join(OUT, "units", "halftrack_allies.png"))
        print("  OK: halftrack_allies")
except Exception as e:
    print(f"  ERROR: halftrack: {e}")

# Jeep
try:
    jeep = PixelArtist3D.create_jeep_sprite(
        direction=Direction.NORTH,
        faction=Faction.ALLIES,
        state="idle",
        frame=0,
    )
    if jeep:
        scaled = pygame.transform.scale(jeep, (jeep.get_width() * 4, jeep.get_height() * 4))
        pygame.image.save(scaled, os.path.join(OUT, "units", "jeep_allies.png"))
        print("  OK: jeep_allies")
except Exception as e:
    print(f"  ERROR: jeep: {e}")

# AT Gun
try:
    at_gun = PixelArtist3D.create_at_gun_sprite(
        direction=Direction.NORTH,
        faction=Faction.ALLIES,
        state="idle",
        frame=0,
    )
    if at_gun:
        scaled = pygame.transform.scale(at_gun, (at_gun.get_width() * 4, at_gun.get_height() * 4))
        pygame.image.save(scaled, os.path.join(OUT, "units", "at_gun_allies.png"))
        print("  OK: at_gun_allies")
except Exception as e:
    print(f"  ERROR: at_gun: {e}")

# Tree
try:
    tree = PixelArtist3D.create_tree_sprite(variant=0)
    if tree:
        scaled = pygame.transform.scale(tree, (tree.get_width() * 4, tree.get_height() * 4))
        pygame.image.save(scaled, os.path.join(OUT, "terrain", "tree_3d.png"))
        print("  OK: tree_3d")
except Exception as e:
    print(f"  ERROR: tree: {e}")

# Building sprite (3D style)
try:
    bldg = PixelArtist3D.create_building_sprite(building_type="house")
    if bldg:
        scaled = pygame.transform.scale(bldg, (bldg.get_width() * 2, bldg.get_height() * 2))
        pygame.image.save(scaled, os.path.join(OUT, "buildings", "house_3d.png"))
        print("  OK: house_3d")
except Exception as e:
    print(f"  ERROR: house_3d: {e}")

# 3. Buildings (CC2 top-down style) at 2x zoom
print("\n=== CC2 Buildings (Top-Down) ===")
for btype in CC2BuildingType:
    for damage in DamageLevel:
        try:
            bldg = render_cc2_building(
                building_type=btype,
                damage=damage,
                tile_size=48,
            )
            if bldg:
                scaled = pygame.transform.scale(bldg, (bldg.get_width() * 2, bldg.get_height() * 2))
                pygame.image.save(
                    scaled, os.path.join(OUT, "buildings", f"{btype.value}_{damage.name}.png")
                )
                print(f"  OK: {btype.value}_{damage.name}")
        except Exception as e:
            print(f"  ERROR: {btype.value}_{damage.name}: {e}")

# 4. Infantry animation sheet
print("\n=== Infantry Animation Sheet ===")
try:
    sheet, dir_order, anim_order = PixelArtist3D.create_infantry_animation_sheet(
        faction=Faction.ALLIES,
        infantry_type=InfantryType.RIFLEMAN,
    )
    scaled = pygame.transform.scale(sheet, (sheet.get_width() * 2, sheet.get_height() * 2))
    pygame.image.save(scaled, os.path.join(OUT, "infantry_anim_sheet_allies.png"))
    print("  OK: infantry_anim_sheet_allies")

    sheet_axis, _, _ = PixelArtist3D.create_infantry_animation_sheet(
        faction=Faction.AXIS,
        infantry_type=InfantryType.RIFLEMAN,
    )
    scaled = pygame.transform.scale(
        sheet_axis, (sheet_axis.get_width() * 2, sheet_axis.get_height() * 2)
    )
    pygame.image.save(scaled, os.path.join(OUT, "infantry_anim_sheet_axis.png"))
    print("  OK: infantry_anim_sheet_axis")
except Exception as e:
    print(f"  ERROR: animation_sheet: {e}")

# 5. Full battle scene using EnhancedRenderer
print("\n=== Battle Scene ===")
try:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

    tile_grid = np.zeros((15, 20), dtype=np.int8)
    rng = np.random.RandomState(42)
    for y in range(15):
        for x in range(20):
            r = rng.random()
            if r < 0.45:
                tile_grid[y, x] = TerrainType.GRASS.value
            elif r < 0.65:
                tile_grid[y, x] = TerrainType.OPEN.value
            elif r < 0.75:
                tile_grid[y, x] = TerrainType.WOODS.value
            elif r < 0.82:
                tile_grid[y, x] = TerrainType.ROAD.value
            elif r < 0.88:
                tile_grid[y, x] = TerrainType.HEDGE.value
            elif r < 0.92:
                tile_grid[y, x] = TerrainType.BUILDING_ENTERABLE.value
            elif r < 0.95:
                tile_grid[y, x] = TerrainType.WATER.value
            elif r < 0.97:
                tile_grid[y, x] = TerrainType.ROUGH.value
            else:
                tile_grid[y, x] = TerrainType.CRATER.value

    gmap = GameMap(
        id="smoke_test",
        name="Smoke Test Map",
        width=20,
        height=15,
        tile_grid=tile_grid,
    )

    renderer_full = EnhancedRenderer()
    renderer_full.initialize(screen)
    camera = Camera(
        position=Vec2(0, 0), viewport_width=screen.get_width(), viewport_height=screen.get_height()
    )

    renderer_full.render(
        game_map=gmap,
        units=[],
        camera=camera,
    )
    pygame.image.save(screen, os.path.join(OUT, "battle_scene.png"))
    print("  OK: battle_scene")
except Exception as e:
    import traceback

    print(f"  ERROR: battle_scene: {e}")
    traceback.print_exc()

# 6. Composite showcase image
print("\n=== Composite Showcase ===")
try:
    showcase = pygame.Surface((1280, 720))
    showcase.fill((30, 50, 30))

    # Terrain row
    x_off = 10
    for tt in [
        TerrainType.GRASS,
        TerrainType.ROAD,
        TerrainType.WOODS,
        TerrainType.WATER,
        TerrainType.HEDGE,
        TerrainType.BUILDING_ENTERABLE,
        TerrainType.ROUGH,
        TerrainType.CRATER,
        TerrainType.SWAMP,
    ]:
        canvas = create_terrain_tile(tt.value, size=48)
        tile = canvas.to_surface()
        scaled = pygame.transform.scale(tile, (96, 96))
        showcase.blit(scaled, (x_off, 10))
        x_off += 100

    # Infantry row (allies + axis)
    x_off = 10
    for direction in Direction:
        sprite = PixelArtist3D.create_infantry_sprite(
            direction, Faction.ALLIES, "idle", 0, InfantryType.RIFLEMAN
        )
        scaled = pygame.transform.scale(sprite, (96, 96))
        showcase.blit(scaled, (x_off, 120))
        x_off += 100

    x_off = 10
    for direction in Direction:
        sprite = PixelArtist3D.create_infantry_sprite(
            direction, Faction.AXIS, "idle", 0, InfantryType.RIFLEMAN
        )
        scaled = pygame.transform.scale(sprite, (96, 96))
        showcase.blit(scaled, (x_off, 230))
        x_off += 100

    # Tank row
    x_off = 10
    for tank_type in TankType:
        for faction in [Faction.ALLIES, Faction.AXIS]:
            sprite = PixelArtist3D.create_tank_sprite(Direction.NORTH, faction, tank_type=tank_type)
            scaled = pygame.transform.scale(
                sprite, (sprite.get_width() * 2, sprite.get_height() * 2)
            )
            showcase.blit(scaled, (x_off, 340))
            x_off += sprite.get_width() * 2 + 10

    # Building row
    x_off = 10
    for btype in CC2BuildingType:
        bldg = render_cc2_building(btype, DamageLevel.INTACT, tile_size=48)
        scaled = pygame.transform.scale(bldg, (bldg.get_width(), bldg.get_height()))
        showcase.blit(scaled, (x_off, 460))
        x_off += bldg.get_width() + 10

    pygame.image.save(showcase, os.path.join(OUT, "composite_showcase.png"))
    print("  OK: composite_showcase")
except Exception as e:
    import traceback

    print(f"  ERROR: composite_showcase: {e}")
    traceback.print_exc()

pygame.quit()
print(f"\nScreenshots saved to: {OUT}")
