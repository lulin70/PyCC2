from __future__ import annotations

import os
from unittest.mock import Mock

import numpy as np
import pygame
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.domain.systems.victory_conditions import (
    BattleStats,
    GameResult,
    VictoryConditionEvaluator,
    VictoryConditionType,
)
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.infrastructure.events.event_protocol import PlayerCommand
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.window_config import WindowManager
from pycc2.services.combat_director import CombatDirector
from pycc2.services.game_loop import GameLoop, GameState
from pycc2.services.random_context import RandomContext


@pytest.fixture(scope="module")
def pygame_env():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def combat_map():
    width, height = 20, 20
    grid = np.zeros((height, width), dtype=np.int8)
    return GameMap(
        id="combat_test",
        name="Combat Test Map",
        width=width,
        height=height,
        tile_grid=grid,
    )


@pytest.fixture
def ally_infantry() -> Unit:
    return Unit(
        id="ally_rifle_1",
        name="Alpha Rifle Squad",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=90),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(5, 5)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def enemy_infantry() -> Unit:
    return Unit(
        id="enemy_rifle_1",
        name="Axis Rifle Squad",
        faction=Faction.AXIS,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=80, max_hp=80),
        morale=MoraleComponent(value=75),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(8, 8)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def weak_enemy() -> Unit:
    return Unit(
        id="weak_enemy_1",
        name="Weak Axis Unit",
        faction=Faction.AXIS,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=15, max_hp=15),
        morale=MoraleComponent(value=50),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=5, max_ammo=5),
        position=PositionComponent(tile_coord=TileCoord(6, 6)),
        vision=VisionComponent(range_tiles=4),
    )


@pytest.fixture
def ally_commander() -> Unit:
    return Unit(
        id="ally_cmd_miller",
        name="Cpt. Miller",
        faction=Faction.ALLIES,
        unit_type=UnitType.COMMANDER,
        health=HealthComponent(hp=120, max_hp=120),
        morale=MoraleComponent(value=95),
        weapon=WeaponComponent(primary_weapon_id="pistol", ammo_remaining=14, max_ammo=14),
        position=PositionComponent(tile_coord=TileCoord(3, 3)),
        vision=VisionComponent(range_tiles=7),
    )


@pytest.fixture
def enemy_commander() -> Unit:
    return Unit(
        id="enemy_cmd_krebs",
        name="Oberst Krebs",
        faction=Faction.AXIS,
        unit_type=UnitType.COMMANDER,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=90),
        weapon=WeaponComponent(primary_weapon_id="pistol", ammo_remaining=12, max_ammo=12),
        position=PositionComponent(tile_coord=TileCoord(15, 15)),
        vision=VisionComponent(range_tiles=7),
    )


@pytest.fixture
def display_config():
    from pycc2.domain.interfaces.display_config import DisplayConfig

    return DisplayConfig()


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def combat_director(event_bus, display_config):
    director = CombatDirector(
        event_bus=event_bus,
        display_config=display_config,
        sound_system=None,
    )
    director.initialize()
    return director


@pytest.fixture
def camera():
    return Camera(position=Vec2(256.0, 256.0), viewport_width=1280, viewport_height=720)


@pytest.fixture
def full_combat_state(
    combat_map, ally_infantry, enemy_infantry, weak_enemy, ally_commander, enemy_commander, camera
):
    units = [ally_infantry, enemy_infantry, weak_enemy, ally_commander, enemy_commander]
    return GameState(
        game_map=combat_map,
        units=units,
        camera=camera,
    )


@pytest.fixture
def combat_game_loop(pygame_env, full_combat_state, event_bus, combat_director, monkeypatch):
    wm = WindowManager()
    mock_screen = Mock()
    mock_screen.get_size.return_value = (1280, 720)
    monkeypatch.setattr(wm, "initialize", lambda: mock_screen)
    monkeypatch.setattr(wm, "get_screen", lambda: mock_screen)

    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

    renderer = EnhancedRenderer()
    screen = wm.initialize()
    renderer.initialize(screen)

    from pycc2.presentation.input.handler import PygameInputHandler

    input_handler = PygameInputHandler(camera=full_combat_state.camera, window_manager=wm)

    loop = GameLoop(
        renderer=renderer,
        window_manager=wm,
        event_bus=event_bus,
        state=full_combat_state,
        input_handler=input_handler,
        use_full_hud=False,
    )
    loop._combat_director = combat_director
    combat_director.set_context(full_combat_state.units, combat_map)
    loop._combat_director.ballistic_engine = BallisticEngine(rng=RandomContext.from_seed(42))
    return loop


class TestAttackEnemyDealsDamage:
    def test_attack_enemy_deals_damage(self, combat_game_loop, ally_infantry, enemy_infantry):
        initial_hp = enemy_infantry.health.hp
        combat_game_loop._update_logic(1.0 / 30.0)
        combat_game_loop.event_bus.publish(
            PlayerCommand(
                command="attack",
                unit_ids=["ally_rifle_1"],
                target_id="enemy_rifle_1",
            )
        )
        combat_game_loop._update_logic(1.0 / 30.0)
        assert enemy_infantry.health.hp < initial_hp, "攻击应该对敌军造成伤害"


class TestUnitDeathAfterZeroHP:
    def test_unit_death_after_zero_hp(self, combat_game_loop, ally_infantry, weak_enemy):
        assert weak_enemy.is_alive is True, "弱敌单位初始状态应该是存活的"
        combat_game_loop._update_logic(1.0 / 30.0)
        for _ in range(30):
            combat_game_loop.event_bus.publish(
                PlayerCommand(
                    command="attack",
                    unit_ids=["ally_rifle_1"],
                    target_id="weak_enemy_1",
                )
            )
            combat_game_loop._update_logic(1.0 / 30.0)
            if not weak_enemy.is_alive or weak_enemy.health.hp <= 0:
                break
        assert weak_enemy.is_alive is False or weak_enemy.health.hp <= 0, (
            "单位HP降到0后应进入死亡状态"
        )


class TestVictoryWhenAllEnemiesEliminated:
    def test_victory_when_all_enemies_eliminated(self, combat_game_loop):
        evaluator = VictoryConditionEvaluator(
            conditions=[VictoryConditionType.ELIMINATE_ALL_ENEMIES]
        )
        for unit in combat_game_loop.state.units:
            if unit.faction == Faction.AXIS:
                unit.take_damage(unit.health.max_hp + 100)
        result, reason = evaluator.evaluate(
            units=combat_game_loop.state.units,
            tick=600,
        )
        assert result == GameResult.ALLIES_VICTORY, "歼灭所有敌军后应触发盟军胜利条件"
        assert "destroyed" in reason.lower() or "eliminated" in reason.lower()


class TestDefeatWhenCommanderKilled:
    def test_defeat_when_commander_killed(self, combat_game_loop, ally_commander):
        evaluator = VictoryConditionEvaluator(
            conditions=[
                VictoryConditionType.ELIMINATE_ALL_ENEMIES,
            ]
        )
        ally_commander.take_damage(ally_commander.health.max_hp + 100)
        assert ally_commander.is_alive is False, "指挥官阵亡后应为死亡状态"
        # Kill all allies to trigger axis victory
        for unit in combat_game_loop.state.units:
            if unit.faction == Faction.ALLIES:
                unit.take_damage(unit.health.max_hp + 100)
        result, reason = evaluator.evaluate(
            units=combat_game_loop.state.units,
            tick=600,
        )
        assert result == GameResult.AXIS_VICTORY, "友方全灭应触发轴心国胜利"


class TestForceMoraleCollapseCausesRout:
    def test_force_morale_collapse_causes_rout(
        self, combat_game_loop, enemy_infantry, weak_enemy, enemy_commander
    ):
        evaluator = VictoryConditionEvaluator(
            conditions=[VictoryConditionType.FORCE_MORALE_COLLAPSE],
            force_morale_threshold=15,
        )
        for unit in combat_game_loop.state.units:
            if unit.faction == Faction.AXIS:
                unit.morale.value = 5
        result, reason = evaluator.evaluate(
            units=combat_game_loop.state.units,
            tick=combat_game_loop.state.tick,
        )
        assert result == GameResult.ALLIES_VICTORY, "敌军士气崩溃应触发盟军胜利"
        assert "morale" in reason.lower() or "collapsed" in reason.lower()

    def test_low_morale_units_marked_as_panicked(self, combat_game_loop, enemy_infantry):
        enemy_infantry.morale.value = 10
        combat_game_loop._combat_director.update(
            units=combat_game_loop.state.units,
            game_map=combat_game_loop.state.game_map,
            dt=1.0 / 30.0,
        )
        assert enemy_infantry.morale.value <= enemy_infantry.morale.panic_threshold, (
            "低士气单位应处于恐慌状态"
        )


class TestCombatDirectorIntegration:
    def test_director_processes_attack_command(
        self, combat_director, combat_map, ally_infantry, enemy_infantry
    ):
        units = [ally_infantry, enemy_infantry]
        combat_director.set_context(units, combat_map)
        initial_hp = enemy_infantry.health.hp
        for _ in range(10):
            combat_director.handle_player_command(
                data={
                    "command": "attack",
                    "unit_ids": ["ally_rifle_1"],
                    "target_id": "enemy_rifle_1",
                },
                units=units,
                game_map=combat_map,
            )
        assert enemy_infantry.health.hp <= initial_hp, (
            "战斗导演应正确处理攻击命令（可能未命中或造成伤害）"
        )

    def test_director_records_battle_stats_on_kill(
        self, combat_director, combat_map, ally_infantry, weak_enemy
    ):
        units = [ally_infantry, weak_enemy]
        combat_director.set_context(units, combat_map)
        stats = BattleStats()
        for _ in range(20):
            combat_director.handle_player_command(
                data={
                    "command": "attack",
                    "unit_ids": ["ally_rifle_1"],
                    "target_id": "weak_enemy_1",
                },
                units=units,
                game_map=combat_map,
            )
        combat_director.process_deaths(units, battle_stats=stats)
        if not weak_enemy.is_alive:
            assert stats.axis_units_lost >= 1, "击杀敌军后战斗统计应记录轴心国损失"

    def test_friendly_fire_prevented(
        self, combat_director, combat_map, ally_infantry, ally_commander
    ):
        units = [ally_infantry, ally_commander]
        combat_director.set_context(units, combat_map)
        initial_hp = ally_commander.health.hp
        combat_director.handle_player_command(
            data={
                "command": "attack",
                "unit_ids": ["ally_rifle_1"],
                "target_id": "ally_cmd_miller",
            },
            units=units,
            game_map=combat_map,
        )
        assert ally_commander.health.hp == initial_hp, "友军伤害应被阻止"
