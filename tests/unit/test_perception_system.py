import pytest

from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.perception_system import PerceptionSystem
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord


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
def perception():
    return PerceptionSystem()


class TestPerceptionBasicUpdates:
    def test_updates_health_ratio(self, perception):
        unit = _make_unit(hp=75)
        bb = Blackboard()
        perception.update_blackboard(bb, unit)
        assert bb.get("health_ratio") == 0.75

    def test_updates_current_tile(self, perception):
        unit = _make_unit(x=10, y=20)
        bb = Blackboard()
        perception.update_blackboard(bb, unit)
        tile = bb.get("current_tile")
        assert tile is not None
        assert tile.x == 10
        assert tile.y == 20

    def test_detects_suppressed_unit(self, perception):
        unit = _make_unit()
        unit.morale.add_suppression(10)
        bb = Blackboard()
        perception.update_blackboard(bb, unit)
        assert bb.get("is_suppressed") is True

    def test_normal_unit_not_suppressed(self, perception):
        unit = _make_unit()
        bb = Blackboard()
        perception.update_blackboard(bb, unit)
        assert bb.get("is_suppressed") is False


class TestPerceptionEnemyDetection:
    def test_detects_visible_enemies(self, perception):
        unit = _make_unit(unit_id="ally_1")
        enemy = _make_unit(unit_id="enemy_1", faction=Faction.AXIS, x=6, y=5)
        bb = Blackboard()
        perception.update_blackboard(bb, unit, all_units=[unit, enemy])
        enemies = bb.get("visible_enemies")
        assert "enemy_1" in enemies

    def test_calculates_nearest_enemy_distance(self, perception):
        unit = _make_unit(x=0, y=0)
        enemy = _make_unit(unit_id="e1", faction=Faction.AXIS, x=3, y=4)
        bb = Blackboard()
        perception.update_blackboard(bb, unit, all_units=[unit, enemy])
        dist = bb.get("nearest_enemy_distance")
        assert dist == 4.0

    def test_no_enemies_sets_infinite_distance(self, perception):
        unit = _make_unit()
        bb = Blackboard()
        perception.update_blackboard(bb, unit, all_units=[unit])
        assert bb.get("nearest_enemy_distance") == float("inf")

    def test_fog_of_war_hides_enemies(self, perception):
        unit = _make_unit(x=0, y=0)
        enemy = _make_unit(unit_id="e1", faction=Faction.AXIS, x=3, y=4)
        fow = {(3, 4): False}
        bb = Blackboard()
        perception.update_blackboard(bb, unit, all_units=[unit, enemy], fog_of_war=fow)
        enemies = bb.get("visible_enemies")
        assert "e1" not in enemies


class TestPerceptionAllyDetection:
    def test_counts_allies_nearby(self, perception):
        unit = _make_unit(unit_id="u1")
        ally1 = _make_unit(unit_id="a1", x=5, y=6)
        ally2 = _make_unit(unit_id="a2", x=6, y=5)
        bb = Blackboard()
        perception.update_blackboard(bb, unit, all_units=[unit, ally1, ally2])
        allies = bb.get("allies_nearby")
        assert allies == 2

    def test_ignores_far_allies(self, perception):
        unit = _make_unit(x=0, y=0)
        far_ally = _make_unit(unit_id="a1", x=20, y=20)
        bb = Blackboard()
        perception.update_blackboard(bb, unit, all_units=[unit, far_ally])
        allies = bb.get("allies_nearby")
        assert allies == 0

    def test_ignores_self_in_ally_count(self, perception):
        unit = _make_unit()
        bb = Blackboard()
        perception.update_blackboard(bb, unit, all_units=[unit])
        assert bb.get("allies_nearby") == 0
