"""P2 E2E: Error recovery — graceful degradation when subsystems fail.

Validates that the GameLoop degrades gracefully when individual subsystems
raise exceptions: AI tick failures, render failures, per-unit component
exceptions, event-bus overflow, and corrupted save files. None of these
should crash the game loop or corrupt state.

Error handling is provided by the real GameLoop (no Mock of error paths):
  - GameLoopUpdatingMixin._update_ai: try/except around ai_service.tick()
    → logs warning, units idle this tick, game continues (TD-039).
  - GameLoopRenderingMixin._render_scene: try/except around render pipeline
    → skips this frame, game continues (TD-039).
  - conftest.GameLoopFactory.render_frame: try/except → returns False.
  - GameLoopFactory.run_ticks: try/except per tick → collects errors.
  - EventBus: _MAX_QUEUE_SIZE=1000, drops oldest on overflow; circuit
    breaker unsubscribes handlers after 3 consecutive errors.
  - SecureSaveManager: corrupted file → SaveSlotStatus.CORRUPTED,
    returns (None, None, CORRUPTED) — never raises.

Uses the real GameLoop (assembled via conftest.GameLoopFactory) — no Mock
of domain objects. Exception injection uses monkeypatch (auto-restored).
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

from pycc2.infrastructure.save_system import SaveSlotStatus, SecureSaveManager

# Stable HMAC key so save/load work across separate SecureSaveManager
# instances (simulates: save -> corrupt -> load). 32+ bytes.
_STABLE_HMAC_KEY = "pycc2-e2e-error-recovery-hmac-key-0123456789abcdef"


# ---------------------------------------------------------------------------
# P2 E2E: Error recovery
# ---------------------------------------------------------------------------


class TestErrorRecoveryE2E:
    """Error recovery E2E — graceful degradation when subsystems fail."""

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

    # ------------------------------------------------------------------
    # 1. AI tick failure → graceful degradation
    # ------------------------------------------------------------------

    def test_ai_tick_failure_graceful_degradation(
        self, factory: GameLoopFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AI tick failure degrades gracefully — GameLoop does not crash.

        Injects a RuntimeError into ai_service.tick(). The GameLoop's
        _update_ai mixin catches it (TD-039) and logs a warning; the
        tick is dropped (units idle) but the game continues. run_ticks
        returns no errors because the exception is contained inside
        _update_ai.
        """
        # Ensure at least one AI unit is registered (enemy units from
        # complete_deployment are registered on the first tick).
        factory.run_ticks(3, dt=0.1)
        assert factory.ai_service.managed_unit_count > 0, (
            "Test requires at least one AI unit registered"
        )

        # Inject a raising tick. *args/**kwargs absorb the real signature.
        def raising_tick(*args, **kwargs):
            raise RuntimeError("Simulated AI service failure")

        monkeypatch.setattr(factory.ai_service, "tick", raising_tick)

        errors = factory.run_ticks(30, dt=0.1)
        # _update_ai catches the exception → no errors propagate to run_ticks
        assert errors == [], (
            f"AI tick failure should be contained in _update_ai, got {len(errors)} errors"
        )
        # GameLoop survived: state still valid
        assert factory.state.game_map is not None
        assert len(factory.state.units) > 0
        # Tick advanced despite AI failure each tick
        assert factory.state.tick > 0

    # ------------------------------------------------------------------
    # 2. Render failure → no crash
    # ------------------------------------------------------------------

    def test_render_failure_no_crash(
        self, factory: GameLoopFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Render failure does not crash — render_frame returns False.

        Injects a RuntimeError into renderer.render(). render_frame's
        try/except catches it and returns False. The GameLoop itself
        is unaffected: subsequent run_ticks still work.
        """
        factory.run_ticks(10, dt=0.1)

        def raising_render(*args, **kwargs):
            raise RuntimeError("Simulated renderer failure")

        monkeypatch.setattr(factory.renderer, "render", raising_render)

        # render_frame catches the exception → returns False (graceful)
        result = factory.render_frame()
        assert result is False, "render_frame should return False when renderer raises"

        # GameLoop survived: run_ticks still works after the render failure
        errors = factory.run_ticks(20, dt=0.1)
        assert errors == [], "GameLoop should continue running after render failure"

    # ------------------------------------------------------------------
    # 3. Per-unit component exception isolated
    # ------------------------------------------------------------------

    def test_unit_component_exception_isolated(
        self, factory: GameLoopFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failing unit component is isolated — other units/game survive.

        Makes one unit's update_movement_mode raise for 5 ticks, then
        recover. The failing ticks are recorded in the errors list
        (run_ticks catches per-tick exceptions), but:
          - Other units remain in state.units (not removed)
          - The failing unit itself remains in state.units
          - After recovery, subsequent ticks succeed (game_loop continues)
        """
        assert len(factory.state.units) >= 2, "Test requires at least 2 units"
        target_unit = factory.state.units[0]
        other_unit = factory.state.units[1]
        other_id = other_unit.id
        target_id = target_unit.id
        original = target_unit.update_movement_mode  # bound method

        call_count = [0]

        def flaky_update():
            call_count[0] += 1
            if call_count[0] <= 5:
                raise RuntimeError("Simulated unit component failure")
            return original()

        monkeypatch.setattr(target_unit, "update_movement_mode", flaky_update)

        errors = factory.run_ticks(30, dt=0.1)
        # Some ticks failed (the 5 flaky calls), but the loop continued
        assert len(errors) > 0, "Expected errors from the failing unit component"

        # Other units survived (isolation: failure didn't remove them)
        unit_ids = {u.id for u in factory.state.units}
        assert other_id in unit_ids, "Other unit should survive the failure"
        assert target_id in unit_ids, "Failing unit should still be in state"

        # GameLoop recovered: subsequent ticks succeed (flaky_update already
        # past the failure window — call_count > 5, so it delegates to original)
        post_errors = factory.run_ticks(20, dt=0.1)
        assert post_errors == [], (
            f"GameLoop should recover after the unit failure cleared, got {len(post_errors)}"
        )

    # ------------------------------------------------------------------
    # 4. Event bus overflow → no crash
    # ------------------------------------------------------------------

    def test_event_bus_overflow_handling(self, factory: GameLoopFactory) -> None:
        """Event bus overflow is handled — drops oldest, no crash.

        Enqueues 2000 events (2x _MAX_QUEUE_SIZE=1000). The EventBus
        drops the oldest events and keeps the queue bounded. process_queue
        then dispatches without crashing.
        """
        event_bus = factory.event_bus
        max_size = event_bus._MAX_QUEUE_SIZE

        # Enqueue well beyond the limit
        for i in range(max_size * 2):
            event_bus.enqueue({"event_type": "test_overflow", "index": i})

        # Queue is bounded at _MAX_QUEUE_SIZE (oldest dropped)
        assert event_bus.queue_size <= max_size, (
            f"Queue should be bounded at {max_size}, got {event_bus.queue_size}"
        )
        assert event_bus.queue_size == max_size, (
            f"Queue should be exactly full at {max_size}, got {event_bus.queue_size}"
        )

        # process_queue dispatches all queued events without crashing
        processed = event_bus.process_queue()
        assert processed == max_size, (
            f"process_queue should dispatch {max_size} events, got {processed}"
        )
        assert event_bus.queue_size == 0, "Queue should be empty after process_queue"

    # ------------------------------------------------------------------
    # 5. Corrupted save → recovery (no crash)
    # ------------------------------------------------------------------

    def test_save_corrupted_recovery(
        self,
        factory: GameLoopFactory,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Loading a corrupted save returns failure status — no crash.

        Saves a valid game state, then overwrites the save file with
        garbage (invalid JSON). quick_load detects the corruption
        (HMAC mismatch / JSONDecodeError) and returns False. The GameLoop
        continues to work normally after the failed load.
        """
        # Use a stable HMAC key + tmp_path isolation
        monkeypatch.setenv("PYCC2_SAVE_HMAC_KEY", _STABLE_HMAC_KEY)
        save_manager = SecureSaveManager(base_dir=tmp_path)
        factory.game_loop._save_controller.save_manager = save_manager

        # Run a few ticks to advance state, then save
        factory.run_ticks(30, dt=0.1)
        saved_tick = factory.state.tick
        assert factory.game_loop.quick_save(0) is True, "quick_save should succeed"

        slot_file = save_manager._slot_path(0)
        assert slot_file.exists(), "Save file should exist after quick_save"

        # Corrupt the save file with garbage (invalid JSON + no HMAC)
        slot_file.write_text("THIS IS NOT VALID JSON {{corrupted}}", encoding="utf-8")

        # quick_load detects corruption → returns False (no exception raised)
        loaded = factory.game_loop.quick_load(0)
        assert loaded is False, "quick_load should return False for corrupted save"

        # Verify at the SecureSaveManager level too: status is CORRUPTED
        _, _, status = save_manager.load_game(0)
        assert status == SaveSlotStatus.CORRUPTED, (
            f"Corrupted save should return CORRUPTED status, got {status}"
        )

        # GameLoop survived: state.tick is unchanged (load failed), and
        # subsequent run_ticks still work
        assert factory.state.tick == saved_tick, "State tick should be unchanged after failed load"
        post_errors = factory.run_ticks(20, dt=0.1)
        assert post_errors == [], (
            f"GameLoop should continue after corrupted save load, got {len(post_errors)} errors"
        )
