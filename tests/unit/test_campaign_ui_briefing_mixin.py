"""Tests for campaign_ui_briefing_mixin — briefing and preview screen rendering.

Covers:
  - _render_briefing: operation briefing with day header, strategic map, battle selection
  - _render_preview: pre-battle preview with mini map, objectives, and forces
"""

from __future__ import annotations

import pytest
from pygame import Surface

from pycc2.presentation.ui.campaign_ui import CampaignUI
from pycc2.presentation.ui.campaign_ui_types import CampaignBattle, CampaignOperation


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


def _make_battle(
    battle_id="b1",
    name="Battle of Arnhem",
    map_file="Map001",
    description="Secure the bridge",
    completed=False,
    locked=False,
    objectives=None,
    allied_forces=None,
    axis_forces=None,
):
    return CampaignBattle(
        battle_id=battle_id,
        name=name,
        map_file=map_file,
        description=description,
        completed=completed,
        locked=locked,
        objectives=objectives or ["Secure the bridge", "Hold for 3 turns"],
        allied_forces=allied_forces or ["1st Airborne", "XXX Corps"],
        axis_forces=axis_forces or ["9th SS Panzer"],
    )


def _make_operation(
    operation_id="op1",
    name="Operation Market Garden",
    day=3,
    total_days=9,
    battles=None,
    sector="arnhem",
    description="Allied airborne assault",
    historical_briefing="On September 17, 1944, the largest airborne operation",
):
    return CampaignOperation(
        operation_id=operation_id,
        name=name,
        day=day,
        total_days=total_days,
        battles=battles or [_make_battle()],
        sector=sector,
        description=description,
        historical_briefing=historical_briefing,
    )


class TestRenderBriefing:
    """Tests for _render_briefing method."""

    def test_no_operation_returns_early(self, ui, surface):
        """With no current operation, should return early without setting button rects."""
        ui._current_operation = None
        ui._renderer._render_briefing(surface)
        assert ui._start_button_rect is None
        assert ui._back_button_rect is None
        assert ui._battle_rects == {}

    def test_renders_with_operation(self, ui, surface):
        """Briefing should render with a valid operation and set button rects."""
        op = _make_operation()
        ui._current_operation = op
        ui._renderer._render_briefing(surface)
        assert ui._start_button_rect is not None
        assert ui._back_button_rect is not None
        assert len(ui._battle_rects) > 0

    def test_battle_rects_populated(self, ui, surface):
        """Each visible battle should get a rect in _battle_rects."""
        battles = [_make_battle(battle_id=f"b{i}", name=f"Battle {i}") for i in range(3)]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._renderer._render_briefing(surface)
        assert len(ui._battle_rects) == 3
        for i in range(3):
            assert f"b{i}" in ui._battle_rects

    def test_selected_battle_highlighted(self, ui, surface):
        """Selected battle should be rendered with highlight."""
        battles = [_make_battle(battle_id="b1"), _make_battle(battle_id="b2")]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._selected_battle_id = "b2"
        ui._renderer._render_briefing(surface)
        assert "b2" in ui._battle_rects

    def test_hovered_battle_rendered(self, ui, surface):
        """Hovered battle should be rendered with hover styling."""
        battles = [_make_battle(battle_id="b1"), _make_battle(battle_id="b2")]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._hovered_battle_id = "b1"
        ui._renderer._render_briefing(surface)

    def test_locked_battle_rendered(self, ui, surface):
        """Locked battles should be rendered with different styling."""
        battles = [_make_battle(battle_id="b1", locked=True), _make_battle(battle_id="b2")]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._renderer._render_briefing(surface)
        assert "b1" in ui._battle_rects

    def test_completed_battle_rendered(self, ui, surface):
        """Completed battles should show [OK] icon."""
        battles = [_make_battle(battle_id="b1", completed=True)]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._renderer._render_briefing(surface)
        assert "b1" in ui._battle_rects

    def test_selected_battle_description_rendered(self, ui, surface):
        """Description of selected battle should be rendered below battle list."""
        battles = [
            _make_battle(battle_id="b1", description="A fierce battle at the bridge"),
        ]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._selected_battle_id = "b1"
        ui._renderer._render_briefing(surface)

    def test_hovered_start_button(self, ui, surface):
        """Hovering start button should not crash."""
        op = _make_operation()
        ui._current_operation = op
        ui._hovered_button = "start"
        ui._renderer._render_briefing(surface)
        assert ui._start_button_rect is not None

    def test_hovered_back_button(self, ui, surface):
        """Hovering back button should not crash."""
        op = _make_operation()
        ui._current_operation = op
        ui._hovered_button = "back"
        ui._renderer._render_briefing(surface)
        assert ui._back_button_rect is not None

    def test_historical_briefing_text(self, ui, surface):
        """Long historical briefing text should wrap without crash."""
        op = _make_operation(historical_briefing="A detailed historical briefing text " * 20)
        ui._current_operation = op
        ui._renderer._render_briefing(surface)

    def test_no_briefing_falls_back_to_description(self, ui, surface):
        """When historical_briefing is empty, description should be used."""
        op = _make_operation(historical_briefing="", description="Fallback description " * 10)
        ui._current_operation = op
        ui._renderer._render_briefing(surface)

    def test_no_briefing_no_description(self, ui, surface):
        """When both historical_briefing and description are empty, fallback message used."""
        op = _make_operation(historical_briefing="", description="")
        ui._current_operation = op
        ui._renderer._render_briefing(surface)

    def test_operation_description_rendered(self, ui, surface):
        """Operation description should be rendered in right panel."""
        op = _make_operation(description="A detailed operation description " * 5)
        ui._current_operation = op
        ui._renderer._render_briefing(surface)


class TestRenderPreview:
    """Tests for _render_preview method."""

    def test_no_battle_returns_early(self, ui, surface):
        """With no current battle, should return early without setting button rects."""
        ui._current_battle = None
        ui._renderer._render_preview(surface)
        assert ui._deploy_button_rect is None
        assert ui._back_button_rect is None

    def test_renders_with_battle(self, ui, surface):
        """Preview should render with a valid battle and set button rects."""
        battle = _make_battle()
        ui._current_battle = battle
        ui._renderer._render_preview(surface)
        assert ui._deploy_button_rect is not None
        assert ui._back_button_rect is not None

    def test_objectives_rendered(self, ui, surface):
        """Objectives should be rendered when present."""
        battle = _make_battle(objectives=["Take the bridge", "Hold position", "Eliminate AA"])
        ui._current_battle = battle
        ui._renderer._render_preview(surface)

    def test_no_objectives_fallback(self, ui, surface):
        """Default objective text should be shown when objectives list is empty."""
        battle = _make_battle(objectives=[])
        ui._current_battle = battle
        ui._renderer._render_preview(surface)

    def test_allied_forces_rendered(self, ui, surface):
        """Allied forces should be rendered when present."""
        battle = _make_battle(allied_forces=["1st Airborne", "XXX Corps", "82nd Airborne"])
        ui._current_battle = battle
        ui._renderer._render_preview(surface)

    def test_axis_forces_rendered(self, ui, surface):
        """Axis forces should be rendered when present."""
        battle = _make_battle(axis_forces=["9th SS Panzer", "10th SS Panzer"])
        ui._current_battle = battle
        ui._renderer._render_preview(surface)

    def test_empty_forces_use_defaults(self, ui, surface):
        """Empty forces lists should use default values."""
        battle = _make_battle(allied_forces=[], axis_forces=[])
        ui._current_battle = battle
        ui._renderer._render_preview(surface)

    def test_battle_description_rendered(self, ui, surface):
        """Battle description should be rendered below the map."""
        battle = _make_battle(description="A long description of the battle that should wrap " * 5)
        ui._current_battle = battle
        ui._renderer._render_preview(surface)

    def test_hovered_deploy_button(self, ui, surface):
        """Hovering deploy button should not crash."""
        battle = _make_battle()
        ui._current_battle = battle
        ui._hovered_button = "deploy"
        ui._renderer._render_preview(surface)

    def test_hovered_back_button(self, ui, surface):
        """Hovering back button should not crash."""
        battle = _make_battle()
        ui._current_battle = battle
        ui._hovered_button = "back"
        ui._renderer._render_preview(surface)
