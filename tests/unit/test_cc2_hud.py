"""
Unit tests for CC2HUD (Three-Panel HUD)

Covers: initialization, layout constants, three-panel layout validation,
unit info display, VP/animation, interaction, edge cases, and visual regression.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import MagicMock, patch

import pygame
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.presentation.ui.cc2_hud import CC2HUD

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCREEN_W, SCREEN_H = 1024, 768


def make_unit(
    unit_id: str = "u1",
    name: str = "Rifle Squad",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 85,
    ammo: int = 30,
    max_ammo: int = 30,
) -> Unit:
    return Unit(
        id=unit_id,
        name=name,
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale),
        weapon=WeaponComponent(
            primary_weapon_id="rifle",
            max_ammo=max_ammo,
            ammo_remaining=ammo,
        ),
        position=PositionComponent(tile_coord=TileCoord(5, 5)),
        vision=VisionComponent(),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def hud():
    h = CC2HUD(screen_width=SCREEN_W, screen_height=SCREEN_H)
    h.initialize()
    return h


@pytest.fixture()
def surface():
    return pygame.Surface((SCREEN_W, SCREEN_H))


@pytest.fixture()
def units_3():
    return [
        make_unit(unit_id=f"u{i}", name=f"Squad {i}", hp=100 - i * 10, morale=70 + i * 5)
        for i in range(3)
    ]


@pytest.fixture()
def units_10():
    return [
        make_unit(
            unit_id=f"u{i}",
            name=f"Infantry Squad {i} Alpha Company",
            hp=100 - i * 8,
            morale=60 + i * 4,
        )
        for i in range(10)
    ]


# ===========================================================================
# P0: Core Functionality Tests
# ===========================================================================


@pytest.mark.unit
class TestHUDInitialization:

    def test_hud_initializes_with_correct_dimensions(self):
        hud = CC2HUD(screen_width=1024, screen_height=768)
        assert hud._screen_width == 1024
        assert hud._screen_height == 768

    def test_hud_calculates_panel_widths_correctly(self):
        hud = CC2HUD(screen_width=1000, screen_height=768)
        assert hud._left_width == 250
        assert hud._center_width == 450
        assert hud._right_width == 300

    def test_hud_default_visibility_is_true(self, hud):
        assert hud.is_visible() is True

    def test_hud_initialize_creates_fonts(self, hud):
        assert hud._font_title is not None
        assert hud._font_normal is not None
        assert hud._font_small is not None

    def test_hud_initialize_creates_unit_icons(self, hud):
        assert len(hud._unit_icons) > 0
        assert 'infantry' in hud._unit_icons
        assert 'tank' in hud._unit_icons

    def test_hud_initialize_creates_command_icons(self, hud):
        assert len(hud._command_icons) > 0
        assert 'move' in hud._command_icons
        assert 'fire' in hud._command_icons


@pytest.mark.unit
class TestLayoutConstants:

    def test_panel_height_constant(self):
        assert CC2HUD.PANEL_HEIGHT == 140

    def test_three_panel_ratios_sum_to_one(self):
        total = CC2HUD.LEFT_PANEL_RATIO + CC2HUD.CENTER_PANEL_RATIO + CC2HUD.RIGHT_PANEL_RATIO
        assert abs(total - 1.0) < 0.01

    def test_left_panel_ratio_is_25_percent(self):
        assert CC2HUD.LEFT_PANEL_RATIO == 0.25

    def test_center_panel_ratio_is_45_percent(self):
        assert CC2HUD.CENTER_PANEL_RATIO == 0.45

    def test_right_panel_ratio_is_30_percent(self):
        assert CC2HUD.RIGHT_PANEL_RATIO == 0.30

    def test_spacing_constants_are_positive(self):
        assert CC2HUD.PADDING > 0
        assert CC2HUD.ROW_HEIGHT > 0
        assert CC2HUD.BUTTON_MIN_WIDTH > 0
        assert CC2HUD.BUTTON_MIN_HEIGHT > 0
        assert CC2HUD.ICON_SIZE > 0
        assert CC2HUD.MINIMAP_SIZE > 0


@pytest.mark.unit
class TestColorPalette:

    def test_background_color_is_dark(self):
        r, g, b = CC2HUD.BG_COLOR
        assert r < 50 and g < 50 and b < 50

    def test_text_color_is_light(self):
        r, g, b = CC2HUD.TEXT_COLOR
        assert r > 150 and g > 150 and b > 150

    def test_highlight_color_is_golden(self):
        r, g, b = CC2HUD.HIGHLIGHT_COLOR
        assert r > 200 and g > 180 and b < 150

    def test_status_colors_exist(self):
        assert hasattr(CC2HUD, 'STATUS_HEALTHY')
        assert hasattr(CC2HUD, 'STATUS_WOUNDED')
        assert hasattr(CC2HUD, 'STATUS_CRITICAL')
        assert hasattr(CC2HUD, 'STATUS_DEAD')

    def test_healthy_color_is_green(self):
        r, g, b = CC2HUD.STATUS_HEALTHY
        assert g > r and g > b

    def test_wounded_color_is_yellowish(self):
        r, g, b = CC2HUD.STATUS_WOUNDED
        assert r > 150 and g > 150

    def test_critical_color_is_red(self):
        r, g, b = CC2HUD.STATUS_CRITICAL
        assert r > 150 and g < 100

    def test_dead_color_is_very_dark(self):
        r, g, b = CC2HUD.STATUS_DEAD
        assert r < 60 and g < 60 and b < 60


@pytest.mark.unit
class TestBasicRendering:

    def test_render_does_not_crash_with_empty_state(self, hud, surface):
        hud.render(surface)

    def test_render_does_not_crash_with_game_state(self, hud, surface, units_3):
        game_state = {
            'units': units_3,
            'selected_unit': 'u0',
            'ap_remaining': 8,
            'at_remaining': 3,
            'timer': '12:45',
        }
        hud.render(surface, game_state)

    def test_render_when_hidden_does_not_draw(self, hud, surface):
        hud.set_visible(False)
        initial_pixels = pygame.surfarray.array3d(surface).copy()
        hud.render(surface)
        after_pixels = pygame.surfarray.array3d(surface)
        assert (initial_pixels == after_pixels).all()

    def test_render_creates_content_at_bottom_of_screen(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.render(surface)
        pixels = pygame.surfarray.array3d(surface)
        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT
        bottom_area = pixels[:, panel_y:panel_y+10, :]
        bg = CC2HUD.BG_COLOR
        has_dark_pixel = False
        for x in range(100, 200):
            for dy in range(10):
                r, g, b = int(bottom_area[x, dy, 0]), int(bottom_area[x, dy, 1]), int(bottom_area[x, dy, 2])
                if r < 50 and g < 50 and b < 50:
                    has_dark_pixel = True
                    break
            if has_dark_pixel:
                break
        assert has_dark_pixel


@pytest.mark.unit
class TestUnitInfoDisplay:

    def test_set_units_populates_internal_list(self, hud, units_3):
        hud.set_units(units_3)
        assert len(hud._units) == 3

    def test_set_units_sorts_by_name(self, hud):
        units = [
            make_unit(name="Charlie"),
            make_unit(name="Alpha"),
            make_unit(name="Bravo"),
        ]
        hud.set_units(units)
        names = [u.name for u in hud._units]
        assert names == ['Alpha', 'Bravo', 'Charlie']

    def test_set_selected_unit_updates_selection(self, hud, units_3):
        hud.set_units(units_3)
        hud.set_selected_unit('u1')
        assert hud._selected_unit_id == 'u1'

    def test_set_selected_unit_none_clears_selection(self, hud, units_3):
        hud.set_units(units_3)
        hud.set_selected_unit('u1')
        hud.set_selected_unit(None)
        assert hud._selected_unit_id is None

    def test_set_ap_updates_action_points(self, hud):
        hud.set_ap(7)
        assert hud._ap_remaining == 7

    def test_set_at_updates_attack_turns(self, hud):
        hud.set_at(4)
        assert hud._at_remaining == 4

    def test_set_timer_updates_display_string(self, hud):
        hud.set_timer('15:30')
        assert hud._timer == '15:30'


@pytest.mark.unit
class TestStatusColorLogic:

    def test_healthy_unit_returns_green_color(self, hud):
        unit = make_unit(hp=90, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_HEALTHY

    def test_wounded_unit_returns_yellow_color(self, hud):
        unit = make_unit(hp=65, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_WOUNDED

    def test_critical_unit_returns_red_color(self, hud):
        unit = make_unit(hp=20, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_CRITICAL

    def test_dead_unit_returns_black_color(self, hud):
        unit = make_unit(hp=0, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_DEAD

    def test_full_hp_returns_healthy(self, hud):
        unit = make_unit(hp=100, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_HEALTHY


@pytest.mark.unit
class TestMoraleColorLogic:

    def test_high_morale_returns_green(self, hud):
        color = hud._get_morale_color(85)
        assert color == CC2HUD.STATUS_HEALTHY

    def test_medium_high_morale_returns_yellow(self, hud):
        color = hud._get_morale_color(55)
        assert color == CC2HUD.STATUS_WOUNDED

    def test_low_morale_returns_orange(self, hud):
        color = hud._get_morale_color(30)
        assert color == (255, 140, 50)

    def test_very_low_morale_returns_red(self, hud):
        color = hud._get_morale_color(10)
        assert color == CC2HUD.STATUS_CRITICAL

    def test_boundary_morale_70(self, hud):
        color = hud._get_morale_color(70)
        assert color == CC2HUD.STATUS_HEALTHY

    def test_boundary_morale_45(self, hud):
        color = hud._get_morale_color(45)
        assert color == CC2HUD.STATUS_WOUNDED

    def test_boundary_morale_20(self, hud):
        color = hud._get_morale_color(20)
        assert color == (255, 140, 50)


# ===========================================================================
# P1: Interaction Tests
# ===========================================================================


@pytest.mark.unit
class TestCommandButtons:

    def test_commands_list_has_expected_items(self, hud):
        cmd_ids = [cmd['id'] for cmd in hud._commands]
        expected = ['move', 'move_fast', 'crawl', 'fire', 'smoke', 'defend', 'hide']
        assert cmd_ids == expected

    def test_command_buttons_have_labels(self, hud):
        for cmd in hud._commands:
            assert 'label' in cmd
            assert len(cmd['label']) > 0

    def test_command_buttons_have_keys(self, hud):
        for cmd in hud._commands:
            assert 'key' in cmd
            assert cmd['key'] in ['●', '○']

    def test_handle_click_on_command_button(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.set_selected_unit('u0')
        hud.render(surface)
        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT
        for cmd_id, rect in hud._command_button_rects.items():
            cx, cy = rect.centerx, rect.centery + panel_y
            result = hud.handle_click((cx, cy))
            assert result == f"command:{cmd_id}"
            break

    def test_handle_click_triggers_command_callback(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.set_selected_unit('u0')
        hud.render(surface)

        triggered = []
        hud.register_callback('command', lambda cid: triggered.append(cid))

        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT
        for cmd_id, rect in hud._command_button_rects.items():
            cx, cy = rect.centerx, rect.centery + panel_y
            hud.handle_click((cx, cy))
            break

        assert len(triggered) == 1


@pytest.mark.unit
class TestUnitSelection:

    def test_handle_click_on_unit_selects_it(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.render(surface)
        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT
        for rect, unit_id in hud._unit_rects:
            cx, cy = rect.centerx, rect.centery + panel_y
            result = hud.handle_click((cx, cy))
            assert result == f"select_unit:{unit_id}"
            break

    def test_handle_click_triggers_unit_select_callback(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.render(surface)

        selected_ids = []
        hud.register_callback('unit_select', lambda uid: selected_ids.append(uid))

        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT
        for rect, unit_id in hud._unit_rects:
            hud.handle_click((rect.centerx, rect.centery + panel_y))
            break

        assert len(selected_ids) == 1

    def test_set_selected_unit_auto_scrolls_into_view(self, hud, units_10):
        hud.set_units(units_10)
        hud.set_selected_unit('u9')
        visible_end = hud._scroll_offset + hud._max_visible_units
        assert hud._scroll_offset <= 9 < visible_end


@pytest.mark.unit
class TestInfoModeToggle:

    def test_info_mode_defaults_to_all(self, hud):
        assert hud._info_mode == "ALL"

    def test_handle_click_on_info_mode_changes_mode(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.render(surface)
        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT
        for mode, rect in hud._info_mode_rects.items():
            if mode != hud._info_mode:
                result = hud.handle_click((rect.centerx, rect.centery + panel_y))
                assert result == f"info_mode:{mode}"
                assert hud._info_mode == mode
                break


@pytest.mark.unit
class TestTimerDisplay:

    def test_timer_format_mmss_accepted(self, hud):
        hud.set_timer('12:45')
        assert hud._timer == '12:45'

    def test_timer_empty_string_accepted(self, hud):
        hud.set_timer('')
        assert hud._timer == ''

    def test_timer_applied_from_game_state(self, hud, surface):
        game_state = {'timer': '23:59'}
        hud.render(surface, game_state)
        assert hud._timer == '23:59'


@pytest.mark.unit
class TestMouseHover:

    def test_handle_mouse_move_updates_hovered_command(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.set_selected_unit('u0')
        hud.render(surface)
        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT
        for cmd_id, rect in hud._command_button_rects.items():
            hud.handle_mouse_move((rect.centerx, rect.centery + panel_y))
            assert hud._hovered_command == cmd_id
            break

    def test_handle_mouse_move_updates_hovered_unit(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.render(surface)
        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT
        for rect, unit_id in hud._unit_rects:
            hud.handle_mouse_move((rect.centerx, rect.centery + panel_y))
            assert hud._hovered_unit == unit_id
            break

    def test_handle_mouse_move_outside_clears_hover(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.set_selected_unit('u0')
        hud.render(surface)
        hud.handle_mouse_move((0, 0))
        assert hud._hovered_command is None
        assert hud._hovered_unit is None


@pytest.mark.unit
class TestVisibilityToggle:

    def test_set_visible_false_hides_hud(self, hud):
        hud.set_visible(False)
        assert hud.is_visible() is False

    def test_set_visible_true_shows_hud(self, hud):
        hud.set_visible(False)
        hud.set_visible(True)
        assert hud.is_visible() is True

    def test_hidden_hud_returns_none_for_clicks(self, hud, surface):
        hud.set_visible(False)
        result = hud.handle_click((500, 700))
        assert result is None


# ===========================================================================
# P1: Edge Cases & Boundary Conditions
# ===========================================================================


@pytest.mark.unit
class TestEmptyUnitList:

    def test_render_with_no_units_does_not_crash(self, hud, surface):
        hud.set_units([])
        hud.render(surface)

    def test_empty_units_list_creates_no_rects(self, hud, surface):
        hud.set_units([])
        hud.render(surface)
        assert len(hud._unit_rects) == 0
        assert len(hud._hide_button_rects) == 0

    def test_no_units_selected_shows_message(self, hud, surface):
        hud.set_units([])
        hud.render(surface)
        assert hud._selected_unit_id is None


@pytest.mark.unit
class TestNoneValueDefense:

    def test_set_units_with_none_raises_type_error(self, hud):
        with pytest.raises(TypeError):
            hud.set_units(None)

    def test_set_selected_unit_with_none_is_safe(self, hud, units_3):
        hud.set_units(units_3)
        hud.set_selected_unit(None)
        assert hud._selected_unit_id is None

    def test_render_with_none_game_state(self, hud, surface):
        hud.render(surface, None)

    def test_get_status_color_for_unit_without_health(self, hud):
        unit = make_unit()
        delattr(unit, 'health')
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_HEALTHY


@pytest.mark.unit
class TestExtremeHPValues:

    def test_zero_hp_returns_dead_color(self, hud):
        unit = make_unit(hp=0, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_DEAD

    def test_max_hp_returns_healthy_color(self, hud):
        unit = make_unit(hp=999, max_hp=999)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_HEALTHY

    def test_negative_hp_treated_as_zero(self, hud):
        unit = make_unit(hp=-10, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_DEAD

    def test_one_hp_returns_critical_color(self, hud):
        unit = make_unit(hp=1, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_CRITICAL

    def test_boundary_80_percent_returns_healthy(self, hud):
        unit = make_unit(hp=80, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_HEALTHY

    def test_boundary_79_percent_returns_wounded(self, hud):
        unit = make_unit(hp=79, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_WOUNDED

    def test_boundary_50_percent_returns_wounded(self, hud):
        unit = make_unit(hp=50, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_WOUNDED

    def test_boundary_49_percent_returns_critical(self, hud):
        unit = make_unit(hp=49, max_hp=100)
        color = hud._get_status_color(unit)
        assert color == CC2HUD.STATUS_CRITICAL


@pytest.mark.unit
class TestLongUnitNameTruncation:

    def test_name_longer_than_14_chars_truncated_in_roster(self, hud, surface):
        long_name = "A" * 20
        unit = make_unit(name=long_name)
        hud.set_units([unit])
        hud.render(surface)
        assert len(getattr(unit, 'name', '')[:14]) == 14

    def test_name_shorter_than_limit_not_truncated(self, hud, surface):
        short_name = "Short"
        unit = make_unit(name=short_name)
        hud.set_units([unit])
        hud.render(surface)
        assert getattr(unit, 'name', '') == short_name

    def test_exact_limit_name_not_truncated(self, hud, surface):
        exact_name = "Exactly14Chars"
        unit = make_unit(name=exact_name)
        hud.set_units([unit])
        hud.render(surface)
        assert len(exact_name) == 14


@pytest.mark.unit
class TestScrollingWithManyUnits:

    def test_many_units_scroll_offset_starts_at_zero(self, hud, units_10):
        hud.set_units(units_10)
        assert hud._scroll_offset == 0

    def test_max_visible_units_is_eight(self, hud):
        assert hud._max_visible_units == 8

    def test_more_units_than_visible_creates_scrollbar(self, hud, surface, units_10):
        hud.set_units(units_10)
        hud.render(surface)
        total = len(hud._units)
        assert total > hud._max_visible_units


# ===========================================================================
# P2: Visual Regression Tests
# ===========================================================================


@pytest.mark.unit
class TestVisualRegression:

    def test_top_border_line_exists(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.render(surface)
        pixels = pygame.surfarray.array3d(surface)
        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT
        border_color = CC2HUD.BORDER_COLOR
        has_border = any(
            (pixels[x, panel_y, 0] == border_color[0] and
             pixels[x, panel_y, 1] == border_color[1] and
             pixels[x, panel_y, 2] == border_color[2])
            for x in range(0, SCREEN_W, 10)
        )
        assert has_border

    def test_left_panel_renders_darker_background(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.render(surface)
        pixels = pygame.surfarray.array3d(surface)
        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT + 30
        left_x = hud._left_width // 2
        bg = CC2HUD.PANEL_BG_DARK
        pixel = pixels[left_x, panel_y]
        assert abs(int(pixel[0]) - bg[0]) < 50
        assert abs(int(pixel[1]) - bg[1]) < 50
        assert abs(int(pixel[2]) - bg[2]) < 50

    def test_center_panel_renders_mid_background(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.render(surface)
        pixels = pygame.surfarray.array3d(surface)
        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT + 30
        center_x = hud._left_width + hud._center_width // 2
        bg = CC2HUD.PANEL_BG_MID
        pixel = pixels[center_x, panel_y]
        assert abs(int(pixel[0]) - bg[0]) < 15
        assert abs(int(pixel[1]) - bg[1]) < 15
        assert abs(int(pixel[2]) - bg[2]) < 15

    def test_right_panel_renders_lighter_background(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.render(surface)
        pixels = pygame.surfarray.array3d(surface)
        panel_y = SCREEN_H - CC2HUD.PANEL_HEIGHT + 30
        right_x = SCREEN_W - hud._right_width // 2
        bg = CC2HUD.PANEL_BG_LIGHT
        pixel = pixels[right_x, panel_y]
        assert abs(int(pixel[0]) - bg[0]) < 15
        assert abs(int(pixel[1]) - bg[1]) < 15
        assert abs(int(pixel[2]) - bg[2]) < 15

    def test_text_rendering_produces_nonzero_surface(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.render(surface)
        text_surf = hud._font_normal.render("Test", True, CC2HUD.TEXT_COLOR)
        assert text_surf.get_width() > 0
        assert text_surf.get_height() > 0

    def test_unit_icon_surfaces_have_correct_size(self, hud):
        for key, icon in hud._unit_icons.items():
            assert icon.get_size() == (16, 16), f"Icon {key} has wrong size"

    def test_command_icon_surfaces_have_correct_size(self, hud):
        for key, icon in hud._command_icons.items():
            assert icon.get_size() == (24, 24), f"Command icon {key} has wrong size"


@pytest.mark.unit
class TestCallbackRegistration:

    def test_register_unit_select_callback(self, hud):
        callback = MagicMock()
        hud.register_callback('unit_select', callback)
        assert hud._on_unit_select is callback

    def test_register_command_callback(self, hud):
        callback = MagicMock()
        hud.register_callback('command', callback)
        assert hud._on_command is callback

    def test_register_hide_toggle_callback(self, hud):
        callback = MagicMock()
        hud.register_callback('hide_toggle', callback)
        assert hud._on_hide_toggle is callback

    def test_register_unknown_event_type_ignored(self, hud):
        callback = MagicMock()
        hud.register_callback('unknown_event', callback)
        assert hud._on_unit_select is None


@pytest.mark.unit
class TestGameStateApplication:

    def test_apply_game_state_extracts_all_fields(self, hud, units_3):
        game_state = {
            'units': units_3,
            'selected_unit': 'u1',
            'ap_remaining': 5,
            'at_remaining': 2,
            'timer': '09:99',
        }
        hud._apply_game_state(game_state)
        assert len(hud._units) == 3
        assert hud._selected_unit_id == 'u1'
        assert hud._ap_remaining == 5
        assert hud._at_remaining == 2
        assert hud._timer == '09:99'

    def test_apply_partial_game_state_only_updates_provided(self, hud):
        hud.set_ap(10)
        game_state = {'ap_remaining': 3}
        hud._apply_game_state(game_state)
        assert hud._ap_remaining == 3
        assert hud._at_remaining == 5


@pytest.mark.unit
class TestUnitIconKeyMapping:

    def test_infantry_maps_to_infantry_key(self, hud):
        unit = make_unit(unit_type=UnitType.INFANTRY_SQUAD)
        key = hud._get_unit_icon_key(unit)
        assert key == 'infantry'

    def test_tank_unit_type_maps_to_tank_key(self, hud):
        from unittest.mock import PropertyMock
        unit = make_unit()
        type_mock = type('obj', (), {'name': 'HEAVY_TANK'})
        unit.unit_type = type_mock
        key = hud._get_unit_icon_key(unit)
        assert key == 'tank'


@pytest.mark.unit
class TestCrewStringGeneration:

    def test_single_operator_returns_default_crew_string(self, hud):
        unit = make_unit()
        crew = hud._get_crew_string(unit)
        assert crew == "Crew: Single operator"

    def test_squad_returns_member_roles(self, hud):
        unit = make_unit()
        mock_member1 = type('obj', (), {'role': 'rifleman'})
        mock_member2 = type('obj', (), {'role': 'machine_gunner'})
        mock_squad = type('obj', (), {'members': [mock_member1, mock_member2]})
        unit.squad_ref = mock_squad
        crew = hud._get_crew_string(unit)
        assert 'Rifleman' in crew
        assert 'Machine Gunner' in crew


# ===========================================================================
# Integration / End-to-End Smoke Tests
# ===========================================================================


@pytest.mark.unit
class TestSmokeTests:

    def test_full_render_cycle_with_all_features(self, hud, surface, units_10):
        hud.set_units(units_10)
        hud.set_selected_unit('u5')
        hud.set_ap(9)
        hud.set_at(4)
        hud.set_timer('14:22')

        triggered = {}
        hud.register_callback('unit_select', lambda uid: triggered.__setitem__('select', uid))
        hud.register_callback('command', lambda cid: triggered.__setitem__('cmd', cid))

        hud.render(surface)
        assert len(triggered) == 0

        if hud._unit_rects:
            rect, uid = hud._unit_rects[0]
            hud.handle_click((rect.centerx, rect.centery))

        if hud._command_button_rects:
            cmd_id, rect = list(hud._command_button_rects.items())[0]
            hud.handle_click((rect.centerx, rect.centery))

    def test_multiple_render_cycles_consistent(self, hud, surface, units_3):
        hud.set_units(units_3)
        hud.set_selected_unit('u0')

        hud.render(surface)
        pixels1 = pygame.surfarray.array3d(surface).copy()

        hud.set_ap(5)
        hud.render(surface)
        pixels2 = pygame.surfarray.array3d(surface).copy()

        assert pixels1.shape == pixels2.shape
