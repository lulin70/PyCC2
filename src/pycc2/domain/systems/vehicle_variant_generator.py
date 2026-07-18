"""STATUS: INTEGRATED v0.7.6 — Vehicle variant generator — Sherman/Panzer/Halftrack/TD families (P5-1 batch 1).

Extracted from unit_diversity_expansion.py. Generates vehicle variants
(Sherman M4A1/Firefly/DD, Panzer IV Ausf J/III Ausf M, SdKfz 251 variants,
M10/M36/JagdPz IV/StuG III Ausf G).
"""

from __future__ import annotations

import logging

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.cc2_authentic_units import CC2UnitTemplate
from pycc2.domain.systems.cc2_authentic_weapons import VehicleType

logger = logging.getLogger(__name__)


class VehicleVariantGenerator:
    """Generate vehicle variant templates (Sherman, Panzer, Halftrack, TD families)."""

    def generate(self) -> list[CC2UnitTemplate]:
        """Create vehicle variants (Sherman, Panzer, Half-track, TD families)."""
        variants: list[CC2UnitTemplate] = []

        # --- Sherman variants ---
        # Sherman M4A1 (basic) — already exists as us_sherman_m4

        # Sherman Firefly (17pdr AT) — already exists as uk_firefly

        # Sherman DD (amphibious, slower) — already exists as uk_sherman_dd

        # Sherman M4A3E8 "Easy Eight" (improved 76mm)
        variants.append(
            CC2UnitTemplate(
                template_id="us_sherman_easy_eight",
                display_name='M4A3E8 Sherman "Easy Eight"',
                faction=Faction.AMERICAN,
                role=VehicleType.TANK_MEDIUM,
                squad_size=1,
                weapon_primary_id="us_76mm_sherman",
                weapon_secondary_id="coax_30cal",
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
                historical_notes="Improved Sherman with 76mm HVSS suspension, best US tank of the war",
            )
        )

        # Sherman M4A3 75mm (Wet Stowage)
        variants.append(
            CC2UnitTemplate(
                template_id="us_sherman_m4a3_75",
                display_name="M4A3 Sherman (75mm Wet)",
                faction=Faction.AMERICAN,
                role=VehicleType.TANK_MEDIUM,
                squad_size=1,
                weapon_primary_id="m3_75mm_m4",
                weapon_secondary_id="coax_30cal",
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
                historical_notes="M4A3 with wet ammo stowage, reduced fire risk",
            )
        )

        # Sherman Calliope (rocket launcher)
        variants.append(
            CC2UnitTemplate(
                template_id="us_sherman_calliope",
                display_name="Sherman Calliope (T34 Rocket)",
                faction=Faction.AMERICAN,
                role=VehicleType.SP_ARTILLERY,
                squad_size=1,
                weapon_primary_id="m3_75mm_m4",
                weapon_secondary_id="coax_30cal",
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
                historical_notes="Sherman with T34 rocket launcher, devastating barrage capability",
            )
        )

        # --- Panzer variants ---
        # PzKpfw IV Ausf J (late war, no turret traverse motor)
        variants.append(
            CC2UnitTemplate(
                template_id="de_panzer_iv_ausf_j",
                display_name="PzKpfw IV Ausf J",
                faction=Faction.GERMAN,
                role=VehicleType.TANK_MEDIUM,
                squad_size=1,
                weapon_primary_id="kwk40_75mm",
                weapon_secondary_id="coax_mg34",
                vehicle_armor=80,
                vehicle_speed=32,  # Slower — no turret traverse motor, manual only
                vehicle_crew=4,  # Reduced crew
                experience_level=0,  # Late war conscript crews
                morale_initial=78.0,
                stealth_rating=0.14,
                vision_range=6,
                can_deploy_in_building=False,
                can_capture=True,
                deployment_cost=280,
                historical_notes="Late-war PzIV with manual turret traverse, reduced crew quality",
            )
        )

        # PzKpfw III Ausf M (older, weaker)
        variants.append(
            CC2UnitTemplate(
                template_id="de_panzer_iii_ausf_m",
                display_name="PzKpfw III Ausf M",
                faction=Faction.GERMAN,
                role=VehicleType.TANK_LIGHT,
                squad_size=1,
                weapon_primary_id="de_mg34_vehicle",  # 50mm KwK 39 L/60
                weapon_secondary_id="coax_mg34",
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
                historical_notes="Obsolete Panzer III, relegated to recon and support roles",
            )
        )

        # --- Half-track variants ---
        # SdKfz 251/1 (transport) — already exists as de_sdkfz_251

        # SdKfz 251/16 (flamethrower)
        variants.append(
            CC2UnitTemplate(
                template_id="de_sdkfz_251_16",
                display_name="SdKfz 251/16 Flammpanzerwagen",
                faction=Faction.GERMAN,
                role=VehicleType.FLAME_TANK,
                squad_size=1,
                weapon_primary_id="de_flammenwerfer",
                weapon_secondary_id="coax_mg34",
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
                historical_notes="Half-track flamethrower variant, devastating vs infantry in cover",
            )
        )

        # SdKfz 251/9 (75mm gun — "Stummel")
        variants.append(
            CC2UnitTemplate(
                template_id="de_sdkfz_251_9",
                display_name='SdKfz 251/9 "Stummel"',
                faction=Faction.GERMAN,
                role=VehicleType.TANK_DESTROYER,
                squad_size=1,
                weapon_primary_id="kwk40_75mm",  # 7.5cm KwK 37 L/24
                weapon_secondary_id="coax_mg34",
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
                historical_notes="Half-track with short 75mm gun, infantry fire support",
            )
        )

        # M3 Half-track with 75mm GMC
        variants.append(
            CC2UnitTemplate(
                template_id="us_m3_halftrack_75",
                display_name="M3 Half-track (75mm GMC)",
                faction=Faction.AMERICAN,
                role=VehicleType.TANK_DESTROYER,
                squad_size=1,
                weapon_primary_id="m3_75mm_m4",
                weapon_secondary_id="coax_30cal",
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
                historical_notes="M3 half-track with mounted 75mm gun, mobile fire support",
            )
        )

        # --- TD variants ---
        # M10 Wolverine — already exists as us_wolverine_m10

        # M36 Jackson
        variants.append(
            CC2UnitTemplate(
                template_id="us_m36_jackson",
                display_name="M36 Jackson Tank Destroyer",
                faction=Faction.AMERICAN,
                role=VehicleType.TANK_DESTROYER,
                squad_size=1,
                weapon_primary_id="us_76mm_sherman",  # 90mm M3 gun
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
                historical_notes="90mm gun TD, could penetrate Tiger/Panther front armor",
            )
        )

        # JagdPz IV
        variants.append(
            CC2UnitTemplate(
                template_id="de_jagdpanzer_iv",
                display_name="Jagdpanzer IV",
                faction=Faction.GERMAN,
                role=VehicleType.TANK_DESTROYER,
                squad_size=1,
                weapon_primary_id="kwk40_75mm",  # 7.5cm PaK 42 L/70
                weapon_secondary_id="coax_mg34",
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
                historical_notes="Low-profile tank destroyer, excellent ambush weapon with L/70 gun",
            )
        )

        # StuG III Ausf G — already exists as de_stug_iii_g

        # Jagdpanther
        variants.append(
            CC2UnitTemplate(
                template_id="de_jagdpanther",
                display_name="Jagdpanther",
                faction=Faction.GERMAN,
                role=VehicleType.TANK_DESTROYER,
                squad_size=1,
                weapon_primary_id="kwk36_88mm",  # 8.8cm PaK 43
                weapon_secondary_id="coax_mg34",
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
                historical_notes="Best German TD — 88mm gun on Panther chassis, rare but devastating",
            )
        )

        # M8 Greyhound Armored Car
        variants.append(
            CC2UnitTemplate(
                template_id="us_m8_greyhound",
                display_name="M8 Greyhound Armored Car",
                faction=Faction.AMERICAN,
                role=VehicleType.ARMORED_CAR,
                squad_size=1,
                weapon_primary_id="m3_37mm",
                weapon_secondary_id="coax_30cal",
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
                historical_notes="Fast armored car, excellent recon but thin armor",
            )
        )

        # SdKfz 234/2 Puma
        variants.append(
            CC2UnitTemplate(
                template_id="de_sdkfz_234_puma",
                display_name="SdKfz 234/2 Puma",
                faction=Faction.GERMAN,
                role=VehicleType.ARMORED_CAR,
                squad_size=1,
                weapon_primary_id="m3_37mm",  # 5cm KwK 39
                weapon_secondary_id="coax_mg34",
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
                historical_notes="Heavy armored car with 50mm gun, fast and well-armed recon",
            )
        )

        # British Tetrarch (airborne light tank)
        variants.append(
            CC2UnitTemplate(
                template_id="uk_tetrarch",
                display_name="Tetrarch Light Tank",
                faction=Faction.BRITISH,
                role=VehicleType.TANK_LIGHT,
                squad_size=1,
                weapon_primary_id="m3_37mm",  # QF 2-pdr
                weapon_secondary_id="coax_besa",
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
                historical_notes="Airborne light tank delivered by Hamilcar glider, thin armor",
            )
        )

        return variants
