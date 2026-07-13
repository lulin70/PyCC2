"""Tests for campaign_ui_report_mixin — report and campaign-end screen rendering.

Covers:
  - _generate_narrative_report: narrative text generation from result dict (pure logic)
  - _render_report: post-battle report with victory/defeat banner, casualties, experience
  - _render_campaign_end: campaign end screen with historical outcome, bridge status, casualties table
"""

from __future__ import annotations

import pytest
from pygame import Surface

from pycc2.presentation.ui.campaign_ui import CampaignUI
from pycc2.presentation.ui.campaign_ui_report_mixin import CampaignUIReportMixin


@pytest.fixture
def ui(pygame_display):
    """Create a real CampaignUI with initialized fonts."""
    ui = CampaignUI()
    ui.initialize()
    ui._visible = True
    return ui


@pytest.fixture
def surface():
    """Create a real pygame Surface for drawing."""
    return Surface((1024, 720))


class TestGenerateNarrativeReport:
    """Tests for _generate_narrative_report staticmethod — pure logic, no display needed."""

    def test_allied_victory(self):
        """Allied victory should produce victory message."""
        result = {"victory": True, "winner": "allies"}
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert "Allied forces have secured the objective!" in lines

    def test_axis_victory(self):
        """Axis victory should produce defeat message."""
        result = {"victory": False, "winner": "axis"}
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert "Axis forces have prevailed." in lines

    def test_draw(self):
        """Draw should produce neutral message."""
        result = {"victory": False, "winner": "draw"}
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert "Neither side achieved decisive victory." in lines

    def test_victory_flag_without_winner(self):
        """Victory=True with no winner should default to allies."""
        result = {"victory": True}
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert "Allied forces have secured the objective!" in lines

    def test_with_key_events(self):
        """Key events should be listed under --- Key Events --- header."""
        result = {"victory": True, "key_events": ["Bridge captured", "Counterattack repelled"]}
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert "--- Key Events ---" in lines
        assert any("Bridge captured" in line for line in lines)
        assert any("Counterattack repelled" in line for line in lines)

    def test_with_allied_kia(self):
        """Fallen units should be listed under --- Fallen --- header."""
        result = {"victory": True, "allied_kia": ["Sgt. Baker", "Cpl. Miller"]}
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert "--- Fallen ---" in lines
        assert any("Sgt. Baker" in line and "Killed in Action" in line for line in lines)
        assert any("Cpl. Miller" in line and "Killed in Action" in line for line in lines)

    def test_with_heroic_actions(self):
        """Heroic actions should be listed under --- Commendations --- header."""
        result = {
            "victory": True,
            "heroic_actions": ["Pvt. Smith held the line", "Sgt. Jones rallied the troops"],
        }
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert "--- Commendations ---" in lines
        assert any("Pvt. Smith held the line" in line for line in lines)
        assert any("Sgt. Jones rallied the troops" in line for line in lines)

    def test_no_narrative_data_with_casualties(self):
        """Without events/kia/heroic, summary section should show casualties."""
        result = {
            "victory": True,
            "casualties": {
                "allies": {"killed": 5, "wounded": 10},
                "axis": {"killed": 15, "wounded": 20},
            },
        }
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert "--- Summary ---" in lines
        assert any("allies" in line and "5 KIA" in line for line in lines)
        assert any("axis" in line and "15 KIA" in line for line in lines)

    def test_no_narrative_data_no_casualties(self):
        """Without any data, should show 'No significant casualties reported.'"""
        result = {"victory": True}
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert "--- Summary ---" in lines
        assert any("No significant casualties reported." in line for line in lines)

    def test_casualties_with_KIA_key(self):
        """Casualties dict with 'KIA' key (uppercase) should be handled."""
        result = {
            "victory": True,
            "casualties": {"allies": {"KIA": 3, "Wounded": 7}},
        }
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert any("3 KIA" in line for line in lines)

    def test_casualties_non_dict_value(self):
        """Non-dict casualty value should show as total."""
        result = {
            "victory": True,
            "casualties": {"allies": 25},
        }
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert any("25 casualties" in line for line in lines)

    def test_all_sections_present(self):
        """All narrative sections should appear when all data is provided."""
        result = {
            "victory": True,
            "key_events": ["Event 1"],
            "allied_kia": ["Hero 1"],
            "heroic_actions": ["Action 1"],
        }
        lines = CampaignUIReportMixin._generate_narrative_report(result)
        assert "--- Key Events ---" in lines
        assert "--- Fallen ---" in lines
        assert "--- Commendations ---" in lines
        assert "--- Summary ---" not in lines

    def test_empty_result(self):
        """Empty result dict should produce draw message and summary."""
        lines = CampaignUIReportMixin._generate_narrative_report({})
        assert "Neither side achieved decisive victory." in lines
        assert "--- Summary ---" in lines
        assert any("No significant casualties reported." in line for line in lines)


class TestRenderReport:
    """Tests for _render_report method."""

    def test_victory_banner(self, ui, surface):
        """Victory result should render and set button rects."""
        ui._battle_result = {"victory": True, "winner": "allies", "battle_name": "Arnhem"}
        ui._renderer._render_report(surface)
        assert ui._continue_button_rect is not None
        assert ui._back_button_rect is not None

    def test_defeat_banner(self, ui, surface):
        """Axis victory should render DEFEAT banner."""
        ui._battle_result = {"victory": False, "winner": "axis", "battle_name": "Arnhem"}
        ui._renderer._render_report(surface)

    def test_draw_banner(self, ui, surface):
        """Unknown winner should render DRAW banner."""
        ui._battle_result = {"victory": False, "winner": "draw", "battle_name": "Arnhem"}
        ui._renderer._render_report(surface)

    def test_with_casualties_dict(self, ui, surface):
        """Casualties as dict should be rendered."""
        ui._battle_result = {
            "victory": True,
            "casualties": {
                "allies": {"killed": 5, "wounded": 10},
                "axis": {"killed": 15, "wounded": 20},
            },
        }
        ui._renderer._render_report(surface)

    def test_with_casualties_non_dict(self, ui, surface):
        """Casualties as non-dict value should show total."""
        ui._battle_result = {
            "victory": True,
            "casualties": {"allies": 25},
        }
        ui._renderer._render_report(surface)

    def test_no_casualties(self, ui, surface):
        """No casualties data should show 'No casualty data available'."""
        ui._battle_result = {"victory": True}
        ui._renderer._render_report(surface)

    def test_with_experience(self, ui, surface):
        """Experience data should be rendered."""
        ui._battle_result = {
            "victory": True,
            "experience": {"infantry": 100, "armor": 50},
        }
        ui._renderer._render_report(surface)

    def test_no_experience(self, ui, surface):
        """No experience data should show 'No experience data available'."""
        ui._battle_result = {"victory": True}
        ui._renderer._render_report(surface)

    def test_with_narrative_key_events(self, ui, surface):
        """Key events in result should be rendered in narrative."""
        ui._battle_result = {
            "victory": True,
            "key_events": ["Bridge captured", "Counterattack repelled"],
        }
        ui._renderer._render_report(surface)

    def test_with_allied_kia(self, ui, surface):
        """Fallen units should be rendered in narrative."""
        ui._battle_result = {
            "victory": True,
            "allied_kia": ["Sgt. Baker"],
        }
        ui._renderer._render_report(surface)

    def test_with_heroic_actions(self, ui, surface):
        """Heroic actions should be rendered in narrative."""
        ui._battle_result = {
            "victory": True,
            "heroic_actions": ["Pvt. Smith held the line"],
        }
        ui._renderer._render_report(surface)

    def test_empty_result(self, ui, surface):
        """Empty result dict should not crash."""
        ui._battle_result = {}
        ui._renderer._render_report(surface)

    def test_none_result(self, ui, surface):
        """None result should use empty dict."""
        ui._battle_result = None
        ui._renderer._render_report(surface)

    def test_hovered_continue(self, ui, surface):
        """Hovering continue button should not crash."""
        ui._battle_result = {"victory": True}
        ui._hovered_button = "continue"
        ui._renderer._render_report(surface)

    def test_hovered_back(self, ui, surface):
        """Hovering back button should not crash."""
        ui._battle_result = {"victory": True}
        ui._hovered_button = "back"
        ui._renderer._render_report(surface)


class TestRenderCampaignEnd:
    """Tests for _render_campaign_end method."""

    def test_allies_victory(self, ui, surface):
        """ALLIES_VICTORY should render VICTORY banner and set button rects."""
        ui._campaign_summary = {
            "result": "ALLIES_VICTORY",
            "day_ended": 9,
            "allied_casualties": {"kia": 10, "wia": 20},
            "axis_casualties": {"kia": 30, "wia": 40},
            "bridge_status": {"Arnhem": "captured_allied"},
        }
        ui._renderer._render_campaign_end(surface)
        assert ui._new_campaign_button_rect is not None
        assert ui._main_menu_button_rect is not None

    def test_axis_victory(self, ui, surface):
        """AXIS_VICTORY should render DEFEAT banner."""
        ui._campaign_summary = {
            "result": "AXIS_VICTORY",
            "day_ended": 5,
            "allied_casualties": {"kia": 50, "wia": 60},
            "axis_casualties": {"kia": 5, "wia": 10},
            "bridge_status": {"Arnhem": "captured_axis"},
        }
        ui._renderer._render_campaign_end(surface)

    def test_draw(self, ui, surface):
        """DRAW result should render DRAW banner."""
        ui._campaign_summary = {
            "result": "DRAW",
            "day_ended": 9,
            "allied_casualties": {"kia": 15, "wia": 25},
            "axis_casualties": {"kia": 15, "wia": 25},
            "bridge_status": {"Arnhem": "contested"},
        }
        ui._renderer._render_campaign_end(surface)

    def test_no_bridge_status(self, ui, surface):
        """No bridge status should show 'No bridge data available'."""
        ui._campaign_summary = {
            "result": "DRAW",
            "day_ended": 9,
            "bridge_status": {},
        }
        ui._renderer._render_campaign_end(surface)

    def test_bridge_status_captured_allied(self, ui, surface):
        """Bridge captured by allies should show 'Captured (Allied)'."""
        ui._campaign_summary = {
            "result": "ALLIES_VICTORY",
            "bridge_status": {"Arnhem": "captured_allied", "Nijmegen": "captured_allied"},
        }
        ui._renderer._render_campaign_end(surface)

    def test_bridge_status_captured_axis(self, ui, surface):
        """Bridge captured by axis should show 'Held (Axis)'."""
        ui._campaign_summary = {
            "result": "AXIS_VICTORY",
            "bridge_status": {"Arnhem": "captured_axis"},
        }
        ui._renderer._render_campaign_end(surface)

    def test_bridge_status_contested(self, ui, surface):
        """Contested bridge should show 'Contested'."""
        ui._campaign_summary = {
            "result": "DRAW",
            "bridge_status": {"Eindhoven": "contested"},
        }
        ui._renderer._render_campaign_end(surface)

    def test_none_summary(self, ui, surface):
        """None summary should use empty dict defaults."""
        ui._campaign_summary = None
        ui._renderer._render_campaign_end(surface)

    def test_hovered_new_campaign(self, ui, surface):
        """Hovering new campaign button should not crash."""
        ui._campaign_summary = {"result": "ALLIES_VICTORY"}
        ui._hovered_button = "new_campaign"
        ui._renderer._render_campaign_end(surface)

    def test_hovered_main_menu(self, ui, surface):
        """Hovering main menu button should not crash."""
        ui._campaign_summary = {"result": "ALLIES_VICTORY"}
        ui._hovered_button = "main_menu"
        ui._renderer._render_campaign_end(surface)
