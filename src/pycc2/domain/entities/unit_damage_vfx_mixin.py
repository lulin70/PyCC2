"""Unit damage VFX mixin — extracted from unit.py (D12 Phase 4 P0-2 God Class split).

Contains damage-state and visual-effect methods used by the Unit facade:
  - damage_state, is_damaged, damage_level_numeric (state queries from HP).
  - update_damage_vfx (per-tick smoke/fire particle generation).
  - is_vehicle, update_vehicle_damage_components (TD-065: vehicle component
    damage differentiation — tracks/turret/engine rendered with distinct VFX).

This is a mixin — do not instantiate directly. The Unit facade inherits this
mixin and provides all required fields via its dataclass definition.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.components.health_component import HealthComponent
    from pycc2.domain.entities.unit import UnitType

__all__ = ["UnitDamageVfxMixin"]


# TD-065: Vehicle components tracked for differentiated damage rendering.
_VEHICLE_COMPONENTS: tuple[str, ...] = ("tracks", "turret", "engine")

# TD-065: Component damage plan per damage_state.
# Maps state → {damaged_count, destroyed_count} applied to the 3 components.
# Escalates monotonically so heavier HP loss always yields more component failure.
_VEHICLE_COMPONENT_DAMAGE_PLAN: dict[str, dict[str, int]] = {
    "undamaged": {"damaged": 0, "destroyed": 0},
    "light": {"damaged": 1, "destroyed": 0},
    "moderate": {"damaged": 1, "destroyed": 1},
    "heavy": {"damaged": 2, "destroyed": 1},
    "destroyed": {"damaged": 0, "destroyed": 3},
}


class UnitDamageVfxMixin:
    """Damage-state and visual-effect methods for Unit.

    Inherited by the Unit facade, not instantiated. Provides damage-state
    classification (undamaged/light/moderate/heavy/destroyed), per-tick
    smoke/fire particle generation, and (TD-065) vehicle component damage
    differentiation — tracks/turret/engine rendered with distinct VFX.
    """

    # -- Facade fields used by damage-VFX methods (set by Unit dataclass) --
    health: HealthComponent
    _smoke_particles: list
    _fire_particles: list
    _damage_vfx_timer: int
    _damage_components: dict
    id: str
    unit_type: UnitType

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

    @property
    def is_vehicle(self) -> bool:
        """TD-065: True if this unit is a vehicle (TANK unit type).

        Compared via enum ``.name`` to avoid a runtime import of UnitType
        (which would create a circular reference at module load time).
        """
        return getattr(self.unit_type, "name", "") == "TANK"

    # ------------------------------------------------------------------
    # VFX update
    # ------------------------------------------------------------------

    def update_damage_vfx(self) -> None:
        """STEP A-2: Update visual effect particles based on current damage state.

        Called each tick to animate smoke/fire particles.
        Generates particle positions for renderer to display.

        TD-065: For vehicles, also refreshes component damage (tracks/turret/
        engine) and emits component-specific particles in addition to the
        generic smoke/fire baseline so the player sees distinct feedback
        ("tracks knocked out" → black low smoke + sparks, "turret jammed"
        → high gray smoke, "engine hit" → rear thick smoke + fire).
        """
        self._damage_vfx_timer += 1

        state = self.damage_state

        # Clear old particles periodically
        if self._damage_vfx_timer % 30 == 0:
            self._smoke_particles.clear()
            self._fire_particles.clear()

        # TD-065: Refresh vehicle component damage for current state
        if self.is_vehicle:
            self.update_vehicle_damage_components(state)

        # Generate new particles based on damage state
        rng = random.Random(self.id + str(self._damage_vfx_timer))

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

        # TD-065: Vehicle component-specific VFX overlay
        if self.is_vehicle and state != "undamaged":
            self._emit_vehicle_component_vfx(rng)

    # ------------------------------------------------------------------
    # TD-065: Vehicle component damage differentiation
    # ------------------------------------------------------------------

    def update_vehicle_damage_components(self, state: str | None = None) -> None:
        """TD-065: Assign vehicle component damage based on current damage state.

        Deterministic per (unit.id, damage_state) — same unit at the same
        damage level always shows the same component failures, so the player
        sees consistent "tracks knocked out" / "turret jammed" feedback
        rather than flickering component states between ticks.

        Components: tracks (mobility), turret (offense), engine (power).
        Each component is set to one of: intact / damaged / destroyed.

        Args:
            state: Damage state to compute components for. If None, uses
                current ``self.damage_state``.
        """
        # Self-protective guard: component damage is vehicle-only. Keeps
        # infantry _damage_components empty even if callers invoke directly.
        if not self.is_vehicle:
            return

        if state is None:
            state = self.damage_state

        plan = _VEHICLE_COMPONENT_DAMAGE_PLAN.get(
            state, _VEHICLE_COMPONENT_DAMAGE_PLAN["undamaged"]
        )

        # Deterministic component selection: stable per (unit.id, state)
        rng = random.Random(self.id + ":components:" + state)
        pool = list(_VEHICLE_COMPONENTS)
        rng.shuffle(pool)

        destroyed_count = plan["destroyed"]
        damaged_count = plan["damaged"]

        new_components: dict[str, str] = {}
        for idx, comp in enumerate(pool):
            if idx < destroyed_count:
                new_components[comp] = "destroyed"
            elif idx < destroyed_count + damaged_count:
                new_components[comp] = "damaged"
            else:
                new_components[comp] = "intact"

        # Replace atomically — readers see a consistent snapshot rather
        # than a half-mutated dict during iteration.
        self._damage_components.clear()
        self._damage_components.update(new_components)

    def _emit_vehicle_component_vfx(self, rng: random.Random) -> None:
        """TD-065: Emit component-specific particles for vehicles.

        - tracks:  black smoke + sparks at low offset (mobility hit)
        - turret:  gray smoke at high offset (weapon jam)
        - engine:  thick dark smoke + fire at rear (power loss)

        Particle dicts gain a ``tag`` field so the renderer can theme them
        distinctly from the generic smoke/fire baseline.

        Args:
            rng: Shared random instance for this tick (deterministic per
                unit.id + timer).
        """
        for comp, status in self._damage_components.items():
            if status == "intact":
                continue

            intensity = 2 if status == "damaged" else 4

            if comp == "tracks":
                for _ in range(intensity):
                    self._smoke_particles.append(
                        {
                            "x": rng.randint(-10, 10),
                            "y": rng.randint(0, 4),
                            "alpha": rng.randint(140, 200),
                            "size": rng.randint(3, 6),
                            "life": rng.randint(20, 35),
                            "color": (40, 40, 40),
                            "tag": "tracks",
                        }
                    )
                for _ in range(intensity):
                    self._fire_particles.append(
                        {
                            "x": rng.randint(-8, 8),
                            "y": rng.randint(0, 3),
                            "color": (255, 200, 80),
                            "size": rng.randint(1, 2),
                            "life": rng.randint(4, 10),
                            "tag": "tracks_spark",
                        }
                    )

            elif comp == "turret":
                for _ in range(intensity):
                    self._smoke_particles.append(
                        {
                            "x": rng.randint(-4, 4),
                            "y": rng.randint(-12, -6),
                            "alpha": rng.randint(100, 160),
                            "size": rng.randint(2, 4),
                            "life": rng.randint(15, 25),
                            "color": (140, 140, 140),
                            "tag": "turret",
                        }
                    )

            elif comp == "engine":
                for _ in range(intensity):
                    self._smoke_particles.append(
                        {
                            "x": rng.randint(4, 10),
                            "y": rng.randint(-4, 2),
                            "alpha": rng.randint(160, 220),
                            "size": rng.randint(4, 7),
                            "life": rng.randint(25, 40),
                            "color": (60, 60, 60),
                            "tag": "engine",
                        }
                    )
                for _ in range(intensity):
                    self._fire_particles.append(
                        {
                            "x": rng.randint(4, 9),
                            "y": rng.randint(-3, 3),
                            "color": rng.choice([(220, 80, 20), (200, 40, 10)]),
                            "size": rng.randint(2, 5),
                            "life": rng.randint(10, 20),
                            "tag": "engine_fire",
                        }
                    )
