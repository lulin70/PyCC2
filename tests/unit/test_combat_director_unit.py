"""
Unit Tests for CombatDirector

Tests the combat director's command routing, event publishing,
and weapon selection logic.
"""

from unittest.mock import MagicMock, Mock

import numpy as np
import pytest

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, UnitType
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.combat_director import CombatDirector

# ===========================================================================
# Stub helpers
# ===========================================================================


class StubEventBus:
    """Minimal event bus stub that records published events."""

    def __init__(self):
        self.published = []

    def subscribe(self, event_type, handler):
        pass

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

    # Position
    tc = TileCoord(tile_x, tile_y)
    pos = Mock()
    pos.tile_coord = tc
    pos.pixel_position = Mock(x=tile_x * 32, y=tile_y * 32)
    pos.facing_rad = 0.0
    unit.position = pos

    # Weapon — use a real-like state mock so .name works correctly
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


# ===========================================================================
# Tests
# ===========================================================================


@pytest.mark.unit
class TestCombatDirectorInit:
    """Test CombatDirector initialization."""

    def test_default_state(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        assert dc._units == []
        assert dc._game_map is None
        assert dc._pending_effects == []
        assert dc._move_orders == {}

    def test_set_context(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        units = [_make_unit("u1", Faction.ALLIES)]
        game_map = _make_game_map()
        dc.set_context(units, game_map)
        assert dc._units is units
        assert dc._game_map is game_map


@pytest.mark.unit
class TestHandlePlayerCommand:
    """Test command routing in handle_player_command."""

    def test_attack_command_routes_to_execute_attack(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        attacker = _make_unit("ally1", Faction.ALLIES, 5, 5, weapon_id="rifle")
        target = _make_unit("enemy1", Faction.AXIS, 6, 5)
        units = [attacker, target]
        game_map = _make_game_map()

        dc.execute_attack = Mock()
        dc.handle_player_command(
            {"command": "attack", "unit_ids": ["ally1"], "target_id": "enemy1"},
            units,
            game_map,
        )
        dc.execute_attack.assert_called_once_with(attacker, target)

    def test_attack_command_ignores_same_faction(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        ally1 = _make_unit("ally1", Faction.ALLIES, 5, 5)
        ally2 = _make_unit("ally2", Faction.ALLIES, 6, 5)
        units = [ally1, ally2]
        game_map = _make_game_map()

        dc.execute_attack = Mock()
        dc.handle_player_command(
            {"command": "attack", "unit_ids": ["ally1"], "target_id": "ally2"},
            units,
            game_map,
        )
        dc.execute_attack.assert_not_called()

    def test_take_cover_removes_move_orders(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        unit = _make_unit("u1", Faction.ALLIES)
        dc._move_orders["u1"] = {"path": [TileCoord(6, 5)], "current_idx": 0}

        dc.handle_player_command(
            {"command": "take_cover", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        assert "u1" not in dc._move_orders

    def test_stop_command_removes_move_orders(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        unit = _make_unit("u1", Faction.ALLIES)
        dc._move_orders["u1"] = {"path": [TileCoord(6, 5)], "current_idx": 0}

        dc.handle_player_command(
            {"command": "stop", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        assert "u1" not in dc._move_orders

    def test_defend_command_sets_defend_mode(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        unit = _make_unit("u1", Faction.ALLIES)
        unit.movement_mode = "normal"

        dc.handle_player_command(
            {"command": "defend", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        unit.set_movement_mode.assert_called_with("defend", duration_ticks=-1)

    def test_defend_command_toggles_off(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        unit = _make_unit("u1", Faction.ALLIES)
        unit.movement_mode = "defend"

        dc.handle_player_command(
            {"command": "defend", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        unit.set_movement_mode.assert_called_with("normal")

    def test_fast_move_command_sets_fast_move_mode(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        unit = _make_unit("u1", Faction.ALLIES)
        unit.movement_mode = "normal"

        dc.handle_player_command(
            {"command": "fast_move", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        unit.set_movement_mode.assert_called_with("fast_move", duration_ticks=-1)

    def test_sneak_command_sets_sneak_mode(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        unit = _make_unit("u1", Faction.ALLIES)
        unit.movement_mode = "normal"
        unit.can_sneak = True

        dc.handle_player_command(
            {"command": "sneak", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        unit.set_movement_mode.assert_called_with("sneak", duration_ticks=-1)

    def test_sneak_command_ignored_for_non_sneak_units(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        unit = _make_unit("u1", Faction.ALLIES)
        unit.movement_mode = "normal"
        unit.can_sneak = False

        dc.handle_player_command(
            {"command": "sneak", "unit_ids": ["u1"]},
            [unit],
            _make_game_map(),
        )
        unit.set_movement_mode.assert_not_called()


@pytest.mark.unit
class TestExecuteAttack:
    """Test attack execution logic."""

    def test_execute_attack_no_ballistic_engine(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        dc.ballistic_engine = None
        attacker = _make_unit("a1", Faction.ALLIES)
        target = _make_unit("e1", Faction.AXIS)

        dc.execute_attack(attacker, target)
        # Should not publish any events
        assert len(bus.published) == 0

    def test_execute_attack_weapon_not_ready(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        dc.ballistic_engine = Mock()
        dc._game_map = _make_game_map()
        attacker = _make_unit("a1", Faction.ALLIES, weapon_state_name="RELOADING")
        target = _make_unit("e1", Faction.AXIS)

        dc.execute_attack(attacker, target)
        assert len(bus.published) == 0

    def test_execute_attack_out_of_range(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        dc.ballistic_engine = Mock()
        dc._game_map = _make_game_map()
        # Attacker at (0,0), target at (20,20) — distance > 15
        attacker = _make_unit("a1", Faction.ALLIES, 0, 0)
        target = _make_unit("e1", Faction.AXIS, 20, 20)

        dc.execute_attack(attacker, target)
        assert len(bus.published) == 0


@pytest.mark.unit
class TestOnUnitAttacked:
    """Test on_unit_attacked event handling."""

    def test_damage_creates_hit_effect(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        dc.on_unit_attacked({"target_id": "u1", "damage": 25, "killed": False})
        assert len(dc._pending_effects) == 1
        assert dc._pending_effects[0]["type"] == "hit"
        assert dc._pending_effects[0]["damage"] == 25

    def test_kill_creates_death_effect(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        dc.on_unit_attacked({"target_id": "u1", "damage": 100, "killed": True})
        assert len(dc._pending_effects) == 2
        types = [e["type"] for e in dc._pending_effects]
        assert "hit" in types
        assert "death" in types

    def test_zero_damage_no_effect(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        dc.on_unit_attacked({"target_id": "u1", "damage": 0, "killed": False})
        assert len(dc._pending_effects) == 0


@pytest.mark.unit
class TestIsExplosiveWeapon:
    """Test _is_explosive_weapon static method."""

    def test_tank_cannon_is_explosive(self):
        assert CombatDirector._is_explosive_weapon("tank_cannon") is True

    def test_mortar_is_explosive(self):
        assert CombatDirector._is_explosive_weapon("81mm_mortar") is True

    def test_bazooka_is_explosive(self):
        assert CombatDirector._is_explosive_weapon("bazooka") is True

    def test_rifle_is_not_explosive(self):
        assert CombatDirector._is_explosive_weapon("rifle") is False

    def test_mg_is_not_explosive(self):
        assert CombatDirector._is_explosive_weapon("mg42") is False


@pytest.mark.unit
class TestProcessDeaths:
    """Test process_deaths method."""

    def test_dead_units_recorded_in_stats(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        dead_unit = _make_unit("u1", Faction.ALLIES, alive=False)
        battle_stats = Mock()

        dc.process_deaths([dead_unit], battle_stats)
        battle_stats.record_unit_lost.assert_called_once_with("allies")

    def test_alive_units_not_recorded(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        alive_unit = _make_unit("u1", Faction.ALLIES, alive=True)
        battle_stats = Mock()

        dc.process_deaths([alive_unit], battle_stats)
        battle_stats.record_unit_lost.assert_not_called()


@pytest.mark.unit
class TestTickWeaponReload:
    """Test tick_weapon_reload method."""

    def test_reloading_weapon_ticks(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        unit = _make_unit("u1", Faction.ALLIES, weapon_state_name="RELOADING")

        dc.tick_weapon_reload([unit])
        unit.weapon.tick.assert_called_once()

    def test_ready_weapon_not_ticked(self):
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())
        unit = _make_unit("u1", Faction.ALLIES, weapon_state_name="READY")

        dc.tick_weapon_reload([unit])
        unit.weapon.tick.assert_not_called()


def _make_real_map(width: int = 5, height: int = 5) -> GameMap:
    """Create a real GameMap with grass terrain."""
    grid = np.full((height, width), TerrainType.GRASS.value, dtype=np.int8)
    return GameMap(id="cc2_mech", name="CC2 Mech", width=width, height=height, tile_grid=grid)


def _make_engineer(unit_id: str, x: int, y: int) -> Mock:
    """Create an engineer unit mock with demolition capability."""
    unit = _make_unit(unit_id, Faction.ALLIES, x, y)
    unit.has_demolitions = True
    unit.template_id = "us_engineer_squad"
    return unit


@pytest.mark.unit
class TestBuildBridge:
    """CC2-02: engineers build bridges on adjacent water or broken tiles."""

    def test_engineer_builds_bridge_on_adjacent_water(self):
        game_map = _make_real_map()
        game_map.set_terrain(TileCoord(2, 1), TerrainType.WATER)
        engineer = _make_engineer("eng1", 1, 1)
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())

        dc.handle_player_command(
            {"command": "build_bridge", "unit_ids": ["eng1"]}, [engineer], game_map
        )

        assert game_map.get_terrain(TileCoord(2, 1)) == TerrainType.BRIDGE
        assert any(event.get("action") == "bridge_built" for event in bus.published)

    def test_non_engineer_cannot_build_bridge(self):
        game_map = _make_real_map()
        game_map.set_terrain(TileCoord(2, 1), TerrainType.WATER)
        rifleman = _make_unit("rifle1", Faction.ALLIES, 1, 1)
        rifleman.has_demolitions = False
        rifleman.template_id = "us_rifle_squad"
        dc = CombatDirector(event_bus=StubEventBus(), display_config=StubDisplayConfig())

        dc.handle_player_command(
            {"command": "build_bridge", "unit_ids": ["rifle1"]}, [rifleman], game_map
        )

        assert game_map.get_terrain(TileCoord(2, 1)) == TerrainType.WATER
        assert not bus_events(dc)


def bus_events(director: CombatDirector) -> list:
    """Return events recorded by a director's stub bus."""
    return director.event_bus.published


@pytest.mark.unit
class TestAirStrike:
    """CC2-04: air strikes are limited and damage the 3x3 target area."""

    def test_air_strike_hits_units_in_radius(self):
        game_map = _make_real_map(width=12, height=12)
        near = _make_unit("axis_near", Faction.AXIS, 5, 5)
        edge = _make_unit("axis_edge", Faction.AXIS, 6, 6)
        far = _make_unit("axis_far", Faction.AXIS, 10, 10)
        bus = StubEventBus()
        dc = CombatDirector(event_bus=bus, display_config=StubDisplayConfig())

        dc.handle_player_command(
            {"command": "air_strike", "unit_ids": [], "target": (5, 5)},
            [near, edge, far],
            game_map,
        )

        near.take_damage.assert_called_once_with(45)
        edge.take_damage.assert_called_once_with(45)
        far.take_damage.assert_not_called()
        assert dc._air_strikes_remaining == 2
        assert any(event.get("action") == "air_strike" for event in bus.published)

    def test_no_air_support_blocks_strike(self):
        game_map = _make_real_map(width=12, height=12)
        enemy = _make_unit("axis1", Faction.AXIS, 5, 5)
        dc = CombatDirector(event_bus=StubEventBus(), display_config=StubDisplayConfig())
        dc.configure_air_support("none")

        dc.handle_player_command(
            {"command": "air_strike", "unit_ids": [], "target": (5, 5)}, [enemy], game_map
        )

        enemy.take_damage.assert_not_called()
        assert dc._air_strikes_remaining == 0

    def test_limited_support_allows_one_strike(self):
        game_map = _make_real_map(width=12, height=12)
        enemy = _make_unit("axis1", Faction.AXIS, 5, 5)
        dc = CombatDirector(event_bus=StubEventBus(), display_config=StubDisplayConfig())
        dc.configure_air_support("limited")

        command = {"command": "air_strike", "unit_ids": [], "target": (5, 5)}
        dc.handle_player_command(command, [enemy], game_map)
        dc.handle_player_command(command, [enemy], game_map)

        enemy.take_damage.assert_called_once_with(45)
        assert dc._air_strikes_remaining == 0

    @pytest.mark.parametrize("level,expected", [("none", 0), ("limited", 1), ("full", 3)])
    def test_air_support_level_sets_strike_count(self, level, expected):
        dc = CombatDirector(event_bus=StubEventBus(), display_config=StubDisplayConfig())
        dc.configure_air_support(level)
        assert dc._air_strikes_remaining == expected
