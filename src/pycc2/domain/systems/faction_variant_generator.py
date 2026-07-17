"""STATUS: ORPHAN — pending v0.8.0+ integration (TD-077). Faction-specific variant generator — Commando/PIAT/Ranger/Fallschirmjäger etc (P5-1 batch 1).

Extracted from unit_diversity_expansion.py. Generates faction-specific variants
(Commando, PIAT team, Recce troop, Ranger, Bazooka team, Glider infantry,
Fallschirmjäger, Panzergrenadier, Volksgrenadier, Polish Para Brigade).
"""

from __future__ import annotations

import logging

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.cc2_authentic_units import CC2UnitTemplate
from pycc2.domain.systems.cc2_authentic_weapons import InfantryRole

logger = logging.getLogger(__name__)


class FactionVariantGenerator:
    """Generate faction-specific unit templates (special forces / elite units)."""

    def generate(self) -> list[CC2UnitTemplate]:
        """Create faction-specific unique units."""
        variants: list[CC2UnitTemplate] = []

        # --- British ---
        # Commando squad (elite infantry)
        variants.append(
            CC2UnitTemplate(
                template_id="uk_commando_squad",
                display_name="British Commando Squad",
                faction=Faction.BRITISH,
                role=InfantryRole.HEAVY_ASSAULT,
                squad_size=10,
                weapon_primary_id="uk_sten",
                weapon_secondary_id="uk_lee_enfield",
                experience_level=3,
                morale_initial=95.0,
                stealth_rating=0.45,
                vision_range=7,
                can_capture=True,
                deployment_cost=250,
                max_per_battle=1,
                historical_notes="Elite Commando squad, specialized in raids and close assault",
            )
        )

        # PIAT team (dedicated AT) — already exists as uk_piat_team, add elite variant
        variants.append(
            CC2UnitTemplate(
                template_id="uk_piat_team_veteran",
                display_name="PIAT Team (Veteran)",
                faction=Faction.BRITISH,
                role=InfantryRole.ANTI_TANK,
                squad_size=3,
                weapon_primary_id="uk_piat",
                weapon_secondary_id="uk_sten",
                experience_level=2,
                morale_initial=84.0,
                stealth_rating=0.38,
                vision_range=7,
                has_demolitions=True,
                deployment_cost=180,
                max_per_battle=1,
                historical_notes="Veteran PIAT team, experienced in ambush tactics vs armor",
            )
        )

        # Recce troop (fast scout)
        variants.append(
            CC2UnitTemplate(
                template_id="uk_recce_troop",
                display_name="Recce Troop",
                faction=Faction.BRITISH,
                role=InfantryRole.SCOUT,
                squad_size=4,
                weapon_primary_id="uk_lee_enfield",
                weapon_secondary_id="uk_sten",
                experience_level=2,
                morale_initial=85.0,
                stealth_rating=0.55,
                vision_range=10,
                can_capture=False,
                deployment_cost=130,
                max_per_battle=1,
                historical_notes="Reconnaissance troop, fast stealthy scouts with extended vision",
            )
        )

        # --- American ---
        # Ranger squad (elite infantry) — already exists as us_ranger_squad, add elite variant
        variants.append(
            CC2UnitTemplate(
                template_id="us_ranger_squad_elite",
                display_name="US Ranger Squad (Elite)",
                faction=Faction.AMERICAN,
                role=InfantryRole.HEAVY_ASSAULT,
                squad_size=12,
                weapon_primary_id="us_m1_garand",
                weapon_secondary_id="us_browning_bar",
                experience_level=3,
                morale_initial=95.0,
                stealth_rating=0.35,
                vision_range=7,
                can_capture=True,
                deployment_cost=300,
                max_per_battle=1,
                historical_notes="Elite Ranger squad, veterans of Pointe du Hoc and beyond",
            )
        )

        # Bazooka team — already exists as us_at_team, add veteran variant
        variants.append(
            CC2UnitTemplate(
                template_id="us_bazooka_team_veteran",
                display_name="US Bazooka Team (Veteran)",
                faction=Faction.AMERICAN,
                role=InfantryRole.ANTI_TANK,
                squad_size=3,
                weapon_primary_id="us_bazooka",
                weapon_secondary_id="us_m1_carbine",
                experience_level=2,
                morale_initial=84.0,
                stealth_rating=0.38,
                vision_range=7,
                has_demolitions=True,
                deployment_cost=190,
                max_per_battle=1,
                historical_notes="Veteran bazooka team, experienced tank hunters",
            )
        )

        # Glider infantry (heavy weapons)
        variants.append(
            CC2UnitTemplate(
                template_id="us_glider_infantry",
                display_name="US Glider Infantry (Heavy Weapons)",
                faction=Faction.AMERICAN,
                role=InfantryRole.MACHINE_GUN,
                squad_size=8,
                weapon_primary_id="us_m1919a4",
                weapon_secondary_id="us_m1_garand",
                experience_level=1,
                morale_initial=82.0,
                stealth_rating=0.28,
                vision_range=6,
                can_capture=True,
                has_demolitions=False,
                deployment_cost=200,
                max_per_battle=1,
                historical_notes="Gider-borne heavy weapons squad, M1919A4 + Garands",
            )
        )

        # US Medic Team
        variants.append(
            CC2UnitTemplate(
                template_id="us_medic_team",
                display_name="US Medic Team",
                faction=Faction.AMERICAN,
                role=InfantryRole.OFFICER,  # Support role
                squad_size=3,
                weapon_primary_id="us_m1_carbine",
                weapon_secondary_id=None,
                experience_level=1,
                morale_initial=90.0,
                stealth_rating=0.30,
                vision_range=5,
                can_capture=False,
                deployment_cost=120,
                max_per_battle=1,
                historical_notes="Medical team, can treat wounded units, non-combat priority",
            )
        )

        # --- German ---
        # Fallschirmjäger (elite paratroop) — already exists as de_fallschirmjager, add elite variant
        variants.append(
            CC2UnitTemplate(
                template_id="de_fallschirmjager_elite",
                display_name="Fallschirmjäger (Elite)",
                faction=Faction.GERMAN,
                role=InfantryRole.RIFLE,
                squad_size=10,
                weapon_primary_id="de_fg42",
                weapon_secondary_id="de_mp40",
                experience_level=3,
                morale_initial=95.0,
                stealth_rating=0.38,
                vision_range=7,
                can_capture=True,
                deployment_cost=220,
                max_per_battle=1,
                historical_notes="Elite Fallschirmjäger, Crete veterans with FG42 automatic rifles",
            )
        )

        # Panzergrenadier (mechanized infantry)
        variants.append(
            CC2UnitTemplate(
                template_id="de_panzergrenadier_squad",
                display_name="Panzergrenadier Squad",
                faction=Faction.GERMAN,
                role=InfantryRole.HEAVY_ASSAULT,
                squad_size=11,
                weapon_primary_id="de_kar98k",
                weapon_secondary_id="de_mg42",
                experience_level=2,
                morale_initial=88.0,
                stealth_rating=0.28,
                vision_range=6,
                can_capture=True,
                deployment_cost=180,
                max_per_battle=2,
                historical_notes="Mechanized infantry with half-track support, MG42 firepower",
            )
        )

        # Volksgrenadier (conscript)
        variants.append(
            CC2UnitTemplate(
                template_id="de_volksgrenadier_squad",
                display_name="Volksgrenadier Squad",
                faction=Faction.GERMAN,
                role=InfantryRole.RIFLE,
                squad_size=9,
                weapon_primary_id="de_kar98k",
                weapon_secondary_id=None,
                experience_level=0,
                morale_initial=55.0,
                stealth_rating=0.30,
                vision_range=5,
                can_capture=True,
                deployment_cost=60,
                max_per_battle=4,
                historical_notes="Late-war conscript infantry, poorly trained and equipped",
            )
        )

        # Volksgrenadier AT team (Panzerfaust-heavy)
        variants.append(
            CC2UnitTemplate(
                template_id="de_volksgrenadier_at",
                display_name="Volksgrenadier AT Team",
                faction=Faction.GERMAN,
                role=InfantryRole.ANTI_TANK,
                squad_size=4,
                weapon_primary_id="de_panzerfaust",
                weapon_secondary_id="de_kar98k",
                experience_level=0,
                morale_initial=50.0,
                stealth_rating=0.32,
                vision_range=5,
                has_demolitions=False,
                deployment_cost=80,
                max_per_battle=3,
                historical_notes="Volksgrenadier AT team, cheap but low morale and accuracy",
            )
        )

        # German Medic Team
        variants.append(
            CC2UnitTemplate(
                template_id="de_medic_team",
                display_name="German Sanitäter Team",
                faction=Faction.GERMAN,
                role=InfantryRole.OFFICER,
                squad_size=3,
                weapon_primary_id="de_kar98k",
                weapon_secondary_id=None,
                experience_level=1,
                morale_initial=88.0,
                stealth_rating=0.30,
                vision_range=5,
                can_capture=False,
                deployment_cost=120,
                max_per_battle=1,
                historical_notes="German medical team, can treat wounded under ceasefire",
            )
        )

        # --- Polish ---
        # Polish Para Brigade (special units for Arnhem)
        variants.append(
            CC2UnitTemplate(
                template_id="pl_para_commando",
                display_name="Polish Para Commando Squad",
                faction=Faction.POLISH,
                role=InfantryRole.HEAVY_ASSAULT,
                squad_size=8,
                weapon_primary_id="uk_sten",
                weapon_secondary_id="pl_enfield_no4",
                experience_level=2,
                morale_initial=90.0,
                stealth_rating=0.42,
                vision_range=7,
                can_capture=True,
                deployment_cost=220,
                max_per_battle=1,
                historical_notes="Elite Polish Para commando squad, volunteers for Driel crossing",
            )
        )

        # Polish Para Scout Team
        variants.append(
            CC2UnitTemplate(
                template_id="pl_para_scout",
                display_name="Polish Para Scout Team",
                faction=Faction.POLISH,
                role=InfantryRole.SCOUT,
                squad_size=4,
                weapon_primary_id="pl_enfield_no4",
                weapon_secondary_id="uk_sten",
                experience_level=2,
                morale_initial=85.0,
                stealth_rating=0.52,
                vision_range=9,
                can_capture=False,
                deployment_cost=130,
                max_per_battle=1,
                historical_notes="Polish Para reconnaissance team, fast scouts with good stealth",
            )
        )

        # Polish Para Sniper Team
        variants.append(
            CC2UnitTemplate(
                template_id="pl_para_sniper",
                display_name="Polish Para Sniper Team",
                faction=Faction.POLISH,
                role=InfantryRole.SNIPER,
                squad_size=2,
                weapon_primary_id="uk_sniper_no4",
                experience_level=3,
                morale_initial=82.0,
                stealth_rating=0.65,
                vision_range=12,
                can_capture=False,
                deployment_cost=180,
                max_per_battle=1,
                historical_notes="Polish Para sniper team with scoped Lee-Enfield No.4(T)",
            )
        )

        # Polish Para Heavy Weapons Team
        variants.append(
            CC2UnitTemplate(
                template_id="pl_para_heavy_weapons",
                display_name="Polish Para Heavy Weapons Team",
                faction=Faction.POLISH,
                role=InfantryRole.MACHINE_GUN,
                squad_size=5,
                weapon_primary_id="pl_bren_mk2",
                weapon_secondary_id="uk_mills_bomb",
                experience_level=1,
                morale_initial=80.0,
                stealth_rating=0.26,
                vision_range=5,
                can_capture=False,
                deployment_cost=170,
                max_per_battle=1,
                historical_notes="Polish Para heavy weapons team with BREN and grenades",
            )
        )

        return variants
