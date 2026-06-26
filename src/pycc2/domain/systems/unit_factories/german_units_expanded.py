"""CC2 authentic unit factory — faction-specific entries."""
from __future__ import annotations

from pycc2.domain.systems.cc2_authentic_weapons import (
    Faction,
    InfantryRole,
    VehicleType,
)
from pycc2.domain.systems.unit_templates import CC2UnitTemplate


def _build_german_expanded_units() -> dict[str, CC2UnitTemplate]:
    units: dict[str, CC2UnitTemplate] = {}
    # --- GERMAN EXPANDED UNITS ---

    units["de_mortar_squad"] = CC2UnitTemplate(
        template_id="de_mortar_squad",
        display_name="German 81mm Mortar Squad",
        faction=Faction.GERMAN,
        role=InfantryRole.MORTAR,
        squad_size=5,
        weapon_primary_id="de_81mm_mortar",
        weapon_secondary_id="de_kar98k",
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.30,
        vision_range=5,
        can_capture=False,
        deployment_cost=190,
        max_per_battle=2,
        historical_notes="German 81mm mortar squad, GrW 34 battalion-level indirect fire",
    )

    units["de_panzergrenadier_mg"] = CC2UnitTemplate(
        template_id="de_panzergrenadier_mg",
        display_name="German Panzergrenadier MG Squad",
        faction=Faction.GERMAN,
        role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id="de_mg42",
        weapon_secondary_id="de_mp40",
        experience_level=1,
        morale_initial=83.0,
        stealth_rating=0.24,
        vision_range=5,
        deployment_cost=160,
        max_per_battle=2,
        historical_notes="Panzergrenadier MG squad with MG42, devastating suppression",
    )

    units["de_officer"] = CC2UnitTemplate(
        template_id="de_officer",
        display_name="German Officer",
        faction=Faction.GERMAN,
        role=InfantryRole.OFFICER,
        squad_size=3,
        weapon_primary_id="de_officer_p08",
        weapon_secondary_id="de_mp40",
        experience_level=2,
        morale_initial=90.0,
        stealth_rating=0.35,
        vision_range=7,
        is_command_unit=True,
        can_capture=False,
        deployment_cost=140,
        max_per_battle=1,
        historical_notes="German officer with Luger P08, provides morale bonus to nearby units",
    )

    units["de_sniper_team"] = CC2UnitTemplate(
        template_id="de_sniper_team",
        display_name="German Sniper Team",
        faction=Faction.GERMAN,
        role=InfantryRole.SNIPER,
        squad_size=2,
        weapon_primary_id="de_kar98k_sniper",
        experience_level=3,
        morale_initial=80.0,
        stealth_rating=0.65,
        vision_range=12,
        can_capture=False,
        deployment_cost=170,
        max_per_battle=1,
        historical_notes="German sniper team with scoped Kar98k ZF39",
    )

    units["de_recon_team"] = CC2UnitTemplate(
        template_id="de_recon_team",
        display_name="German Recon Team",
        faction=Faction.GERMAN,
        role=InfantryRole.RECON,
        squad_size=4,
        weapon_primary_id="de_kar98k",
        weapon_secondary_id="de_mp40",
        experience_level=2,
        morale_initial=82.0,
        stealth_rating=0.48,
        vision_range=9,
        deployment_cost=110,
        max_per_battle=1,
        historical_notes="German reconnaissance team, small fast unit with good vision",
    )

    units["de_panzerfaust60_team"] = CC2UnitTemplate(
        template_id="de_panzerfaust60_team",
        display_name="German Panzerfaust 60 Team",
        faction=Faction.GERMAN,
        role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id="de_panzerfaust60",
        weapon_secondary_id="de_kar98k",
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.36,
        vision_range=5,
        deployment_cost=160,
        max_per_battle=3,
        historical_notes="Panzerfaust 60 team, improved 60m range disposable AT weapon",
    )

    units["de_fallschirmjager"] = CC2UnitTemplate(
        template_id="de_fallschirmjager",
        display_name="German Fallschirmjäger Squad",
        faction=Faction.GERMAN,
        role=InfantryRole.RIFLE,
        squad_size=10,
        weapon_primary_id="de_fg42",
        weapon_secondary_id="de_mp40",
        experience_level=2,
        morale_initial=88.0,
        stealth_rating=0.32,
        vision_range=6,
        deployment_cost=120,
        max_per_battle=2,
        historical_notes="Elite German paratrooper squad with FG42 automatic rifles",
    )

    units["de_fallschirmjager_mg"] = CC2UnitTemplate(
        template_id="de_fallschirmjager_mg",
        display_name="Fallschirmjäger MG Squad",
        faction=Faction.GERMAN,
        role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id="de_mg42",
        weapon_secondary_id="de_fg42",
        experience_level=2,
        morale_initial=86.0,
        stealth_rating=0.25,
        vision_range=5,
        deployment_cost=160,
        max_per_battle=1,
        historical_notes="Fallschirmjäger MG squad with MG42, elite airborne support",
    )

    units["de_assault_pioneer"] = CC2UnitTemplate(
        template_id="de_assault_pioneer",
        display_name="German Assault Pioneer",
        faction=Faction.GERMAN,
        role=InfantryRole.ENGINEER,
        squad_size=8,
        weapon_primary_id="de_kar98k",
        weapon_secondary_id="de_flammenwerfer",
        experience_level=2,
        morale_initial=82.0,
        stealth_rating=0.35,
        vision_range=6,
        has_demolitions=True,
        deployment_cost=200,
        max_per_battle=1,
        historical_notes="German assault pioneers, demolition and flamethrower specialists",
    )
    # --- GERMAN ARMOR EXPANDED ---

    units["de_pziv_h"] = CC2UnitTemplate(
        template_id="de_pziv_h",
        display_name="Panzer IV Ausf. H",
        faction=Faction.GERMAN,
        role=VehicleType.TANK_MEDIUM,
        squad_size=5,
        weapon_primary_id="de_75mm_kwk40",
        weapon_secondary_id="coax_mg34",
        vehicle_armor=80,
        vehicle_speed=40,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=87.0,
        stealth_rating=0.14,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=320,
        max_per_battle=2,
        historical_notes="Panzer IV Ausf. H, improved armor and KwK 40 L/48 gun",
    )

    units["de_stug_iii_g"] = CC2UnitTemplate(
        template_id="de_stug_iii_g",
        display_name="StuG III Ausf. G",
        faction=Faction.GERMAN,
        role=VehicleType.TANK_DESTROYER,
        squad_size=4,
        weapon_primary_id="de_75mm_stug",
        weapon_secondary_id="coax_mg34",
        vehicle_armor=80,
        vehicle_speed=40,
        vehicle_crew=4,
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.16,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=280,
        max_per_battle=2,
        historical_notes="StuG III Ausf. G assault gun, low profile, excellent ambush weapon",
    )

    units["de_sdkfz_222"] = CC2UnitTemplate(
        template_id="de_sdkfz_222",
        display_name="SdKfz 222 Armored Car",
        faction=Faction.GERMAN,
        role=VehicleType.ARMORED_CAR,
        squad_size=3,
        weapon_primary_id="de_mg34_vehicle",
        weapon_secondary_id=None,
        vehicle_armor=30,
        vehicle_speed=80,
        vehicle_crew=3,
        experience_level=1,
        morale_initial=80.0,
        stealth_rating=0.20,
        vision_range=9,
        can_deploy_in_building=False,
        deployment_cost=140,
        max_per_battle=2,
        historical_notes="Light armored car, fast recon vehicle with MG34",
    )

    units["de_hummel"] = CC2UnitTemplate(
        template_id="de_hummel",
        display_name="Hummel SPG",
        faction=Faction.GERMAN,
        role=VehicleType.SP_ARTILLERY,
        squad_size=5,
        weapon_primary_id="de_150mm_hummel",
        weapon_secondary_id="coax_mg34",
        vehicle_armor=50,
        vehicle_speed=42,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.12,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=380,
        max_per_battle=1,
        historical_notes="Hummel self-propelled gun, 150mm howitzer, devastating indirect fire",
    )
    return units
