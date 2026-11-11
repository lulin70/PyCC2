"""CC2-03: truck unit templates exist and their weapons resolve."""

from __future__ import annotations

import pytest

from pycc2.domain.systems.cc2_authentic_weapons import VehicleType
from pycc2.domain.systems.unit_database import get_cc2_units

TRUCK_IDS = {"us_gmc_cckw", "uk_bedford_ql", "de_opel_blitz"}


@pytest.mark.unit
class TestTruckTemplates:
    """Verify the three faction trucks are in the CC2 unit database."""

    def test_all_faction_trucks_exist(self):
        units = get_cc2_units()
        assert TRUCK_IDS.issubset(units.keys())

    def test_truck_templates_use_truck_role(self):
        units = get_cc2_units()
        for template_id in TRUCK_IDS:
            assert units[template_id].role is VehicleType.TRUCK

    def test_truck_weapons_resolve(self):
        units = get_cc2_units()
        for template_id in TRUCK_IDS:
            template = units[template_id]
            assert template.get_weapon() is not None, template.weapon_primary_id

    def test_trucks_cannot_capture_or_enter_buildings(self):
        units = get_cc2_units()
        for template_id in TRUCK_IDS:
            template = units[template_id]
            assert template.can_capture is False
            assert template.can_deploy_in_building is False


@pytest.mark.unit
class TestAmphibiousTemplate:
    """CC2-01: an amphibious template exists for river crossings."""

    def test_amphibious_template_is_available(self):
        template = get_cc2_units()["uk_sherman_dd"]
        assert template.is_amphibious is True
