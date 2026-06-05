"""Quick verification: SAVE and LOAD actually work end-to-end."""
import os, json
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()

from pycc2.services.game_loop import GameLoop, GameState
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
from pycc2.presentation.rendering.camera import Camera
from pycc2.services.event_bus import EventBus
from pycc2.services.ai_service import AIService
from pycc2.presentation.input.interaction_controller import InteractionController
from pycc2.presentation.input.handler import PygameInputHandler
from pycc2.presentation.rendering.window_config import WindowManager
import numpy as np

screen = pygame.display.set_mode((1024, 768))
wm = WindowManager()
wm._screen = screen
camera = Camera(position=Vec2(512, 384), viewport_width=1024, viewport_height=768)
renderer = EnhancedRenderer()
renderer.initialize(screen)
event_bus = EventBus()
game_map = GameMap(id="test", name="Test", width=40, height=30,
    tile_grid=np.zeros((30, 40), dtype=np.int8))
units = [Unit(
    id="u1", name="Test Unit", faction=Faction.ALLIES, unit_type=UnitType.INFANTRY_SQUAD,
    position=PositionComponent(tile_coord=TileCoord(5, 12)),
    vision=VisionComponent(),
    health=HealthComponent(hp=80, max_hp=100),
    weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=100),
    morale=MoraleComponent(value=75),
)]
state = GameState(game_map=game_map, units=units, camera=camera, tick=42)

ih = PygameInputHandler(camera=camera, window_manager=wm)
ai_svc = AIService(event_bus=event_bus)
ic = InteractionController(camera, game_map, event_bus)

gl = GameLoop(renderer=renderer, window_manager=wm, event_bus=event_bus,
    state=state, input_handler=ih, ai_service=ai_svc,
    interaction_controller=ic)

print("=== SAVE ===")
save_ok = gl.quick_save(0)
print(f"quick_save(0) => {save_ok}")

# SecureSaveManager saves relative to src/pycc2/infrastructure → up 3 = src/
import pathlib
_project_root = pathlib.Path(__file__).resolve().parent.parent  # scripts/ → project root
_save_root = _project_root / "src" / "saves" / "saves"
save_path = str(_save_root / "save_slot_0.json")
if os.path.exists(save_path):
    with open(save_path) as f:
        data = json.load(f)
    print(f"File: {save_path}")
    print(f"Version: {data['meta']['version']}")
    print(f"Tick saved: {data['meta']['tick']}")
    print(f"Units in save: {len(data['state'].get('units', []))}")
    print(f"HMAC valid: {'hmac' in data and len(data['hmac']) > 10}")
else:
    # Try project-root saves/ as fallback
    alt = _project_root / "saves" / "saves" / "save_slot_0.json"
    if alt.exists():
        save_path = str(alt)
        with open(save_path) as f:
            data = json.load(f)
        print(f"File: {save_path}")
        print(f"Version: {data['meta']['version']}")
        print(f"Tick saved: {data['meta']['tick']}")
        print(f"Units in save: {len(data['state'].get('units', []))}")
        print(f"HMAC valid: {'hmac' in data and len(data['hmac']) > 10}")
    else:
        print(f"ERROR: save_slot_0.json not found at any expected location!")

print("\n=== LOAD ===")
# Modify state to prove load restores it
gl.state.tick = 999
load_ok = gl.quick_load(0)
print(f"quick_load(0) => {load_ok}")
print(f"Tick after load: {gl.state.tick} (should be 42)")
print(f"Units after load: {len(gl.state.units)} (should be 1)")

gl.shutdown()
pygame.quit()

print(f"\n{'SAVE/LOAD: WORKING' if save_ok and load_ok else 'SAVE/LOAD: BROKEN'}")
