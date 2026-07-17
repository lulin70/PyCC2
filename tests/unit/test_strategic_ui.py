"""
Unit tests for P5.2 Strategic Map.
Covers: CampaignState integration
"""

from __future__ import annotations

import pytest

from pycc2.domain.systems.campaign_state import (
    CampaignState,
)


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


class TestCampaignStateToStrategicMapIntegration:
    def test_mid_campaign_two_bridges_captured(self, mid_campaign):
        assert mid_campaign.bridges_held == 2
        assert mid_campaign.bridges_captured["son"] is True
        assert mid_campaign.bridges_captured["veghel"] is True

    def test_capture_bridge_updates_state(self, fresh_campaign):
        assert fresh_campaign.capture_bridge("son") is True
        assert fresh_campaign.bridges_captured["son"] is True

    def test_campaign_progress_pct(self, fresh_campaign, mid_campaign):
        assert fresh_campaign.campaign_progress_pct == 0.0
        assert mid_campaign.campaign_progress_pct == 0.4
