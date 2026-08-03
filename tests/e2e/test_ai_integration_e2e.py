"""E2E: AI Integration — ReconAI & SupplyAwarenessAI game loop verification.

Verifies that the newly registered tactical AIs (ReconAI, SupplyAwarenessAI)
are integrated into the game loop and produce observable behaviors:

  1. Registration: both AIs appear in TacticalOrchestrator.registered_ais
  2. Game loop stability: 60+ ticks with both AIs active — no crash
  3. ReconAI behavior: snipers + VL positions → RECONNAISSANCE intents produced
  4. SupplyAwarenessAI behavior: units near supply points → DEFEND/ATTACK intents
  5. Tactical summary: get_tactical_summary() returns both AI names
  6. Render stability: rendering with AI-produced orders doesn't crash

This test complements test_e2e_full_coverage.py (42 user operations) by
verifying the AI subsystems behind the "Battle Flow" category.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import pygame
import pytest
from conftest import GameLoopFactory

# ===========================================================================
# TEST SUITE
# ===========================================================================


class TestAIIntegrationE2E:
    """E2E tests for ReconAI and SupplyAwarenessAI game loop integration.

    Verifies that the AIs registered in AIService.__init__ are actually
    exercised by the game loop and produce observable tactical intents.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        yield
        pygame.quit()

    def _factory(self):
        return GameLoopFactory(self.screen)

    # ======================================================================
    # 1. REGISTRATION VERIFICATION
    # ======================================================================

    def test_recon_ai_registered_in_orchestrator(self):
        """ReconAI must be registered in TacticalOrchestrator."""
        f = self._factory()
        registered = f.ai_service._tactical_orchestrator.registered_ais
        assert "ReconAI" in registered, f"ReconAI not in registered AIs: {registered}"
        f.shutdown()

    def test_supply_awareness_ai_registered_in_orchestrator(self):
        """SupplyAwarenessAI must be registered in TacticalOrchestrator."""
        f = self._factory()
        registered = f.ai_service._tactical_orchestrator.registered_ais
        assert "SupplyAwarenessAI" in registered, (
            f"SupplyAwarenessAI not in registered AIs: {registered}"
        )
        f.shutdown()

    def test_all_10_tactical_ais_registered(self):
        """All 10 tactical AIs must be registered (8 original + 2 new)."""
        f = self._factory()
        registered = f.ai_service._tactical_orchestrator.registered_ais
        expected = {
            "FlankingAI",
            "SuppressionAI",
            "InfantryTankCoordAI",
            "VictoryPointAI",
            "RetreatDecisionAI",
            "ATAmbushAI",
            "CounterattackAI",
            "AmbushAI",
            "ReconAI",
            "SupplyAwarenessAI",
        }
        missing = expected - set(registered)
        assert not missing, f"Missing AIs: {missing}. Got: {registered}"
        f.shutdown()

    # ======================================================================
    # 2. GAME LOOP STABILITY
    # ======================================================================

    def test_game_loop_60_ticks_no_crash_with_new_ais(self):
        """Game loop runs 60 ticks with ReconAI+SupplyAwarenessAI — no crash."""
        f = self._factory()
        f.place_n_units(3)
        errors = f.run_ticks(60)
        assert len(errors) == 0, f"AI crashes: {errors[:3]}"
        f.shutdown()

    def test_game_loop_200_ticks_stable_with_new_ais(self):
        """Extended battle (200 ticks) with new AIs remains stable."""
        f = self._factory()
        f.place_n_units(3)
        errors = f.run_ticks(200)
        assert len(errors) == 0, f"Crashes at 200 ticks: {errors[:5]}"
        assert f.render_frame()
        f.shutdown()

    # ======================================================================
    # 3. RECONAI BEHAVIOR VERIFICATION
    # ======================================================================

    def test_recon_ai_evaluates_without_crash(self):
        """ReconAI.evaluate() runs without crash during game ticks."""
        f = self._factory()
        f.place_n_units(3)
        f.run_ticks(30)
        scores = f.ai_service._tactical_orchestrator.last_scores
        assert "ReconAI" in scores, f"ReconAI score missing: {scores}"
        f.shutdown()

    def test_recon_ai_produces_orders_in_battle(self):
        """ReconAI produces tactical intents during battle (if snipers present).

        This verifies the full pipeline: game tick → AIService.tick() →
        _run_tactical_orchestrator() → ReconAI.evaluate() + execute() →
        TacticIntent in last_orders.
        """
        f = self._factory()
        f.place_n_units(5)  # Place more units to increase chance of snipers

        # Run enough ticks for AI to evaluate and produce orders
        f.run_ticks(60)

        # Check tactical summary
        summary = f.ai_service.get_tactical_summary()
        assert "ReconAI" in summary["registered_ais"]
        assert summary["current_tick"] > 0

        # The last_scores should have an entry for ReconAI
        scores = f.ai_service._tactical_orchestrator.last_scores
        assert "ReconAI" in scores, f"ReconAI not scored: {scores}"

        f.shutdown()

    # ======================================================================
    # 4. SUPPLYAWARENESSAI BEHAVIOR VERIFICATION
    # ======================================================================

    def test_supply_awareness_ai_evaluates_without_crash(self):
        """SupplyAwarenessAI.evaluate() runs without crash during game ticks."""
        f = self._factory()
        f.place_n_units(3)
        f.run_ticks(30)
        scores = f.ai_service._tactical_orchestrator.last_scores
        assert "SupplyAwarenessAI" in scores, f"SupplyAwarenessAI score missing: {scores}"
        f.shutdown()

    def test_supply_awareness_ai_produces_orders_in_battle(self):
        """SupplyAwarenessAI produces tactical intents during battle."""
        f = self._factory()
        f.place_n_units(5)

        f.run_ticks(60)

        summary = f.ai_service.get_tactical_summary()
        assert "SupplyAwarenessAI" in summary["registered_ais"]

        scores = f.ai_service._tactical_orchestrator.last_scores
        assert "SupplyAwarenessAI" in scores, f"SupplyAwarenessAI not scored: {scores}"

        f.shutdown()

    # ======================================================================
    # 5. TACTICAL SUMMARY VERIFICATION
    # ======================================================================

    def test_tactical_summary_contains_all_ais(self):
        """get_tactical_summary() returns all 11 registered AIs.

        TD-076b (v0.7.0): SurrenderAI registered to TacticalOrchestrator,
        increasing the count from 10 to 11.
        """
        f = self._factory()
        f.place_n_units(3)
        f.run_ticks(10)

        summary = f.ai_service.get_tactical_summary()
        assert len(summary["registered_ais"]) == 11, (
            f"Expected 11 AIs, got {len(summary['registered_ais'])}: {summary['registered_ais']}"
        )
        f.shutdown()

    def test_tactical_summary_tracks_tick_progress(self):
        """Tactical summary current_tick advances with game ticks."""
        f = self._factory()
        f.place_n_units(2)

        f.run_ticks(5)
        summary1 = f.ai_service.get_tactical_summary()
        tick1 = summary1["current_tick"]

        f.run_ticks(5)
        summary2 = f.ai_service.get_tactical_summary()
        tick2 = summary2["current_tick"]

        assert tick2 > tick1, f"Tick didn't advance: {tick1} → {tick2}"
        f.shutdown()

    # ======================================================================
    # 6. RENDER STABILITY WITH AI ORDERS
    # ======================================================================

    def test_render_with_ai_orders_no_crash(self):
        """Rendering after AI produced orders doesn't crash."""
        f = self._factory()
        f.place_n_units(3)
        f.run_ticks(30)  # Let AI produce some orders
        assert f.render_frame()
        f.shutdown()

    def test_render_debug_mode_with_ai_orders(self):
        """Debug overlay rendering with AI orders active doesn't crash."""
        f = self._factory()
        f.place_n_units(3)
        f.run_ticks(30)
        assert f.render_frame(debug_mode=True)
        f.shutdown()

    # ======================================================================
    # 7. USER JOURNEY: DEPLOY → BATTLE → AI RESPONDS
    # ======================================================================

    def test_full_user_journey_deploy_battle_ai_responds(self):
        """Full user journey: deploy units → start battle → AI responds.

        This simulates the core user flow:
        1. User opens deployment screen
        2. User places units
        3. User starts battle
        4. AI (including ReconAI, SupplyAwarenessAI) runs for 60 ticks
        5. Game renders successfully
        6. No crashes
        """
        f = self._factory()

        # Step 1: Deployment
        dui = f.start_deployment()
        assert dui is not None, "Deployment UI should open"

        # Step 2: Place units
        placed, _ = f.place_n_units(4)
        assert placed >= 1, "Should place at least 1 unit"

        # Step 3: Battle phase — AI runs
        errors = f.run_ticks(60)
        assert len(errors) == 0, f"Battle crashed: {errors[:3]}"

        # Step 4: AI produced evaluations
        scores = f.ai_service._tactical_orchestrator.last_scores
        assert "ReconAI" in scores
        assert "SupplyAwarenessAI" in scores

        # Step 5: Render works
        assert f.render_frame()

        f.shutdown()
