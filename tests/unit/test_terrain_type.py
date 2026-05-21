"""
Tests for TerrainType IntEnum
"""

from pycc2.domain.value_objects.terrain_type import TerrainType


class TestTerrainTypeEnumValues:
    def test_all_12_types_exist(self):
        assert TerrainType.OPEN.value == 0
        assert TerrainType.ROAD.value == 1
        assert TerrainType.GRASS.value == 2
        assert TerrainType.WOODS.value == 3
        assert TerrainType.BUILDING_ENTERABLE.value == 4
        assert TerrainType.BUILDING_SOLID.value == 5
        assert TerrainType.WATER.value == 6
        assert TerrainType.HEDGE.value == 7
        assert TerrainType.WALL.value == 8
        assert TerrainType.ROUGH.value == 9
        assert TerrainType.SHALLOW.value == 10
        assert TerrainType.BRIDGE.value == 11

    def test_total_count(self):
        assert len(TerrainType) == 14


class TestTerrainTypeMovementCost:
    def test_open_cost(self):
        assert TerrainType.OPEN.movement_cost == 1.0

    def test_road_cost(self):
        assert TerrainType.ROAD.movement_cost == 0.8

    def test_grass_cost(self):
        assert TerrainType.GRASS.movement_cost == 1.2

    def test_woods_cost(self):
        assert TerrainType.WOODS.movement_cost == 2.0

    def test_building_enterable_cost(self):
        assert TerrainType.BUILDING_ENTERABLE.movement_cost == 1.5

    def test_building_solid_cost_infinite(self):
        assert TerrainType.BUILDING_SOLID.movement_cost == float("inf")

    def test_water_cost_infinite(self):
        assert TerrainType.WATER.movement_cost == float("inf")

    def test_hedge_cost(self):
        assert TerrainType.HEDGE.movement_cost == 2.5

    def test_wall_cost_infinite(self):
        assert TerrainType.WALL.movement_cost == float("inf")

    def test_rough_cost(self):
        assert TerrainType.ROUGH.movement_cost == 1.8

    def test_shallow_cost(self):
        assert TerrainType.SHALLOW.movement_cost == 3.0

    def test_bridge_cost(self):
        assert TerrainType.BRIDGE.movement_cost == 0.9


class TestTerrainTypeCoverBonus:
    def test_open_no_cover(self):
        assert TerrainType.OPEN.cover_bonus == 0.0

    def test_woods_cover(self):
        assert TerrainType.WOODS.cover_bonus == 0.20

    def test_building_solid_high_cover(self):
        assert TerrainType.BUILDING_SOLID.cover_bonus == 0.80


class TestTerrainTypeBlocksLOS:
    def test_open_no_block_los(self):
        assert TerrainType.OPEN.blocks_los is False

    def test_woods_blocks_los(self):
        assert TerrainType.WOODS.blocks_los is True

    def test_wall_blocks_los(self):
        assert TerrainType.WALL.blocks_los is True


class TestTerrainTypePassability:
    def test_open_passable(self):
        assert TerrainType.OPEN.is_passable is True

    def test_road_passable(self):
        assert TerrainType.ROAD.is_passable is True

    def test_water_not_passable(self):
        assert TerrainType.WATER.is_passable is False

    def test_building_solid_not_passable(self):
        assert TerrainType.BUILDING_SOLID.is_passable is False

    def test_wall_not_passable(self):
        assert TerrainType.WALL.is_passable is False

    def test_hedge_passable(self):
        assert TerrainType.HEDGE.is_passable is True
