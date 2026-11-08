"""Tests for weather affecting LOS and accuracy (P1-4)."""

from __future__ import annotations

import numpy as np

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.domain.systems.los_system import LOSSystem
from pycc2.domain.systems.weather_effects import (
    WeatherEffects,
    WeatherState,
    WeatherType,
    weather_type_from_name,
)
from pycc2.domain.value_objects.tile_coord import TileCoord


class _FixedRng:
    def uniform(self, low: float, high: float) -> float:
        return (low + high) / 2.0

    def gaussian(self, mu: float, sigma: float) -> float:
        return mu


def _map(width: int = 20, height: int = 20) -> GameMap:
    return GameMap(
        id="test",
        name="Test Map",
        width=width,
        height=height,
        tile_grid=np.zeros((height, width), dtype=np.int8),
    )


def _unit(x: int = 0, y: int = 0) -> Unit:
    return Unit(
        id="u1",
        name="Test",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(),
    )


def test_weather_name_mapping():
    assert weather_type_from_name("fog") == WeatherType.FOG
    assert weather_type_from_name("RAIN") == WeatherType.RAIN
    assert weather_type_from_name("unknown") == WeatherType.CLEAR


def test_fog_reduces_los_range():
    game_map = _map()
    los = LOSSystem(game_map, weather_effects=WeatherEffects())
    start = TileCoord(0, 0)
    end = TileCoord(10, 0)

    los.set_weather(WeatherType.CLEAR)
    clear_visible, _ = los.check_los(start, end)
    los.set_weather(WeatherType.FOG)
    fog_visible, _ = los.check_los(start, end)

    assert clear_visible is True
    assert fog_visible is False


def test_rain_reduces_accuracy():
    game_map = _map()
    attacker = _unit(0, 0)
    target = _unit(5, 0)
    engine = BallisticEngine(rng=_FixedRng())

    clear_state = WeatherState(weather_type=WeatherType.CLEAR)
    game_map.weather_state = clear_state
    clear_shot = engine.calculate_shot(attacker, target, game_map=game_map)

    rain_state = WeatherState(weather_type=WeatherType.RAIN)
    game_map.weather_state = rain_state
    rain_shot = engine.calculate_shot(attacker, target, game_map=game_map)

    assert rain_shot.actual_accuracy < clear_shot.actual_accuracy


def test_clear_weather_has_no_penalty():
    effects = WeatherEffects()

    assert effects.apply_to_vision(15.0, WeatherType.CLEAR) == 15.0
    assert effects.apply_to_accuracy(0.5, WeatherType.CLEAR) == 0.5
