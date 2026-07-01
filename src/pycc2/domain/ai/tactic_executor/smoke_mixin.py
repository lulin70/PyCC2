"""Smoke tactics mixin — extracted from tactic_executor.py (D11 SRP split).

Contains smoke deployment tactic execution methods used by the TacticExecutor
facade:
  - ``_execute_deploy_smoke``: consume smoke charge, create SmokeDeployment on
    SmokeManager, publish smoke_deployed event. Reads ``self._environment`` for
    wind drift direction — pre-existing dead code (``_environment`` is set to
    ``None`` in ``__init__`` with no setter; preserved verbatim, do NOT fix).

This is a mixin — do not instantiate directly. The TacticExecutor facade
inherits this mixin and provides all required attributes via its __init__.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from pycc2.domain.ai.smoke_tactical_ai import SmokeDeployment, SmokeGrenadeCapability, SmokeManager
from pycc2.domain.ai.tactic_intent import TacticIntent

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher

__all__ = ["SmokeTacticsMixin"]


class SmokeTacticsMixin:
    """Smoke tactic execution methods. Inherited by the TacticExecutor facade,
    not instantiated directly."""

    # -- Facade attributes used by smoke methods (no defaults; set by TacticExecutor.__init__) --
    event_bus: IEventPublisher
    game_map: GameMap | None
    _unit_registry: dict[str, Unit]
    smoke_manager: SmokeManager
    _smoke_capabilities: dict[str, SmokeGrenadeCapability]
    # _environment is dead code: set to None in __init__ with no setter; read by
    # _execute_deploy_smoke for wind drift direction. Preserved verbatim
    # (pre-existing bug). Typed as None since it is always None at runtime.
    _environment: None
    _logger: logging.Logger

    if TYPE_CHECKING:
        # -- Cross-mixin method provided by the TacticExecutor facade --
        # Declared as TYPE_CHECKING-only stub so mypy can verify smoke
        # methods without runtime shadowing (facade is first in MRO; real
        # method comes from TacticExecutor).
        def _get_unit(self, unit_id: str) -> Unit | None: ...

    def _execute_deploy_smoke(self, intent: TacticIntent) -> bool:
        """Execute a DEPLOY_SMOKE intent.

        Consumes a smoke charge from the unit's SmokeGrenadeCapability,
        creates a SmokeDeployment on the SmokeManager, and publishes
        a smoke_deployed event.
        """
        unit = self._get_unit(intent.unit_id)
        if unit is None:
            return False
        if intent.target_position is None:
            self._logger.warning(f"DEPLOY_SMOKE for {intent.unit_id} has no target_position")
            return False

        # Check smoke capability
        capability = self._smoke_capabilities.get(intent.unit_id)
        if capability is not None:
            if not capability.has_smoke:
                self._logger.debug(f"Unit {intent.unit_id} has no smoke charges remaining")
                return False
            capability.use_smoke()
        # Units without registered capability can still deploy smoke
        # (fallback for units not explicitly registered)

        # Determine wind drift direction from environment
        drift_direction = (0, 0)
        env = self._environment
        if env is not None:
            wind = env.wind_direction if env is not None else (0, 0)
            wx, wy = wind
            length = (wx * wx + wy * wy) ** 0.5
            if length >= 0.01:
                drift_direction = (int(round(wx / length)), int(round(wy / length)))

        # Create and register the smoke deployment
        smoke = SmokeDeployment(
            position=(intent.target_position.x, intent.target_position.y),
            radius=3,
            duration_ticks=180,
            remaining_ticks=180,
            drift_direction=drift_direction,
            deployed_by=intent.unit_id,
        )
        self.smoke_manager.deploy(smoke)

        # Update unit concealment: unit is now in smoke
        combat_state = unit.combat_state
        if combat_state is not None:
            concealment = combat_state.concealment if combat_state is not None else None
            if concealment is not None:
                concealment.in_smoke = True

        # Publish event
        event = {
            "unit_id": intent.unit_id,
            "smoke_position": (intent.target_position.x, intent.target_position.y),
            "smoke_radius": smoke.radius,
            "smoke_duration": smoke.duration_ticks,
            "timestamp": time.time(),
        }
        self.event_bus.publish(event)
        self._logger.debug(
            f"Unit {intent.unit_id} deployed smoke at "
            f"({intent.target_position.x}, {intent.target_position.y})"
        )
        return True
