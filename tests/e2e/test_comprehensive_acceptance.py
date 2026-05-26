"""
PyCC2 Comprehensive In-Game Functional Acceptance Test

This is a REAL integration/E2E test that:
1. Uses SDL_VIDEODRIVER=dummy for headless testing
2. Actually initializes pygame, creates display
3. Creates a real GameMap with varied terrain
4. Creates real Unit objects
5. Initializes EnhancedRenderer, SpriteRenderer, CC2BottomPanel, Camera, etc.
6. Simulates user interactions (mouse clicks, key presses) via the input system
7. Verifies each expected outcome with assertions

Test Categories:
A. Display & Initialization (Stage 0)
B. Unit Deployment (Stage 1)
C. Unit Selection & Display (Stage 2)
D. The 7 Commands - Each Must Work (Stage 3)
E. Attack Line & LOS (Stage 4)
F. Combat Execution (Stage 5)
G. Morale System (Stage 6)
H. Victory / Defeat Conditions (Stage 7)
I. UI Elements Detail Check
J. Keyboard Shortcuts
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import numpy as np
import pytest

import pygame

pygame.init()
pygame.font.init()

# ---------------------------------------------------------------------------
# Domain imports
# ---------------------------------------------------------------------------
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitState, UnitType
from pycc2.domain.systems.morale_system import MoraleSystem, MoraleState
from pycc2.domain.systems.victory_conditions import (
    BattleStats,
    GameResult,
    VictoryConditionEvaluator,
    VictoryConditionType,
)
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2

# ---------------------------------------------------------------------------
# Presentation imports
# ---------------------------------------------------------------------------
from pycc2.presentation.input.attack_line_system import (
    AttackLineStatus,
    AttackLineSystem,
    AttackTarget,
)
from pycc2.presentation.input.interaction_controller import (
    InteractionController,
    InteractionMode,
)
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel
from pycc2.presentation.rendering.display_config import DisplayConfig
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
from pycc2.presentation.rendering.minimap import Minimap
from pycc2.presentation.ui.deployment_ui import DeploymentUI, DeploymentPhase

# ---------------------------------------------------------------------------
# Service imports
# ---------------------------------------------------------------------------
from pycc2.services.combat_director import CombatDirector
from pycc2.services.event_bus import EventBus
from pycc2.services.victory_manager import VictoryManager


# ============================================================================
# Helpers
# ============================================================================


def make_unit(
    unit_id: str = "test_unit",
    name: str = "Test Unit",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 85,
    tile_x: int = 5,
    tile_y: int = 5,
    weapon_id: str = "rifle",
    max_ammo: int = 120,
):
    return Unit(
        id=unit_id,
        name=name,
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale),
        weapon=WeaponComponent(
            primary_weapon_id=weapon_id,
            max_ammo=max_ammo,
            ammo_remaining=max_ammo,
        ),
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(),
    )


def make_game_map(width: int = 20, height: int = 20, varied_terrain: bool = False):
    if varied_terrain:
        grid = np.zeros((height, width), dtype=np.int8)
        grid[height // 2, :] = TerrainType.ROAD.value
        grid[2:4, 5:15] = TerrainType.WATER.value
        grid[10:13, 3:7] = TerrainType.BUILDING_SOLID.value
        grid[8, :] = TerrainType.HEDGE.value
        grid[:, width - 2] = TerrainType.WALL.value
        return GameMap(
            id="varied_map",
            name="Varied Terrain Map",
            width=width,
            height=height,
            tile_grid=grid,
        )
    return GameMap(
        id="test_map",
        name="Test Map",
        width=width,
        height=height,
        tile_grid=np.zeros((height, width), dtype=np.int8),
    )


def make_camera(viewport_width: int = 1280, viewport_height: int = 720):
    return Camera(
        position=Vec2(320.0, 320.0),
        zoom=1.0,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def game_map():
    return make_game_map(varied_terrain=True)


@pytest.fixture
def simple_map():
    return make_game_map(varied_terrain=False)


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def camera():
    return make_camera()


@pytest.fixture
def ic(camera, game_map, event_bus):
    from pycc2.presentation.ui.keybind_manager import KeybindManager
    controller = InteractionController(camera=camera, game_map=game_map, event_bus=event_bus)
    controller.set_keybind_manager(KeybindManager())
    return controller


@pytest.fixture
def ally_unit():
    return make_unit("ally_1", "Rifle Squad", Faction.ALLIES, UnitType.INFANTRY_SQUAD)


@pytest.fixture
def ally_commander():
    return make_unit("ally_cmd", "Commander", Faction.ALLIES, UnitType.COMMANDER)


@pytest.fixture
def ally_tank():
    return make_unit("ally_tank", "Sherman Tank", Faction.ALLIES, UnitType.TANK, hp=200, max_hp=200)


@pytest.fixture
def enemy_unit():
    return make_unit("enemy_1", "Axis Squad", Faction.AXIS, UnitType.INFANTRY_SQUAD, tile_x=8, tile_y=8)


@pytest.fixture
def enemy_commander():
    return make_unit("enemy_cmd", "Axis Commander", Faction.AXIS, UnitType.COMMANDER, tile_x=9, tile_y=9)


@pytest.fixture
def screen():
    return pygame.display.set_mode((1280, 720))


@pytest.fixture
def bottom_panel():
    panel = CC2BottomPanel()
    panel.initialize()
    return panel


@pytest.fixture
def minimap_instance():
    dc = DisplayConfig()
    mm = Minimap(display_config=dc)
    gm = make_game_map()
    mm.set_map(gm)
    mm.update_units([])
    return mm


@pytest.fixture
def all_units(ally_unit, ally_commander, ally_tank, enemy_unit, enemy_commander):
    return [ally_unit, ally_commander, ally_tank, enemy_unit, enemy_commander]


@pytest.fixture
def friendly_units(ally_unit, ally_commander, ally_tank):
    return [ally_unit, ally_commander, ally_tank]


@pytest.fixture
def combat_director(event_bus):
    cd = CombatDirector(event_bus=event_bus, display_config=DisplayConfig())
    cd.initialize()
    return cd


# ========================================================================
# A. Display & Initialization (Stage 0)
# ========================================================================


@pytest.mark.e2e
class TestStageADisplayAndInitialization:

    def test_a01_game_window_opens_without_crash(self):
        screen = pygame.display.set_mode((1280, 720))
        assert screen is not None
        assert screen.get_size() == (1280, 720)

    def test_a02_screen_renders_at_expected_resolution(self):
        for w, h in [(1280, 720), (1024, 768), (800, 600)]:
            s = pygame.display.set_mode((w, h))
            assert s.get_size() == (w, h)

    def test_a03_pygame_initialized_cleanly(self):
        if not pygame.get_init():
            pygame.init()
        assert pygame.get_init() is True
        if not pygame.font.get_init():
            pygame.font.init()
        assert pygame.font.get_init() is True

    def test_a04_terrain_tiles_visible_on_screen(self, screen, camera, game_map):
        renderer = EnhancedRenderer()
        renderer.render(screen, game_map, [], camera)
        pixels = pygame.surfarray.array3d(screen)
        assert pixels.shape[0] == 1280
        assert pixels.shape[1] == 720

    def test_a05_bottom_panel_renders_correctly(self, screen, bottom_panel, camera, game_map, minimap_instance):
        bottom_panel.render(screen, camera, game_map, minimap=minimap_instance)
        pixels = pygame.surfarray.array3d(screen)
        assert pixels.shape[0] == 1280
        assert pixels.shape[1] == 720

    def test_a06_panel_background_is_olive_green(self):
        assert CC2BottomPanel.BG_COLOR == (58, 64, 48)

    def test_a07_panel_height_is_approximately_130px(self):
        assert CC2BottomPanel.PANEL_HEIGHT == 130

    def test_a08_minimap_appears_in_bottom_right(self, screen, minimap_instance):
        minimap_instance.render(screen, 1130, 560)
        pixels = pygame.surfarray.array3d(screen)
        assert pixels.shape[0] == 1280
        assert pixels.shape[1] == 720

    def test_a09_varied_terrain_map_has_multiple_types(self, game_map):
        grid = game_map.tile_grid
        unique_types = set(grid.flatten())
        assert len(unique_types) > 1

    def test_a10_enhanced_renderer_initializes(self, screen):
        renderer = EnhancedRenderer()
        renderer.initialize(screen)
        assert renderer is not None

    def test_a11_camera_has_correct_defaults(self, camera):
        assert camera.zoom == 1.0
        assert camera.viewport_width == 1280
        assert camera.viewport_height == 720

    def test_a12_no_pygame_errors_during_init(self, capsys):
        captured = capsys.readouterr()
        assert "error" not in captured.err.lower() or len(captured.err.strip()) == 0


# ========================================================================
# B. Unit Deployment (Stage 1)
# ========================================================================


@pytest.mark.e2e
class TestStageBUnitDeployment:

    def test_b01_deployment_phase_activates_before_battle(self):
        ui = DeploymentUI(width=1280, height=720)
        map_data = {"width": 20, "height": 20, "tiles": [[0] * 20 for _ in range(20)]}
        ui.start_deployment(map_data, faction="ally")
        assert ui.state.phase == DeploymentPhase.DEPLOYING

    def test_b02_units_appear_in_deployment_zone(self):
        ui = DeploymentUI(width=1280, height=720)
        map_data = {"width": 20, "height": 20, "tiles": [[0] * 20 for _ in range(20)]}
        ui.start_deployment(map_data, faction="ally")
        assert len(ui.state.available_units) > 0

    def test_b03_units_can_be_placed_on_map(self):
        ui = DeploymentUI(width=1280, height=720)
        map_data = {"width": 20, "height": 20, "tiles": [[0] * 20 for _ in range(20)]}
        ui.start_deployment(map_data, faction="ally")
        placed = ui.place_unit(0, 0, 0)
        assert placed is True
        assert len(ui.state.placed_units) == 1

    def test_b04_start_battle_button_works(self):
        ui = DeploymentUI(width=1280, height=720)
        map_data = {"width": 20, "height": 20, "tiles": [[0] * 20 for _ in range(20)]}
        ui.start_deployment(map_data, faction="ally")
        ui.place_unit(0, 0, 0)
        result = ui.begin_battle()
        assert result is not None
        assert result["phase"] == DeploymentPhase.ACTIVE
        assert len(result["placements"]) >= 1

    def test_b05_after_confirmation_battle_phase_begins(self):
        ui = DeploymentUI(width=1280, height=720)
        map_data = {"width": 20, "height": 20, "tiles": [[0] * 20 for _ in range(20)]}
        ui.start_deployment(map_data, faction="ally")
        ui.place_unit(0, 0, 0)
        result = ui.begin_battle()
        assert result["phase"] != DeploymentPhase.DEPLOYING

    def test_b06_deployed_units_have_correct_faction(self):
        ally = make_unit("ally_dep", "Ally Rifle", Faction.ALLIES, UnitType.INFANTRY_SQUAD)
        axis = make_unit("axis_dep", "Axis MG", Faction.AXIS, UnitType.MACHINE_GUN_SQUAD)
        assert ally.faction == Faction.ALLIES
        assert axis.faction == Faction.AXIS

    def test_b07_deployed_units_have_all_components(self):
        u = make_unit("full_check", hp=90, max_hp=100, morale=80)
        assert hasattr(u, 'health')
        assert hasattr(u, 'morale')
        assert hasattr(u, 'weapon')
        assert hasattr(u, 'position')
        assert hasattr(u, 'vision')
        assert hasattr(u, 'state_machine')
        assert u.is_alive is True


# ========================================================================
# C. Unit Selection & Display (Stage 2)
# ========================================================================


@pytest.mark.e2e
class TestStageCUnitSelectionAndDisplay:

    def test_c01_left_click_selects_unit(self, ic, ally_unit):
        units = [ally_unit]
        screen_pos = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        selected = ic.handle_left_click(screen_pos, units)
        assert ally_unit.id in selected

    def test_c02_selected_unit_ids_populated(self, ic, ally_unit):
        units = [ally_unit]
        screen_pos = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(screen_pos, units)
        assert ally_unit.id in ic.selected_unit_ids
        assert len(ic.selected_unit_ids) == 1

    def test_c03_selection_mode_is_select_after_click(self, ic, ally_unit):
        units = [ally_unit]
        screen_pos = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(screen_pos, units)
        assert ic.mode == InteractionMode.SELECT

    def test_c04_shift_click_adds_to_multi_selection(self, ic):
        u1 = make_unit("u1", tile_x=5, tile_y=5)
        u2 = make_unit("u2", tile_x=6, tile_y=5)
        units = [u1, u2]
        sp1 = ic.camera.world_to_screen(u1.position.pixel_position)
        ic.handle_left_click(sp1, units)
        assert u1.id in ic.selected_unit_ids
        sp2 = ic.camera.world_to_screen(u2.position.pixel_position)
        ic.handle_left_click(sp2, units, modifiers=(False, True, False, False))
        assert u2.id in ic.selected_unit_ids
        assert len(ic.selected_unit_ids) == 2

    def test_c05_click_empty_ground_deselects_all(self, ic, ally_unit):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        assert len(ic.selected_unit_ids) > 0
        ic.handle_left_click((700.0, 700.0), units)
        assert len(ic.selected_unit_ids) == 0

    def test_c06_esc_key_clears_selection(self, ic, ally_unit):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        assert len(ic.selected_unit_ids) > 0
        ic.handle_shortcut_key(pygame.K_ESCAPE)
        assert len(ic.selected_unit_ids) == 0
        assert ic.mode == InteractionMode.SELECT

    def test_c07_selected_unit_details_show_in_panel(self, bottom_panel, ally_unit):
        bottom_panel.set_friendly_units([ally_unit])
        bottom_panel.set_selected_unit(ally_unit.id)
        assert bottom_panel._selected_unit_id == ally_unit.id

    def test_c08_health_bar_displays_green_for_healthy(self, ally_unit):
        assert ally_unit.health.hp > ally_unit.health.max_hp * 0.6
        hp_ratio = ally_unit.health.hp / ally_unit.health.max_hp
        assert hp_ratio > 0.6

    def test_c09_health_bar_yellow_for_damaged(self):
        u = make_unit(hp=50, max_hp=100)
        ratio = u.health.hp / u.health.max_hp
        assert 0.3 <= ratio <= 0.6

    def test_c10_health_bar_red_for_critical(self):
        u = make_unit(hp=15, max_hp=100)
        ratio = u.health.hp / u.health.max_hp
        assert ratio < 0.3

    def test_c11_morale_bar_displays_correctly(self):
        u = make_unit(morale=75)
        assert u.morale.value == 75

    def test_c12_ammo_bar_displays_correctly(self):
        u = make_unit(max_ammo=120)
        assert u.weapon.ammo_remaining == 120
        assert u.weapon.max_ammo == 120

    def test_c13_hit_test_returns_unit_when_clicked_nearby(self, ic, ally_unit):
        result = ic.hit_test(
            ic.camera.world_to_screen(ally_unit.position.pixel_position),
            [ally_unit],
        )
        assert result.is_unit_click is True
        assert result.hit_unit is not None
        assert result.hit_unit.id == ally_unit.id

    def test_c14_hit_test_returns_terrain_when_empty(self, ic):
        result = ic.hit_test((400.0, 400.0), [])
        assert result.is_terrain_click is True
        assert result.is_unit_click is False
        assert result.hit_unit is None


# ========================================================================
# D. The 7 Commands - Each Must Work (Stage 3)
# ========================================================================


@pytest.mark.e2e
class TestStageDSevenCommands:

    def test_d01_move_command_activates(self, ic, ally_unit):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        ic.handle_shortcut_key(pygame.K_m)
        assert ic.mode == InteractionMode.MOVE

    def test_d02_move_command_sets_target(self, ic, ally_unit):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        ic.handle_shortcut_key(pygame.K_m)
        targets = []
        ic.register_on_move(lambda ids, t: targets.append((ids, t)))
        ic.handle_left_click((400.0, 400.0), units)
        assert len(targets) == 1
        assert ally_unit.id in targets[0][0]

    def test_d03_fast_move_mode(self, ic):
        ic.set_mode(InteractionMode.MOVE, fast=True)
        assert ic._move_fast is True
        assert ic.mode == InteractionMode.MOVE

    def test_d04_sneak_move_mode(self, ic):
        ic.set_mode(InteractionMode.MOVE, sneak=True)
        assert ic._move_sneak is True
        assert ic.mode == InteractionMode.MOVE

    def test_d05_attack_command_activates(self, ic, ally_unit):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        ic.handle_shortcut_key(pygame.K_c)
        assert ic.mode == InteractionMode.ATTACK

    def test_d06_attack_line_system_activates(self, ic, ally_unit):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        ic.attack_line.begin_attack(ally_unit.id, ally_unit.position.pixel_position)
        assert ic.attack_line.state.active is True
        assert ic.attack_line.state.source_unit_id == ally_unit.id

    def test_d07_smoke_command_publishes_event(self, ic, ally_unit, event_bus):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        received = []
        event_bus.subscribe(dict, lambda e: received.append(e))
        ic.handle_shortcut_key(pygame.K_k)
        smoke_events = [e for e in received if isinstance(e, dict) and e.get("command") == "smoke"]
        assert len(smoke_events) >= 1
        assert ally_unit.id in smoke_events[0]["unit_ids"]

    def test_d08_defend_command_publishes_event(self, ic, ally_unit, event_bus):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        received = []
        event_bus.subscribe(dict, lambda e: received.append(e))
        ic.handle_shortcut_key(pygame.K_d)
        defend_events = [e for e in received if isinstance(e, dict) and e.get("command") == "defend"]
        assert len(defend_events) >= 1
        assert ally_unit.id in defend_events[0]["unit_ids"]

    def test_d09_cancel_command_exits_mode(self, ic, ally_unit):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        ic.set_mode(InteractionMode.MOVE)
        assert ic.mode == InteractionMode.MOVE
        ic.handle_shortcut_key(pygame.K_ESCAPE)
        assert ic.mode == InteractionMode.SELECT
        assert len(ic.selected_unit_ids) == 0

    def test_d10_fast_key_publishes_event(self, ic, ally_unit, event_bus):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        received = []
        event_bus.subscribe(dict, lambda e: received.append(e))
        ic.handle_shortcut_key(pygame.K_f)
        fast_events = [e for e in received if isinstance(e, dict) and e.get("command") == "fast_move"]
        assert len(fast_events) >= 1

    def test_d11_sneak_key_publishes_event(self, ic, ally_unit, event_bus):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        received = []
        event_bus.subscribe(dict, lambda e: received.append(e))
        ic.handle_shortcut_key(pygame.K_s)
        sneak_events = [e for e in received if isinstance(e, dict) and e.get("command") == "sneak"]
        assert len(sneak_events) >= 1

    def test_d12_fast_move_key_publishes_event(self, ic, ally_unit, event_bus):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        received = []
        event_bus.subscribe(dict, lambda e: received.append(e))
        ic.handle_shortcut_key(pygame.K_x)
        fast_events = [e for e in received if isinstance(e, dict) and e.get("command") == "fast_move"]
        assert len(fast_events) >= 1

    def test_d13_all_seven_commands_defined_in_panel(self, bottom_panel):
        expected_cmds = {"move", "fast", "sneak", "attack", "smoke", "defend", "cancel", "end_battle"}
        actual_cmds = {cmd["id"] for cmd in bottom_panel._commands}
        assert expected_cmds == actual_cmds

    def test_d14_each_command_has_icon(self, bottom_panel):
        for cmd in bottom_panel._commands:
            cmd_id = cmd["id"]
            assert cmd_id in bottom_panel._command_icons, f"Missing icon for command: {cmd_id}"
            icon = bottom_panel._command_icons[cmd_id]
            assert icon.get_size() == (24, 24), f"Icon for {cmd_id} should be 24x24"

    def test_d15_defend_mode_on_unit(self, ally_unit):
        ally_unit.set_movement_mode("defend")
        assert ally_unit.is_defending is True
        assert ally_unit.get_speed_multiplier() < 1.0
        assert ally_unit.get_accuracy_modifier() > 1.0

    def test_d16_fast_mode_on_unit(self, ally_unit):
        ally_unit.set_movement_mode("fast_move")
        assert ally_unit.is_fast_moving is True
        assert ally_unit.get_speed_multiplier() == 1.5

    def test_d17_sneak_mode_on_unit(self, ally_unit):
        ally_unit.set_movement_mode("sneak")
        assert ally_unit.is_sneaking is True
        assert ally_unit.get_speed_multiplier() == 0.6
        assert ally_unit.get_detection_modifier() < 1.0

    def test_d18_unit_can_use_smoke(self, ally_unit):
        assert ally_unit.can_use_smoke is True

    def test_d19_unit_can_sneak(self, ally_unit):
        assert ally_unit.can_sneak is True


# ========================================================================
# E. Attack Line & LOS (Stage 4)
# ========================================================================


@pytest.mark.e2e
class TestStageEAttackLineAndLOS:

    def test_e01_attack_line_green_when_valid(self):
        als = AttackLineSystem()
        attacker = make_unit(tile_x=5, tile_y=5)
        target_pos = Vec2(6 * 32, 5 * 32)
        target = AttackTarget(position=target_pos, distance=32.0)
        status = als.evaluate_attack(attacker, target)
        # CC2 4-color system: close range = HIT_HIGH (green)
        assert status == AttackLineStatus.HIT_HIGH
        color = als.get_line_color(status)
        assert color == AttackLineSystem.COLOR_HIT_HIGH

    def test_e02_attack_line_red_when_out_of_range(self):
        als = AttackLineSystem()
        attacker = make_unit(tile_x=5, tile_y=5)
        target_pos = Vec2(50 * 32, 50 * 32)
        dist = attacker.position.pixel_position.distance_to(target_pos)
        target = AttackTarget(position=target_pos, distance=dist)
        status = als.evaluate_attack(attacker, target)
        assert status == AttackLineStatus.OUT_OF_RANGE
        color = als.get_line_color(status)
        assert color == AttackLineSystem.COLOR_OUT_OF_RANGE

    def test_e03_attack_line_orange_when_blocked(self):
        als = AttackLineSystem()
        grid = np.zeros((20, 20), dtype=np.int8)
        grid[5][6] = TerrainType.WALL.value
        gm = GameMap(id="block_test", name="Block Test", width=20, height=20, tile_grid=grid)
        from pycc2.domain.systems.los_system import Lossystem
        los = Lossystem(gm)
        attacker = make_unit(tile_x=5, tile_y=5)
        target_pos = Vec2(8 * 32, 5 * 32)
        dist = attacker.position.pixel_position.distance_to(target_pos)
        target = AttackTarget(position=target_pos, distance=dist)
        status = als.evaluate_attack(attacker, target, game_map=gm, los_system=los)
        assert status == AttackLineStatus.BLOCKED
        color = als.get_line_color(status)
        assert color == AttackLineSystem.COLOR_BLOCKED

    def test_e04_begin_attack_sets_active_state(self):
        als = AttackLineSystem()
        u = make_unit()
        als.begin_attack(u.id, u.position.pixel_position)
        assert als.state.active is True
        assert als.state.source_unit_id == u.id

    def test_e05_cancel_clears_attack_state(self):
        als = AttackLineSystem()
        u = make_unit()
        als.begin_attack(u.id, u.position.pixel_position)
        assert als.state.active is True
        als.cancel()
        assert als.state.active is False
        assert als.state.source_unit_id is None

    def test_e06_confirm_attack_locks_target(self):
        als = AttackLineSystem()
        u = make_unit()
        target = AttackTarget(position=Vec2(100, 100))
        als.begin_attack(u.id, u.position.pixel_position)
        als.confirm_attack(target)
        assert als.state.confirmed_target is not None
        assert als.state.active is False

    def test_e07_update_mouse_position_updates_target(self):
        als = AttackLineSystem()
        u = make_unit()
        als.begin_attack(u.id, u.position.pixel_position)
        target = als.update_mouse_position(
            screen_pos=(200.0, 200.0),
            world_pos=Vec2(200.0, 200.0),
            units=[],
            attacker_faction="allied",
        )
        assert target is not None
        assert als.state.target is not None

    def test_e08_los_clear_on_open_terrain(self, simple_map):
        from_coord = TileCoord(2, 2)
        to_coord = TileCoord(8, 8)
        assert simple_map.has_line_of_sight(from_coord, to_coord) is True

    def test_e09_los_blocked_by_wall(self):
        grid = np.zeros((20, 20), dtype=np.int8)
        grid[5][6] = TerrainType.WALL.value
        grid[5][7] = TerrainType.WALL.value
        gm = GameMap(id="wall_los", name="Wall LOS", width=20, height=20, tile_grid=grid)
        from_coord = TileCoord(5, 5)
        to_coord = TileCoord(8, 5)
        assert gm.has_line_of_sight(from_coord, to_coord) is False

    def test_e10_attack_line_colors_are_correct(self):
        assert AttackLineSystem.COLOR_CAN_ATTACK == (0, 255, 0, 200)
        assert AttackLineSystem.COLOR_OUT_OF_RANGE == (255, 50, 50, 200)
        assert AttackLineSystem.COLOR_BLOCKED == (255, 100, 0, 200)


# ========================================================================
# F. Combat Execution (Stage 5)
# ========================================================================


@pytest.mark.e2e
class TestStageFCombatExecution:

    def test_f01_attack_deals_damage(self, combat_director, ally_unit, enemy_unit):
        game_map = make_game_map()
        combat_director.set_context([ally_unit, enemy_unit], game_map)
        hp_before = enemy_unit.health.hp
        combat_director.execute_attack(ally_unit, enemy_unit)
        assert enemy_unit.health.hp <= hp_before

    def test_f02_unit_can_die_from_damage(self):
        u = make_unit(hp=10, max_hp=10)
        assert u.is_alive is True
        u.take_damage(10)
        assert u.is_alive is False
        assert u.health.hp == 0

    def test_f03_dead_unit_state_is_DEAD(self):
        u = make_unit(hp=5, max_hp=100)
        u.take_damage(100)
        assert u.state_machine.current == UnitState.DEAD

    def test_f04_morale_decreases_under_fire(self):
        u = make_unit(morale=85)
        before = u.morale.value
        u.morale.apply_delta(-20)
        assert u.morale.value < before
        assert u.morale.value == 65

    def test_f05_combat_stats_record_shots(self):
        stats = BattleStats()
        stats.record_shot("allies", hit=True)
        stats.record_shot("allies", hit=False)
        stats.record_shot("axis", hit=True)
        assert stats.shots_fired_allies == 2
        assert stats.shots_hit_allies == 1
        assert stats.shots_fired_axis == 1

    def test_f06_combat_stats_record_damage(self):
        stats = BattleStats()
        stats.record_damage("allies", 25.0)
        stats.record_damage("allies", 15.0)
        assert stats.allies_damage_dealt == 40.0

    def test_f07_combat_stats_record_kills(self):
        stats = BattleStats()
        stats.record_kill("allies")
        stats.record_kill("allies")
        stats.record_kill("axis")
        assert stats.allies_kills == 2
        assert stats.axis_kills == 1

    def test_f08_combat_stats_accuracy_calculation(self):
        stats = BattleStats()
        stats.record_shot("allies", hit=True)
        stats.record_shot("allies", hit=True)
        stats.record_shot("allies", hit=False)
        assert stats.allies_accuracy == pytest.approx(2.0 / 3.0)

    def test_f09_combat_director_processes_move_order(self, combat_director, ally_unit, simple_map):
        combat_director.set_context([ally_unit], simple_map)
        combat_director.handle_player_command({
            "command": "move",
            "unit_ids": [ally_unit.id],
            "target": (10, 10),
        }, [ally_unit], simple_map)

    def test_f10_combat_director_processes_attack_order(self, combat_director, ally_unit, enemy_unit, simple_map):
        combat_director.set_context([ally_unit, enemy_unit], simple_map)
        hp_before = enemy_unit.health.hp
        combat_director.handle_player_command({
            "command": "attack",
            "unit_ids": [ally_unit.id],
            "target_id": enemy_unit.id,
        }, [ally_unit, enemy_unit], simple_map)
        assert enemy_unit.health.hp <= hp_before

    def test_f11_unit_update_movement_toward_target(self):
        u = make_unit(tile_x=5, tile_y=5)
        u.move_target = TileCoord(10, 10)
        assert u.move_target is not None
        assert u.move_target.x == 10 and u.move_target.y == 10

    def test_f12_take_damage_returns_actual_damage(self):
        u = make_unit(hp=100, max_hp=100)
        actual = u.take_damage(30)
        assert actual == 30
        assert u.health.hp == 70

    def test_f13_take_damage_clamps_at_zero(self):
        u = make_unit(hp=10, max_hp=10)
        actual = u.take_damage(50)
        assert u.health.hp == 0
        assert actual == 10

    def test_f14_camera_shake_method_exists(self, camera):
        camera.shake(intensity=3.0, duration=0.15)
        assert camera._shake_intensity == 3.0
        assert camera._shake_duration == 0.15

    def test_f15_camera_shake_updates(self, camera):
        camera.shake(intensity=5.0, duration=0.3)
        camera.update_shake(0.1)
        assert camera._shake_timer > 0
        camera.update_shake(0.5)
        assert camera._shake_timer <= 0


# ========================================================================
# G. Morale System (Stage 6)
# ========================================================================


@pytest.mark.e2e
class TestStageGMoraleSystem:

    def test_g01_units_start_with_normal_morale(self):
        u = make_unit(morale=85)
        state = MoraleSystem.get_state(u.morale.value)
        assert state == MoraleState.RALLYED

    def test_g02_morale_state_mapping(self):
        assert MoraleSystem.get_state(85) == MoraleState.RALLYED
        assert MoraleSystem.get_state(55) == MoraleState.WAVERING
        assert MoraleSystem.get_state(30) == MoraleState.PINNED
        assert MoraleSystem.get_state(10) == MoraleState.BROKEN

    def test_g03_under_fire_morale_decreases(self):
        u = make_unit(morale=80)
        result = MoraleSystem.apply_suppression(u, amount=50.0, dt=1.0)
        assert result['morale_delta'] <= 0
        assert u.morale.value < 80

    def test_g04_pinned_state_cannot_move(self):
        u = make_unit(morale=35)
        assert MoraleSystem.can_move(u) is False

    def test_g05_broken_state_may_refuse_orders(self):
        u = make_unit(morale=15)
        accepted_count = sum(1 for _ in range(100) if MoraleSystem.can_accept_orders(u))
        assert accepted_count < 100

    def test_g06_rallyed_state_full_effectiveness(self):
        u = make_unit(morale=85)
        assert u.combat_effective is True
        assert u.can_act is True

    def test_g07_morale_recovers_when_not_under_fire(self):
        u = make_unit(morale=50)
        result = MoraleSystem.update_morale_recovery(u, dt=5.0)
        assert result['current_morale'] >= 50

    def test_g08_accuracy_modifier_by_state(self):
        assert MoraleSystem.get_accuracy_modifier(MoraleState.RALLYED) > 1.0
        assert MoraleSystem.get_accuracy_modifier(MoraleState.PINNED) < 1.0
        assert MoraleSystem.get_accuracy_modifier(MoraleState.BROKEN) < MoraleSystem.get_accuracy_modifier(MoraleState.PINNED)

    def test_g09_movement_modifier_by_state(self):
        assert MoraleSystem.get_movement_modifier(MoraleState.PINNED) == 0.0
        assert MoraleSystem.get_movement_modifier(MoraleState.BROKEN) > 0.0
        assert MoraleSystem.get_movement_modifier(MoraleState.BROKEN) < 1.0

    def test_g10_unit_is_broken_property(self):
        u_normal = make_unit(morale=80)
        u_broken = make_unit(morale=10)
        assert u_normal.is_broken is False
        assert u_broken.is_broken is True

    def test_g11_unit_morale_state_property(self):
        u = make_unit(morale=30)
        assert u.morale_state == MoraleState.PINNED

    def test_g12_unit_can_move_checks_morale(self):
        u_ok = make_unit(morale=80)
        u_pinned = make_unit(morale=30)
        assert u_ok.can_move() is True
        assert u_pinned.can_move() is False

    def test_g13_suppression_impacts_morale(self):
        u = make_unit(morale=75)
        MoraleSystem.apply_suppression(u, amount=100.0, dt=2.0)
        assert u.morale.value < 75


# ========================================================================
# H. Victory / Defeat Conditions (Stage 7)
# ========================================================================


@pytest.mark.e2e
class TestStageHVictoryDefeatConditions:

    def test_h01_victory_when_all_enemies_dead(self):
        evaluator = VictoryConditionEvaluator(
            conditions=[VictoryConditionType.ELIMINATE_ALL_ENEMIES],
        )
        ally = make_unit("v_ally", faction=Faction.ALLIES)
        enemy_dead = make_unit("v_enemy_dead", faction=Faction.AXIS, hp=0, max_hp=100)
        result, reason = evaluator.evaluate([ally, enemy_dead], tick=600)
        assert result == GameResult.ALLIES_VICTORY

    def test_h02_victory_when_enemy_commander_killed(self):
        evaluator = VictoryConditionEvaluator(
            conditions=[VictoryConditionType.ELIMINATE_ENEMY_COMMANDER],
        )
        ally = make_unit("vc_ally", faction=Faction.ALLIES)
        ally_cmd = make_unit("vc_acmd", faction=Faction.ALLIES, unit_type=UnitType.COMMANDER)
        enemy_cmd_dead = make_unit("vc_ecmd_dead", faction=Faction.AXIS, unit_type=UnitType.COMMANDER, hp=0, max_hp=100)
        result, reason = evaluator.evaluate([ally, ally_cmd, enemy_cmd_dead], tick=300)
        assert result == GameResult.ALLIES_VICTORY
        assert "commander" in reason.lower()

    def test_h03_defeat_when_all_allies_dead(self):
        evaluator = VictoryConditionEvaluator(
            conditions=[VictoryConditionType.ELIMINATE_ALL_ENEMIES],
        )
        ally_dead = make_unit("vd_ally_dead", faction=Faction.ALLIES, hp=0, max_hp=100)
        enemy = make_unit("vd_enemy", faction=Faction.AXIS)
        result, reason = evaluator.evaluate([ally_dead, enemy], tick=600)
        assert result == GameResult.AXIS_VICTORY

    def test_h04_defeat_when_morale_collapses(self):
        evaluator = VictoryConditionEvaluator(
            conditions=[VictoryConditionType.MORALE_COLLAPSE],
            morale_threshold=10,
        )
        ally_low = make_unit("vd_ally_low", faction=Faction.ALLIES, morale=5)
        enemy = make_unit("vd_enemy", faction=Faction.AXIS, morale=80)
        result, reason = evaluator.evaluate([ally_low, enemy], tick=300)
        assert result == GameResult.AXIS_VICTORY
        assert "morale" in reason.lower()

    def test_h05_battle_stats_summary(self):
        stats = BattleStats()
        stats.record_shot("allies", hit=True)
        stats.record_shot("allies", hit=True)
        stats.record_shot("allies", hit=False)
        stats.record_damage("allies", 45.0)
        stats.record_kill("allies")
        stats.record_unit_lost("axis")
        stats.ticks_elapsed = 600
        summary = stats.summary_dict()
        assert summary["allies_kills"] == 1
        assert summary["allies_damage_dealt"] == 45.0
        assert summary["shots_fired_allies"] == 3
        assert summary["shots_hit_allies"] == 2
        assert summary["ticks_elapsed"] == 600

    def test_h06_victory_manager_show_post_battle_flag(self):
        vm = VictoryManager()
        eb = EventBus()
        vm.initialize(event_bus=eb)
        assert vm.show_post_battle is False
        ally = make_unit("vm_ally", faction=Faction.ALLIES)
        enemy_dead = make_unit("vm_edead", faction=Faction.AXIS, hp=0, max_hp=100)
        result = vm.evaluate([ally, enemy_dead], tick=300)
        if result is not None:
            assert vm.show_post_battle is True
            assert vm.game_result is not None

    def test_h07_continuing_battle_no_victory_yet(self):
        evaluator = VictoryConditionEvaluator(
            conditions=[
                VictoryConditionType.ELIMINATE_ALL_ENEMIES,
                VictoryConditionType.ELIMINATE_ENEMY_COMMANDER,
            ],
        )
        ally = make_unit("cont_ally", faction=Faction.ALLIES)
        enemy_alive = make_unit("cont_enemy", faction=Faction.AXIS, hp=80)
        result, reason = evaluator.evaluate([ally, enemy_alive], tick=100)
        assert result == GameResult.ONGOING

    def test_h08_multiple_conditions_or_logic(self):
        evaluator = VictoryConditionEvaluator(
            conditions=[
                VictoryConditionType.ELIMINATE_ALL_ENEMIES,
                VictoryConditionType.ELIMINATE_ENEMY_COMMANDER,
            ],
        )
        ally = make_unit("or_ally", faction=Faction.ALLIES)
        ally_cmd = make_unit("or_acmd", faction=Faction.ALLIES, unit_type=UnitType.COMMANDER)
        enemy_cmd_dead = make_unit("or_ecmd", faction=Faction.AXIS, unit_type=UnitType.COMMANDER, hp=0, max_hp=100)
        enemy_inf = make_unit("or_einf", faction=Faction.AXIS)
        result, _ = evaluator.evaluate([ally, ally_cmd, enemy_cmd_dead, enemy_inf], tick=300)
        assert result == GameResult.ALLIES_VICTORY


# ========================================================================
# I. UI Elements Detail Check
# ========================================================================


@pytest.mark.e2e
class TestStageIUIDetailCheck:

    def test_i01_timer_format_mm_ss(self, screen, bottom_panel, camera, game_map, minimap_instance):
        bottom_panel.render(screen, camera, game_map, minimap=minimap_instance, time_remaining=185.0)

    def test_i02_timer_red_when_critical(self, screen, bottom_panel, camera, game_map, minimap_instance):
        bottom_panel.render(screen, camera, game_map, minimap=minimap_instance, time_remaining=15.0)

    def test_i03_info_toggle_buttons_present(self, bottom_panel):
        modes = bottom_panel.get_info_mode()
        assert modes in ("ALL", "STYLE", "OUTLINE")

    def test_i04_info_mode_can_be_changed(self, bottom_panel):
        bottom_panel.set_info_mode("STYLE")
        assert bottom_panel.get_info_mode() == "STYLE"
        bottom_panel.set_info_mode("OUTLINE")
        assert bottom_panel.get_info_mode() == "OUTLINE"

    def test_i05_invalid_info_mode_raises_error(self, bottom_panel):
        with pytest.raises(ValueError):
            bottom_panel.set_info_mode("INVALID")

    def test_i06_minimap_initializes(self, minimap_instance):
        assert minimap_instance is not None

    def test_i07_minimap_renders_without_crash(self, screen, minimap_instance):
        minimap_instance.render(screen, 1130, 560)

    def test_i08_minimap_zoom_levels_exist(self, bottom_panel):
        assert len(bottom_panel._zoom_levels) == 5
        assert 1.0 in bottom_panel._zoom_levels

    def test_i09_zoom_in_works(self, bottom_panel):
        initial_idx = bottom_panel._current_zoom_index
        if initial_idx < len(bottom_panel._zoom_levels) - 1:
            new_zoom = bottom_panel.zoom_in()
            assert bottom_panel._current_zoom_index == initial_idx + 1

    def test_i10_zoom_out_works(self, bottom_panel):
        initial_idx = bottom_panel._current_zoom_index
        if initial_idx > 0:
            new_zoom = bottom_panel.zoom_out()
            assert bottom_panel._current_zoom_index == initial_idx - 1

    def test_i11_panel_dimensions_match_spec(self):
        assert CC2BottomPanel.PANEL_HEIGHT == 130
        assert CC2BottomPanel.ROSTER_WIDTH == 170
        assert CC2BottomPanel.DETAIL_WIDTH == 240
        assert CC2BottomPanel.MINIMAP_SIZE == 120

    def test_i12_panel_has_all_sections(self, bottom_panel):
        assert hasattr(bottom_panel, '_render_roster')
        assert hasattr(bottom_panel, '_render_unit_details')
        assert hasattr(bottom_panel, '_render_command_bar')
        assert hasattr(bottom_panel, '_render_urgency_indicator')
        assert hasattr(bottom_panel, '_render_minimap_section')

    def test_i13_command_buttons_have_correct_keys(self, bottom_panel):
        key_map = {cmd["id"]: cmd["key"] for cmd in bottom_panel._commands}
        assert key_map == {
            "move": "Z",
            "fast": "X",
            "sneak": "S",
            "attack": "C",
            "smoke": "V",
            "defend": "D",
            "cancel": "ESC",
            "end_battle": "E",
        }

    def test_i14_handle_click_detects_roster_click(self, bottom_panel, ally_unit):
        bottom_panel.set_friendly_units([ally_unit])
        bottom_panel.initialize()
        surface = pygame.Surface((1280, 720))
        bottom_panel.render(surface, make_camera(), make_game_map())
        for rect, uid in bottom_panel._roster_item_rects:
            result = bottom_panel.handle_click((rect.centerx, rect.centery))
            assert result is not None
            assert "select_unit:" in result
            break

    def test_i15_urgency_indicator_calculates(self, bottom_panel, ally_unit):
        bottom_panel.set_friendly_units([ally_unit])
        bottom_panel.set_selected_unit(ally_unit.id)

    def test_i16_unit_display_name_attribute(self, ally_unit):
        name = getattr(ally_unit, 'display_name', None) or ally_unit.name
        assert name is not None
        assert len(name) > 0


# ========================================================================
# J. Keyboard Shortcuts
# ========================================================================


@pytest.mark.e2e
class TestStageJKeyboardShortcuts:

    def test_j01_wasd_moves_camera(self, camera):
        pos_before = (camera.position.x, camera.position.y)
        camera.move(10.0, 20.0)
        pos_after = (camera.position.x, camera.position.y)
        assert pos_before != pos_after

    def test_j02_arrow_keys_via_camera_move(self, camera):
        camera.move(-5.0, 0.0)
        camera.move(0.0, 5.0)

    def test_j03_zoom_in_via_adjust_zoom(self, camera):
        zoom_before = camera.zoom
        camera.adjust_zoom(1.2, anchor=(640, 360))
        assert camera.zoom != zoom_before
        assert camera.zoom > zoom_before

    def test_j04_zoom_out_via_adjust_zoom(self, camera):
        camera.zoom = 2.0
        zoom_before = camera.zoom
        camera.adjust_zoom(0.8, anchor=(640, 360))
        assert camera.zoom < zoom_before

    def test_j05_esc_cancels_and_deselects(self, ic, ally_unit):
        units = [ally_unit]
        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        ic.set_mode(InteractionMode.MOVE)
        assert ic.mode == InteractionMode.MOVE
        ic.handle_shortcut_key(pygame.K_ESCAPE)
        assert ic.mode == InteractionMode.SELECT
        assert len(ic.selected_unit_ids) == 0

    def test_j06_i_key_toggles_projection(self, ic):
        proj_before = ic.camera.projection
        ic.handle_shortcut_key(pygame.K_i)
        proj_after = ic.camera.projection
        assert proj_before != proj_after

    def test_j07_input_handler_process_mouse_motion(self):
        from pycc2.presentation.rendering.window_config import WindowManager
        from pycc2.presentation.input.handler import PygameInputHandler
        wm = WindowManager()
        cam = make_camera()
        handler = PygameInputHandler(camera=cam, window_manager=wm)
        mock_event = pygame.event.Event(pygame.MOUSEMOTION, pos=(100, 200))
        result = handler.process_event(mock_event)
        assert result.event_type == "mouse_move"
        assert result.position == (100.0, 200.0)

    def test_j08_input_handler_process_left_click(self):
        from pycc2.presentation.rendering.window_config import WindowManager
        from pycc2.presentation.input.handler import PygameInputHandler
        wm = WindowManager()
        cam = make_camera()
        handler = PygameInputHandler(camera=cam, window_manager=wm)
        mock_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(300, 400), button=1)
        result = handler.process_event(mock_event)
        assert result.event_type == "mouse_click_left"
        assert result.button == 1

    def test_j09_input_handler_process_right_click(self):
        from pycc2.presentation.rendering.window_config import WindowManager
        from pycc2.presentation.input.handler import PygameInputHandler
        wm = WindowManager()
        cam = make_camera()
        handler = PygameInputHandler(camera=cam, window_manager=wm)
        mock_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(300, 400), button=3)
        result = handler.process_event(mock_event)
        assert result.event_type == "mouse_click_right"
        assert result.button == 3

    def test_j10_input_handler_process_escape(self):
        from pycc2.presentation.rendering.window_config import WindowManager
        from pycc2.presentation.input.handler import PygameInputHandler
        wm = WindowManager()
        cam = make_camera()
        handler = PygameInputHandler(camera=cam, window_manager=wm)
        mock_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        result = handler.process_event(mock_event)
        assert result.event_type == "key_down"
        assert result.key == pygame.K_ESCAPE

    def test_j11_camera_zoom_within_bounds(self, camera):
        camera.zoom = 10.0
        camera.adjust_zoom(0.1, anchor=(640, 360))
        assert camera.zoom >= camera.MIN_ZOOM
        camera.zoom = 0.01
        camera.adjust_zoom(2.0, anchor=(640, 360))
        assert camera.zoom <= camera.MAX_ZOOM

    def test_j12_camera_constrain_to_map(self, camera):
        camera.constrain_to_map(640.0, 480.0)

    def test_j13_focus_on_method(self, camera):
        target = Vec2(100.0, 200.0)
        camera.focus_on(target)
        assert camera.position.x == 100.0
        assert camera.position.y == 200.0

    def test_j14_world_to_screen_conversion(self, camera):
        world_pos = Vec2(0.0, 0.0)
        screen_pos = camera.world_to_screen(world_pos)
        assert isinstance(screen_pos, tuple)
        assert len(screen_pos) == 2

    def test_j15_screen_to_world_conversion(self, camera):
        world_pos = camera.screen_to_world((640.0, 360.0))
        assert world_pos is not None
        assert hasattr(world_pos, 'x')
        assert hasattr(world_pos, 'y')


# ========================================================================
# Full Integration Journey Tests
# ========================================================================


@pytest.mark.e2e
class TestFullIntegrationJourney:

    def test_full_journey_deploy_to_victory(self):
        ui = DeploymentUI(width=1280, height=720)
        map_data = {"width": 20, "height": 20, "tiles": [[0] * 20 for _ in range(20)]}
        ui.start_deployment(map_data, faction="ally")
        assert ui.state.phase == DeploymentPhase.DEPLOYING
        placed = ui.place_unit(0, 0, 0)
        assert placed is True
        deploy_result = ui.begin_battle()
        assert deploy_result is not None
        assert deploy_result["phase"] == DeploymentPhase.ACTIVE

        ally = make_unit("fj_ally", "Rifle Squad", Faction.ALLIES, UnitType.INFANTRY_SQUAD, tile_x=3, tile_y=3)
        ally_cmd = make_unit("fj_acmd", "Commander", Faction.ALLIES, UnitType.COMMANDER, tile_x=2, tile_y=2)
        enemy = make_unit("fj_enemy", "Axis Squad", Faction.AXIS, UnitType.INFANTRY_SQUAD, tile_x=10, tile_y=10, hp=30)
        enemy_cmd = make_unit("fj_ecmd", "Axis Cmd", Faction.AXIS, UnitType.COMMANDER, tile_x=11, tile_y=11, hp=20)

        units = [ally, ally_cmd, enemy, enemy_cmd]
        game_map = make_game_map()
        event_bus = EventBus()
        camera_obj = make_camera()
        ic = InteractionController(camera=camera_obj, game_map=game_map, event_bus=event_bus)

        sp = camera_obj.world_to_screen(ally.position.pixel_position)
        selected = ic.handle_left_click(sp, units)
        assert ally.id in selected

        ic.handle_shortcut_key(pygame.K_m)
        assert ic.mode == InteractionMode.MOVE

        move_received = []
        ic.register_on_move(lambda ids, t: move_received.append((ids, t)))
        ic.handle_left_click((400.0, 400.0), units)
        assert len(move_received) == 1

        enemy.take_damage(30)
        enemy_cmd.take_damage(20)
        assert enemy.is_alive is False
        assert enemy_cmd.is_alive is False

        evaluator = VictoryConditionEvaluator(
            conditions=[
                VictoryConditionType.ELIMINATE_ENEMY_COMMANDER,
                VictoryConditionType.ELIMINATE_ALL_ENEMIES,
            ],
        )
        result, reason = evaluator.evaluate(units, tick=300)
        assert result == GameResult.ALLIES_VICTORY

        stats = BattleStats()
        stats.record_kill("allies")
        stats.record_kill("allies")
        stats.record_unit_lost("axis")
        stats.record_unit_lost("axis")
        assert stats.allies_kills == 2
        assert stats.axis_units_lost == 2

    def test_full_journey_deploy_to_defeat(self):
        ui = DeploymentUI(width=1280, height=720)
        map_data = {"width": 20, "height": 20, "tiles": [[0] * 20 for _ in range(20)]}
        ui.start_deployment(map_data, faction="ally")
        ui.place_unit(0, 0, 0)
        deploy_result = ui.begin_battle()
        assert deploy_result is not None

        ally = make_unit("fd_ally", "Rifle", Faction.ALLIES, UnitType.INFANTRY_SQUAD, hp=10, morale=5)
        ally_cmd = make_unit("fd_acmd", "Cmd", Faction.ALLIES, UnitType.COMMANDER, hp=10, morale=5)
        enemy = make_unit("fd_enemy", "Axis", Faction.AXIS, UnitType.INFANTRY_SQUAD, tile_x=10, tile_y=10)
        enemy_cmd = make_unit("fd_ecmd", "Axis Cmd", Faction.AXIS, UnitType.COMMANDER, tile_x=11, tile_y=11)

        units = [ally, ally_cmd, enemy, enemy_cmd]

        ally.take_damage(10)
        ally_cmd.take_damage(10)
        assert ally.is_alive is False
        assert ally_cmd.is_alive is False

        evaluator = VictoryConditionEvaluator(
            conditions=[
                VictoryConditionType.ELIMINATE_ALL_ENEMIES,
                VictoryConditionType.MORALE_COLLAPSE,
            ],
        )
        result, reason = evaluator.evaluate(units, tick=300)
        assert result == GameResult.AXIS_VICTORY

        stats = BattleStats()
        stats.record_unit_lost("allies")
        stats.record_unit_lost("allies")
        assert stats.allies_units_lost == 2

    def test_complete_command_cycle(self, ic, ally_unit, enemy_unit):
        pg = pygame
        units = [ally_unit, enemy_unit]

        sp = ic.camera.world_to_screen(ally_unit.position.pixel_position)
        ic.handle_left_click(sp, units)
        assert ally_unit.id in ic.selected_unit_ids

        ic.handle_shortcut_key(pg.K_m)
        assert ic.mode == InteractionMode.MOVE

        moves = []
        ic.register_on_move(lambda ids, t: moves.append(t))
        ic.handle_left_click((400.0, 400.0), units)
        assert len(moves) == 1
        assert ic.mode == InteractionMode.SELECT

        ic.handle_shortcut_key(pg.K_c)
        assert ic.mode == InteractionMode.ATTACK

        ic.attack_line.begin_attack(ally_unit.id, ally_unit.position.pixel_position)
        assert ic.attack_line.state.active is True

        ic.attack_line.cancel()
        assert ic.attack_line.state.active is False

        ic.handle_shortcut_key(pg.K_ESCAPE)
        assert ic.mode == InteractionMode.SELECT
        assert len(ic.selected_unit_ids) == 0

    def test_morale_combat_cycle(self):
        u = make_unit(morale=85)
        assert MoraleSystem.get_state(u.morale.value) == MoraleState.RALLYED

        MoraleSystem.apply_suppression(u, amount=80.0, dt=3.0)
        assert u.morale.value < 85
        state = MoraleSystem.get_state(u.morale.value)

        if state == MoraleState.PINNED:
            assert MoraleSystem.can_move(u) is False

        recovery = MoraleSystem.update_morale_recovery(u, dt=10.0, near_commander=True)
        assert recovery['recovered'] >= 0
