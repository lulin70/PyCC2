"""Unit tests for the split cc2_authentic_units subsystem."""
from __future__ import annotations

import pytest

from pycc2.domain.systems import cc2_authentic_units as facade
from pycc2.domain.systems.cc2_authentic_weapons import InfantryRole, VehicleType
from pycc2.domain.systems.deployment import (
    DeploymentConfig,
    DeploymentPhase,
    ZoneType,
    create_default_deployment_config,
)
from pycc2.domain.systems.unit_database import (
    build_cc2_unit_database,
    get_cc2_units,
    get_units_by_role,
    get_units_for_faction,
)
from pycc2.domain.systems.unit_templates import CC2UnitTemplate


@pytest.fixture(autouse=True)
def _reset_unit_cache():
    """Reset the lazy unit cache around each test to avoid cross-test state."""
    import pycc2.domain.systems.unit_database as db_module

    old_cache = db_module.CC2_UNITS
    db_module.CC2_UNITS = {}
    yield
    db_module.CC2_UNITS = old_cache


class TestFacadeReexports:
    def test_classes_are_same_objects_as_submodules(self):
        assert facade.CC2UnitTemplate is CC2UnitTemplate
        assert facade.DeploymentConfig is DeploymentConfig
        assert facade.DeploymentPhase is DeploymentPhase
        assert facade.ZoneType is ZoneType

    def test_functions_are_same_objects_as_submodules(self):
        assert facade.build_cc2_unit_database is build_cc2_unit_database
        assert facade.get_cc2_units is get_cc2_units
        assert facade.get_units_for_faction is get_units_for_faction
        assert facade.get_units_by_role is get_units_by_role
        assert facade.create_default_deployment_config is create_default_deployment_config


class TestUnitTemplate:
    def test_calculate_effective_stats_returns_expected_keys(self):
        db = build_cc2_unit_database()
        unit = db["us_rifle_squad"]
        stats = unit.calculate_effective_stats()

        assert "error" not in stats
        assert stats["name"] == unit.display_name
        assert stats["faction"] == unit.faction.name
        assert stats["role"] == unit.role.name
        assert "weapon_name" in stats
        assert "accuracy_short" in stats

    def test_get_weapon_resolves_primary(self):
        db = build_cc2_unit_database()
        unit = db["de_mg42_team"]
        weapon = unit.get_weapon()
        assert weapon is not None
        assert weapon.id == "de_mg42"

    def test_get_secondary_weapon_returns_none_when_absent(self):
        unit = CC2UnitTemplate(
            template_id="test_unit",
            display_name="Test Unit",
            faction=facade.Faction.AMERICAN,
            role=InfantryRole.RIFLE,
            weapon_primary_id="us_m1_garand",
            weapon_secondary_id=None,
        )
        assert unit.get_secondary_weapon() is None


class TestUnitDatabase:
    def test_database_contains_all_factions_and_many_units(self):
        db = build_cc2_unit_database()
        assert len(db) >= 80
        assert "us_rifle_squad" in db
        assert "de_tiger_i" in db
        assert "uk_firefly" in db
        assert "pl_para_rifle_squad" in db

    def test_get_cc2_units_is_lazy_cache(self):
        import pycc2.domain.systems.unit_database as db_module

        db_module.CC2_UNITS = {}
        first = get_cc2_units()
        second = get_cc2_units()
        assert first is second
        assert len(second) >= 80

    def test_get_units_for_faction_filters_correctly(self):
        db = build_cc2_unit_database()
        for faction in facade.Faction:
            faction_units = get_units_for_faction(faction)
            assert all(u.faction == faction for u in faction_units)
            assert len(faction_units) < len(db)

    def test_get_units_by_role(self):
        db = build_cc2_unit_database()
        rifle_units = get_units_by_role(InfantryRole.RIFLE)
        assert all(u.role == InfantryRole.RIFLE for u in rifle_units)
        assert len(rifle_units) >= 4

        tank_units = get_units_by_role(VehicleType.TANK_HEAVY)
        assert all(u.role == VehicleType.TANK_HEAVY for u in tank_units)


class TestDeployment:
    def _small_config(self) -> DeploymentConfig:
        ally_zones = [[ZoneType.NO_MANS_LAND for _ in range(9)] for _ in range(9)]
        axis_zones = [[ZoneType.NO_MANS_LAND for _ in range(9)] for _ in range(9)]
        for y in range(9):
            ally_zones[y][0] = ZoneType.FRIENDLY
            axis_zones[y][8] = ZoneType.FRIENDLY
        return DeploymentConfig(
            map_width=9,
            map_height=9,
            ally_zones=ally_zones,
            axis_zones=axis_zones,
            max_infantry=9,
            max_support=6,
            max_total=15,
        )

    def test_can_deploy_at_respects_boundaries_and_zones(self):
        config = self._small_config()
        assert config.can_deploy_at(0, 0, facade.Faction.AMERICAN) is True
        assert config.can_deploy_at(8, 0, facade.Faction.GERMAN) is True
        assert config.can_deploy_at(4, 4, facade.Faction.AMERICAN) is False
        assert config.can_deploy_at(-1, 0, facade.Faction.AMERICAN) is False
        assert config.can_deploy_at(0, 9, facade.Faction.AMERICAN) is False

    def test_place_unit_basic_flow(self):
        config = self._small_config()
        phase = DeploymentPhase(config)
        phase.start_deployment(facade.Faction.AMERICAN)

        assert phase.place_unit("us_rifle_squad", 0, 0) is True
        assert phase.place_unit("us_rifle_squad", 8, 0) is False  # enemy zone
        assert phase.remove_unit(0) is True
        assert phase.remove_unit(0) is False
        assert phase.confirm_deployment() is True
        assert phase.is_complete is True

    def test_place_unit_enforces_limits(self):
        config = DeploymentConfig(
            map_width=3,
            map_height=3,
            ally_zones=[[ZoneType.FRIENDLY for _ in range(3)] for _ in range(3)],
            axis_zones=[[ZoneType.FRIENDLY for _ in range(3)] for _ in range(3)],
            max_infantry=1,
            max_support=1,
            max_total=2,
        )
        phase = DeploymentPhase(config)
        phase.start_deployment(facade.Faction.AMERICAN)

        assert phase.place_unit("us_rifle_squad", 0, 0) is True
        assert phase.place_unit("us_rifle_squad", 1, 0) is False  # max infantry
        assert phase.place_unit("us_sherman_m4", 2, 0) is True
        assert phase.place_unit("us_sherman_m4", 2, 1) is False  # max support / total

    def test_create_default_deployment_config(self):
        config = create_default_deployment_config(12, 9)
        assert config.map_width == 12
        assert config.map_height == 9
        assert len(config.ally_zones) == 9
        assert len(config.ally_zones[0]) == 12
        assert any(z == ZoneType.FRIENDLY for row in config.ally_zones for z in row)
        assert any(z == ZoneType.NO_MANS_LAND for row in config.ally_zones for z in row)
