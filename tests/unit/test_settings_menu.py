from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from pycc2.domain.interfaces.display_config import DisplayConfig
from pycc2.presentation.ui.settings_menu import (
    SettingsMenu,
    SettingsState,
    SettingsTab,
)


@pytest.fixture
def display_config():
    return DisplayConfig()


@pytest.fixture
def menu(display_config):
    return SettingsMenu(display_config)


def _make_key_event(key):
    import pygame

    ev = MagicMock()
    ev.type = pygame.KEYDOWN
    ev.key = key
    return ev


def _make_mouse_event(button=1):
    import pygame

    ev = MagicMock()
    ev.type = pygame.MOUSEBUTTONDOWN
    ev.button = button
    return ev


class TestSettingsStateDefaults:
    def test_master_volume_default(self):
        s = SettingsState()
        assert s.master_volume == 0.8

    def test_music_volume_default(self):
        s = SettingsState()
        assert s.music_volume == 0.6

    def test_sfx_volume_default(self):
        s = SettingsState()
        assert s.sfx_volume == 1.0

    def test_quality_preset_default(self):
        s = SettingsState()
        assert s.quality_preset == "HIGH"

    def test_show_fps_default_true(self):
        s = SettingsState()
        assert s.show_fps is True

    def test_show_debug_default_false(self):
        s = SettingsState()
        assert s.show_debug is False

    def test_screen_shake_default_true(self):
        s = SettingsState()
        assert s.screen_shake is True

    def test_particles_default_true(self):
        s = SettingsState()
        assert s.particles is True

    def test_damage_numbers_default_true(self):
        s = SettingsState()
        assert s.damage_numbers is True

    def test_difficulty_default_medium(self):
        s = SettingsState()
        assert s.difficulty == "MEDIUM"

    def test_autosave_interval_default_300(self):
        s = SettingsState()
        assert s.autosave_interval == 300


class TestVisibilityToggle:
    def test_initial_not_visible(self, menu):
        assert menu.visible is False

    def test_toggle_makes_visible(self, menu):
        menu.toggle()
        assert menu.visible is True

    def test_toggle_twice_returns_hidden(self, menu):
        menu.toggle()
        menu.toggle()
        assert menu.visible is False

    def test_show_sets_visible(self, menu):
        menu.show()
        assert menu.visible is True

    def test_hide_sets_hidden(self, menu):
        menu.show()
        menu.hide()
        assert menu.visible is False


class TestTabSwitching:
    def test_initial_tab_is_general(self, menu):
        assert menu._active_tab == SettingsTab.GENERAL

    def test_tab_switches_to_audio(self, menu):
        ev = _make_key_event(9)
        result = menu.handle_input(ev, (0, 0))
        assert result is None
        assert menu._active_tab == SettingsTab.AUDIO

    def test_tab_switches_to_controls(self, menu):
        menu.handle_input(_make_key_event(9), (0, 0))
        menu.handle_input(_make_key_event(9), (0, 0))
        assert menu._active_tab == SettingsTab.CONTROLS

    def test_tab_switches_to_gameplay(self, menu):
        for _ in range(3):
            menu.handle_input(_make_key_event(9), (0, 0))
        assert menu._active_tab == SettingsTab.GAMEPLAY

    def test_tab_wraps_around_back_to_general(self, menu):
        for _ in range(4):
            menu.handle_input(_make_key_event(9), (0, 0))
        assert menu._active_tab == SettingsTab.GENERAL


class TestHandleInput:
    def test_esc_closes_menu(self, menu):
        import pygame

        menu.show()
        ev = _make_key_event(pygame.K_ESCAPE)
        result = menu.handle_input(ev, (0, 0))
        assert result == "closed"
        assert menu.visible is False

    def test_esc_on_hidden_menu_stays_closed(self, menu):
        import pygame

        ev = _make_key_event(pygame.K_ESCAPE)
        result = menu.handle_input(ev, (0, 0))
        assert result == "closed"

    def test_up_arrow_adjusts_selection(self, menu):
        import pygame

        ev = _make_key_event(pygame.K_UP)
        result = menu.handle_input(ev, (0, 0))
        assert result is None

    def test_down_arrow_adjusts_selection(self, menu):
        import pygame

        ev = _make_key_event(pygame.K_DOWN)
        result = menu.handle_input(ev, (0, 0))
        assert result is None

    def test_w_key_same_as_up_arrow(self, menu):
        import pygame

        ev = _make_key_event(pygame.K_w)
        result = menu.handle_input(ev, (0, 0))
        assert result is None

    def test_s_key_same_as_down_arrow(self, menu):
        import pygame

        ev = _make_key_event(pygame.K_s)
        result = menu.handle_input(ev, (0, 0))
        assert result is None

    def test_return_toggles_option(self, menu):
        import pygame

        menu.show()
        ev = _make_key_event(pygame.K_RETURN)
        result = menu.handle_input(ev, (0, 0))
        assert result == "applied"

    def test_left_key_cycles_value(self, menu):
        import pygame

        ev = _make_key_event(pygame.K_LEFT)
        result = menu.handle_input(ev, (0, 0))
        assert result == "applied"

    def test_right_key_cycles_value(self, menu):
        import pygame

        ev = _make_key_event(pygame.K_RIGHT)
        result = menu.handle_input(ev, (0, 0))
        assert result == "applied"


class TestRender:
    def test_render_does_not_crash(self, menu):
        mock_pygame = MagicMock()
        mock_screen = MagicMock()
        mock_screen.get_size.return_value = (1024, 768)
        mock_pygame.Surface.return_value = MagicMock()
        mock_pygame.font.Font.return_value.render.return_value = MagicMock(get_width=lambda: 100)
        real_pygame = sys.modules.get("pygame")
        try:
            sys.modules["pygame"] = mock_pygame
            menu.show()
            menu.render(mock_screen)
            mock_pygame.Surface.assert_called()
        finally:
            if real_pygame:
                sys.modules["pygame"] = real_pygame

    def test_render_when_hidden_does_not_crash(self, menu):
        mock_pygame = MagicMock()
        mock_screen = MagicMock()
        mock_screen.get_size.return_value = (800, 600)
        real_pygame = sys.modules.get("pygame")
        try:
            sys.modules["pygame"] = mock_pygame
            menu.render(mock_screen)
        finally:
            if real_pygame:
                sys.modules["pygame"] = real_pygame

    def test_render_draws_title(self, menu):
        mock_pygame = MagicMock()
        mock_screen = MagicMock()
        mock_screen.get_size.return_value = (1024, 768)
        mock_font = MagicMock()
        mock_font.render.return_value = MagicMock(get_width=lambda: 120, get_height=lambda: 30)
        mock_pygame.font.Font.return_value = mock_font
        real_pygame = sys.modules.get("pygame")
        try:
            sys.modules["pygame"] = mock_pygame
            menu.show()
            menu.render(mock_screen)
            mock_font.render.assert_called()
        finally:
            if real_pygame:
                sys.modules["pygame"] = real_pygame


class TestOptionsPerTab:
    def test_general_tab_has_options(self, menu):
        options = menu._get_options_for_tab()
        assert len(options) >= 4
        names = [o[0] for o in options]
        assert "Quality Preset" in names
        assert "Show FPS Counter" in names

    def test_audio_tab_has_volume_options(self, menu):
        menu._active_tab = SettingsTab.AUDIO
        options = menu._get_options_for_tab()
        names = [o[0] for o in options]
        assert "Master Volume" in names
        assert "Music Volume" in names
        assert "SFX Volume" in names

    def test_controls_tab_has_info_options(self, menu):
        menu._active_tab = SettingsTab.CONTROLS
        options = menu._get_options_for_tab()
        assert len(options) >= 4
        types = [o[2] for o in options]
        assert all(t == "info" for t in types)

    def test_gameplay_tab_has_difficulty(self, menu):
        menu._active_tab = SettingsTab.GAMEPLAY
        options = menu._get_options_for_tab()
        names = [o[0] for o in options]
        assert "Difficulty" in names
        assert "Autosave interval" in names

    def test_all_four_tabs_produce_valid_options(self, menu):
        for tab in SettingsTab:
            menu._active_tab = tab
            options = menu._get_options_for_tab()
            assert isinstance(options, list)
            assert len(options) >= 1, f"Tab {tab} should have at least 1 option, got {len(options)}"
            for opt_name, opt_val, opt_type in options:
                assert isinstance(opt_name, str)
                assert opt_type in ("enum", "bool", "slider", "info", "toggle")


class TestBoolToggle:
    def test_toggle_fps_counter_flips_state(self, menu):
        original = menu.state.show_fps
        menu._toggle_option_at_index(1)
        assert menu.state.show_fps != original

    def test_toggle_screen_shake_flips_state(self, menu):
        original = menu.state.screen_shake
        menu._toggle_option_at_index(2)
        assert menu.state.screen_shake != original

    def test_toggle_particles_flips_state(self, menu):
        original = menu.state.particles
        menu._toggle_option_at_index(3)
        assert menu.state.particles != original

    def test_toggle_damage_numbers_flips_state(self, menu):
        original = menu.state.damage_numbers
        menu._toggle_option_at_index(4)
        assert menu.state.damage_numbers != original

    def test_double_toggle_returns_original(self, menu):
        original = menu.state.show_fps
        menu._toggle_option_at_index(1)
        menu._toggle_option_at_index(1)
        assert menu.state.show_fps == original


class TestApplyToSystems:
    def test_apply_with_sound_system_calls_set_master_volume(self, menu):
        mock_sound = MagicMock()
        changes = menu.apply_to_systems(sound_system=mock_sound)
        mock_sound.set_master_volume.assert_called_once_with(menu.state.master_volume)
        assert "volume" in changes

    def test_apply_without_sound_system_returns_empty(self, menu):
        changes = menu.apply_to_systems(sound_system=None)
        assert changes == {}

    def test_apply_with_no_args_returns_empty(self, menu):
        changes = menu.apply_to_systems()
        assert changes == {}


class TestFormatValue:
    def test_format_bool_true(self, menu):
        assert "ON" in menu._format_value(True, "bool")

    def test_format_bool_false(self, menu):
        assert "OFF" in menu._format_value(False, "bool")

    def test_format_non_bool_returns_str(self, menu):
        assert menu._format_value("HIGH", "enum") == "HIGH"


class TestSelectionIndex:
    def test_selection_starts_at_zero(self, menu):
        assert menu._selected_option_idx == 0

    def test_adjust_selection_down_increments_index(self, menu):
        menu._adjust_selection(1)
        assert menu._selected_option_idx == 1

    def test_adjust_selection_up_wraps_around(self, menu):
        menu._adjust_selection(-1)
        options = menu._get_options_for_tab()
        assert menu._selected_option_idx == len(options) - 1

    def test_adjust_selection_beyond_max_wraps(self, menu):
        options = menu._get_options_for_tab()
        for _ in range(len(options) + 5):
            menu._adjust_selection(1)
        assert 0 <= menu._selected_option_idx < len(options)


class TestCycleEnumValue:
    def test_cycle_quality_preset_forward(self, menu):
        original = menu.state.quality_preset
        menu._cycle_option_value(1)
        assert menu.state.quality_preset != original

    def test_cycle_quality_preset_backward(self, menu):
        presets = ["LOW", "MEDIUM", "HIGH", "ULTRA"]
        menu.state.quality_preset = "LOW"
        menu._cycle_option_value(-1)
        assert menu.state.quality_preset == "ULTRA"

    def test_cycle_difficulty_forward(self, menu):
        difficulties = ["EASY", "MEDIUM", "HARD", "VETERAN"]
        menu.state.difficulty = "EASY"
        menu._selected_option_idx = 0
        menu._active_tab = SettingsTab.GAMEPLAY
        menu._cycle_option_value(1)
        assert menu.state.difficulty == "MEDIUM"

    def test_cycle_difficulty_wraps_around(self, menu):
        menu.state.difficulty = "VETERAN"
        menu._selected_option_idx = 0
        menu._active_tab = SettingsTab.GAMEPLAY
        menu._cycle_option_value(1)
        assert menu.state.difficulty == "EASY"
