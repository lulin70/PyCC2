"""MC2-06 unit tests: RefitService repair / reinforce / RP bookkeeping."""

from __future__ import annotations

import os

import pytest

# Headless pygame (must precede any pygame import)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.squad import MemberState, Squad, SquadType
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.campaign_persistence import CampaignPersistenceManager
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.refit_service import RefitService, normalize_side


def _make_unit(unit_id: str, faction: Faction, hp: int, max_hp: int, morale: int = 50) -> Unit:
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(3, 3)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def manager(tmp_path):
    return CampaignPersistenceManager(base_dir=tmp_path)


@pytest.fixture
def service(manager) -> RefitService:
    return RefitService(manager=manager, campaign_id="refit_test")


@pytest.mark.unit
class TestNormalizeSide:
    def test_allied_strings(self):
        assert normalize_side("allies") == "allies"
        assert normalize_side("ALLIES") == "allies"
        assert normalize_side("ally") == "allies"
        assert normalize_side("allied") == "allies"

    def test_axis_strings(self):
        assert normalize_side("axis") == "axis"
        assert normalize_side("AXIS") == "axis"
        assert normalize_side("German") == "axis"

    def test_unknown_defaults_to_allies(self):
        assert normalize_side("") == "allies"


@pytest.mark.unit
class TestRequisitionPoints:
    def test_default_pool(self, service):
        assert service.available_rp("allies") == 500
        assert service.available_rp("axis") == 500

    def test_spend_deducts_and_persists(self, service):
        assert service.spend_rp("allies", 100) is True
        assert service.available_rp("ALLIES") == 400
        # Reload through a fresh service to prove persistence.
        fresh = RefitService(manager=service.manager, campaign_id="refit_test")
        assert fresh.available_rp("allies") == 400

    def test_spend_insufficient_fails_without_change(self, service):
        assert service.spend_rp("allies", 10_000) is False
        assert service.available_rp("allies") == 500

    def test_spend_non_positive_fails(self, service):
        assert service.spend_rp("allies", 0) is False
        assert service.spend_rp("allies", -5) is False

    def test_sides_are_independent(self, service):
        service.spend_rp("axis", 500)
        assert service.available_rp("axis") == 0
        assert service.available_rp("allies") == 500


@pytest.mark.unit
class TestRepair:
    def test_repair_cost_missing_hp(self, service):
        unit = _make_unit("u1", Faction.ALLIES, hp=40, max_hp=100)
        assert RefitService.repair_cost(unit) == 60

    def test_repair_cost_full_hp_is_zero(self, service):
        unit = _make_unit("u1", Faction.ALLIES, hp=100, max_hp=100)
        assert RefitService.repair_cost(unit) == 0

    def test_repair_spends_rp_and_heals(self, service):
        unit = _make_unit("u1", Faction.ALLIES, hp=40, max_hp=100)
        healed = service.repair(unit, 30)
        assert healed == 30
        assert unit.health.hp == 70
        assert service.available_rp("allies") == 470

    def test_repair_capped_by_available_rp(self, service):
        service.spend_rp("allies", 480)  # 20 RP left
        unit = _make_unit("u1", Faction.ALLIES, hp=40, max_hp=100)
        healed = service.repair(unit, 60)
        assert healed == 20
        assert unit.health.hp == 60
        assert service.available_rp("allies") == 0

    def test_repair_capped_by_missing_hp(self, service):
        unit = _make_unit("u1", Faction.ALLIES, hp=90, max_hp=100)
        healed = service.repair(unit, 50)
        assert healed == 10
        assert unit.health.hp == 100

    def test_repair_zero_or_negative_rp_is_noop(self, service):
        unit = _make_unit("u1", Faction.ALLIES, hp=40, max_hp=100)
        assert service.repair(unit, 0) == 0
        assert service.repair(unit, -1) == 0
        assert unit.health.hp == 40


@pytest.mark.unit
class TestReinforce:
    def _unit_with_casualties(self, dead: int) -> Unit:
        unit = _make_unit("u1", Faction.ALLIES, hp=100, max_hp=100, morale=40)
        squad = Squad(
            squad_id="u1",
            squad_type=SquadType.RIFLE_SQUAD,
            faction="allies",
            name="u1",
        )
        for member in squad.members[:dead]:
            member.state = MemberState.DEAD
            member.hp = 0
        unit.squad_ref = squad
        return unit

    def test_reinforce_cost_missing_members(self, service):
        unit = self._unit_with_casualties(dead=3)
        assert service.reinforce_cost(unit) == 30

    def test_reinforce_cost_no_squad(self, service):
        unit = _make_unit("u1", Faction.ALLIES, hp=100, max_hp=100)
        assert service.reinforce_cost(unit) == 0

    def test_reinforce_spends_rp_and_restores_manpower(self, service):
        unit = self._unit_with_casualties(dead=4)
        size_before = unit.squad_ref.size  # 8
        reinforced = service.reinforce(unit, 25)  # 25 RP → 2 members
        assert reinforced == 2
        # Fallen members are struck from the roster, replacements appended.
        assert unit.squad_ref.dead_count == 0
        assert unit.squad_ref.size == size_before - 4 + 2
        assert unit.squad_ref.alive_count == unit.squad_ref.size
        assert service.available_rp("allies") == 500 - 20

    def test_reinforce_lifts_morale(self, service):
        unit = self._unit_with_casualties(dead=1)
        service.reinforce(unit, 10)
        assert unit.morale.value == 50

    def test_reinforce_insufficient_rp_is_noop(self, service):
        unit = self._unit_with_casualties(dead=3)
        size_before = unit.squad_ref.size
        assert service.reinforce(unit, 5) == 0  # < cost of one member
        assert unit.squad_ref.size == size_before
        assert service.available_rp("allies") == 500

    def test_reinforce_full_squad_is_noop(self, service):
        unit = self._unit_with_casualties(dead=0)
        assert service.reinforce(unit, 100) == 0
