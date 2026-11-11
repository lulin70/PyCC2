"""Regression tests for deployment roster template IDs (GAP-15)."""

from __future__ import annotations

from pycc2.domain.systems.unit_database import build_cc2_unit_database
from pycc2.services.deployment_factory import (
    build_default_roster,
    build_force_pool_from_settings,
    generate_ai_deployment,
)
from pycc2.services.deployment_manager import DeploymentManager


def _database_ids() -> set[str]:
    return set(build_cc2_unit_database())


def test_default_roster_ids_exist_in_database() -> None:
    db_ids = _database_ids()
    missing = {u.unit_template_id for u in build_default_roster()} - db_ids
    assert missing == set()


def test_force_pool_ids_exist_in_database() -> None:
    db_ids = _database_ids()
    for faction in ("allied", "axis"):
        pool = build_force_pool_from_settings(faction)
        missing = {u.unit_template_id for u in pool} - db_ids
        assert missing == set(), f"{faction}: {missing}"


def test_ai_deployment_ids_exist_in_database() -> None:
    db_ids = _database_ids()
    map_data = {"width": 20, "height": 20}
    for faction in ("allied", "axis"):
        placements = generate_ai_deployment(map_data, faction=faction)
        missing = {p["unit_template_id"] for p in placements} - db_ids
        assert missing == set(), f"{faction}: {missing}"


def test_allied_pools_include_amphibious_tank() -> None:
    for pool in (build_default_roster(), build_force_pool_from_settings("allied")):
        assert "uk_sherman_dd" in {u.unit_template_id for u in pool}


def test_attach_squad_sets_amphibious_flag() -> None:
    from types import SimpleNamespace

    from pycc2.domain.entities.unit import UnitType

    unit = SimpleNamespace(
        id="dd1",
        name="Sherman DD",
        faction=SimpleNamespace(name="BRITISH"),
        squad_ref=None,
    )
    DeploymentManager._attach_squad(unit, "uk_sherman_dd", UnitType.INFANTRY_SQUAD, "allied")
    assert unit.is_amphibious is True


def test_deployment_template_maps_use_database_ids() -> None:
    db_ids = _database_ids()
    assert set(DeploymentManager._TEMPLATE_TYPE_MAP) <= db_ids
    assert set(DeploymentManager._TEMPLATE_WEAPON_MAP) <= db_ids
