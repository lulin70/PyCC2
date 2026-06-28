"""Allied infantry weapon profiles — American + British (P5-1 batch 1).

Extracted from cc2_authentic_weapons.py. Builds the Allied portion of the
CC2 weapon database (US 82nd/101st Airborne + British 1st Airborne / XXX Corps).
"""

from __future__ import annotations

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.weapon_type_defs import WeaponProfile, WeaponType


def build_allied_weapons() -> dict[str, WeaponProfile]:
    """Build American + British infantry weapon profiles."""
    weapons: dict[str, WeaponProfile] = {}
    # ================================================================
    # AMERICAN WEAPONS (82nd / 101st Airborne)
    # ================================================================

    weapons["us_m1_garand"] = WeaponProfile(
        id="us_m1_garand",
        name="M1 Garand",
        weapon_type=WeaponType.RIFLE,
        users=[Faction.AMERICAN],
        range_short=4,
        range_medium=6,
        range_long=8,
        range_max=10,
        accuracy_short=0.72,
        accuracy_medium=0.55,
        accuracy_long=0.32,
        damage_vs_infantry=38.0,
        damage_vs_light_armor=8,
        rpm=45,
        burst_size=8,
        suppress_power=0.18,
        ammo_capacity=96,  # 8-round clip x 12 clips
        year_introduced=1936,
        notes="Standard US rifle, semi-auto, 8-round en-bloc clip",
    )

    weapons["us_m1_carbine"] = WeaponProfile(
        id="us_m1_carbine",
        name="M1 Carbine",
        weapon_type=WeaponType.RIFLE,
        users=[Faction.AMERICAN],
        range_short=3,
        range_medium=5,
        range_long=7,
        range_max=8,
        accuracy_short=0.65,
        accuracy_medium=0.48,
        accuracy_long=0.28,
        damage_vs_infantry=28.0,
        damage_vs_light_armor=5,
        rpm=45,
        burst_size=15,
        suppress_power=0.12,
        ammo_capacity=120,  # 15-round mag
        year_introduced=1941,
        notes="Light rifle for officers/support troops",
    )

    weapons["us_thompson"] = WeaponProfile(
        id="us_thompson",
        name="Thompson M1A1",
        weapon_type=WeaponType.SUBMACHINE_GUN,
        users=[Faction.AMERICAN],
        range_short=2,
        range_medium=4,
        range_long=5,
        range_max=6,
        accuracy_short=0.58,
        accuracy_medium=0.42,
        accuracy_long=0.22,
        damage_vs_infantry=32.0,
        damage_vs_light_armor=5,
        rpm=700,
        burst_size=15,
        suppress_power=0.42,
        ammo_capacity=230,  # 20/30-round mags
        year_introduced=1942,
        notes=".45 ACP SMG, standard issue for NCOs and paratroopers",
    )

    weapons["us_m3_grease_gun"] = WeaponProfile(
        id="us_m3_grease_gun",
        name='M3 "Grease Gun"',
        weapon_type=WeaponType.SUBMACHINE_GUN,
        users=[Faction.AMERICAN],
        range_short=2,
        range_medium=4,
        range_long=5,
        range_max=6,
        accuracy_short=0.55,
        accuracy_medium=0.40,
        accuracy_long=0.20,
        damage_vs_infantry=30.0,
        damage_vs_light_armor=5,
        rpm=450,
        burst_size=15,
        suppress_power=0.38,
        ammo_capacity=180,  # 30-round mag
        year_introduced=1942,
        notes="Simplified Thompson, cheaper to produce",
    )

    # *** THE TWO US MACHINE GUNS (User specifically mentioned!) ***
    weapons["us_m1919"] = WeaponProfile(
        id="us_m1919",
        name="M1919 (M34)",
        weapon_type=WeaponType.MACHINE_GUN_LIGHT,
        users=[Faction.AMERICAN],
        range_short=4,
        range_medium=7,
        range_long=10,
        range_max=12,
        accuracy_short=0.62,
        accuracy_medium=0.48,
        accuracy_long=0.28,
        damage_vs_infantry=40.0,
        damage_vs_light_armor=12,
        rpm=500,
        burst_size=20,
        suppress_power=0.55,
        ammo_capacity=250,  # Belt fed
        year_introduced=1919,
        notes="Air-cooled Browning, earlier variant (M34), lighter tripod mount",
    )

    weapons["us_m1919a4"] = WeaponProfile(
        id="us_m1919a4",
        name="M1919A4 (M42)",
        weapon_type=WeaponType.MACHINE_GUN_HEAVY,
        users=[Faction.AMERICAN],
        range_short=5,
        range_medium=8,
        range_long=12,
        range_max=14,
        accuracy_short=0.68,
        accuracy_medium=0.52,
        accuracy_long=0.30,
        damage_vs_infantry=44.0,
        damage_vs_light_armor=14,
        rpm=550,
        burst_size=25,
        suppress_power=0.65,
        ammo_capacity=250,
        year_introduced=1943,
        notes="Improved M1919 with shoulder stock (M42), primary US MMG",
    )

    weapons["us_m1903_springfield"] = WeaponProfile(
        id="us_m1903_springfield",
        name="M1903 Springfield",
        weapon_type=WeaponType.SNIPER_RIFLE,
        users=[Faction.AMERICAN],
        range_short=6,
        range_medium=10,
        range_long=14,
        range_max=18,
        accuracy_short=0.85,
        accuracy_medium=0.72,
        accuracy_long=0.50,
        damage_vs_infantry=45.0,
        damage_vs_light_armor=12,
        rpm=12,
        burst_size=1,
        suppress_power=0.08,
        ammo_capacity=30,  # 5-round stripper clip
        year_introduced=1903,
        notes="Bolt-action, used by designated marksmen",
    )

    weapons["us_bazooka"] = WeaponProfile(
        id="us_bazooka",
        name="M1A1 Bazooka",
        weapon_type=WeaponType.ANTI_TANK_ROCKET,
        users=[Faction.AMERICAN],
        range_short=2,
        range_medium=3,
        range_long=4,
        range_max=5,
        accuracy_short=0.42,
        accuracy_medium=0.32,
        accuracy_long=0.18,
        damage_vs_infantry=22.0,
        damage_vs_light_armor=65.0,
        damage_vs_heavy_armor=35.0,
        rpm=10,
        burst_size=1,
        suppress_power=0.45,
        can_penetrate=True,
        area_effect=True,
        splash_radius=1,
        ammo_capacity=6,  # Single-shot reload
        year_introduced=1942,
        notes='2.36" rocket launcher, nickname from Bob Burns',
    )

    weapons["us_m2_60mm"] = WeaponProfile(
        id="us_m2_60mm",
        name="M2 60mm Mortar",
        weapon_type=WeaponType.MORTAR_LIGHT,
        users=[Faction.AMERICAN, Faction.BRITISH],
        range_short=3,
        range_medium=6,
        range_long=10,
        range_max=14,
        accuracy_short=0.58,
        accuracy_medium=0.45,
        accuracy_long=0.25,
        damage_vs_infantry=50.0,
        damage_vs_light_armor=18,
        rpm=18,
        burst_size=1,
        suppress_power=0.72,
        area_effect=True,
        splash_radius=2,
        ammo_capacity=30,
        year_introduced=1940,
        notes="Light company-level mortar",
    )

    weapons["us_m1_81mm"] = WeaponProfile(
        id="us_m1_81mm",
        name="M1 81mm Mortar",
        weapon_type=WeaponType.MORTAR_HEAVY,
        users=[Faction.AMERICAN],
        range_short=5,
        range_medium=10,
        range_long=16,
        range_max=20,
        accuracy_short=0.52,
        accuracy_medium=0.40,
        accuracy_long=0.22,
        damage_vs_infantry=62.0,
        damage_vs_light_armor=24,
        rpm=12,
        burst_size=1,
        suppress_power=0.78,
        area_effect=True,
        splash_radius=3,
        ammo_capacity=16,
        year_introduced=1942,
        notes="Battalion-level heavy mortar",
    )

    weapons["us_flamethrower_m2"] = WeaponProfile(
        id="us_flamethrower_m2",
        name="M2 Flamethrower",
        weapon_type=WeaponType.FLAMETHROWER,
        users=[Faction.AMERICAN],
        range_short=1,
        range_medium=2,
        range_long=3,
        range_max=4,
        accuracy_short=0.90,
        accuracy_medium=0.70,
        accuracy_long=0.40,
        damage_vs_infantry=85.0,
        damage_vs_light_armor=55.0,
        damage_vs_heavy_armor=20.0,
        rpm=900,
        burst_size=10,
        suppress_power=0.95,  # Continuous stream
        incendiary=True,
        area_effect=True,
        splash_radius=1,
        ammo_capacity=10,  # Seconds of fuel
        year_introduced=1943,
        notes="Portable flame weapon, terror value extreme",
    )

    # ================================================================
    # BRITISH WEAPONS (1st Airborne / XXX Corps)
    # ================================================================

    weapons["uk_lee_enfield"] = WeaponProfile(
        id="uk_lee_enfield",
        name="Lee-Enfield No.4",
        weapon_type=WeaponType.RIFLE,
        users=[Faction.BRITISH, Faction.POLISH],
        range_short=5,
        range_medium=8,
        range_long=11,
        range_max=13,
        accuracy_short=0.76,
        accuracy_medium=0.60,
        accuracy_long=0.35,
        damage_vs_infantry=40.0,
        damage_vs_light_armor=9,
        rpm=25,
        burst_size=10,
        suppress_power=0.20,
        ammo_capacity=50,  # 10-round magazine
        year_introduced=1941,
        notes='Bolt-action, fastest bolt of war, "Smelly"',
    )

    weapons["uk_sten"] = WeaponProfile(
        id="uk_sten",
        name="STEN Mark II/IV",
        weapon_type=WeaponType.SUBMACHINE_GUN,
        users=[Faction.BRITISH, Faction.POLISH],
        range_short=2,
        range_medium=3,
        range_long=4,
        range_max=5,
        accuracy_short=0.52,
        accuracy_medium=0.38,
        accuracy_long=0.20,
        damage_vs_infantry=28.0,
        damage_vs_light_armor=4,
        rpm=550,
        burst_size=15,
        suppress_power=0.35,
        ammo_capacity=192,  # 32-round mag
        year_introduced=1941,
        notes="Cheap mass-produced 9mm SMG, notorious reliability issues",
    )

    weapons["uk_bren"] = WeaponProfile(
        id="uk_bren",
        name="Bren Gun",
        weapon_type=WeaponType.MACHINE_GUN_HEAVY,
        users=[Faction.BRITISH, Faction.POLISH],
        range_short=5,
        range_medium=8,
        range_long=12,
        range_max=14,
        accuracy_short=0.68,
        accuracy_medium=0.54,
        accuracy_long=0.32,
        damage_vs_infantry=43.0,
        damage_vs_light_armor=13,
        rpm=520,
        burst_size=20,
        suppress_power=0.62,
        ammo_capacity=180,  # 30-round curved magazine
        year_introduced=1938,
        notes="Modified Czech ZB-26, .303 British, main British LMG",
    )

    weapons["uk_vickers"] = WeaponProfile(
        id="uk_vickers",
        name="Vickers KGV (.303)",
        weapon_type=WeaponType.MACHINE_GUN_LIGHT,
        users=[Faction.BRITISH],
        range_short=5,
        range_medium=9,
        range_long=14,
        range_max=18,
        accuracy_short=0.64,
        accuracy_medium=0.50,
        accuracy_long=0.28,
        damage_vs_infantry=41.0,
        damage_vs_light_armor=12,
        rpm=450,
        burst_size=30,
        suppress_power=0.55,
        ammo_capacity=250,  # 250-round belt
        year_introduced=1912,
        notes="Water-cooled HMG, extremely reliable, used on vehicles too",
    )

    weapons["uk_piat"] = WeaponProfile(
        id="uk_piat",
        name="PIAT",
        weapon_type=WeaponType.ANTI_TANK_ROCKET,
        users=[Faction.BRITISH, Faction.POLISH],
        range_short=1,
        range_medium=2,
        range_long=3,
        range_max=4,
        accuracy_short=0.48,
        accuracy_medium=0.35,
        accuracy_long=0.18,
        damage_vs_infantry=25.0,
        damage_vs_light_armor=60.0,
        damage_vs_heavy_armor=30.0,
        rpm=8,
        burst_size=1,
        suppress_power=0.40,
        can_penetrate=True,
        area_effect=True,
        splash_radius=1,
        ammo_capacity=1,  # Single shot, long reload
        year_introduced=1943,
        notes="Projector Infantry Anti-Tank, spring-powered, awkward but effective",
    )

    weapons["uk_2inch_mortar"] = WeaponProfile(
        id="uk_2inch_mortar",
        name="2-inch Mortar",
        weapon_type=WeaponType.MORTAR_LIGHT,
        users=[Faction.BRITISH, Faction.POLISH],
        range_short=3,
        range_medium=5,
        range_long=9,
        range_max=12,
        accuracy_short=0.56,
        accuracy_medium=0.42,
        accuracy_long=0.23,
        damage_vs_infantry=46.0,
        damage_vs_light_armor=16,
        rpm=20,
        burst_size=1,
        suppress_power=0.68,
        area_effect=True,
        splash_radius=2,
        ammo_capacity=36,
        year_introduced=1936,
        notes="Light platoon mortar (actually 51mm bore)",
    )

    weapons["uk_3inch_mortar"] = WeaponProfile(
        id="uk_3inch_mortar",
        name="Ordnance ML 3-inch Mortar",
        weapon_type=WeaponType.MORTAR_HEAVY,
        users=[Faction.BRITISH, Faction.POLISH],
        range_short=4,
        range_medium=10,
        range_long=16,
        range_max=20,
        accuracy_short=0.60,
        accuracy_medium=0.45,
        accuracy_long=0.25,
        damage_vs_infantry=50.0,
        damage_vs_light_armor=15.0,
        damage_vs_heavy_armor=3.0,
        rpm=6,
        burst_size=1,
        suppress_power=0.65,
        can_penetrate=False,
        area_effect=True,
        splash_radius=3,
        ammo_capacity=25,
        year_introduced=1939,
        notes="British 3-inch mortar (76.2mm), battalion level, also used by Polish Paras",
    )

    weapons["uk_flamethrower"] = WeaponProfile(
        id="uk_flamethrower",
        name="Lifebuoy Flamethrower",
        weapon_type=WeaponType.FLAMETHROWER,
        users=[Faction.BRITISH],
        range_short=1,
        range_medium=2,
        range_long=3,
        range_max=4,
        accuracy_short=0.88,
        accuracy_medium=0.68,
        accuracy_long=0.38,
        damage_vs_infantry=82.0,
        damage_vs_light_armor=50.0,
        damage_vs_heavy_armor=18.0,
        rpm=900,
        burst_size=8,
        suppress_power=0.92,  # Continuous stream
        incendiary=True,
        area_effect=True,
        splash_radius=1,
        ammo_capacity=10,
        year_introduced=1943,
        notes='British portable flamethrower, nicknamed "Lifebuoy"',
    )
    return weapons
