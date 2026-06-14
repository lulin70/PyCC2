import pygame
from pycc2.presentation.rendering.weather_system import WeatherSystem


class TestWeatherSystemInit:
    def test_default_mode_is_clear(self):
        ws = WeatherSystem()
        assert ws.mode == "clear"

    def test_default_alpha_is_zero(self):
        ws = WeatherSystem()
        assert ws._alpha == 0.0

    def test_default_screen_size(self):
        ws = WeatherSystem()
        assert ws._screen_size == (800, 600)


class TestWeatherSystemSetMode:
    def test_set_dust_mode_creates_particles(self):
        ws = WeatherSystem()
        ws.set_mode("dust")
        assert ws.mode == "dust"
        assert len(ws._particles) > 0

    def test_set_smoke_mode_creates_particles(self):
        ws = WeatherSystem()
        ws.set_mode("smoke")
        assert ws.mode == "smoke"
        assert len(ws._particles) > 0

    def test_set_light_fog_sets_alpha(self):
        ws = WeatherSystem()
        ws.set_mode("light_fog")
        assert ws.mode == "light_fog"
        assert ws._alpha > 0

    def test_set_clear_resets_state(self):
        ws = WeatherSystem()
        ws.set_mode("dust")
        ws.set_mode("clear")
        assert ws.mode == "clear"
        assert ws._alpha == 0.0
        assert len(ws._particles) == 0

    def test_invalid_mode_warns_and_ignores(self):
        ws = WeatherSystem()
        ws.set_mode("invalid_mode")
        assert ws.mode == "clear"


class TestWeatherSystemUpdate:
    def test_update_dust_moves_particles(self):
        ws = WeatherSystem()
        ws.set_mode("dust")
        initial = list(ws._particles)
        ws.update(0.1)
        # particles should have moved
        moved = any(
            ws._particles[i][0] != initial[i][0] or ws._particles[i][1] != initial[i][1]
            for i in range(len(ws._particles))
        )
        assert moved

    def test_update_clear_does_nothing(self):
        ws = WeatherSystem()
        ws.update(0.1)
        assert ws.mode == "clear"


class TestWeatherSystemScreenSize:
    def test_update_screen_size(self):
        ws = WeatherSystem()
        ws.update_screen_size(1024, 768)
        assert ws._screen_size == (1024, 768)


class TestWeatherSystemRender:
    def test_render_clear_does_not_crash(self):
        ws = WeatherSystem()
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        ws.render(surf)  # should not raise

    def test_render_light_fog_does_not_crash(self):
        ws = WeatherSystem()
        ws.set_mode("light_fog")
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        ws.render(surf)  # should not raise
