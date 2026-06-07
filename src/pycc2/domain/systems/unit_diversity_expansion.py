"""
Unit Diversity Expansion — CC2-Authentic Unit Roster Expansion

Expands unit templates from 53+ to 100+ to close the gap with CC2's 130+.

Three expansion strategies:
  1. Vehicle variants — Sherman M4A1/Firefly/DD, Panzer IV Ausf J/III Ausf M,
     SdKfz 251/1/16/9, M10/M36/JagdPz IV/StuG III Ausf G
  2. Experience-level variants — CONSCRIPT/REGULAR/VETERAN/ELITE for each
     base template, with stat modifiers
  3. Faction-specific variants — Commando, PIAT team, Recce troop, Ranger,
     Bazooka team, Glider infantry, Fallschirmjäger, Panzergrenadier,
     Volksgrenadier, Polish Para Brigade special units

Experience level effects (matching game_settings.py ExperienceLevel):
  CONSCRIPT: -20% accuracy, -10% speed, +20% panic chance
  REGULAR:   base stats
  VETERAN:   +15% accuracy, +10% speed, -15% panic chance
  ELITE:     +25% accuracy, +15% speed, -25% panic chance, +1 action/turn
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

from pycc2.domain.systems.cc2_authentic_units import CC2UnitTemplate, get_cc2_units
from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.cc2_authentic_weapons import InfantryRole, VehicleType
from pycc2.domain.systems.game_settings import ExperienceLevel

logger = logging.getLogger(__name__)

# ========================================================================
# Experience-level stat modifiers
# ========================================================================

EXPERIENCE_MODIFIERS: dict[ExperienceLevel, dict[str, Any]] = {
    ExperienceLevel.CONSCRIPT: {
        'accuracy_modifier': 0.80,       # -20% accuracy
        'speed_modifier': 0.90,          # -10% speed
        'panic_modifier': 1.20,          # +20% panic chance
        'morale_modifier': 0.80,         # Lower starting morale
        'stealth_modifier': 0.90,        # Slightly worse stealth
        'vision_modifier': -1,           # -1 vision range
        'extra_actions': 0,
        'exp_level_int': 0,
        'suffix': '(Conscript)',
        'cost_modifier': 0.70,           # Cheaper to deploy
    },
    ExperienceLevel.REGULAR: {
        'accuracy_modifier': 1.0,
        'speed_modifier': 1.0,
        'panic_modifier': 1.0,
        'morale_modifier': 1.0,
        'stealth_modifier': 1.0,
        'vision_modifier': 0,
        'extra_actions': 0,
        'exp_level_int': 1,
        'suffix': '',
        'cost_modifier': 1.0,
    },
    ExperienceLevel.VETERAN: {
        'accuracy_modifier': 1.15,       # +15% accuracy
        'speed_modifier': 1.10,          # +10% speed
        'panic_modifier': 0.85,          # -15% panic chance
        'morale_modifier': 1.10,         # Higher starting morale
        'stealth_modifier': 1.05,        # Slightly better stealth
        'vision_modifier': 1,            # +1 vision range
        'extra_actions': 0,
        'exp_level_int': 2,
        'suffix': '(Veteran)',
        'cost_modifier': 1.30,
    },
    ExperienceLevel.ELITE: {
        'accuracy_modifier': 1.25,       # +25% accuracy
        'speed_modifier': 1.15,          # +15% speed
        'panic_modifier': 0.75,          # -25% panic chance
        'morale_modifier': 1.20,         # Much higher starting morale
        'stealth_modifier': 1.10,        # Better stealth
        'vision_modifier': 1,            # +1 vision range
        'extra_actions': 1,              # +1 action per turn
        'exp_level_int': 3,
        'suffix': '(Elite)',
        'cost_modifier': 1.60,
    },
}


# ========================================================================
# UnitDiversityGenerator
# ========================================================================

class UnitDiversityGenerator:
    """Generate unit variants to expand the roster to 100+ templates.

    Usage::

        gen = UnitDiversityGenerator()
        all_units = gen.generate_variants(base_templates)
        print(f"Total: {gen.count_total_units()}")
    """

    def __init__(self) -> None:
        self._generated: dict[str, CC2UnitTemplate] = {}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate_variants(self, base_templates: list[CC2UnitTemplate]) -> list[CC2UnitTemplate]:
        """Expand base templates with vehicle, experience, and faction variants.

        Returns the complete list of all generated unit templates.
        """
        self._generated.clear()

        # Step 1: Add all base templates
        for t in base_templates:
            self._generated[t.template_id] = t

        # Step 2: Generate vehicle variants
        vehicle_variants = self.generate_vehicle_variants()
        for v in vehicle_variants:
            self._generated[v.template_id] = v

        # Step 3: Generate experience-level variants for infantry
        for t in list(base_templates):
            if isinstance(t.role, InfantryRole):
                exp_variants = self.generate_experience_variants(
                    t,
                    [ExperienceLevel.CONSCRIPT, ExperienceLevel.VETERAN, ExperienceLevel.ELITE],
                )
                for v in exp_variants:
                    self._generated[v.template_id] = v

        # Step 4: Generate faction-specific variants
        faction_variants = self.generate_faction_variants()
        for v in faction_variants:
            self._generated[v.template_id] = v

        return list(self._generated.values())

    # ------------------------------------------------------------------
    # Vehicle variants
    # ------------------------------------------------------------------

    def generate_vehicle_variants(self) -> list[CC2UnitTemplate]:
        """Create vehicle variants (Sherman, Panzer, Half-track, TD families)."""
        variants: list[CC2UnitTemplate] = []

        # --- Sherman variants ---
        # Sherman M4A1 (basic) — already exists as us_sherman_m4

        # Sherman Firefly (17pdr AT) — already exists as uk_firefly

        # Sherman DD (amphibious, slower) — already exists as uk_sherman_dd

        # Sherman M4A3E8 "Easy Eight" (improved 76mm)
        variants.append(CC2UnitTemplate(
            template_id='us_sherman_easy_eight',
            display_name='M4A3E8 Sherman "Easy Eight"',
            faction=Faction.AMERICAN, role=VehicleType.TANK_MEDIUM,
            squad_size=1,
            weapon_primary_id='us_76mm_sherman',
            weapon_secondary_id='coax_30cal',
            vehicle_armor=76,
            vehicle_speed=42,
            vehicle_crew=5,
            experience_level=2,
            morale_initial=88.0,
            stealth_rating=0.14,
            vision_range=7,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=420,
            historical_notes='Improved Sherman with 76mm HVSS suspension, best US tank of the war',
        ))

        # Sherman M4A3 75mm (Wet Stowage)
        variants.append(CC2UnitTemplate(
            template_id='us_sherman_m4a3_75',
            display_name='M4A3 Sherman (75mm Wet)',
            faction=Faction.AMERICAN, role=VehicleType.TANK_MEDIUM,
            squad_size=1,
            weapon_primary_id='m3_75mm_m4',
            weapon_secondary_id='coax_30cal',
            vehicle_armor=64,
            vehicle_speed=42,
            vehicle_crew=5,
            experience_level=1,
            morale_initial=85.0,
            stealth_rating=0.15,
            vision_range=7,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=360,
            historical_notes='M4A3 with wet ammo stowage, reduced fire risk',
        ))

        # Sherman Calliope (rocket launcher)
        variants.append(CC2UnitTemplate(
            template_id='us_sherman_calliope',
            display_name='Sherman Calliope (T34 Rocket)',
            faction=Faction.AMERICAN, role=VehicleType.SP_ARTILLERY,
            squad_size=1,
            weapon_primary_id='m3_75mm_m4',
            weapon_secondary_id='coax_30cal',
            vehicle_armor=64,
            vehicle_speed=36,
            vehicle_crew=5,
            experience_level=1,
            morale_initial=82.0,
            stealth_rating=0.10,
            vision_range=7,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=400,
            max_per_battle=1,
            historical_notes='Sherman with T34 rocket launcher, devastating barrage capability',
        ))

        # --- Panzer variants ---
        # PzKpfw IV Ausf J (late war, no turret traverse motor)
        variants.append(CC2UnitTemplate(
            template_id='de_panzer_iv_ausf_j',
            display_name='PzKpfw IV Ausf J',
            faction=Faction.GERMAN, role=VehicleType.TANK_MEDIUM,
            squad_size=1,
            weapon_primary_id='kwk40_75mm',
            weapon_secondary_id='coax_mg34',
            vehicle_armor=80,
            vehicle_speed=32,  # Slower — no turret traverse motor, manual only
            vehicle_crew=4,    # Reduced crew
            experience_level=0,  # Late war conscript crews
            morale_initial=78.0,
            stealth_rating=0.14,
            vision_range=6,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=280,
            historical_notes='Late-war PzIV with manual turret traverse, reduced crew quality',
        ))

        # PzKpfw III Ausf M (older, weaker)
        variants.append(CC2UnitTemplate(
            template_id='de_panzer_iii_ausf_m',
            display_name='PzKpfw III Ausf M',
            faction=Faction.GERMAN, role=VehicleType.TANK_LIGHT,
            squad_size=1,
            weapon_primary_id='de_mg34_vehicle',  # 50mm KwK 39 L/60
            weapon_secondary_id='coax_mg34',
            vehicle_armor=57,
            vehicle_speed=40,
            vehicle_crew=5,
            experience_level=0,
            morale_initial=75.0,
            stealth_rating=0.18,
            vision_range=7,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=200,
            historical_notes='Obsolete Panzer III, relegated to recon and support roles',
        ))

        # --- Half-track variants ---
        # SdKfz 251/1 (transport) — already exists as de_sdkfz_251

        # SdKfz 251/16 (flamethrower)
        variants.append(CC2UnitTemplate(
            template_id='de_sdkfz_251_16',
            display_name='SdKfz 251/16 Flammpanzerwagen',
            faction=Faction.GERMAN, role=VehicleType.FLAME_TANK,
            squad_size=1,
            weapon_primary_id='de_flammenwerfer',
            weapon_secondary_id='coax_mg34',
            vehicle_armor=14,
            vehicle_speed=48,
            vehicle_crew=3,
            experience_level=1,
            morale_initial=78.0,
            stealth_rating=0.15,
            vision_range=5,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=240,
            max_per_battle=1,
            historical_notes='Half-track flamethrower variant, devastating vs infantry in cover',
        ))

        # SdKfz 251/9 (75mm gun — "Stummel")
        variants.append(CC2UnitTemplate(
            template_id='de_sdkfz_251_9',
            display_name='SdKfz 251/9 "Stummel"',
            faction=Faction.GERMAN, role=VehicleType.TANK_DESTROYER,
            squad_size=1,
            weapon_primary_id='kwk40_75mm',  # 7.5cm KwK 37 L/24
            weapon_secondary_id='coax_mg34',
            vehicle_armor=14,
            vehicle_speed=48,
            vehicle_crew=4,
            experience_level=1,
            morale_initial=80.0,
            stealth_rating=0.16,
            vision_range=6,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=260,
            max_per_battle=1,
            historical_notes='Half-track with short 75mm gun, infantry fire support',
        ))

        # M3 Half-track with 75mm GMC
        variants.append(CC2UnitTemplate(
            template_id='us_m3_halftrack_75',
            display_name='M3 Half-track (75mm GMC)',
            faction=Faction.AMERICAN, role=VehicleType.TANK_DESTROYER,
            squad_size=1,
            weapon_primary_id='m3_75mm_m4',
            weapon_secondary_id='coax_30cal',
            vehicle_armor=13,
            vehicle_speed=64,
            vehicle_crew=4,
            experience_level=1,
            morale_initial=80.0,
            stealth_rating=0.16,
            vision_range=6,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=250,
            max_per_battle=1,
            historical_notes='M3 half-track with mounted 75mm gun, mobile fire support',
        ))

        # --- TD variants ---
        # M10 Wolverine — already exists as us_wolverine_m10

        # M36 Jackson
        variants.append(CC2UnitTemplate(
            template_id='us_m36_jackson',
            display_name='M36 Jackson Tank Destroyer',
            faction=Faction.AMERICAN, role=VehicleType.TANK_DESTROYER,
            squad_size=1,
            weapon_primary_id='us_76mm_sherman',  # 90mm M3 gun
            vehicle_armor=51,
            vehicle_speed=42,
            vehicle_crew=5,
            experience_level=1,
            morale_initial=82.0,
            stealth_rating=0.15,
            vision_range=7,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=380,
            max_per_battle=1,
            historical_notes='90mm gun TD, could penetrate Tiger/Panther front armor',
        ))

        # JagdPz IV
        variants.append(CC2UnitTemplate(
            template_id='de_jagdpanzer_iv',
            display_name='Jagdpanzer IV',
            faction=Faction.GERMAN, role=VehicleType.TANK_DESTROYER,
            squad_size=1,
            weapon_primary_id='kwk40_75mm',  # 7.5cm PaK 42 L/70
            weapon_secondary_id='coax_mg34',
            vehicle_armor=80,
            vehicle_speed=38,
            vehicle_crew=4,
            experience_level=1,
            morale_initial=84.0,
            stealth_rating=0.16,
            vision_range=6,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=330,
            max_per_battle=1,
            historical_notes='Low-profile tank destroyer, excellent ambush weapon with L/70 gun',
        ))

        # StuG III Ausf G — already exists as de_stug_iii_g

        # Jagdpanther
        variants.append(CC2UnitTemplate(
            template_id='de_jagdpanther',
            display_name='Jagdpanther',
            faction=Faction.GERMAN, role=VehicleType.TANK_DESTROYER,
            squad_size=1,
            weapon_primary_id='kwk36_88mm',  # 8.8cm PaK 43
            weapon_secondary_id='coax_mg34',
            vehicle_armor=100,
            vehicle_speed=46,
            vehicle_crew=5,
            experience_level=2,
            morale_initial=90.0,
            stealth_rating=0.12,
            vision_range=7,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=480,
            max_per_battle=1,
            historical_notes='Best German TD — 88mm gun on Panther chassis, rare but devastating',
        ))

        # M8 Greyhound Armored Car
        variants.append(CC2UnitTemplate(
            template_id='us_m8_greyhound',
            display_name='M8 Greyhound Armored Car',
            faction=Faction.AMERICAN, role=VehicleType.ARMORED_CAR,
            squad_size=1,
            weapon_primary_id='m3_37mm',
            weapon_secondary_id='coax_30cal',
            vehicle_armor=19,
            vehicle_speed=88,
            vehicle_crew=4,
            experience_level=1,
            morale_initial=78.0,
            stealth_rating=0.22,
            vision_range=9,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=160,
            max_per_battle=2,
            historical_notes='Fast armored car, excellent recon but thin armor',
        ))

        # SdKfz 234/2 Puma
        variants.append(CC2UnitTemplate(
            template_id='de_sdkfz_234_puma',
            display_name='SdKfz 234/2 Puma',
            faction=Faction.GERMAN, role=VehicleType.ARMORED_CAR,
            squad_size=1,
            weapon_primary_id='m3_37mm',  # 5cm KwK 39
            weapon_secondary_id='coax_mg34',
            vehicle_armor=30,
            vehicle_speed=90,
            vehicle_crew=4,
            experience_level=1,
            morale_initial=82.0,
            stealth_rating=0.20,
            vision_range=9,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=180,
            max_per_battle=1,
            historical_notes='Heavy armored car with 50mm gun, fast and well-armed recon',
        ))

        # British Tetrarch (airborne light tank)
        variants.append(CC2UnitTemplate(
            template_id='uk_tetrarch',
            display_name='Tetrarch Light Tank',
            faction=Faction.BRITISH, role=VehicleType.TANK_LIGHT,
            squad_size=1,
            weapon_primary_id='m3_37mm',  # QF 2-pdr
            weapon_secondary_id='coax_besa',
            vehicle_armor=16,
            vehicle_speed=64,
            vehicle_crew=3,
            is_amphibious=False,
            experience_level=0,
            morale_initial=75.0,
            stealth_rating=0.22,
            vision_range=7,
            can_deploy_in_building=False,
            can_capture=True,
            deployment_cost=180,
            max_per_battle=1,
            historical_notes='Airborne light tank delivered by Hamilcar glider, thin armor',
        ))

        return variants

    # ------------------------------------------------------------------
    # Experience-level variants
    # ------------------------------------------------------------------

    def generate_experience_variants(
        self,
        template: CC2UnitTemplate,
        levels: list[ExperienceLevel],
    ) -> list[CC2UnitTemplate]:
        """Generate experience-level variants of a base infantry template.

        Skips REGULAR (that's the base template itself).
        """
        variants: list[CC2UnitTemplate] = []

        for level in levels:
            if level == ExperienceLevel.REGULAR:
                continue  # Base template IS regular

            mod = EXPERIENCE_MODIFIERS[level]
            suffix = mod['suffix']

            new_id = f"{template.template_id}_{level.name.lower()}"
            new_name = f"{template.display_name} {suffix}".strip()

            # Calculate modified stats
            new_morale = min(100.0, template.morale_initial * mod['morale_modifier'])
            new_stealth = min(1.0, template.stealth_rating * mod['stealth_modifier'])
            new_vision = max(1, template.vision_range + mod['vision_modifier'])
            new_cost = max(10, int(template.deployment_cost * mod['cost_modifier']))
            new_speed = int(template.vehicle_speed * mod['speed_modifier']) if template.vehicle_speed > 0 else template.vehicle_speed

            variant = replace(
                template,
                template_id=new_id,
                display_name=new_name,
                experience_level=mod['exp_level_int'],
                morale_initial=round(new_morale, 1),
                stealth_rating=round(new_stealth, 2),
                vision_range=new_vision,
                deployment_cost=new_cost,
                vehicle_speed=new_speed,
                historical_notes=(
                    f"{template.historical_notes} — {level.name} experience variant"
                    if template.historical_notes
                    else f"{level.name} experience variant"
                ),
            )
            variants.append(variant)

        return variants

    # ------------------------------------------------------------------
    # Faction-specific variants
    # ------------------------------------------------------------------

    def generate_faction_variants(self) -> list[CC2UnitTemplate]:
        """Create faction-specific unique units."""
        variants: list[CC2UnitTemplate] = []

        # --- British ---
        # Commando squad (elite infantry)
        variants.append(CC2UnitTemplate(
            template_id='uk_commando_squad',
            display_name='British Commando Squad',
            faction=Faction.BRITISH, role=InfantryRole.HEAVY_ASSAULT,
            squad_size=10,
            weapon_primary_id='uk_sten',
            weapon_secondary_id='uk_lee_enfield',
            experience_level=3,
            morale_initial=95.0,
            stealth_rating=0.45,
            vision_range=7,
            can_capture=True,
            deployment_cost=250,
            max_per_battle=1,
            historical_notes='Elite Commando squad, specialized in raids and close assault',
        ))

        # PIAT team (dedicated AT) — already exists as uk_piat_team, add elite variant
        variants.append(CC2UnitTemplate(
            template_id='uk_piat_team_veteran',
            display_name='PIAT Team (Veteran)',
            faction=Faction.BRITISH, role=InfantryRole.ANTI_TANK,
            squad_size=3,
            weapon_primary_id='uk_piat',
            weapon_secondary_id='uk_sten',
            experience_level=2,
            morale_initial=84.0,
            stealth_rating=0.38,
            vision_range=7,
            has_demolitions=True,
            deployment_cost=180,
            max_per_battle=1,
            historical_notes='Veteran PIAT team, experienced in ambush tactics vs armor',
        ))

        # Recce troop (fast scout)
        variants.append(CC2UnitTemplate(
            template_id='uk_recce_troop',
            display_name='Recce Troop',
            faction=Faction.BRITISH, role=InfantryRole.SCOUT,
            squad_size=4,
            weapon_primary_id='uk_lee_enfield',
            weapon_secondary_id='uk_sten',
            experience_level=2,
            morale_initial=85.0,
            stealth_rating=0.55,
            vision_range=10,
            can_capture=False,
            deployment_cost=130,
            max_per_battle=1,
            historical_notes='Reconnaissance troop, fast stealthy scouts with extended vision',
        ))

        # --- American ---
        # Ranger squad (elite infantry) — already exists as us_ranger_squad, add elite variant
        variants.append(CC2UnitTemplate(
            template_id='us_ranger_squad_elite',
            display_name='US Ranger Squad (Elite)',
            faction=Faction.AMERICAN, role=InfantryRole.HEAVY_ASSAULT,
            squad_size=12,
            weapon_primary_id='us_m1_garand',
            weapon_secondary_id='us_browning_bar',
            experience_level=3,
            morale_initial=95.0,
            stealth_rating=0.35,
            vision_range=7,
            can_capture=True,
            deployment_cost=300,
            max_per_battle=1,
            historical_notes='Elite Ranger squad, veterans of Pointe du Hoc and beyond',
        ))

        # Bazooka team — already exists as us_at_team, add veteran variant
        variants.append(CC2UnitTemplate(
            template_id='us_bazooka_team_veteran',
            display_name='US Bazooka Team (Veteran)',
            faction=Faction.AMERICAN, role=InfantryRole.ANTI_TANK,
            squad_size=3,
            weapon_primary_id='us_bazooka',
            weapon_secondary_id='us_m1_carbine',
            experience_level=2,
            morale_initial=84.0,
            stealth_rating=0.38,
            vision_range=7,
            has_demolitions=True,
            deployment_cost=190,
            max_per_battle=1,
            historical_notes='Veteran bazooka team, experienced tank hunters',
        ))

        # Glider infantry (heavy weapons)
        variants.append(CC2UnitTemplate(
            template_id='us_glider_infantry',
            display_name='US Glider Infantry (Heavy Weapons)',
            faction=Faction.AMERICAN, role=InfantryRole.MACHINE_GUN,
            squad_size=8,
            weapon_primary_id='us_m1919a4',
            weapon_secondary_id='us_m1_garand',
            experience_level=1,
            morale_initial=82.0,
            stealth_rating=0.28,
            vision_range=6,
            can_capture=True,
            has_demolitions=False,
            deployment_cost=200,
            max_per_battle=1,
            historical_notes='Gider-borne heavy weapons squad, M1919A4 + Garands',
        ))

        # US Medic Team
        variants.append(CC2UnitTemplate(
            template_id='us_medic_team',
            display_name='US Medic Team',
            faction=Faction.AMERICAN, role=InfantryRole.OFFICER,  # Support role
            squad_size=3,
            weapon_primary_id='us_m1_carbine',
            weapon_secondary_id=None,
            experience_level=1,
            morale_initial=90.0,
            stealth_rating=0.30,
            vision_range=5,
            can_capture=False,
            deployment_cost=120,
            max_per_battle=1,
            historical_notes='Medical team, can treat wounded units, non-combat priority',
        ))

        # --- German ---
        # Fallschirmjäger (elite paratroop) — already exists as de_fallschirmjager, add elite variant
        variants.append(CC2UnitTemplate(
            template_id='de_fallschirmjager_elite',
            display_name='Fallschirmjäger (Elite)',
            faction=Faction.GERMAN, role=InfantryRole.RIFLE,
            squad_size=10,
            weapon_primary_id='de_fg42',
            weapon_secondary_id='de_mp40',
            experience_level=3,
            morale_initial=95.0,
            stealth_rating=0.38,
            vision_range=7,
            can_capture=True,
            deployment_cost=220,
            max_per_battle=1,
            historical_notes='Elite Fallschirmjäger, Crete veterans with FG42 automatic rifles',
        ))

        # Panzergrenadier (mechanized infantry)
        variants.append(CC2UnitTemplate(
            template_id='de_panzergrenadier_squad',
            display_name='Panzergrenadier Squad',
            faction=Faction.GERMAN, role=InfantryRole.HEAVY_ASSAULT,
            squad_size=11,
            weapon_primary_id='de_kar98k',
            weapon_secondary_id='de_mg42',
            experience_level=2,
            morale_initial=88.0,
            stealth_rating=0.28,
            vision_range=6,
            can_capture=True,
            deployment_cost=180,
            max_per_battle=2,
            historical_notes='Mechanized infantry with half-track support, MG42 firepower',
        ))

        # Volksgrenadier (conscript)
        variants.append(CC2UnitTemplate(
            template_id='de_volksgrenadier_squad',
            display_name='Volksgrenadier Squad',
            faction=Faction.GERMAN, role=InfantryRole.RIFLE,
            squad_size=9,
            weapon_primary_id='de_kar98k',
            weapon_secondary_id=None,
            experience_level=0,
            morale_initial=55.0,
            stealth_rating=0.30,
            vision_range=5,
            can_capture=True,
            deployment_cost=60,
            max_per_battle=4,
            historical_notes='Late-war conscript infantry, poorly trained and equipped',
        ))

        # Volksgrenadier AT team (Panzerfaust-heavy)
        variants.append(CC2UnitTemplate(
            template_id='de_volksgrenadier_at',
            display_name='Volksgrenadier AT Team',
            faction=Faction.GERMAN, role=InfantryRole.ANTI_TANK,
            squad_size=4,
            weapon_primary_id='de_panzerfaust',
            weapon_secondary_id='de_kar98k',
            experience_level=0,
            morale_initial=50.0,
            stealth_rating=0.32,
            vision_range=5,
            has_demolitions=False,
            deployment_cost=80,
            max_per_battle=3,
            historical_notes='Volksgrenadier AT team, cheap but low morale and accuracy',
        ))

        # German Medic Team
        variants.append(CC2UnitTemplate(
            template_id='de_medic_team',
            display_name='German Sanitäter Team',
            faction=Faction.GERMAN, role=InfantryRole.OFFICER,
            squad_size=3,
            weapon_primary_id='de_kar98k',
            weapon_secondary_id=None,
            experience_level=1,
            morale_initial=88.0,
            stealth_rating=0.30,
            vision_range=5,
            can_capture=False,
            deployment_cost=120,
            max_per_battle=1,
            historical_notes='German medical team, can treat wounded under ceasefire',
        ))

        # --- Polish ---
        # Polish Para Brigade (special units for Arnhem)
        variants.append(CC2UnitTemplate(
            template_id='pl_para_commando',
            display_name='Polish Para Commando Squad',
            faction=Faction.POLISH, role=InfantryRole.HEAVY_ASSAULT,
            squad_size=8,
            weapon_primary_id='uk_sten',
            weapon_secondary_id='pl_enfield_no4',
            experience_level=2,
            morale_initial=90.0,
            stealth_rating=0.42,
            vision_range=7,
            can_capture=True,
            deployment_cost=220,
            max_per_battle=1,
            historical_notes='Elite Polish Para commando squad, volunteers for Driel crossing',
        ))

        # Polish Para Scout Team
        variants.append(CC2UnitTemplate(
            template_id='pl_para_scout',
            display_name='Polish Para Scout Team',
            faction=Faction.POLISH, role=InfantryRole.SCOUT,
            squad_size=4,
            weapon_primary_id='pl_enfield_no4',
            weapon_secondary_id='uk_sten',
            experience_level=2,
            morale_initial=85.0,
            stealth_rating=0.52,
            vision_range=9,
            can_capture=False,
            deployment_cost=130,
            max_per_battle=1,
            historical_notes='Polish Para reconnaissance team, fast scouts with good stealth',
        ))

        # Polish Para Sniper Team
        variants.append(CC2UnitTemplate(
            template_id='pl_para_sniper',
            display_name='Polish Para Sniper Team',
            faction=Faction.POLISH, role=InfantryRole.SNIPER,
            squad_size=2,
            weapon_primary_id='uk_sniper_no4',
            experience_level=3,
            morale_initial=82.0,
            stealth_rating=0.65,
            vision_range=12,
            can_capture=False,
            deployment_cost=180,
            max_per_battle=1,
            historical_notes='Polish Para sniper team with scoped Lee-Enfield No.4(T)',
        ))

        # Polish Para Heavy Weapons Team
        variants.append(CC2UnitTemplate(
            template_id='pl_para_heavy_weapons',
            display_name='Polish Para Heavy Weapons Team',
            faction=Faction.POLISH, role=InfantryRole.MACHINE_GUN,
            squad_size=5,
            weapon_primary_id='pl_bren_mk2',
            weapon_secondary_id='uk_mills_bomb',
            experience_level=1,
            morale_initial=80.0,
            stealth_rating=0.26,
            vision_range=5,
            can_capture=False,
            deployment_cost=170,
            max_per_battle=1,
            historical_notes='Polish Para heavy weapons team with BREN and grenades',
        ))

        return variants

    # ------------------------------------------------------------------
    # Count
    # ------------------------------------------------------------------

    def count_total_units(self) -> int:
        """Count all generated unit templates."""
        return len(self._generated)

    def get_all_units(self) -> dict[str, CC2UnitTemplate]:
        """Return the complete generated unit dictionary."""
        return dict(self._generated)

    def get_units_by_faction(self, faction: Faction) -> list[CC2UnitTemplate]:
        """Get all generated units for a specific faction."""
        return [u for u in self._generated.values() if u.faction == faction]


# ========================================================================
# Convenience function
# ========================================================================

_EXPANDED_UNITS: dict[str, CC2UnitTemplate] = {}


def get_expanded_unit_database() -> dict[str, CC2UnitTemplate]:
    """Lazy-initialize and return the expanded unit database (100+ templates)."""
    global _EXPANDED_UNITS
    if not _EXPANDED_UNITS:
        base_db = get_cc2_units()
        base_list = list(base_db.values())
        gen = UnitDiversityGenerator()
        expanded = gen.generate_variants(base_list)
        _EXPANDED_UNITS = {u.template_id: u for u in expanded}
    return _EXPANDED_UNITS


# ========================================================================
# Demo
# ========================================================================

if __name__ == '__main__':
    logger.info("=" * 90)
    logger.info("UNIT DIVERSITY EXPANSION — CC2-Authentic Roster Generator")
    logger.info("=" * 90)

    base_db = get_cc2_units()
    base_list = list(base_db.values())
    logger.info("Base templates: %d", len(base_list))

    gen = UnitDiversityGenerator()
    all_units = gen.generate_variants(base_list)

    logger.info("Expanded templates: %d", gen.count_total_units())

    for faction in Faction:
        faction_units = gen.get_units_by_faction(faction)
        inf_count = sum(1 for u in faction_units if isinstance(u.role, InfantryRole))
        veh_count = sum(1 for u in faction_units if isinstance(u.role, VehicleType))

        logger.info("--- %s (%d units: %d infantry + %d vehicles) ---",
                     faction.name, len(faction_units), inf_count, veh_count)
        for u in sorted(faction_units, key=lambda x: (type(x.role).__name__, x.template_id)):
            exp_label = ['Conscript', 'Regular', 'Veteran', 'Elite'][u.experience_level]
            logger.info("  [%-15s] %-40s | Exp:%-9s | Cost:%d",
                        u.role.name, u.display_name, exp_label, u.deployment_cost)

    logger.info("✅ Total unique unit templates: %d", gen.count_total_units())
