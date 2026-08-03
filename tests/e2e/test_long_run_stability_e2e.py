"""P2 E2E: Long-run stability — extends test_game_run_60s_e2e.py beyond 60s.

Existing E2E coverage only runs 60 simulated seconds (1800 ticks). This
module validates that the GameLoop remains stable over a 5-minute simulated
run, with no crashes, no significant memory growth, correct tick advancement,
stable rendering, and no error accumulation.

Long-run strategy (per task constraint: < 30s real time per test):
  - 5-minute simulation uses dt=0.1 (3x standard LOGIC_DT) so 3000 ticks
    represent 300 seconds of simulated time. This keeps real run time ~10s
    while exercising the same code paths as a real 5-minute session.
  - Ticks are batched in 1000-tick chunks to avoid pytest-timeout triggers.
  - Memory growth measured via tracemalloc with a generous 5 MiB threshold
    to avoid flakiness from pygame internal caches.

Uses the real GameLoop (assembled via conftest.GameLoopFactory) — no Mock.
"""

from __future__ import annotations

import os
import tracemalloc

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import pygame
import pytest
from conftest import EventInjector, GameLoopFactory  # noqa: F401

# Long-run simulation parameters:
#   5 min simulated = 300 s ; dt=0.1 → 3000 ticks represent 5 min.
#   Batched in 1000-tick chunks to stay well under pytest-timeout.
SIM_DT = 0.1
SIM_5MIN_TICKS = 3000
BATCH_SIZE = 1000

# Memory growth threshold (bytes). 5 MiB is generous: it catches leaks that
# would compound over a real 5-min session while tolerating pygame cache
# warming during the first 1000 ticks.
MEM_GROWTH_THRESHOLD = 5 * 1024 * 1024


# ---------------------------------------------------------------------------
# P2 E2E: Long-run stability
# ---------------------------------------------------------------------------


class TestLongRunStabilityE2E:
    """Long-run stability E2E — extends coverage beyond the existing 60s test."""

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

    def test_long_run_5min_no_crash(self, factory: GameLoopFactory) -> None:
        """5-minute simulated run (3000 ticks @ dt=0.1) does not crash.

        Batches 3000 ticks in 3 chunks of 1000 to stay under pytest-timeout.
        Verifies the GameLoop survives the full run and state remains valid.
        """
        total_errors: list = []
        for batch in range(0, SIM_5MIN_TICKS, BATCH_SIZE):
            errors = factory.run_ticks(BATCH_SIZE, dt=SIM_DT)
            total_errors.extend(errors)

        # GameLoop did not crash: state still valid
        assert factory.state.game_map is not None, "Game map should survive long run"
        assert len(factory.state.units) > 0, "Units should survive long run"
        assert factory.state.tick == SIM_5MIN_TICKS, (
            f"Tick should advance to {SIM_5MIN_TICKS}, got {factory.state.tick}"
        )

    def test_long_run_no_memory_growth(self, factory: GameLoopFactory) -> None:
        """Long-run (1500 ticks) does not produce significant memory growth.

        Uses tracemalloc to compare traced memory before and after the run.
        Threshold is 5 MiB — a real leak (e.g., appending to an unbounded
        list each tick) would far exceed this over 1500 ticks.
        """
        tracemalloc.start()
        # Warm up: let pygame initialize caches outside the measurement window
        factory.run_ticks(60, dt=SIM_DT)

        current_before, _ = tracemalloc.get_traced_memory()
        factory.run_ticks(1500, dt=SIM_DT)
        current_after, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        growth = current_after - current_before
        assert growth < MEM_GROWTH_THRESHOLD, (
            f"Memory grew {growth / 1024 / 1024:.2f} MiB over 1500 ticks, "
            f"threshold is {MEM_GROWTH_THRESHOLD / 1024 / 1024:.2f} MiB"
        )

    def test_long_run_tick_count_advances(self, factory: GameLoopFactory) -> None:
        """Tick counter advances by exactly the number of ticks run.

        Guards against regressions where _update_logic early-returns or
        state.tick is reset mid-run.
        """
        initial_tick = factory.state.tick
        run_for = 150
        factory.run_ticks(run_for, dt=SIM_DT)
        assert factory.state.tick == initial_tick + run_for, (
            f"Tick should advance by {run_for} (from {initial_tick} to "
            f"{initial_tick + run_for}), got {factory.state.tick}"
        )

    def test_long_run_render_stable(self, factory: GameLoopFactory) -> None:
        """After a long run, render_frame still succeeds (returns True).

        Catches accumulated renderer state corruption (e.g., dirty caches,
        leaked surfaces) that would only manifest after sustained play.
        """
        factory.run_ticks(300, dt=SIM_DT)
        result = factory.render_frame()
        assert result is True, "render_frame should return True after a long run (no render crash)"

    def test_long_run_no_error_accumulation(self, factory: GameLoopFactory) -> None:
        """Long-run (1000 ticks) accumulates no errors in the errors list.

        run_ticks returns a list of (tick, error_msg) tuples; this must be
        empty for a healthy long run. Non-empty errors indicate a regression
        in any of the per-tick update mixins (weather/movement/combat/ai).
        """
        errors = factory.run_ticks(1000, dt=SIM_DT)
        assert errors == [], (
            f"Long run accumulated {len(errors)} errors; first: {errors[0] if errors else 'none'}"
        )
