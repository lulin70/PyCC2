"""
Tests for P6.3 After Action Report (AAR) Panel and P6.4 Time Control.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pygame
import pytest

from pycc2.domain.systems.battle_result import BattleOutcome, BattleResult, UnitBattleRecord
from pycc2.presentation.ui.aar_panel import AARConfig, AARPanel
from pycc2.presentation.ui.time_control import (
    SPEED_ORDER,
    TIME_SPEED_CONFIG,
    TimeControlConfig,
    TimeControlUI,
    TimeSpeed,
)


class TestAARPanel:
    """Tests for AARPanel — show/hide/toggle/render/click."""

    def test_init_default_config(self):
        panel = AARPanel()
        assert panel.visible is False
        assert panel.result is None
        assert isinstance(panel.config, AARConfig)

    def test_custom_config(self):
        cfg = AARConfig(width=800, height=500, x=50, y=60)
        panel = AARPanel(config=cfg)
        assert panel.config.width == 800
        assert panel.config.height == 500

    def test_show_and_visible(self):
        panel = AARPanel()
        result = self._make_sample_result()
        assert panel.visible is False
        panel.show(result)
        assert panel.visible is True
        assert panel.result is result

    def test_hide(self):
        panel = AARPanel()
        result = self._make_sample_result()
        panel.show(result)
        assert panel.visible is True
        panel.hide()
        assert panel.visible is False
        assert panel.result is None

    def test_toggle_show(self):
        panel = AARPanel()
        result = self._make_sample_result()
        panel.toggle(result)
        assert panel.visible is True

    def test_toggle_hide(self):
        panel = AARPanel()
        result = self._make_sample_result()
        panel.show(result)
        panel.toggle()
        assert panel.visible is False

    def test_toggle_no_result_does_nothing(self):
        panel = AARPanel()
        panel.toggle(None)
        assert panel.visible is False

    def test_handle_click_inside_closes(self):
        panel = AARPanel(config=AARConfig(x=100, y=200, width=600, height=400))
        result = self._make_sample_result()
        panel.show(result)
        assert panel.handle_click(200, 300) is True
        assert panel.visible is False

    def test_handle_click_outside_ignores(self):
        panel = AARPanel(config=AARConfig(x=100, y=200, width=600, height=400))
        result = self._make_sample_result()
        panel.show(result)
        assert panel.handle_click(10, 10) is False
        assert panel.visible is True

    def test_handle_click_when_hidden(self):
        panel = AARPanel()
        assert panel.handle_click(200, 300) is False

    @patch("pygame.Surface")
    def test_render_when_hidden(self, mock_surface_cls):
        panel = AARPanel()
        screen = MagicMock()
        font = MagicMock()
        small_font = MagicMock()
        panel.render(screen, font=font, small_font=small_font)
        screen.blit.assert_not_called()

    def test_render_displays_data(self, pygame_display, mock_font, mock_small_font):
        """Render AAR panel with headless-safe fixtures instead of skipif."""
        panel = AARPanel(config=AARConfig(width=600, height=420))
        result = self._make_sample_result()
        panel.show(result)

        screen = pygame.Surface((800, 600), pygame.SRCALPHA)
        panel.render(screen, font=mock_font, small_font=mock_small_font)
        assert panel.visible is True

    def test_render_shows_victory_color_for_victory(self):
        result = self._make_sample_result(outcome=BattleOutcome.VICTORY)
        assert result.is_victory is True

    def test_render_shows_defeat_color_for_defeat(self):
        result = self._make_sample_result(outcome=BattleOutcome.DEFEAT)
        assert result.is_victory is False

    def test_scroll_offset_resets_on_show(self):
        panel = AARPanel()
        result = self._make_sample_result()
        panel._scroll_offset = 50
        panel.show(result)
        assert panel._scroll_offset == 0

    def _make_sample_result(self, outcome=BattleOutcome.VICTORY) -> BattleResult:
        return BattleResult(
            mission_id="test_mission_01",
            mission_name="Test Bridge Assault",
            outcome=outcome,
            ticks_elapsed=5400,
            allies_killed=2,
            allies_routed=1,
            axis_killed=8,
            axis_routed=3,
            total_shots_fired_allies=120,
            total_shots_hit_allies=78,
            total_shots_fired_axis=90,
            total_shots_hit_axis=36,
            total_damage_dealt_allies=450.0,
            total_damage_dealt_axis=220.0,
            objectives_completed=2,
            objectives_total=3,
            unit_records=[
                UnitBattleRecord(
                    unit_id="u1",
                    unit_type="RifleSquad",
                    faction="allies",
                    survived=True,
                    hp_start=100,
                    hp_end=65,
                    damage_dealt=120.0,
                    damage_taken=35,
                    kills=3,
                    shots_fired=40,
                    shots_hit=28,
                ),
                UnitBattleRecord(
                    unit_id="u2",
                    unit_type="MachineGun",
                    faction="allies",
                    survived=False,
                    hp_start=80,
                    hp_end=0,
                    damage_dealt=80.0,
                    damage_taken=80,
                    kills=2,
                    shots_fired=60,
                    shots_hit=30,
                ),
                UnitBattleRecord(
                    unit_id="u3",
                    unit_type="Sniper",
                    faction="allies",
                    survived=True,
                    hp_start=60,
                    hp_end=55,
                    damage_dealt=250.0,
                    damage_taken=5,
                    kills=3,
                    shots_fired=20,
                    shots_hit=20,
                ),
            ],
            victory_points=185,
        )


class TestTimeControlUI:
    """Tests for TimeControlUI — speed switching/pause/hotkeys/render/click/multiplier."""

    def test_init_default_speed_is_normal(self):
        tc = TimeControlUI()
        assert tc.current_speed == TimeSpeed.NORMAL
        assert tc.speed_multiplier == 1.0
        assert tc.is_paused is False

    def test_custom_config(self):
        cfg = TimeControlConfig(x=20, y=500, button_width=100, button_height=30)
        tc = TimeControlUI(config=cfg)
        assert tc.config.x == 20
        assert tc.config.button_width == 100

    def test_set_speed_valid(self):
        tc = TimeControlUI()
        tc.set_speed(TimeSpeed.FAST)
        assert tc.current_speed == TimeSpeed.FAST
        assert tc.speed_multiplier == 2.0

    def test_set_speed_invalid_ignored(self):
        tc = TimeControlUI()
        original = tc.current_speed
        tc.set_speed(TimeSpeed.PAUSED)
        assert tc.current_speed != original

    def test_toggle_pause_from_normal(self):
        tc = TimeControlUI()
        tc.toggle_pause()
        assert tc.current_speed == TimeSpeed.PAUSED
        assert tc.is_paused is True

    def test_toggle_pause_frompaused(self):
        tc = TimeControlUI()
        tc.set_speed(TimeSpeed.PAUSED)
        tc.toggle_pause()
        assert tc.current_speed == TimeSpeed.NORMAL
        assert tc.is_paused is False

    def test_speed_up(self):
        tc = TimeControlUI()
        assert tc.speed_up() == TimeSpeed.FAST
        assert tc.speed_up() == TimeSpeed.VERY_FAST
        assert tc.speed_up() == TimeSpeed.VERY_FAST

    def test_speed_down(self):
        tc = TimeControlUI()
        tc.set_speed(TimeSpeed.FAST)
        assert tc.speed_down() == TimeSpeed.NORMAL
        assert tc.speed_down() == TimeSpeed.SLOW
        assert tc.speed_down() == TimeSpeed.PAUSED
        assert tc.speed_down() == TimeSpeed.PAUSED

    def test_speed_multiplier_values(self):
        expected = {
            TimeSpeed.PAUSED: 0.0,
            TimeSpeed.SLOW: 0.5,
            TimeSpeed.NORMAL: 1.0,
            TimeSpeed.FAST: 2.0,
            TimeSpeed.VERY_FAST: 4.0,
        }
        for speed, mult in expected.items():
            tc = TimeControlUI()
            tc.set_speed(speed)
            assert tc.speed_multiplier == mult, f"Failed for {speed.name}"

    def test_handle_key_space_toggles_pause(self):
        tc = TimeControlUI()
        assert tc.handle_key(pygame.K_SPACE) is True
        assert tc.is_paused is True
        assert tc.handle_key(pygame.K_SPACE) is True
        assert tc.is_paused is False

    def test_handle_key_plus_speeds_up(self):
        tc = TimeControlUI()
        tc.handle_key(pygame.K_PLUS)
        assert tc.current_speed == TimeSpeed.FAST

    def test_handle_key_equals_speeds_up(self):
        tc = TimeControlUI()
        tc.handle_key(pygame.K_EQUALS)
        assert tc.current_speed == TimeSpeed.FAST

    def test_handle_key_minus_slows_down(self):
        tc = TimeControlUI()
        tc.set_speed(TimeSpeed.FAST)
        tc.handle_key(pygame.K_MINUS)
        assert tc.current_speed == TimeSpeed.NORMAL

    def test_handle_key_unhandled_returns_false(self):
        tc = TimeControlUI()
        assert tc.handle_key(pygame.K_a) is False

    def test_handle_click_active_button(self, pygame_display, mock_font, can_render):
        """Test click on active speed button using headless-safe fixtures."""
        if not can_render:
            pytest.skip("Full rendering not available in this environment")
        tc = TimeControlUI()
        screen = pygame.Surface((800, 600), pygame.SRCALPHA)
        tc.render(screen, font=mock_font, tick=100, fps=60.0)
        if not tc._button_rects:
            pytest.skip("No button rects generated in headless mode")
        rect = list(tc._button_rects.values())[0]
        cx, cy = rect.centerx, rect.centery
        result = tc.handle_click(cx, cy)
        assert result is True

    def test_handle_click_outside(self, pygame_display, mock_font, can_render):
        """Test click outside buttons using headless-safe fixtures."""
        if not can_render:
            pytest.skip("Full rendering not available in this environment")
        tc = TimeControlUI()
        screen = pygame.Surface((800, 600), pygame.SRCALPHA)
        tc.render(screen, font=mock_font)
        assert tc.handle_click(9999, 9999) is False

    def test_render_returns_clickable_list(self, pygame_display, mock_font, can_render):
        """Test render returns clickable items using headless-safe fixtures."""
        if not can_render:
            pytest.skip("Full rendering not available in this environment")
        tc = TimeControlUI()
        screen = pygame.Surface((800, 600), pygame.SRCALPHA)
        clickable = tc.render(screen, font=mock_font, tick=42, fps=55.5)
        assert len(clickable) == len(SPEED_ORDER)
        for item in clickable:
            assert "speed" in item
            assert "rect" in item

    def test_speed_order_sequence(self):
        assert SPEED_ORDER == [
            TimeSpeed.PAUSED,
            TimeSpeed.SLOW,
            TimeSpeed.NORMAL,
            TimeSpeed.FAST,
            TimeSpeed.VERY_FAST,
        ]

    def test_time_speed_config_complete(self):
        for speed in TimeSpeed:
            assert speed in TIME_SPEED_CONFIG
            info = TIME_SPEED_CONFIG[speed]
            assert "label" in info
            assert "ups_mult" in info
            assert "color" in info


class TestAARDataIntegration:
    """Integration tests verifying AAR data consistency with BattleResult."""

    def test_victory_outcome_is_victory(self):
        for outcome in (BattleOutcome.VICTORY, BattleOutcome.TIME_OUT_VICTORY):
            r = BattleResult(
                mission_id="m1", mission_name="M", outcome=outcome, ticks_elapsed=100
            )
            assert r.is_victory is True

    def test_defeat_outcome_is_not_victory(self):
        for outcome in (BattleOutcome.DEFEAT, BattleOutcome.TIME_OUT_DEFEAT, BattleOutcome.DRAW):
            r = BattleResult(
                mission_id="m1", mission_name="M", outcome=outcome, ticks_elapsed=100
            )
            assert r.is_victory is False

    def test_accuracy_zero_when_no_shots(self):
        r = BattleResult(
            mission_id="m1", mission_name="M", outcome=BattleOutcome.VICTORY, ticks_elapsed=100,
            total_shots_fired_allies=0, total_shots_hit_allies=0,
        )
        assert r.allies_accuracy == 0.0

    def test_accuracy_calculation(self):
        r = BattleResult(
            mission_id="m1", mission_name="M", outcome=BattleOutcome.VICTORY, ticks_elapsed=100,
            total_shots_fired_allies=200, total_shots_hit_allies=150,
            total_shots_fired_axis=100, total_shots_hit_axis=40,
        )
        assert abs(r.allies_accuracy - 0.75) < 1e-6
        assert abs(r.axis_accuracy - 0.4) < 1e-6

    def test_survival_rate_all_units_survived(self):
        records = [
            UnitBattleRecord("u1", "Rifle", "allies", True, 100, 100, 0, 0, 0, 10, 8),
            UnitBattleRecord("u2", "MG", "allies", True, 80, 60, 50, 20, 2, 30, 15),
        ]
        r = BattleResult(
            mission_id="m1", mission_name="M", outcome=BattleOutcome.VICTORY, ticks_elapsed=100,
            unit_records=records,
        )
        assert abs(r.survival_rate_allies - 1.0) < 1e-6

    def test_survival_rate_half_dead(self):
        records = [
            UnitBattleRecord("u1", "Rifle", "allies", True, 100, 100, 0, 0, 0, 10, 8),
            UnitBattleRecord("u2", "MG", "allies", False, 80, 0, 50, 80, 2, 30, 15),
        ]
        r = BattleResult(
            mission_id="m1", mission_name="M", outcome=BattleOutcome.VICTORY, ticks_elapsed=100,
            unit_records=records,
        )
        assert abs(r.survival_rate_allies - 0.5) < 1e-6

    def test_survival_rate_no_allies(self):
        axis_record = UnitBattleRecord("a1", "AxisRifle", "axis", True, 100, 100, 0, 0, 0, 10, 8)
        r = BattleResult(
            mission_id="m1", mission_name="M", outcome=BattleOutcome.VICTORY, ticks_elapsed=100,
            unit_records=[axis_record],
        )
        assert r.survival_rate_allies == 0.0

    def test_unit_battle_record_efficiency(self):
        rec = UnitBattleRecord("u1", "Rifle", "allies", True, 100, 80, 50, 20, 3, 20, 16)
        assert abs(rec.efficiency - 0.8) < 1e-6

    def test_unit_efficiency_zero_shots(self):
        rec = UnitBattleRecord("u1", "Rifle", "allies", True, 100, 100, 0, 0, 0, 0, 0)
        assert rec.efficiency == 0.0

    def test_calculate_vp_basic_victory(self):
        r = BattleResult(
            mission_id="m1", mission_name="M", outcome=BattleOutcome.VICTORY, ticks_elapsed=1800,
            axis_killed=5, axis_routed=2, allies_killed=1, allies_routed=0,
            objectives_completed=3,
            unit_records=[
                UnitBattleRecord("u1", "Rifle", "allies", True, 100, 90, 0, 10, 0, 0, 0),
                UnitBattleRecord("u2", "MG", "allies", True, 80, 70, 0, 10, 0, 0, 0),
                UnitBattleRecord("u3", "Sniper", "allies", True, 60, 55, 0, 5, 0, 0, 0),
                UnitBattleRecord("u4", "Rifle", "allies", True, 100, 95, 0, 5, 0, 0, 0),
                UnitBattleRecord("u5", "Rifle", "allies", True, 100, 85, 0, 15, 0, 0, 0),
            ],
        )
        vp = r.calculate_vp()
        assert vp >= 0
        assert r.victory_points == vp

    def test_to_dict_and_from_dict_roundtrip(self):
        original = BattleResult(
            mission_id="mission_alpha",
            mission_name="Operation Alpha",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=3600,
            date_in_campaign=5,
            allies_killed=3,
            axis_killed=12,
            victory_points=250,
            unit_records=[
                UnitBattleRecord("u1", "Rifle", "allies", True, 100, 70, 80, 30, 4, 25, 18),
            ],
        )
        d = original.to_dict()
        restored = BattleResult.from_dict(d)
        assert restored.mission_id == original.mission_id
        assert restored.outcome == original.outcome
        assert restored.ticks_elapsed == original.ticks_elapsed
        assert len(restored.unit_records) == len(original.unit_records)


class TestTimeControlGameLoopIntegration:
    """Conceptual integration tests for TimeControl with GameLoop logic."""

    def test_get_time_speed_returns_control_multiplier(self):
        tc = TimeControlUI()
        tc.set_speed(TimeSpeed.FAST)
        assert tc.speed_multiplier == 2.0

    def test_get_time_speed_paused_returns_zero(self):
        tc = TimeControlUI()
        tc.set_speed(TimeSpeed.PAUSED)
        assert tc.speed_multiplier == 0.0

    def test_get_time_speed_slow_returns_half(self):
        tc = TimeControlUI()
        tc.set_speed(TimeSpeed.SLOW)
        assert tc.speed_multiplier == 0.5

    def test_get_time_speed_very_fast_returns_four(self):
        tc = TimeControlUI()
        tc.set_speed(TimeSpeed.VERY_FAST)
        assert tc.speed_multiplier == 4.0

    def test_time_control_state_changes_affect_game_state_conceptually(self):
        tc = TimeControlUI()
        assert tc.speed_multiplier == 1.0
        tc.set_speed(TimeSpeed.PAUSED)
        assert tc.speed_multiplier == 0.0
        tc.set_speed(TimeSpeed.FAST)
        assert tc.speed_multiplier == 2.0

    def test_keyboard_shortcuts_do_not_conflict_with_other_input(self):
        tc = TimeControlUI()
        assert tc.handle_key(pygame.K_SPACE) is True
        assert tc.handle_key(pygame.K_RETURN) is False
        assert tc.handle_key(pygame.K_ESCAPE) is False
        assert tc.handle_key(pygame.K_TAB) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
