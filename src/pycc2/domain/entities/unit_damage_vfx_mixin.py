"""Unit damage VFX mixin — extracted from unit.py (D12 Phase 4 P0-2 God Class split).

Contains damage-state and visual-effect methods used by the Unit facade:
  - damage_state, is_damaged, damage_level_numeric (state queries from HP).
  - update_damage_vfx (per-tick smoke/fire particle generation).

This is a mixin — do not instantiate directly. The Unit facade inherits this
mixin and provides all required fields via its dataclass definition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.components.health_component import HealthComponent

__all__ = ["UnitDamageVfxMixin"]


class UnitDamageVfxMixin:
    """Damage-state and visual-effect methods for Unit.

    Inherited by the Unit facade, not instantiated. Provides 4 methods
    covering damage-state classification (undamaged/light/moderate/heavy/
    destroyed) and per-tick smoke/fire particle generation for renderer
    consumption.
    """

    # -- Facade fields used by damage-VFX methods (set by Unit dataclass) --
    health: HealthComponent
    _smoke_particles: list
    _fire_particles: list
    _damage_vfx_timer: int
    id: str

    # ------------------------------------------------------------------
    # Damage-state queries
    # ------------------------------------------------------------------

    @property
    def damage_state(self) -> str:
        """STEP A-2: Calculate damage state based on HP percentage.

        Returns one of: undamaged / light / moderate / heavy / destroyed
        Used for visual feedback (smoke, fire, appearance changes).
        """
        if not hasattr(self, "health") or self.health is None:
            return "undamaged"

        hp_ratio = self.health.hp / self.health.max_hp if self.health.max_hp > 0 else 1.0

        if hp_ratio <= 0:
            return "destroyed"
        elif hp_ratio <= 0.25:
            return "heavy"  # Heavy damage: fire + thick smoke
        elif hp_ratio <= 0.50:
            return "moderate"  # Moderate: smoke + visible damage
        elif hp_ratio <= 0.75:
            return "light"  # Light: light smoke wisps
        else:
            return "undamaged"

    @property
    def is_damaged(self) -> bool:
        """Check if unit has any damage (for quick filtering)."""
        return self.damage_state != "undamaged"

    @property
    def damage_level_numeric(self) -> int:
        """Numeric damage level (0-4) for rendering intensity."""
        states = {"undamaged": 0, "light": 1, "moderate": 2, "heavy": 3, "destroyed": 4}
        return states.get(self.damage_state, 0)

    # ------------------------------------------------------------------
    # VFX update
    # ------------------------------------------------------------------

    def update_damage_vfx(self) -> None:
        """STEP A-2: Update visual effect particles based on current damage state.

        Called each tick to animate smoke/fire particles.
        Generates particle positions for renderer to display.
        """
        self._damage_vfx_timer += 1

        state = self.damage_state

        # Clear old particles periodically
        if self._damage_vfx_timer % 30 == 0:
            self._smoke_particles.clear()
            self._fire_particles.clear()

        # Generate new particles based on damage state
        import random as _rng

        rng = _rng.Random(self.id + str(self._damage_vfx_timer))

        if state in ("light", "moderate", "heavy", "destroyed"):
            # Smoke particles (more for heavier damage)
            num_smoke = {"light": 2, "moderate": 4, "heavy": 6, "destroyed": 8}.get(state, 0)
            for _ in range(num_smoke):
                offset_x = rng.randint(-8, 8)
                offset_y = rng.randint(-10, -2)  # Smoke rises upward
                alpha = rng.randint(80, 180)  # Semi-transparent
                size = rng.randint(2, 5)
                self._smoke_particles.append(
                    {
                        "x": offset_x,
                        "y": offset_y,
                        "alpha": alpha,
                        "size": size,
                        "life": rng.randint(15, 30),  # Ticks until fade
                    }
                )

        if state in ("heavy", "destroyed"):
            # Fire particles (only for heavy damage or destroyed)
            num_fire = 4 if state == "heavy" else 6
            for _ in range(num_fire):
                offset_x = rng.randint(-6, 6)
                offset_y = rng.randint(-4, 4)
                color_var = rng.choice(
                    [
                        (220, 120, 20),  # Orange
                        (240, 200, 50),  # Yellow
                        (180, 50, 10),  # Red-orange
                    ]
                )
                size = rng.randint(2, 4)
                self._fire_particles.append(
                    {
                        "x": offset_x,
                        "y": offset_y,
                        "color": color_var,
                        "size": size,
                        "life": rng.randint(8, 20),
                    }
                )
