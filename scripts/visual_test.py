#!/usr/bin/env python3
"""PyCC2 Playable Demo — v0.5-p4-week1 (ALL P0-P4 Features)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pygame

from pycc2.domain.ai.combat_engagement import CombatEngagement, EngagementRule
from pycc2.domain.ai.commander_ai import CommanderAI, CommanderRole
from pycc2.domain.ai.difficulty_system import DifficultyLevel, DifficultySystem
from pycc2.domain.ai.perception_system import PerceptionSystem
from pycc2.domain.ai.squad_coordinator import SquadCoordinator
from pycc2.domain.ai.unit_bt_factory import UnitBTFactory
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import (
    Faction,
    Unit,
    UnitType,
)
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.domain.systems.fog_of_war import FogOfWar
from pycc2.domain.systems.pathfinder import PathFinder
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.input.handler import PygameInputHandler
from pycc2.presentation.input.interaction_controller import InteractionController
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.display_config import DisplayConfig
from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
from pycc2.presentation.rendering.window_config import WindowManager
from pycc2.services.ai_service import AIService
from pycc2.services.event_bus import EventBus
from pycc2.services.game_loop import GameLoop, GameState
from pycc2.presentation.audio.sound_system import SoundSystem, SoundType
from pycc2.domain.entities.unit import UNIT_TEMPLATES
from pycc2.domain.systems.campaign import create_default_campaign, CampaignManager
from pycc2.domain.systems.victory_conditions import VictoryConditionType, GameResult
from pycc2.presentation.ui.settings_menu import SettingsMenu
from pycc2.presentation.ui.tutorial_system import TutorialOverlay, TutorialStep
from pycc2.presentation.ui.hint_manager import HintManager


def create_tutorial_map() -> GameMap:
    width, height = 24, 24
    grid = np.zeros((height, width), dtype=np.int8)
    
    grid[4:6, 4:10] = 3
    grid[8:10, 12:18] = 5
    grid[16, :] = 1
    grid[:, 16] = 1
    grid[7, 7] = 11
    
    grid[10:13, 4:8] = 12
    grid[18:21, 18:23] = 13
    grid[3, 14:20] = 7
    grid[14:17, 2:5] = 9
    
    return GameMap(
        id="tutorial_v2",
        name="Market Garden Battlefield",
        width=width,
        height=height,
        tile_grid=grid,
    )


def create_battle_units() -> list[Unit]:
    allies = [
        Unit(
            id="ally_infantry_1",
            name="Alpha-1",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=85),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(2, 2)),
            vision=VisionComponent(range_tiles=5),
        ),
        Unit(
            id="ally_infantry_2",
            name="Alpha-2",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=90),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(2, 5)),
            vision=VisionComponent(range_tiles=5),
        ),
        Unit(
            id="ally_infantry_3",
            name="Alpha-3",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=90, max_hp=100),
            morale=MoraleComponent(value=80),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=8, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(4, 3)),
            vision=VisionComponent(range_tiles=5),
        ),
        Unit(
            id="ally_mg_1",
            name="Bravo-MG",
            faction=Faction.ALLIES,
            unit_type=UnitType.MACHINE_GUN_SQUAD,
            health=HealthComponent(hp=80, max_hp=80),
            morale=MoraleComponent(value=75),
            weapon=WeaponComponent(primary_weapon_id="mg42", ammo_remaining=50, max_ammo=50),
            position=PositionComponent(tile_coord=TileCoord(2, 8)),
            vision=VisionComponent(range_tiles=6),
        ),
        Unit(
            id="ally_commander",
            name="Cpt. Miller",
            faction=Faction.ALLIES,
            unit_type=UnitType.COMMANDER,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=95),
            weapon=WeaponComponent(primary_weapon_id="pistol", ammo_remaining=14, max_ammo=14),
            position=PositionComponent(tile_coord=TileCoord(4, 5)),
            vision=VisionComponent(range_tiles=7),
        ),
        Unit(
            id="ally_sniper_1",
            name="Hawkeye",
            faction=Faction.ALLIES,
            unit_type=UnitType.SNIPER_TEAM,
            health=HealthComponent(hp=60, max_hp=60),
            morale=MoraleComponent(value=80),
            weapon=WeaponComponent(primary_weapon_id="sniper_rifle", ammo_remaining=15, max_ammo=15),
            position=PositionComponent(tile_coord=TileCoord(3, 10)),
            vision=VisionComponent(range_tiles=10),
        ),
        Unit(
            id="ally_medic_1",
            name="Doc",
            faction=Faction.ALLIES,
            unit_type=UnitType.MEDIC_TEAM,
            health=HealthComponent(hp=70, max_hp=70),
            morale=MoraleComponent(value=88),
            weapon=WeaponComponent(primary_weapon_id="pistol", ammo_remaining=12, max_ammo=12),
            position=PositionComponent(tile_coord=TileCoord(5, 7)),
            vision=VisionComponent(range_tiles=5)),
    ]

    axis_units = [
        Unit(
            id="axis_infantry_1",
            name="Grenadier-1",
            faction=Faction.AXIS,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=85),
            weapon=WeaponComponent(primary_weapon_id="mp40", ammo_remaining=30, max_ammo=30),
            position=PositionComponent(tile_coord=TileCoord(17, 17)),
            vision=VisionComponent(range_tiles=5),
        ),
        Unit(
            id="axis_infantry_2",
            name="Grenadier-2",
            faction=Faction.AXIS,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=88),
            weapon=WeaponComponent(primary_weapon_id="mp40", ammo_remaining=30, max_ammo=30),
            position=PositionComponent(tile_coord=TileCoord(17, 14)),
            vision=VisionComponent(range_tiles=5),
        ),
        Unit(
            id="axis_infantry_3",
            name="Grenadier-3",
            faction=Faction.AXIS,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=95, max_hp=100),
            morale=MoraleComponent(value=82),
            weapon=WeaponComponent(primary_weapon_id="mp40", ammo_remaining=25, max_ammo=30),
            position=PositionComponent(tile_coord=TileCoord(15, 16)),
            vision=VisionComponent(range_tiles=5),
        ),
        Unit(
            id="axis_mg_1",
            name="MG Team",
            faction=Faction.AXIS,
            unit_type=UnitType.MACHINE_GUN_SQUAD,
            health=HealthComponent(hp=80, max_hp=80),
            morale=MoraleComponent(value=70),
            weapon=WeaponComponent(primary_weapon_id="mg42", ammo_remaining=50, max_ammo=50),
            position=PositionComponent(tile_coord=TileCoord(15, 18)),
            vision=VisionComponent(range_tiles=6),
        ),
        Unit(
            id="axis_commander",
            name="Oberst Krebs",
            faction=Faction.AXIS,
            unit_type=UnitType.COMMANDER,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=92),
            weapon=WeaponComponent(primary_weapon_id="luger", ammo_remaining=8, max_ammo=8),
            position=PositionComponent(tile_coord=TileCoord(16, 15)),
            vision=VisionComponent(range_tiles=7),
        ),
        Unit(
            id="axis_tank_1",
            name="Panzer IV",
            faction=Faction.AXIS,
            unit_type=UnitType.TANK,
            health=HealthComponent(hp=200, max_hp=200),
            morale=MoraleComponent(value=90),
            weapon=WeaponComponent(primary_weapon_id="tank_cannon", ammo_remaining=30, max_ammo=30),
            position=PositionComponent(tile_coord=TileCoord(19, 15)),
            vision=VisionComponent(range_tiles=7)),
        Unit(
            id="axis_sniper_1",
            name="Scharfschütze",
            faction=Faction.AXIS,
            unit_type=UnitType.SNIPER_TEAM,
            health=HealthComponent(hp=60, max_hp=60),
            morale=MoraleComponent(value=82),
            weapon=WeaponComponent(primary_weapon_id="sniper_rifle", ammo_remaining=15, max_ammo=15),
            position=PositionComponent(tile_coord=TileCoord(18, 11)),
            vision=VisionComponent(range_tiles=10)),
    ]

    return allies + axis_units


def main():
    pygame.init()
    wm = WindowManager()
    screen = wm.initialize()

    display_cfg = DisplayConfig.from_screen(
        screen_width=wm.display_info.screen_width or 1440,
        screen_height=wm.display_info.screen_height or 900,
        dpi_scale=wm.display_info.dpi_scale,
        is_retina=wm.display_info.is_retina,
    )

    game_map = create_tutorial_map()
    all_units = create_battle_units()
    camera = Camera(
        position=Vec2(
            float(game_map.width * display_cfg.base_tile_size // 2),
            float(game_map.height * display_cfg.base_tile_size // 2),
        ),
        viewport_width=display_cfg.window_width,
        viewport_height=display_cfg.window_height,
    )
    camera.zoom = display_cfg.compute_default_zoom(game_map.width, game_map.height)

    renderer = SpriteRenderer(display_config=display_cfg)
    renderer.initialize(screen)
    event_bus = EventBus()
    input_handler = PygameInputHandler(camera=camera, window_manager=wm)

    pathfinder = PathFinder()
    ballistic = BallisticEngine()
    FogOfWar(width=24, height=24)
    PerceptionSystem()

    ally_units = [u for u in all_units if u.faction == Faction.ALLIES]
    axis_units_list = [u for u in all_units if u.faction == Faction.AXIS]

    interaction_ctrl = InteractionController(camera=camera, game_map=game_map, event_bus=event_bus)

    def execute_move(unit_ids: set[str], target: TileCoord):
        for uid in unit_ids:
            unit = next((u for u in all_units if u.id == uid), None)
            if unit and game_map.is_passable(target.x, target.y):
                path = pathfinder.find_path(unit.position.tile_coord, target, game_map)
                if path:
                    unit._move_order = {"path": path[1:], "current_idx": 0}

    def execute_attack(unit_ids: set[str], target_id: str):
        for uid in unit_ids:
            unit = next((u for u in all_units if u.id == uid), None)
            target = next((u for u in all_units if u.id == target_id), None)
            if unit and target and target.faction != unit.faction:
                event_bus.publish("player_command", {"command": "attack", "attacker_id": uid, "target_id": target_id})

    interaction_ctrl.register_on_move(execute_move)
    interaction_ctrl.register_on_attack(execute_attack)

    axis_commander_unit = next((u for u in axis_units_list if u.id == "axis_commander"), None)

    axis_commander_ai = None
    if axis_commander_unit:
        axis_commander_ai = CommanderAI(
            commander_unit=axis_commander_unit,
            role=CommanderRole.OVERALL,
        )

    squad_coord = SquadCoordinator()
    if len(axis_units_list) >= 4:
        squad_coord.register_squad("axis_alpha", [axis_units_list[0].id, axis_units_list[1].id, axis_units_list[2].id])
        squad_coord.register_squad("axis_bravo", [axis_units_list[3].id, axis_units_list[4].id])

    difficulty = DifficultySystem(DifficultyLevel.MEDIUM)
    engagement = CombatEngagement(EngagementRule())

    campaign = create_default_campaign()
    print(f"\nCampaign: {campaign.total_missions} missions ({campaign.completed_count} completed)")
    for m in campaign.available_missions:
        print(f"  - [{m.id}] {m.name} ({m.difficulty.name})")

    ai_service = AIService(
        event_bus=event_bus,
        pathfinder=pathfinder,
        ballistic_engine=ballistic,
        difficulty_system=difficulty,
        squad_coordinator=squad_coord,
        combat_engagement=engagement,
    )

    if axis_commander_ai:
        ai_service.set_commander(axis_commander_ai)

    for unit in axis_units_list:
        bt = _create_bt_for_unit(unit)
        ai_service.register_ai_unit(unit, bt)
        if unit.unit_type == UnitType.MACHINE_GUN_SQUAD:
            ai_service.set_blackboard_value(unit.id, "patrol_points", [(15, 2), (18, 17), (15, 19), (2, 17)])
            ai_service.set_blackboard_value(unit.id, "patrol_target", (15, 2))
            ai_service.set_blackboard_value(unit.id, "current_patrol_index", 0)

    state = GameState(
        game_map=game_map,
        units=all_units,
        camera=camera,
    )
    game_loop = GameLoop(
        renderer=renderer,
        window_manager=wm,
        event_bus=event_bus,
        state=state,
        input_handler=input_handler,
        ai_service=ai_service,
        interaction_controller=interaction_ctrl,
        use_full_hud=True,
        display_config=display_cfg,
        settings_menu=settings_menu,
        tutorial_overlay=tutorial_overlay,
        hint_manager=hint_manager,
    )

    settings_menu = SettingsMenu(display_cfg)

    tutorial_overlay = TutorialOverlay(display_cfg)
    hint_manager = HintManager()
    tutorial_overlay.show(step=TutorialStep.WELCOME)
    _tutorial_active = True
    _first_unit_selected = False

    print("=" * 64)
    print("  🎮 PyCC2 Playable Demo — v0.5-p4-week1")
    print("=" * 64)
    print(f"  Display: {display_cfg.window_width}x{display_cfg.window_height} "
          f"[tile={display_cfg.base_tile_size}px Retina={'Yes' if display_cfg.is_retina else 'No'} "
          f"dpi={display_cfg.dpi_scale:.1f}x]")
    print(f"  UI Scale: {display_cfg.ui_scale:.2f}x | Font Normal={display_cfg.font_size_normal}")
    print("=" * 64)
    print("  Controls:")
    print("    Left Click:     Select unit | Right Click: Move/Attack")
    print("    M/A/S/K/D:      Mode shortcuts | ESC: Pause/Menu")
    print("    WASD: Camera | Scroll: Zoom | F11: Fullscreen | F3: Debug")
    print("    F5: Quick Save | F9: Quick Load | F10: Settings Menu | F1: Tutorial")
    print("=" * 64)
    print("  ★ P4 Features Active:")
    print("    • GameLoop Decomposition (RenderPipeline/CombatDirector/InputRouter/SaveController)")
    print("    • Settings Menu (4 tabs: General/Audio/Controls/Gameplay)")
    print("    • Security Hardening (HMAC env key / Input bounds checking)")
    print("    • Victory Conditions (Commander kill / Eliminate / Morale)")
    print("    • Post-Battle Statistics Panel")
    print("    • Unit Animations (Idle/Walk/Shoot/Death/Hit-react)")
    print("    • Screen Shake (impacts scale with intensity)")
    print("    • Enhanced Particles (Blood/Smoke/Debris/Sparks/Rings)")
    print("    • Damage Numbers (graded color/scale/shadow/fade)")
    print("    • New Units: Tank / Sniper / Medic (+ pixel art sprites)")
    print("    • New Terrain: Crater / Swamp (+ tile rendering)")
    print("    • Campaign System (3 mission definitions)")
    print("    • Secure Save System (HMAC-SHA256, 8 slots)")
    print("    • Tutorial & Hint System (First-launch guidance / F1 / Contextual tooltips)")
    print("=" * 64)
    print(f"\nAllies: {len(ally_units)} units (Player Controlled)")
    for u in ally_units:
        print(f"  - {u.name} ({u.id}): {u.unit_type.name}")
    print(f"\nAxis: {len(axis_units_list)} units (AI Controlled)")
    for u in axis_units_list:
        print(f"  - {u.name} ({u.id}): {u.unit_type.name}")
    print(f"\nAI-Controlled Units: {ai_service.managed_unit_count}")
    if ai_service.has_commander():
        print(f"Commander AI: {ai_service.commander.commander.name} [{ai_service.commander.role.name}]")
    if ai_service._squad_coordinator:
        print(f"Active Squads: {len(ai_service._squad_coordinator.active_squads)}")
        for sq in ai_service._squad_coordinator.active_squads:
            members = ai_service._squad_coordinator.get_squad_units(sq, all_units)
            print(f"  - {sq}: {[m.name for m in members]}")
    print(f"Difficulty: {difficulty.level.name}")
    print("-" * 60)
    print(f"\nAudio: {'✓ Active' if game_loop.sound_system else '✗ Disabled'}")
    if game_loop.sound_system:
        print(f"  Sound cache: {len(game_loop.sound_system._sound_cache)} preloaded sounds")
    print(f"Save System: {'✓ Ready' if game_loop._save_manager else '✗ None'}")
    if game_loop._save_manager:
        slots = game_loop.list_saves()
        empty = sum(1 for _, _, s in slots if s.name == "EMPTY")
        print(f"  Slots: {empty}/{game_loop._save_manager.MAX_SLOTS} available")
    game_loop.run()


def _create_bt_for_unit(unit: Unit):
    match unit.unit_type:
        case UnitType.INFANTRY_SQUAD:
            return UnitBTFactory.create_infantry_bt(unit_id=unit.id)
        case UnitType.MACHINE_GUN_SQUAD:
            return UnitBTFactory.create_mg_squad_bt(unit_id=unit.id)
        case UnitType.COMMANDER:
            return UnitBTFactory.create_commander_bt(unit_id=unit.id)
        case UnitType.TANK:
            return UnitBTFactory.create_infantry_bt(unit_id=unit.id)
        case UnitType.SNIPER_TEAM:
            return UnitBTFactory.create_infantry_bt(unit_id=unit.id)
        case UnitType.MEDIC_TEAM:
            return UnitBTFactory.create_infantry_bt(unit_id=unit.id)
        case UnitType.AT_GUN_TEAM:
            return UnitBTFactory.create_infantry_bt(unit_id=unit.id)
        case UnitType.MORTAR_TEAM:
            return UnitBTFactory.create_infantry_bt(unit_id=unit.id)
        case _:
            return UnitBTFactory.create_infantry_bt(unit_id=unit.id)


if __name__ == "__main__":
    main()
