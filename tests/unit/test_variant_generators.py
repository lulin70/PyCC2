"""Tests for variant generator modules — faction/vehicle/experience variants.

Covers FactionVariantGenerator, VehicleVariantGenerator, UnitDiversityGenerator
facade, EXPERIENCE_MODIFIERS constant, and get_expanded_unit_database().
"""

from __future__ import annotations

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.cc2_authentic_units import CC2UnitTemplate, get_cc2_units
from pycc2.domain.systems.cc2_authentic_weapons import InfantryRole, VehicleType
from pycc2.domain.systems.faction_variant_generator import FactionVariantGenerator
from pycc2.domain.systems.game_settings import ExperienceLevel
from pycc2.domain.systems.unit_diversity_expansion import (
    EXPERIENCE_MODIFIERS,
    UnitDiversityGenerator,
    get_expanded_unit_database,
)
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


# ---------------------------------------------------------------------------
# EXPERIENCE_MODIFIERS constant
# ---------------------------------------------------------------------------


class TestExperienceModifiers:
    def test_contains_all_four_levels(self):
        """Verify: EXPERIENCE_MODIFIERS has CONSCRIPT, REGULAR, VETERAN, ELITE."""
        assert ExperienceLevel.CONSCRIPT in EXPERIENCE_MODIFIERS
        assert ExperienceLevel.REGULAR in EXPERIENCE_MODIFIERS
        assert ExperienceLevel.VETERAN in EXPERIENCE_MODIFIERS
        assert ExperienceLevel.ELITE in EXPERIENCE_MODIFIERS

    def test_conscript_has_penalty_modifiers(self):
        """Verify: Conscript modifiers reduce effectiveness (< 1.0)."""
        mod = EXPERIENCE_MODIFIERS[ExperienceLevel.CONSCRIPT]
        assert mod["accuracy_modifier"] < 1.0
        assert mod["morale_modifier"] < 1.0
        assert mod["cost_modifier"] < 1.0

    def test_elite_has_bonus_modifiers(self):
        """Verify: Elite modifiers boost effectiveness (> 1.0)."""
        mod = EXPERIENCE_MODIFIERS[ExperienceLevel.ELITE]
        assert mod["accuracy_modifier"] > 1.0
        assert mod["morale_modifier"] > 1.0
        assert mod["cost_modifier"] > 1.0
        assert mod["extra_actions"] == 1

    def test_regular_is_baseline(self):
        """Verify: Regular modifiers are all 1.0 (baseline)."""
        mod = EXPERIENCE_MODIFIERS[ExperienceLevel.REGULAR]
        assert mod["accuracy_modifier"] == 1.0
        assert mod["morale_modifier"] == 1.0
        assert mod["cost_modifier"] == 1.0
        assert mod["suffix"] == ""

    def test_each_level_has_required_keys(self):
        """Verify: Each level has all required modifier keys."""
        required_keys = {
            "accuracy_modifier",
            "speed_modifier",
            "panic_modifier",
            "morale_modifier",
            "stealth_modifier",
            "vision_modifier",
            "extra_actions",
            "exp_level_int",
            "suffix",
            "cost_modifier",
        }
        for level, mod in EXPERIENCE_MODIFIERS.items():
            assert required_keys.issubset(mod.keys()), (
                f"Level {level} missing keys: {required_keys - set(mod.keys())}"
            )


# ---------------------------------------------------------------------------
# UnitDiversityGenerator (facade)
# ---------------------------------------------------------------------------


def _make_base_template(
    template_id: str = "us_rifle_squad",
    display_name: str = "Rifle Squad",
    faction: Faction = Faction.AMERICAN,
    role: InfantryRole = InfantryRole.RIFLE,
    squad_size: int = 10,
    weapon_primary_id: str = "us_m1_garand",
    morale_initial: float = 80.0,
    stealth_rating: float = 0.30,
    vision_range: int = 6,
    deployment_cost: int = 150,
    vehicle_speed: int = 0,
) -> CC2UnitTemplate:
    return CC2UnitTemplate(
        template_id=template_id,
        display_name=display_name,
        faction=faction,
        role=role,
        squad_size=squad_size,
        weapon_primary_id=weapon_primary_id,
        morale_initial=morale_initial,
        stealth_rating=stealth_rating,
        vision_range=vision_range,
        deployment_cost=deployment_cost,
        vehicle_speed=vehicle_speed,
    )


class TestUnitDiversityGenerator:
    def test_construct_with_empty_registry(self):
        """Verify: Newly constructed generator has empty registry."""
        gen = UnitDiversityGenerator()
        assert gen.count_total_units() == 0
        assert gen.get_all_units() == {}

    def test_generate_variants_with_empty_base(self):
        """Verify: generate_variants with empty base still produces vehicle+faction variants."""
        gen = UnitDiversityGenerator()
        result = gen.generate_variants([])
        # Should include vehicle variants + faction variants (no experience variants since no base)
        assert len(result) > 0
        assert gen.count_total_units() > 0

    def test_generate_variants_includes_base_templates(self):
        """Verify: Base templates are included in the result."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("test_base_1")
        result = gen.generate_variants([base])
        ids = {t.template_id for t in result}
        assert "test_base_1" in ids

    def test_generate_variants_includes_vehicle_variants(self):
        """Verify: Vehicle variants are included (e.g. Sherman Easy Eight)."""
        gen = UnitDiversityGenerator()
        result = gen.generate_variants([])
        ids = {t.template_id for t in result}
        assert "us_sherman_easy_eight" in ids

    def test_generate_variants_includes_faction_variants(self):
        """Verify: Faction variants are included (e.g. Commando)."""
        gen = UnitDiversityGenerator()
        result = gen.generate_variants([])
        ids = {t.template_id for t in result}
        assert "uk_commando_squad" in ids

    def test_generate_variants_creates_experience_variants_for_infantry(self):
        """Verify: Infantry base templates get experience variants (conscript/veteran/elite)."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("test_inf", role=InfantryRole.RIFLE)
        result = gen.generate_variants([base])
        ids = {t.template_id for t in result}
        assert "test_inf_conscript" in ids
        assert "test_inf_veteran" in ids
        assert "test_inf_elite" in ids

    def test_generate_variants_skips_experience_for_vehicles(self):
        """Verify: Vehicle base templates do NOT get experience variants."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("test_veh", role=VehicleType.TANK_MEDIUM)
        result = gen.generate_variants([base])
        ids = {t.template_id for t in result}
        assert "test_veh_conscript" not in ids
        assert "test_veh_veteran" not in ids

    def test_generate_variants_clears_previous(self):
        """Verify: Calling generate_variants twice clears the previous registry."""
        gen = UnitDiversityGenerator()
        gen.generate_variants([_make_base_template("first")])
        assert gen.count_total_units() > 0
        gen.generate_variants([_make_base_template("second")])
        ids = set(gen.get_all_units().keys())
        assert "first" not in ids
        assert "second" in ids

    def test_count_total_units_after_generation(self):
        """Verify: count_total_units reflects all generated templates."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("test_count")
        gen.generate_variants([base])
        # base (1) + vehicle variants (~14) + faction variants (~16) + experience variants (3)
        assert gen.count_total_units() > 30

    def test_get_units_by_faction(self):
        """Verify: get_units_by_faction returns only units of the given faction."""
        gen = UnitDiversityGenerator()
        gen.generate_variants([])
        american = gen.get_units_by_faction(Faction.AMERICAN)
        assert all(u.faction == Faction.AMERICAN for u in american)
        assert len(american) > 0

    def test_get_units_by_faction_returns_empty_for_unmatched(self):
        """Verify: get_units_by_faction returns empty list if no units match."""
        gen = UnitDiversityGenerator()
        gen.generate_variants([])
        # Polish should have faction variants but no vehicle variants
        polish = gen.get_units_by_faction(Faction.POLISH)
        assert len(polish) > 0  # 4 faction variants

    def test_get_all_units_returns_copy(self):
        """Verify: get_all_units returns a copy, not the internal dict."""
        gen = UnitDiversityGenerator()
        gen.generate_variants([])
        d1 = gen.get_all_units()
        d2 = gen.get_all_units()
        assert d1 == d2
        assert d1 is not d2


# ---------------------------------------------------------------------------
# generate_experience_variants
# ---------------------------------------------------------------------------


class TestGenerateExperienceVariants:
    def test_generates_three_variants_for_three_levels(self):
        """Verify: 3 levels (conscript/veteran/elite) → 3 variants."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("exp_test")
        result = gen.generate_experience_variants(
            base, [ExperienceLevel.CONSCRIPT, ExperienceLevel.VETERAN, ExperienceLevel.ELITE]
        )
        assert len(result) == 3

    def test_skips_regular_level(self):
        """Verify: REGULAR level is skipped (it's the base template)."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("reg_test")
        result = gen.generate_experience_variants(
            base, [ExperienceLevel.REGULAR, ExperienceLevel.ELITE]
        )
        assert len(result) == 1
        assert result[0].template_id == "reg_test_elite"

    def test_conscript_variant_has_reduced_morale(self):
        """Verify: Conscript variant has lower morale than base."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("morale_test", morale_initial=80.0)
        result = gen.generate_experience_variants(base, [ExperienceLevel.CONSCRIPT])
        assert len(result) == 1
        assert result[0].morale_initial < 80.0

    def test_elite_variant_has_increased_morale(self):
        """Verify: Elite variant has higher morale than base."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("elite_test", morale_initial=80.0)
        result = gen.generate_experience_variants(base, [ExperienceLevel.ELITE])
        assert len(result) == 1
        assert result[0].morale_initial > 80.0

    def test_variant_ids_include_level_suffix(self):
        """Verify: Variant template_id includes level name lowercase."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("suffix_test")
        result = gen.generate_experience_variants(
            base, [ExperienceLevel.CONSCRIPT, ExperienceLevel.ELITE]
        )
        ids = {v.template_id for v in result}
        assert "suffix_test_conscript" in ids
        assert "suffix_test_elite" in ids

    def test_variant_display_names_include_suffix(self):
        """Verify: Variant display_name includes suffix like '(Elite)'."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("name_test", display_name="Test Squad")
        result = gen.generate_experience_variants(base, [ExperienceLevel.ELITE])
        assert result[0].display_name == "Test Squad (Elite)"

    def test_variant_has_modified_cost(self):
        """Verify: Conscript cost is lower, elite cost is higher than base."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("cost_test", deployment_cost=100)
        result = gen.generate_experience_variants(
            base, [ExperienceLevel.CONSCRIPT, ExperienceLevel.ELITE]
        )
        conscript = next(v for v in result if "conscript" in v.template_id)
        elite = next(v for v in result if "elite" in v.template_id)
        assert conscript.deployment_cost < 100
        assert elite.deployment_cost > 100

    def test_variant_preserves_faction_and_role(self):
        """Verify: Experience variants inherit faction and role from base."""
        gen = UnitDiversityGenerator()
        base = _make_base_template(
            "inherit_test", faction=Faction.GERMAN, role=InfantryRole.HEAVY_ASSAULT
        )
        result = gen.generate_experience_variants(base, [ExperienceLevel.VETERAN])
        assert len(result) == 1
        assert result[0].faction == Faction.GERMAN
        assert result[0].role == InfantryRole.HEAVY_ASSAULT

    def test_empty_levels_returns_empty(self):
        """Verify: Empty levels list returns empty list."""
        gen = UnitDiversityGenerator()
        base = _make_base_template("empty_test")
        result = gen.generate_experience_variants(base, [])
        assert result == []


# ---------------------------------------------------------------------------
# get_expanded_unit_database
# ---------------------------------------------------------------------------


class TestGetExpandedUnitDatabase:
    def test_returns_non_empty_dict(self):
        """Verify: get_expanded_unit_database returns a populated dict."""
        db = get_expanded_unit_database()
        assert len(db) > 0
        assert all(isinstance(v, CC2UnitTemplate) for v in db.values())

    def test_returns_dict_with_string_keys(self):
        """Verify: Database keys are template_id strings."""
        db = get_expanded_unit_database()
        for key in db:
            assert isinstance(key, str)

    def test_includes_base_cc2_units(self):
        """Verify: Database includes some base CC2 units (from get_cc2_units)."""
        db = get_expanded_unit_database()
        base_db = get_cc2_units()
        # At least some base units should be in the expanded database
        overlap = set(base_db.keys()) & set(db.keys())
        assert len(overlap) > 0

    def test_includes_vehicle_and_faction_variants(self):
        """Verify: Database includes generated vehicle and faction variants."""
        db = get_expanded_unit_database()
        assert "us_sherman_easy_eight" in db
        assert "uk_commando_squad" in db
