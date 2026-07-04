"""Tests for variant generator modules — faction/vehicle variants.

Covers FactionVariantGenerator and VehicleVariantGenerator (non-ghost modules
retained after Phase 3 P1-1 ghost cleanup on 2026-07-04; the
unit_diversity_expansion facade and its tests were removed as ghost).
"""

from __future__ import annotations

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.cc2_authentic_units import CC2UnitTemplate
from pycc2.domain.systems.cc2_authentic_weapons import InfantryRole, VehicleType
from pycc2.domain.systems.faction_variant_generator import FactionVariantGenerator
from pycc2.domain.systems.vehicle_variant_generator import VehicleVariantGenerator

# ---------------------------------------------------------------------------
# FactionVariantGenerator
# ---------------------------------------------------------------------------


class TestFactionVariantGenerator:
    def test_generate_returns_non_empty_list(self):
        """Verify: generate() returns a non-empty list of CC2UnitTemplate."""
        gen = FactionVariantGenerator()
        result = gen.generate()
        assert len(result) > 0
        assert all(isinstance(t, CC2UnitTemplate) for t in result)

    def test_generate_includes_british_commando(self):
        """Verify: British Commando Squad is present with correct key stats."""
        gen = FactionVariantGenerator()
        result = gen.generate()
        commando = next(t for t in result if t.template_id == "uk_commando_squad")
        assert commando.faction == Faction.BRITISH
        assert commando.role == InfantryRole.HEAVY_ASSAULT
        assert commando.squad_size == 10
        assert commando.experience_level == 3
        assert commando.morale_initial == 95.0

    def test_generate_includes_american_ranger_elite(self):
        """Verify: US Ranger Squad (Elite) is present."""
        gen = FactionVariantGenerator()
        result = gen.generate()
        ranger = next(t for t in result if t.template_id == "us_ranger_squad_elite")
        assert ranger.faction == Faction.AMERICAN
        assert ranger.experience_level == 3
        assert ranger.deployment_cost == 300

    def test_generate_includes_german_fallschirmjager(self):
        """Verify: Elite Fallschirmjäger is present with FG42."""
        gen = FactionVariantGenerator()
        result = gen.generate()
        fjh = next(t for t in result if t.template_id == "de_fallschirmjager_elite")
        assert fjh.faction == Faction.GERMAN
        assert fjh.weapon_primary_id == "de_fg42"

    def test_generate_includes_polish_para_units(self):
        """Verify: Polish Para Brigade units are present (4 variants)."""
        gen = FactionVariantGenerator()
        result = gen.generate()
        polish = [t for t in result if t.faction == Faction.POLISH]
        assert len(polish) == 4
        ids = {t.template_id for t in polish}
        assert "pl_para_commando" in ids
        assert "pl_para_scout" in ids
        assert "pl_para_sniper" in ids
        assert "pl_para_heavy_weapons" in ids

    def test_generate_includes_medic_teams(self):
        """Verify: US and German medic teams are present."""
        gen = FactionVariantGenerator()
        result = gen.generate()
        ids = {t.template_id for t in result}
        assert "us_medic_team" in ids
        assert "de_medic_team" in ids

    def test_generate_includes_volksgrenadier_at(self):
        """Verify: Volksgrenadier AT team with Panzerfaust is present."""
        gen = FactionVariantGenerator()
        result = gen.generate()
        vg_at = next(t for t in result if t.template_id == "de_volksgrenadier_at")
        assert vg_at.weapon_primary_id == "de_panzerfaust"
        assert vg_at.morale_initial == 50.0
        assert vg_at.deployment_cost == 80

    def test_all_templates_have_unique_ids(self):
        """Verify: No duplicate template_id in faction variants."""
        gen = FactionVariantGenerator()
        result = gen.generate()
        ids = [t.template_id for t in result]
        assert len(ids) == len(set(ids))

    def test_all_templates_have_required_fields(self):
        """Verify: Every template has non-None required fields."""
        gen = FactionVariantGenerator()
        result = gen.generate()
        for t in result:
            assert t.template_id, f"Missing template_id: {t}"
            assert t.display_name, f"Missing display_name: {t}"
            assert t.faction is not None
            assert t.role is not None
            assert t.deployment_cost > 0


# ---------------------------------------------------------------------------
# VehicleVariantGenerator
# ---------------------------------------------------------------------------


class TestVehicleVariantGenerator:
    def test_generate_returns_non_empty_list(self):
        """Verify: generate() returns a non-empty list of CC2UnitTemplate."""
        gen = VehicleVariantGenerator()
        result = gen.generate()
        assert len(result) > 0
        assert all(isinstance(t, CC2UnitTemplate) for t in result)

    def test_generate_includes_sherman_easy_eight(self):
        """Verify: M4A3E8 Sherman "Easy Eight" is present with correct stats."""
        gen = VehicleVariantGenerator()
        result = gen.generate()
        ee = next(t for t in result if t.template_id == "us_sherman_easy_eight")
        assert ee.faction == Faction.AMERICAN
        assert ee.role == VehicleType.TANK_MEDIUM
        assert ee.vehicle_armor == 76
        assert ee.vehicle_speed == 42

    def test_generate_includes_panzer_iv_ausf_j(self):
        """Verify: PzKpfw IV Ausf J has reduced speed (no turret motor)."""
        gen = VehicleVariantGenerator()
        result = gen.generate()
        pz4 = next(t for t in result if t.template_id == "de_panzer_iv_ausf_j")
        assert pz4.faction == Faction.GERMAN
        assert pz4.vehicle_speed == 32
        assert pz4.vehicle_crew == 4

    def test_generate_includes_jagdpanther(self):
        """Verify: Jagdpanther is the most expensive German TD."""
        gen = VehicleVariantGenerator()
        result = gen.generate()
        jp = next(t for t in result if t.template_id == "de_jagdpanther")
        assert jp.weapon_primary_id == "kwk36_88mm"
        assert jp.vehicle_armor == 100
        assert jp.deployment_cost == 480

    def test_generate_includes_armored_cars(self):
        """Verify: M8 Greyhound and SdKfz 234 Puma are present."""
        gen = VehicleVariantGenerator()
        result = gen.generate()
        ids = {t.template_id for t in result}
        assert "us_m8_greyhound" in ids
        assert "de_sdkfz_234_puma" in ids

    def test_generate_includes_tetrarch(self):
        """Verify: British Tetrarch airborne light tank is present."""
        gen = VehicleVariantGenerator()
        result = gen.generate()
        tet = next(t for t in result if t.template_id == "uk_tetrarch")
        assert tet.faction == Faction.BRITISH
        assert tet.role == VehicleType.TANK_LIGHT

    def test_generate_includes_halftrack_variants(self):
        """Verify: SdKfz 251/16 (flamethrower) and 251/9 (Stummel) are present."""
        gen = VehicleVariantGenerator()
        result = gen.generate()
        ids = {t.template_id for t in result}
        assert "de_sdkfz_251_16" in ids
        assert "de_sdkfz_251_9" in ids

    def test_all_templates_have_unique_ids(self):
        """Verify: No duplicate template_id in vehicle variants."""
        gen = VehicleVariantGenerator()
        result = gen.generate()
        ids = [t.template_id for t in result]
        assert len(ids) == len(set(ids))

    def test_all_vehicle_templates_have_armor_and_speed(self):
        """Verify: Every vehicle template has positive armor and speed."""
        gen = VehicleVariantGenerator()
        result = gen.generate()
        for t in result:
            assert t.vehicle_armor > 0, f"{t.template_id} missing armor"
            assert t.vehicle_speed > 0, f"{t.template_id} missing speed"
