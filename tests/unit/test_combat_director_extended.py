"""Extended unit tests for CombatDirector.

Complements test_combat_director_unit.py by targeting uncovered branches:
initialize, update, event callbacks, all handle_player_command branches
(move/hide/deploy_smoke/toggles), execute_attack full flow, on_unit_attacked
position lookup, record_stats, process_effects (all effect types),
process_movements (arrival/partial/empty), and _is_explosive_weapon edges.

Design:
- Reuses StubEventBus/StubDisplayConfig/_make_unit/_make_game_map helpers
  (copied to avoid cross-test-module import fragility).
- Uses real PositionComponent for movement tests (accurate pixel math).
- Uses Mock/MagicMock for renderer/camera/sound_system where real impls
  would require pygame display surfaces.
- No xfail/skip. Source bugs are documented in test docstrings, not worked around.
"""

from __future__ import annotations

import os
from collections import deque
from unittest.mock import MagicMock, Mock

import pytest

# Headless pygame (must precede any pygame import)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.entities.unit import Faction, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.services.combat_director import CombatDirector

# ===========================================================================
# Stub helpers (copied from test_combat_director_unit.py for isolation)
# ===========================================================================


class StubEventBus:
    """Minimal event bus stub that records published events."""

    def __init__(self):
        self.published = []
        self.subscribed = []

    def subscribe(self, event_type, handler):
        self.subscribed.append((event_type, handler))

    def publish(self, event):
        self.published.append(event)

    def publish_named(self, name, data):
        self.published.append({"name": name, "data": data})


class StubDisplayConfig:
    """Minimal display config stub."""

    pass


def _make_unit(
    unit_id, faction, tile_x=5, tile_y=5, weapon_state_name="READY", weapon_id="rifle", alive=True
):
    """Create a mock unit with sensible defaults."""
    unit = Mock()
    unit.id = unit_id
    unit.name = unit_id
    unit.faction = faction
    unit.is_alive = alive
    unit.unit_type = UnitType.INFANTRY_SQUAD
    unit.movement_mode = "normal"
    unit.role = "infantry"

    # Position
    tc = TileCoord(tile_x, tile_y)
    pos = Mock()
    pos.tile_coord = tc
    pos.pixel_position = Mock(x=tile_x * 32, y=tile_y * 32)
    pos.facing_rad = 0.0
    unit.position = pos

    # Weapon
    weapon = Mock()
    state_mock = Mock()
    state_mock.name = weapon_state_name
    weapon.state = state_mock
    weapon.primary_weapon_id = weapon_id
    weapon.ammo_remaining = 100
    weapon.fire = Mock(return_value=True)
    weapon.tick = Mock()
    unit.weapon = weapon

    # Methods
    unit.take_damage = Mock()
    unit.set_movement_mode = Mock()
    unit.update_garrison_status = Mock()
    unit.can_sneak = True
    unit.can_hide = True
    unit.can_use_smoke = False

    # Combat state
    combat_state = Mock()
    combat_state.concealment = Mock()
    combat_state.concealment.special_bonus = 0.0
    combat_state.concealment.in_smoke = False
    unit.combat_state = combat_state

    return unit


def _make_game_map(width=30, height=30):
    """Create a minimal mock game map."""
    game_map = Mock()
    game_map.width = width
    game_map.height = height
    game_map.tile_grid = MagicMock()
    game_map.objectives = []
    return game_map


def _make_director(**overrides):
    """Create a CombatDirector with stub deps."""
    bus = StubEventBus()
    dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
    for key, val in overrides.items():
        setattr(dc, key, val)
    return dc, bus


# ===========================================================================
# initialize()
# ===========================================================================


@pytest.mark.unit
class TestInitialize:
    """Test CombatDirector.initialize()."""

    def test_initialize_creates_ballistic_engine_and_pathfinder(self):
        dc, _ = _make_director()
        assert dc.ballistic_engine is None
        assert dc.pathfinder is None

        dc.initialize()

        assert dc.ballistic_engine is not None
        assert dc.pathfinder is not None

    def test_initialize_subscribes_player_command_and_unit_attacked(self):
        dc, bus = _make_director()
        dc.initialize()

        # PlayerCommand and UnitAttacked should both be subscribed
        assert len(bus.subscribed) == 2
        # Verify handler binding (handlers should be the director's private methods)
        handlers = [h for _, h in bus.subscribed]
        assert dc._on_player_command_event in handlers
        assert dc._on_unit_attacked_event in handlers


# ===========================================================================
# set_context / update
# ===========================================================================


@pytest.mark.unit
class TestUpdate:
    """Test CombatDirector.update()."""

    def test_update_caches_context_and_processes(self):
        dc, _ = _make_director()
        dc.process_movements = Mock()
        dc.process_deaths = Mock()
        unit_ready = _make_unit("u1", Faction.ALLIES, weapon_state_name="READY")
        game_map = _make_game_map()

        dc.update([unit_ready], game_map, dt=1.0 / 30.0)

        assert dc._units == [unit_ready] or dc._units == [unit_ready]
        assert dc._game_map is game_map
        dc.process_movements.assert_called_once_with([unit_ready], game_map)
        dc.process_deaths.assert_called_once_with([unit_ready], None)

    def test_update_ticks_reloading_weapon(self):
        dc, _ = _make_director()
        dc.process_movements = Mock()
        dc.process_deaths = Mock()
        unit_reloading = _make_unit("u1", Faction.ALLIES, weapon_state_name="RELOADING")
        game_map = _make_game_map()

        dc.update([unit_reloading], game_map, dt=1.0 / 30.0)

        unit_reloading.weapon.tick.assert_called_once()

    def test_update_does_not_tick_ready_weapon(self):
        dc, _ = _make_director()
        dc.process_movements = Mock()
        dc.process_deaths = Mock()
        unit_ready = _make_unit("u1", Faction.ALLIES, weapon_state_name="READY")
        game_map = _make_game_map()

        dc.update([unit_ready], game_map, dt=1.0 / 30.0)

        unit_ready.weapon.tick.assert_not_called()

    def test_update_passes_battle_stats_to_process_deaths(self):
        dc, _ = _make_director()
        dc.process_movements = Mock()
        dc.process_deaths = Mock()
        unit = _make_unit("u1", Faction.ALLIES)
        game_map = _make_game_map()
        stats = Mock()

        dc.update([unit], game_map, dt=1.0 / 30.0, battle_stats=stats)

        dc.process_deaths.assert_called_once_with([unit], stats)


# ===========================================================================
# _on_player_command_event / _on_unit_attacked_event
# ===========================================================================


@pytest.mark.unit
class TestEventCallbacks:
    """Test event callback wiring."""

    def test_on_player_command_event_dispatches_when_context_present(self):
        dc, _ = _make_director()
        dc.handle_player_command = Mock()
        unit = _make_unit("u1", Faction.ALLIES)
        game_map = _make_game_map()
        dc._units = [unit]
        dc._game_map = game_map
        data = {"command": "stop", "unit_ids": ["u1"]}

        dc._on_player_command_event(data)

        dc.handle_player_command.assert_called_once_with(data, [unit], game_map)

    def test_on_player_command_event_skips_when_units_empty(self):
        dc, _ = _make_director()
        dc.handle_player_command = Mock()
        dc._units = []
        dc._game_map = _make_game_map()

        dc._on_player_command_event({"command": "stop"})

        dc.handle_player_command.assert_not_called()

    def test_on_player_command_event_skips_when_game_map_none(self):
        dc, _ = _make_director()
        dc.handle_player_command = Mock()
        dc._units = [_make_unit("u1", Faction.ALLIES)]
        dc._game_map = None

        dc._on_player_command_event({"command": "stop"})

        dc.handle_player_command.assert_not_called()

    def test_on_unit_attacked_event_dispatches_to_on_unit_attacked(self):
        dc, _ = _make_director()
        dc.on_unit_attacked = Mock()
        data = {"target_id": "u1", "damage": 10}

        dc._on_unit_attacked_event(data)

        dc.on_unit_attacked.assert_called_once_with(data)


# ===========================================================================
# handle_player_command branches
# ===========================================================================


@pytest.mark.unit
class TestHandlePlayerCommandMove:
    """Test move command branch."""

    def test_move_command_with_path_sets_move_orders(self):
        dc, _ = _make_director()
        dc.pathfinder = Mock()
        # find_path returns a multi-element path so [1:] is non-empty
        dc.pathfinder.find_path = Mock(
            return_value=[TileCoord(5, 5), TileCoord(6, 5), TileCoord(7, 5)]
        )
        unit = _make_unit("u1", Faction.ALLIES, 5, 5)
        game_map = _make_game_map()

        dc.handle_player_command(
            {"command": "move", "unit_ids": ["u1"], "target": (7, 5)},
            [unit],
            game_map,
        )

        assert "u1" in dc._move_orders
        order = dc._move_orders["u1"]
        assert "path" in order
        # deque should contain the tail of the path (excluding start)
        assert list(order["path"]) == [TileCoord(6, 5), TileCoord(7, 5)]
        assert order["current_idx"] == 0

    def test_move_command_without_pathfinder_skips(self):
        dc, _ = _make_director()
        dc.pathfinder = None
        unit = _make_unit("u1", Faction.ALLIES, 5, 5)
        game_map = _make_game_map()

        dc.handle_player_command(
            {"command": "move", "unit_ids": ["u1"], "target": (7, 5)},
            [unit],
            game_map,
        )

        assert "u1" not in dc._move_orders

    def test_move_command_no_path_skips(self):
        dc, _ = _make_director()
        dc.pathfinder = Mock()
        dc.pathfinder.find_path = Mock(return_value=None)
        unit = _make_unit("u1", Faction.ALLIES, 5, 5)
        game_map = _make_game_map()

        dc.handle_player_command(
            {"command": "move", "unit_ids": ["u1"], "target": (7, 5)},
            [unit],
            game_map,
        )

        assert "u1" not in dc._move_orders


@pytest.mark.unit
class TestHandlePlayerCommandToggles:
    """Test defend/fast_move/sneak toggle-off and unknown command."""

    def test_fast_move_command_toggles_off_when_already_fast(self):
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)
        unit.movement_mode = "fast_move"

        dc.handle_player_command(
            {"command": "fast_move", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        unit.set_movement_mode.assert_called_once_with("normal")

    def test_sneak_command_toggles_off_when_already_sneak(self):
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)
        unit.movement_mode = "sneak"
        unit.can_sneak = True

        dc.handle_player_command(
            {"command": "sneak", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        unit.set_movement_mode.assert_called_once_with("normal")

    def test_sneak_command_warns_when_cannot_sneak(self):
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)
        unit.movement_mode = "normal"
        unit.can_sneak = False

        dc.handle_player_command(
            {"command": "sneak", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        unit.set_movement_mode.assert_not_called()

    def test_unknown_command_is_no_op(self):
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)

        dc.handle_player_command(
            {"command": "dance", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        unit.set_movement_mode.assert_not_called()
        assert "u1" not in dc._move_orders


@pytest.mark.unit
class TestHandlePlayerCommandHide:
    """Test hide command branch."""

    def test_hide_command_enters_defend_with_concealment_bonus(self):
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)
        unit.movement_mode = "normal"
        unit.can_hide = True
        dc._move_orders["u1"] = {"path": deque([TileCoord(6, 5)])}

        dc.handle_player_command(
            {"command": "hide", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )

        unit.set_movement_mode.assert_called_once_with("defend", duration_ticks=-1)
        # Concealment bonus applied
        assert unit.combat_state.concealment.special_bonus == pytest.approx(0.2)
        # Move order cleared
        assert "u1" not in dc._move_orders

    def test_hide_command_skipped_when_cannot_hide(self):
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)
        unit.movement_mode = "normal"
        unit.can_hide = False

        dc.handle_player_command(
            {"command": "hide", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        unit.set_movement_mode.assert_not_called()
        # Concealment bonus unchanged
        assert unit.combat_state.concealment.special_bonus == 0.0

    def test_hide_command_skipped_when_already_defending(self):
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)
        unit.movement_mode = "defend"
        unit.can_hide = True

        dc.handle_player_command(
            {"command": "hide", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        # Already defending → no mode change, no bonus
        unit.set_movement_mode.assert_not_called()


@pytest.mark.unit
class TestHandlePlayerCommandDeploySmoke:
    """Test deploy_smoke command branch."""

    def test_deploy_smoke_warns_when_unit_cannot_use_smoke(self):
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)
        unit.can_use_smoke = False

        dc.handle_player_command(
            {"command": "deploy_smoke", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        # No smoke effect queued
        assert all(e["type"] != "smoke" for e in dc._pending_effects)
        assert unit.combat_state.concealment.in_smoke is False

    def test_deploy_smoke_warns_when_unit_has_no_weapon(self):
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)
        unit.can_use_smoke = True
        unit.weapon = None  # no weapon system

        dc.handle_player_command(
            {"command": "deploy_smoke", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        assert all(e["type"] != "smoke" for e in dc._pending_effects)

    def test_deploy_smoke_with_capability_and_successful_deploy(self):
        """When unit.ammo_inventory.deploy_smoke returns truthy, smoke effect is queued."""
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)
        unit.can_use_smoke = True
        game_map = _make_game_map()

        # Source calls unit.ammo_inventory.deploy_smoke((tc.x, tc.y)).
        ammo_inv = Mock(name="ammo_inventory")
        ammo_inv.deploy_smoke = Mock(return_value={"position": (5, 5)})
        unit.ammo_inventory = ammo_inv

        dc.handle_player_command(
            {"command": "deploy_smoke", "unit_ids": ["u1"]},
            [unit],
            game_map,
        )

        smoke_effects = [e for e in dc._pending_effects if e["type"] == "smoke"]
        assert len(smoke_effects) == 1
        assert smoke_effects[0]["radius"] == 144.0
        assert unit.combat_state.concealment.in_smoke is True

    def test_deploy_smoke_continues_on_deploy_exception(self):
        """When unit.ammo_inventory.deploy_smoke raises, smoke effect is still queued
        (exception is caught and visual effect proceeds)."""
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)
        unit.can_use_smoke = True
        game_map = _make_game_map()

        # Source wraps ammo_inv.deploy_smoke() in try/except; raising here
        # exercises the except branch (visual effect still proceeds).
        ammo_inv = Mock(name="ammo_inventory")
        ammo_inv.deploy_smoke = Mock(side_effect=RuntimeError("boom"))
        unit.ammo_inventory = ammo_inv

        dc.handle_player_command(
            {"command": "deploy_smoke", "unit_ids": ["u1"]},
            [unit],
            game_map,
        )

        smoke_effects = [e for e in dc._pending_effects if e["type"] == "smoke"]
        assert len(smoke_effects) == 1
        assert unit.combat_state.concealment.in_smoke is True

    def test_deploy_smoke_skips_when_deploy_returns_falsy(self):
        """When unit.ammo_inventory.deploy_smoke returns None/False, the unit is
        skipped (continue) and no smoke effect is queued."""
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES)
        unit.can_use_smoke = True
        game_map = _make_game_map()

        # Source checks unit.ammo_inventory attribute (not AmmoInventory class
        # method). Attach a mock ammo_inventory whose deploy_smoke returns None.
        ammo_inv = Mock(name="ammo_inventory")
        ammo_inv.deploy_smoke = Mock(return_value=None)
        unit.ammo_inventory = ammo_inv

        dc.handle_player_command(
            {"command": "deploy_smoke", "unit_ids": ["u1"]},
            [unit],
            game_map,
        )

        smoke_effects = [e for e in dc._pending_effects if e["type"] == "smoke"]
        assert len(smoke_effects) == 0
        assert unit.combat_state.concealment.in_smoke is False


# ===========================================================================
# execute_attack
# ===========================================================================


def _make_shot_result(hit=True, damage=25.0, kill=False):
    """Create a Mock ShotResult-like object."""
    r = Mock()
    r.hit = hit
    r.damage_dealt = damage
    r.is_killing_blow = kill
    return r


@pytest.mark.unit
class TestExecuteAttackFull:
    """Test execute_attack full flow (not just early returns)."""

    def test_execute_attack_normal_hit_publishes_events_and_damage(self):
        dc, bus = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(return_value=_make_shot_result(hit=True, damage=25.0))
        dc._game_map = _make_game_map()
        attacker = _make_unit("a1", Faction.ALLIES, 5, 5, weapon_id="rifle")
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        # Events: UnitAttacked + ProjectileFired (named)
        assert len(bus.published) == 2
        # UnitAttacked first
        ua = bus.published[0]
        assert ua["attacker_id"] == "a1"
        assert ua["target_id"] == "e1"
        assert ua["is_hit"] is True
        assert ua["damage"] == 25.0
        # ProjectileFired named event
        pf = bus.published[1]
        assert pf["name"] == "ProjectileFired"
        assert pf["data"]["weapon_type"] == "bullet"
        assert pf["data"]["is_hit"] is True
        # Damage applied
        target.take_damage.assert_called_once_with(25)
        # Hit + muzzle effects queued
        types = [e["type"] for e in dc._pending_effects]
        assert "hit" in types
        assert "muzzle" in types

    def test_execute_attack_kill_shot_publishes_unit_killed(self):
        dc, bus = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(
            return_value=_make_shot_result(hit=True, damage=100.0, kill=True)
        )
        dc._game_map = _make_game_map()
        attacker = _make_unit("a1", Faction.ALLIES, weapon_id="rifle")
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        # UnitAttacked + ProjectileFired + UnitKilled
        assert len(bus.published) == 3
        killed_event = bus.published[2]
        assert killed_event["unit_id"] == "e1"
        assert killed_event["attacker_id"] == "a1"

    def test_execute_attack_kill_when_target_already_dead(self):
        """is_killing_blow False but target.is_alive False → still publishes UnitKilled."""
        dc, bus = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(
            return_value=_make_shot_result(hit=True, damage=25.0, kill=False)
        )
        dc._game_map = _make_game_map()
        attacker = _make_unit("a1", Faction.ALLIES)
        target = _make_unit("e1", Faction.AXIS, 6, 5, alive=False)

        dc.execute_attack(attacker, target)

        assert len(bus.published) == 3  # UnitAttacked + ProjectileFired + UnitKilled

    def test_execute_attack_miss_no_hit_effects(self):
        dc, bus = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(
            return_value=_make_shot_result(hit=False, damage=0.0)
        )
        dc._game_map = _make_game_map()
        attacker = _make_unit("a1", Faction.ALLIES)
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        # Still publishes UnitAttacked + ProjectileFired
        assert len(bus.published) == 2
        # No hit/muzzle effects (only queued on hit)
        types = [e["type"] for e in dc._pending_effects]
        assert "hit" not in types
        assert "muzzle" not in types
        # No damage applied
        target.take_damage.assert_not_called()

    def test_execute_attack_weapon_type_shell_for_tank_cannon(self):
        dc, bus = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(return_value=_make_shot_result(hit=True, damage=50.0))
        dc._game_map = _make_game_map()
        attacker = _make_unit("a1", Faction.ALLIES, weapon_id="tank_cannon")
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        pf = next(e for e in bus.published if isinstance(e, dict) and e.get("name") == "ProjectileFired")
        assert pf["data"]["weapon_type"] == "shell"

    def test_execute_attack_weapon_type_shell_for_at_gun(self):
        dc, bus = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(return_value=_make_shot_result(hit=True, damage=40.0))
        dc._game_map = _make_game_map()
        attacker = _make_unit("a1", Faction.ALLIES, weapon_id="at_gun_57mm")
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        pf = next(e for e in bus.published if isinstance(e, dict) and e.get("name") == "ProjectileFired")
        assert pf["data"]["weapon_type"] == "shell"

    def test_execute_attack_weapon_type_rocket_for_bazooka(self):
        dc, bus = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(return_value=_make_shot_result(hit=True, damage=45.0))
        dc._game_map = _make_game_map()
        attacker = _make_unit("a1", Faction.ALLIES, weapon_id="bazooka_m1")
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        pf = next(e for e in bus.published if isinstance(e, dict) and e.get("name") == "ProjectileFired")
        assert pf["data"]["weapon_type"] == "rocket"

    def test_execute_attack_weapon_type_mortar(self):
        dc, bus = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(return_value=_make_shot_result(hit=True, damage=32.0))
        dc._game_map = _make_game_map()
        attacker = _make_unit("a1", Faction.ALLIES, weapon_id="81mm_mortar")
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        pf = next(e for e in bus.published if isinstance(e, dict) and e.get("name") == "ProjectileFired")
        assert pf["data"]["weapon_type"] == "mortar"

    def test_execute_attack_weapon_type_bullet_for_mg(self):
        dc, bus = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(return_value=_make_shot_result(hit=True, damage=30.0))
        dc._game_map = _make_game_map()
        attacker = _make_unit("a1", Faction.ALLIES, weapon_id="mg42")
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        pf = next(e for e in bus.published if isinstance(e, dict) and e.get("name") == "ProjectileFired")
        assert pf["data"]["weapon_type"] == "bullet"

    def test_execute_attack_sound_play_shot_without_camera(self):
        dc, _ = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(return_value=_make_shot_result(hit=True, damage=25.0))
        dc._game_map = _make_game_map()
        sound = Mock(spec=["play_shot", "play_hit", "play_death", "play_footstep", "play_sound_with_distance"])
        dc.sound_system = sound
        attacker = _make_unit("a1", Faction.ALLIES, weapon_id="rifle")
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        sound.play_shot.assert_called_once_with("rifle")

    def test_execute_attack_sound_play_sound_with_distance_with_camera(self):
        dc, _ = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(return_value=_make_shot_result(hit=True, damage=25.0))
        dc._game_map = _make_game_map()
        sound = Mock(spec=["play_shot", "play_hit", "play_death", "play_footstep", "play_sound_with_distance"])
        dc.sound_system = sound
        dc._camera_position = Mock(x=100, y=100)
        attacker = _make_unit("a1", Faction.ALLIES, weapon_id="mg42")
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        sound.play_sound_with_distance.assert_called_once()
        call_args = sound.play_sound_with_distance.call_args
        assert call_args[0][0] == "MG_BURST"  # mg weapon → MG_BURST sound

    def test_execute_attack_sound_pistol_with_camera(self):
        dc, _ = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(return_value=_make_shot_result(hit=True, damage=12.0))
        dc._game_map = _make_game_map()
        sound = Mock(spec=["play_shot", "play_hit", "play_death", "play_footstep", "play_sound_with_distance"])
        dc.sound_system = sound
        dc._camera_position = Mock(x=100, y=100)
        attacker = _make_unit("a1", Faction.ALLIES, weapon_id="pistol_45")
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        sound.play_sound_with_distance.assert_called_once()
        assert sound.play_sound_with_distance.call_args[0][0] == "PISTOL_SHOT"

    def test_execute_attack_no_sound_when_fire_returns_false(self):
        dc, _ = _make_director()
        dc.ballistic_engine = Mock()
        dc.ballistic_engine.calculate_shot = Mock(return_value=_make_shot_result(hit=True, damage=25.0))
        dc._game_map = _make_game_map()
        sound = Mock(spec=["play_shot", "play_hit", "play_death", "play_footstep", "play_sound_with_distance"])
        dc.sound_system = sound
        attacker = _make_unit("a1", Faction.ALLIES, weapon_id="rifle")
        attacker.weapon.fire = Mock(return_value=False)  # weapon failed to fire
        target = _make_unit("e1", Faction.AXIS, 6, 5)

        dc.execute_attack(attacker, target)

        sound.play_shot.assert_not_called()


# ===========================================================================
# on_unit_attacked position lookup
# ===========================================================================


@pytest.mark.unit
class TestOnUnitAttackedPositionLookup:
    """Test on_unit_attacked position resolution from units list."""

    def test_position_resolved_from_units_when_not_in_data(self):
        dc, _ = _make_director()
        unit = _make_unit("u1", Faction.ALLIES, 7, 3)
        dc._units = [unit]

        dc.on_unit_attacked({"target_id": "u1", "damage": 10, "killed": False})

        assert len(dc._pending_effects) == 1
        effect = dc._pending_effects[0]
        assert effect["position"] is unit.position.pixel_position

    def test_position_none_when_unit_not_found(self):
        dc, _ = _make_director()
        dc._units = [_make_unit("other", Faction.ALLIES)]

        dc.on_unit_attacked({"target_id": "missing", "damage": 10, "killed": False})

        assert len(dc._pending_effects) == 1
        assert dc._pending_effects[0]["position"] is None

    def test_kill_shot_field_triggers_death_effect(self):
        dc, _ = _make_director()

        dc.on_unit_attacked({"target_id": "u1", "damage": 50, "kill_shot": True})

        types = [e["type"] for e in dc._pending_effects]
        assert "hit" in types
        assert "death" in types


# ===========================================================================
# record_stats
# ===========================================================================


@pytest.mark.unit
class TestRecordStats:
    """Test record_stats method."""

    def test_record_stats_none_battle_stats_early_return(self):
        dc, _ = _make_director()
        attacker = _make_unit("a1", Faction.ALLIES)
        # Should not raise
        dc.record_stats({"attacker_id": "a1"}, [attacker], None)

    def test_record_stats_with_damage_records_shot_and_damage(self):
        dc, _ = _make_director()
        attacker = _make_unit("a1", Faction.ALLIES)
        target = _make_unit("e1", Faction.AXIS)
        battle_stats = Mock()

        dc.record_stats(
            {"attacker_id": "a1", "target_id": "e1", "damage": 25, "killed": False},
            [attacker, target],
            battle_stats,
        )

        battle_stats.record_shot.assert_called_once_with("allies", hit=True)
        battle_stats.record_damage.assert_called_once_with("allies", 25)
        battle_stats.record_kill.assert_not_called()

    def test_record_stats_with_kill_records_kill_and_unit_lost(self):
        dc, _ = _make_director()
        attacker = _make_unit("a1", Faction.ALLIES)
        target = _make_unit("e1", Faction.AXIS)
        battle_stats = Mock()

        dc.record_stats(
            {"attacker_id": "a1", "target_id": "e1", "damage": 100, "killed": True},
            [attacker, target],
            battle_stats,
        )

        battle_stats.record_shot.assert_called_once_with("allies", hit=True)
        battle_stats.record_damage.assert_called_once_with("allies", 100)
        battle_stats.record_kill.assert_called_once_with("allies")
        # Target is AXIS → record_unit_lost("axis")
        battle_stats.record_unit_lost.assert_called_once_with("axis")

    def test_record_stats_no_attacker_no_records(self):
        dc, _ = _make_director()
        target = _make_unit("e1", Faction.AXIS)
        battle_stats = Mock()

        dc.record_stats(
            {"attacker_id": "missing", "target_id": "e1", "damage": 25},
            [target],
            battle_stats,
        )

        battle_stats.record_shot.assert_not_called()
        battle_stats.record_damage.assert_not_called()

    def test_record_stats_axis_attacker(self):
        dc, _ = _make_director()
        attacker = _make_unit("a1", Faction.AXIS)
        target = _make_unit("e1", Faction.ALLIES)
        battle_stats = Mock()

        dc.record_stats(
            {"attacker_id": "a1", "target_id": "e1", "damage": 25, "killed": True},
            [attacker, target],
            battle_stats,
        )

        battle_stats.record_shot.assert_called_once_with("axis", hit=True)
        # Target is ALLIES → target_faction = "allies"
        battle_stats.record_unit_lost.assert_called_once_with("allies")

    def test_record_stats_zero_damage_miss(self):
        dc, _ = _make_director()
        attacker = _make_unit("a1", Faction.ALLIES)
        battle_stats = Mock()

        dc.record_stats(
            {"attacker_id": "a1", "damage": 0, "killed": False},
            [attacker],
            battle_stats,
        )

        battle_stats.record_shot.assert_called_once_with("allies", hit=False)
        battle_stats.record_damage.assert_not_called()


# ===========================================================================
# process_effects
# ===========================================================================


def _make_renderer():
    """Create a MagicMock renderer with all spawn methods."""
    renderer = MagicMock()
    return renderer


def _make_camera():
    """Create a MagicMock camera with shake."""
    camera = MagicMock()
    return camera


@pytest.mark.unit
class TestProcessEffects:
    """Test process_effects method."""

    def test_process_effects_no_renderer_clears_queue(self):
        dc, _ = _make_director()
        dc._pending_effects.append({"type": "hit", "position": Mock(x=0, y=0), "damage": 10, "target_id": "u1"})

        dc.process_effects(renderer=None)

        assert dc._pending_effects == []

    def test_process_effects_renderer_without_spawn_hit_flash_clears(self):
        dc, _ = _make_director()
        renderer = Mock(spec=[])  # no spawn_hit_flash attribute
        dc._pending_effects.append({"type": "hit", "position": Mock(x=0, y=0), "damage": 10, "target_id": "u1"})

        dc.process_effects(renderer=renderer)

        assert dc._pending_effects == []

    def test_process_effects_hit_non_explosive(self):
        dc, _ = _make_director()
        renderer = _make_renderer()
        camera = _make_camera()
        pos = Vec2(100, 100)
        dc._pending_effects.append(
            {
                "type": "hit",
                "target_id": "u1",
                "position": pos,
                "damage": 25,
                "is_kill": False,
                "weapon_id": "rifle",
            }
        )

        dc.process_effects(renderer=renderer, camera=camera)

        renderer.spawn_hit_flash.assert_called_once_with("u1")
        renderer.spawn_damage_number.assert_called_once_with(pos, 25, False)
        renderer.spawn_shell_casing.assert_called_once_with(100, 100)
        renderer.spawn_dirt_splash.assert_called_once_with(100, 100, count=8)
        renderer.spawn_blood_pool.assert_not_called()  # not a kill
        renderer.spawn_hit_marker.assert_called_once_with(100, 100, damage_type="normal")
        # Non-explosive → small explosion
        renderer.spawn_explosion.assert_called_once_with(pos, "small")
        camera.shake.assert_called_once_with(1.5, 0.1)
        # Non-kill → no pale red flash
        renderer.trigger_flash.assert_not_called()
        assert dc._pending_effects == []

    def test_process_effects_hit_explosive_large_explosion(self):
        dc, bus = _make_director()
        renderer = _make_renderer()
        camera = _make_camera()
        pos = Vec2(100, 100)
        dc._pending_effects.append(
            {
                "type": "hit",
                "target_id": "u1",
                "position": pos,
                "damage": 50,
                "is_kill": False,
                "weapon_id": "tank_cannon",
            }
        )

        dc.process_effects(renderer=renderer, camera=camera)

        renderer.spawn_explosion.assert_called_once_with(pos, "large")
        camera.shake.assert_called_once_with(3.0, 0.15)
        renderer.trigger_flash.assert_called_once_with((255, 240, 200), 0.5, 0.15)
        # Explosion event published
        explosion_events = [e for e in bus.published if isinstance(e, dict) and e.get("name") == "Explosion"]
        assert len(explosion_events) == 1
        assert explosion_events[0]["data"]["intensity"] == 4.0

    def test_process_effects_hit_kill_triggers_pale_red_flash(self):
        dc, _ = _make_director()
        renderer = _make_renderer()
        camera = _make_camera()
        pos = Vec2(100, 100)
        dc._pending_effects.append(
            {
                "type": "hit",
                "target_id": "u1",
                "position": pos,
                "damage": 100,
                "is_kill": True,
                "weapon_id": "rifle",
            }
        )

        dc.process_effects(renderer=renderer, camera=camera)

        # Kill → blood pool spawned
        renderer.spawn_blood_pool.assert_called_once_with(100, 100, size=10)
        # Kill → hit marker critical
        renderer.spawn_hit_marker.assert_called_once_with(100, 100, damage_type="critical")
        # Non-explosive + kill → pale red flash
        renderer.trigger_flash.assert_called_once_with((255, 100, 100), 0.3, 0.12)

    def test_process_effects_hit_kill_and_explosive_dual_flash(self):
        dc, _ = _make_director()
        renderer = _make_renderer()
        camera = _make_camera()
        pos = Vec2(100, 100)
        dc._pending_effects.append(
            {
                "type": "hit",
                "target_id": "u1",
                "position": pos,
                "damage": 100,
                "is_kill": True,
                "weapon_id": "mortar_81mm",
            }
        )

        dc.process_effects(renderer=renderer, camera=camera)

        # Both flashes: warm white (explosive) + pale red (kill)
        assert renderer.trigger_flash.call_count == 2
        renderer.trigger_flash.assert_any_call((255, 240, 200), 0.5, 0.15)
        renderer.trigger_flash.assert_any_call((255, 100, 100), 0.3, 0.12)

    def test_process_effects_hit_with_sound_system(self):
        dc, _ = _make_director()
        renderer = _make_renderer()
        sound = Mock(spec=["play_shot", "play_hit", "play_death", "play_footstep", "play_sound_with_distance"])
        dc.sound_system = sound
        pos = Vec2(100, 100)
        dc._pending_effects.append(
            {
                "type": "hit",
                "target_id": "u1",
                "position": pos,
                "damage": 25,
                "is_kill": True,
                "weapon_id": "rifle",
            }
        )

        dc.process_effects(renderer=renderer)

        sound.play_hit.assert_called_once_with(is_critical=True)

    def test_process_effects_muzzle_effect(self):
        dc, _ = _make_director()
        renderer = _make_renderer()
        pos = Vec2(50, 50)
        dc._pending_effects.append(
            {"type": "muzzle", "position": pos, "direction": 1.57}
        )

        dc.process_effects(renderer=renderer)

        renderer.spawn_muzzle_flash.assert_called_once_with(pos, 1.57)

    def test_process_effects_death_effect(self):
        dc, _ = _make_director()
        renderer = _make_renderer()
        sound = Mock(spec=["play_shot", "play_hit", "play_death", "play_footstep", "play_sound_with_distance"])
        dc.sound_system = sound
        pos = Vec2(80, 80)
        dc._pending_effects.append(
            {"type": "death", "unit_id": "u1", "position": pos}
        )

        dc.process_effects(renderer=renderer)

        renderer.spawn_death_effect.assert_called_once_with("u1", pos)
        sound.play_death.assert_called_once()

    def test_process_effects_smoke_effect(self):
        dc, _ = _make_director()
        renderer = _make_renderer()
        pos = Vec2(120, 120)
        dc._pending_effects.append(
            {"type": "smoke", "position": pos, "radius": 144.0}
        )

        dc.process_effects(renderer=renderer)

        renderer.spawn_smoke_screen.assert_called_once_with(pos, radius=144.0)

    def test_process_effects_smoke_default_radius(self):
        dc, _ = _make_director()
        renderer = _make_renderer()
        pos = Vec2(120, 120)
        dc._pending_effects.append({"type": "smoke", "position": pos})

        dc.process_effects(renderer=renderer)

        renderer.spawn_smoke_screen.assert_called_once_with(pos, radius=64.0)

    def test_process_effects_clears_queue_after_processing(self):
        dc, _ = _make_director()
        renderer = _make_renderer()
        dc._pending_effects.extend(
            [
                {"type": "muzzle", "position": Vec2(0, 0), "direction": 0},
                {"type": "smoke", "position": Vec2(0, 0), "radius": 50},
            ]
        )

        dc.process_effects(renderer=renderer)

        assert dc._pending_effects == []


# ===========================================================================
# process_movements
# ===========================================================================


def _make_unit_with_real_position(unit_id, faction, tile_x, tile_y, pixel_offset=None):
    """Create a unit with a real PositionComponent for accurate pixel math."""
    unit = Mock()
    unit.id = unit_id
    unit.name = unit_id
    unit.faction = faction
    unit.is_alive = True
    unit.unit_type = UnitType.INFANTRY_SQUAD
    unit.movement_mode = "normal"

    pos = PositionComponent(tile_coord=TileCoord(tile_x, tile_y))
    if pixel_offset is not None:
        pos.set_pixel_offset(pixel_offset)
    unit.position = pos

    unit.update_garrison_status = Mock()
    unit.weapon = Mock()
    state_mock = Mock()
    state_mock.name = "READY"
    unit.weapon.state = state_mock
    return unit


@pytest.mark.unit
class TestProcessMovements:
    """Test process_movements method."""

    def test_process_movements_no_order_skips(self):
        dc, _ = _make_director()
        unit = _make_unit_with_real_position("u1", Faction.ALLIES, 5, 5)
        game_map = _make_game_map()

        dc.process_movements([unit], game_map)

        unit.update_garrison_status.assert_not_called()

    def test_process_movements_empty_path_deletes_order(self):
        dc, _ = _make_director()
        unit = _make_unit_with_real_position("u1", Faction.ALLIES, 5, 5)
        game_map = _make_game_map()
        dc._move_orders["u1"] = {"path": deque([])}

        dc.process_movements([unit], game_map)

        assert "u1" not in dc._move_orders

    def test_process_movements_arrival_updates_tile_and_pops(self):
        dc, _ = _make_director()
        # Unit at center of tile (5,5): pixel_offset (24,24) → pixel_position (264,264)
        # Target tile (5,5) center: (5*48+24, 5*48+24) = (264,264) → dist=0 → arrival
        unit = _make_unit_with_real_position(
            "u1", Faction.ALLIES, 5, 5, pixel_offset=Vec2(24.0, 24.0)
        )
        game_map = _make_game_map()
        dc._move_orders["u1"] = {"path": deque([TileCoord(5, 5)])}

        dc.process_movements([unit], game_map)

        unit.update_garrison_status.assert_called_once_with(game_map)
        # Path is now empty → order deleted
        assert "u1" not in dc._move_orders

    def test_process_movements_arrival_with_remaining_path_keeps_order(self):
        dc, _ = _make_director()
        unit = _make_unit_with_real_position(
            "u1", Faction.ALLIES, 5, 5, pixel_offset=Vec2(24.0, 24.0)
        )
        game_map = _make_game_map()
        dc._move_orders["u1"] = {
            "path": deque([TileCoord(5, 5), TileCoord(6, 5)])
        }

        dc.process_movements([unit], game_map)

        # First tile popped, second remains
        assert "u1" in dc._move_orders
        assert list(dc._move_orders["u1"]["path"]) == [TileCoord(6, 5)]

    def test_process_movements_partial_move_advances_and_sets_facing(self):
        dc, _ = _make_director()
        # Unit at tile (5,5) origin: pixel_position (240,240)
        # Target tile (10,5) center: (10*48+24, 5*48+24) = (504,264)
        # dist >> move_pixels → partial move
        unit = _make_unit_with_real_position("u1", Faction.ALLIES, 5, 5)
        game_map = _make_game_map()
        dc._move_orders["u1"] = {"path": deque([TileCoord(10, 5)])}

        original_facing = unit.position.facing_rad
        dc.process_movements([unit], game_map)

        # Tile coord recomputed (may still be 5,5 due to small step)
        unit.update_garrison_status.assert_called_once_with(game_map)
        # Facing should be updated toward target
        assert unit.position.facing_rad != original_facing
        # Order still present (path not empty)
        assert "u1" in dc._move_orders
        assert dc._move_orders["u1"]["path"][0] == TileCoord(10, 5)

    def test_process_movements_arrival_plays_footstep_terrain_grass(self):
        dc, _ = _make_director()
        sound = Mock(spec=["play_shot", "play_hit", "play_death", "play_footstep", "play_sound_with_distance"])
        dc.sound_system = sound
        unit = _make_unit_with_real_position(
            "u1", Faction.ALLIES, 5, 5, pixel_offset=Vec2(24.0, 24.0)
        )
        # tile_grid returns a value that is neither 1 nor 2 → grass
        game_map = _make_game_map()
        game_map.tile_grid = MagicMock()
        game_map.tile_grid.__getitem__ = Mock(return_value=0)
        dc._move_orders["u1"] = {"path": deque([TileCoord(5, 5)])}

        dc.process_movements([unit], game_map)

        sound.play_footstep.assert_called_once_with("grass")

    def test_process_movements_arrival_plays_footstep_terrain_road(self):
        dc, _ = _make_director()
        sound = Mock(spec=["play_shot", "play_hit", "play_death", "play_footstep", "play_sound_with_distance"])
        dc.sound_system = sound
        unit = _make_unit_with_real_position(
            "u1", Faction.ALLIES, 5, 5, pixel_offset=Vec2(24.0, 24.0)
        )
        game_map = _make_game_map()
        game_map.tile_grid = MagicMock()
        game_map.tile_grid.__getitem__ = Mock(return_value=1)  # road
        dc._move_orders["u1"] = {"path": deque([TileCoord(5, 5)])}

        dc.process_movements([unit], game_map)

        sound.play_footstep.assert_called_once_with("road")

    def test_process_movements_arrival_plays_footstep_terrain_wood(self):
        dc, _ = _make_director()
        sound = Mock(spec=["play_shot", "play_hit", "play_death", "play_footstep", "play_sound_with_distance"])
        dc.sound_system = sound
        unit = _make_unit_with_real_position(
            "u1", Faction.ALLIES, 5, 5, pixel_offset=Vec2(24.0, 24.0)
        )
        game_map = _make_game_map()
        game_map.tile_grid = MagicMock()
        game_map.tile_grid.__getitem__ = Mock(return_value=2)  # wood
        dc._move_orders["u1"] = {"path": deque([TileCoord(5, 5)])}

        dc.process_movements([unit], game_map)

        sound.play_footstep.assert_called_once_with("wood")

    def test_process_movements_no_sound_system_no_footstep(self):
        dc, _ = _make_director()
        dc.sound_system = None
        unit = _make_unit_with_real_position(
            "u1", Faction.ALLIES, 5, 5, pixel_offset=Vec2(24.0, 24.0)
        )
        game_map = _make_game_map()
        dc._move_orders["u1"] = {"path": deque([TileCoord(5, 5)])}

        # Should not raise
        dc.process_movements([unit], game_map)
        assert "u1" not in dc._move_orders


# ===========================================================================
# _is_explosive_weapon (edge cases)
# ===========================================================================


@pytest.mark.unit
class TestIsExplosiveWeaponEdges:
    """Test _is_explosive_weapon for all keyword branches."""

    def test_at_gun_is_explosive(self):
        assert CombatDirector._is_explosive_weapon("at_gun_57mm") is True

    def test_piat_is_explosive(self):
        assert CombatDirector._is_explosive_weapon("piat_m1") is True

    def test_panzerschreck_is_explosive(self):
        assert CombatDirector._is_explosive_weapon("panzerschreck") is True

    def test_panzerfaust_is_explosive(self):
        assert CombatDirector._is_explosive_weapon("panzerfaust_60") is True

    def test_empty_string_not_explosive(self):
        assert CombatDirector._is_explosive_weapon("") is False

    def test_case_insensitive_match(self):
        assert CombatDirector._is_explosive_weapon("TANK_CANNON") is True

    def test_sniper_rifle_not_explosive(self):
        assert CombatDirector._is_explosive_weapon("sniper_rifle") is False


# ===========================================================================
# tick_weapon_reload (additional edge)
# ===========================================================================


@pytest.mark.unit
class TestTickWeaponReloadEdges:
    """Test tick_weapon_reload with mixed states."""

    def test_mixed_units_only_reloading_ticked(self):
        dc, _ = _make_director()
        ready_unit = _make_unit("u1", Faction.ALLIES, weapon_state_name="READY")
        reloading_unit = _make_unit("u2", Faction.ALLIES, weapon_state_name="RELOADING")
        jammed_unit = _make_unit("u3", Faction.ALLIES, weapon_state_name="JAMMED")

        dc.tick_weapon_reload([ready_unit, reloading_unit, jammed_unit])

        ready_unit.weapon.tick.assert_not_called()
        reloading_unit.weapon.tick.assert_called_once()
        jammed_unit.weapon.tick.assert_not_called()
