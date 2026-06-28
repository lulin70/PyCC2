"""Axis infantry weapon profiles — German (P5-1 batch 1).

Extracted from cc2_authentic_weapons.py. Builds the Axis portion of the
CC2 weapon database (15th Army / SS Panzer Divisions).
"""

from __future__ import annotations

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.weapon_type_defs import WeaponProfile, WeaponType


def build_axis_weapons() -> dict[str, WeaponProfile]:
    """Build German infantry weapon profiles."""
    weapons: dict[str, WeaponProfile] = {}
    # ================================================================
    # GERMAN WEAPONS (15th Army / SS Panzer Divisions)
    # ================================================================

    weapons["de_kar98k"] = WeaponProfile(
        id="de_kar98k",
        name="Kar98k",
        weapon_type=WeaponType.RIFLE,
        users=[Faction.GERMAN],
        range_short=6,
        range_medium=9,
        range_long=12,
        range_max=14,
        accuracy_short=0.75,
        accuracy_medium=0.58,
        accuracy_long=0.33,
        damage_vs_infantry=40.0,
        damage_vs_light_armor=9,
        rpm=15,
        burst_size=5,
        suppress_power=0.20,
        ammo_capacity=40,  # 5-round stripper clip
        year_introduced=1935,
        notes="Standard German bolt-action rifle, excellent accuracy",
    )

    weapons["de_mp40"] = WeaponProfile(
        id="de_mp40",
        name="MP40",
        weapon_type=WeaponType.SUBMACHINE_GUN,
        users=[Faction.GERMAN],
        range_short=2,
        range_medium=4,
        range_long=5,
        range_max=6,
        accuracy_short=0.60,
        accuracy_medium=0.44,
        accuracy_long=0.24,
        damage_vs_infantry=30.0,
        damage_vs_light_armor=5,
        rpm=600,
        burst_size=15,
        suppress_power=0.42,
        ammo_capacity=192,  # 32-round mag
        year_introduced=1940,
        notes='9mm "Schmeisser", iconic German SMG',
    )

    weapons["de_mp44"] = WeaponProfile(
        id="de_mp44",
        name="StG 44 (MP44)",
        weapon_type=WeaponType.RIFLE,
        users=[Faction.GERMAN],
        range_short=3,
        range_medium=5,
        range_long=7,
        range_max=8,
        accuracy_short=0.62,
        accuracy_medium=0.48,
        accuracy_long=0.28,
        damage_vs_infantry=36.0,
        damage_vs_light_armor=8,
        rpm=600,
        burst_size=10,
        suppress_power=0.38,
        ammo_capacity=150,  # 30-round mag
        year_introduced=1943,
        notes="First assault rifle, intermediate cartridge, rare in CC2 timeframe",
    )

    # *** THE TWO GERMAN MACHINE GUNS ***
    weapons["de_mg34"] = WeaponProfile(
        id="de_mg34",
        name="MG34",
        weapon_type=WeaponType.MACHINE_GUN_LIGHT,
        users=[Faction.GERMAN],
        range_short=5,
        range_medium=9,
        range_long=13,
        range_max=16,
        accuracy_short=0.66,
        accuracy_medium=0.50,
        accuracy_long=0.29,
        damage_vs_infantry=42.0,
        damage_vs_light_armor=12,
        rpm=850,
        burst_size=25,
        suppress_power=0.62,
        ammo_capacity=250,  # 50-round drum or belt
        year_introduced=1934,
        notes="First universal MG, replaced by MG42 but still in use",
    )

    weapons["de_mg42"] = WeaponProfile(
        id="de_mg42",
        name="MG42",
        weapon_type=WeaponType.MACHINE_GUN_HEAVY,
        users=[Faction.GERMAN],
        range_short=6,
        range_medium=10,
        range_long=14,
        range_max=18,
        accuracy_short=0.70,
        accuracy_medium=0.54,
        accuracy_long=0.31,
        damage_vs_infantry=48.0,
        damage_vs_light_armor=14,
        rpm=1200,
        burst_size=30,
        suppress_power=0.90,  # "Hitler's Saw"
        ammo_capacity=250,  # Belt fed
        year_introduced=1942,
        notes="THE iconic German MG, terrifying ROF, distinctive sound",
    )

    weapons["de_panzerschreck"] = WeaponProfile(
        id="de_panzerschreck",
        name="Panzerschreck (RPzB 54)",
        weapon_type=WeaponType.ANTI_TANK_ROCKET,
        users=[Faction.GERMAN],
        range_short=2,
        range_medium=3,
        range_long=4,
        range_max=5,
        accuracy_short=0.45,
        accuracy_medium=0.34,
        accuracy_long=0.19,
        damage_vs_infantry=26.0,
        damage_vs_light_armor=70.0,
        damage_vs_heavy_armor=40.0,
        rpm=8,
        burst_size=1,
        suppress_power=0.50,
        can_penetrate=True,
        area_effect=True,
        splash_radius=1,
        ammo_capacity=1,
        year_introduced=1943,
        notes='88mm RPzB "Tank Terror", copied from Bazooka but improved',
    )

    weapons["de_panzerfaust"] = WeaponProfile(
        id="de_panzerfaust",
        name="Panzerfaust (30/60/100)",
        weapon_type=WeaponType.ANTI_TANK_ROCKET,
        users=[Faction.GERMAN],
        range_short=1,
        range_medium=2,
        range_long=3,
        range_max=4,
        accuracy_short=0.50,
        accuracy_medium=0.36,
        accuracy_long=0.18,
        damage_vs_infantry=30.0,
        damage_vs_light_armor=75.0,
        damage_vs_heavy_armor=45.0,
        rpm=4,
        burst_size=1,
        suppress_power=0.55,
        can_penetrate=True,
        area_effect=True,
        splash_radius=1,
        ammo_capacity=1,  # Disposable!
        year_introduced=1943,
        notes="Disposable AT weapon, one-shot, very common late-war",
    )

    weapons["de_grw36_50mm"] = WeaponProfile(
        id="de_grw36_50mm",
        name="GrW 36 50mm Mortar",
        weapon_type=WeaponType.MORTAR_LIGHT,
        users=[Faction.GERMAN],
        range_short=2,
        range_medium=4,
        range_long=7,
        range_max=10,
        accuracy_short=0.54,
        accuracy_medium=0.41,
        accuracy_long=0.22,
        damage_vs_infantry=42.0,
        damage_vs_light_armor=14,
        rpm=24,
        burst_size=1,
        suppress_power=0.64,
        area_effect=True,
        splash_radius=1,
        ammo_capacity=50,
        year_introduced=1936,
        notes="Light platoon mortar, small but effective",
    )

    weapons["de_grw34_81mm"] = WeaponProfile(
        id="de_grw34_81mm",
        name="GrW 34 81mm Mortar",
        weapon_type=WeaponType.MORTAR_HEAVY,
        users=[Faction.GERMAN],
        range_short=5,
        range_medium=11,
        range_long=17,
        range_max=22,
        accuracy_short=0.52,
        accuracy_medium=0.39,
        accuracy_long=0.21,
        damage_vs_infantry=58.0,
        damage_vs_light_armor=22,
        rpm=15,
        burst_size=1,
        suppress_power=0.74,
        area_effect=True,
        splash_radius=3,
        ammo_capacity=14,
        year_introduced=1934,
        notes="Standard German medium mortar",
    )

    weapons["de_flammenwerfer_41"] = WeaponProfile(
        id="de_flammenwerfer_41",
        name="Flammenwerfer 41",
        weapon_type=WeaponType.FLAMETHROWER,
        users=[Faction.GERMAN],
        range_short=1,
        range_medium=2,
        range_long=3,
        range_max=4,
        accuracy_short=0.88,
        accuracy_medium=0.68,
        accuracy_long=0.38,
        damage_vs_infantry=84.0,
        damage_vs_light_armor=52.0,
        damage_vs_heavy_armor=19.0,
        rpm=900,
        burst_size=10,
        suppress_power=0.94,  # Continuous stream
        incendiary=True,
        area_effect=True,
        splash_radius=1,
        ammo_capacity=10,
        year_introduced=1941,
        notes="German portable flamethrower, feared by Allied infantry",
    )

    weapons["de_flammenwerfer"] = WeaponProfile(
        id="de_flammenwerfer",
        name="Flammenwerfer 41",
        weapon_type=WeaponType.FLAMETHROWER,
        users=[Faction.GERMAN],
        range_short=2,
        range_medium=3,
        range_long=0,
        range_max=3,
        accuracy_short=0.85,
        accuracy_medium=0.60,
        accuracy_long=0.0,
        damage_vs_infantry=80.0,
        damage_vs_light_armor=30.0,
        damage_vs_heavy_armor=5.0,
        rpm=4,
        burst_size=1,
        suppress_power=0.90,
        can_penetrate=False,
        ammo_capacity=8,
        year_introduced=1941,
        notes="German infantry flamethrower, devastating vs infantry in buildings",
    )

    weapons["de_75mm_inf_gun"] = WeaponProfile(
        id="de_75mm_inf_gun",
        name="7.5cm leIG 18",
        weapon_type=WeaponType.MORTAR_HEAVY,
        users=[Faction.GERMAN],
        range_short=3,
        range_medium=8,
        range_long=14,
        range_max=18,
        accuracy_short=0.65,
        accuracy_medium=0.50,
        accuracy_long=0.30,
        damage_vs_infantry=55.0,
        damage_vs_light_armor=25.0,
        damage_vs_heavy_armor=5.0,
        rpm=8,
        burst_size=1,
        suppress_power=0.60,
        can_penetrate=False,
        ammo_capacity=30,
        year_introduced=1939,
        notes="German light infantry gun, indirect fire support",
    )

    # ================================================================
    # VEHICLE WEAPONS (Tank Guns, Coaxial MGs)
    # ================================================================

    weapons["pl_enfield_no4"] = WeaponProfile(
        id="pl_enfield_no4",
        name="Polish Lee-Enfield No.4",
        weapon_type=WeaponType.RIFLE,
        users=[Faction.POLISH],
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
        notes="British-issue Lee-Enfield No.4 used by Polish Paras",
    )

    weapons["pl_bren_mk2"] = WeaponProfile(
        id="pl_bren_mk2",
        name="Polish BREN Mk.II",
        weapon_type=WeaponType.MACHINE_GUN_HEAVY,
        users=[Faction.POLISH],
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
        notes="British-issue BREN Mk.II used by Polish Paras",
    )

    weapons["pl_piat"] = WeaponProfile(
        id="pl_piat",
        name="Polish PIAT",
        weapon_type=WeaponType.ANTI_TANK_ROCKET,
        users=[Faction.POLISH],
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
        notes="British-issue PIAT used by Polish Paras",
    )
    return weapons
