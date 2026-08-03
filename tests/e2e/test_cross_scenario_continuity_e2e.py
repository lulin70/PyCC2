"""P2 E2E: Cross-scenario continuity — full user journey integrity.

Validates that the full user journey (menu → deployment → battle → save →
load → continue battle → post-battle → campaign progression) maintains
state continuity without crashes or data loss.

Covers scenarios not exercised by existing E2E tests:
  - Full journey menu→deployment→battle in one test (existing tests cover
    each phase in isolation).
  - Save during battle → load → verify state restored (real quick_save/
    quick_load via GameLoop._save_controller, not just SecureSaveManager).
  - Load → continue battle (run_ticks after load, state advances).
  - Post-battle screen rendering (show_post_battle=True path in
    RenderPipeline._render_post_battle_screen).
  - Campaign progression between battles (Day1 → Day2 via
    CampaignState.advance_day, with battle history recorded).

Uses the real GameLoop (assembled via conftest.GameLoopFactory) — no Mock
of domain objects. Save/load isolation via tmp_path + stable HMAC key.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import pygame
import pytest
from conftest import EventInjector, GameLoopFactory  # noqa: F401

from pycc2.domain.systems.battle_result import BattleOutcome, BattleResult
from pycc2.domain.systems.campaign_state import (
    CampaignState,
    OperationPhase,
)
from pycc2.domain.systems.victory_conditions import GameResult
from pycc2.infrastructure.save_system import SecureSaveManager

# Stable HMAC key so save/load work across the test's save/load cycle.
# 32+ bytes (SecureSaveManager rejects shorter keys).
_STABLE_HMAC_KEY = "pycc2-e2e-cross-scenario-hmac-key-0123456789abcdef"


# ---------------------------------------------------------------------------
# P2 E2E: Cross-scenario continuity
# ---------------------------------------------------------------------------


class TestCrossScenarioContinuityE2E:
    """Cross-scenario continuity — full journey state integrity."""

    @pytest.fixture(autouse=True)
    def pygame_env(self):
        """Initialize pygame headless with a 1280x720 screen."""
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        yield
        pygame.quit()

    @pytest.fixture
    def factory(self):
        """Assemble a real GameLoop via GameLoopFactory, with 3 units placed."""
        f = GameLoopFactory(self.screen)
        f.start_deployment()
        f.place_n_units(3)
        yield f
        f.shutdown()

    @pytest.fixture
    def save_manager(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SecureSaveManager:
        """tmp_path-isolated SecureSaveManager with a stable HMAC key.

        Wired into the GameLoop's _save_controller so quick_save/quick_load
        route through the real SaveController → SecureSaveManager pipeline.
        """
        monkeypatch.setenv("PYCC2_SAVE_HMAC_KEY", _STABLE_HMAC_KEY)
        mgr = SecureSaveManager(base_dir=tmp_path)
        return mgr

    # ------------------------------------------------------------------
    # 1. Full journey: menu (deployment) → battle, no crash
    # ------------------------------------------------------------------

    def test_full_journey_menu_to_battle(self, factory: GameLoopFactory) -> None:
        """Full journey: deployment screen → place units → battle, no crash.

        Verifies the phase transition from deployment (the pre-battle
        "menu" where the user places units) into the battle phase,
        followed by 60 ticks of battle simulation and a render frame.
        """
        # start_deployment + place_n_units already done in the fixture
        assert factory.game_loop.deployment_phase_active is False, (
            "Deployment should be complete (transitioned to battle)"
        )
        assert len(factory.state.units) > 0, "Battle phase should have units"

        # Run battle ticks
        errors = factory.run_ticks(60, dt=0.1)
        assert errors == [], f"Battle phase had {len(errors)} errors: {errors[:3]}"

        # Render a battle frame
        assert factory.render_frame() is True, "Battle frame should render"

    # ------------------------------------------------------------------
    # 2. Save during battle → load → state restored
    # ------------------------------------------------------------------

    def test_save_during_battle_then_load(
        self,
        factory: GameLoopFactory,
        save_manager: SecureSaveManager,
    ) -> None:
        """Save during battle → load → state.tick restored to saved value.

        Routes through the real GameLoop.quick_save / quick_load (which
        delegate to SaveController → SecureSaveManager) to verify the
        full save/load pipeline end-to-end.
        """
        factory.game_loop._save_controller.save_manager = save_manager

        # Run ticks to advance state, then save
        factory.run_ticks(30, dt=0.1)
        saved_tick = factory.state.tick
        assert factory.game_loop.quick_save(0) is True, "quick_save should succeed"

        # Verify save file exists on disk
        slot_file = save_manager._slot_path(0)
        assert slot_file.exists(), "Save file should exist after quick_save"

        # Run more ticks (state diverges from saved)
        factory.run_ticks(20, dt=0.1)
        assert factory.state.tick == saved_tick + 20, "Tick should advance after save"

        # Load → state restored to saved tick
        assert factory.game_loop.quick_load(0) is True, "quick_load should succeed"
        assert factory.state.tick == saved_tick, (
            f"After load, tick should be restored to {saved_tick}, got {factory.state.tick}"
        )
        assert len(factory.state.units) > 0, "Units should be restored after load"

    # ------------------------------------------------------------------
    # 3. Load → continue battle (run_ticks after load)
    # ------------------------------------------------------------------

    def test_load_then_continue_battle(
        self,
        factory: GameLoopFactory,
        save_manager: SecureSaveManager,
    ) -> None:
        """After loading, battle continues without crash and state advances.

        Guards against a regression where loading leaves the GameLoop in
        an inconsistent state (e.g., stale unit animators, broken combat
        director references) that would crash subsequent ticks.
        """
        factory.game_loop._save_controller.save_manager = save_manager

        factory.run_ticks(30, dt=0.1)
        assert factory.game_loop.quick_save(0) is True

        # Load restores state
        assert factory.game_loop.quick_load(0) is True
        tick_after_load = factory.state.tick

        # Continue battle: run_ticks should not crash and tick should advance
        errors = factory.run_ticks(30, dt=0.1)
        assert errors == [], (
            f"Post-load run_ticks should not error, got {len(errors)}: {errors[:3]}"
        )
        assert factory.state.tick == tick_after_load + 30, (
            "Tick should advance by 30 after load + run_ticks"
        )

        # Render should still work after load + continue
        assert factory.render_frame() is True, "Render should work after load + continue"

    # ------------------------------------------------------------------
    # 4. Battle end → post-battle screen renders
    # ------------------------------------------------------------------

    def test_battle_end_to_post_battle_screen(self, factory: GameLoopFactory) -> None:
        """Battle end → post-battle screen renders without crash.

        Exercises the RenderPipeline._render_post_battle_screen path by
        calling render_frame with show_post_battle=True and a real
        BattleResult object as game_result. This is the screen the user
        sees after a battle concludes (victory/defeat banner + stats).
        """
        factory.run_ticks(30, dt=0.1)

        # GameResult is the enum the render pipeline expects (checks
        # result.name == "ALLIES_VICTORY" / "AXIS_VICTORY" for the banner).
        game_result = GameResult.ALLIES_VICTORY

        # Render the post-battle screen — should not crash
        result = factory.render_frame(
            show_post_battle=True,
            game_result=game_result,
            battle_stats=None,
        )
        assert result is True, "render_frame with show_post_battle=True should succeed (no crash)"

    # ------------------------------------------------------------------
    # 5. Campaign progression between battles (Day1 → Day2)
    # ------------------------------------------------------------------

    def test_campaign_progression_between_battles(self) -> None:
        """Campaign progresses between battles: Day1 battle → Day2 start.

        Uses the real CampaignState (the heart of the CC2 campaign system)
        to verify that recording a Day 1 battle and advancing the day
        transitions the campaign to Day 2 with correct aggregate stats.
        """
        campaign = CampaignState.create_default()
        assert campaign.current_day == OperationPhase.DAY_1_SEPT17, (
            "Campaign should start on Day 1 (Sept 17)"
        )
        initial_battles = campaign.total_battles_played

        # Record a Day 1 battle (victory)
        day1_battle = BattleResult(
            mission_id="day1_son_bridge",
            mission_name="Day 1 — Son Bridge",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=1800,
            date_in_campaign=1,
        )
        day1_battle.calculate_vp()
        campaign.record_battle(day1_battle)

        assert campaign.total_battles_played == initial_battles + 1, (
            "total_battles_played should increment after recording a battle"
        )
        assert len(campaign.battle_history) == 1, "battle_history should have 1 entry"
        assert campaign.battle_history[0].is_victory, "Recorded battle should be a victory"

        # Advance to Day 2
        campaign.advance_day()
        assert campaign.current_day == OperationPhase.DAY_2_SEPT18, (
            f"Campaign should advance to Day 2 (Sept 18), got {campaign.current_day}"
        )
        # Enemy strength escalates across days
        assert campaign.enemy_strength_modifier > 1.0, (
            "Enemy strength modifier should escalate after advancing a day"
        )

        # Day 2 battle can be recorded (campaign continues accepting battles)
        day2_battle = BattleResult(
            mission_id="day2_veghel_bridge",
            mission_name="Day 2 — Veghel Bridge",
            outcome=BattleOutcome.VICTORY,
            ticks_elapsed=2100,
            date_in_campaign=2,
        )
        day2_battle.calculate_vp()
        campaign.record_battle(day2_battle)

        assert campaign.total_battles_played == initial_battles + 2, (
            "total_battles_played should be 2 after Day 2 battle"
        )
        assert campaign.current_battle_number == 2, (
            "current_battle_number should be 2 after two battles"
        )
        assert campaign.campaign_outcome == "ongoing", (
            "Campaign should still be ongoing after 2 battles (not all bridges captured)"
        )
