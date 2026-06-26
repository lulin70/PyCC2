"""CC2 authentic unit factory — faction-specific entries."""

from __future__ import annotations

from pycc2.domain.systems.cc2_authentic_weapons import (
    Faction,
    InfantryRole,
    VehicleType,
)
from pycc2.domain.systems.unit_templates import CC2UnitTemplate


def _build_german_units() -> dict[str, CC2UnitTemplate]:
    units: dict[str, CC2UnitTemplate] = {}
    # GERMAN FORCES (15th Army / SS Panzer Divisions)
    # ================================================================

    units["de_rifle_squad"] = CC2UnitTemplate(
        template_id="de_rifle_squad",
        display_name="German Rifle Squad (Grenadier)",
        faction=Faction.GERMAN,
        role=InfantryRole.RIFLE,
        squad_size=10,
        weapon_primary_id="de_kar98k",
        weapon_secondary_id="de_mp40",
        experience_level=1,
        morale_initial=85.0,
        stealth_rating=0.30,
        vision_range=6,
        deployment_cost=125,
        historical_notes="Standard Wehrmacht Grenadier squad, Kar98k rifles",
    )

    units["de_ss_squad"] = CC2UnitTemplate(
        template_id="de_ss_squad",
        display_name="SS Panzergrenadier Squad",
        faction=Faction.GERMAN,
        role=InfantryRole.RIFLE,
        squad_size=11,
        weapon_primary_id="de_mp44",  # StG 44 assault rifles!
        weapon_secondary_id="de_mp40",
        experience_level=2,
        morale_initial=92.0,
        is_fanatic=True,  # *** SS FANATIC UNIT - NEVER PANICS! ***
        stealth_rating=0.28,
        vision_range=6,
        deployment_cost=165,
        historical_notes="Elite SS Panzergrenadiers, StG 44 rifles, fanatical morale",
    )

    units["de_ss_panzergrenadier"] = CC2UnitTemplate(
        template_id="de_ss_panzergrenadier",
        display_name="SS Panzergrenadiere",
        faction=Faction.GERMAN,
        role=InfantryRole.HEAVY_ASSAULT,
        squad_size=12,
        weapon_primary_id="de_kar98k",
        weapon_secondary_id="de_mg42",
        experience_level=3,
        morale_initial=95.0,
        is_fanatic=True,
        stealth_rating=0.27,
        vision_range=6,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        deployment_cost=130,
        max_per_battle=3,
        historical_notes="Elite SS troops with Kar98k and MG42, higher morale and fanatical resolve",
    )

    units["de_reservist_squad"] = CC2UnitTemplate(
        template_id="de_reservist_squad",
        display_name="Reservisten Squad",
        faction=Faction.GERMAN,
        role=InfantryRole.RIFLE,
        squad_size=8,
        weapon_primary_id="de_kar98k",
        weapon_secondary_id=None,
        experience_level=0,
        morale_initial=55.0,
        stealth_rating=0.30,
        vision_range=5,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        deployment_cost=60,
        max_per_battle=4,
        historical_notes="Poor quality reservist troops, low morale and minimal equipment",
    )

    units["de_mg42_team"] = CC2UnitTemplate(  # *** THE LEGENDARY MG42 ***
        template_id="de_mg42_team",
        display_name="MG42 Machine Gun Team",
        faction=Faction.GERMAN,
        role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id="de_mg42",  # *** HITLER'S SAW - SUPPRESSION 0.90 ***
        weapon_secondary_id="de_mp40",
        experience_level=1,
        morale_initial=83.0,
        stealth_rating=0.24,
        vision_range=5,
        deployment_cost=175,
        historical_notes="MG42 team - most feared German weapon, 1200 RPM, devastating suppression",
    )

    units["de_mg34_team"] = CC2UnitTemplate(  # *** MG34 - EARLIER VARIANT ***
        template_id="de_mg34_team",
        display_name="MG34 Machine Gun Team",
        faction=Faction.GERMAN,
        role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id="de_mg34",  # Earlier universal MG
        weapon_secondary_id="de_kar98k",
        experience_level=1,
        morale_initial=81.0,
        stealth_rating=0.26,
        vision_range=5,
        deployment_cost=150,
        historical_notes="MG34 team - still widely used alongside MG42",
    )

    units["de_panzerschreck_team"] = CC2UnitTemplate(
        template_id="de_panzerschreck_team",
        display_name="Panzerschreck Team",
        faction=Faction.GERMAN,
        role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id="de_panzerschreck",  # 88mm RPzB
        weapon_secondary_id="de_mp40",
        experience_level=1,
        morale_initial=79.0,
        stealth_rating=0.33,
        vision_range=6,
        has_demolitions=True,
        deployment_cost=155,
        historical_notes="88mm rocket AT team, copied from Bazooka but improved",
    )

    units["de_panzerfaust_team"] = CC2UnitTemplate(
        template_id="de_panzerfaust_team",
        display_name="Panzerfaust Team",
        faction=Faction.GERMAN,
        role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id="de_panzerfaust",  # Disposable one-shot
        weapon_secondary_id="de_kar98k",
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.36,
        vision_range=5,
        deployment_cost=120,  # Cheaper (disposable weapon)
        historical_notes="Disposable Panzerfaust team, cheap and numerous late-war",
    )

    units["de_flame_team"] = CC2UnitTemplate(
        template_id="de_flame_team",
        display_name="Flammenwerfer Team",
        faction=Faction.GERMAN,
        role=InfantryRole.FLAMETHROWER,
        squad_size=3,
        weapon_primary_id="de_flammenwerfer_41",
        weapon_secondary_id="de_mp40",
        experience_level=1,
        morale_initial=73.0,
        stealth_rating=0.38,
        vision_range=5,
        deployment_cost=168,
        historical_notes="German flamethrower operators",
    )

    units["de_flamethrower_squad"] = CC2UnitTemplate(
        template_id="de_flamethrower_squad",
        display_name="Flamethrower Squad",
        faction=Faction.GERMAN,
        role=InfantryRole.ENGINEER,
        squad_size=4,
        weapon_primary_id="de_flammenwerfer",
        weapon_secondary_id=None,
        experience_level=1,
        morale_initial=72.0,
        stealth_rating=0.36,
        vision_range=5,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        deployment_cost=200,
        max_per_battle=1,
        historical_notes="German flamethrower assault squad, devastating vs infantry in buildings",
    )

    units["de_grw50_team"] = CC2UnitTemplate(  # *** LIGHT MORTAR ***
        template_id="de_grw50_team",
        display_name="GrW 36 50mm Mortar Team",
        faction=Faction.GERMAN,
        role=InfantryRole.RIFLE,
        squad_size=3,
        weapon_primary_id="de_grw36_50mm",
        weapon_secondary_id="de_kar98k",
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.34,
        vision_range=6,
        can_capture=False,
        deployment_cost=135,
        historical_notes="Light 50mm platoon mortar team",
    )

    units["de_grw81_team"] = CC2UnitTemplate(  # *** HEAVY MORTAR ***
        template_id="de_grw81_team",
        display_name="GrW 34 81mm Mortar Team",
        faction=Faction.GERMAN,
        role=InfantryRole.RIFLE,
        squad_size=4,
        weapon_primary_id="de_grw34_81mm",
        weapon_secondary_id="de_mp40",
        experience_level=1,
        morale_initial=76.0,
        stealth_rating=0.31,
        vision_range=5,
        can_capture=False,
        deployment_cost=170,
        historical_notes="Medium 81mm battalion mortar team",
    )

    # --- GERMAN ARMOR ---

    units["de_panzer_iv"] = CC2UnitTemplate(
        template_id="de_panzer_iv",
        display_name="Panzer IV Ausf H/J",
        faction=Faction.GERMAN,
        role=VehicleType.TANK_MEDIUM,
        squad_size=1,
        weapon_primary_id="kwk40_75mm",  # Long-barrel 75mm
        weapon_secondary_id="coax_mg34",
        vehicle_armor=80,
        vehicle_speed=40,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=87.0,
        stealth_rating=0.14,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=360,
        historical_notes="Main German medium tank, excellent all-around, long 75mm KwK 40 L/48",
    )

    units["de_tiger_i"] = CC2UnitTemplate(  # *** THE TIGER I ***
        template_id="de_tiger_i",
        display_name="Tiger I E",
        faction=Faction.GERMAN,
        role=VehicleType.TANK_HEAVY,
        squad_size=1,
        weapon_primary_id="kwk36_88mm",  # *** 88MM KWK 36 - DEVASTATING ***
        weapon_secondary_id="coax_mg34",
        vehicle_armor=100,
        vehicle_speed=38,
        vehicle_crew=5,
        experience_level=2,
        morale_initial=95.0,
        stealth_rating=0.10,  # Very loud and big!
        vision_range=8,
        can_deploy_in_building=False,
        deployment_cost=550,
        historical_notes="Tiger I heavy tank - 88mm gun, 100mm armor, terror weapon, rare but deadly",
    )

    units["de_panther"] = CC2UnitTemplate(  # *** THE PANTHER ***
        template_id="de_panther",
        display_name="Panther D/A/G",
        faction=Faction.GERMAN,
        role=VehicleType.TANK_HEAVY,
        squad_size=1,
        weapon_primary_id="kwk42_75mm",  # High-velocity 75mm L/70
        weapon_secondary_id="coax_mg34",
        vehicle_armor=120,  # Sloped armor!
        vehicle_speed=46,
        vehicle_crew=5,
        experience_level=2,
        morale_initial=92.0,
        stealth_rating=0.12,
        vision_range=8,
        can_deploy_in_building=False,
        deployment_cost=500,
        historical_notes="Panther - best German medium/heavy hybrid, excellent gun and armor",
    )

    units["de_stug_iii"] = CC2UnitTemplate(  # *** STURMGESCHÜTZ III ***
        template_id="de_stug_iii",
        display_name="StuG III G",
        faction=Faction.GERMAN,
        role=VehicleType.TANK_DESTROYER,
        squad_size=1,
        weapon_primary_id="kwk40_75mm",  # Same gun as PzIV
        vehicle_armor=80,
        vehicle_speed=40,
        vehicle_crew=4,
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.14,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=340,
        historical_notes="Assault gun - no turret, low profile, excellent ambush weapon",
    )

    units["de_flammpanzer"] = CC2UnitTemplate(
        template_id="de_flammpanzer",
        display_name="Flammpanzer III",
        faction=Faction.GERMAN,
        role=VehicleType.FLAME_TANK,
        squad_size=3,
        weapon_primary_id="de_flammenwerfer",
        weapon_secondary_id=None,
        vehicle_armor=50,
        vehicle_speed=38,
        vehicle_crew=3,
        experience_level=1,
        morale_initial=80.0,
        stealth_rating=0.13,
        vision_range=5,
        can_deploy_in_building=False,
        can_deploy_in_open=True,
        deployment_cost=300,
        max_per_battle=1,
        historical_notes="Flame tank variant of Panzer III, devastating vs infantry and fortifications",
    )

    units["de_sdkfz_251"] = CC2UnitTemplate(
        template_id="de_sdkfz_251",
        display_name="SdKfz 251/1 Half-track",
        faction=Faction.GERMAN,
        role=VehicleType.HALFTRACK,
        squad_size=2,
        weapon_primary_id="coax_mg34",
        weapon_secondary_id=None,
        vehicle_armor=14,
        vehicle_speed=53,
        vehicle_crew=3,
        experience_level=1,
        morale_initial=81.0,
        stealth_rating=0.17,
        vision_range=6,
        can_deploy_in_building=False,
        can_deploy_in_open=True,
        deployment_cost=180,
        max_per_battle=2,
        historical_notes="German halftrack, transports Panzergrenadiers",
    )
    units["de_pak40_at_gun"] = CC2UnitTemplate(
        template_id="de_pak40_at_gun",
        display_name="7.5cm Pak 40 AT Gun",
        faction=Faction.GERMAN,
        role=InfantryRole.ANTI_TANK,
        squad_size=4,
        weapon_primary_id="de_pak40",
        weapon_secondary_id=None,
        can_deploy_in_building=False,
        can_deploy_in_open=True,
        deployment_cost=280,
        max_per_battle=2,
    )
    return units
