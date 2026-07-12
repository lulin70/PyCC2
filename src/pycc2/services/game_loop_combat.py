"""Game Loop Combat Mixin — extracted from game_loop.py (P5-1 batch 2).

Contains combat event handler methods used by the GameLoop facade:
  - _handle_player_command: route player commands to combat director
  - _execute_attack: delegate attack execution to combat director
  - _on_unit_attacked: handle unit-attacked events + "taking fire" popup
  - _on_unit_attacked_for_stats: record combat stats
  - _on_projectile_fired: add projectile trails
  - _process_combat_popups: scan units and emit floating combat popups

This is a mixin — do not instantiate directly. The facade GameLoop class
inherits this mixin and provides all required attributes via its dataclass
fields. Class-level attribute declarations below tell mypy which facade
fields the mixin methods rely on.
"""

from __future__ import annotations

from pycc2.domain.interfaces import (
    ICombatDirector,
    IPopupManager,
    IProjectileTrailSystem,
    IVictoryManager,
)
from pycc2.services.game_loop_types import GameState


class GameLoopCombatMixin:
    """Combat event handler methods for GameLoop. Inherited by the facade."""

    # -- Facade attributes used by combat methods (no defaults; set by GameLoop) --
    state: GameState
    _combat_director: ICombatDirector | None
    _popup_manager: IPopupManager | None
    _victory_manager: IVictoryManager | None
    _projectile_trail_sys: IProjectileTrailSystem | None

    def _handle_player_command(self, data: dict) -> None:
        if self._combat_director is None:
            return
        self._combat_director.handle_player_command(data, self.state.units, self.state.game_map)

    def _execute_attack(self, attacker, target) -> None:
        if self._combat_director is None:
            return
        self._combat_director.execute_attack(attacker, target)

    def _on_unit_attacked(self, data: dict) -> None:
        if self._combat_director is None:
            return
        self._combat_director.on_unit_attacked(data)
        # Trigger "Taking fire!" popup on the target unit
        target_id = data.get("target_id")
        if target_id and self._popup_manager is not None:
            target = next((u for u in self.state.units if u.id == target_id), None)
            if target and target.position is not None:
                pp = target.position.pixel_position
                self._popup_manager.add_taking_fire(pp.x, pp.y)

    def _on_unit_attacked_for_stats(self, data: dict) -> None:
        if self._combat_director is None or self._victory_manager is None:
            return
        self._combat_director.record_stats(
            data, self.state.units, self._victory_manager.battle_stats
        )

    def _on_projectile_fired(self, data: dict) -> None:
        """Handle ProjectileFired event — add trail to ProjectileTrailSystem."""
        if self._projectile_trail_sys is None:
            return
        weapon_type = data.get("weapon_type", "bullet")
        sx = data.get("start_x", 0.0)
        sy = data.get("start_y", 0.0)
        ex = data.get("end_x", 0.0)
        ey = data.get("end_y", 0.0)

        if weapon_type == "shell":
            self._projectile_trail_sys.add_shell_trail(sx, sy, ex, ey)
        elif weapon_type == "rocket":
            self._projectile_trail_sys.add_rocket_trail(sx, sy, ex, ey)
        elif weapon_type == "mortar":
            self._projectile_trail_sys.add_mortar_trail(sx, sy, ex, ey)
        else:
            self._projectile_trail_sys.add_bullet_trail(sx, sy, ex, ey)

    def _process_combat_popups(self) -> None:
        """Scan units for combat events and trigger floating popups."""
        if self._popup_manager is None:
            return
        from pycc2.domain.systems.morale_system import MoraleState, MoraleSystem

        for unit in self.state.units:
            if not unit.is_alive:
                continue
            # Get pixel position for popup placement
            px, py = 0.0, 0.0
            if unit.position is not None:
                pp = unit.position.pixel_position
                px, py = pp.x, pp.y

            # Check morale state changes → popup
            if unit.morale is not None:
                morale_state = MoraleSystem.get_state(unit.morale.value)
                # Track previous state to detect transitions
                prev_state = getattr(unit, "_prev_morale_state", None)
                if prev_state is not None and prev_state != morale_state:
                    if morale_state == MoraleState.BROKEN:
                        self._popup_manager.add_breaking(px, py)
                    elif morale_state == MoraleState.PINNED:
                        self._popup_manager.add_pinned(px, py)
                unit._prev_morale_state = morale_state

            # Check for out-of-ammo
            if unit.weapon is not None:
                weapon_state = unit.weapon.state
                if weapon_state is not None:
                    if weapon_state.name == "OUT_OF_AMMO" and not getattr(
                        unit, "_ammo_popup_shown", False
                    ):
                        self._popup_manager.add_out_of_ammo(px, py)
                        unit._ammo_popup_shown = True
                    elif weapon_state.name != "OUT_OF_AMMO":
                        unit._ammo_popup_shown = False

        # Check for KIA (newly dead units)
        for unit in self.state.units:
            if not unit.is_alive and not getattr(unit, "_kia_popup_shown", False):
                px, py = 0.0, 0.0
                if unit.position is not None:
                    pp = unit.position.pixel_position
                    px, py = pp.x, pp.y
                self._popup_manager.add_kia(px, py)
                unit._kia_popup_shown = True


__all__ = ["GameLoopCombatMixin"]
