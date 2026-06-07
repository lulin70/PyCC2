"""
CC2 Authentic Unit Type System & Deployment Phase

Complete implementation of CC2's unit diversity and pre-battle deployment.

Based on CC2 Wiki (gamia-archive.fandom.com):
- Infantry category: Rifle, Scout, Sniper, MG, AT, Heavy Assault, Reserve
- Support category: Flamethrower Engineer, Mortar Team, MG Team, Vehicles
- Deployment phase: Player drags units to setup area before battle
- Three zones: Enemy Controlled (dark), No Man's Land (light), Friendly (clear)

Total unit types modeled: 80+ (matching CC2's 130+ with vehicle variants)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)

from pycc2.domain.systems.cc2_authentic_weapons import (
    WeaponProfile, Faction, InfantryRole, VehicleType,
    get_cc2_weapons, get_weapons_for_faction
)


# ========================================================================
# UNIT TEMPLATES
# ========================================================================

@dataclass 
class CC2UnitTemplate:
    """
    Complete unit specification matching CC2's internal data structure.
    
    Each template represents a deployable team/squad/vehicle.
    """
    
    # === IDENTITY ===
    template_id: str                   # Unique identifier: 'us_rifle_squad_82nd'
    display_name: str                  # "82nd Airborne Rifle Squad"
    faction: Faction
    role: InfantryRole | VehicleType   # Unit role classification
    
    # === COMPOSITION (Infantry only) ===
    squad_size: int = 10               # Number of men (1-15)
    weapon_primary_id: str = ''        # Primary weapon key from weapon DB
    weapon_secondary_id: str | None = None  # Optional secondary weapon
    
    # === VEHICLE DATA (Vehicles only) ===
    vehicle_armor: int = 0             # Armor thickness (mm equivalent)
    vehicle_speed: int = 0            # Max speed (km/h)
    vehicle_crew: int = 0             # Crew size
    is_amphibious: bool = False       # Can cross water
    
    # === COMBAT STATS (derived from weapons + experience) ===
    experience_level: int = 0         # 0=Green, 1=Regular, 2=Veteran, 3=Elite
    morale_initial: float = 80.0      # Starting morale (0-100)
    stealth_rating: float = 0.3       # Base concealment (0.0-1.0)
    vision_range: int = 6             # Tiles of visibility
    
    # === SPECIAL PROPERTIES ===
    can_capture: bool = True          # Can capture victory locations
    can_deploy_in_building: bool = True
    can_deploy_in_open: bool = True
    is_command_unit: bool = False     # Morale boost to nearby units
    is_fanatic: bool = False         # Never panics (SS/Fanatics)
    has_demolitions: bool = False     # Can destroy structures
    
    # === DEPLOYMENT RULES ===
    deployment_cost: int = 100        # "Requisition points" cost (Operations mode)
    max_per_battle: int = 99           # Limit on how many can be brought
    min_turns_reinforce: int = 0     # 0=available start, >0=reinforcement turn
    
    # === FLAVOR TEXT ===
    historical_notes: str = ""
    
    def get_weapon(self) -> WeaponProfile:
        """Resolve and return primary weapon profile."""
        db = get_cc2_weapons()
        return db.get(self.weapon_primary_id)
    
    def get_secondary_weapon(self) -> WeaponProfile | None:
        """Resolve optional secondary weapon."""
        if not self.weapon_secondary_id:
            return None
        db = get_cc2_weapons()
        return db.get(self.weapon_secondary_id)
    
    def calculate_effective_stats(self) -> dict[str, Any]:
        """
        Calculate effective combat stats based on equipment + experience.
        
        Returns dict with all relevant combat parameters.
        """
        weapon = self.get_weapon()
        if not weapon:
            return {'error': f'Unknown weapon: {self.weapon_primary_id}'}
        
        # Experience multipliers (CC2-style)
        exp_mult = {
            0: {'accuracy': 1.0, 'morale': 1.0, 'suppression_resist': 1.0},
            1: {'accuracy': 1.10, 'morale': 1.05, 'suppression_resist': 1.05},
            2: {'accuracy': 1.20, 'morale': 1.12, 'suppression_resist': 1.12},
            3: {'accuracy': 1.35, 'morale': 1.25, 'suppression_resist': 1.25},
        }
        
        m = exp_mult.get(self.experience_level, exp_mult[0])
        
        base_stats = {
            'name': self.display_name,
            'role': self.role.name,
            'faction': self.faction.name,
            'squad_size': self.squad_size,
            
            # Weapon stats (experience-modified)
            'weapon_name': weapon.name,
            'weapon_type': weapon.weapon_type.name,
            'range_short': weapon.range_short,
            'range_max': weapon.range_max,
            'accuracy_short': min(0.95, weapon.accuracy_short * m['accuracy']),
            'accuracy_long': min(0.95, weapon.accuracy_long * m['accuracy']),
            'damage_vs_infantry': weapon.damage_vs_infantry,
            'damage_vs_light_armor': weapon.damage_vs_light_armor,
            'suppress_power': min(1.0, weapon.suppress_power),
            'rpm': weapon.rpm,
            
            # Unit stats
            'morale': min(100, self.morale_initial * m['morale']),
            'stealth': self.stealth_rating,
            'vision': self.vision_range,
            'exp_level': self.experience_level,
            'is_fanatic': self.is_fanatic,
            'can_capture': self.can_capture,
            'deployment_cost': self.deployment_cost,
        }
        
        return base_stats


def build_cc2_unit_database() -> dict[str, CC2UnitTemplate]:
    """
    Build complete CC2 unit database.
    
    Based on historical OOBs for Operation Market Garden (Sept 1944).
    Covers all four factions with authentic compositions.
    """
    units = {}
    
    # ================================================================
    # AMERICAN FORCES (82nd Airborne / 101st Airborne)
    # ================================================================
    
    # --- INFANTRY CATEGORY ---
    
    units['us_rifle_squad'] = CC2UnitTemplate(
        template_id='us_rifle_squad',
        display_name='US Rifle Squad',
        faction=Faction.AMERICAN, role=InfantryRole.RIFLE,
        squad_size=12,
        weapon_primary_id='us_m1_garand',
        weapon_secondary_id='us_thompson',  # BAR or Thompson for squad leader
        experience_level=1,
        morale_initial=85.0,
        stealth_rating=0.30,
        vision_range=6,
        can_capture=True,
        deployment_cost=120,
        historical_notes='Standard US airborne rifle squad, 12 men with M1 Garands'
    )
    
    units['us_rifle_squad_veteran'] = CC2UnitTemplate(
        template_id='us_rifle_squad_veteran',
        display_name='Veteran Rifle Squad',
        faction=Faction.AMERICAN, role=InfantryRole.RIFLE,
        squad_size=11,
        weapon_primary_id='us_m1_garand',
        weapon_secondary_id='us_m1903_springfield',  # Designated marksman
        experience_level=2,
        morale_initial=90.0,
        stealth_rating=0.32,
        vision_range=7,
        deployment_cost=150,
        historical_notes='Battle-hardened squad from earlier campaigns'
    )
    
    units['us_machine_gun_team_a4'] = CC2UnitTemplate(  # M1919A4 (M42)
        template_id='us_machine_gun_team_a4',
        display_name='US MG Team (M1919A4)',
        faction=Faction.AMERICAN, role=InfantryRole.MACHINE_GUN,
        squad_size=5,
        weapon_primary_id='us_m1919a4',  # *** THE M42 HEAVY MG ***
        weapon_secondary_id='us_thompson',
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.25,
        vision_range=5,
        can_capture=True,
        deployment_cost=160,
        historical_notes='Heavy machine gun team with M1919A4 (.30 cal), excellent suppression'
    )
    
    units['us_machine_gun_team_m34'] = CC2UnitTemplate(  # M1919 (M34)
        template_id='us_machine_gun_team_m34',
        display_name='US MG Team (M1919)',
        faction=Faction.AMERICAN, role=InfantryRole.MACHINE_GUN,
        squad_size=5,
        weapon_primary_id='us_m1919',  # *** THE M34 LIGHT MG ***
        weapon_secondary_id='us_m1_carbine',
        experience_level=0,
        morale_initial=78.0,
        stealth_rating=0.27,
        vision_range=5,
        deployment_cost=130,
        historical_notes='Lighter machine gun team with M1919 variant, more mobile but less firepower'
    )
    
    units['us_scout_team'] = CC2UnitTemplate(
        template_id='us_scout_team',
        display_name='US Scout Team',
        faction=Faction.AMERICAN, role=InfantryRole.SCOUT,
        squad_size=4,
        weapon_primary_id='us_m1_carbine',
        weapon_secondary_id='us_thompson',
        experience_level=2,
        morale_initial=83.0,
        stealth_rating=0.50,  # Better than regular infantry
        vision_range=9,  # Extended vision
        deployment_cost=110,
        historical_notes='Reconnaissance specialists, small fast teams'
    )
    
    units['us_sniper_team'] = CC2UnitTemplate(
        template_id='us_sniper_team',
        display_name='US Sniper Team',
        faction=Faction.AMERICAN, role=InfantryRole.SNIPER,
        squad_size=2,
        weapon_primary_id='us_m1903_springfield',
        experience_level=3,
        morale_initial=80.0,
        stealth_rating=0.65,
        vision_range=12,
        can_capture=False,  # Snipers don't capture objectives
        deployment_cost=140,
        historical_notes='Designated marksmen with scoped Springfields'
    )
    
    units['us_at_team'] = CC2UnitTemplate(
        template_id='us_at_team',
        display_name='US AT Team (Bazooka)',
        faction=Faction.AMERICAN, role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id='us_bazooka',
        weapon_secondary_id='us_m1_carbine',
        experience_level=1,
        morale_initial=78.0,
        stealth_rating=0.35,
        vision_range=6,
        can_capture=True,
        has_demolitions=True,
        deployment_cost=150,
        historical_notes='Anti-tank specialists with M1A1 Bazooka'
    )
    
    units['us_engineer_team'] = CC2UnitTemplate(
        template_id='us_engineer_team',
        display_name='US Engineer Squad',
        faction=Faction.AMERICAN, role=InfantryRole.ENGINEER,
        squad_size=8,
        weapon_primary_id='us_m1_carbine',
        weapon_secondary_id='us_thompson',
        experience_level=1,
        morale_initial=81.0,
        stealth_rating=0.38,
        vision_range=6,
        can_capture=True,
        has_demolitions=True,
        deployment_cost=140,
        historical_notes='Combat engineers, can build fortifications and demolish obstacles'
    )

    units['us_engineer_squad'] = CC2UnitTemplate(
        template_id='us_engineer_squad',
        display_name='Engineer Squad',
        faction=Faction.AMERICAN, role=InfantryRole.ENGINEER,
        squad_size=8,
        weapon_primary_id='us_m1_garand',
        weapon_secondary_id='us_m1_carbine',
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.36,
        vision_range=6,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        has_demolitions=True,
        deployment_cost=170,
        max_per_battle=1,
        historical_notes='US combat engineers with Garands, demolition and fortification specialists'
    )
    
    units['us_flamethrower_team'] = CC2UnitTemplate(
        template_id='us_flamethrower_team',
        display_name='US Flamethrower Team',
        faction=Faction.AMERICAN, role=InfantryRole.FLAMETHROWER,
        squad_size=3,
        weapon_primary_id='us_flamethrower_m2',
        weapon_secondary_id='us_m1_carbine',
        experience_level=1,
        morale_initial=75.0,  # Low morale (dangerous job!)
        stealth_rating=0.40,
        vision_range=5,
        can_capture=True,
        deployment_cost=170,
        historical_notes='Flame specialists, devastating in close quarters, high casualty risk'
    )
    
    units['us_officer'] = CC2UnitTemplate(
        template_id='us_officer',
        display_name='US Officer / Commander',
        faction=Faction.AMERICAN, role=InfantryRole.OFFICER,
        squad_size=3,
        weapon_primary_id='us_m1_carbine',
        weapon_secondary_id='us_thompson',
        experience_level=2,
        morale_initial=95.0,  # High morale (leadership)
        stealth_rating=0.35,
        vision_range=7,
        is_command_unit=True,  # Boosts nearby unit morale!
        can_capture=False,
        deployment_cost=180,
        historical_notes='Platoon/Battalion commander, provides morale bonus to adjacent units'
    )
    
    units['us_heavy_assault'] = CC2UnitTemplate(
        template_id='us_heavy_assault',
        display_name='US Assault Squad',
        faction=Faction.AMERICAN, role=InfantryRole.HEAVY_ASSAULT,
        squad_size=9,
        weapon_primary_id='us_thompson',
        weapon_secondary_id='us_m3_grease_gun',
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.32,
        vision_range=6,
        deployment_cost=145,
        historical_notes='Close-quarters assault troops, heavily armed with SMGs'
    )
    
    # --- SUPPORT CATEGORY ---
    
    units['us_mortar_light_team'] = CC2UnitTemplate(
        template_id='us_mortar_light_team',
        display_name='US Light Mortar Team (60mm)',
        faction=Faction.AMERICAN, role=InfantryRole.RIFLE,  # Support category
        squad_size=4,
        weapon_primary_id='us_m2_60mm',  # *** LIGHT MORTAR ***
        weapon_secondary_id='us_m1_carbine',
        experience_level=1,
        morale_initial=79.0,
        stealth_rating=0.33,
        vision_range=6,
        can_capture=False,
        deployment_cost=140,
        historical_notes='Company-level 60mm mortar team, indirect fire support'
    )
    
    units['us_mortar_heavy_team'] = CC2UnitTemplate(
        template_id='us_mortar_heavy_team',
        display_name='US Heavy Mortar Team (81mm)',
        faction=Faction.AMERICAN, role=InfantryRole.RIFLE,
        squad_size=5,
        weapon_primary_id='us_m1_81mm',  # *** HEAVY MORTAR ***
        weapon_secondary_id='us_m1_carbine',
        experience_level=1,
        morale_initial=78.0,
        stealth_rating=0.30,
        vision_range=5,
        can_capture=False,
        deployment_cost=175,
        historical_notes='Battalion-level 81mm mortar, heavy indirect fire'
    )
    
    # --- VEHICLES ---
    
    units['us_sherman_m4'] = CC2UnitTemplate(
        template_id='us_sherman_m4',
        display_name='M4 Sherman (75mm)',
        faction=Faction.AMERICAN, role=VehicleType.TANK_MEDIUM,
        squad_size=1,  # Crew count
        weapon_primary_id='m3_75mm_m4',
        weapon_secondary_id='coax_30cal',
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
        historical_notes='Main US medium tank, reliable but undergunned vs late German armor'
    )
    
    units['us_stuart_m5'] = CC2UnitTemplate(
        template_id='us_stuart_m5',
        display_name='M5 Stuart (37mm)',
        faction=Faction.AMERICAN, role=VehicleType.TANK_LIGHT,
        squad_size=1,
        weapon_primary_id='m3_37mm',
        weapon_secondary_id='coax_30cal',
        vehicle_armor=51,
        vehicle_speed=58,
        vehicle_crew=4,
        experience_level=0,
        morale_initial=78.0,
        stealth_rating=0.22,
        vision_range=8,
        can_deploy_in_building=False,
        deployment_cost=220,
        historical_notes='Light tank, fast but weak armor/gun, used for recon'
    )
    
    units['us_halftrack_m3'] = CC2UnitTemplate(
        template_id='us_halftrack_m3',
        display_name='M3 Halftrack',
        faction=Faction.AMERICAN, role=VehicleType.HALFTRACK,
        squad_size=1,
        weapon_primary_id='coax_30cal',  # .30 cal mounted
        vehicle_armor=13,  # Thin armor
        vehicle_speed=72,
        vehicle_crew=3,
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.18,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=180,
        historical_notes='Armored personnel carrier, transports infantry'
    )
    
    units['us_wolverine_m10'] = CC2UnitTemplate(
        template_id='us_wolverine_m10',
        display_name='M10 Wolverine Tank Destroyer',
        faction=Faction.AMERICAN, role=VehicleType.TANK_DESTROYER,
        squad_size=1,
        weapon_primary_id='m3_75mm_m4',  # Same 75mm as Sherman but open-topped
        vehicle_armor=51,
        vehicle_speed=48,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=80.0,
        stealth_rating=0.16,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=320,
        historical_notes='Open-topped TD, good gun but vulnerable to infantry/heavy fire'
    )
    
    # ================================================================
    # BRITISH FORCES (1st Airborne / XXX Corps)
    # ================================================================
    
    units['uk_rifle_section'] = CC2UnitTemplate(
        template_id='uk_rifle_section',
        display_name='British Rifle Section',
        faction=Faction.BRITISH, role=InfantryRole.RIFLE,
        squad_size=10,  # British sections smaller than US squads
        weapon_primary_id='uk_lee_enfield',
        weapon_secondary_id='uk_sten',
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.32,
        vision_range=6,
        deployment_cost=115,
        historical_notes='British airborne section, Lee-Enfields, 10 men'
    )
    
    units['uk_bren_team'] = CC2UnitTemplate(
        template_id='uk_bren_team',
        display_name='Bren Gun Team',
        faction=Faction.BRITISH, role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id='uk_bren',  # Main British LMG
        weapon_secondary_id='uk_sten',
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.26,
        vision_range=5,
        deployment_cost=155,
        historical_notes='Bren gun team, .303 LMG, reliable and accurate'
    )
    
    units['uk_piat_team'] = CC2UnitTemplate(
        template_id='uk_piat_team',
        display_name='PIAT Team',
        faction=Faction.BRITISH, role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id='uk_piat',  # Unique British AT weapon
        weapon_secondary_id='uk_sten',
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.34,
        vision_range=6,
        has_demolitions=True,
        deployment_cost=145,
        historical_notes='PIAT anti-tank team, spring-powered awkward but effective'
    )
    
    units['uk_flame_team'] = CC2UnitTemplate(
        template_id='uk_flame_team',
        display_name='British Flamethrower Team',
        faction=Faction.BRITISH, role=InfantryRole.FLAMETHROWER,
        squad_size=3,
        weapon_primary_id='uk_flamethrower',
        weapon_secondary_id='uk_sten',
        experience_level=1,
        morale_initial=74.0,
        stealth_rating=0.39,
        vision_range=5,
        deployment_cost=165,
        historical_notes='Lifebuoy flamethrower operators'
    )

    units['uk_para_engineer_squad'] = CC2UnitTemplate(
        template_id='uk_para_engineer_squad',
        display_name='Para Engineer Squad',
        faction=Faction.BRITISH, role=InfantryRole.ENGINEER,
        squad_size=8,
        weapon_primary_id='uk_lee_enfield',
        weapon_secondary_id='uk_sten',
        experience_level=2,
        morale_initial=86.0,
        stealth_rating=0.35,
        vision_range=6,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        has_demolitions=True,
        deployment_cost=180,
        max_per_battle=1,
        historical_notes='British Para combat engineers, demolition specialists with airborne training'
    )
    
    units['uk_churchill_mkiv'] = CC2UnitTemplate(
        template_id='uk_churchill_mkiv',
        display_name='Churchill Mk IV/VII',
        faction=Faction.BRITISH, role=VehicleType.TANK_HEAVY,
        squad_size=1,
        weapon_primary_id='qv_75mm',  # 75mm or 95mm CS variant
        weapon_secondary_id='coax_besa',
        vehicle_armor=102,  # Heavily armored!
        vehicle_speed=28,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=88.0,
        stealth_rating=0.12,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=380,
        historical_notes='British heavy infantry tank, very thick armor, slow but tough'
    )
    
    units['uk_cromwell'] = CC2UnitTemplate(
        template_id='uk_cromwell',
        display_name='Cromwell Mk IV/VII',
        faction=Faction.BRITISH, role=VehicleType.TANK_MEDIUM,
        squad_size=1,
        weapon_primary_id='qv_75mm',
        weapon_secondary_id='coax_besa',
        vehicle_armor=76,
        vehicle_speed=64,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.16,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=340,
        historical_notes='Cruiser tank, fast and well-armed, standard XXX Corps issue'
    )
    
    units['uk_firefly'] = CC2UnitTemplate(
        template_id='uk_firefly',
        display_name='Sherman VC Firefly',
        faction=Faction.BRITISH, role=VehicleType.TANK_MEDIUM,
        squad_size=1,
        weapon_primary_id='qf_17pdr',  # *** 17-POUNDER! Best allied AT gun ***
        weapon_secondary_id='coax_besa',
        vehicle_armor=64,
        vehicle_speed=40,
        vehicle_crew=5,
        experience_level=2,
        morale_initial=86.0,
        stealth_rating=0.14,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=400,
        historical_notes='Sherman hull with 17-pdr gun, can kill Tigers/Panthers at range'
    )
    
    units['uk_crocodile'] = CC2UnitTemplate(
        template_id='uk_crocodile',
        display_name='Churchill Crocodile',
        faction=Faction.BRITISH, role=VehicleType.FLAME_TANK,
        squad_size=1,
        weapon_primary_id='qv_75mm',
        vehicle_armor=102,
        vehicle_speed=24,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=85.0,
        stealth_rating=0.11,  # Very conspicuous!
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=450,
        historical_notes='Flamethrower tank, terrifying to infantry, limited fuel'
    )

    units['uk_sherman_dd'] = CC2UnitTemplate(
        template_id='uk_sherman_dd',
        display_name='Sherman DD (Duplex Drive)',
        faction=Faction.BRITISH, role=VehicleType.TANK_MEDIUM,
        squad_size=5,
        weapon_primary_id='qv_75mm',
        weapon_secondary_id='coax_besa',
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
        historical_notes='Amphibious Sherman variant with duplex drive, used during river crossings'
    )
    
    # ================================================================
    # POLISH FORCES (1st Independent Parachute Brigade)
    # ================================================================

    units['pl_para_rifle_squad'] = CC2UnitTemplate(
        template_id='pl_para_rifle_squad',
        display_name='Polish Para Rifle Squad',
        faction=Faction.POLISH, role=InfantryRole.RIFLE,
        squad_size=10,
        weapon_primary_id='pl_enfield_no4',
        weapon_secondary_id='uk_mills_bomb',
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.30,
        vision_range=6,
        can_deploy_in_building=True, can_deploy_in_open=True,
        deployment_cost=100, max_per_battle=4,
        historical_notes='Polish Para Brigade rifle squad, British-equipped, 10 men'
    )

    units['pl_para_mg_squad'] = CC2UnitTemplate(
        template_id='pl_para_mg_squad',
        display_name='Polish Para MG Squad',
        faction=Faction.POLISH, role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id='pl_bren_mk2',
        weapon_secondary_id=None,
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.26,
        vision_range=5,
        can_deploy_in_building=True, can_deploy_in_open=True,
        deployment_cost=150, max_per_battle=2,
        historical_notes='Polish Para BREN gun team, British-issue BREN Mk.II'
    )

    units['pl_para_at_squad'] = CC2UnitTemplate(
        template_id='pl_para_at_squad',
        display_name='Polish Para AT Squad',
        faction=Faction.POLISH, role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id='pl_piat',
        weapon_secondary_id=None,
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.34,
        vision_range=6,
        can_deploy_in_building=True, can_deploy_in_open=True,
        deployment_cost=200, max_per_battle=2,
        historical_notes='Polish Para PIAT anti-tank team'
    )

    units['pl_para_engineer_squad'] = CC2UnitTemplate(
        template_id='pl_para_engineer_squad',
        display_name='Polish Para Engineer Squad',
        faction=Faction.POLISH, role=InfantryRole.ENGINEER,
        squad_size=8,
        weapon_primary_id='pl_enfield_no4',
        weapon_secondary_id='uk_mills_bomb',
        experience_level=1,
        morale_initial=81.0,
        stealth_rating=0.38,
        vision_range=6,
        can_deploy_in_building=True, can_deploy_in_open=True,
        has_demolitions=True,
        deployment_cost=180, max_per_battle=1,
        historical_notes='Polish Para combat engineers, demolitions and fortifications'
    )

    # ================================================================
    # GERMAN FORCES (15th Army / SS Panzer Divisions)
    # ================================================================
    
    units['de_rifle_squad'] = CC2UnitTemplate(
        template_id='de_rifle_squad',
        display_name='German Rifle Squad (Grenadier)',
        faction=Faction.GERMAN, role=InfantryRole.RIFLE,
        squad_size=10,
        weapon_primary_id='de_kar98k',
        weapon_secondary_id='de_mp40',
        experience_level=1,
        morale_initial=85.0,
        stealth_rating=0.30,
        vision_range=6,
        deployment_cost=125,
        historical_notes='Standard Wehrmacht Grenadier squad, Kar98k rifles'
    )
    
    units['de_ss_squad'] = CC2UnitTemplate(
        template_id='de_ss_squad',
        display_name='SS Panzergrenadier Squad',
        faction=Faction.GERMAN, role=InfantryRole.RIFLE,
        squad_size=11,
        weapon_primary_id='de_mp44',  # StG 44 assault rifles!
        weapon_secondary_id='de_mp40',
        experience_level=2,
        morale_initial=92.0,
        is_fanatic=True,  # *** SS FANATIC UNIT - NEVER PANICS! ***
        stealth_rating=0.28,
        vision_range=6,
        deployment_cost=165,
        historical_notes='Elite SS Panzergrenadiers, StG 44 rifles, fanatical morale'
    )

    units['de_ss_panzergrenadier'] = CC2UnitTemplate(
        template_id='de_ss_panzergrenadier',
        display_name='SS Panzergrenadiere',
        faction=Faction.GERMAN, role=InfantryRole.HEAVY_ASSAULT,
        squad_size=12,
        weapon_primary_id='de_kar98k',
        weapon_secondary_id='de_mg42',
        experience_level=3,
        morale_initial=95.0,
        is_fanatic=True,
        stealth_rating=0.27,
        vision_range=6,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        deployment_cost=130,
        max_per_battle=3,
        historical_notes='Elite SS troops with Kar98k and MG42, higher morale and fanatical resolve'
    )

    units['de_reservist_squad'] = CC2UnitTemplate(
        template_id='de_reservist_squad',
        display_name='Reservisten Squad',
        faction=Faction.GERMAN, role=InfantryRole.RIFLE,
        squad_size=8,
        weapon_primary_id='de_kar98k',
        weapon_secondary_id=None,
        experience_level=0,
        morale_initial=55.0,
        stealth_rating=0.30,
        vision_range=5,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        deployment_cost=60,
        max_per_battle=4,
        historical_notes='Poor quality reservist troops, low morale and minimal equipment'
    )
    
    units['de_mg42_team'] = CC2UnitTemplate(  # *** THE LEGENDARY MG42 ***
        template_id='de_mg42_team',
        display_name='MG42 Machine Gun Team',
        faction=Faction.GERMAN, role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id='de_mg42',  # *** HITLER'S SAW - SUPPRESSION 0.90 ***
        weapon_secondary_id='de_mp40',
        experience_level=1,
        morale_initial=83.0,
        stealth_rating=0.24,
        vision_range=5,
        deployment_cost=175,
        historical_notes='MG42 team - most feared German weapon, 1200 RPM, devastating suppression'
    )
    
    units['de_mg34_team'] = CC2UnitTemplate(  # *** MG34 - EARLIER VARIANT ***
        template_id='de_mg34_team',
        display_name='MG34 Machine Gun Team',
        faction=Faction.GERMAN, role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id='de_mg34',  # Earlier universal MG
        weapon_secondary_id='de_kar98k',
        experience_level=1,
        morale_initial=81.0,
        stealth_rating=0.26,
        vision_range=5,
        deployment_cost=150,
        historical_notes='MG34 team - still widely used alongside MG42'
    )
    
    units['de_panzerschreck_team'] = CC2UnitTemplate(
        template_id='de_panzerschreck_team',
        display_name='Panzerschreck Team',
        faction=Faction.GERMAN, role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id='de_panzerschreck',  # 88mm RPzB
        weapon_secondary_id='de_mp40',
        experience_level=1,
        morale_initial=79.0,
        stealth_rating=0.33,
        vision_range=6,
        has_demolitions=True,
        deployment_cost=155,
        historical_notes='88mm rocket AT team, copied from Bazooka but improved'
    )
    
    units['de_panzerfaust_team'] = CC2UnitTemplate(
        template_id='de_panzerfaust_team',
        display_name='Panzerfaust Team',
        faction=Faction.GERMAN, role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id='de_panzerfaust',  # Disposable one-shot
        weapon_secondary_id='de_kar98k',
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.36,
        vision_range=5,
        deployment_cost=120,  # Cheaper (disposable weapon)
        historical_notes='Disposable Panzerfaust team, cheap and numerous late-war'
    )
    
    units['de_flame_team'] = CC2UnitTemplate(
        template_id='de_flame_team',
        display_name='Flammenwerfer Team',
        faction=Faction.GERMAN, role=InfantryRole.FLAMETHROWER,
        squad_size=3,
        weapon_primary_id='de_flammenwerfer_41',
        weapon_secondary_id='de_mp40',
        experience_level=1,
        morale_initial=73.0,
        stealth_rating=0.38,
        vision_range=5,
        deployment_cost=168,
        historical_notes='German flamethrower operators'
    )

    units['de_flamethrower_squad'] = CC2UnitTemplate(
        template_id='de_flamethrower_squad',
        display_name='Flamethrower Squad',
        faction=Faction.GERMAN, role=InfantryRole.ENGINEER,
        squad_size=4,
        weapon_primary_id='de_flammenwerfer',
        weapon_secondary_id=None,
        experience_level=1,
        morale_initial=72.0,
        stealth_rating=0.36,
        vision_range=5,
        can_deploy_in_building=True,
        can_deploy_in_open=True,
        deployment_cost=200,
        max_per_battle=1,
        historical_notes='German flamethrower assault squad, devastating vs infantry in buildings'
    )
    
    units['de_grw50_team'] = CC2UnitTemplate(  # *** LIGHT MORTAR ***
        template_id='de_grw50_team',
        display_name='GrW 36 50mm Mortar Team',
        faction=Faction.GERMAN, role=InfantryRole.RIFLE,
        squad_size=3,
        weapon_primary_id='de_grw36_50mm',
        weapon_secondary_id='de_kar98k',
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.34,
        vision_range=6,
        can_capture=False,
        deployment_cost=135,
        historical_notes='Light 50mm platoon mortar team'
    )
    
    units['de_grw81_team'] = CC2UnitTemplate(  # *** HEAVY MORTAR ***
        template_id='de_grw81_team',
        display_name='GrW 34 81mm Mortar Team',
        faction=Faction.GERMAN, role=InfantryRole.RIFLE,
        squad_size=4,
        weapon_primary_id='de_grw34_81mm',
        weapon_secondary_id='de_mp40',
        experience_level=1,
        morale_initial=76.0,
        stealth_rating=0.31,
        vision_range=5,
        can_capture=False,
        deployment_cost=170,
        historical_notes='Medium 81mm battalion mortar team'
    )
    
    # --- GERMAN ARMOR ---
    
    units['de_panzer_iv'] = CC2UnitTemplate(
        template_id='de_panzer_iv',
        display_name='Panzer IV Ausf H/J',
        faction=Faction.GERMAN, role=VehicleType.TANK_MEDIUM,
        squad_size=1,
        weapon_primary_id='kwk40_75mm',  # Long-barrel 75mm
        weapon_secondary_id='coax_mg34',
        vehicle_armor=80,
        vehicle_speed=40,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=87.0,
        stealth_rating=0.14,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=360,
        historical_notes='Main German medium tank, excellent all-around, long 75mm KwK 40 L/48'
    )
    
    units['de_tiger_i'] = CC2UnitTemplate(  # *** THE TIGER I ***
        template_id='de_tiger_i',
        display_name='Tiger I E',
        faction=Faction.GERMAN, role=VehicleType.TANK_HEAVY,
        squad_size=1,
        weapon_primary_id='kwk36_88mm',  # *** 88MM KWK 36 - DEVASTATING ***
        weapon_secondary_id='coax_mg34',
        vehicle_armor=100,
        vehicle_speed=38,
        vehicle_crew=5,
        experience_level=2,
        morale_initial=95.0,
        stealth_rating=0.10,  # Very loud and big!
        vision_range=8,
        can_deploy_in_building=False,
        deployment_cost=550,
        historical_notes='Tiger I heavy tank - 88mm gun, 100mm armor, terror weapon, rare but deadly'
    )
    
    units['de_panther'] = CC2UnitTemplate(  # *** THE PANTHER ***
        template_id='de_panther',
        display_name='Panther D/A/G',
        faction=Faction.GERMAN, role=VehicleType.TANK_HEAVY,
        squad_size=1,
        weapon_primary_id='kwk42_75mm',  # High-velocity 75mm L/70
        weapon_secondary_id='coax_mg34',
        vehicle_armor=120,  # Sloped armor!
        vehicle_speed=46,
        vehicle_crew=5,
        experience_level=2,
        morale_initial=92.0,
        stealth_rating=0.12,
        vision_range=8,
        can_deploy_in_building=False,
        deployment_cost=500,
        historical_notes='Panther - best German medium/heavy hybrid, excellent gun and armor'
    )
    
    units['de_stug_iii'] = CC2UnitTemplate(  # *** STURMGESCHÜTZ III ***
        template_id='de_stug_iii',
        display_name='StuG III G',
        faction=Faction.GERMAN, role=VehicleType.TANK_DESTROYER,
        squad_size=1,
        weapon_primary_id='kwk40_75mm',  # Same gun as PzIV
        vehicle_armor=80,
        vehicle_speed=40,
        vehicle_crew=4,
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.14,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=340,
        historical_notes='Assault gun - no turret, low profile, excellent ambush weapon'
    )

    units['de_flammpanzer'] = CC2UnitTemplate(
        template_id='de_flammpanzer',
        display_name='Flammpanzer III',
        faction=Faction.GERMAN, role=VehicleType.FLAME_TANK,
        squad_size=3,
        weapon_primary_id='de_flammenwerfer',
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
        historical_notes='Flame tank variant of Panzer III, devastating vs infantry and fortifications'
    )
    
    units['de_sdkfz_251'] = CC2UnitTemplate(
        template_id='de_sdkfz_251',
        display_name='SdKfz 251/1 Half-track',
        faction=Faction.GERMAN, role=VehicleType.HALFTRACK,
        squad_size=2,
        weapon_primary_id='coax_mg34',
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
        historical_notes='German halftrack, transports Panzergrenadiers'
    )

    # ================================================================
    # ANTI-TANK GUN TEAMS (Fixed AT artillery)
    # ================================================================

    units['uk_6pdr_at_gun'] = CC2UnitTemplate(
        template_id='uk_6pdr_at_gun',
        display_name='6-pounder AT Gun',
        faction=Faction.BRITISH, role=InfantryRole.ANTI_TANK,
        squad_size=4,
        weapon_primary_id='uk_6pdr', weapon_secondary_id=None,
        can_deploy_in_building=False, can_deploy_in_open=True,
        deployment_cost=250, max_per_battle=2
    )

    units['de_pak40_at_gun'] = CC2UnitTemplate(
        template_id='de_pak40_at_gun',
        display_name='7.5cm Pak 40 AT Gun',
        faction=Faction.GERMAN, role=InfantryRole.ANTI_TANK,
        squad_size=4,
        weapon_primary_id='de_pak40', weapon_secondary_id=None,
        can_deploy_in_building=False, can_deploy_in_open=True,
        deployment_cost=280, max_per_battle=2
    )

    units['us_m1_57mm_at_gun'] = CC2UnitTemplate(
        template_id='us_m1_57mm_at_gun',
        display_name='M1 57mm AT Gun',
        faction=Faction.AMERICAN, role=InfantryRole.ANTI_TANK,
        squad_size=4,
        weapon_primary_id='us_m1_57mm', weapon_secondary_id=None,
        can_deploy_in_building=False, can_deploy_in_open=True,
        deployment_cost=240, max_per_battle=2
    )

    # ================================================================
    # EXPANDED ROSTER UNITS
    # ================================================================

    # --- BRITISH PARA UNITS ---

    units['uk_para_mortar_squad'] = CC2UnitTemplate(
        template_id='uk_para_mortar_squad',
        display_name='British Para 3-inch Mortar Squad',
        faction=Faction.BRITISH, role=InfantryRole.MORTAR,
        squad_size=5,
        weapon_primary_id='uk_3inch_mortar',
        weapon_secondary_id='uk_sten',
        experience_level=1,
        morale_initial=78.0,
        stealth_rating=0.28,
        vision_range=5,
        can_capture=False,
        deployment_cost=200, max_per_battle=2,
        historical_notes='British Para mortar squad with 3-inch mortar, indirect fire support'
    )

    units['uk_para_officer'] = CC2UnitTemplate(
        template_id='uk_para_officer',
        display_name='British Para Officer',
        faction=Faction.BRITISH, role=InfantryRole.OFFICER,
        squad_size=3,
        weapon_primary_id='uk_officer_sten',
        weapon_secondary_id='uk_lee_enfield',
        experience_level=2,
        morale_initial=92.0,
        stealth_rating=0.35,
        vision_range=7,
        is_command_unit=True,
        can_capture=False,
        deployment_cost=150, max_per_battle=1,
        historical_notes='British Para officer, provides morale bonus to nearby units'
    )

    units['uk_para_sniper'] = CC2UnitTemplate(
        template_id='uk_para_sniper',
        display_name='British Para Sniper Team',
        faction=Faction.BRITISH, role=InfantryRole.SNIPER,
        squad_size=2,
        weapon_primary_id='uk_sniper_no4',
        experience_level=3,
        morale_initial=80.0,
        stealth_rating=0.65,
        vision_range=12,
        can_capture=False,
        deployment_cost=180, max_per_battle=1,
        historical_notes='British Para sniper team with scoped Lee-Enfield No.4(T)'
    )

    units['uk_para_recon'] = CC2UnitTemplate(
        template_id='uk_para_recon',
        display_name='British Para Recon Team',
        faction=Faction.BRITISH, role=InfantryRole.RECON,
        squad_size=4,
        weapon_primary_id='uk_enfield_no4',
        weapon_secondary_id='uk_sten',
        experience_level=2,
        morale_initial=83.0,
        stealth_rating=0.50,
        vision_range=9,
        deployment_cost=120, max_per_battle=1,
        historical_notes='British Para reconnaissance team, small fast unit with good vision'
    )

    # --- US EXPANDED UNITS ---

    units['us_ranger_squad'] = CC2UnitTemplate(
        template_id='us_ranger_squad',
        display_name='US Ranger Squad',
        faction=Faction.AMERICAN, role=InfantryRole.HEAVY_ASSAULT,
        squad_size=12,
        weapon_primary_id='us_m1_garand',
        weapon_secondary_id='us_browning_bar',
        experience_level=2,
        morale_initial=88.0,
        stealth_rating=0.30,
        vision_range=6,
        deployment_cost=130, max_per_battle=2,
        historical_notes='Elite US Ranger squad, Garands and BAR, heavy assault specialists'
    )

    units['us_mortar_squad'] = CC2UnitTemplate(
        template_id='us_mortar_squad',
        display_name='US 60mm Mortar Squad',
        faction=Faction.AMERICAN, role=InfantryRole.MORTAR,
        squad_size=5,
        weapon_primary_id='us_60mm_mortar',
        weapon_secondary_id='us_m1_carbine',
        experience_level=1,
        morale_initial=79.0,
        stealth_rating=0.30,
        vision_range=5,
        can_capture=False,
        deployment_cost=180, max_per_battle=2,
        historical_notes='US 60mm mortar squad, company-level indirect fire support'
    )

    units['us_at_squad_bazooka'] = CC2UnitTemplate(
        template_id='us_at_squad_bazooka',
        display_name='US Bazooka Team',
        faction=Faction.AMERICAN, role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id='us_bazooka',
        weapon_secondary_id='us_m1_carbine',
        experience_level=1,
        morale_initial=78.0,
        stealth_rating=0.35,
        vision_range=6,
        has_demolitions=True,
        deployment_cost=190, max_per_battle=2,
        historical_notes='US bazooka anti-tank team, M1A1 Bazooka vs enemy armor'
    )

    units['us_mg_squad'] = CC2UnitTemplate(
        template_id='us_mg_squad',
        display_name='US .30cal MG Squad',
        faction=Faction.AMERICAN, role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id='us_browning_30cal',
        weapon_secondary_id='us_m1_carbine',
        experience_level=1,
        morale_initial=80.0,
        stealth_rating=0.25,
        vision_range=5,
        deployment_cost=150, max_per_battle=2,
        historical_notes='US .30 cal machine gun squad, excellent suppression capability'
    )

    # --- GERMAN EXPANDED UNITS ---

    units['de_mortar_squad'] = CC2UnitTemplate(
        template_id='de_mortar_squad',
        display_name='German 81mm Mortar Squad',
        faction=Faction.GERMAN, role=InfantryRole.MORTAR,
        squad_size=5,
        weapon_primary_id='de_81mm_mortar',
        weapon_secondary_id='de_kar98k',
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.30,
        vision_range=5,
        can_capture=False,
        deployment_cost=190, max_per_battle=2,
        historical_notes='German 81mm mortar squad, GrW 34 battalion-level indirect fire'
    )

    units['de_panzergrenadier_mg'] = CC2UnitTemplate(
        template_id='de_panzergrenadier_mg',
        display_name='German Panzergrenadier MG Squad',
        faction=Faction.GERMAN, role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id='de_mg42',
        weapon_secondary_id='de_mp40',
        experience_level=1,
        morale_initial=83.0,
        stealth_rating=0.24,
        vision_range=5,
        deployment_cost=160, max_per_battle=2,
        historical_notes='Panzergrenadier MG squad with MG42, devastating suppression'
    )

    units['de_officer'] = CC2UnitTemplate(
        template_id='de_officer',
        display_name='German Officer',
        faction=Faction.GERMAN, role=InfantryRole.OFFICER,
        squad_size=3,
        weapon_primary_id='de_officer_p08',
        weapon_secondary_id='de_mp40',
        experience_level=2,
        morale_initial=90.0,
        stealth_rating=0.35,
        vision_range=7,
        is_command_unit=True,
        can_capture=False,
        deployment_cost=140, max_per_battle=1,
        historical_notes='German officer with Luger P08, provides morale bonus to nearby units'
    )

    units['de_sniper_team'] = CC2UnitTemplate(
        template_id='de_sniper_team',
        display_name='German Sniper Team',
        faction=Faction.GERMAN, role=InfantryRole.SNIPER,
        squad_size=2,
        weapon_primary_id='de_kar98k_sniper',
        experience_level=3,
        morale_initial=80.0,
        stealth_rating=0.65,
        vision_range=12,
        can_capture=False,
        deployment_cost=170, max_per_battle=1,
        historical_notes='German sniper team with scoped Kar98k ZF39'
    )

    units['de_recon_team'] = CC2UnitTemplate(
        template_id='de_recon_team',
        display_name='German Recon Team',
        faction=Faction.GERMAN, role=InfantryRole.RECON,
        squad_size=4,
        weapon_primary_id='de_kar98k',
        weapon_secondary_id='de_mp40',
        experience_level=2,
        morale_initial=82.0,
        stealth_rating=0.48,
        vision_range=9,
        deployment_cost=110, max_per_battle=1,
        historical_notes='German reconnaissance team, small fast unit with good vision'
    )

    units['de_panzerfaust60_team'] = CC2UnitTemplate(
        template_id='de_panzerfaust60_team',
        display_name='German Panzerfaust 60 Team',
        faction=Faction.GERMAN, role=InfantryRole.ANTI_TANK,
        squad_size=3,
        weapon_primary_id='de_panzerfaust60',
        weapon_secondary_id='de_kar98k',
        experience_level=1,
        morale_initial=77.0,
        stealth_rating=0.36,
        vision_range=5,
        deployment_cost=160, max_per_battle=3,
        historical_notes='Panzerfaust 60 team, improved 60m range disposable AT weapon'
    )

    units['de_fallschirmjager'] = CC2UnitTemplate(
        template_id='de_fallschirmjager',
        display_name='German Fallschirmjäger Squad',
        faction=Faction.GERMAN, role=InfantryRole.RIFLE,
        squad_size=10,
        weapon_primary_id='de_fg42',
        weapon_secondary_id='de_mp40',
        experience_level=2,
        morale_initial=88.0,
        stealth_rating=0.32,
        vision_range=6,
        deployment_cost=120, max_per_battle=2,
        historical_notes='Elite German paratrooper squad with FG42 automatic rifles'
    )

    units['de_fallschirmjager_mg'] = CC2UnitTemplate(
        template_id='de_fallschirmjager_mg',
        display_name='Fallschirmjäger MG Squad',
        faction=Faction.GERMAN, role=InfantryRole.MACHINE_GUN,
        squad_size=4,
        weapon_primary_id='de_mg42',
        weapon_secondary_id='de_fg42',
        experience_level=2,
        morale_initial=86.0,
        stealth_rating=0.25,
        vision_range=5,
        deployment_cost=160, max_per_battle=1,
        historical_notes='Fallschirmjäger MG squad with MG42, elite airborne support'
    )

    units['de_assault_pioneer'] = CC2UnitTemplate(
        template_id='de_assault_pioneer',
        display_name='German Assault Pioneer',
        faction=Faction.GERMAN, role=InfantryRole.ENGINEER,
        squad_size=8,
        weapon_primary_id='de_kar98k',
        weapon_secondary_id='de_flammenwerfer',
        experience_level=2,
        morale_initial=82.0,
        stealth_rating=0.35,
        vision_range=6,
        has_demolitions=True,
        deployment_cost=200, max_per_battle=1,
        historical_notes='German assault pioneers, demolition and flamethrower specialists'
    )

    # --- GERMAN ARMOR EXPANDED ---

    units['de_pziv_h'] = CC2UnitTemplate(
        template_id='de_pziv_h',
        display_name='Panzer IV Ausf. H',
        faction=Faction.GERMAN, role=VehicleType.TANK_MEDIUM,
        squad_size=5,
        weapon_primary_id='de_75mm_kwk40',
        weapon_secondary_id='coax_mg34',
        vehicle_armor=80,
        vehicle_speed=40,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=87.0,
        stealth_rating=0.14,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=320, max_per_battle=2,
        historical_notes='Panzer IV Ausf. H, improved armor and KwK 40 L/48 gun'
    )

    units['de_stug_iii_g'] = CC2UnitTemplate(
        template_id='de_stug_iii_g',
        display_name='StuG III Ausf. G',
        faction=Faction.GERMAN, role=VehicleType.TANK_DESTROYER,
        squad_size=4,
        weapon_primary_id='de_75mm_stug',
        weapon_secondary_id='coax_mg34',
        vehicle_armor=80,
        vehicle_speed=40,
        vehicle_crew=4,
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.16,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=280, max_per_battle=2,
        historical_notes='StuG III Ausf. G assault gun, low profile, excellent ambush weapon'
    )

    units['de_sdkfz_222'] = CC2UnitTemplate(
        template_id='de_sdkfz_222',
        display_name='SdKfz 222 Armored Car',
        faction=Faction.GERMAN, role=VehicleType.ARMORED_CAR,
        squad_size=3,
        weapon_primary_id='de_mg34_vehicle',
        weapon_secondary_id=None,
        vehicle_armor=30,
        vehicle_speed=80,
        vehicle_crew=3,
        experience_level=1,
        morale_initial=80.0,
        stealth_rating=0.20,
        vision_range=9,
        can_deploy_in_building=False,
        deployment_cost=140, max_per_battle=2,
        historical_notes='Light armored car, fast recon vehicle with MG34'
    )

    units['de_hummel'] = CC2UnitTemplate(
        template_id='de_hummel',
        display_name='Hummel SPG',
        faction=Faction.GERMAN, role=VehicleType.SP_ARTILLERY,
        squad_size=5,
        weapon_primary_id='de_150mm_hummel',
        weapon_secondary_id='coax_mg34',
        vehicle_armor=50,
        vehicle_speed=42,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.12,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=380, max_per_battle=1,
        historical_notes='Hummel self-propelled gun, 150mm howitzer, devastating indirect fire'
    )

    # --- BRITISH ARMOR EXPANDED ---

    units['uk_cromwell_tank'] = CC2UnitTemplate(
        template_id='uk_cromwell_tank',
        display_name='Cromwell Tank',
        faction=Faction.BRITISH, role=VehicleType.TANK_MEDIUM,
        squad_size=5,
        weapon_primary_id='uk_75mm_cromwell',
        weapon_secondary_id='coax_besa',
        vehicle_armor=76,
        vehicle_speed=64,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.16,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=300, max_per_battle=2,
        historical_notes='Cromwell cruiser tank, fast and well-armed, XXX Corps standard'
    )

    units['uk_carrier'] = CC2UnitTemplate(
        template_id='uk_carrier',
        display_name='Universal Carrier',
        faction=Faction.BRITISH, role=VehicleType.HALFTRACK,
        squad_size=2,
        weapon_primary_id='uk_bren',
        weapon_secondary_id=None,
        vehicle_armor=12,
        vehicle_speed=48,
        vehicle_crew=2,
        experience_level=1,
        morale_initial=80.0,
        stealth_rating=0.20,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=120, max_per_battle=3,
        historical_notes='Universal Carrier (Bren Carrier), light tracked transport with Bren gun'
    )

    # --- US ARMOR EXPANDED ---

    units['us_m3_halftrack'] = CC2UnitTemplate(
        template_id='us_m3_halftrack',
        display_name='M3 Half-track',
        faction=Faction.AMERICAN, role=VehicleType.HALFTRACK,
        squad_size=2,
        weapon_primary_id='us_m2hb_50cal',
        weapon_secondary_id=None,
        vehicle_armor=13,
        vehicle_speed=72,
        vehicle_crew=2,
        experience_level=1,
        morale_initial=82.0,
        stealth_rating=0.18,
        vision_range=6,
        can_deploy_in_building=False,
        deployment_cost=160, max_per_battle=2,
        historical_notes='M3 half-track with .50 cal HMG, infantry transport and fire support'
    )

    units['us_sherman_76'] = CC2UnitTemplate(
        template_id='us_sherman_76',
        display_name='Sherman 76mm',
        faction=Faction.AMERICAN, role=VehicleType.TANK_MEDIUM,
        squad_size=5,
        weapon_primary_id='us_76mm_sherman',
        weapon_secondary_id='coax_30cal',
        vehicle_armor=64,
        vehicle_speed=40,
        vehicle_crew=5,
        experience_level=1,
        morale_initial=84.0,
        stealth_rating=0.14,
        vision_range=7,
        can_deploy_in_building=False,
        deployment_cost=350, max_per_battle=1,
        historical_notes='Sherman with 76mm gun, improved anti-tank performance over 75mm'
    )

    # --- POLISH EXPANDED UNITS ---

    units['pl_para_mortar_squad'] = CC2UnitTemplate(
        template_id='pl_para_mortar_squad',
        display_name='Polish Para Mortar Squad',
        faction=Faction.POLISH, role=InfantryRole.MORTAR,
        squad_size=5,
        weapon_primary_id='uk_3inch_mortar',
        weapon_secondary_id='uk_sten',
        experience_level=1,
        morale_initial=78.0,
        stealth_rating=0.28,
        vision_range=5,
        can_capture=False,
        deployment_cost=200, max_per_battle=1,
        historical_notes='Polish Para mortar squad with British 3-inch mortar'
    )

    units['pl_para_officer'] = CC2UnitTemplate(
        template_id='pl_para_officer',
        display_name='Polish Para Officer',
        faction=Faction.POLISH, role=InfantryRole.OFFICER,
        squad_size=3,
        weapon_primary_id='uk_officer_sten',
        weapon_secondary_id='pl_enfield_no4',
        experience_level=2,
        morale_initial=90.0,
        stealth_rating=0.35,
        vision_range=7,
        is_command_unit=True,
        can_capture=False,
        deployment_cost=150, max_per_battle=1,
        historical_notes='Polish Para officer with STEN Mk.V, provides morale bonus'
    )

    # Total count: 80+ unique unit templates covering all CC2 roles

    return units


# Global instance
CC2_UNITS: dict[str, CC2UnitTemplate] = {}


def get_cc2_units() -> dict[str, CC2UnitTemplate]:
    """Lazy-initialize and return unit database."""
    global CC2_UNITS
    if not CC2_UNITS:
        CC2_UNITS = build_cc2_unit_database()
    return CC2_UNITS


def get_units_for_faction(faction: Faction) -> list[CC2UnitTemplate]:
    """Get all unit templates available to a faction."""
    db = get_cc2_units()
    return [u for u in db.values() if u.faction == faction]


def get_units_by_role(role: InfantryRole | VehicleType) -> list[CC2UnitTemplate]:
    """Get all units matching a specific role."""
    db = get_cc2_units()
    return [u for u in db.values() if u.role == role]


# ========================================================================
# DEPLOYMENT PHASE SYSTEM
# ========================================================================

class ZoneType(Enum):
    """CC2 map zone types during deployment."""
    FRIENDLY = auto()      # Clear shading - player can deploy here
    NO_MANS_LAND = auto()  # Light gray - contested area
    ENEMY_CONTROLLED = auto()  # Dark gray - enemy territory


@dataclass
class TileZone:
    """Zone assignment for a single tile during deployment."""
    x: int
    y: int
    zone: ZoneType


@dataclass
class DeploymentConfig:
    """
    Configuration for a battle's deployment phase.
    
    Defines where each side can place their units.
    """
    map_width: int
    map_height: int
    
    # Zone assignments per tile (indexed by [y][x])
    ally_zones: list[list[ZoneType]]
    axis_zones: list[list[ZoneType]]
    
    # Deployment constraints
    max_infantry: int = 9          # Max infantry units (CC2 default)
    max_support: int = 6           # Max support units (vehicles/mortars/MGs)
    max_total: int = 15            # Absolute maximum
    
    # Time limit for deployment (seconds)
    time_limit: int = 300          # 5 minutes default
    
    def can_deploy_at(self, x: int, y: int, faction: Faction) -> bool:
        """Check if a tile is legal for deployment by given faction."""
        if not (0 <= x < self.map_width and 0 <= y < self.map_height):
            return False
        
        zones = self.ally_zones if faction in [Faction.AMERICAN, Faction.BRITISH, Faction.POLISH] else self.axis_zones
        return zones[y][x] == ZoneType.FRIENDLY


class DeploymentPhase:
    """
    Manages the pre-battle deployment phase.
    
    Implements CC2's drag-and-drop unit placement system.
    """
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.deployed_units: dict[Faction, list[tuple[int, int, str]]] = {
            faction: [] for faction in Faction
        }
        self.is_complete: bool = False
        self.current_faction: Faction | None = None
    
    def start_deployment(self, faction: Faction) -> None:
        """Begin deployment for a specific faction."""
        self.current_faction = faction
        self.deployed_units[faction] = []
        self.is_complete = False
    
    def place_unit(self, unit_template_id: str, x: int, y: int) -> bool:
        """
        Attempt to place a unit at specified position.
        
        Returns True if placement succeeded.
        """
        if not self.current_faction:
            return False
        
        # Check zone legality
        if not self.config.can_deploy_at(x, y, self.current_faction):
            return False
        
        # Check unit limits
        current_count = len(self.deployed_units[self.current_faction])
        if current_count >= self.config.max_total:
            return False
        
        # Get unit type to check infantry/support limits
        unit_db = get_cc2_units()
        unit = unit_db.get(unit_template_id)
        if not unit:
            return False
        
        # Count current infantry vs support
        infantry_count = sum(
            1 for _, _, tid in self.deployed_units[self.current_faction]
            if tid in unit_db and unit_db[tid].role in [r for r in InfantryRole]
        )
        support_count = current_count - infantry_count
        
        is_infantry = unit.role in [r for r in InfantryRole]
        
        if is_infantry and infantry_count >= self.config.max_infantry:
            return False
        if not is_infantry and support_count >= self.config.max_support:
            return False
        
        # Check terrain legality (no tanks in buildings, etc.)
        # This would need map data integration
        
        # Place the unit
        self.deployed_units[self.current_faction].append((x, y, unit_template_id))
        return True
    
    def remove_unit(self, index: int) -> bool:
        """Remove a previously placed unit."""
        if not self.current_faction:
            return False
        
        if 0 <= index < len(self.deployed_units[self.current_faction]):
            self.deployed_units[self.current_faction].pop(index)
            return True
        return False
    
    def confirm_deployment(self) -> bool:
        """Confirm and lock in deployment."""
        if not self.current_faction:
            return False
        
        self.is_complete = True
        return True
    
    def get_deployed_positions(self, faction: Faction) -> list[tuple[int, int, str]]:
        """Return all deployed unit positions for a faction."""
        return self.deployed_units.get(faction, [])
    
    def generate_zone_map_for_display(self, faction: Faction) -> list[list[int]]:
        """
        Generate numeric zone map for rendering.
        
        Returns 2D array: 0=friendly, 1=no mans land, 2=enemy
        """
        zones = self.config.ally_zones if faction in [Faction.AMERICAN, Faction.BRITISH, Faction.POLISH] else self.config.axis_zones
        
        zone_map = []
        for row in zones:
            numeric_row = []
            for z in row:
                if z == ZoneType.FRIENDLY:
                    numeric_row.append(0)
                elif z == ZoneType.NO_MANS_LAND:
                    numeric_row.append(1)
                else:
                    numeric_row.append(2)
            zone_map.append(numeric_row)
        
        return zone_map


def create_default_deployment_config(map_width: int, map_height: int) -> DeploymentConfig:
    """
    Create a standard split-map deployment configuration.
    
    Default: Allies get left third, Axis gets right third, middle is no-man's-land.
    """
    ally_zones = [[ZoneType.NO_MANS_LAND for _ in range(map_width)] for _ in range(map_height)]
    axis_zones = [[ZoneType.NO_MANS_LAND for _ in range(map_width)] for _ in range(map_height)]
    
    third = map_width // 3
    
    for y in range(map_height):
        for x in range(map_width):
            if x < third - 1:
                ally_zones[y][x] = ZoneType.FRIENDLY
            elif x >= map_width - third + 1:
                axis_zones[y][x] = ZoneType.FRIENDLY
    
    return DeploymentConfig(
        map_width=map_width,
        map_height=map_height,
        ally_zones=ally_zones,
        axis_zones=axis_zones,
        max_infantry=9,
        max_support=6,
        max_total=15
    )


# Demo
if __name__ == '__main__':
    logger.debug("=" * 90)
    logger.debug("🎖️  CLOSE COMBAT 2 - AUTHENTIC UNIT DATABASE & DEPLOYMENT SYSTEM")
    logger.debug("=" * 90)
    logger.debug("")

    # Show unit counts
    db = get_cc2_units()
    logger.debug("📊 TOTAL UNIT TEMPLATES: %s", len(db))
    logger.debug("")
    
    for faction in Faction:
        units = get_units_for_faction(faction)
        inf_count = sum(1 for u in units if isinstance(u.role, InfantryRole))
        veh_count = sum(1 for u in units if isinstance(u.role, VehicleType))
        
        logger.debug("─" * 70)
        logger.debug("🏴 %s (%s units: %s infantry + %s vehicles)",
                     faction.name, len(units), inf_count, veh_count)
        logger.debug("─" * 70)
        
        for u in sorted(units, key=lambda x: (type(x.role).__name__, x.template_id)):
            weapon = u.get_weapon()
            wname = weapon.name if weapon else 'N/A'
            suppr_icon = '💥' if weapon and weapon.suppress_power > 0.7 else ''
            fanatic_icon = '😤' if u.is_fanatic else ''
            cmd_icon = '⭐' if u.is_command_unit else ''
            
            logger.debug(
                "  [%s] %s | %d men | %s | Exp:%s %s%s%s",
                u.role.name, u.display_name, u.squad_size, wname,
                u.experience_level, suppr_icon, fanatic_icon, cmd_icon)
        logger.debug("")
    
    # Demonstrate deployment system
    logger.debug("=" * 90)
    logger.debug("🗺️  DEPLOYMENT PHASE DEMO")
    logger.debug("=" * 90)
    
    config = create_default_deployment_config(50, 42)  # Arnhem-sized map
    deployment = DeploymentPhase(config)
    
    deployment.start_deployment(Faction.AMERICAN)
    
    test_placements = [
        ('us_rifle_squad', 5, 20),
        ('us_machine_gun_team_a4', 6, 21),
        ('us_at_team', 4, 19),
        ('us_mortar_light_team', 7, 22),
        ('us_officer', 5, 21),
    ]
    
    logger.debug("\n📍 Placing American units on 50×42 map...")
    for uid, x, y in test_placements:
        success = deployment.place_unit(uid, x, y)
        status = '✅' if success else '❌'
        logger.debug("   %s %s → (%s, %s)", status, uid, x, y)

    logger.debug("\n📦 Deployed %s units",
                 len(deployment.get_deployed_positions(Faction.AMERICAN)))
    logger.debug("\n✅ System ready for integration!")
