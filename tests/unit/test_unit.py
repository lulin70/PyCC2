"""
Tests for Unit Entity
"""

from __future__ import annotations

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import (
    Faction,
    Unit,
    UnitState,
    UnitType,
)
from pycc2.domain.value_objects.tile_coord import TileCoord


def _make_unit(
    id: str = "u1",
    name: str = "Test Unit",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    morale_value: int = 80,
    squad_id: str | None = None,
) -> Unit:
    return Unit(
        id=id,
        name=name,
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale_value),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x=0, y=0)),
        vision=VisionComponent(range_tiles=5),
        squad_id=squad_id,
    )


class TestUnitConstruction:
    def test_basic_construction(self):
        u = _make_unit()
        assert u.id == "u1"
        assert u.name == "Test Unit"
        assert u.faction == Faction.ALLIES
        assert u.unit_type == UnitType.INFANTRY_SQUAD

    def test_initial_state_is_idle(self):
        u = _make_unit()
        assert u.state_machine.current == UnitState.IDLE

    def test_squad_id_default_none(self):
        u = _make_unit()
        assert u.squad_id is None

    def test_squad_id_can_be_set(self):
        u = _make_unit(squad_id="squad-1")
        assert u.squad_id == "squad-1"

    def test_all_components_present(self):
        u = _make_unit()
        assert isinstance(u.health, HealthComponent)
        assert isinstance(u.morale, MoraleComponent)
        assert isinstance(u.weapon, WeaponComponent)
        assert isinstance(u.position, PositionComponent)
        assert isinstance(u.vision, VisionComponent)


class TestIsAlive:
    def test_alive_when_healthy(self):
        u = _make_unit(hp=100)
        assert u.is_alive is True

    def test_dead_when_zero_hp(self):
        u = _make_unit(hp=0)
        assert u.is_alive is False


class TestCanAct:
    def test_can_act_when_alive_and_idle(self):
        u = _make_unit()
        assert u.can_act is True

    def test_cannot_act_when_dead(self):
        u = _make_unit()
        u.die()
        assert u.can_act is False

    def test_cannot_act_when_reloading(self):
        u = _make_unit()
        u.state_machine.force_transition(UnitState.RELOADING)
        assert u.can_act is False


class TestCombatEffective:
    def test_combat_effective_with_good_morale(self):
        u = _make_unit(morale_value=80)
        assert u.combat_effective is True

    def test_not_combat_effective_when_panicked(self):
        u = _make_unit(morale_value=15)
        assert u.combat_effective is False


class TestMoveToTile:
    def test_move_to_tile_delegates(self):
        u = _make_unit()
        target = TileCoord(x=5, y=3)
        u.move_to_tile(target)
        assert u.position.tile_coord == target


class TestTakeDamage:
    def test_take_damage_delegates_to_health(self):
        u = _make_unit(hp=100, max_hp=100)
        actual = u.take_damage(30)
        assert actual == 30
        assert u.health.hp == 70

    def test_lethal_damage_triggers_die(self):
        u = _make_unit(hp=100, max_hp=100)
        u.take_damage(100)
        assert u.state_machine.current == UnitState.DEAD

    def test_returns_actual_damage_clamped(self):
        u = _make_unit(hp=50, max_hp=100)
        actual = u.take_damage(200)
        assert actual == 50
        assert u.state_machine.current == UnitState.DEAD


class TestDie:
    def test_die_transitions_to_dead(self):
        u = _make_unit()
        u.die()
        assert u.state_machine.current == UnitState.DEAD

    def test_die_from_any_state(self):
        u = _make_unit()
        u.state_machine.force_transition(UnitState.ATTACKING)
        u.die()
        assert u.state_machine.current == UnitState.DEAD


class TestStateMachineTransitions:
    def test_idle_to_moving_valid(self):
        u = _make_unit()
        result = u.state_machine.try_transition(UnitState.MOVING)
        assert result is True
        assert u.state_machine.current == UnitState.MOVING

    def test_idle_to_dead_valid(self):
        u = _make_unit()
        result = u.state_machine.try_transition(UnitState.DEAD)
        assert result is True
        assert u.state_machine.current == UnitState.DEAD

    def test_dead_to_idle_invalid(self):
        u = _make_unit()
        u.state_machine.transition_or_raise(UnitState.DEAD)
        result = u.state_machine.try_transition(UnitState.IDLE)
        assert result is False
        assert u.state_machine.current == UnitState.DEAD

    def test_moving_to_reloading_invalid(self):
        u = _make_unit()
        u.state_machine.transition_or_raise(UnitState.MOVING)
        result = u.state_machine.try_transition(UnitState.RELOADING)
        assert result is False


class TestSquadAssociation:
    def test_squad_id_stored(self):
        u = _make_unit(squad_id="alpha")
        assert u.squad_id == "alpha"
