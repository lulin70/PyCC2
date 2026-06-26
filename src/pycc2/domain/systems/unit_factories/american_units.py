"""CC2 authentic unit factory — faction-specific entries."""
from __future__ import annotations

from pycc2.domain.systems.cc2_authentic_weapons import (
    Faction,
    InfantryRole,
    VehicleType,
)
from pycc2.domain.systems.unit_templates import CC2UnitTemplate


def _build_american_units() -> dict[str, CC2UnitTemplate]:
    units: dict[str, CC2UnitTemplate] = {}
    # AMERICAN FORCES (82nd Airborne / 101st Airborne)
    # ================================================================

    # --- INFANTRY CATEGORY ---

    units["us_rifle_squad"] = CC2UnitTemplate(
        template_id="us_rifle_squad",
        display_name="US Rifle Squad",
        faction=Faction.AMERICAN,
        role=InfantryRole.RIFLE,
        squad_size=12,
        weapon_primary_id="us_m1_garand",
        weapon_secondary_id="us_thompson",  # BAR or Thompson for squad leader
        experience_level=1,
        morale_initial=85.0,
        stealth_rating=0.30,
        vision_range=6,
        can_capture=True,
        deployment_cost=120,
        historical_notes="Standard US airborne rifle squad, 12 men with M1 Garands",
    )

    units["us_rifle_squad_veteran"] = CC2UnitTemplate(
        template_id="us_rifle_squad_veteran",
        display_name="Veteran Rifle Squad",
        faction=Faction.AMERICAN,
        role=InfantryRole.RIFLE,
        squad_size=11,
        weapon_primary_id="us_m1_garand",
        weapon_secondary_id="us_m1903_springfield",  # Designated marksman
        experience_level=2,
        morale_initial=90.0,
        stealth_rating=0.32,
        vision_range=7,
        deployment_cost=150,
        historical_notes="Battle-hardened squad from earlier campaigns",
    )

    units["us_machine_gun_team_a4"] = CC2UnitTemplate(  # M1919A4 (M42)
        template_id="us_machine_gun_team_a4",
        display_name="US MG Team (M1919A4)",
        faction=Faction.AMERICAN,
        role=InfantryRole.MACHINE_GUN,
        squad_size=5,
        weapon_primary_id="us_m1919a4",  # *** THE M42 HEAVY MG ***
        weapon_secondary_id="us_thompson",
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.25,
        vision_range=5,
        can_capture=True,
        deployment_cost=160,
        historical_notes="Heavy machine gun team with M1919A4 (.30 cal), excellent suppression",
    )

    units["us_machine_gun_team_m34"] = CC2UnitTemplate(  # M1919 (M34)
        template_id="us_machine_gun_team_m34",
        display_name="US MG Team (M1919)",
        faction=Faction.AMERICAN,
        role=InfantryRole.MACHINE_GUN,
        squad_size=5,
        weapon_primary_id="us_m1919",  # *** THE M34 LIGHT MG ***
        weapon_secondary_id="us_m1_carbine",
        experience_level=0,
        morale_initial=78.0,
        stealth_rating=0.27,
        vision_range=5,
        deployment_cost=130,
        historical_notes="Lighter machine gun team with M1919 variant, more mobile but less firepower",
    )

    units["us_scout_team"] = CC2UnitTemplate(
        template_id="us_scout_team",
        display_name="US Scout Team",
        faction=Faction.AMERICAN,
        role=InfantryRole.SCOUT,
        squad_size=4,
        weapon_primary_id="us_m1_carbine",
        weapon_secondary_id="us_thompson",
        experience_level=2,
        morale_initial=83.0,
        stealth_rating=0.50,  # Better than regular infantry
        vision_range=9,  # Extended vision
        deployment_cost=110,
        historical_notes="Reconnaissance specialists, small fast teams",
    )

    units["us_sniper_team"] = CC2UnitTemplate(
        template_id="us_sniper_team",
        display_name="US Sniper Team",
        faction=Faction.AMERICAN,
        role=InfantryRole.SNIPER,
        squad_size=2,
        weapon_primary_id="us_m1903_springfield",
        experience_level=3,
        morale_initial=80.0,
        stealth_rating=0.65,
        vision_range=12,
        can_capture=False,  # Snipers don't capture objectives
        deployment_cost=140,
        historical_notes="Designated marksmen with scoped Springfields",
    )

    units["us_at_team"] = CC2UnitTemplate(
        template_id="us_at_team",
        display_name="US AT Team (Bazooka)",
        faction=Faction.AMERICAN,
        role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id="us_bazooka",
        weapon_secondary_id="us_m1_carbine",
        experience_level=1,
        morale_initial=78.0,
        stealth_rating=0.35,
        vision_range=6,
        can_capture=True,
        has_demolitions=True,
        deployment_cost=150,
        historical_notes="Anti-tank specialists with M1A1 Bazooka",
    )

    units["us_engineer_team"] = CC2UnitTemplate(
        template_id="us_engineer_team",
        display_name="US Engineer Squad",
        faction=Faction.AMERICAN,
        role=InfantryRole.ENGINEER,
        squad_size=8,
        weapon_primary_id="us_m1_carbine",
        weapon_secondary_id="us_thompson",
        experience_level=1,
        morale_initial=81.0,
        stealth_rating=0.38,
        vision_range=6,
        can_capture=True,
        has_demolitions=True,
        deployment_cost=140,
        historical_notes="Combat engineers, can build fortifications and demolish obstacles",
    )

    units["us_engineer_squad"] = CC2UnitTemplate(
        template_id="us_engineer_squad",
        display_name="Engineer Squad",
        faction=Faction.AMERICAN,
        role=InfantryRole.ENGINEER,
        squad_size=8,
        weapon_primary_id="us_m1_garand",
        weapon_secondary_id="us_m1_carbine",
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.36,
        vision_range=6,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        has_demolitions=True,
        deployment_cost=170,
        max_per_battle=1,
        historical_notes="US combat engineers with Garands, demolition and fortification specialists",
    )

    units["us_flamethrower_team"] = CC2UnitTemplate(
        template_id="us_flamethrower_team",
        display_name="US Flamethrower Team",
        faction=Faction.AMERICAN,
        role=InfantryRole.FLAMETHROWER,
        squad_size=3,
        weapon_primary_id="us_flamethrower_m2",
        weapon_secondary_id="us_m1_carbine",
        experience_level=1,
        morale_initial=75.0,  # Low morale (dangerous job!)
        stealth_rating=0.40,
        vision_range=5,
        can_capture=True,
        deployment_cost=170,
        historical_notes="Flame specialists, devastating in close quarters, high casualty risk",
    )

    units["us_officer"] = CC2UnitTemplate(
        template_id="us_officer",
        display_name="US Officer / Commander",
        faction=Faction.AMERICAN,
        role=InfantryRole.OFFICER,
        squad_size=3,
        weapon_primary_id="us_m1_carbine",
        weapon_secondary_id="us_thompson",
        experience_level=2,
        morale_initial=95.0,  # High morale (leadership)
        stealth_rating=0.35,
        vision_range=7,
        is_command_unit=True,  # Boosts nearby unit morale!
        can_capture=False,
        deployment_cost=180,
        historical_notes="Platoon/Battalion commander, provides morale bonus to adjacent units",
    )

    units["us_heavy_assault"] = CC2UnitTemplate(
        template_id="us_heavy_assault",
        display_name="US Assault Squad",
        faction=Faction.AMERICAN,
        role=InfantryRole.HEAVY_ASSAULT,
        squad_size=9,
        weapon_primary_id="us_thompson",
        weapon_secondary_id="us_m3_grease_gun",
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.32,
        vision_range=6,
        deployment_cost=145,
        historical_notes="Close-quarters assault troops, heavily armed with SMGs",
    )

    # --- SUPPORT CATEGORY ---

    units["us_mortar_light_team"] = CC2UnitTemplate(
        template_id="us_mortar_light_team",
        display_name="US Light Mortar Team (60mm)",
        faction=Faction.AMERICAN,
        role=InfantryRole.RIFLE,  # Support category
        squad_size=4,
        weapon_primary_id="us_m2_60mm",  # *** LIGHT MORTAR ***
        weapon_secondary_id="us_m1_carbine",
        experience_level=1,
        morale_initial=79.0,
        stealth_rating=0.33,
        vision_range=6,
        can_capture=False,
        deployment_cost=140,
        historical_notes="Company-level 60mm mortar team, indirect fire support",
    )

    units["us_mortar_heavy_team"] = CC2UnitTemplate(
        template_id="us_mortar_heavy_team",
        display_name="US Heavy Mortar Team (81mm)",
        faction=Faction.AMERICAN,
        role=InfantryRole.RIFLE,
        squad_size=5,
        weapon_primary_id="us_m1_81mm",  # *** HEAVY MORTAR ***
        weapon_secondary_id="us_m1_carbine",
        experience_level=1,
        morale_initial=78.0,
        stealth_rating=0.30,
        vision_range=5,
        can_capture=False,
        deployment_cost=175,
        historical_notes="Battalion-level 81mm mortar, heavy indirect fire",
    )

    # --- VEHICLES ---

    units["us_sherman_m4"] = CC2UnitTemplate(
        template_id="us_sherman_m4",
        display_name="M4 Sherman (75mm)",
        faction=Faction.AMERICAN,
        role=VehicleType.TANK_MEDIUM,
        squad_size=1,  # Crew count
        weapon_primary_id="m3_75mm_m4",
        weapon_secondary_id="coax_30cal",
        vehicle_armor=64,  # ~64mm effective vs AP
        vehicle_speed=40,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=85.0,
        stealth_rating=0.15,  # Tanks are loud!
        vision_range=7,
        can_deploy_in_building=False,
        can_capture=True,
        deployment_cost=350,
        historical_notes="Main US medium tank, reliable but undergunned vs late German armor",
    )

    units["us_stuart_m5"] = CC2UnitTemplate(
        template_id="us_stuart_m5",
        display_name="M5 Stuart (37mm)",
        faction=Faction.AMERICAN,
        role=VehicleType.TANK_LIGHT,
        squad_size=1,
        weapon_primary_id="m3_37mm",
        weapon_secondary_id="coax_30cal",
        vehicle_armor=51,
        vehicle_speed=58,
        vehicle_crew=4,
        experience_level=0,
        morale_initial=78.0,
        stealth_rating=0.22,
        vision_range=8,
        can_deploy_in_building=False,
        deployment_cost=220,
        historical_notes="Light tank, fast but weak armor/gun, used for recon",
    )

    units["us_halftrack_m3"] = CC2UnitTemplate(
        template_id="us_halftrack_m3",
        display_name="M3 Halftrack",
        faction=Faction.AMERICAN,
        role=VehicleType.HALFTRACK,
        squad_size=1,
        weapon_primary_id="coax_30cal",  # .30 cal mounted
        vehicle_armor=13,  # Thin armor
        vehicle_speed=72,
        vehicle_crew=3,
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.18,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=180,
        historical_notes="Armored personnel carrier, transports infantry",
    )

    units["us_wolverine_m10"] = CC2UnitTemplate(
        template_id="us_wolverine_m10",
        display_name="M10 Wolverine Tank Destroyer",
        faction=Faction.AMERICAN,
        role=VehicleType.TANK_DESTROYER,
        squad_size=1,
        weapon_primary_id="m3_75mm_m4",  # Same 75mm as Sherman but open-topped
        vehicle_armor=51,
        vehicle_speed=48,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=80.0,
        stealth_rating=0.16,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=320,
        historical_notes="Open-topped TD, good gun but vulnerable to infantry/heavy fire",
    )
    # --- US EXPANDED UNITS ---

    units["us_ranger_squad"] = CC2UnitTemplate(
        template_id="us_ranger_squad",
        display_name="US Ranger Squad",
        faction=Faction.AMERICAN,
        role=InfantryRole.HEAVY_ASSAULT,
        squad_size=12,
        weapon_primary_id="us_m1_garand",
        weapon_secondary_id="us_browning_bar",
        experience_level=2,
        morale_initial=88.0,
        stealth_rating=0.30,
        vision_range=6,
        deployment_cost=130,
        max_per_battle=2,
        historical_notes="Elite US Ranger squad, Garands and BAR, heavy assault specialists",
    )

    units["us_mortar_squad"] = CC2UnitTemplate(
        template_id="us_mortar_squad",
        display_name="US 60mm Mortar Squad",
        faction=Faction.AMERICAN,
        role=InfantryRole.MORTAR,
        squad_size=5,
        weapon_primary_id="us_60mm_mortar",
        weapon_secondary_id="us_m1_carbine",
        experience_level=1,
        morale_initial=79.0,
        stealth_rating=0.30,
        vision_range=5,
        can_capture=False,
        deployment_cost=180,
        max_per_battle=2,
        historical_notes="US 60mm mortar squad, company-level indirect fire support",
    )

    units["us_at_squad_bazooka"] = CC2UnitTemplate(
        template_id="us_at_squad_bazooka",
        display_name="US Bazooka Team",
        faction=Faction.AMERICAN,
        role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id="us_bazooka",
        weapon_secondary_id="us_m1_carbine",
        experience_level=1,
        morale_initial=78.0,
        stealth_rating=0.35,
        vision_range=6,
        has_demolitions=True,
        deployment_cost=190,
        max_per_battle=2,
        historical_notes="US bazooka anti-tank team, M1A1 Bazooka vs enemy armor",
    )

    units["us_mg_squad"] = CC2UnitTemplate(
        template_id="us_mg_squad",
        display_name="US .30cal MG Squad",
        faction=Faction.AMERICAN,
        role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id="us_browning_30cal",
        weapon_secondary_id="us_m1_carbine",
        experience_level=1,
        morale_initial=80.0,
        stealth_rating=0.25,
        vision_range=5,
        deployment_cost=150,
        max_per_battle=2,
        historical_notes="US .30 cal machine gun squad, excellent suppression capability",
    )
    units["us_m1_57mm_at_gun"] = CC2UnitTemplate(
        template_id="us_m1_57mm_at_gun",
        display_name="M1 57mm AT Gun",
        faction=Faction.AMERICAN,
        role=InfantryRole.ANTI_TANK,
        squad_size=4,
        weapon_primary_id="us_m1_57mm",
        weapon_secondary_id=None,
        can_deploy_in_building=False,
        can_deploy_in_open=True,
        deployment_cost=240,
        max_per_battle=2,
    )
    # --- US ARMOR EXPANDED ---

    units["us_m3_halftrack"] = CC2UnitTemplate(
        template_id="us_m3_halftrack",
        display_name="M3 Half-track",
        faction=Faction.AMERICAN,
        role=VehicleType.HALFTRACK,
        squad_size=2,
        weapon_primary_id="us_m2hb_50cal",
        weapon_secondary_id=None,
        vehicle_armor=13,
        vehicle_speed=72,
        vehicle_crew=2,
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.18,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=160,
        max_per_battle=2,
        historical_notes="M3 half-track with .50 cal HMG, infantry transport and fire support",
    )

    units["us_sherman_76"] = CC2UnitTemplate(
        template_id="us_sherman_76",
        display_name="Sherman 76mm",
        faction=Faction.AMERICAN,
        role=VehicleType.TANK_MEDIUM,
        squad_size=5,
        weapon_primary_id="us_76mm_sherman",
        weapon_secondary_id="coax_30cal",
        vehicle_armor=64,
        vehicle_speed=40,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.14,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=350,
        max_per_battle=1,
        historical_notes="Sherman with 76mm gun, improved anti-tank performance over 75mm",
    )
    return units
