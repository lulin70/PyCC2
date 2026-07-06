"""Startup preflight checks for GameLoop subsystems (TD-040).

Verifies that all critical subsystems are non-None and initialized before
entering the main loop. Catches configuration/wiring errors at startup
instead of at first use (where the error message would be cryptic — e.g.
"AttributeError: 'NoneType' object has no attribute 'render'").

Design:
    The check is intentionally simple: it only verifies non-None status
    of subsystems that GameLoopAssembler should have wired. It does NOT
    call initialize() on each subsystem (that already happened during
    assemble()), and it does NOT run functional smoke tests (those are
    covered by integration tests). The goal is fail-fast at startup for
    obvious wiring failures.

Usage in GameLoop.run()::

    from pycc2.infrastructure.diagnostics.preflight_check import run_preflight_check

    result = run_preflight_check(self)
    if not result.ok:
        logger.critical("Preflight check failed: %s", result.failures)
        return 1
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.services.game_loop import GameLoop

logger = logging.getLogger(__name__)


@dataclass
class PreflightResult:
    """Result of a preflight check.

    Attributes:
        ok: True if all critical subsystems are non-None.
        failures: List of human-readable failure messages (empty if ok).

    """

    ok: bool
    failures: list[str] = field(default_factory=list)


def run_preflight_check(game_loop: GameLoop) -> PreflightResult:
    """Run preflight checks on critical GameLoop subsystems.

    Checks three tiers of subsystems:
    1. **Critical** (constructor-injected): renderer, window_manager, event_bus,
       state, display_config. If any is None, the GameLoop was constructed
       incorrectly.
    2. **Assembler-initialized** (__post_init__): _combat_director,
       _render_pipeline, _event_dispatcher. If any is None, GameLoopAssembler
       failed to wire a subsystem.
    3. **Optional** (headless-safe): ai_service, sound_system, input_handler.
       None is acceptable (e.g. headless test mode); logged at DEBUG only.

    Args:
        game_loop: The GameLoop instance to check. Must have been through
            ``__post_init__`` (i.e. ``GameLoopAssembler.assemble()`` must
            have run).

    Returns:
        PreflightResult with ok=True if all critical + assembler subsystems
        are non-None, otherwise ok=False with a list of failure messages.

    """
    failures: list[str] = []

    # Tier 1: Critical subsystems (constructor-injected, must be non-None).
    critical_checks = [
        ("renderer", game_loop.renderer),
        ("window_manager", game_loop.window_manager),
        ("event_bus", game_loop.event_bus),
        ("state", game_loop.state),
        ("display_config", game_loop.display_config),
    ]
    for name, value in critical_checks:
        if value is None:
            failures.append(f"Critical subsystem '{name}' is None")

    # Tier 2: Assembler-initialized subsystems (should be non-None after assemble()).
    assembler_checks = [
        ("_combat_director", game_loop._combat_director),
        ("_render_pipeline", game_loop._render_pipeline),
        ("_event_dispatcher", game_loop._event_dispatcher),
    ]
    for name, value in assembler_checks:
        if value is None:
            failures.append(
                f"Assembler subsystem '{name}' is None "
                "(GameLoopAssembler.assemble() may have failed)",
            )

    # Tier 3: Optional subsystems (None is acceptable in headless/test mode).
    optional_checks = [
        ("ai_service", game_loop.ai_service),
        ("sound_system", game_loop.sound_system),
        ("input_handler", game_loop.input_handler),
    ]
    for name, value in optional_checks:
        if value is None:
            logger.debug("Optional subsystem '%s' is None (headless mode)", name)

    if failures:
        for f_msg in failures:
            logger.critical("Preflight check FAILED: %s", f_msg)
    else:
        logger.info("Preflight check passed: all critical subsystems ready")

    return PreflightResult(ok=len(failures) == 0, failures=failures)
