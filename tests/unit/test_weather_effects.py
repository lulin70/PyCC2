"""
Comprehensive test suite for Weather Effects System (B8).
Tests business logic, state management, transitions, and integration.
"""

from __future__ import annotations

import random

import pytest

from pycc2.domain.systems.weather_effects import (
    WeatherEffects,
    WeatherState,
    WeatherTransitionTable,
    WeatherType,
)


class TestWeatherTypeEnum:
    def test_all_weather_types_exist(self):
        expected = {"CLEAR", "RAIN", "FOG", "SNOW", "OVERCAST"}
        actual = {t.name for t in WeatherType}
        assert expected == actual

    def test_weather_type_values_are_unique(self):
        values = [t.value for t in WeatherType]
        assert len(values) == len(set(values))


class TestWeatherStateInit:
    def test_default_state_is_clear(self):
        state = WeatherState()
        assert state.weather_type == WeatherType.CLEAR
        assert state.intensity == 1.0
        assert state.duration_turns == 0
        assert state.remaining_turns == 0

    def test_custom_state_init(self):
        state = WeatherState(
            weather_type=WeatherType.RAIN,
            intensity=0.7,
            duration_turns=5,
            remaining_turns=5,
        )
        assert state.weather_type == WeatherType.RAIN
        assert state.intensity == 0.7
        assert state.duration_turns == 5


class TestWeatherStateIsActive:
    def test_clear_is_not_active(self):
        state = WeatherState()
        assert not state.is_active()

    def test_rain_is_active(self):
        state = WeatherState(weather_type=WeatherType.RAIN)
        assert state.is_active()

    def test_fog_is_active(self):
        state = WeatherState(weather_type=WeatherType.FOG)
        assert state.is_active()

    def test_snow_is_active(self):
        state = WeatherState(weather_type=WeatherType.SNOW)
        assert state.is_active()


class TestWeatherStateExpiration:
    def test_infinite_duration_never_expires(self):
        state = WeatherState(weather_type=WeatherType.RAIN, duration_turns=0)
        assert not state.is_expired()

    def test_remaining_turns_expires(self):
        state = WeatherState(
            weather_type=WeatherType.RAIN,
            duration_turns=3,
            remaining_turns=0,
        )
        assert state.is_expired()

    def test_positive_remaining_not_expired(self):
        state = WeatherState(
            weather_type=WeatherType.RAIN,
            duration_turns=3,
            remaining_turns=2,
        )
        assert not state.is_expired()


class TestWeatherStateAdvanceTurn:
    def test_advance_decrements_remaining(self):
        state = WeatherState(
            weather_type=WeatherType.RAIN,
            duration_turns=3,
            remaining_turns=3,
        )
        state.advance_turn()
        assert state.remaining_turns == 2

    def test_advance_to_zero_clears_weather(self):
        state = WeatherState(
            weather_type=WeatherType.RAIN,
            duration_turns=1,
            remaining_turns=1,
        )
        state.advance_turn()
        assert state.weather_type == WeatherType.CLEAR

    def test_advance_already_clear_no_change(self):
        state = WeatherState()
        initial_remaining = state.remaining_turns
        state.advance_turn()
        assert state.remaining_turns == initial_remaining


class TestWeatherStateSetWeather:
    def test_set_weather_updates_all_fields(self):
        state = WeatherState()
        state.set_weather(WeatherType.FOG, 0.8, 4)
        assert state.weather_type == WeatherType.FOG
        assert state.intensity == 0.8
        assert state.duration_turns == 4
        assert state.remaining_turns == 4

    def test_set_weather_clamps_intensity_high(self):
        state = WeatherState()
        state.set_weather(WeatherType.RAIN, intensity=2.0)
        assert state.intensity == 1.0

    def test_set_weather_clamps_intensity_low(self):
        state = WeatherState()
        state.set_weather(WeatherType.RAIN, intensity=-0.5)
        assert state.intensity == 0.0


class TestWeatherEffectsVisionModifiers:
    @pytest.mark.parametrize(
        "weather,expected",
        [
            (WeatherType.CLEAR, 1.0),
            (WeatherType.RAIN, 0.7),
            (WeatherType.FOG, 0.5),
            (WeatherType.SNOW, 0.85),
            (WeatherType.OVERCAST, 0.9),
        ],
    )
    def test_vision_modifier_values(self, weather, expected):
        effects = WeatherEffects()
        result = effects.apply_to_vision(10.0, weather)
        assert result == pytest.approx(10.0 * expected, rel=1e-2)

    def test_vision_base_range_preserved_shape(self):
        effects = WeatherEffects()
        base = 15.0
        for weather in WeatherType:
            modified = effects.apply_to_vision(base, weather)
            assert modified <= base


class TestWeatherEffectsMovementModifiers:
    @pytest.mark.parametrize(
        "weather,expected",
        [
            (WeatherType.CLEAR, 1.0),
            (WeatherType.RAIN, 0.9),
            (WeatherType.FOG, 1.0),
            (WeatherType.SNOW, 0.8),
            (WeatherType.OVERCAST, 1.0),
        ],
    )
    def test_movement_modifier_values(self, weather, expected):
        effects = WeatherEffects()
        result = effects.apply_to_movement(6.0, weather)
        assert result == pytest.approx(6.0 * expected, rel=1e-2)


class TestWeatherEffectsMudPenalty:
    def test_mud_penalty_in_rain(self):
        effects = WeatherEffects()
        base = 6.0
        result = effects.apply_to_movement(base, WeatherType.RAIN, is_muddy_terrain=True)
        expected = base * 0.9 * 0.7
        assert result == pytest.approx(expected, rel=1e-2)

    def test_mud_penalty_not_applied_in_clear(self):
        effects = WeatherEffects()
        base = 6.0
        result = effects.apply_to_movement(base, WeatherType.CLEAR, is_muddy_terrain=True)
        assert result == base

    def test_mud_penalty_not_applied_without_mud(self):
        effects = WeatherEffects()
        base = 6.0
        result = effects.apply_to_movement(base, WeatherType.RAIN, is_muddy_terrain=False)
        assert result == pytest.approx(base * 0.9, rel=1e-2)


class TestWeatherEffectsConcealmentBonus:
    @pytest.mark.parametrize(
        "weather,expected",
        [
            (WeatherType.CLEAR, 0.0),
            (WeatherType.RAIN, 0.1),
            (WeatherType.FOG, 0.2),
            (WeatherType.SNOW, 0.05),
            (WeatherType.OVERCAST, 0.0),
        ],
    )
    def test_concealment_bonus_values(self, weather, expected):
        effects = WeatherEffects()
        assert effects.get_concealment_bonus(weather) == pytest.approx(expected, rel=1e-2)


class TestWeatherEffectsAccuracyModifiers:
    def test_accuracy_rain_reduced(self):
        effects = WeatherEffects()
        result = effects.apply_to_accuracy(0.9, WeatherType.RAIN)
        assert result < 0.9

    def test_accuracy_clear_unaffected(self):
        effects = WeatherEffects()
        result = effects.apply_to_accuracy(0.85, WeatherType.CLEAR)
        assert result == 0.85


class TestWeatherTransitionTable:
    def test_transition_from_clear_stays_likely(self):
        rng = random.Random(42)
        results = [
            WeatherTransitionTable.get_next_weather(WeatherType.CLEAR, rng) for _ in range(100)
        ]
        clear_count = sum(1 for w in results if w == WeatherType.CLEAR)
        assert clear_count > 50

    def test_transition_returns_valid_weather(self):
        rng = random.Random(123)
        for current in WeatherType:
            for _ in range(20):
                next_w = WeatherTransitionTable.get_next_weather(current, rng)
                assert next_w in WeatherType

    def test_generate_duration_returns_positive(self):
        rng = random.Random(99)
        for weather in WeatherType:
            duration = WeatherTransitionTable.generate_weather_duration(weather, rng)
            assert duration >= 1, (
                f"Weather {weather.name} duration should be at least 1 turn, got {duration}"
            )

    def test_snow_longer_than_fog_typically(self):
        rng = random.Random(42)
        snow_durations = [
            WeatherTransitionTable.generate_weather_duration(WeatherType.SNOW, rng)
            for _ in range(50)
        ]
        fog_durations = [
            WeatherTransitionTable.generate_weather_duration(WeatherType.FOG, rng)
            for _ in range(50)
        ]
        assert sum(snow_durations) > sum(fog_durations)


class TestIntegrationWeatherAndEnvironment:
    def test_combined_vision_reduction_night_rain(self):
        from pycc2.domain.systems.environment import EnvironmentState, TimeOfDay, WeatherCondition

        env = EnvironmentState(time_of_day=TimeOfDay.NIGHT, weather=WeatherCondition.RAIN)
        mult = env.get_vision_multiplier()
        expected = 0.45 * 0.80
        assert mult == pytest.approx(expected, rel=1e-2)

    def test_stealth_bonus_forest_night_capped(self):
        from pycc2.domain.systems.environment import EnvironmentState

        env = EnvironmentState(night_stealth_bonus=0.50, forest_stealth_bonus=0.20)
        bonus = env.get_stealth_bonus(terrain_id=3)
        assert bonus <= 0.60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
