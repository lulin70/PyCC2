"""CC2 authentic unit factory — faction-specific entries."""
from __future__ import annotations

from pycc2.domain.systems.cc2_authentic_weapons import (
    Faction,
    InfantryRole,
    VehicleType,
)
from pycc2.domain.systems.unit_templates import CC2UnitTemplate


def _build_british_units() -> dict[str, CC2UnitTemplate]:
    units: dict[str, CC2UnitTemplate] = {}
    # BRITISH FORCES (1st Airborne / XXX Corps)
    # ================================================================

    units["uk_rifle_section"] = CC2UnitTemplate(
        template_id="uk_rifle_section",
        display_name="British Rifle Section",
        faction=Faction.BRITISH,
        role=InfantryRole.RIFLE,
        squad_size=10,  # British sections smaller than US squads
        weapon_primary_id="uk_lee_enfield",
        weapon_secondary_id="uk_sten",
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.32,
        vision_range=6,
        deployment_cost=115,
        historical_notes="British airborne section, Lee-Enfields, 10 men",
    )

    units["uk_bren_team"] = CC2UnitTemplate(
        template_id="uk_bren_team",
        display_name="Bren Gun Team",
        faction=Faction.BRITISH,
        role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id="uk_bren",  # Main British LMG
        weapon_secondary_id="uk_sten",
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.26,
        vision_range=5,
        deployment_cost=155,
        historical_notes="Bren gun team, .303 LMG, reliable and accurate",
    )

    units["uk_piat_team"] = CC2UnitTemplate(
        template_id="uk_piat_team",
        display_name="PIAT Team",
        faction=Faction.BRITISH,
        role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id="uk_piat",  # Unique British AT weapon
        weapon_secondary_id="uk_sten",
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.34,
        vision_range=6,
        has_demolitions=True,
        deployment_cost=145,
        historical_notes="PIAT anti-tank team, spring-powered awkward but effective",
    )

    units["uk_flame_team"] = CC2UnitTemplate(
        template_id="uk_flame_team",
        display_name="British Flamethrower Team",
        faction=Faction.BRITISH,
        role=InfantryRole.FLAMETHROWER,
        squad_size=3,
        weapon_primary_id="uk_flamethrower",
        weapon_secondary_id="uk_sten",
        experience_level=1,
        morale_initial=74.0,
        stealth_rating=0.39,
        vision_range=5,
        deployment_cost=165,
        historical_notes="Lifebuoy flamethrower operators",
    )

    units["uk_para_engineer_squad"] = CC2UnitTemplate(
        template_id="uk_para_engineer_squad",
        display_name="Para Engineer Squad",
        faction=Faction.BRITISH,
        role=InfantryRole.ENGINEER,
        squad_size=8,
        weapon_primary_id="uk_lee_enfield",
        weapon_secondary_id="uk_sten",
        experience_level=2,
        morale_initial=86.0,
        stealth_rating=0.35,
        vision_range=6,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        has_demolitions=True,
        deployment_cost=180,
        max_per_battle=1,
        historical_notes="British Para combat engineers, demolition specialists with airborne training",
    )

    units["uk_churchill_mkiv"] = CC2UnitTemplate(
        template_id="uk_churchill_mkiv",
        display_name="Churchill Mk IV/VII",
        faction=Faction.BRITISH,
        role=VehicleType.TANK_HEAVY,
        squad_size=1,
        weapon_primary_id="qv_75mm",  # 75mm or 95mm CS variant
        weapon_secondary_id="coax_besa",
        vehicle_armor=102,  # Heavily armored!
        vehicle_speed=28,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=88.0,
        stealth_rating=0.12,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=380,
        historical_notes="British heavy infantry tank, very thick armor, slow but tough",
    )

    units["uk_cromwell"] = CC2UnitTemplate(
        template_id="uk_cromwell",
        display_name="Cromwell Mk IV/VII",
        faction=Faction.BRITISH,
        role=VehicleType.TANK_MEDIUM,
        squad_size=1,
        weapon_primary_id="qv_75mm",
        weapon_secondary_id="coax_besa",
        vehicle_armor=76,
        vehicle_speed=64,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.16,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=340,
        historical_notes="Cruiser tank, fast and well-armed, standard XXX Corps issue",
    )

    units["uk_firefly"] = CC2UnitTemplate(
        template_id="uk_firefly",
        display_name="Sherman VC Firefly",
        faction=Faction.BRITISH,
        role=VehicleType.TANK_MEDIUM,
        squad_size=1,
        weapon_primary_id="qf_17pdr",  # *** 17-POUNDER! Best allied AT gun ***
        weapon_secondary_id="coax_besa",
        vehicle_armor=64,
        vehicle_speed=40,
        vehicle_crew=5,
        experience_level=2,
        morale_initial=86.0,
        stealth_rating=0.14,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=400,
        historical_notes="Sherman hull with 17-pdr gun, can kill Tigers/Panthers at range",
    )

    units["uk_crocodile"] = CC2UnitTemplate(
        template_id="uk_crocodile",
        display_name="Churchill Crocodile",
        faction=Faction.BRITISH,
        role=VehicleType.FLAME_TANK,
        squad_size=1,
        weapon_primary_id="qv_75mm",
        vehicle_armor=102,
        vehicle_speed=24,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=85.0,
        stealth_rating=0.11,  # Very conspicuous!
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=450,
        historical_notes="Flamethrower tank, terrifying to infantry, limited fuel",
    )

    units["uk_sherman_dd"] = CC2UnitTemplate(
        template_id="uk_sherman_dd",
        display_name="Sherman DD (Duplex Drive)",
        faction=Faction.BRITISH,
        role=VehicleType.TANK_MEDIUM,
        squad_size=5,
        weapon_primary_id="qv_75mm",
        weapon_secondary_id="coax_besa",
        vehicle_armor=64,
        vehicle_speed=40,
        vehicle_crew=5,
        is_amphibious=True,
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.15,
        vision_range=7,
        can_deploy_in_building=False,
        can_deploy_in_open=True,
        deployment_cost=350,
        max_per_battle=1,
        historical_notes="Amphibious Sherman variant with duplex drive, used during river crossings",
    )
    # --- BRITISH PARA UNITS ---

    units["uk_para_mortar_squad"] = CC2UnitTemplate(
        template_id="uk_para_mortar_squad",
        display_name="British Para 3-inch Mortar Squad",
        faction=Faction.BRITISH,
        role=InfantryRole.MORTAR,
        squad_size=5,
        weapon_primary_id="uk_3inch_mortar",
        weapon_secondary_id="uk_sten",
        experience_level=1,
        morale_initial=78.0,
        stealth_rating=0.28,
        vision_range=5,
        can_capture=False,
        deployment_cost=200,
        max_per_battle=2,
        historical_notes="British Para mortar squad with 3-inch mortar, indirect fire support",
    )

    units["uk_para_officer"] = CC2UnitTemplate(
        template_id="uk_para_officer",
        display_name="British Para Officer",
        faction=Faction.BRITISH,
        role=InfantryRole.OFFICER,
        squad_size=3,
        weapon_primary_id="uk_officer_sten",
        weapon_secondary_id="uk_lee_enfield",
        experience_level=2,
        morale_initial=92.0,
        stealth_rating=0.35,
        vision_range=7,
        is_command_unit=True,
        can_capture=False,
        deployment_cost=150,
        max_per_battle=1,
        historical_notes="British Para officer, provides morale bonus to nearby units",
    )

    units["uk_para_sniper"] = CC2UnitTemplate(
        template_id="uk_para_sniper",
        display_name="British Para Sniper Team",
        faction=Faction.BRITISH,
        role=InfantryRole.SNIPER,
        squad_size=2,
        weapon_primary_id="uk_sniper_no4",
        experience_level=3,
        morale_initial=80.0,
        stealth_rating=0.65,
        vision_range=12,
        can_capture=False,
        deployment_cost=180,
        max_per_battle=1,
        historical_notes="British Para sniper team with scoped Lee-Enfield No.4(T)",
    )

    units["uk_para_recon"] = CC2UnitTemplate(
        template_id="uk_para_recon",
        display_name="British Para Recon Team",
        faction=Faction.BRITISH,
        role=InfantryRole.RECON,
        squad_size=4,
        weapon_primary_id="uk_enfield_no4",
        weapon_secondary_id="uk_sten",
        experience_level=2,
        morale_initial=83.0,
        stealth_rating=0.50,
        vision_range=9,
        deployment_cost=120,
        max_per_battle=1,
        historical_notes="British Para reconnaissance team, small fast unit with good vision",
    )
    # ANTI-TANK GUN TEAMS (Fixed AT artillery)
    # ================================================================

    units["uk_6pdr_at_gun"] = CC2UnitTemplate(
        template_id="uk_6pdr_at_gun",
        display_name="6-pounder AT Gun",
        faction=Faction.BRITISH,
        role=InfantryRole.ANTI_TANK,
        squad_size=4,
        weapon_primary_id="uk_6pdr",
        weapon_secondary_id=None,
        can_deploy_in_building=False,
        can_deploy_in_open=True,
        deployment_cost=250,
        max_per_battle=2,
    )
    # --- BRITISH ARMOR EXPANDED ---

    units["uk_cromwell_tank"] = CC2UnitTemplate(
        template_id="uk_cromwell_tank",
        display_name="Cromwell Tank",
        faction=Faction.BRITISH,
        role=VehicleType.TANK_MEDIUM,
        squad_size=5,
        weapon_primary_id="uk_75mm_cromwell",
        weapon_secondary_id="coax_besa",
        vehicle_armor=76,
        vehicle_speed=64,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.16,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=300,
        max_per_battle=2,
        historical_notes="Cromwell cruiser tank, fast and well-armed, XXX Corps standard",
    )

    units["uk_carrier"] = CC2UnitTemplate(
        template_id="uk_carrier",
        display_name="Universal Carrier",
        faction=Faction.BRITISH,
        role=VehicleType.HALFTRACK,
        squad_size=2,
        weapon_primary_id="uk_bren",
        weapon_secondary_id=None,
        vehicle_armor=12,
        vehicle_speed=48,
        vehicle_crew=2,
        experience_level=1,
        morale_initial=80.0,
        stealth_rating=0.20,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=120,
        max_per_battle=3,
        historical_notes="Universal Carrier (Bren Carrier), light tracked transport with Bren gun",
    )
    return units
