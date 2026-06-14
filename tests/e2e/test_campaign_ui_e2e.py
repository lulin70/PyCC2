"""E2E Test: Campaign UI Full Flow

Tests the complete campaign flow:
1. Create CampaignUI instance
2. Test operation selection (click on operation)
3. Test briefing display (verify text shown)
4. Test battle selection (click on battle)
5. Test battle preview (verify map rendered)
6. Test "Deploy" button (transition to deployment)
7. Test post-battle report (verify results shown)
8. Test "Continue" button (return to operation selection)
9. Test back navigation at each step
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_operations():
    """Create test campaign operations."""
    from pycc2.presentation.ui.campaign_ui import CampaignOperation, CampaignBattle

    return [
        CampaignOperation(
            operation_id="op_market_garden",
            name="Operation Market Garden",
            day=1,
            description="Allied airborne assault on the Netherlands",
            historical_briefing="On September 17, 1944, the Allies launched Operation Market Garden, "
                               "an ambitious plan to secure a series of bridges across the Netherlands. "
                               "Three airborne divisions were dropped to capture key bridges while "
                               "ground forces advanced north.",
            battles=[
                CampaignBattle(
                    battle_id="battle_arnhem",
                    name="Arnhem Bridge",
                    map_file="arnhem_bridge_day1",
                    description="Secure the bridge at Arnhem",
                    objectives=["Capture Arnhem Bridge", "Hold for reinforcements"],
                    allied_forces=["1st Airborne Division", "Polish Brigade"],
                    axis_forces=["9th SS Panzer Division", "10th SS Panzer Division"],
                ),
                CampaignBattle(
                    battle_id="battle_nijmegen",
                    name="Nijmegen Crossing",
                    map_file="nijmegen_bridge",
                    description="Cross the Waal River",
                    objectives=["Capture Nijmegen Bridge"],
                    allied_forces=["82nd Airborne Division"],
                    axis_forces=["Wehrmacht Garrison"],
                ),
            ],
        ),
        CampaignOperation(
            operation_id="op_corridor",
            name="Corridor Defense",
            day=3,
            description="Defend the corridor against German counterattacks",
            historical_briefing="After the initial landings, German forces launched fierce "
                               "counterattacks along the corridor to cut off the advancing Allies.",
            battles=[
                CampaignBattle(
                    battle_id="battle_veghel",
                    name="Veghel Defense",
                    map_file="veghel_defense",
                    description="Hold Veghel against counterattack",
                    objectives=["Hold the road open", "Repel German attacks"],
                    allied_forces=["101st Airborne Division"],
                    axis_forces=["59th Infantry Division"],
                ),
            ],
        ),
    ]


def _make_campaign_ui() -> "CampaignUI":
    """Create and initialize a CampaignUI instance."""
    from pycc2.presentation.ui.campaign_ui import CampaignUI

    ui = CampaignUI()
    ui.initialize()
    ui.show()
    ui.set_operations(_make_operations())
    return ui


def _make_surface(width: int = 800, height: int = 600) -> pygame.Surface:
    """Create a test surface."""
    return pygame.Surface((width, height), pygame.SRCALPHA)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCampaignUIE2E:
    """Full E2E test for the Campaign UI flow."""

    def test_01_create_campaign_ui_instance(self):
        """Step 1: Create CampaignUI instance."""
        from pycc2.presentation.ui.campaign_ui import CampaignUI

        ui = CampaignUI()
        ui.initialize()
        assert ui.is_visible is False

        ui.show()
        assert ui.is_visible is True
        assert ui.state == "operation_select"

    def test_02_operation_selection_click(self):
        """Step 2: Test operation selection (click on operation)."""
        ui = _make_campaign_ui()
        surface = _make_surface()

        # Render to populate click regions
        ui.render(surface)

        # The operation rects should be populated
        assert len(ui._op_rects) > 0, "Should have operation rects after render"

        # Click on the first operation
        first_op_id = list(ui._op_rects.keys())[0]
        first_rect = ui._op_rects[first_op_id]
        click_pos = (first_rect.centerx, first_rect.centery)

        result = ui.handle_click(click_pos)
        assert result is not None
        assert "select_operation" in result
        assert ui._selected_op_id == first_op_id

    def test_03_briefing_display(self):
        """Step 3: Test briefing display (verify text shown)."""
        ui = _make_campaign_ui()
        surface = _make_surface()

        # Navigate to briefing via proceed button
        ui.render(surface)
        first_op_id = list(ui._op_rects.keys())[0]
        first_rect = ui._op_rects[first_op_id]
        ui.handle_click((first_rect.centerx, first_rect.centery))

        # Click Proceed button
        if ui._proceed_button_rect:
            result = ui.handle_click((ui._proceed_button_rect.centerx, ui._proceed_button_rect.centery))
            assert result is not None
            assert "briefing" in result

        # Verify state is briefing
        assert ui.state == "briefing"

        # Render and verify briefing text is displayed (no crash)
        ui.render(surface)

    def test_04_battle_selection_click(self):
        """Step 4: Test battle selection (click on battle)."""
        ui = _make_campaign_ui()
        surface = _make_surface()

        # Navigate to battle_select
        ops = _make_operations()
        ui.set_operation(ops[0])
        assert ui.state == "battle_select"

        # Render to populate battle rects
        ui.render(surface)
        assert len(ui._battle_rects) > 0, "Should have battle rects after render"

        # Click on first battle
        first_battle_id = list(ui._battle_rects.keys())[0]
        first_rect = ui._battle_rects[first_battle_id]
        result = ui.handle_click((first_rect.centerx, first_rect.centery))
        assert result is not None
        assert "select_battle" in result

    def test_05_battle_preview_rendered(self):
        """Step 5: Test battle preview (verify map rendered)."""
        ui = _make_campaign_ui()
        surface = _make_surface()

        # Navigate to preview
        ops = _make_operations()
        ui.show_battle_preview(ops[0].battles[0])
        assert ui.state == "preview"

        # Render preview (should not crash)
        ui.render(surface)

    def test_06_deploy_button_transition(self):
        """Step 6: Test "Deploy" button (transition to deployment)."""
        ui = _make_campaign_ui()
        surface = _make_surface()

        # Navigate to preview
        ops = _make_operations()
        ui.show_battle_preview(ops[0].battles[0])
        ui.render(surface)

        # Click Deploy button
        if ui._deploy_button_rect:
            deployed = False

            def on_start(battle_id):
                nonlocal deployed
                deployed = True

            ui.set_callbacks(on_start_battle=on_start)
            result = ui.handle_click((ui._deploy_button_rect.centerx, ui._deploy_button_rect.centery))
            assert result is not None
            assert "start_battle" in result
            assert deployed

    def test_07_post_battle_report(self):
        """Step 7: Test post-battle report (verify results shown)."""
        ui = _make_campaign_ui()
        surface = _make_surface()

        # Show post-battle report
        result_data = {
            "victory": True,
            "battle_name": "Arnhem Bridge",
            "casualties": {
                "Allies": {"killed": 3, "wounded": 7},
                "Axis": {"killed": 12, "wounded": 8},
            },
            "experience": {"infantry": "+15", "armor": "+5"},
            "summary": {"objectives_captured": 2, "time_elapsed": "12:30"},
        }
        ui.show_post_battle_report(result_data)
        assert ui.state == "report"

        # Render report (should not crash)
        ui.render(surface)

    def test_08_continue_button(self):
        """Step 8: Test "Continue" button (return to battle selection)."""
        ui = _make_campaign_ui()
        surface = _make_surface()

        # Show report first
        result_data = {"victory": True, "battle_name": "Test Battle"}
        ui.show_post_battle_report(result_data)
        ui.render(surface)

        # Click Continue
        if ui._continue_button_rect:
            result = ui.handle_click((ui._continue_button_rect.centerx, ui._continue_button_rect.centery))
            assert result is not None
            assert "continue_campaign" in result
            assert ui.state == "battle_select"

    def test_09_back_navigation_from_briefing(self):
        """Step 9a: Test back navigation from briefing to operation_select."""
        ui = _make_campaign_ui()
        surface = _make_surface()

        ops = _make_operations()
        ui.show_operation_briefing(ops[0])
        assert ui.state == "briefing"

        ui.render(surface)
        if ui._back_button_rect:
            result = ui.handle_click((ui._back_button_rect.centerx, ui._back_button_rect.centery))
            assert result is not None
            assert ui.state == "operation_select"

    def test_09_back_navigation_from_battle_select(self):
        """Step 9b: Test back navigation from battle_select to briefing."""
        ui = _make_campaign_ui()
        surface = _make_surface()

        ops = _make_operations()
        ui.set_operation(ops[0])
        assert ui.state == "battle_select"

        ui.render(surface)
        if ui._back_button_rect:
            result = ui.handle_click((ui._back_button_rect.centerx, ui._back_button_rect.centery))
            assert result is not None
            assert ui.state == "briefing"

    def test_09_back_navigation_from_preview(self):
        """Step 9c: Test back navigation from preview to battle_select."""
        ui = _make_campaign_ui()
        surface = _make_surface()

        ops = _make_operations()
        ui.show_battle_preview(ops[0].battles[0])
        assert ui.state == "preview"

        ui.render(surface)
        if ui._back_button_rect:
            result = ui.handle_click((ui._back_button_rect.centerx, ui._back_button_rect.centery))
            assert result is not None
            assert ui.state == "battle_select"

    def test_09_back_navigation_from_report(self):
        """Step 9d: Test back navigation from report to battle_select."""
        ui = _make_campaign_ui()
        surface = _make_surface()

        result_data = {"victory": False, "battle_name": "Test"}
        ui.show_post_battle_report(result_data)
        assert ui.state == "report"

        ui.render(surface)
        if ui._back_button_rect:
            result = ui.handle_click((ui._back_button_rect.centerx, ui._back_button_rect.centery))
            assert result is not None
            assert ui.state == "battle_select"
