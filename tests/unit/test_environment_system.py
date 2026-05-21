from __future__ import annotations

import pytest

from pycc2.domain.systems.environment import (
    EnvironmentState,
    TimeOfDay,
    WeatherCondition,
)


class TestDayVisionNoPenalty:
    def test_day_vision_no_penalty(self):
        env = EnvironmentState.create_day_mission()
        assert env.get_vision_multiplier() == 1.0

    def test_day_is_not_night(self):
        env = EnvironmentState.create_day_mission()
        assert not env.is_night()


class TestNightVisionReduced:
    def test_night_vision_reduced(self):
        env = EnvironmentState.create_night_mission()
        mult = env.get_vision_multiplier()
        assert mult == pytest.approx(0.45, rel=1e-2)

    def test_night_is_night(self):
        env = EnvironmentState.create_night_mission()
        assert env.is_night()


class TestNightWithFlareRestoresVision:
    def test_flare_illuminates_tile(self):
        env = EnvironmentState.create_night_mission()
        env.add_flare(5, 5)
        assert env.is_tile_illuminated(5, 5)

    def test_flare_radius(self):
        env = EnvironmentState.create_night_mission()
        env.add_flare(5, 5)
        assert env.is_tile_illuminated(5 + env.FLARE_VISION_RADIUS, 5)
        assert not env.is_tile_illuminated(5 + env.FLARE_VISION_RADIUS + 1, 5)


class TestFlareExpiresAfterDuration:
    def test_flare_expires(self):
        env = EnvironmentState.create_night_mission()
        env.add_flare(5, 5)
        for _ in range(env.FLARE_DURATION_TICKS + 1):
            env.update_flares()
        assert len(env.active_flares) == 0
        assert not env.is_tile_illuminated(5, 5)

    def test_flare_still_active_before_expiry(self):
        env = EnvironmentState.create_night_mission()
        env.add_flare(5, 5)
        for _ in range(env.FLARE_DURATION_TICKS):
            env.update_flares()
        assert len(env.active_flares) == 1
        assert env.is_tile_illuminated(5, 5)


class TestRainCombinedWithNight:
    def test_rain_and_night_combined(self):
        env = EnvironmentState(
            time_of_day=TimeOfDay.NIGHT,
            weather=WeatherCondition.RAIN,
        )
        mult = env.get_vision_multiplier()
        expected = 0.45 * 0.80
        assert mult == pytest.approx(expected, rel=1e-2)


class TestStealthBonusInForestAtNight:
    def test_stealth_bonus_forest_at_night(self):
        env = EnvironmentState.create_night_mission()
        bonus = env.get_stealth_bonus(terrain_id=3)
        assert bonus == pytest.approx(0.50, rel=1e-2)

    def test_stealth_bonus_capped_at_max(self):
        env = EnvironmentState(
            time_of_day=TimeOfDay.NIGHT,
            night_stealth_bonus=0.50,
            forest_stealth_bonus=0.20,
        )
        bonus = env.get_stealth_bonus(terrain_id=3)
        assert bonus <= 0.60


class TestNightAccuracyReduction:
    def test_night_accuracy_reduction(self):
        env = EnvironmentState.create_night_mission()
        mod = env.get_accuracy_modifier()
        assert mod == pytest.approx(0.85, rel=1e-2)

    def test_day_accuracy_no_reduction(self):
        env = EnvironmentState.create_day_mission()
        mod = env.get_accuracy_modifier()
        assert mod == 1.0


class TestEnvironmentFactoryMethods:
    def test_factory_night_mission(self):
        env = EnvironmentState.create_night_mission()
        assert env.time_of_day == TimeOfDay.NIGHT
        assert env.weather == WeatherCondition.CLEAR

    def test_factory_day_mission(self):
        env = EnvironmentState.create_day_mission()
        assert env.time_of_day == TimeOfDay.DAY
        assert env.weather == WeatherCondition.CLEAR

    def test_default_state_is_day(self):
        env = EnvironmentState()
        assert env.time_of_day == TimeOfDay.DAY
