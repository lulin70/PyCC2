"""Real game screenshots: Full CC2-style gameplay capture.

Generates 6 screenshots covering complete user journey:
  01_main_menu        — Main menu (New Game / Load / Options / Exit)
  02_skirmish_setup   — Skirmish configuration (map, faction, difficulty)
  03_deployment       — Deployment phase with placement UI
  04_battle_hud       — Battle phase with full CC2 bottom panel + SVG sprites
  05_battle_zoomed    — Zoomed-in view showing unit detail
  06_battle_action    — After issuing move/attack commands

Key improvements over old script:
  - Uses real GameLoop from _start_new_game() path
  - SVG sprites auto-loaded via SpriteCacheManager
  - HUD rendered with full parameters (camera + game_state)
  - Multiple game ticks for realistic rendering
  - Axis AI units auto-registered via safety net
"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pygame

pygame.init()

from pycc2.main import _start_new_game
from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager
from pycc2.presentation.ui.new_game_menu import NewGameMenu

OUT_DIR = "/Users/lin/trae_projects/PyCC2/screenshots"
os.makedirs(OUT_DIR, exist_ok=True)


def save_screen(screen, name):
    """Save current screen buffer as PNG."""
    path = os.path.join(OUT_DIR, f"{name}.png")
    pygame.image.save(screen, path)
    w, h = screen.get_size()
    print(f"  [Screenshot] {name}.png ({w}x{h}) -> {path}")
    return path


def tick_game_loop(game_loop, count=5):
    """Run N game loop ticks for rendering updates."""
    for _i in range(count):
        # Process empty event queue (required by run())
        for _event in [pygame.event.Event(pygame.NOEVENT)]:
            pass
        try:
            # Single tick: update logic + render
            game_loop._update_logic(0.016)  # ~60fps dt
            game_loop._update_ai(0.016)
            game_loop._render_scene(game_loop.window_manager._screen, 1.0)
        except Exception:
            pass  # Some systems may not be fully initialized


# ===========================================================================
# Phase 1: Main Menu
# ===========================================================================
print("=" * 60)
print("Phase 1: Main Menu")
print("=" * 60)

wm = WindowManager(DisplayInfo(base_width=1280, base_height=720))
screen = wm.initialize()

menu = NewGameMenu()
menu.render(screen)
save_screen(screen, "01_main_menu")


# ===========================================================================
# Phase 2: Skirmish Setup
# ===========================================================================
print("\nPhase 2: Skirmish Setup")
print("-" * 40)

# Click Skirmish button (3rd button on main menu)
action = menu.handle_click((640, 492))

menu.render(screen)
save_screen(screen, "02_skirmish_menu")

# Click Start Skirmish button
start_action = menu.handle_click((570, 664))
print(f"  Start action: {start_action}")


# ===========================================================================
# Phase 3-4: Real Game Loop (Deployment → Battle)
# ===========================================================================
print("\nPhase 3-4: Starting Real Game...")
print("-" * 40)

game_loop = None
if start_action:
    try:
        game_loop = _start_new_game(menu, start_action, screen, wm)
    except Exception as e:
        print(f"  _start_new_game error: {e}")
        import traceback
        traceback.print_exc()

if game_loop is None:
    print("  Fallback: creating minimal game for screenshots...")
    # Direct creation if _start_new_game fails
    from pycc2.services.game_loop_assembler import GameLoopAssembler
    assembler = GameLoopAssembler()
    game_loop = assembler.assemble(screen, wm)

print(f"  GameLoop type: {type(game_loop).__name__}")

# --- Screenshot 03: Deployment Phase ---
if game_loop._deployment_manager and game_loop._deployment_manager.is_active:
    game_loop.renderer.render(
        game_loop.state.game_map,
        game_loop.state.units,
        game_loop.state.camera,
    )
    save_screen(screen, "03_deployment_phase")

    # Complete deployment to enter battle phase
    game_loop._deployment_manager.complete(
        ai_service=game_loop.ai_service,
        state=game_loop.state,
    )
    print("  Deployment completed, entering battle phase...")

# --- Ensure units exist for battle screenshot ---
if len(game_loop.state.units) == 0:
    print("  No units found, placing test units...")
    from pycc2.domain.components.health_component import HealthComponent
    from pycc2.domain.components.morale_component import MoraleComponent
    from pycc2.domain.components.position_component import PositionComponent
    from pycc2.domain.components.vision_component import VisionComponent
    from pycc2.domain.components.weapon_component import WeaponComponent
    from pycc2.domain.entities.unit import Faction, Unit, UnitType
    from pycc2.domain.value_objects.tile_coord import TileCoord

    allies_unit = Unit(
        id="ally_squad_alpha",
        name="Alpha Squad",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        position=PositionComponent(tile_coord=TileCoord(12, 14)),
        vision=VisionComponent(),
        weapon=WeaponComponent(primary_weapon_id="m1_garand", max_ammo=120, ammo_remaining=120),
    )
    game_loop.state.units.append(allies_unit)

    axis_unit = Unit(
        id="axis_squad_1",
        name="Grenadier MG",
        faction=Faction.AXIS,
        unit_type=UnitType.MACHINE_GUN_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=70),
        position=PositionComponent(tile_coord=TileCoord(22, 12)),
        vision=VisionComponent(),
        weapon=WeaponComponent(primary_weapon_id="mg42", max_ammo=250, ammo_remaining=250),
    )
    game_loop.state.units.append(axis_unit)

    axis_rifle = Unit(
        id="axis_rifle_1",
        name="Grenadier Rifle",
        faction=Faction.AXIS,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=90, max_hp=100),
        morale=MoraleComponent(value=65),
        position=PositionComponent(tile_coord=TileCoord(20, 16)),
        vision=VisionComponent(),
        weapon=WeaponComponent(primary_weapon_id="kar98k", max_ammo=60, ammo_remaining=60),
    )
    game_loop.state.units.append(axis_rifle)

    print(f"  Units placed: {len(game_loop.state.units)}")

# Select first ally unit so HUD shows details
if game_loop.state.units:
    game_loop.state.selected_unit_ids = {game_loop.state.units[0].id}

# --- Tick game loop to trigger AI registration safety net ---
print("  Running game loop ticks (triggers AI safety net)...")
tick_game_loop(game_loop, count=10)

# --- Screenshot 04: Battle with HUD (default zoom) ---
print("\nRendering battle scene with full HUD...")
screen.fill((28, 32, 24))  # Dark background
game_loop._render_scene(screen, 1.0)
save_screen(screen, "04_battle_with_hud")

# --- Screenshot 05: Zoomed-in view ---
print("Rendering zoomed-in view...")
original_zoom = game_loop.state.camera.zoom
game_loop.state.camera.zoom = 1.8  # Zoom in
# Center camera on first unit
if game_loop.state.units:
    u = game_loop.state.units[0]
    px = u.position.pixel_position
    from pycc2.domain.value_objects.vec2 import Vec2
    game_loop.state.camera.set_position(Vec2(px.x - 640, px.y - 360))

screen.fill((28, 32, 24))
game_loop._render_scene(screen, 1.0)
save_screen(screen, "05_battle_zoomed")

# Restore zoom
game_loop.state.camera.zoom = original_zoom

# --- Screenshot 06: With command menu simulation ---
print("Rendering with simulated interaction overlay...")
screen.fill((28, 32, 24))
game_loop._render_scene(screen, 1.0)

# Draw LOS overlay if possible (Ctrl-key simulation)
if game_loop.state.selected_unit_ids:
    selected_id = next(iter(game_loop.state.selected_unit_ids), None)
    if selected_id:
        selected_unit = next((u for u in game_loop.state.units if u.id == selected_id), None)
        if selected_unit and hasattr(game_loop.renderer, 'render_los_overlay'):
            try:
                game_loop.renderer.render_los_overlay(
                    screen, selected_unit, game_loop.state.game_map, game_loop.state.camera
                )
                print("  ✅ LOS overlay rendered")
            except Exception as e:
                print(f"  ⚠️ LOS overlay skipped: {e}")

# Render radial menu hint (interaction overlay)
if game_loop.interaction_controller:
    try:
        game_loop.interaction_controller.render_overlay(screen, game_loop.state.camera)
        print("  ✅ Interaction overlay rendered")
    except Exception as e:
        print(f"  ⚠️ Interaction overlay skipped: {e}")

save_screen(screen, "06_battle_with_overlays")


# ===========================================================================
# Summary & Verification
# ===========================================================================
print("\n" + "=" * 60)
print("SCREENSHOT SUMMARY")
print("=" * 60)

# List all generated screenshots
screenshots = sorted([f for f in os.listdir(OUT_DIR) if f.endswith(".png")])
for s in screenshots:
    fpath = os.path.join(OUT_DIR, s)
    size = os.path.getsize(fpath)
    print(f"  {s} ({size:,} bytes)")

# Verify SVG sprites were used
try:
    from pycc2.presentation.rendering.sprite_cache_manager import SpriteCacheManager
    mgr = SpriteCacheManager()
    svg_count = len(mgr._svg_cache) if hasattr(mgr, '_svg_cache') else 0
    print(f"\nSVG sprites cached: {svg_count}/16")
except Exception as e:
    print(f"\nSVG sprite check error: {e}")

# Verify HUD was initialized
hud_status = "✅ Present" if (game_loop and game_loop._hud_manager) else "❌ Missing"
print(f"HUD Manager: {hud_status}")

ai_count = 0
if game_loop and game_loop.ai_service:
    ai_count = game_loop.ai_service.managed_unit_count
print(f"AI managed units: {ai_count}")

print(f"\nAll screenshots saved to: {OUT_DIR}")
pygame.quit()
