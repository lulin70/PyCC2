"""Run the game and capture screenshots for comparison with CC2.

Initializes pygame in headless mode, loads a map, creates units,
renders one frame of the battle phase and one of the deployment phase,
then saves both screenshots to the screenshots/ directory.
"""
import os
import sys

# Headless rendering — must be set before any pygame import
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import json
import numpy as np
import pygame

# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 1024, 768
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")


def create_game_map() -> "GameMap":
    """Create a test map with varied terrain, buildings, and objectives."""
    from pycc2.domain.entities.game_map import GameMap, MapObjective
    from pycc2.domain.value_objects.tile_coord import TileCoord

    width, height = 30, 24
    # Start with grass (2) everywhere
    grid = np.full((height, width), 2, dtype=np.int8)

    # Add a road through the middle
    for x in range(width):
        grid[12, x] = 1  # ROAD
        grid[11, x] = 1

    # Add buildings
    for bx in range(10, 14):
        for by in range(8, 11):
            grid[by, bx] = 4  # BUILDING_ENTERABLE
    for bx in range(18, 22):
        for by in range(14, 17):
            grid[by, bx] = 5  # BUILDING_SOLID

    # Add woods
    for wx in range(0, 5):
        for wy in range(0, 5):
            grid[wy, wx] = 3  # WOODS

    # Add water
    for wx in range(24, 30):
        for wy in range(0, 6):
            grid[wy, wx] = 6  # WATER

    # Add hedges
    for hx in range(5, 10):
        grid[5, hx] = 7  # HEDGE

    objectives = [
        MapObjective(
            id="vl_bridge",
            name="Bridge",
            position=TileCoord(15, 12),
            radius=2,
            required=True,
        ),
        MapObjective(
            id="vl_church",
            name="Church",
            position=TileCoord(12, 9),
            radius=1,
            required=True,
        ),
    ]

    return GameMap(
        id="screenshot_map",
        name="Screenshot Test Map",
        width=width,
        height=height,
        tile_grid=grid,
        objectives=objectives,
    )


def create_units() -> list:
    """Create a set of allied and axis units for the screenshot."""
    from pycc2.domain.components.health_component import HealthComponent
    from pycc2.domain.components.morale_component import MoraleComponent
    from pycc2.domain.components.position_component import PositionComponent
    from pycc2.domain.components.vision_component import VisionComponent
    from pycc2.domain.components.weapon_component import WeaponComponent
    from pycc2.domain.entities.unit import Faction, Unit, UnitType
    from pycc2.domain.value_objects.tile_coord import TileCoord

    units = []

    # Allied infantry squads
    for i, (x, y) in enumerate([(6, 10), (8, 14), (5, 8)]):
        units.append(Unit(
            id=f"ally_inf_{i}",
            name=f"Rifle Squad {i+1}",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            position=PositionComponent(tile_coord=TileCoord(x, y)),
            vision=VisionComponent(),
            health=HealthComponent(hp=100, max_hp=100),
            weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
            morale=MoraleComponent(value=75),
        ))

    # Allied MG team
    units.append(Unit(
        id="ally_mg_0",
        name="MG Team Alpha",
        faction=Faction.ALLIES,
        unit_type=UnitType.MACHINE_GUN_SQUAD,
        position=PositionComponent(tile_coord=TileCoord(7, 12)),
        vision=VisionComponent(),
        health=HealthComponent(hp=80, max_hp=80),
        weapon=WeaponComponent(primary_weapon_id="mg42", max_ammo=250, ammo_remaining=250),
        morale=MoraleComponent(value=80),
    ))

    # Allied tank
    units.append(Unit(
        id="ally_tank_0",
        name="Sherman",
        faction=Faction.ALLIES,
        unit_type=UnitType.TANK,
        position=PositionComponent(tile_coord=TileCoord(9, 12)),
        vision=VisionComponent(),
        health=HealthComponent(hp=200, max_hp=200),
        weapon=WeaponComponent(primary_weapon_id="tank_cannon", max_ammo=30, ammo_remaining=30),
        morale=MoraleComponent(value=90),
    ))

    # Allied commander
    units.append(Unit(
        id="ally_cmd_0",
        name="Captain Ness",
        faction=Faction.ALLIES,
        unit_type=UnitType.COMMANDER,
        position=PositionComponent(tile_coord=TileCoord(6, 12)),
        vision=VisionComponent(),
        health=HealthComponent(hp=100, max_hp=100),
        weapon=WeaponComponent(primary_weapon_id="pistol", max_ammo=14, ammo_remaining=14),
        morale=MoraleComponent(value=95),
    ))

    # Axis infantry
    for i, (x, y) in enumerate([(22, 10), (24, 14), (20, 8)]):
        units.append(Unit(
            id=f"axis_inf_{i}",
            name=f"Grenadier {i+1}",
            faction=Faction.AXIS,
            unit_type=UnitType.INFANTRY_SQUAD,
            position=PositionComponent(tile_coord=TileCoord(x, y)),
            vision=VisionComponent(),
            health=HealthComponent(hp=100, max_hp=100),
            weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
            morale=MoraleComponent(value=70),
        ))

    # Axis tank
    units.append(Unit(
        id="axis_tank_0",
        name="Panther",
        faction=Faction.AXIS,
        unit_type=UnitType.TANK,
        position=PositionComponent(tile_coord=TileCoord(23, 12)),
        vision=VisionComponent(),
        health=HealthComponent(hp=200, max_hp=200),
        weapon=WeaponComponent(primary_weapon_id="tank_cannon", max_ammo=30, ammo_remaining=30),
        morale=MoraleComponent(value=85),
    ))

    return units


def render_battle_screenshot(screen, game_map, units) -> pygame.Surface:
    """Render a battle-phase frame and return the surface."""
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
    from pycc2.domain.value_objects.vec2 import Vec2

    renderer = EnhancedRenderer()
    renderer.initialize(screen)

    camera = Camera(
        position=Vec2(400, 300),
        viewport_width=SCREEN_W,
        viewport_height=SCREEN_H,
    )

    # Select first allied unit for visual feedback
    selected = {u.id for u in units if u.faction.name == "ALLIES"} if units else set()

    renderer.render(
        game_map=game_map,
        units=units,
        camera=camera,
        alpha=1.0,
        selected_unit_ids=selected,
        debug_mode=False,
    )

    # Blit offscreen to screen
    if renderer._offscreen is not None:
        screen.blit(renderer._offscreen, (0, 0))

    return screen


def render_deployment_screenshot(screen, game_map) -> pygame.Surface:
    """Render a deployment-phase frame and return the surface."""
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
    from pycc2.services.deployment_manager import DeploymentManager
    from pycc2.domain.value_objects.vec2 import Vec2

    renderer = EnhancedRenderer()
    renderer.initialize(screen)

    camera = Camera(
        position=Vec2(400, 300),
        viewport_width=SCREEN_W,
        viewport_height=SCREEN_H,
    )

    # Start deployment
    dm = DeploymentManager()
    map_data = {
        "width": game_map.width,
        "height": game_map.height,
        "tiles": [[int(game_map.tile_grid[y, x]) for x in range(game_map.width)]
                   for y in range(game_map.height)],
        "spawn_points": [
            {"id": "sp_ally", "side": "ally", "position": [5, 10], "units_max": 6},
            {"id": "sp_axis", "side": "axis", "position": [25, 10], "units_max": 6},
        ],
        "objectives": [],
    }

    try:
        dm.start(map_data=map_data, faction="ally")
    except Exception as e:
        print(f"[WARN] Deployment start failed (non-fatal for screenshot): {e}")

    # Render the map as background
    renderer.render(
        game_map=game_map,
        units=[],
        camera=camera,
        alpha=1.0,
        selected_unit_ids=set(),
        debug_mode=False,
    )

    if renderer._offscreen is not None:
        screen.blit(renderer._offscreen, (0, 0))

    # Draw deployment zone indicator
    font = pygame.font.Font(None, 24)
    label = font.render("DEPLOYMENT PHASE", True, (255, 255, 0))
    screen.blit(label, (SCREEN_W // 2 - label.get_width() // 2, 10))

    # Draw spawn zone rectangle
    pygame.draw.rect(screen, (0, 255, 0), (5 * 48, 10 * 48, 6 * 48, 6 * 48), 2)

    return screen


def main():
    """Main entry point: initialize, render, save screenshots."""
    # Create output directory
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # Initialize pygame
    pygame.init()
    try:
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        print(f"[OK] Pygame display initialized ({SCREEN_W}x{SCREEN_H})")
    except pygame.error as e:
        print(f"[WARN] Could not create display: {e}")
        print("[INFO] Using Surface fallback")
        screen = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

    # Create game map and units
    game_map = create_game_map()
    units = create_units()
    print(f"[OK] Map created: {game_map.width}x{game_map.height}")
    print(f"[OK] Units created: {len(units)} ({sum(1 for u in units if u.faction.name == 'ALLIES')} allies, "
          f"{sum(1 for u in units if u.faction.name == 'AXIS')} axis)")

    # ---- Battle phase screenshot ----
    print("[INFO] Rendering battle phase...")
    try:
        battle_screen = render_battle_screenshot(screen, game_map, units)
        battle_path = os.path.join(SCREENSHOT_DIR, "current_state.png")
        pygame.image.save(battle_screen, battle_path)
        print(f"[OK] Battle screenshot saved: {battle_path}")
    except Exception as e:
        print(f"[ERROR] Battle screenshot failed: {e}")
        import traceback
        traceback.print_exc()

    # ---- Deployment phase screenshot ----
    print("[INFO] Rendering deployment phase...")
    try:
        # Clear screen for deployment render
        screen.fill((0, 0, 0))
        deploy_screen = render_deployment_screenshot(screen, game_map)
        deploy_path = os.path.join(SCREENSHOT_DIR, "deployment_phase.png")
        pygame.image.save(deploy_screen, deploy_path)
        print(f"[OK] Deployment screenshot saved: {deploy_path}")
    except Exception as e:
        print(f"[ERROR] Deployment screenshot failed: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    pygame.quit()
    print("[DONE] Screenshot capture complete.")


if __name__ == "__main__":
    main()
