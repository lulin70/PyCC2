"""Unit tests for GameLoopCombatMixin.

Covers the six combat event-handler methods extracted from the GameLoop
facade:
  - _handle_player_command
  - _execute_attack
  - _on_unit_attacked
  - _on_unit_attacked_for_stats
  - _on_projectile_fired
  - _process_combat_popups

The mixin is not instantiated directly; a concrete host class provides the
facade attributes (state / _combat_director / _popup_manager /
_victory_manager / _projectile_trail_sys). Real domain components
(Unit / PositionComponent / MoraleComponent / WeaponComponent) are used
wherever practical; collaborators (directors / managers) are Mocks so call
arguments can be asserted precisely.
"""

# ruff: noqa: I001
# SDL dummy drivers must be set before any pygame import (transitively pulled
# in via pycc2.domain). Import ordering is intentionally non-standard here.
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import Mock

import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.morale_system import MoraleState, MoraleSystem
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.game_loop_combat import GameLoopCombatMixin
from pycc2.services.game_loop_types import GameState


# ===========================================================================
# Host + helpers
# ===========================================================================


class _CombatMixinHost(GameLoopCombatMixin):
    """Concrete host exposing the facade attributes the mixin relies on.

    GameLoopCombatMixin declares class-level attribute annotations but no
    defaults; the real GameLoop facade supplies them via dataclass fields.
    This host mirrors that contract for isolated unit testing.
    """

    def __init__(
        self,
        state: GameState,
        combat_director=None,
        popup_manager=None,
        victory_manager=None,
        projectile_trail_sys=None,
    ) -> None:
        self.state = state
        self._combat_director = combat_director
        self._popup_manager = popup_manager
        self._victory_manager = victory_manager
        self._projectile_trail_sys = projectile_trail_sys


def _make_state(units):
    """Build a GameState with stub game_map/camera (unused by combat methods)."""
    return GameState(game_map=Mock(name="game_map"), units=list(units), camera=Mock(name="camera"))


def _make_host(
    units,
    combat_director=None,
    popup_manager=None,
    victory_manager=None,
    projectile_trail_sys=None,
) -> _CombatMixinHost:
    """Build a host instance wired with the given collaborators and units."""
    state = _make_state(units)
    return _CombatMixinHost(
        state=state,
        combat_director=combat_director,
        popup_manager=popup_manager,
        victory_manager=victory_manager,
        projectile_trail_sys=projectile_trail_sys,
    )


def _make_real_unit(
    unit_id: str,
    faction: Faction = Faction.ALLIES,
    tile_x: int = 5,
    tile_y: int = 5,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 85,
    ammo: int = 120,
    max_ammo: int = 120,
) -> Unit:
    """Build a real Unit with sensible defaults for combat-popup tests."""
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale),
        weapon=WeaponComponent(
            primary_weapon_id="rifle", ammo_remaining=ammo, max_ammo=max_ammo
        ),
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(),
    )


def _pixel(tile_x: int, tile_y: int) -> tuple[float, float]:
    """Return the expected pixel position for a tile (mirrors PositionComponent)."""
    return (float(tile_x * 48), float(tile_y * 48))


# ===========================================================================
# _handle_player_command
# ===========================================================================


@pytest.mark.unit
class TestHandlePlayerCommand:
    def test_no_combat_director_returns_early(self):
        unit = _make_real_unit("u1")
        host = _make_host([unit], combat_director=None)
        # Should be a no-op; no attribute of state should be touched.
        host._handle_player_command({"command": "attack"})
        # No assertion error means early return succeeded; assert state intact.
        assert host._combat_director is None

    def test_routes_command_to_combat_director(self):
        unit = _make_real_unit("u1")
        director = Mock(name="combat_director")
        host = _make_host([unit], combat_director=director)
        data = {"command": "attack", "unit_ids": ["u1"]}
        host._handle_player_command(data)
        director.handle_player_command.assert_called_once_with(
            data, host.state.units, host.state.game_map
        )


# ===========================================================================
# _execute_attack
# ===========================================================================


@pytest.mark.unit
class TestExecuteAttack:
    def test_no_combat_director_returns_early(self):
        attacker = _make_real_unit("a1")
        target = _make_real_unit("e1", faction=Faction.AXIS)
        host = _make_host([attacker, target], combat_director=None)
        host._execute_attack(attacker, target)
        assert host._combat_director is None  # early return path taken

    def test_delegates_attack_to_combat_director(self):
        attacker = _make_real_unit("a1")
        target = _make_real_unit("e1", faction=Faction.AXIS)
        director = Mock(name="combat_director")
        host = _make_host([attacker, target], combat_director=director)
        host._execute_attack(attacker, target)
        director.execute_attack.assert_called_once_with(attacker, target)


# ===========================================================================
# _on_unit_attacked
# ===========================================================================


@pytest.mark.unit
class TestOnUnitAttacked:
    def test_no_combat_director_returns_early(self):
        unit = _make_real_unit("u1")
        host = _make_host([unit], combat_director=None, popup_manager=Mock())
        host._on_unit_attacked({"target_id": "u1", "damage": 10})
        # Early return: nothing to assert beyond no exception; verify director
        # is still None (the guard that was hit).
        assert host._combat_director is None

    def test_popup_manager_none_only_calls_on_unit_attacked(self):
        unit = _make_real_unit("u1")
        director = Mock(name="combat_director")
        host = _make_host([unit], combat_director=director, popup_manager=None)
        data = {"target_id": "u1", "damage": 10}
        host._on_unit_attacked(data)
        director.on_unit_attacked.assert_called_once_with(data)
        # No popup manager → no add_taking_fire call possible. Verify director
        # was the only collaborator touched by checking no exception raised and
        # popup_manager still None.
        assert host._popup_manager is None

    def test_adds_taking_fire_popup_for_target(self):
        unit = _make_real_unit("u1", tile_x=5, tile_y=5)
        director = Mock(name="combat_director")
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], combat_director=director, popup_manager=popup_mgr)
        data = {"target_id": "u1", "damage": 10}
        host._on_unit_attacked(data)
        director.on_unit_attacked.assert_called_once_with(data)
        px, py = _pixel(5, 5)
        popup_mgr.add_taking_fire.assert_called_once_with(px, py)

    def test_no_popup_when_target_id_not_in_units(self):
        unit = _make_real_unit("u1")
        director = Mock(name="combat_director")
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], combat_director=director, popup_manager=popup_mgr)
        host._on_unit_attacked({"target_id": "ghost", "damage": 10})
        director.on_unit_attacked.assert_called_once()
        popup_mgr.add_taking_fire.assert_not_called()

    def test_no_popup_when_target_position_is_none(self):
        unit = _make_real_unit("u1")
        unit.position = None
        director = Mock(name="combat_director")
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], combat_director=director, popup_manager=popup_mgr)
        host._on_unit_attacked({"target_id": "u1", "damage": 10})
        director.on_unit_attacked.assert_called_once()
        popup_mgr.add_taking_fire.assert_not_called()

    def test_no_popup_when_target_id_falsy(self):
        unit = _make_real_unit("u1")
        director = Mock(name="combat_director")
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], combat_director=director, popup_manager=popup_mgr)
        # Missing target_id key → data.get returns None → falsy guard skips popup.
        host._on_unit_attacked({"damage": 10})
        director.on_unit_attacked.assert_called_once()
        popup_mgr.add_taking_fire.assert_not_called()


# ===========================================================================
# _on_unit_attacked_for_stats
# ===========================================================================


@pytest.mark.unit
class TestOnUnitAttackedForStats:
    def test_no_combat_director_returns_early(self):
        unit = _make_real_unit("u1")
        host = _make_host(
            [unit], combat_director=None, victory_manager=Mock()
        )
        host._on_unit_attacked_for_stats({"attacker_id": "u1", "damage": 10})
        assert host._combat_director is None

    def test_no_victory_manager_returns_early(self):
        unit = _make_real_unit("u1")
        director = Mock(name="combat_director")
        host = _make_host([unit], combat_director=director, victory_manager=None)
        host._on_unit_attacked_for_stats({"attacker_id": "u1", "damage": 10})
        director.record_stats.assert_not_called()
        assert host._victory_manager is None

    def test_records_stats_with_battle_stats(self):
        unit = _make_real_unit("u1")
        director = Mock(name="combat_director")
        victory_mgr = Mock(name="victory_manager")
        host = _make_host(
            [unit], combat_director=director, victory_manager=victory_mgr
        )
        data = {"attacker_id": "u1", "damage": 25, "killed": False}
        host._on_unit_attacked_for_stats(data)
        director.record_stats.assert_called_once_with(
            data, host.state.units, victory_mgr.battle_stats
        )


# ===========================================================================
# _on_projectile_fired
# ===========================================================================


@pytest.mark.unit
class TestOnProjectileFired:
    def test_no_projectile_trail_sys_returns_early(self):
        host = _make_host([], projectile_trail_sys=None)
        host._on_projectile_fired({"weapon_type": "shell"})
        assert host._projectile_trail_sys is None

    def test_shell_trail(self):
        trail_sys = Mock(name="trail_sys")
        host = _make_host([], projectile_trail_sys=trail_sys)
        host._on_projectile_fired(
            {"weapon_type": "shell", "start_x": 1.0, "start_y": 2.0, "end_x": 3.0, "end_y": 4.0}
        )
        trail_sys.add_shell_trail.assert_called_once_with(1.0, 2.0, 3.0, 4.0)
        trail_sys.add_bullet_trail.assert_not_called()

    def test_rocket_trail(self):
        trail_sys = Mock(name="trail_sys")
        host = _make_host([], projectile_trail_sys=trail_sys)
        host._on_projectile_fired(
            {"weapon_type": "rocket", "start_x": 1.0, "start_y": 2.0, "end_x": 3.0, "end_y": 4.0}
        )
        trail_sys.add_rocket_trail.assert_called_once_with(1.0, 2.0, 3.0, 4.0)
        trail_sys.add_bullet_trail.assert_not_called()

    def test_mortar_trail(self):
        trail_sys = Mock(name="trail_sys")
        host = _make_host([], projectile_trail_sys=trail_sys)
        host._on_projectile_fired(
            {"weapon_type": "mortar", "start_x": 1.0, "start_y": 2.0, "end_x": 3.0, "end_y": 4.0}
        )
        trail_sys.add_mortar_trail.assert_called_once_with(1.0, 2.0, 3.0, 4.0)
        trail_sys.add_bullet_trail.assert_not_called()

    def test_bullet_trail_default_weapon_type(self):
        trail_sys = Mock(name="trail_sys")
        host = _make_host([], projectile_trail_sys=trail_sys)
        host._on_projectile_fired(
            {"weapon_type": "bullet", "start_x": 1.0, "start_y": 2.0, "end_x": 3.0, "end_y": 4.0}
        )
        trail_sys.add_bullet_trail.assert_called_once_with(1.0, 2.0, 3.0, 4.0)

    def test_unknown_weapon_type_falls_back_to_bullet_trail(self):
        trail_sys = Mock(name="trail_sys")
        host = _make_host([], projectile_trail_sys=trail_sys)
        host._on_projectile_fired(
            {"weapon_type": "laser", "start_x": 1.0, "start_y": 2.0, "end_x": 3.0, "end_y": 4.0}
        )
        trail_sys.add_bullet_trail.assert_called_once_with(1.0, 2.0, 3.0, 4.0)
        trail_sys.add_shell_trail.assert_not_called()
        trail_sys.add_rocket_trail.assert_not_called()
        trail_sys.add_mortar_trail.assert_not_called()

    def test_missing_fields_use_zero_defaults(self):
        trail_sys = Mock(name="trail_sys")
        host = _make_host([], projectile_trail_sys=trail_sys)
        # Empty dict → weapon_type defaults to "bullet", coords default to 0.0.
        host._on_projectile_fired({})
        trail_sys.add_bullet_trail.assert_called_once_with(0.0, 0.0, 0.0, 0.0)


# ===========================================================================
# _process_combat_popups
# ===========================================================================


@pytest.mark.unit
class TestProcessCombatPopups:
    def test_no_popup_manager_returns_early(self):
        unit = _make_real_unit("u1")
        host = _make_host([unit], popup_manager=None)
        host._process_combat_popups()
        assert host._popup_manager is None

    def test_dead_unit_skipped_in_first_loop(self):
        # A dead unit should be skipped in the morale/ammo scan (first loop)
        # but still trigger a KIA popup in the second loop.
        dead = _make_real_unit("dead1", hp=0, max_hp=100, morale=10)  # BROKEN morale
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([dead], popup_manager=popup_mgr)
        host._process_combat_popups()
        # Not processed in first loop → no morale/ammo popups.
        popup_mgr.add_breaking.assert_not_called()
        popup_mgr.add_pinned.assert_not_called()
        popup_mgr.add_out_of_ammo.assert_not_called()
        # But KIA popup emitted in second loop.
        popup_mgr.add_kia.assert_called_once()

    def test_morale_transition_to_broken_adds_breaking(self):
        unit = _make_real_unit("u1", tile_x=5, tile_y=5, morale=85)  # RALLYED
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        # First call: prev_state is None → no popup; sets _prev_morale_state.
        host._process_combat_popups()
        popup_mgr.add_breaking.assert_not_called()
        assert unit._prev_morale_state == MoraleState.RALLYED
        # Drop morale into BROKEN territory and process again.
        unit.morale.apply_delta(-75)  # 85 → 10 → BROKEN
        assert MoraleSystem.get_state(unit.morale.value) == MoraleState.BROKEN
        host._process_combat_popups()
        px, py = _pixel(5, 5)
        popup_mgr.add_breaking.assert_called_once_with(px, py)

    def test_morale_transition_to_pinned_adds_pinned(self):
        unit = _make_real_unit("u1", tile_x=3, tile_y=4, morale=85)  # RALLYED
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        host._process_combat_popups()  # establish prev_state = RALLYED
        unit.morale.apply_delta(-60)  # 85 → 25 → PINNED
        assert MoraleSystem.get_state(unit.morale.value) == MoraleState.PINNED
        host._process_combat_popups()
        px, py = _pixel(3, 4)
        popup_mgr.add_pinned.assert_called_once_with(px, py)
        popup_mgr.add_breaking.assert_not_called()

    def test_no_morale_popup_on_first_call(self):
        # prev_state is None on the first call → no popup even if morale is low.
        unit = _make_real_unit("u1", morale=10)  # BROKEN from the start
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        host._process_combat_popups()
        popup_mgr.add_breaking.assert_not_called()
        assert unit._prev_morale_state == MoraleState.BROKEN

    def test_no_morale_popup_when_state_unchanged(self):
        unit = _make_real_unit("u1", morale=85)  # RALLYED
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        host._process_combat_popups()  # prev = RALLYED
        host._process_combat_popups()  # prev == current → no popup
        popup_mgr.add_breaking.assert_not_called()
        popup_mgr.add_pinned.assert_not_called()

    def test_morale_transition_to_wavering_emits_no_popup(self):
        # Transitioning to a non-BROKEN/non-PINNED state should emit no popup.
        unit = _make_real_unit("u1", morale=85)  # RALLYED
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        host._process_combat_popups()  # prev = RALLYED
        unit.morale.apply_delta(-30)  # 85 → 55 → WAVERING
        assert MoraleSystem.get_state(unit.morale.value) == MoraleState.WAVERING
        host._process_combat_popups()
        popup_mgr.add_breaking.assert_not_called()
        popup_mgr.add_pinned.assert_not_called()

    def test_no_morale_component_skips_morale_check(self):
        unit = _make_real_unit("u1", morale=85)
        unit.morale = None
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        host._process_combat_popups()
        popup_mgr.add_breaking.assert_not_called()
        popup_mgr.add_pinned.assert_not_called()

    def test_alive_unit_position_none_uses_zero_coords(self):
        # Alive unit with position=None → px/py stay 0.0; morale transition
        # still emits a popup at (0.0, 0.0).
        unit = _make_real_unit("u1", morale=85)
        unit.position = None
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        host._process_combat_popups()  # prev = RALLYED
        unit.morale.apply_delta(-75)  # → BROKEN
        host._process_combat_popups()
        popup_mgr.add_breaking.assert_called_once_with(0.0, 0.0)

    def test_out_of_ammo_popup_with_out_of_ammo_weapon(self):
        # Source correctly checks weapon_state.name == "OUT_OF_AMMO" (matches
        # real WeaponState enum). A mock weapon with state.name == "OUT_OF_AMMO"
        # exercises the popup branch.
        unit = _make_real_unit("u1", tile_x=5, tile_y=5, morale=85)
        mock_weapon = Mock(name="weapon")
        mock_state = Mock(name="weapon_state")
        mock_state.name = "OUT_OF_AMMO"
        mock_weapon.state = mock_state
        unit.weapon = mock_weapon

        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        host._process_combat_popups()
        px, py = _pixel(5, 5)
        popup_mgr.add_out_of_ammo.assert_called_once_with(px, py)
        assert unit._ammo_popup_shown is True

    def test_out_of_ammo_popup_shown_only_once(self):
        unit = _make_real_unit("u1", morale=85)
        mock_weapon = Mock(name="weapon")
        mock_state = Mock(name="weapon_state")
        mock_state.name = "OUT_OF_AMMO"
        mock_weapon.state = mock_state
        unit.weapon = mock_weapon

        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        host._process_combat_popups()
        host._process_combat_popups()  # already shown → should not repeat
        popup_mgr.add_out_of_ammo.assert_called_once()

    def test_ammo_popup_reset_when_weapon_not_out_of_ammo(self):
        # Real WeaponComponent in READY state → state.name == "READY" (!= "OUT_OF_AMMO")
        # → the elif branch resets _ammo_popup_shown to False.
        unit = _make_real_unit("u1", morale=85, ammo=120)  # READY weapon
        unit._ammo_popup_shown = True  # pretend it was shown previously

        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        host._process_combat_popups()
        assert unit._ammo_popup_shown is False
        popup_mgr.add_out_of_ammo.assert_not_called()

    def test_weapon_state_none_skips_ammo_check(self):
        unit = _make_real_unit("u1", morale=85)
        mock_weapon = Mock(name="weapon")
        mock_weapon.state = None
        unit.weapon = mock_weapon

        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        host._process_combat_popups()
        popup_mgr.add_out_of_ammo.assert_not_called()

    def test_no_weapon_skips_ammo_check(self):
        unit = _make_real_unit("u1", morale=85)
        unit.weapon = None

        popup_mgr = Mock(name="popup_manager")
        host = _make_host([unit], popup_manager=popup_mgr)
        host._process_combat_popups()
        popup_mgr.add_out_of_ammo.assert_not_called()

    def test_kia_popup_for_dead_unit(self):
        dead = _make_real_unit("dead1", tile_x=5, tile_y=5, hp=0, max_hp=100)
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([dead], popup_manager=popup_mgr)
        host._process_combat_popups()
        px, py = _pixel(5, 5)
        popup_mgr.add_kia.assert_called_once_with(px, py)
        assert dead._kia_popup_shown is True

    def test_kia_popup_shown_only_once(self):
        dead = _make_real_unit("dead1", hp=0, max_hp=100)
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([dead], popup_manager=popup_mgr)
        host._process_combat_popups()
        host._process_combat_popups()  # already shown → should not repeat
        popup_mgr.add_kia.assert_called_once()

    def test_kia_popup_with_position_none_uses_zero_coords(self):
        dead = _make_real_unit("dead1", hp=0, max_hp=100)
        dead.position = None
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([dead], popup_manager=popup_mgr)
        host._process_combat_popups()
        popup_mgr.add_kia.assert_called_once_with(0.0, 0.0)
        assert dead._kia_popup_shown is True

    def test_alive_unit_does_not_trigger_kia(self):
        alive = _make_real_unit("alive1", hp=100, max_hp=100)
        popup_mgr = Mock(name="popup_manager")
        host = _make_host([alive], popup_manager=popup_mgr)
        host._process_combat_popups()
        popup_mgr.add_kia.assert_not_called()
