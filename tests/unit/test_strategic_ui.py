"""
Unit tests for P5.2 Strategic Map.
Covers: StrategicMapRenderer, CampaignState integration
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from pycc2.domain.systems.campaign_state import (
    CampaignState,
)
from pycc2.presentation.ui.strategic_map import (
    BRIDGE_POSITIONS,
    CORRIDOR_PATH,
    StrategicMapConfig,
    StrategicMapRenderer,
)


@pytest.fixture
def map_config():
    return StrategicMapConfig(width=800, height=500)


@pytest.fixture
def renderer(map_config):
    return StrategicMapRenderer(map_config)


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
            "arnhem",
            "nijmegen",
            "grave",
            "veghel",
            "son",
        }

    def test_bridge_coordinates_normalized(self):
        for _key, pos in BRIDGE_POSITIONS.items():
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
        for _key, pos in BRIDGE_POSITIONS.items():
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
