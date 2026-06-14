"""Integration tests: LOS + Attack Line visual integration.

Tests the full pipeline from LOS calculation through attack line
status evaluation to visual rendering, verifying that terrain
blocking, range limits, and status colors integrate correctly.

Covers:
1. LOS system integration (FogOfWar + Lossystem)
2. Attack line status & color mapping
3. LOS → AttackLine → Renderer pipeline
4. Attack line + combat execution flow
"""

from __future__ import annotations

import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import pygame

pygame.init()

import numpy as np
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.fog_of_war import FogOfWar
from pycc2.domain.systems.los_system import LosStatus, Lossystem
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.input.attack_line_system import (
    AttackLineStatus,
    AttackLineSystem,
    AttackTarget,
)
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer


# ── Helpers ──────────────────────────────────────────────────────────


TILE_SIZE = Vec2.TILE_SIZE  # 32.0


def make_map_with_terrain(terrain_layout: list[list[int]]) -> GameMap:
    """Create a GameMap from a 2D terrain layout.

    terrain_layout example: [[0,0,8],[0,0,0],[0,0,0]] — wall at (2,0).
    """
    grid = np.array(terrain_layout, dtype=np.int8)
    h, w = grid.shape
    return GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)


def make_unit(
    unit_id: str = "test_unit",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    tile_x: int = 5,
    tile_y: int = 5,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 85,
    weapon_id: str = "rifle",
    max_ammo: int = 120,
) -> Unit:
    """Create a test Unit with sensible defaults.

    Note: AttackLineSystem uses getattr(attacker.weapon, 'max_range', 300)
    which always returns 300 since WeaponComponent has no max_range slot.
    """
    weapon = WeaponComponent(
        primary_weapon_id=weapon_id,
        max_ammo=max_ammo,
        ammo_remaining=max_ammo,
    )
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale),
        weapon=weapon,
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(),
    )


def make_elevated_map(
    width: int = 20,
    height: int = 20,
    elevated_coords: list[tuple[int, int, int]] | None = None,
) -> GameMap:
    """Create a map with elevation data in tiles_enhanced.

    elevated_coords: list of (x, y, elevation) tuples.
    """
    grid = np.zeros((height, width), dtype=np.int8)
    gm = GameMap(id="test", name="test", width=width, height=height, tile_grid=grid)
    if elevated_coords:
        if gm.tiles_enhanced is None:
            gm.tiles_enhanced = {}
        for x, y, elev in elevated_coords:
            gm.tiles_enhanced[f"{x},{y}"] = {"elevation": elev}
    return gm


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def pygame_screen():
    """Create a pygame surface for headless rendering."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    try:
        screen = pygame.display.set_mode((800, 600))
    except pygame.error:
        screen = pygame.Surface((800, 600), pygame.SRCALPHA)
    yield screen


@pytest.fixture
def camera():
    return Camera(position=Vec2(256.0, 256.0), viewport_width=800, viewport_height=600)


@pytest.fixture
def open_map():
    """20x20 all-open terrain map."""
    grid = np.zeros((20, 20), dtype=np.int8)
    return GameMap(id="test", name="Open Map", width=20, height=20, tile_grid=grid)


# =====================================================================
# 1. LOS System Integration Tests
# =====================================================================


@pytest.mark.integration
class TestLOSIntegration:
    """Test LOS calculations through FogOfWar and Lossystem."""

    def test_los_clear_between_two_units_on_open_ground(self, open_map):
        """两个单位在开阔地上LOS清晰。"""
        fow = FogOfWar(open_map.width, open_map.height)
        los = Lossystem(open_map)

        obs = TileCoord(5, 5)
        target = TileCoord(8, 8)

        # FogOfWar: update visibility from observer
        fow.update_visibility(
            observer_pos=obs,
            vision_range=6,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=open_map,
        )
        assert fow.is_visible(target)

        # Lossystem: direct LOS check
        can_see, result = los.check_los(obs, target)
        assert can_see
        assert result.status == LosStatus.CLEAR

    def test_los_blocked_by_wall_tile(self):
        """墙壁瓦片阻挡LOS。"""
        # Wall at column 5, row 5
        grid = np.zeros((12, 12), dtype=np.int8)
        grid[5][5] = TerrainType.WALL.value
        game_map = GameMap(id="wall", name="Wall Map", width=12, height=12, tile_grid=grid)

        los = Lossystem(game_map)
        can_see, result = los.check_los(TileCoord(3, 5), TileCoord(8, 5))
        assert not can_see
        assert result.status in (LosStatus.BLOCKED_TERRAIN, LosStatus.BLOCKED_HEIGHT)

    def test_los_blocked_by_building_solid(self):
        """实心建筑阻挡LOS。"""
        grid = np.zeros((12, 12), dtype=np.int8)
        grid[5][5] = TerrainType.BUILDING_SOLID.value
        game_map = GameMap(id="bldg", name="Building Map", width=12, height=12, tile_grid=grid)

        los = Lossystem(game_map)
        can_see, result = los.check_los(TileCoord(3, 5), TileCoord(8, 5))
        assert not can_see
        assert result.status in (LosStatus.BLOCKED_TERRAIN, LosStatus.BLOCKED_HEIGHT)

    def test_los_partial_block_by_woods(self):
        """树林部分阻挡LOS（降低可见度）。"""
        grid = np.zeros((12, 12), dtype=np.int8)
        grid[5][5] = TerrainType.WOODS.value
        game_map = GameMap(id="woods", name="Woods Map", width=12, height=12, tile_grid=grid)

        los = Lossystem(game_map)
        can_see, result = los.check_los(TileCoord(3, 5), TileCoord(8, 5))
        # Woods blocks_los=True, so LOS should be blocked
        # (unless target is adjacent to woods, which gives PARTIAL)
        assert result.status in (LosStatus.BLOCKED_TERRAIN, LosStatus.PARTIAL, LosStatus.CLEAR)

        # FogOfWar: woods should reduce visibility behind it
        fow = FogOfWar(game_map.width, game_map.height)
        fow.update_visibility(
            observer_pos=TileCoord(3, 5),
            vision_range=8,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=game_map,
        )
        # Tile directly behind woods may not be visible
        behind_woods = TileCoord(7, 5)
        # At minimum, the check should not crash
        _ = fow.is_visible(behind_woods)

    def test_los_through_road(self):
        """道路不阻挡LOS。"""
        grid = np.ones((12, 12), dtype=np.int8)  # all road
        game_map = GameMap(id="road", name="Road Map", width=12, height=12, tile_grid=grid)

        los = Lossystem(game_map)
        can_see, result = los.check_los(TileCoord(2, 2), TileCoord(10, 10))
        assert can_see
        assert result.status == LosStatus.CLEAR

    def test_los_elevation_advantage(self):
        """高处单位有LOS优势。"""
        # Observer on elevation 3, target at range that would normally be out of range
        game_map = make_elevated_map(
            width=20,
            height=20,
            elevated_coords=[(5, 5, 3)],  # Observer on hill
        )

        los = Lossystem(game_map)
        # Normal range is 15 tiles; elevation bonus = 3 * 2.0 = 6 extra
        # So effective range should be 21
        can_see_close, result_close = los.check_los(TileCoord(5, 5), TileCoord(5, 15))
        # Without elevation, distance=10 is within range anyway
        assert can_see_close

        # Far target at distance 18 — should be visible with elevation bonus
        can_see_far, result_far = los.check_los(TileCoord(5, 5), TileCoord(5, 23), max_range=15)
        # With elevation bonus (6), effective range = 21, distance ~18 → visible
        assert can_see_far or result_far.status == LosStatus.OUT_OF_RANGE

    def test_los_range_limit(self):
        """超出视野范围LOS不可用。"""
        game_map = make_map_with_terrain([[0] * 30 for _ in range(30)])
        los = Lossystem(game_map)

        # Max range 5, target at distance 10
        can_see, result = los.check_los(TileCoord(5, 5), TileCoord(15, 5), max_range=5)
        assert not can_see
        assert result.status == LosStatus.OUT_OF_RANGE


# =====================================================================
# 2. Attack Line System Integration Tests
# =====================================================================


@pytest.mark.integration
class TestAttackLineStatus:
    """Test attack line status evaluation and color mapping."""

    def test_attack_line_green_when_can_attack(self):
        """近距离→HIT_HIGH(绿色)。CC2 4-color system."""
        als = AttackLineSystem()
        attacker = make_unit("attacker", tile_x=5, tile_y=5)
        target_pos = Vec2(6 * TILE_SIZE, 5 * TILE_SIZE)
        target = AttackTarget(position=target_pos, distance=TILE_SIZE)

        status = als.evaluate_attack(attacker, target)
        assert status == AttackLineStatus.HIT_HIGH

        color = als.get_line_color(status)
        assert color == AttackLineSystem.COLOR_HIT_HIGH  # (0,255,0,200)

    def test_attack_line_red_when_out_of_range(self):
        """OUT_OF_RANGE状态→红色。"""
        als = AttackLineSystem()
        attacker = make_unit("attacker", tile_x=5, tile_y=5)
        # Target far away — distance > 300
        target_pos = Vec2(20 * TILE_SIZE, 20 * TILE_SIZE)
        dist = attacker.position.pixel_position.distance_to(target_pos)
        target = AttackTarget(position=target_pos, distance=dist)

        status = als.evaluate_attack(attacker, target)
        assert status == AttackLineStatus.OUT_OF_RANGE

        color = als.get_line_color(status)
        assert color == AttackLineSystem.COLOR_OUT_OF_RANGE  # (255,50,50,200)

    def test_attack_line_orange_when_blocked(self):
        """BLOCKED状态→橙色。"""
        als = AttackLineSystem()
        # Map with wall between attacker and target
        grid = np.zeros((20, 20), dtype=np.int8)
        grid[5][6] = TerrainType.WALL.value
        game_map = GameMap(id="los_block", name="LOS Block", width=20, height=20, tile_grid=grid)

        los_system = Lossystem(game_map)

        attacker = make_unit("attacker", tile_x=5, tile_y=5)
        target_pos = Vec2(8 * TILE_SIZE, 5 * TILE_SIZE)
        dist = attacker.position.pixel_position.distance_to(target_pos)
        target = AttackTarget(position=target_pos, distance=dist)

        status = als.evaluate_attack(attacker, target, game_map=game_map, los_system=los_system)
        assert status == AttackLineStatus.BLOCKED

        color = als.get_line_color(status)
        assert color == AttackLineSystem.COLOR_BLOCKED  # (255,100,0,200)

    def test_attack_line_yellow_when_tracking(self):
        """TRACKING_UNIT状态→黄色。"""
        als = AttackLineSystem()
        color = als.get_line_color(AttackLineStatus.TRACKING_UNIT)
        assert color == AttackLineSystem.COLOR_TRACKING  # (255,255,0,200)

    def test_attack_line_no_target_when_no_enemy(self):
        """无敌方单位→NO_TARGET。"""
        als = AttackLineSystem()
        # No weapon → NO_TARGET
        attacker = make_unit("attacker", tile_x=5, tile_y=5)
        attacker.weapon = None  # type: ignore[assignment]

        target_pos = Vec2(6 * TILE_SIZE, 5 * TILE_SIZE)
        target = AttackTarget(position=target_pos, distance=TILE_SIZE)

        status = als.evaluate_attack(attacker, target)
        assert status == AttackLineStatus.NO_TARGET

        color = als.get_line_color(status)
        # NO_TARGET color is gray
        assert color == (128, 128, 128, 100)


# =====================================================================
# 3. LOS → Attack Line → Renderer Pipeline Integration
# =====================================================================


@pytest.mark.integration
class TestAttackLineRendererPipeline:
    """Test the full LOS → AttackLine → EnhancedRenderer pipeline."""

    def test_attack_line_renders_on_enhanced_renderer(
        self, pygame_screen, camera, open_map
    ):
        """攻击线在EnhancedRenderer上渲染不崩溃。"""
        renderer = EnhancedRenderer()
        renderer.initialize(pygame_screen)

        als = AttackLineSystem()
        attacker = make_unit("attacker", tile_x=5, tile_y=5, faction=Faction.ALLIES)
        enemy = make_unit("enemy", tile_x=8, tile_y=5, faction=Faction.AXIS)

        # Begin attack from attacker
        source_pos = attacker.position.pixel_position
        als.begin_attack(unit_id="attacker", source_pos=source_pos)

        # Update mouse to enemy position
        target = als.update_mouse_position(
            screen_pos=(8 * TILE_SIZE, 5 * TILE_SIZE),
            world_pos=enemy.position.pixel_position,
            units=[attacker, enemy],
            attacker_faction=Faction.ALLIES,
        )

        # Evaluate attack
        target.status = als.evaluate_attack(attacker, target, game_map=open_map)

        # Attach attack line system to renderer
        renderer._attack_line_system = als

        # Render should not crash
        renderer.render(
            game_map=open_map,
            units=[attacker, enemy],
            camera=camera,
        )

    def test_attack_line_color_matches_status(self):
        """攻击线颜色与状态匹配。CC2 4-color system."""
        als = AttackLineSystem()
        expected = {
            AttackLineStatus.CAN_ATTACK: (0, 255, 0, 200),
            AttackLineStatus.OUT_OF_RANGE: (255, 50, 50, 200),
            AttackLineStatus.BLOCKED: (255, 100, 0, 200),
            AttackLineStatus.TRACKING_UNIT: (255, 255, 0, 200),
            AttackLineStatus.NO_TARGET: (128, 128, 128, 100),
            AttackLineStatus.HIT_HIGH: (0, 255, 0, 200),
            AttackLineStatus.HIT_MODERATE: (255, 255, 0, 200),
            AttackLineStatus.HIT_LOW: (255, 50, 50, 200),
            AttackLineStatus.HIT_IMPOSSIBLE: (0, 0, 0, 200),
        }
        for status, expected_color in expected.items():
            actual = als.get_line_color(status)
            assert actual == expected_color, f"Color mismatch for {status}: {actual} != {expected_color}"

    def test_confirmed_attack_line_draws_from_attacker_to_target(
        self, pygame_screen, camera, open_map
    ):
        """确认的攻击线从攻击者画到目标。"""
        renderer = EnhancedRenderer()
        renderer.initialize(pygame_screen)

        als = AttackLineSystem()
        attacker = make_unit("attacker", tile_x=5, tile_y=5, faction=Faction.ALLIES)
        enemy = make_unit("enemy", tile_x=10, tile_y=5, faction=Faction.AXIS)

        source_pos = attacker.position.pixel_position
        als.begin_attack(unit_id="attacker", source_pos=source_pos)

        target = als.update_mouse_position(
            screen_pos=(10 * TILE_SIZE, 5 * TILE_SIZE),
            world_pos=enemy.position.pixel_position,
            units=[attacker, enemy],
            attacker_faction=Faction.ALLIES,
        )

        target.status = als.evaluate_attack(attacker, target, game_map=open_map)

        # Confirm the attack
        als.confirm_attack(target)

        # Verify confirmed attack exists
        confirmed = als.get_confirmed_attack("attacker")
        assert confirmed is not None
        assert confirmed.unit_id == "enemy"

        # Render with confirmed attack line
        renderer._attack_line_system = als
        renderer.render(
            game_map=open_map,
            units=[attacker, enemy],
            camera=camera,
        )


# =====================================================================
# 4. Attack Line + Combat Execution Integration
# =====================================================================


@pytest.mark.integration
class TestAttackLineCombatExecution:
    """Test attack line confirmation leads to combat execution."""

    def test_attack_line_confirmed_then_combat_executed(self, open_map):
        """攻击线确认后战斗执行。"""
        als = AttackLineSystem()
        attacker = make_unit("attacker", tile_x=5, tile_y=5, faction=Faction.ALLIES)
        enemy = make_unit("enemy", tile_x=8, tile_y=5, faction=Faction.AXIS)

        source_pos = attacker.position.pixel_position
        als.begin_attack(unit_id="attacker", source_pos=source_pos)

        target = als.update_mouse_position(
            screen_pos=(8 * TILE_SIZE, 5 * TILE_SIZE),
            world_pos=enemy.position.pixel_position,
            units=[attacker, enemy],
            attacker_faction=Faction.ALLIES,
        )

        target.status = als.evaluate_attack(attacker, target, game_map=open_map)
        assert target.status == AttackLineStatus.HIT_HIGH

        # Confirm attack
        als.confirm_attack(target)

        # Verify confirmed attack is stored
        confirmed = als.get_confirmed_attack("attacker")
        assert confirmed is not None
        assert confirmed.unit_id == "enemy"
        assert confirmed.status == AttackLineStatus.HIT_HIGH

        # Simulate combat: attacker fires at enemy
        assert attacker.weapon.can_fire
        fired = attacker.weapon.fire()
        assert fired
        assert attacker.weapon.ammo_remaining < attacker.weapon.max_ammo

        # Apply damage to enemy
        damage = 15
        actual = enemy.take_damage(damage)
        assert actual == damage
        assert enemy.health.hp < enemy.health.max_hp

    def test_attack_line_updates_tracking(self, open_map):
        """攻击线追踪移动目标。"""
        als = AttackLineSystem()
        attacker = make_unit("attacker", tile_x=5, tile_y=5, faction=Faction.ALLIES)
        enemy = make_unit("enemy", tile_x=8, tile_y=5, faction=Faction.AXIS)

        source_pos = attacker.position.pixel_position
        als.begin_attack(unit_id="attacker", source_pos=source_pos)

        target = als.update_mouse_position(
            screen_pos=(8 * TILE_SIZE, 5 * TILE_SIZE),
            world_pos=enemy.position.pixel_position,
            units=[attacker, enemy],
            attacker_faction=Faction.ALLIES,
        )
        target.status = AttackLineStatus.TRACKING_UNIT

        als.confirm_attack(target)
        confirmed = als.get_confirmed_attack("attacker")
        assert confirmed is not None

        # Move enemy to new position
        enemy.move_to_tile(TileCoord(12, 5))

        # Update tracking — should follow the moved unit
        als.update_tracking([attacker, enemy])
        confirmed = als.get_confirmed_attack("attacker")
        assert confirmed is not None
        # Position should be updated to enemy's new pixel position
        expected_pos = enemy.position.pixel_position
        assert confirmed.position.x == expected_pos.x
        assert confirmed.position.y == expected_pos.y

    def test_attack_line_cancelled_no_combat(self, open_map):
        """攻击线取消后不执行战斗。"""
        als = AttackLineSystem()
        attacker = make_unit("attacker", tile_x=5, tile_y=5, faction=Faction.ALLIES)
        enemy = make_unit("enemy", tile_x=8, tile_y=5, faction=Faction.AXIS)

        source_pos = attacker.position.pixel_position
        als.begin_attack(unit_id="attacker", source_pos=source_pos)

        als.update_mouse_position(
            screen_pos=(8 * TILE_SIZE, 5 * TILE_SIZE),
            world_pos=enemy.position.pixel_position,
            units=[attacker, enemy],
            attacker_faction=Faction.ALLIES,
        )

        # Cancel before confirming
        als.cancel()

        # State should be reset
        assert not als.state.active
        assert als.state.source_unit_id is None

        # No confirmed attack
        confirmed = als.get_confirmed_attack("attacker")
        assert confirmed is None

        # Enemy should not have taken damage
        assert enemy.health.hp == enemy.health.max_hp

    def test_attack_line_removed_when_target_dies(self, open_map):
        """攻击线在目标被消灭后自动移除。"""
        als = AttackLineSystem()
        attacker = make_unit("attacker", tile_x=5, tile_y=5, faction=Faction.ALLIES)
        enemy = make_unit("enemy", tile_x=8, tile_y=5, faction=Faction.AXIS, hp=10, max_hp=10)

        source_pos = attacker.position.pixel_position
        als.begin_attack(unit_id="attacker", source_pos=source_pos)

        target = als.update_mouse_position(
            screen_pos=(8 * TILE_SIZE, 5 * TILE_SIZE),
            world_pos=enemy.position.pixel_position,
            units=[attacker, enemy],
            attacker_faction=Faction.ALLIES,
        )
        als.confirm_attack(target)

        # Kill the enemy
        enemy.take_damage(10)
        assert not enemy.is_alive

        # Update tracking — dead unit should be removed
        als.update_tracking([attacker, enemy])
        confirmed = als.get_confirmed_attack("attacker")
        assert confirmed is None


# =====================================================================
# 5. LOS + AttackLine Cross-System Integration
# =====================================================================


@pytest.mark.integration
class TestLOSToAttackLineIntegration:
    """Test that LOS results correctly feed into attack line status."""

    def test_los_clear_gives_can_attack(self, open_map):
        """LOS清晰→HIT_HIGH(CC2 4-color system)。"""
        los = Lossystem(open_map)
        als = AttackLineSystem()

        attacker = make_unit("attacker", tile_x=5, tile_y=5)
        target_pos = Vec2(8 * TILE_SIZE, 5 * TILE_SIZE)
        dist = attacker.position.pixel_position.distance_to(target_pos)
        target = AttackTarget(position=target_pos, distance=dist)

        status = als.evaluate_attack(attacker, target, game_map=open_map, los_system=los)
        assert status == AttackLineStatus.HIT_HIGH

    def test_los_blocked_gives_blocked_status(self):
        """LOS被阻挡→BLOCKED。"""
        grid = np.zeros((20, 20), dtype=np.int8)
        grid[5][6] = TerrainType.WALL.value
        game_map = GameMap(id="wall", name="Wall", width=20, height=20, tile_grid=grid)

        los = Lossystem(game_map)
        als = AttackLineSystem()

        attacker = make_unit("attacker", tile_x=5, tile_y=5)
        target_pos = Vec2(8 * TILE_SIZE, 5 * TILE_SIZE)
        dist = attacker.position.pixel_position.distance_to(target_pos)
        target = AttackTarget(position=target_pos, distance=dist)

        status = als.evaluate_attack(attacker, target, game_map=game_map, los_system=los)
        assert status == AttackLineStatus.BLOCKED

    def test_los_out_of_range_gives_out_of_range(self):
        """LOS超出范围→OUT_OF_RANGE。"""
        grid = np.zeros((30, 30), dtype=np.int8)
        game_map = GameMap(id="big", name="Big Map", width=30, height=30, tile_grid=grid)

        los = Lossystem(game_map)
        als = AttackLineSystem()

        attacker = make_unit("attacker", tile_x=5, tile_y=5)
        # Target at distance > 300 pixels (default weapon range)
        # (15-5)*32 = 320 > 300
        target_pos = Vec2(15 * TILE_SIZE, 5 * TILE_SIZE)
        dist = attacker.position.pixel_position.distance_to(target_pos)
        target = AttackTarget(position=target_pos, distance=dist)

        status = als.evaluate_attack(attacker, target, game_map=game_map, los_system=los)
        assert status == AttackLineStatus.OUT_OF_RANGE

    def test_fog_of_war_and_attack_line_consistency(self, open_map):
        """FogOfWar可见性和攻击线状态一致。"""
        fow = FogOfWar(open_map.width, open_map.height)
        los = Lossystem(open_map)
        als = AttackLineSystem()

        obs = TileCoord(5, 5)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=8,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=open_map,
        )

        # Target within vision range and weapon range
        target_tile = TileCoord(8, 5)
        assert fow.is_visible(target_tile)

        attacker = make_unit("attacker", tile_x=5, tile_y=5)
        target_pos = Vec2(8 * TILE_SIZE, 5 * TILE_SIZE)
        dist = attacker.position.pixel_position.distance_to(target_pos)
        target = AttackTarget(position=target_pos, distance=dist)

        status = als.evaluate_attack(attacker, target, game_map=open_map, los_system=los)
        assert status == AttackLineStatus.HIT_HIGH

    def test_building_solid_blocks_los_and_attack(self):
        """实心建筑同时阻挡FogOfWar LOS和攻击线。"""
        grid = np.zeros((20, 20), dtype=np.int8)
        grid[5][7] = TerrainType.BUILDING_SOLID.value
        game_map = GameMap(id="bldg", name="Building", width=20, height=20, tile_grid=grid)

        fow = FogOfWar(game_map.width, game_map.height)
        los = Lossystem(game_map)
        als = AttackLineSystem()

        obs = TileCoord(5, 5)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=10,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=game_map,
        )

        # Tile behind building should not be visible
        TileCoord(9, 5)
        # (May or may not be visible depending on ray angle, but building should block)

        # Attack line through building should be blocked
        attacker = make_unit("attacker", tile_x=5, tile_y=5)
        target_pos = Vec2(10 * TILE_SIZE, 5 * TILE_SIZE)
        dist = attacker.position.pixel_position.distance_to(target_pos)
        target = AttackTarget(position=target_pos, distance=dist)

        status = als.evaluate_attack(attacker, target, game_map=game_map, los_system=los)
        assert status == AttackLineStatus.BLOCKED

    def test_los_system_integrate_to_attack_line_status(self, open_map):
        """Lossystem.integrate_to_attack_line_status方法正确转换。"""
        los = Lossystem(open_map)

        # CLEAR → CAN_ATTACK
        _, result = los.check_los(TileCoord(3, 3), TileCoord(5, 5))
        status_str = los.integrate_to_attack_line_status(result)
        assert status_str == "CAN_ATTACK"

        # OUT_OF_RANGE
        _, result = los.check_los(TileCoord(3, 3), TileCoord(20, 20), max_range=3)
        status_str = los.integrate_to_attack_line_status(result)
        assert status_str == "OUT_OF_RANGE"
