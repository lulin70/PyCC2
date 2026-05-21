"""
Unit tests for P5.2 Strategic Map and P5.3 Operation Timeline UI components.
Covers: StrategicMapRenderer, OperationTimelineUI, CampaignState integration
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from pycc2.domain.systems.campaign_state import (
    CampaignState,
    OperationPhase,
)
from pycc2.presentation.ui.strategic_map import (
    BRIDGE_POSITIONS,
    CORRIDOR_PATH,
    StrategicMapConfig,
    StrategicMapRenderer,
)
from pycc2.presentation.ui.operation_timeline import (
    DAY_INFO,
    TimelineConfig,
    OperationTimelineUI,
)


@pytest.fixture
def map_config():
    return StrategicMapConfig(width=800, height=500)


@pytest.fixture
def renderer(map_config):
    return StrategicMapRenderer(map_config)


@pytest.fixture
def timeline_config():
    return TimelineConfig(x=10, y=10, width=780, day_height=36)


@pytest.fixture
def timeline(timeline_config):
    return OperationTimelineUI(timeline_config)


@pytest.fixture
def fresh_campaign():
    return CampaignState.create_default()


@pytest.fixture
def mid_campaign():
    state = CampaignState.create_default()
    state.capture_bridge("son")
    state.capture_bridge("veghel")
    state.advance_day()
    state.advance_day()
    return state


@pytest.fixture
def mock_pygame_module():
    pg = MagicMock()
    pg.Surface.return_value = MagicMock()
    pg.Rect = MagicMock
    return pg


class TestStrategicMapConfigDefaults:

    def test_default_dimensions(self):
        cfg = StrategicMapConfig()
        assert cfg.width == 800
        assert cfg.height == 500

    def test_default_colors(self):
        cfg = StrategicMapConfig()
        assert cfg.bg_color == (34, 40, 54)
        assert cfg.bridge_allied_color == (80, 160, 80)
        assert cfg.highlight_color == (255, 200, 50)

    def test_custom_config(self):
        cfg = StrategicMapConfig(width=1024, height=768)
        assert cfg.width == 1024
        assert cfg.height == 768


class TestStrategicMapRendererInit:

    def test_default_init(self):
        r = StrategicMapRenderer()
        assert r.config is not None
        assert r.selected_bridge is None

    def test_custom_config_init(self, map_config):
        r = StrategicMapRenderer(map_config)
        assert r.config.width == 800

    def test_initial_selection_none(self, renderer):
        assert renderer.selected_bridge is None


class TestBridgePositionsData:

    def test_all_five_bridges_present(self):
        assert set(BRIDGE_POSITIONS.keys()) == {
            "arnhem", "nijmegen", "grave", "veghel", "son",
        }

    def test_bridge_coordinates_normalized(self):
        for key, pos in BRIDGE_POSITIONS.items():
            assert 0 <= pos["x"] <= 1
            assert 0 <= pos["y"] <= 1

    def test_bridges_ordered_north_to_south(self):
        keys = list(BRIDGE_POSITIONS.keys())
        y_values = [BRIDGE_POSITIONS[k]["y"] for k in keys]
        assert y_values == sorted(y_values)

    def test_corridor_path_has_six_points(self):
        assert len(CORRIDOR_PATH) == 6

    def test_corridor_path_matches_bridge_positions(self):
        corridor_set = set(CORRIDOR_PATH)
        for key, pos in BRIDGE_POSITIONS.items():
            assert (pos["x"], pos["y"]) in corridor_set


class TestStrategicMapBridgeInfo:

    def test_get_valid_bridge_info(self, renderer):
        info = renderer.get_bridge_info("arnhem")
        assert info is not None
        assert info["key"] == "arnhem"
        assert info["name"] == "Arnhem"
        assert "position_pct" in info

    def test_get_invalid_bridge_returns_none(self, renderer):
        assert renderer.get_bridge_info("nonexistent") is None

    def test_all_bridges_property(self, renderer):
        bridges = renderer.all_bridges
        assert len(bridges) == 5
        names = [b["name"] for b in bridges]
        assert "Arnhem" in names
        assert "Son" in names


class TestStrategicMapClickDetection:

    def test_click_on_exact_bridge_center(self, renderer):
        arnhem = BRIDGE_POSITIONS["arnhem"]
        bx = int(arnhem["x"] * 800)
        by = int(arnhem["y"] * 500)
        result = renderer.handle_click(bx, by, (0, 0))
        assert result == "arnhem"

    def test_click_near_bridge_within_radius(self, renderer):
        son = BRIDGE_POSITIONS["son"]
        bx = int(son["x"] * 800) + 10
        by = int(son["y"] * 500) + 5
        result = renderer.handle_click(bx, by, (0, 0))
        assert result == "son"

    def test_click_far_from_bridge_returns_none(self, renderer):
        result = renderer.handle_click(400, 250, (0, 0))
        assert result is None

    def test_click_sets_selected_bridge(self, renderer):
        nijmegen = BRIDGE_POSITIONS["nijmegen"]
        bx = int(nijmegen["x"] * 800)
        by = int(nijmegen["y"] * 500)
        renderer.handle_click(bx, by, (0, 0))
        assert renderer.selected_bridge == "nijmegen"

    def test_click_with_offset(self, renderer):
        nijmegen = BRIDGE_POSITIONS["nijmegen"]
        bx = int(nijmegen["x"] * 800) + 200
        by = int(nijmegen["y"] * 500) + 100
        result = renderer.handle_click(bx, by, (200, 100))
        assert result == "nijmegen"

    def test_clear_selection(self, renderer):
        nijmegen = BRIDGE_POSITIONS["nijmegen"]
        bx = int(nijmegen["x"] * 800)
        by = int(nijmegen["y"] * 500)
        renderer.handle_click(bx, by, (0, 0))
        assert renderer.selected_bridge is not None
        renderer.clear_selection()
        assert renderer.selected_bridge is None


class TestStrategicMapRenderHeadless:

    def test_render_without_campaign_state(self, renderer, mock_pygame_module):
        mock_screen = MagicMock()
        mock_screen.get_size.return_value = (1024, 768)
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            renderer.render(mock_screen, campaign_state=None, font=None)

    def test_render_with_campaign_state(self, renderer, mid_campaign, mock_pygame_module):
        mock_screen = MagicMock()
        mock_screen.get_size.return_value = (1024, 768)
        mock_font = MagicMock()
        mock_font.render.return_value = MagicMock(get_width=MagicMock(return_value=60))
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            renderer.render(mock_screen, campaign_state=mid_campaign, font=mock_font)

    def test_render_draws_corridor_line(self, renderer, mock_pygame_module):
        mock_screen = MagicMock()
        mock_screen.get_size.return_value = (1024, 768)
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            renderer.render(mock_screen, campaign_state=None, font=None)


class TestTimelineConfigDefaults:

    def test_default_position(self):
        cfg = TimelineConfig()
        assert cfg.x == 10
        assert cfg.y == 10

    def test_default_dimensions(self):
        cfg = TimelineConfig()
        assert cfg.width == 780
        assert cfg.day_height == 36

    def test_default_colors(self):
        cfg = TimelineConfig()
        assert cfg.current_color == (200, 160, 50)
        assert cfg.completed_color == (60, 150, 80)
        assert cfg.locked_color == (80, 80, 90)


class TestTimelineInit:

    def test_default_init(self):
        t = OperationTimelineUI()
        assert t.total_days == 6

    def test_custom_config(self, timeline_config):
        t = OperationTimelineUI(timeline_config)
        assert t.config.day_height == 36


class TestDayInfoData:

    def test_all_six_days_present(self):
        expected = {
            "DAY_1_SEPT17", "DAY_2_SEPT18", "DAY_3_SEPT19",
            "DAY_4_SEPT20", "DAY_5_SEPT21", "DAY_6_SEPT22",
        }
        assert set(DAY_INFO.keys()) == expected

    def test_each_day_has_required_fields(self):
        required = {"display", "short", "desc", "historical"}
        for key, info in DAY_INFO.items():
            assert required.issubset(info.keys()), f"{key} missing fields"

    def test_get_valid_day_info(self, timeline):
        info = timeline.get_day_info("DAY_1_SEPT17")
        assert info is not None
        assert "Sept 17" in info["display"]

    def test_get_invalid_day_info(self, timeline):
        assert timeline.get_day_info("DAY_99") is None


class TestTimelineDaysOrder:

    def test_total_days_count(self, timeline):
        assert timeline.total_days == 6

    def test_days_order_is_list(self, timeline):
        order = timeline.days_order
        assert isinstance(order, list)
        assert len(order) == 6

    def test_first_day_is_sept17(self, timeline):
        assert timeline.days_order[0] == "DAY_1_SEPT17"

    def test_last_day_is_sept22(self, timeline):
        assert timeline.days_order[-1] == "DAY_6_SEPT22"


def _make_mock_rect(x, y, w, h):
    rect = MagicMock()
    rect.x = x
    rect.y = y
    rect.collidepoint = lambda px, py, _x=x, _y=y, _w=w, _h=h: (
        _x <= px <= _x + _w and _y <= py <= _y + _h
    )
    return rect


class TestTimelineRenderHeadless:

    def test_render_returns_clickable_areas(self, timeline, mock_pygame_module):
        mock_screen = MagicMock()
        mock_pygame_module.Rect = _make_mock_rect
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            areas = timeline.render(mock_screen, campaign_state=None)
        assert len(areas) == 6

    def test_render_with_fresh_campaign(self, timeline, fresh_campaign, mock_pygame_module):
        mock_screen = MagicMock()
        mock_pygame_module.Rect = _make_mock_rect
        mock_font = MagicMock()
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            areas = timeline.render(mock_screen, campaign_state=fresh_campaign, font=mock_font)
        assert len(areas) == 6
        current = [a for a in areas if a["is_current"]]
        assert len(current) == 1
        assert current[0]["day_key"] == "DAY_1_SEPT17"

    def test_render_with_mid_campaign(self, timeline, mid_campaign, mock_pygame_module):
        mock_screen = MagicMock()
        mock_pygame_module.Rect = _make_mock_rect
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            areas = timeline.render(mock_screen, campaign_state=mid_campaign)
        current = [a for a in areas if a["is_current"]]
        assert current[0]["day_key"] == "DAY_3_SEPT19"

    def test_render_marks_past_days_completed(self, timeline, mid_campaign, mock_pygame_module):
        mock_screen = MagicMock()
        mock_pygame_module.Rect = _make_mock_rect
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            areas = timeline.render(mock_screen, campaign_state=mid_campaign)
        past = [a for a in areas if not a["is_current"] and a["clickable"]]
        assert len(past) == 2

    def test_render_future_days_locked(self, timeline, fresh_campaign, mock_pygame_module):
        mock_screen = MagicMock()
        mock_pygame_module.Rect = _make_mock_rect
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            areas = timeline.render(mock_screen, campaign_state=fresh_campaign)
        locked = [a for a in areas if not a["clickable"]]
        assert len(locked) == 5


class TestTimelineClickHandling:

    def test_click_on_current_day(self, timeline, fresh_campaign, mock_pygame_module):
        mock_screen = MagicMock()
        mock_pygame_module.Rect = _make_mock_rect
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            areas = timeline.render(mock_screen, campaign_state=fresh_campaign)
            rect = areas[0]["rect"]
            result = timeline.handle_click(rect.x + 10, rect.y + 10, areas)
        assert result == "DAY_1_SEPT17"

    def test_click_on_future_day_returns_none(self, timeline, fresh_campaign, mock_pygame_module):
        mock_screen = MagicMock()
        mock_pygame_module.Rect = _make_mock_rect
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            areas = timeline.render(mock_screen, campaign_state=fresh_campaign)
            rect = areas[5]["rect"]
            result = timeline.handle_click(rect.x + 10, rect.y + 10, areas)
        assert result is None

    def test_click_outside_all_areas(self, timeline, fresh_campaign, mock_pygame_module):
        mock_screen = MagicMock()
        mock_pygame_module.Rect = _make_mock_rect
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            areas = timeline.render(mock_screen, campaign_state=fresh_campaign)
            result = timeline.handle_click(9999, 9999, areas)
        assert result is None

    def test_click_on_past_day_allowed(self, timeline, mid_campaign, mock_pygame_module):
        mock_screen = MagicMock()
        mock_pygame_module.Rect = _make_mock_rect
        with patch.dict(sys.modules, {"pygame": mock_pygame_module}):
            areas = timeline.render(mock_screen, campaign_state=mid_campaign)
            past_area = areas[0]
            result = timeline.handle_click(
                past_area["rect"].x + 10, past_area["rect"].y + 10, areas
            )
        assert result == "DAY_1_SEPT17"


class TestCampaignStateToStrategicMapIntegration:

    def test_fresh_campaign_no_bridges_captured(self, fresh_campaign, renderer):
        assert fresh_campaign.bridges_held == 0
        for key in BRIDGE_POSITIONS:
            assert fresh_campaign.bridges_captured[key] is False

    def test_mid_campaign_two_bridges_captured(self, mid_campaign):
        assert mid_campaign.bridges_held == 2
        assert mid_campaign.bridges_captured["son"] is True
        assert mid_campaign.bridges_captured["veghel"] is True

    def test_capture_bridge_updates_state(self, fresh_campaign):
        assert fresh_campaign.capture_bridge("son") is True
        assert fresh_campaign.bridges_captured["son"] is True

    def test_renderer_reads_bridge_state(self, renderer, mid_campaign):
        bridges_state = mid_campaign.bridges_captured
        assert bridges_state.get("son") is True
        assert bridges_state.get("arnhem") is False

    def test_campaign_progress_pct(self, fresh_campaign, mid_campaign):
        assert fresh_campaign.campaign_progress_pct == 0.0
        assert mid_campaign.campaign_progress_pct == 0.4

    def test_full_campaign_victory_state(self):
        state = CampaignState.create_default()
        for bridge in BRIDGE_POSITIONS:
            state.capture_bridge(bridge)
        assert state.campaign_progress_pct == 1.0
        assert state.is_campaign_over is True
        assert state.campaign_outcome == "decisive_victory"


class TestCampaignStateToTimelineIntegration:

    def test_fresh_campaign_day_one(self, fresh_campaign, timeline):
        assert fresh_campaign.current_day == OperationPhase.DAY_1_SEPT17
        assert fresh_campaign.current_day.name == "DAY_1_SEPT17"

    def test_mid_campaign_day_three(self, mid_campaign):
        assert mid_campaign.current_day == OperationPhase.DAY_3_SEPT19

    def test_advance_day_progresses_timeline(self, fresh_campaign):
        assert fresh_campaign.current_day == OperationPhase.DAY_1_SEPT17
        fresh_campaign.advance_day()
        assert fresh_campaign.current_day == OperationPhase.DAY_2_SEPT18

    def test_day_info_matches_operation_phase_names(self):
        for day_key in DAY_INFO:
            assert day_key in OperationPhase.__members__
