import pytest

from pycc2.domain.ai.unit_bt_factory import UnitBTFactory
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.ai_service import AIService
from pycc2.services.event_bus import EventBus


def _make_unit(
    unit_id: str = "unit_1",
    faction: Faction = Faction.ALLIES,
    hp: int = 100,
    x: int = 5,
    y: int = 5,
) -> Unit:
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=hp, max_hp=100),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=8),
    )


@pytest.fixture
def ai_service():
    event_bus = EventBus()
    return AIService(event_bus=event_bus)


class TestAIServiceRegistration:
    def test_register_ai_unit(self, ai_service):
        unit = _make_unit(unit_id="inf_1")
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        ai_service.register_ai_unit(unit, tree)
        assert ai_service.managed_unit_count == 1
        assert "inf_1" in ai_service.managed_unit_ids

    def test_unregister_ai_unit(self, ai_service):
        unit = _make_unit(unit_id="inf_1")
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        ai_service.register_ai_unit(unit, tree)
        ai_service.unregister_ai_unit("inf_1")
        assert ai_service.managed_unit_count == 0

    def test_get_unit_tree(self, ai_service):
        unit = _make_unit(unit_id="mg_1")
        tree = UnitBTFactory.create_mg_squad_bt(unit_id="mg_1")
        ai_service.register_ai_unit(unit, tree)
        retrieved = ai_service.get_unit_tree("mg_1")
        assert retrieved is tree


class TestAIServiceTick:
    def test_tick_returns_intents(self, ai_service):
        unit = _make_unit(unit_id="inf_1", hp=20)
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        ai_service.register_ai_unit(unit, tree)
        intents = ai_service.tick(dt=0.1)
        assert len(intents) == 1
        assert intents[0].unit_id == "inf_1"

    def test_tick_with_multiple_units(self, ai_service):
        inf = _make_unit(unit_id="inf_1", hp=20)
        mg = _make_unit(unit_id="mg_1", hp=20)
        inf_tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        mg_tree = UnitBTFactory.create_mg_squad_bt(unit_id="mg_1")
        ai_service.register_ai_unit(inf, inf_tree)
        ai_service.register_ai_unit(mg, mg_tree)
        intents = ai_service.tick(dt=0.1)
        assert len(intents) == 2

    def test_tick_no_units_returns_empty(self, ai_service):
        intents = ai_service.tick(dt=0.1)
        assert len(intents) == 0


class TestAIServiceExecute:
    def test_execute_intents(self, ai_service):
        unit = _make_unit(unit_id="inf_1")
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        ai_service.register_ai_unit(unit, tree)
        intents = ai_service.tick(dt=0.1)
        if intents:
            results = ai_service.execute_intents(intents)
            for unit_id, success in results.items():
                assert isinstance(success, bool)


class TestAIServiceBlackboard:
    def test_get_blackboard(self, ai_service):
        unit = _make_unit(unit_id="inf_1")
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        ai_service.register_ai_unit(unit, tree)
        bb = ai_service.get_blackboard("inf_1")
        assert bb is not None

    def test_set_blackboard_value(self, ai_service):
        unit = _make_unit(unit_id="inf_1")
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        ai_service.register_ai_unit(unit, tree)
        ai_service.set_blackboard_value("inf_1", "test_key", 42)
        bb = ai_service.get_blackboard("inf_1")
        assert bb.get("test_key") == 42


class TestAIServiceShutdown:
    def test_shutdown_clears_all(self, ai_service):
        unit = _make_unit(unit_id="inf_1")
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        ai_service.register_ai_unit(unit, tree)
        assert ai_service.managed_unit_count > 0
        ai_service.shutdown()
        assert ai_service.managed_unit_count == 0
