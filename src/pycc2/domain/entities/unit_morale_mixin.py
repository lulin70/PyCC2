"""Unit morale mixin — extracted from unit.py (D12 Phase 4 P0-2 God Class split).

Contains morale-derived methods used by the Unit facade:
  - is_broken, morale_state (state queries via MoraleSystem).
  - can_move, can_accept_orders (order-acceptance gating via MoraleSystem).

This is a mixin — do not instantiate directly. The Unit facade inherits this
mixin and provides all required fields via its dataclass definition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pycc2.domain.components.morale_component import MoraleComponent
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.state_machine import StateMachine
    from pycc2.domain.systems.morale_system import MoraleState

__all__ = ["UnitMoraleMixin"]


class UnitMoraleMixin:
    """Morale-derived order-acceptance methods for Unit.

    Inherited by the Unit facade, not instantiated. Provides 4 methods
    covering broken-state detection, morale-state lookup, and
    movement/order acceptance gating through MoraleSystem.
    """

    # -- Facade fields used by morale methods (set by Unit dataclass) --
    state_machine: StateMachine
    morale: MoraleComponent

    if TYPE_CHECKING:
        # -- Cross-mixin properties provided by Unit facade --
        @property
        def is_alive(self) -> bool: ...

    # ------------------------------------------------------------------
    # Morale state queries
    # ------------------------------------------------------------------

    @property
    def is_broken(self) -> bool:
        """Check if unit is in broken state (morale < 20)."""
        if hasattr(self, "morale") and self.morale is not None:
            return self.morale.value < 20
        return False

    @property
    def morale_state(self) -> MoraleState:
        """Get current morale state from MoraleSystem."""
        from pycc2.domain.systems.morale_system import MoraleState, MoraleSystem

        if hasattr(self, "morale") and self.morale is not None:
            return MoraleSystem.get_state(self.morale.value)
        return MoraleState.RALLYED

    # ------------------------------------------------------------------
    # Order-acceptance gating
    # ------------------------------------------------------------------

    def can_move(self) -> bool:
        """Check if unit can move based on morale and suppression."""
        from pycc2.domain.entities.unit import UnitState
        from pycc2.domain.systems.morale_system import MoraleSystem

        # Check alive status first
        if not self.is_alive:
            return False

        # Check combat state machine
        if self.state_machine.current in (UnitState.DEAD, UnitState.SURRENDERED):
            return False

        # Use MoraleSystem for detailed check
        if hasattr(self, "morale") and self.morale is not None:
            # MoraleSystem.can_move expects a Unit; cast self (the mixin) to
            # Unit since at runtime the facade IS a Unit via inheritance.
            return MoraleSystem.can_move(cast("Unit", self))

        return True

    def can_accept_orders(self) -> bool:
        """Check if unit will accept orders."""
        from pycc2.domain.systems.morale_system import MoraleSystem

        if hasattr(self, "morale") and self.morale is not None:
            return MoraleSystem.can_accept_orders(cast("Unit", self))
        return True
