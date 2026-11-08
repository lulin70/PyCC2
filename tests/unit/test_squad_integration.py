"""Tests for CC2 squad-model integration (P0-1).

Verifies that deployed infantry carry a Squad, that HP loss maps to
individual casualties, and that squad effectiveness feeds combat.
"""

from __future__ import annotations

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.squad import MemberState, Squad, SquadType
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.deployment_manager import DeploymentManager


class _FixedRng:
    """Deterministic RNG stub for ballistic accuracy comparisons."""

    def uniform(self, low: float, high: float) -> float:
        return (low + high) / 2.0

    def gaussian(self, mu: float, sigma: float) -> float:
        return mu


def _make_unit(squad: Squad | None = None) -> Unit:
    unit = Unit(
        id="u1",
        name="Test Squad",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
        position=PositionComponent(tile_coord=TileCoord(1, 1)),
        vision=VisionComponent(),
    )
    unit.squad_ref = squad
    return unit


def test_deployment_attaches_template_sized_squad():
    manager = DeploymentManager()
    unit = manager._create_unit_from_placement(
        placement={
            "unit_template_id": "us_rifle_squad",
            "display_name": "US Rifle Squad",
            "unit_type": "infantry",
            "position": (3, 3),
        },
        faction=Faction.ALLIES,
        id_prefix="player",
        counter=0,
        type_map={"infantry": UnitType.INFANTRY_SQUAD},
        template_type_map={},
    )

    assert unit is not None
    assert unit.squad_ref is not None
    assert unit.squad_ref.size == 12
    assert unit.squad_ref.faction == "allies"


def test_damage_creates_wounded_then_dead():
    squad = Squad(
        squad_id="u1",
        squad_type=SquadType.RIFLE_SQUAD,
        faction="allies",
        initial_size=10,
    )
    unit = _make_unit(squad)

    unit.take_damage(50)

    assert squad.wounded_count == 5
    assert squad.dead_count == 0
    assert unit.squad_effectiveness == 0.75

    unit.take_damage(50)

    assert not unit.is_alive
    assert squad.dead_count == 10
    assert unit.squad_effectiveness == 0.0


def test_dead_unit_destroys_all_squad_members():
    squad = Squad(
        squad_id="u1",
        squad_type=SquadType.RIFLE_SQUAD,
        faction="allies",
        initial_size=6,
    )
    unit = _make_unit(squad)

    unit.take_damage(1000)

    assert squad.dead_count == 6
    assert squad.alive_count == 0


def test_casualties_reduce_ballistic_accuracy():
    full_squad = Squad(
        squad_id="u1",
        squad_type=SquadType.RIFLE_SQUAD,
        faction="allies",
        initial_size=10,
    )
    attacker_full = _make_unit(full_squad)

    wounded_squad = Squad(
        squad_id="u1",
        squad_type=SquadType.RIFLE_SQUAD,
        faction="allies",
        initial_size=10,
    )
    for member in wounded_squad.members:
        member.state = MemberState.WOUNDED
        member.hp = 35
    attacker_wounded = _make_unit(wounded_squad)

    target = _make_unit()
    engine = BallisticEngine(rng=_FixedRng())

    full_shot = engine.calculate_shot(attacker_full, target)
    wounded_shot = engine.calculate_shot(attacker_wounded, target)

    assert wounded_shot.actual_accuracy < full_shot.actual_accuracy


def test_suppression_pins_squad_members(monkeypatch):
    monkeypatch.setattr("pycc2.domain.entities.squad.random.random", lambda: 0.0)

    squad = Squad(
        squad_id="u1",
        squad_type=SquadType.RIFLE_SQUAD,
        faction="allies",
        initial_size=8,
    )
    unit = _make_unit(squad)

    pinned = unit.apply_squad_suppression(1.0)

    assert pinned == 8
    assert squad.pinned_count == 8
    assert unit.squad_effectiveness == 0.0
