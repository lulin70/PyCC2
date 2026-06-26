"""CC2 authentic unit factory — faction-specific entries."""

from __future__ import annotations

from pycc2.domain.systems.cc2_authentic_weapons import (
    Faction,
    InfantryRole,
)
from pycc2.domain.systems.unit_templates import CC2UnitTemplate


def _build_polish_units() -> dict[str, CC2UnitTemplate]:
    units: dict[str, CC2UnitTemplate] = {}
    # POLISH FORCES (1st Independent Parachute Brigade)
    # ================================================================

    units["pl_para_rifle_squad"] = CC2UnitTemplate(
        template_id="pl_para_rifle_squad",
        display_name="Polish Para Rifle Squad",
        faction=Faction.POLISH,
        role=InfantryRole.RIFLE,
        squad_size=10,
        weapon_primary_id="pl_enfield_no4",
        weapon_secondary_id="uk_mills_bomb",
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.30,
        vision_range=6,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        deployment_cost=100,
        max_per_battle=4,
        historical_notes="Polish Para Brigade rifle squad, British-equipped, 10 men",
    )

    units["pl_para_mg_squad"] = CC2UnitTemplate(
        template_id="pl_para_mg_squad",
        display_name="Polish Para MG Squad",
        faction=Faction.POLISH,
        role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id="pl_bren_mk2",
        weapon_secondary_id=None,
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.26,
        vision_range=5,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        deployment_cost=150,
        max_per_battle=2,
        historical_notes="Polish Para BREN gun team, British-issue BREN Mk.II",
    )

    units["pl_para_at_squad"] = CC2UnitTemplate(
        template_id="pl_para_at_squad",
        display_name="Polish Para AT Squad",
        faction=Faction.POLISH,
        role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id="pl_piat",
        weapon_secondary_id=None,
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.34,
        vision_range=6,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        deployment_cost=200,
        max_per_battle=2,
        historical_notes="Polish Para PIAT anti-tank team",
    )

    units["pl_para_engineer_squad"] = CC2UnitTemplate(
        template_id="pl_para_engineer_squad",
        display_name="Polish Para Engineer Squad",
        faction=Faction.POLISH,
        role=InfantryRole.ENGINEER,
        squad_size=8,
        weapon_primary_id="pl_enfield_no4",
        weapon_secondary_id="uk_mills_bomb",
        experience_level=1,
        morale_initial=81.0,
        stealth_rating=0.38,
        vision_range=6,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        has_demolitions=True,
        deployment_cost=180,
        max_per_battle=1,
        historical_notes="Polish Para combat engineers, demolitions and fortifications",
    )
    # --- POLISH EXPANDED UNITS ---

    units["pl_para_mortar_squad"] = CC2UnitTemplate(
        template_id="pl_para_mortar_squad",
        display_name="Polish Para Mortar Squad",
        faction=Faction.POLISH,
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
        max_per_battle=1,
        historical_notes="Polish Para mortar squad with British 3-inch mortar",
    )

    units["pl_para_officer"] = CC2UnitTemplate(
        template_id="pl_para_officer",
        display_name="Polish Para Officer",
        faction=Faction.POLISH,
        role=InfantryRole.OFFICER,
        squad_size=3,
        weapon_primary_id="uk_officer_sten",
        weapon_secondary_id="pl_enfield_no4",
        experience_level=2,
        morale_initial=90.0,
        stealth_rating=0.35,
        vision_range=7,
        is_command_unit=True,
        can_capture=False,
        deployment_cost=150,
        max_per_battle=1,
        historical_notes="Polish Para officer with STEN Mk.V, provides morale bonus",
    )
    return units
