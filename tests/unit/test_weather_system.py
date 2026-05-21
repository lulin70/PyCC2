import pytest
from pycc2.presentation.rendering.weather_system import WeatherRenderer
from pycc2.domain.systems.environment import WeatherCondition, TimeOfDay


class TestWeatherRendererRain:
    def test_rain_drops_count(self):
        wr = WeatherRenderer(800, 600)
        assert len(wr._rain_drops) == WeatherRenderer.RAIN_DROP_COUNT

    def test_update_moves_drops(self):
        wr = WeatherRenderer(800, 600)
        initial_positions = [(d["x"], d["y"]) for d in wr._rain_drops]
        wr.update()
        for i, drop in enumerate(wr._rain_drops):
            assert drop["y"] != initial_positions[i][1] or drop["x"] != initial_positions[i][0]


class TestWeatherRendererNightOverlay:
    def test_night_overlay_alpha(self):
        wr = WeatherRenderer(800, 600)
        assert wr.NIGHT_DARKEN_ALPHA == 140


class TestWeatherRendererFog:
    def test_fog_overlay_base_alpha(self):
        wr = WeatherRenderer(800, 600)
        assert wr.FOG_ALPHA_BASE == 100


class TestWeatherRendererDayNoEffect:
    def test_day_no_effect(self):
        wr = WeatherRenderer(800, 600)
        assert wr.screen_width == 800
        assert wr.screen_height == 600
