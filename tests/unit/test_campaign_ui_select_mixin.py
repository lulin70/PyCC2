"""Tests for campaign_ui_select_mixin — operation and battle selection screens.

Covers:
  - _render_operation_select: operation selection screen
  - _render_battle_select: battle selection screen (original layout)
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
):
    return CampaignBattle(
        battle_id=battle_id,
        name=name,
        map_file=map_file,
        description=description,
        completed=completed,
        locked=locked,
    )


def _make_operation(
    operation_id="op1",
    name="Operation Market Garden",
    day=3,
    total_days=9,
    battles=None,
    description="Allied airborne assault",
):
    return CampaignOperation(
        operation_id=operation_id,
        name=name,
        day=day,
        total_days=total_days,
        battles=battles or [_make_battle()],
        description=description,
    )


class TestRenderOperationSelect:
    """Tests for _render_operation_select method."""

    def test_renders_with_operations(self, ui, surface):
        """Operation select should render with valid operations and set button rects."""
        ops = [_make_operation(operation_id="op1"), _make_operation(operation_id="op2")]
        ui._operations = ops
        ui._renderer._render_operation_select(surface)
        assert ui._proceed_button_rect is not None
        assert ui._back_button_rect is not None
        assert len(ui._op_rects) == 2

    def test_op_rects_populated(self, ui, surface):
        """Each operation should get a rect in _op_rects."""
        ops = [_make_operation(operation_id=f"op{i}") for i in range(3)]
        ui._operations = ops
        ui._renderer._render_operation_select(surface)
        assert len(ui._op_rects) == 3

    def test_selected_operation(self, ui, surface):
        """Selected operation should be highlighted."""
        ops = [_make_operation(operation_id="op1"), _make_operation(operation_id="op2")]
        ui._operations = ops
        ui._selected_op_id = "op2"
        ui._renderer._render_operation_select(surface)
        assert "op2" in ui._op_rects

    def test_hovered_operation(self, ui, surface):
        """Hovered operation should have different styling."""
        ops = [_make_operation(operation_id="op1"), _make_operation(operation_id="op2")]
        ui._operations = ops
        ui._hovered_op_id = "op1"
        ui._renderer._render_operation_select(surface)

    def test_completed_battles_progress(self, ui, surface):
        """Operations with completed battles should show progress."""
        battles = [
            _make_battle(battle_id="b1", completed=True),
            _make_battle(battle_id="b2", completed=False),
        ]
        ops = [_make_operation(operation_id="op1", battles=battles)]
        ui._operations = ops
        ui._renderer._render_operation_select(surface)

    def test_all_battles_completed(self, ui, surface):
        """All battles completed should show full progress in COMPLETED_COLOR."""
        battles = [
            _make_battle(battle_id="b1", completed=True),
            _make_battle(battle_id="b2", completed=True),
        ]
        ops = [_make_operation(operation_id="op1", battles=battles)]
        ui._operations = ops
        ui._renderer._render_operation_select(surface)

    def test_no_operations(self, ui, surface):
        """Empty operations list should not crash."""
        ui._operations = []
        ui._renderer._render_operation_select(surface)
        assert ui._proceed_button_rect is not None

    def test_hovered_proceed_button(self, ui, surface):
        """Hovering proceed button should not crash."""
        ui._operations = [_make_operation()]
        ui._hovered_button = "proceed"
        ui._renderer._render_operation_select(surface)

    def test_hovered_back_button(self, ui, surface):
        """Hovering back button should not crash."""
        ui._operations = [_make_operation()]
        ui._hovered_button = "back"
        ui._renderer._render_operation_select(surface)


class TestRenderBattleSelect:
    """Tests for _render_battle_select method."""

    def test_no_operation_returns_early(self, ui, surface):
        """With no current operation, should render 'No campaign loaded' and return."""
        ui._current_operation = None
        ui._renderer._render_battle_select(surface)
        assert ui._start_button_rect is None
        assert ui._back_button_rect is None

    def test_renders_with_operation(self, ui, surface):
        """Battle select should render with a valid operation and set button rects."""
        op = _make_operation()
        ui._current_operation = op
        ui._renderer._render_battle_select(surface)
        assert ui._start_button_rect is not None
        assert ui._back_button_rect is not None
        assert len(ui._battle_rects) > 0

    def test_battle_rects_populated(self, ui, surface):
        """Each visible battle should get a rect."""
        battles = [_make_battle(battle_id=f"b{i}") for i in range(3)]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._renderer._render_battle_select(surface)
        assert len(ui._battle_rects) == 3

    def test_selected_battle(self, ui, surface):
        """Selected battle should be highlighted."""
        battles = [_make_battle(battle_id="b1"), _make_battle(battle_id="b2")]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._selected_battle_id = "b2"
        ui._renderer._render_battle_select(surface)

    def test_hovered_battle(self, ui, surface):
        """Hovered battle should have different styling."""
        battles = [_make_battle(battle_id="b1"), _make_battle(battle_id="b2")]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._hovered_battle_id = "b1"
        ui._renderer._render_battle_select(surface)

    def test_locked_battle(self, ui, surface):
        """Locked battles should be rendered with different styling."""
        battles = [_make_battle(battle_id="b1", locked=True), _make_battle(battle_id="b2")]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._renderer._render_battle_select(surface)

    def test_completed_battle(self, ui, surface):
        """Completed battles should show [OK] icon."""
        battles = [_make_battle(battle_id="b1", completed=True)]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._renderer._render_battle_select(surface)

    def test_selected_battle_description(self, ui, surface):
        """Selected battle description should be rendered in right panel."""
        battles = [_make_battle(battle_id="b1", description="A fierce battle at the bridge")]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._selected_battle_id = "b1"
        ui._renderer._render_battle_select(surface)

    def test_selected_battle_map_file(self, ui, surface):
        """Selected battle map file should be rendered."""
        battles = [_make_battle(battle_id="b1", map_file="Map003")]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._selected_battle_id = "b1"
        ui._renderer._render_battle_select(surface)

    def test_no_selected_battle_hint(self, ui, surface):
        """When no battle is selected, 'Select a battle' hint should show."""
        battles = [_make_battle(battle_id="b1")]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._selected_battle_id = None
        ui._renderer._render_battle_select(surface)

    def test_operation_description(self, ui, surface):
        """Operation description should be rendered."""
        op = _make_operation(description="A detailed operation description")
        ui._current_operation = op
        ui._renderer._render_battle_select(surface)

    def test_scroll_offset(self, ui, surface):
        """Scroll offset should skip battles from the list."""
        battles = [_make_battle(battle_id=f"b{i}") for i in range(10)]
        op = _make_operation(battles=battles)
        ui._current_operation = op
        ui._scroll_offset = 2
        ui._renderer._render_battle_select(surface)
        assert "b0" not in ui._battle_rects
        assert "b1" not in ui._battle_rects

    def test_hovered_start_button(self, ui, surface):
        """Hovering start button should not crash."""
        op = _make_operation()
        ui._current_operation = op
        ui._hovered_button = "start"
        ui._renderer._render_battle_select(surface)

    def test_hovered_back_button(self, ui, surface):
        """Hovering back button should not crash."""
        op = _make_operation()
        ui._current_operation = op
        ui._hovered_button = "back"
        ui._renderer._render_battle_select(surface)
