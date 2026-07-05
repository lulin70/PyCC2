"""Smoke tests for zero-coverage modules (TD-069).

Covers 9 files identified by D14 coverage audit as having 0% unit test coverage:
- main.py (P0 entry point — helper functions tested)
- font_helper.py (safe_init_font / safe_render_text)
- parsers/__init__.py (re-export integrity)
- unit_panel.py (UnitPanel show/hide/render)
- weather_visual_effects.py (EnhancedWeatherSystem rain/snow/fog)
- context_menu.py (ContextMenu show/hide/handle_event/get_enabled_actions)
- cc2_map_parser.py (CC2TerrainCode / CC2MapParser parse)
- cc2_combat_effects.py (CC2ExplosionEffect / EnhancedParticleSystem)

pixvoxel_loader.py is scripts-only (excluded — only used by scripts/validate_isometric.py).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pygame

# Ensure pygame initialized for headless rendering
pygame.init()
pygame.display.set_mode((1, 1))


# ---------------------------------------------------------------------------
# font_helper.py
# ---------------------------------------------------------------------------


class TestFontHelper:
    """Verify: font_helper.safe_init_font and safe_render_text APIs."""

    def test_safe_init_font_returns_font_happy(self):
        """Verify: safe_init_font returns a Font object with default args.

        Scenario: Call with default parameters
        Expected: Returns pygame.font.Font instance (not None)
        """
        from pycc2.presentation.ui.font_helper import safe_init_font

        font = safe_init_font()
        assert font is not None
        assert isinstance(font, pygame.font.Font)

    def test_safe_init_font_custom_size_bold(self):
        """Verify: safe_init_font respects size and bold parameters.

        Scenario: Call with size=32, bold=True
        Expected: Returns Font, get_height() reflects larger size
        """
        from pycc2.presentation.ui.font_helper import safe_init_font

        font_small = safe_init_font(size=12)
        font_large = safe_init_font(size=32, bold=True)
        assert font_small is not None and font_large is not None
        assert font_large.get_height() >= font_small.get_height()

    def test_safe_render_text_returns_surface(self):
        """Verify: safe_render_text renders text to a Surface.

        Scenario: Render a simple string with a valid font
        Expected: Returns Surface with non-zero dimensions
        """
        from pycc2.presentation.ui.font_helper import safe_init_font, safe_render_text

        font = safe_init_font(size=20)
        surface = safe_render_text(font, "Hello", color=(255, 255, 255))
        assert surface is not None
        assert surface.get_width() > 0
        assert surface.get_height() > 0

    def test_safe_render_text_none_font_returns_none(self):
        """Verify: safe_render_text returns None when font is None.

        Scenario: Pass None as font
        Expected: Returns None (graceful degradation)
        """
        from pycc2.presentation.ui.font_helper import safe_render_text

        assert safe_render_text(None, "text") is None


# ---------------------------------------------------------------------------
# parsers/__init__.py
# ---------------------------------------------------------------------------


class TestParsersInit:
    """Verify: parsers package re-exports public API."""

    def test_reexports_cc2_map_parser_symbols(self):
        """Verify: parsers package exports CC2MapParser, CC2TerrainCode, parse_cc2_map.

        Scenario: Import from pycc2.infrastructure.parsers
        Expected: All three symbols are accessible
        """
        from pycc2.infrastructure.parsers import (
            CC2MapParser,
            CC2TerrainCode,
            parse_cc2_map,
        )

        assert CC2MapParser is not None
        assert CC2TerrainCode is not None
        assert callable(parse_cc2_map)

    def test_all_list_complete(self):
        """Verify: __all__ lists all three exports.

        Scenario: Check __all__ attribute
        Expected: Contains exactly CC2MapParser, CC2TerrainCode, parse_cc2_map
        """
        from pycc2.infrastructure import parsers

        assert set(parsers.__all__) == {"CC2MapParser", "CC2TerrainCode", "parse_cc2_map"}


# ---------------------------------------------------------------------------
# cc2_map_parser.py
# ---------------------------------------------------------------------------


class TestCC2MapParser:
    """Verify: CC2TerrainCode enum and CC2MapParser parse logic."""

    def test_cc2_terrain_code_values(self):
        """Verify: CC2TerrainCode has documented CC2 terrain codes.

        Scenario: Check enum members match CC2 spec
        Expected: OPEN=0x00, ROAD=0x01, BRIDGE=0x0B, WALL=0x0C
        """
        from pycc2.infrastructure.parsers.cc2_map_parser import CC2TerrainCode

        assert CC2TerrainCode.OPEN == 0x00
        assert CC2TerrainCode.ROAD == 0x01
        assert CC2TerrainCode.BRIDGE == 0x0B
        assert CC2TerrainCode.WALL == 0x0C

    def test_cc2_terrain_code_to_terrain_type_mapping(self):
        """Verify: CC2_TO_PYCC2_MAP maps CC2 codes to PyCC2 TerrainType.

        Scenario: Look up OPEN and ROAD codes in the mapping table
        Expected: Returns corresponding TerrainType values
        """
        from pycc2.domain.value_objects.terrain_type import TerrainType
        from pycc2.infrastructure.parsers.cc2_map_parser import (
            CC2_TO_PYCC2_MAP,
            CC2TerrainCode,
        )

        assert CC2_TO_PYCC2_MAP[CC2TerrainCode.OPEN] == TerrainType.OPEN
        assert CC2_TO_PYCC2_MAP[CC2TerrainCode.ROAD] == TerrainType.ROAD
        assert CC2_TO_PYCC2_MAP[CC2TerrainCode.BRIDGE] == TerrainType.BRIDGE
        assert CC2_TO_PYCC2_MAP[CC2TerrainCode.WALL] == TerrainType.WALL

    def test_parse_cc2_map_flat_grid(self, tmp_path):
        """Verify: parse_cc2_map reads a flat byte grid and returns CC2MapData.

        Scenario: Write a 4x4 byte grid with known terrain codes
        Expected: CC2MapData.terrain_grid is a 2D list of TerrainType values
        """
        from pycc2.domain.value_objects.terrain_type import TerrainType
        from pycc2.infrastructure.parsers.cc2_map_parser import parse_cc2_map

        # 4x4 grid: OPEN, ROAD, BRIDGE, WALL per row (16 bytes = 4x4 square)
        data = bytes([0x00, 0x01, 0x0B, 0x0C] * 4)
        map_file = tmp_path / "test_map"
        map_file.write_bytes(data)

        map_data = parse_cc2_map(map_file, width=4, height=4)
        assert map_data.width == 4
        assert map_data.height == 4
        assert len(map_data.terrain_grid) == 4
        assert len(map_data.terrain_grid[0]) == 4
        assert map_data.terrain_grid[0][0] == TerrainType.OPEN.value
        assert map_data.terrain_grid[0][1] == TerrainType.ROAD.value
        assert map_data.terrain_grid[0][2] == TerrainType.BRIDGE.value
        assert map_data.terrain_grid[0][3] == TerrainType.WALL.value


# ---------------------------------------------------------------------------
# unit_panel.py
# ---------------------------------------------------------------------------


class TestUnitPanel:
    """Verify: UnitPanel show/hide/set_unit/render lifecycle."""

    def test_init_defaults(self):
        """Verify: UnitPanel initializes with default dimensions.

        Scenario: Construct with no args
        Expected: width/height > 0, not visible, is_visible False
        """
        from pycc2.presentation.rendering.unit_panel import UnitPanel

        panel = UnitPanel()
        assert panel.width > 0
        assert panel.height > 0
        assert panel.is_visible is False

    def test_show_hide_lifecycle(self):
        """Verify: show() sets visible, hide() clears visible.

        Scenario: Call show() then hide()
        Expected: is_visible True after show, False after hide
        """
        from pycc2.presentation.rendering.unit_panel import UnitPanel

        panel = UnitPanel()
        panel.show()
        assert panel.is_visible is True
        panel.hide()
        assert panel.is_visible is False

    def test_set_unit_shows_panel(self):
        """Verify: set_unit with a unit auto-shows the panel.

        Scenario: Call set_unit with a mock unit
        Expected: Panel becomes visible
        """
        from pycc2.presentation.rendering.unit_panel import UnitPanel

        panel = UnitPanel()
        panel.set_unit(MagicMock())
        assert panel.is_visible is True

    def test_set_unit_none_hides_panel(self):
        """Verify: set_unit(None) hides the panel.

        Scenario: Call set_unit(None) after showing
        Expected: Panel becomes hidden
        """
        from pycc2.presentation.rendering.unit_panel import UnitPanel

        panel = UnitPanel()
        panel.show()
        panel.set_unit(None)
        assert panel.is_visible is False

    def test_render_invisible_panel_noop(self):
        """Verify: render() on invisible panel is a no-op.

        Scenario: Call render on a hidden panel
        Expected: No exception, no drawing
        """
        from pycc2.presentation.rendering.unit_panel import UnitPanel

        panel = UnitPanel()
        surface = pygame.Surface((250, 220))
        # Should not raise even without initialize()
        panel.render(surface)


# ---------------------------------------------------------------------------
# weather_visual_effects.py
# ---------------------------------------------------------------------------


class TestWeatherVisualEffects:
    """Verify: EnhancedWeatherSystem rain/snow/fog lifecycle."""

    def test_init_defaults_clear(self):
        """Verify: EnhancedWeatherSystem starts CLEAR with no particles.

        Scenario: Construct with screen dimensions
        Expected: weather_type=CLEAR, particles empty
        """
        from pycc2.presentation.rendering.weather_visual_effects import (
            EnhancedWeatherSystem,
            WeatherType,
        )

        system = EnhancedWeatherSystem(800, 600)
        assert system.weather_type == WeatherType.CLEAR
        assert len(system.particles) == 0

    def test_set_weather_rain_creates_particles(self):
        """Verify: set_weather(RAIN) creates rain particles.

        Scenario: Set weather to RAIN with intensity 1.0
        Expected: particles list non-empty, weather_type=RAIN
        """
        from pycc2.presentation.rendering.weather_visual_effects import (
            EnhancedWeatherSystem,
            WeatherType,
        )

        system = EnhancedWeatherSystem(800, 600)
        system.set_weather(WeatherType.RAIN, intensity=1.0)
        assert system.weather_type == WeatherType.RAIN
        assert len(system.particles) > 0

    def test_set_weather_snow_creates_particles(self):
        """Verify: set_weather(SNOW) creates snow particles.

        Scenario: Set weather to SNOW
        Expected: particles list non-empty
        """
        from pycc2.presentation.rendering.weather_visual_effects import (
            EnhancedWeatherSystem,
            WeatherType,
        )

        system = EnhancedWeatherSystem(800, 600)
        system.set_weather(WeatherType.SNOW, intensity=1.0)
        assert len(system.particles) > 0

    def test_set_weather_fog_creates_surface(self):
        """Verify: set_weather(FOG) creates a fog surface.

        Scenario: Set weather to FOG
        Expected: fog_surface is not None, fog_alpha > 0
        """
        from pycc2.presentation.rendering.weather_visual_effects import (
            EnhancedWeatherSystem,
            WeatherType,
        )

        system = EnhancedWeatherSystem(800, 600)
        system.set_weather(WeatherType.FOG, intensity=1.0)
        assert system.fog_surface is not None
        assert system.fog_alpha > 0

    def test_update_advances_rain_particles(self):
        """Verify: update() moves rain particles downward.

        Scenario: Set RAIN, record y positions, update, compare
        Expected: At least one particle y increased
        """
        from pycc2.presentation.rendering.weather_visual_effects import (
            EnhancedWeatherSystem,
            WeatherType,
        )

        system = EnhancedWeatherSystem(800, 600)
        system.set_weather(WeatherType.RAIN, intensity=0.5)
        initial_ys = [p.y for p in system.particles]
        system.update()
        moved = any(p.y > initial_ys[i] for i, p in enumerate(system.particles))
        assert moved

    def test_render_rain_no_exception(self):
        """Verify: render() with RAIN draws without error.

        Scenario: Set RAIN, render to a surface
        Expected: No exception raised
        """
        from pycc2.presentation.rendering.weather_visual_effects import (
            EnhancedWeatherSystem,
            WeatherType,
        )

        system = EnhancedWeatherSystem(800, 600)
        system.set_weather(WeatherType.RAIN, intensity=0.3)
        surface = pygame.Surface((800, 600))
        system.render(surface)

    def test_intensity_clamped(self):
        """Verify: intensity is clamped to [0.0, 1.0].

        Scenario: Set intensity to 2.0 (above max)
        Expected: intensity clamped to 1.0
        """
        from pycc2.presentation.rendering.weather_visual_effects import (
            EnhancedWeatherSystem,
            WeatherType,
        )

        system = EnhancedWeatherSystem(800, 600)
        system.set_weather(WeatherType.RAIN, intensity=2.0)
        assert system.intensity == 1.0


# ---------------------------------------------------------------------------
# context_menu.py
# ---------------------------------------------------------------------------


class TestContextMenu:
    """Verify: ContextMenu show/hide/handle_event lifecycle."""

    def test_init_hidden(self):
        """Verify: ContextMenu starts hidden with 7 default items.

        Scenario: Construct ContextMenu
        Expected: visible=False, 7 items (Move/Attack/Defend/Smoke/Hide/Sneak/Cancel)
        """
        from pycc2.presentation.ui.context_menu import ContextMenu

        menu = ContextMenu()
        assert menu.visible is False
        assert len(menu._items) == 7

    def test_show_sets_visible(self):
        """Verify: show() makes menu visible and builds surface.

        Scenario: Call show() with position and callback
        Expected: visible=True, surface built
        """
        from pycc2.presentation.ui.context_menu import ContextMenu

        menu = ContextMenu()
        menu.show((100, 100), lambda action, pos: None)
        assert menu.visible is True
        assert menu._surface is not None

    def test_hide_clears_visible(self):
        """Verify: hide() hides the menu.

        Scenario: Show then hide
        Expected: visible=False
        """
        from pycc2.presentation.ui.context_menu import ContextMenu

        menu = ContextMenu()
        menu.show((100, 100), lambda action, pos: None)
        menu.hide()
        assert menu.visible is False

    def test_handle_event_when_hidden_returns_false(self):
        """Verify: handle_event returns False when menu is hidden.

        Scenario: Send event to hidden menu
        Expected: Returns False (event not consumed)
        """
        from pycc2.presentation.ui.context_menu import ContextMenu

        menu = ContextMenu()
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (0, 0), "button": 1})
        assert menu.handle_event(event) is False

    def test_right_click_hides_menu(self):
        """Verify: right-click (button=3) hides the menu.

        Scenario: Show menu, send right-click
        Expected: visible=False, returns True (consumed)
        """
        from pycc2.presentation.ui.context_menu import ContextMenu

        menu = ContextMenu()
        menu.show((100, 100), lambda action, pos: None)
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (100, 100), "button": 3})
        result = menu.handle_event(event)
        assert result is True
        assert menu.visible is False

    def test_escape_key_hides_menu(self):
        """Verify: ESC key hides the menu.

        Scenario: Show menu, send KEYDOWN ESC
        Expected: visible=False, returns True
        """
        from pycc2.presentation.ui.context_menu import ContextMenu

        menu = ContextMenu()
        menu.show((100, 100), lambda action, pos: None)
        event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
        result = menu.handle_event(event)
        assert result is True
        assert menu.visible is False

    def test_get_enabled_actions_no_unit(self):
        """Verify: get_enabled_actions with no unit returns DEFEND+CANCEL.

        Scenario: Call get_enabled_actions(unit=None)
        Expected: Returns {DEFEND, CANCEL}
        """
        from pycc2.presentation.ui.context_menu import ContextAction, ContextMenu

        menu = ContextMenu()
        actions = menu.get_enabled_actions(unit=None)
        assert ContextAction.DEFEND in actions
        assert ContextAction.CANCEL in actions
        assert ContextAction.MOVE not in actions

    def test_get_enabled_actions_with_unit(self):
        """Verify: get_enabled_actions with a unit adds MOVE+ATTACK.

        Scenario: Call get_enabled_actions with a mock unit
        Expected: Returns {DEFEND, CANCEL, MOVE, ATTACK}
        """
        from pycc2.presentation.ui.context_menu import ContextAction, ContextMenu

        menu = ContextMenu()
        actions = menu.get_enabled_actions(unit=MagicMock())
        assert ContextAction.MOVE in actions
        assert ContextAction.ATTACK in actions
        assert ContextAction.DEFEND in actions
        assert ContextAction.CANCEL in actions

    def test_show_with_enabled_actions_subset(self):
        """Verify: show() with enabled_actions disables others.

        Scenario: Show with only {MOVE, CANCEL} enabled
        Expected: MOVE item enabled, ATTACK item disabled
        """
        from pycc2.presentation.ui.context_menu import ContextAction, ContextMenu

        menu = ContextMenu()
        menu.show(
            (100, 100),
            lambda action, pos: None,
            enabled_actions={ContextAction.MOVE, ContextAction.CANCEL},
        )
        move_item = next(i for i in menu._items if i.action == ContextAction.MOVE)
        attack_item = next(i for i in menu._items if i.action == ContextAction.ATTACK)
        assert move_item.enabled is True
        assert attack_item.enabled is False


# ---------------------------------------------------------------------------
# cc2_combat_effects.py
# ---------------------------------------------------------------------------


class TestCC2CombatEffects:
    """Verify: CC2ExplosionEffect and EnhancedParticleSystem creation."""

    def test_enhanced_particle_system_init(self):
        """Verify: EnhancedParticleSystem initializes with empty particles list.

        Scenario: Construct with no args
        Expected: particles list empty
        """
        from pycc2.presentation.rendering.cc2_combat_effects import (
            EnhancedParticleSystem,
        )

        system = EnhancedParticleSystem()
        assert len(system.particles) == 0

    def test_cc2_explosion_effect_init(self):
        """Verify: CC2ExplosionEffect initializes with x,y coordinates.

        Scenario: Construct with x=100, y=200
        Expected: No exception, coordinates set, alive True
        """
        from pycc2.presentation.rendering.cc2_combat_effects import (
            CC2ExplosionEffect,
        )

        explosion = CC2ExplosionEffect(x=100.0, y=200.0)
        assert explosion.x == 100.0
        assert explosion.y == 200.0
        assert explosion.alive is True

    def test_enhanced_particle_system_update_empty(self):
        """Verify: update() on empty system is a no-op.

        Scenario: Call update with no particles
        Expected: No exception, particles still empty
        """
        from pycc2.presentation.rendering.cc2_combat_effects import (
            EnhancedParticleSystem,
        )

        system = EnhancedParticleSystem()
        system.update()
        assert len(system.particles) == 0


# ---------------------------------------------------------------------------
# main.py (P0 entry point — helper functions)
# ---------------------------------------------------------------------------


class TestMainHelpers:
    """Verify: main.py helper functions _resolve_map_path and _show_main_menu."""

    def test_resolve_map_path_existing(self, tmp_path, monkeypatch):
        """Verify: _resolve_map_path returns path when file exists.

        Scenario: Create a map file, call _resolve_map_path
        Expected: Returns the path
        """
        from pycc2 import main as main_module

        # Create a fake maps directory
        maps_dir = tmp_path / "maps"
        maps_dir.mkdir()
        map_file = maps_dir / "test_map.json"
        map_file.write_text("{}")

        # Monkeypatch the Path to use tmp_path
        def fake_path(p):
            if p == "data/maps/test_map.json":
                return map_file
            return Path(p)

        # Direct test: _resolve_map_path uses Path(f"data/maps/{map_stem}.json")
        # We monkeypatch pathlib.Path to redirect
        original_path = Path

        class FakePath(original_path):
            def __init__(self, *args, **kwargs):
                if args and str(args[0]) == "data/maps/test_map.json":
                    self._real = map_file
                else:
                    self._real = None
                super().__init__(*args, **kwargs)

            def exists(self):
                if hasattr(self, "_real") and self._real:
                    return self._real.exists()
                return original_path(self).exists()

        # Simpler approach: just test the logic with a real file
        monkeypatch.chdir(tmp_path)
        maps_dir2 = tmp_path / "data" / "maps"
        maps_dir2.mkdir(parents=True)
        (maps_dir2 / "test_map.json").write_text("{}")

        result = main_module._resolve_map_path("test_map")
        assert result is not None
        assert result.exists()

    def test_resolve_map_path_fallback_first_available(self, tmp_path, monkeypatch):
        """Verify: _resolve_map_path falls back to first available map.

        Scenario: Request non-existent map, but other maps exist
        Expected: Returns first available map path
        """
        from pycc2 import main as main_module

        monkeypatch.chdir(tmp_path)
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "arnhem.json").write_text("{}")

        result = main_module._resolve_map_path("nonexistent_map")
        assert result is not None
        assert result.stem == "arnhem"

    def test_resolve_map_path_no_maps_returns_none(self, tmp_path, monkeypatch):
        """Verify: _resolve_map_path returns None when no maps found.

        Scenario: Request map in empty maps directory
        Expected: Returns None
        """
        from pycc2 import main as main_module

        monkeypatch.chdir(tmp_path)
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)

        result = main_module._resolve_map_path("nonexistent_map")
        assert result is None

    def test_run_game_loop_returns_exit_code(self):
        """Verify: _run_game_loop returns game_loop.run() result.

        Scenario: Call _run_game_loop with a mock game_loop
        Expected: Returns the exit code from run()
        """
        from pycc2 import main as main_module

        mock_loop = MagicMock()
        mock_loop.run.return_value = 0
        result = main_module._run_game_loop(mock_loop)
        assert result == 0

    def test_run_game_loop_handles_crash(self):
        """Verify: _run_game_loop returns 1 on RuntimeError.

        Scenario: game_loop.run() raises RuntimeError
        Expected: Returns 1 (crash exit code)
        """
        from pycc2 import main as main_module

        mock_loop = MagicMock()
        mock_loop.run.side_effect = RuntimeError("crash")
        result = main_module._run_game_loop(mock_loop)
        assert result == 1
