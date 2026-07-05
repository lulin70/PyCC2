"""Unit combat-state mixin — extracted from unit.py (D12 Phase 4 P0-2 God Class split).

Contains combat-state and suppression/concealment methods used by the Unit
facade:
  - Status properties: can_act, combat_effective, is_pinned.
  - Suppression/concealment: suppression_level, concealment_level.
  - State queries: update_garrison_status (building garrison tracking).

This is a mixin — do not instantiate directly. The Unit facade inherits this
mixin and provides all required fields via its dataclass definition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.components.health_component import HealthComponent
    from pycc2.domain.components.morale_component import MoraleComponent
    from pycc2.domain.state_machine import StateMachine
    from pycc2.domain.systems.combat_mechanics_enhanced import (
        CombatState,
        SuppressionEffect,
    )

__all__ = ["UnitCombatMixin"]


class UnitCombatMixin:
    """Combat-state and suppression methods for Unit.

    Inherited by the Unit facade, not instantiated. Provides 5 methods
    covering combat-action eligibility, suppression level, concealment
    level, and pinned state.
    """

    # -- Facade fields used by combat-state methods (set by Unit dataclass) --
    state_machine: StateMachine
    combat_state: CombatState | None
    health: HealthComponent

    if TYPE_CHECKING:
        # -- Cross-mixin properties provided by Unit facade --
        @property
        def is_alive(self) -> bool: ...

        @property
        def morale(self) -> MoraleComponent: ...

    # ------------------------------------------------------------------
    # Combat-action eligibility
    # ------------------------------------------------------------------

    @property
    def can_act(self) -> bool:
        """Return True if the unit is alive and not in a blocking state."""
        from pycc2.domain.entities.unit import UnitState

        return (
            self.is_alive
            and self.state_machine.current != UnitState.DEAD
            and self.state_machine.current != UnitState.RELOADING
            and self.state_machine.current != UnitState.SURRENDERED
        )

    @property
    def combat_effective(self) -> bool:
        """Return True if the unit is alive and its morale allows combat."""
        return self.is_alive and self.morale.is_combat_effective

    @property
    def is_pinned(self) -> bool:
        """Return True if the unit is currently pinned down by suppression."""
        return self.combat_state.is_pinned if self.combat_state is not None else False

    # ------------------------------------------------------------------
    # Suppression / concealment
    # ------------------------------------------------------------------

    @property
    def suppression_level(self) -> SuppressionEffect:
        """Return the current suppression effect applied to the unit."""
        if self.combat_state is not None:
            return self.combat_state.suppression.get_current_effect()
        from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect

        return SuppressionEffect.NONE

    @property
    def concealment_level(self) -> float:
        """Return the unit's current total concealment value."""
        if self.combat_state is not None:
            return self.combat_state.concealment.calculate_total_concealment()
        return 0.0
