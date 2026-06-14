"""Tests for weather rendering and enhanced particle system."""

from unittest.mock import MagicMock, patch


class TestWeatherRendererInit:
    def test_weather_renderer_init(self):
        from pycc2.presentation.rendering.weather_system import WeatherRenderer

        renderer = WeatherRenderer(800, 600)

        assert renderer.screen_width == 800
        assert renderer.screen_height == 600
        assert len(renderer._rain_drops) == WeatherRenderer.RAIN_DROP_COUNT
        assert all("x" in drop and "y" in drop for drop in renderer._rain_drops)

    def test_rain_drop_properties(self):
        from pycc2.presentation.rendering.weather_system import WeatherRenderer

        renderer = WeatherRenderer(1024, 768)

        for drop in renderer._rain_drops:
            assert 0 <= drop["x"] <= renderer.screen_width
            assert -renderer.screen_height <= drop["y"] <= 0
            assert 8 <= drop["speed"] <= 15
            assert 8 <= drop["length"] <= 18
            assert 40 <= drop["alpha"] <= 100


class TestRainDropsUpdate:
    def test_rain_drops_update(self):
        from pycc2.presentation.rendering.weather_system import WeatherRenderer

        renderer = WeatherRenderer(800, 600)
        initial_positions = [(d["x"], d["y"]) for d in renderer._rain_drops]

        renderer.update()

        for i, drop in enumerate(renderer._rain_drops):
            # Y should increase (falling down)
            assert drop["y"] >= initial_positions[i][1]
            # X should increase slightly (wind drift)
            assert drop["x"] >= initial_positions[i][0]

    def test_rain_drops_recycle(self):
        from pycc2.presentation.rendering.weather_system import WeatherRenderer

        renderer = WeatherRenderer(100, 100)

        # Move all drops below screen
        for drop in renderer._rain_drops:
            drop["y"] = renderer.screen_height + 100

        renderer.update()

        # All drops should be recycled to top
        for drop in renderer._rain_drops:
            assert drop["y"] <= 50  # random.randint(-50, 0) range


class TestNightOverlayRenders:
    @patch("pygame.Surface")
    @patch("pygame.draw")
    def test_night_overlay_renders(self, mock_draw, mock_surface_cls):
        from pycc2.domain.systems.environment import TimeOfDay
        from pycc2.domain.systems.weather_effects import WeatherState, WeatherType
        from pycc2.presentation.rendering.weather_system import WeatherRenderer

        mock_screen = MagicMock()
        mock_surface = MagicMock()
        mock_surface_cls.return_value = mock_surface

        renderer = WeatherRenderer(800, 600)
        weather_state = WeatherState(weather_type=WeatherType.CLEAR)
        renderer.render(mock_screen, weather_state, TimeOfDay.NIGHT)

        mock_surface_cls.assert_called_with((800, 600), 65536)  # pygame.SRCALPHA = 65536
        mock_surface.fill.assert_called_once()
        args = mock_surface.fill.call_args[0][0]
        assert args[3] == WeatherRenderer.NIGHT_DARKEN_ALPHA  # alpha value

    @patch("pygame.Surface")
    @patch("pygame.draw")
    def test_dawn_dusk_lighter_overlay(self, mock_draw, mock_surface_cls):
        from pycc2.domain.systems.environment import TimeOfDay
        from pycc2.domain.systems.weather_effects import WeatherState, WeatherType
        from pycc2.presentation.rendering.weather_system import WeatherRenderer

        mock_screen = MagicMock()
        mock_surface = MagicMock()
        mock_surface_cls.return_value = mock_surface

        renderer = WeatherRenderer(800, 600)
        weather_state = WeatherState(weather_type=WeatherType.CLEAR)
        renderer.render(mock_screen, weather_state, TimeOfDay.DAWN)

        args = mock_surface.fill.call_args[0][0]
        assert args[3] == 70  # lighter alpha for twilight

    @patch("pygame.Surface")
    @patch("pygame.draw")
    def test_day_no_overlay(self, mock_draw, mock_surface_cls):
        from pycc2.domain.systems.environment import TimeOfDay
        from pycc2.domain.systems.weather_effects import WeatherState, WeatherType
        from pycc2.presentation.rendering.weather_system import WeatherRenderer

        mock_screen = MagicMock()
        mock_surface = MagicMock()
        mock_surface_cls.return_value = mock_surface

        renderer = WeatherRenderer(800, 600)
        weather_state = WeatherState(weather_type=WeatherType.CLEAR)
        renderer.render(mock_screen, weather_state, TimeOfDay.DAY)

        # No overlay should be created for day time
        assert not mock_surface.fill.called


class TestFogOverlayRenders:
    @patch("pygame.draw")
    @patch("pygame.Surface")
    def test_fog_overlay_renders(self, mock_surface_cls, mock_draw):
        from pycc2.domain.systems.environment import TimeOfDay
        from pycc2.domain.systems.weather_effects import WeatherState, WeatherType
        from pycc2.presentation.rendering.weather_system import WeatherRenderer

        mock_screen = MagicMock()
        mock_fog_surf = MagicMock()
        mock_surface_cls.return_value = mock_fog_surf

        renderer = WeatherRenderer(800, 600)
        weather_state = WeatherState(weather_type=WeatherType.FOG)
        renderer.render(mock_screen, weather_state, TimeOfDay.DAY)

        # Fog surface should be filled with base color
        fog_fill_args = mock_fog_surf.fill.call_args[0][0]
        assert fog_fill_args[3] == WeatherRenderer.FOG_ALPHA_BASE
        # Circles should be drawn for noise variation
        assert mock_draw.circle.call_count == 20


class TestParticlePresetsExist:
    def test_particle_presets_exist(self):
        from pycc2.presentation.rendering.animation_system import ParticleEmitter

        expected_presets = [
            "rifle_fire",
            "tank_explosion",
            "mortar_impact",
            "blood_hit",
            "muzzle_flash",
        ]

        for preset_name in expected_presets:
            assert preset_name in ParticleEmitter.PRESETS, f"Missing preset: {preset_name}"

    def test_preset_has_required_keys(self):
        from pycc2.presentation.rendering.animation_system import ParticleEmitter

        required_keys = {"count", "speed", "life", "size", "color", "spread", "gravity"}

        for name, preset in ParticleEmitter.PRESETS.items():
            missing = required_keys - set(preset.keys())
            assert not missing, f"Preset '{name}' missing keys: {missing}"


class TestEmitPresetCreatesParticles:
    def test_emit_preset_creates_particles(self):
        from pycc2.presentation.rendering.animation_system import ParticleEmitter

        emitter = ParticleEmitter()
        initial_count = len(emitter.particles)

        count = emitter.emit_preset("rifle_fire", 100, 200)

        assert count > 0
        assert len(emitter.particles) == initial_count + count

    def test_emit_preset_returns_correct_count(self):
        from pycc2.presentation.rendering.animation_system import ParticleEmitter

        emitter = ParticleEmitter()

        for preset_name, preset_config in ParticleEmitter.PRESETS.items():
            emitter.clear()
            count = emitter.emit_preset(preset_name, 0, 0)
            assert count == preset_config["count"], (
                f"{preset_name}: expected {preset_config['count']}, got {count}"
            )

    def test_emit_invalid_preset_returns_zero(self):
        from pycc2.presentation.rendering.animation_system import ParticleEmitter

        emitter = ParticleEmitter()
        initial_count = len(emitter.particles)

        count = emitter.emit_preset("nonexistent_preset", 0, 0)

        assert count == 0
        assert len(emitter.particles) == initial_count

    def test_emit_preset_uses_direction(self):
        import math

        from pycc2.presentation.rendering.animation_system import ParticleEmitter

        emitter = ParticleEmitter()
        emitter.emit_preset("rifle_fire", 100, 100, direction=math.pi / 4)  # 45 degrees

        # Particles should spread around the given direction
        assert len(emitter.particles) > 0
        for p in emitter.particles:
            # Check that velocity is non-zero (particle was emitted with direction)
            assert p.vx != 0 or p.vy != 0


class TestNewParticleTypesExist:
    def test_new_particle_types_defined(self):
        from pycc2.presentation.rendering.animation_system import ParticleEmitter

        new_types = {
            "EXPLOSION_LARGE",
            "EXPLOSION_AP",
            "BLOOD_SPLATTER",
            "DIRT_KICKUP",
            "MUZZLE_FLASH_BURST",
        }

        existing_types = {t.name for t in ParticleEmitter.ParticleType}

        for new_type in new_types:
            assert new_type in existing_types, f"Missing particle type: {new_type}"
