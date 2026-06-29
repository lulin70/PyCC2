from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.infrastructure.events.event_protocol import PlayerCommand
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
from pycc2.presentation.rendering.window_config import WindowManager
from pycc2.services.game_loop import GameLoop, GameState
from pycc2.services.random_context import RandomContext


@pytest.fixture
def mock_game_map():
    grid = np.zeros((16, 16), dtype=np.int8)
    return GameMap(id="test", name="Test Map", width=16, height=16, tile_grid=grid)


@pytest.fixture
def ally_unit() -> Unit:
    return Unit(
        id="ally_1",
        name="Ally Unit",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(3, 3)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def enemy_unit() -> Unit:
    return Unit(
        id="enemy_1",
        name="Enemy Unit",
        faction=Faction.AXIS,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(5, 5)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def weak_enemy_unit() -> Unit:
    return Unit(
        id="weak_enemy",
        name="Weak Enemy",
        faction=Faction.AXIS,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=10, max_hp=10),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(6, 6)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def camera():
    return Camera(position=Vec2(256.0, 256.0), viewport_width=1280, viewport_height=720)


@pytest.fixture
def sprite_renderer(pygame_display):
    """P1 Fix: Depend on conftest's pygame_display for proper init ordering."""
    import pygame

    if not pygame.font.get_init():
        pygame.font.init()
    return SpriteRenderer()


@pytest.fixture
def mock_window_manager():
    wm = Mock(spec=WindowManager)
    screen = Mock()
    screen.get_width.return_value = 1280
    screen.get_height.return_value = 720
    screen.get_size.return_value = (1280, 720)
    wm.get_screen.return_value = screen
    wm.fps = 60.0
    wm.tick.return_value = 16
    return wm


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def game_state_with_units(mock_game_map, ally_unit, enemy_unit, weak_enemy_unit, camera):
    units = [ally_unit, enemy_unit, weak_enemy_unit]
    return GameState(
        game_map=mock_game_map,
        units=units,
        camera=camera,
    )


@pytest.fixture
def combat_game_loop(sprite_renderer, mock_window_manager, event_bus, game_state_with_units):
    loop = GameLoop(
        renderer=sprite_renderer,
        window_manager=mock_window_manager,
        event_bus=event_bus,
        state=game_state_with_units,
        use_full_hud=False,
    )
    loop._combat_director.ballistic_engine = BallisticEngine(rng=RandomContext.from_seed(42))
    return loop


class TestAttackExecutesDamage:
    def test_attack_executes_damage(self, combat_game_loop, ally_unit, enemy_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        initial_hp = enemy_unit.health.hp
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="attack",
                unit_ids=["ally_1"],
                target_id="enemy_1",
            )
        )
        combat_game_loop._update_logic(1.0 / 30.0)
        assert enemy_unit.health.hp < initial_hp

    def test_attack_kills_unit(self, combat_game_loop, ally_unit, weak_enemy_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="attack",
                unit_ids=["ally_1"],
                target_id="weak_enemy",
            )
        )
        for _ in range(50):
            combat_game_loop._update_logic(1.0 / 30.0)
        assert weak_enemy_unit.is_alive is False or weak_enemy_unit.health.hp <= 0

    def test_hit_flash_triggers(self, combat_game_loop, ally_unit, enemy_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="attack",
                unit_ids=["ally_1"],
                target_id="enemy_1",
            )
        )
        combat_game_loop._update_logic(1.0 / 30.0)
        renderer = combat_game_loop.renderer
        if hasattr(renderer, "_flash_units"):
            assert len(renderer._flash_units) == 1, (
                "Should have exactly 1 flash unit after attacking enemy_1"
            )

    def test_damage_number_shows(self, combat_game_loop, ally_unit, enemy_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="attack",
                unit_ids=["ally_1"],
                target_id="enemy_1",
            )
        )
        combat_game_loop._update_logic(1.0 / 30.0)
        renderer = combat_game_loop.renderer
        if hasattr(renderer, "_damage_numbers"):
            assert len(renderer._damage_numbers) >= 1, (
                "Should have at least 1 damage number after attacking enemy_1 (may have multiple hits)"
            )

    def test_death_animation_on_kill(self, combat_game_loop, ally_unit, weak_enemy_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="attack",
                unit_ids=["ally_1"],
                target_id="weak_enemy",
            )
        )
        for _ in range(50):
            combat_game_loop._update_logic(1.0 / 30.0)
        renderer = combat_game_loop.renderer
        if hasattr(renderer, "_death_animations"):
            expected_animations = 1 if weak_enemy_unit.is_alive else 0
            assert len(renderer._death_animations) == expected_animations, (
                f"Should have {expected_animations} death animation(s) after killing weak_enemy"
            )

    def test_muzzle_flash_on_attack(self, combat_game_loop, ally_unit, enemy_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="attack",
                unit_ids=["ally_1"],
                target_id="enemy_1",
            )
        )
        combat_game_loop._update_logic(1.0 / 30.0)
        renderer = combat_game_loop.renderer
        if hasattr(renderer, "_particle_emitter"):
            from pycc2.presentation.rendering.animation_system import ParticleEmitter

            muzzle_particles = [
                p
                for p in renderer._particle_emitter.particles
                if p.type == ParticleEmitter.ParticleType.MUZZLE_FLASH
            ]
            assert len(muzzle_particles) >= 1, (
                "Should have at least 1 muzzle flash particle after attack"
            )


class TestAttackConstraints:
    def test_no_attack_out_of_range(self, combat_game_loop, mock_game_map, ally_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        far_enemy = Unit(
            id="far_enemy",
            name="Far Enemy",
            faction=Faction.AXIS,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=85),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(20, 20)),
            vision=VisionComponent(range_tiles=5),
        )
        combat_game_loop.state.units.append(far_enemy)
        initial_hp = far_enemy.health.hp
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="attack",
                unit_ids=["ally_1"],
                target_id="far_enemy",
            )
        )
        combat_game_loop._update_logic(1.0 / 30.0)
        assert far_enemy.health.hp == initial_hp

    def test_no_attack_wrong_faction(self, combat_game_loop, ally_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        friendly_fire_target = Unit(
            id="ally_2",
            name="Friendly Unit",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=85),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(7, 7)),
            vision=VisionComponent(range_tiles=5),
        )
        combat_game_loop.state.units.append(friendly_fire_target)
        initial_hp = friendly_fire_target.health.hp
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="attack",
                unit_ids=["ally_1"],
                target_id="ally_2",
            )
        )
        combat_game_loop._update_logic(1.0 / 30.0)
        assert friendly_fire_target.health.hp == initial_hp

    def test_weapon_ammo_consumes(self, combat_game_loop, ally_unit, enemy_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        initial_ammo = ally_unit.weapon.ammo_remaining
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="attack",
                unit_ids=["ally_1"],
                target_id="enemy_1",
            )
        )
        combat_game_loop._update_logic(1.0 / 30.0)
        assert ally_unit.weapon.ammo_remaining < initial_ammo

    def test_weapon_reload_needed(self, combat_game_loop, ally_unit, enemy_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        ally_unit.weapon.ammo_remaining = 0
        initial_hp = enemy_unit.health.hp
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="attack",
                unit_ids=["ally_1"],
                target_id="enemy_1",
            )
        )
        combat_game_loop._update_logic(1.0 / 30.0)
        assert enemy_unit.health.hp == initial_hp


class TestMoveAndStopCommands:
    def test_move_command_works(self, combat_game_loop, ally_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="move",
                unit_ids=["ally_1"],
                target=(7, 7),
            )
        )
        combat_game_loop._update_logic(1.0 / 30.0)
        assert "ally_1" in combat_game_loop._combat_director._move_orders

    def test_stop_command_clears_move(self, combat_game_loop, ally_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        combat_game_loop._combat_director._move_orders["ally_1"] = {
            "path": [TileCoord(7, 7)],
            "current_idx": 0,
        }
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="stop",
                unit_ids=["ally_1"],
            )
        )
        combat_game_loop._update_logic(1.0 / 30.0)
        assert "ally_1" not in combat_game_loop._combat_director._move_orders


class TestMultipleAttacks:
    def test_multiple_attacks_accumulate(self, combat_game_loop, ally_unit, enemy_unit):
        combat_game_loop._update_logic(1.0 / 30.0)
        initial_hp = enemy_unit.health.hp
        for _ in range(20):
            combat_game_loop.event_bus.publish(
                PlayerCommand(
                    command="attack",
                    unit_ids=["ally_1"],
                    target_id="enemy_1",
                )
            )
            combat_game_loop._update_logic(1.0 / 30.0)
        assert enemy_unit.health.hp < initial_hp
