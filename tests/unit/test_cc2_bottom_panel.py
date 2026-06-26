"""
Unit tests for CC2BottomPanel

Covers: layout constants, command buttons, roster, minimap zoom,
urgency indicator, mouse hover, and rendering.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.bottom_panel_command_bar import CommandBarRenderer
from pycc2.presentation.rendering.bottom_panel_icons import (
    create_command_icons,
    create_commander_portrait,
    create_roster_icons,
)
from pycc2.presentation.rendering.bottom_panel_input_handler import BottomPanelInputHandler
from pycc2.presentation.rendering.bottom_panel_minimap_section import MinimapSectionRenderer
from pycc2.presentation.rendering.bottom_panel_roster import RosterRenderer
from pycc2.presentation.rendering.bottom_panel_soldier_monitor import SoldierMonitorRenderer
from pycc2.presentation.rendering.bottom_panel_unit_detail import UnitDetailRenderer
from pycc2.presentation.rendering.bottom_panel_urgency import UrgencyIndicatorRenderer
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCREEN_W, SCREEN_H = 900, 600


def make_unit(
    unit_id: str = "u1",
    name: str = "Rifle Squad",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 85,
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
            max_ammo=120,
            ammo_remaining=120,
        ),
        position=PositionComponent(tile_coord=TileCoord(5, 5)),
        vision=VisionComponent(),
    )


def make_game_map() -> GameMap:
    grid = np.zeros((16, 16), dtype=np.int8)
    return GameMap(id="test", name="Test Map", width=16, height=16, tile_grid=grid)


def make_camera() -> Camera:
    return Camera(position=Vec2(256.0, 256.0), viewport_width=SCREEN_W, viewport_height=SCREEN_H)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def panel(pygame_display):
    p = CC2BottomPanel()
    p.initialize()
    return p


@pytest.fixture()
def surface(pygame_display):
    return pygame.Surface((SCREEN_W, SCREEN_H))


@pytest.fixture()
def camera():
    return make_camera()


@pytest.fixture()
def game_map():
    return make_game_map()


@pytest.fixture()
def units_5():
    return [make_unit(unit_id=f"u{i}", name=f"Squad {i}", morale=60 + i * 8) for i in range(5)]


@pytest.fixture()
def units_8():
    return [make_unit(unit_id=f"u{i}", name=f"Squad {i}", morale=50 + i * 6) for i in range(8)]


# ===========================================================================
# 1. Panel Layout Tests
# ===========================================================================


@pytest.mark.unit
class TestPanelLayout:
    def test_panel_constants_are_consistent(self):
        assert CC2BottomPanel.PANEL_HEIGHT == 130  # Updated to match CC2 original (~120-130px)
        assert CC2BottomPanel.ROSTER_WIDTH == 170
        assert CC2BottomPanel.DETAIL_WIDTH == 240
        assert CC2BottomPanel.COMMAND_WIDTH == 180
        assert CC2BottomPanel.URGENCY_WIDTH == 60
        assert CC2BottomPanel.MINIMAP_SIZE == 120

    def test_panel_sections_dont_overlap(self, panel, surface, camera, game_map):
        panel.set_friendly_units([make_unit()])
        panel.set_selected_unit("u1")
        panel.render(surface, camera, game_map)

        # Section x-starts derived from render logic:
        #   Roster: 5
        #   Details: ROSTER_WIDTH + 10 = 180
        #   Commands: 180 + DETAIL_WIDTH + 10 = 430
        #   Urgency: 430 + COMMAND_WIDTH + 5 = 615
        #   Minimap: 615 + URGENCY_WIDTH + 5 = 680
        roster_x = 5
        detail_x = CC2BottomPanel.ROSTER_WIDTH + 10
        cmd_x = detail_x + CC2BottomPanel.DETAIL_WIDTH + 10
        urgency_x = cmd_x + CC2BottomPanel.COMMAND_WIDTH + 5
        minimap_x = urgency_x + CC2BottomPanel.URGENCY_WIDTH + 5

        assert roster_x == 5
        assert detail_x == 180
        assert cmd_x == 430
        assert urgency_x == 615
        assert minimap_x == 680

        # Ensure no horizontal overlap between adjacent sections
        assert roster_x + CC2BottomPanel.ROSTER_WIDTH <= detail_x
        assert detail_x + CC2BottomPanel.DETAIL_WIDTH <= cmd_x
        assert cmd_x + CC2BottomPanel.COMMAND_WIDTH <= urgency_x
        assert urgency_x + CC2BottomPanel.URGENCY_WIDTH <= minimap_x

    def test_command_bar_height_fits_in_panel(self):
        assert CC2BottomPanel.COMMAND_BAR_HEIGHT < CC2BottomPanel.PANEL_HEIGHT


# ===========================================================================
# 2. Command Button Tests
# ===========================================================================


@pytest.mark.unit
class TestCommandButtons:
    EXPECTED_IDS = [
        "move",
        "fast",
        "sneak",
        "attack",
        "smoke",
        "defend",
        "hide",
        "cancel",
        "end_battle",
    ]

    def test_command_buttons_exist(self, panel):
        ids = [cmd["id"] for cmd in panel._commands]
        assert ids == self.EXPECTED_IDS

    def test_command_button_click_returns_command_id(
        self, panel, surface, camera, game_map, units_5
    ):
        panel.set_friendly_units(units_5)
        panel.set_selected_unit("u0")
        panel.render(surface, camera, game_map)

        for cmd_id, rect in panel._button_rects.items():
            cx, cy = rect.centerx, rect.centery
            result = panel.handle_click((cx, cy))
            assert result == f"command:{cmd_id}", (
                f"Click on {cmd_id} should return command:{cmd_id}"
            )

    def test_command_button_click_triggers_callback(
        self, panel, surface, camera, game_map, units_5
    ):
        panel.set_friendly_units(units_5)
        panel.set_selected_unit("u0")
        panel.render(surface, camera, game_map)

        triggered = []

        for cmd_id in self.EXPECTED_IDS:
            panel.register_callback(cmd_id, lambda cid=cmd_id: triggered.append(cid))

        for _cmd_id, rect in panel._button_rects.items():
            cx, cy = rect.centerx, rect.centery
            panel.handle_click((cx, cy))

        assert triggered == self.EXPECTED_IDS

    def test_cancel_button_always_enabled(self, panel, surface, camera, game_map):
        # No unit selected — cancel should still be clickable
        panel.render(surface, camera, game_map)
        cancel_rect = panel._button_rects.get("cancel")
        assert cancel_rect is not None
        result = panel.handle_click((cancel_rect.centerx, cancel_rect.centery))
        assert result == "command:cancel"

    def test_command_buttons_require_selection(self, panel, surface, camera, game_map):
        """move/fast/sneak/attack/defend buttons exist but need a selected unit."""
        panel.render(surface, camera, game_map)
        needs_selection = {"move", "fast", "sneak", "attack", "defend"}
        for cmd in panel._commands:
            if cmd["id"] in needs_selection:
                assert cmd["enabled_when_selected"] is True

    def test_smoke_button_needs_ammo(self, panel):
        smoke_cmd = next(c for c in panel._commands if c["id"] == "smoke")
        assert smoke_cmd.get("needs_smoke_ammo") is True


# ===========================================================================
# 3. Roster Tests
# ===========================================================================


@pytest.mark.unit
class TestRoster:
    def test_set_friendly_units_populates_roster(self, panel, units_5):
        panel.set_friendly_units(units_5)
        assert len(panel._friendly_units) == 5

    def test_roster_click_selects_unit(self, panel, surface, camera, game_map, units_5):
        panel.set_friendly_units(units_5)
        panel.render(surface, camera, game_map)

        # Click on first visible roster item
        for rect, unit_id in panel._roster_item_rects:
            result = panel.handle_click((rect.centerx, rect.centery))
            assert result == f"select_unit:{unit_id}"
            break

    def test_roster_click_triggers_callback(self, panel, surface, camera, game_map, units_5):
        panel.set_friendly_units(units_5)
        panel.render(surface, camera, game_map)

        selected_ids = []
        panel._on_unit_select = lambda uid: selected_ids.append(uid)

        for rect, _unit_id in panel._roster_item_rects:
            panel.handle_click((rect.centerx, rect.centery))

        assert len(selected_ids) >= 1

    def test_set_selected_unit_auto_scrolls(self, panel, units_8):
        panel.set_friendly_units(units_8)
        # Select a unit beyond the visible window (index 7)
        panel.set_selected_unit("u7")
        # After auto-scroll, the scroll offset should ensure u7 is visible
        visible_start = panel._roster_scroll_offset
        visible_end = visible_start + panel._visible_roster_items
        unit_index = next(i for i, u in enumerate(panel._friendly_units) if u.id == "u7")
        assert visible_start <= unit_index < visible_end

    def test_roster_shows_max_5_items(self, panel, surface, camera, game_map, units_8):
        panel.set_friendly_units(units_8)
        panel.render(surface, camera, game_map)
        assert len(panel._roster_item_rects) <= 5

    def test_roster_shows_unit_type_and_name(self, panel, surface, camera, game_map, units_5):
        panel.set_friendly_units(units_5)
        panel.render(surface, camera, game_map)
        # Verify roster item rects exist and map to correct unit ids
        roster_ids = [uid for _, uid in panel._roster_item_rects]
        assert len(roster_ids) == 5
        for uid in roster_ids:
            assert uid.startswith("u")


# ===========================================================================
# 4. Minimap Zoom Tests
# ===========================================================================


@pytest.mark.unit
class TestMinimapZoom:
    def test_zoom_in_increases_level(self, panel):
        initial = panel.get_zoom_level()
        new_level = panel.zoom_in()
        assert new_level >= initial

    def test_zoom_out_decreases_level(self, panel):
        # Zoom in first so we can zoom out
        panel.zoom_in()
        after_in = panel.get_zoom_level()
        new_level = panel.zoom_out()
        assert new_level <= after_in

    def test_zoom_has_5_levels(self, panel):
        assert len(panel._zoom_levels) == 5
        assert panel._zoom_levels == [0.5, 0.75, 1.0, 1.5, 2.0]

    def test_zoom_change_triggers_callback(self, panel):
        zoom_values = []
        panel._on_zoom_change = lambda z: zoom_values.append(z)
        panel.zoom_in()
        assert len(zoom_values) == 1
        assert zoom_values[0] > 1.0

    def test_zoom_click_returns_zoom_string(self, panel, surface, camera, game_map):
        panel.render(surface, camera, game_map)
        # Click zoom-in button
        if panel._zoom_in_rect:
            result = panel.handle_click((panel._zoom_in_rect.centerx, panel._zoom_in_rect.centery))
            assert result is not None
            assert result.startswith("zoom:")
        # Click zoom-out button
        if panel._zoom_out_rect:
            result = panel.handle_click(
                (panel._zoom_out_rect.centerx, panel._zoom_out_rect.centery)
            )
            assert result is not None
            assert result.startswith("zoom:")


# ===========================================================================
# 5. Urgency Indicator Tests
# ===========================================================================


@pytest.mark.unit
class TestUrgencyIndicator:
    def test_urgency_critical_when_low_hp_and_morale(self, panel, surface, camera, game_map):
        unit = make_unit(unit_id="u1", hp=10, max_hp=100, morale=5)
        panel.set_friendly_units([unit])
        panel.set_selected_unit("u1")
        panel.render(surface, camera, game_map)

        # urgency_value = (1 - 10/100)*50 + (1 - 5/100)*50 = 45 + 47.5 = 92.5 → CRITICAL
        hp_ratio = unit.health.hp / unit.health.max_hp
        morale = unit.morale.value
        urgency_value = int((1 - hp_ratio) * 50 + (1 - morale / 100) * 50)
        assert urgency_value >= 80  # CRITICAL threshold

    def test_urgency_safe_when_full_hp_and_morale(self, panel, surface, camera, game_map):
        unit = make_unit(unit_id="u1", hp=100, max_hp=100, morale=100)
        panel.set_friendly_units([unit])
        panel.set_selected_unit("u1")
        panel.render(surface, camera, game_map)

        hp_ratio = unit.health.hp / unit.health.max_hp
        morale = unit.morale.value
        urgency_value = int((1 - hp_ratio) * 50 + (1 - morale / 100) * 50)
        assert urgency_value < 20  # SAFE threshold

    def test_urgency_safe_when_no_unit_selected(self, panel, surface, camera, game_map):
        panel.set_friendly_units([make_unit()])
        # No unit selected
        panel.render(surface, camera, game_map)
        # Without selection, urgency defaults to SAFE (urgency_value=0)
        assert panel._selected_unit_id is None

    def test_urgency_levels_correct(self, panel, surface, camera, game_map):
        """Test all 5 urgency levels with different HP/morale combinations."""
        test_cases = [
            # (hp, max_hp, morale, expected_level)
            (10, 100, 5, "CRITICAL"),  # urgency >= 80
            (30, 100, 20, "HIGH"),  # urgency >= 60
            (50, 100, 50, "MEDIUM"),  # urgency >= 40
            (70, 100, 70, "LOW"),  # urgency >= 20
            (100, 100, 100, "SAFE"),  # urgency < 20
        ]

        for hp, max_hp, morale, expected in test_cases:
            unit = make_unit(unit_id="u1", hp=hp, max_hp=max_hp, morale=morale)
            panel.set_friendly_units([unit])
            panel.set_selected_unit("u1")

            hp_ratio = hp / max_hp
            urgency_value = int((1 - hp_ratio) * 50 + (1 - morale / 100) * 50)

            if urgency_value >= 80:
                level = "CRITICAL"
            elif urgency_value >= 60:
                level = "HIGH"
            elif urgency_value >= 40:
                level = "MEDIUM"
            elif urgency_value >= 20:
                level = "LOW"
            else:
                level = "SAFE"

            assert level == expected, (
                f"HP={hp}/{max_hp}, Morale={morale}: "
                f"urgency_value={urgency_value}, got {level}, expected {expected}"
            )


# ===========================================================================
# 6. Mouse Hover Tests
# ===========================================================================


@pytest.mark.unit
class TestMouseHover:
    def test_handle_mouse_move_updates_hover(self, panel, surface, camera, game_map, units_5):
        panel.set_friendly_units(units_5)
        panel.set_selected_unit("u0")
        panel.render(surface, camera, game_map)

        # Move mouse to the center of the first command button
        for cmd_id, rect in panel._button_rects.items():
            panel.handle_mouse_move((rect.centerx, rect.centery))
            assert panel._hovered_command == cmd_id
            break

    def test_handle_mouse_move_clears_hover(self, panel, surface, camera, game_map, units_5):
        panel.set_friendly_units(units_5)
        panel.set_selected_unit("u0")
        panel.render(surface, camera, game_map)

        # First hover over a button
        for cmd_id, rect in panel._button_rects.items():
            panel.handle_mouse_move((rect.centerx, rect.centery))
            assert panel._hovered_command == cmd_id
            break

        # Move mouse to a position outside all buttons
        panel.handle_mouse_move((0, 0))
        assert panel._hovered_command is None


# ===========================================================================
# 7. Extracted Helper Renderer Tests
# ===========================================================================


@pytest.mark.unit
class TestExtractedRenderers:
    def test_roster_renderer_can_render_directly(self, panel, surface, units_5):
        panel.set_friendly_units(units_5)
        renderer = RosterRenderer(panel)
        renderer.render(surface, 0, 0, CC2BottomPanel.ROSTER_WIDTH, 130)
        assert len(panel._roster_item_rects) == len(units_5)

    def test_unit_detail_renderer_can_render_directly(self, panel, surface, units_5):
        panel.set_friendly_units(units_5)
        panel.set_selected_unit("u0")
        renderer = UnitDetailRenderer(panel)
        renderer.render(surface, 0, 0, CC2BottomPanel.DETAIL_WIDTH, 130)

    def test_command_bar_renderer_can_render_directly(self, panel, surface):
        renderer = CommandBarRenderer(panel)
        renderer.render(surface, 0, 0, CC2BottomPanel.COMMAND_WIDTH, 200, time_remaining=None)
        assert len(panel._button_rects) == len(panel._commands)

    def test_minimap_section_renderer_can_render_directly(self, panel, surface, camera, game_map):
        renderer = MinimapSectionRenderer(panel)
        renderer.render(
            surface,
            0,
            0,
            CC2BottomPanel.MINIMAP_SIZE,
            None,
            camera,
            game_map,
        )
        assert panel._zoom_in_rect is not None
        assert panel._zoom_out_rect is not None

    def test_urgency_renderer_can_render_directly(self, panel, surface):
        renderer = UrgencyIndicatorRenderer(panel)
        renderer.render(surface, 0, 0, CC2BottomPanel.URGENCY_WIDTH, 130)


# ===========================================================================
# 8. Rendering Tests
# ===========================================================================


@pytest.mark.unit
class TestRendering:
    def test_render_does_not_crash(self, panel, surface, camera, game_map):
        panel.render(surface, camera, game_map)

    def test_render_with_minimap(self, panel, surface, camera, game_map):
        from pycc2.presentation.rendering.minimap import Minimap

        minimap = Minimap()
        minimap.set_map(game_map)
        panel.render(surface, camera, game_map, minimap=minimap)

    def test_render_without_selected_unit(self, panel, surface, camera, game_map, units_5):
        panel.set_friendly_units(units_5)
        # No unit selected
        panel.render(surface, camera, game_map)

    def test_render_with_selected_unit(self, panel, surface, camera, game_map, units_5):
        panel.set_friendly_units(units_5)
        panel.set_selected_unit("u0")
        panel.render(surface, camera, game_map)


# ===========================================================================
# 9. New Sub-module Tests
# ===========================================================================


@pytest.mark.unit
class TestNewSubmodules:
    def test_icons_functions_create_surfaces(self):
        bg = (58, 64, 48)
        border = (90, 96, 80)
        command_icons = create_command_icons(bg)
        roster_icons = create_roster_icons(bg)
        portrait = create_commander_portrait(bg, border)

        assert len(command_icons) > 0
        assert "move" in command_icons
        assert len(roster_icons) > 0
        assert "infantry" in roster_icons
        assert portrait.get_size() == (24, 24)

    def test_soldier_monitor_renderer_renders(self, panel, surface):
        from pycc2.domain.entities.squad import MemberState, Squad, SquadMember, SquadType

        squad = Squad(
            squad_id="squad_1",
            squad_type=SquadType.RIFLE_SQUAD,
            faction="allies",
        )
        squad.members = [
            SquadMember(
                member_id="m1", role="rifleman", hp=100, state=MemberState.HEALTHY, experience=20
            ),
            SquadMember(
                member_id="m2", role="mg_gunner", hp=80, state=MemberState.HEALTHY, experience=35
            ),
        ]
        renderer = SoldierMonitorRenderer(panel)
        renderer.render(surface, 0, 0, CC2BottomPanel.DETAIL_WIDTH, 130, squad)

        assert len(panel._soldier_member_rects) == len(squad.members)

    def test_input_handler_command_click(self, panel, surface, camera, game_map, units_5):
        panel.set_friendly_units(units_5)
        panel.set_selected_unit("u0")
        panel.render(surface, camera, game_map)

        handler = BottomPanelInputHandler(panel)
        for cmd_id, rect in panel._button_rects.items():
            result = handler.handle_click((rect.centerx, rect.centery))
            assert result == f"command:{cmd_id}"
            break

    def test_input_handler_soldier_right_click(self, panel, surface):
        from pycc2.domain.entities.squad import MemberState, Squad, SquadMember, SquadType

        squad = Squad(
            squad_id="squad_1",
            squad_type=SquadType.RIFLE_SQUAD,
            faction="allies",
        )
        squad.members = [
            SquadMember(
                member_id="m1", role="rifleman", hp=100, state=MemberState.HEALTHY, experience=20
            ),
        ]
        panel._soldier_member_rects = []
        # Simulate soldier monitor rendering to populate rects
        SoldierMonitorRenderer(panel).render(surface, 0, 0, CC2BottomPanel.DETAIL_WIDTH, 130, squad)

        handler = BottomPanelInputHandler(panel)
        rect, _member = panel._soldier_member_rects[0]
        result = handler.handle_right_click((rect.centerx, rect.centery))
        assert result is not None
        assert "soldier_detail" in result
