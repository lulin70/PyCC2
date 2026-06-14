"""
Comprehensive test suite for Day-Night Cycle System (B9).
Tests time progression, period detection, effects, and searchlight logic.
"""

from __future__ import annotations

import pytest
from pycc2.domain.systems.day_night_cycle import (
    TimeOfDay,
    GameTime,
    DayNightEffects,
    Searchlight,
)


class TestTimeOfDayEnum:
    def test_all_periods_exist(self):
        expected = {"DAWN", "DAY", "DUSK", "NIGHT"}
        actual = {t.name for t in TimeOfDay}
        assert expected == actual


class TestGameTimeInit:
    def test_default_init(self):
        gt = GameTime()
        assert gt.total_seconds == 0.0
        assert gt.time_scale == 600.0

    def test_custom_time_scale(self):
        gt = GameTime(time_scale=300.0)
        assert gt.time_scale == 300.0


class TestGameTimeHours:
    def test_initial_hours_zero(self):
        gt = GameTime()
        assert gt.hours == pytest.approx(0.0, abs=1e-2)

    def test_one_real_second_equals_ten_minutes(self):
        gt = GameTime(time_scale=600.0)
        gt.advance(1.0)
        expected_hours = (1.0 * 600.0) / 3600.0
        assert gt.hours == pytest.approx(expected_hours, rel=1e-2)

    def test_hours_wrap_at_midnight(self):
        gt = GameTime(time_scale=600.0)
        gt.set_time(23.0)
        gt.advance(60.0)
        assert gt.hours < 24.0
        assert gt.hours >= 0.0


class TestGameTimeMinutes:
    def test_minutes_calculated_correctly(self):
        gt = GameTime(time_scale=600.0)
        gt.set_time(6.5)
        assert gt.minutes == 30

    def test_minute_precision(self):
        gt = GameTime(time_scale=3600)
        gt.set_time(12.25)
        assert gt.minutes == 15


class TestGameTimeFormattedOutput:
    def test_formatted_midnight(self):
        gt = GameTime(time_scale=600.0)
        gt.set_time(0.0)
        assert "12:00" in gt.formatted_time
        assert "AM" in gt.formatted_time

    def test_formatted_noon(self):
        gt = GameTime(time_scale=600.0)
        gt.set_time(12.0)
        assert "12:00" in gt.formatted_time
        assert "PM" in gt.formatted_time


class TestGameTimeAdvance:
    def test_advance_increases_total(self):
        gt = GameTime()
        initial = gt.total_seconds
        gt.advance(0.5)
        assert gt.total_seconds > initial

    def test_advance_multiple_steps(self):
        gt = GameTime()
        for _ in range(10):
            gt.advance(0.1)
        assert gt.total_seconds == pytest.approx(1.0, rel=1e-2)


class TestGameTimeSetTime:
    def test_set_morning(self):
        gt = GameTime()
        gt.set_time(8.0)
        assert 7.0 <= gt.hours < 18.0

    def test_set_night(self):
        gt = GameTime()
        gt.set_time(22.0)
        assert gt.hours >= 20.0 or gt.hours < 5.0

    def test_set_negative_wraps(self):
        gt = GameTime()
        gt.set_time(-1.0)
        assert 0.0 <= gt.hours < 24.0


class TestGameTimePeriodDetection:
    @pytest.mark.parametrize("hour,expected_period", [
        (5.5, TimeOfDay.DAWN),
        (6.0, TimeOfDay.DAWN),
        (6.9, TimeOfDay.DAWN),
        (7.0, TimeOfDay.DAY),
        (12.0, TimeOfDay.DAY),
        (17.9, TimeOfDay.DAY),
        (18.0, TimeOfDay.DUSK),
        (19.0, TimeOfDay.DUSK),
        (19.9, TimeOfDay.DUSK),
        (20.0, TimeOfDay.NIGHT),
        (0.0, TimeOfDay.NIGHT),
        (4.0, TimeOfDay.NIGHT),
        (4.9, TimeOfDay.NIGHT),
    ])
    def test_period_detection_accuracy(self, hour, expected_period):
        gt = GameTime()
        gt.set_time(hour)
        assert gt.time_of_day == expected_period


class TestDayNightEffectsVisionModifiers:
    @pytest.mark.parametrize("tod,expected_modifier", [
        (TimeOfDay.DAWN, 0.9),
        (TimeOfDay.DAY, 1.0),
        (TimeOfDay.DUSK, 0.8),
        (TimeOfDay.NIGHT, 0.3),
    ])
    def test_vision_penalty_values(self, tod, expected_modifier):
        effects = DayNightEffects()
        base = 10.0
        result = effects.apply_vision_penalty(base, tod)
        assert result == pytest.approx(base * expected_modifier, rel=1e-2)

    def test_night_severely_reduces_vision(self):
        effects = DayNightEffects()
        day_range = effects.apply_vision_penalty(10.0, TimeOfDay.DAY)
        night_range = effects.apply_vision_penalty(10.0, TimeOfDay.NIGHT)
        assert night_range < day_range * 0.5


class TestDayNightEffectsStealthBonuses:
    @pytest.mark.parametrize("tod,expected_bonus", [
        (TimeOfDay.DAWN, 0.1),
        (TimeOfDay.DAY, 0.0),
        (TimeOfDay.DUSK, 0.2),
        (TimeOfDay.NIGHT, 0.5),
    ])
    def test_stealth_bonus_values(self, tod, expected_bonus):
        effects = DayNightEffects()
        base = 0.3
        result = effects.apply_stealth_bonus(base, tod)
        assert result == pytest.approx(base + expected_bonus, rel=1e-2)

    def test_stealth_capped_at_one(self):
        effects = DayNightEffects()
        result = effects.apply_stealth_bonus(0.8, TimeOfDay.NIGHT)
        assert result <= 1.0


class TestDayNightEffectsAccuracyModifiers:
    def test_night_reduces_accuracy(self):
        effects = DayNightEffects()
        day_acc = effects.apply_accuracy_modifier(0.9, TimeOfDay.DAY)
        night_acc = effects.apply_accuracy_modifier(0.9, TimeOfDay.NIGHT)
        assert night_acc < day_acc


class TestDayNightEffectsLightingColors:
    @pytest.mark.parametrize("tod,expected_rgb", [
        (TimeOfDay.DAWN, (255, 200, 150)),
        (TimeOfDay.DAY, (255, 255, 255)),
        (TimeOfDay.DUSK, (255, 180, 120)),
        (TimeOfDay.NIGHT, (80, 100, 140)),
    ])
    def test_lighting_color_values(self, tod, expected_rgb):
        effects = DayNightEffects()
        color = effects.get_lighting_color(tod)
        assert color == expected_rgb

    def test_dawn_is_warm_tone(self):
        effects = DayNightEffects()
        color = effects.get_lighting_color(TimeOfDay.DAWN)
        assert color[0] > 200
        assert color[1] > 150


class TestDayNightCombinedEffects:
    def test_combined_vision_weather_and_night(self):
        effects = DayNightEffects()
        base = 10.0
        combined = effects.get_combined_vision_modifier(
            base, TimeOfDay.NIGHT, weather_modifier=0.7
        )
        expected = base * 0.3 * 0.7
        assert combined == pytest.approx(expected, rel=1e-2)

    def test_combined_stealth_with_weather(self):
        effects = DayNightEffects()
        base = 0.2
        combined = effects.get_combined_stealth_bonus(
            base, TimeOfDay.NIGHT, weather_concealment=0.2
        )
        assert combined <= 1.0
        assert combined > base


class TestSearchlightInit:
    def test_default_init(self):
        sl = Searchlight(position_x=10, position_y=10)
        assert sl.position_x == 10
        assert sl.position_y == 10
        assert sl.arc_angle == 60.0
        assert sl.reveal_range == 15
        assert sl.is_active is True

    def test_custom_params(self):
        sl = Searchlight(
            position_x=5,
            position_y=5,
            direction_deg=45,
            arc_angle=90,
            reveal_range=20,
        )
        assert sl.direction_deg == 45
        assert sl.arc_angle == 90
        assert sl.reveal_range == 20


class TestSearchlightIllumination:
    def test_center_tile_illuminated(self):
        sl = Searchlight(position_x=10, position_y=10)
        assert sl.is_tile_illuminated(10, 10)

    def test_out_of_range_not_illuminated(self):
        sl = Searchlight(position_x=0, position_y=0, reveal_range=5)
        assert not sl.is_tile_illuminated(10, 10)

    def test_inactive_no_illumination(self):
        sl = Searchlight(position_x=5, position_y=5, is_active=False)
        assert not sl.is_tile_illuminated(5, 5)

    def test_illuminated_tiles_list_non_empty_when_active(self):
        sl = Searchlight(position_x=10, position_y=10)
        tiles = sl.get_illuminated_tiles()
        assert len(tiles) >= 1, f"Active searchlight should illuminate at least 1 tile (center), got {len(tiles)}"

    def test_illuminated_tiles_empty_when_inactive(self):
        sl = Searchlight(position_x=10, position_y=10, is_active=False)
        tiles = sl.get_illuminated_tiles()
        assert len(tiles) == 0


class TestSearchlightUpdate:
    def test_update_changes_direction(self):
        sl = Searchlight(position_x=0, position_y=0, sweep_speed=100)
        initial = sl.current_direction
        sl.update(0.1)
        assert sl.current_direction != initial

    def test_sweep_reverses_at_boundary(self):
        sl = Searchlight(
            position_x=0, position_y=0, sweep_speed=1000
        )
        sl.update(0.2)
        sign_after = sl._sweep_sign
        assert sign_after != 1 or sl._current_direction < 180


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
