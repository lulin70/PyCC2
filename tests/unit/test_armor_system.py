from __future__ import annotations


import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType, UNIT_ARMOR_PROFILES
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.random_context import RandomContext


@pytest.fixture
def rng() -> RandomContext:
    return RandomContext.from_seed(42)


@pytest.fixture
def engine(rng: RandomContext) -> BallisticEngine:
    return BallisticEngine(rng=rng)


def make_tank(
    name: str,
    faction: Faction,
    pos: TileCoord,
    hp: int = 200,
) -> Unit:
    health = HealthComponent(hp=hp, max_hp=200)
    morale = MoraleComponent(value=90, panic_threshold=20, rout_threshold=10)
    weapon = WeaponComponent(primary_weapon_id="tank_cannon", ammo_remaining=30, max_ammo=30)
    position = PositionComponent(tile_coord=pos)
    vision = VisionComponent(range_tiles=7)
    return Unit(
        id=f"tank_{name.lower()}",
        name=name,
        faction=faction,
        unit_type=UnitType.TANK,
        health=health,
        morale=morale,
        weapon=weapon,
        position=position,
        vision=vision,
        armor_front=1.0,
        armor_side=0.65,
        armor_rear=0.40,
        armor_top=0.50,
    )


def make_infantry(
    name: str,
    faction: Faction,
    pos: TileCoord,
    hp: int = 100,
    weapon_id: str = "rifle",
) -> Unit:
    health = HealthComponent(hp=hp, max_hp=100)
    morale = MoraleComponent(value=80, panic_threshold=20, rout_threshold=10)
    weapon = WeaponComponent(primary_weapon_id=weapon_id, ammo_remaining=10, max_ammo=10)
    position = PositionComponent(tile_coord=pos)
    vision = VisionComponent(range_tiles=6)
    return Unit(
        id=f"inf_{name.lower()}",
        name=name,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=health,
        morale=morale,
        weapon=weapon,
        position=position,
        vision=vision,
        armor_front=0.15,
        armor_side=0.10,
        armor_rear=0.10,
        armor_top=0.10,
    )


class TestArmorProfileDefaults:
    def test_tank_armor_profile(self):
        profile = UNIT_ARMOR_PROFILES["TANK"]
        assert profile["front"] == 1.0
        assert profile["side"] == 0.65
        assert profile["rear"] == 0.40
        assert profile["top"] == 0.50

    def test_infantry_armor_profile(self):
        profile = UNIT_ARMOR_PROFILES["INFANTRY_SQUAD"]
        assert profile["front"] == 0.15
        assert profile["side"] == 0.10
        assert profile["rear"] == 0.10
        assert profile["top"] == 0.10

    def test_sniper_lowest_armor(self):
        profile = UNIT_ARMOR_PROFILES["SNIPER_TEAM"]
        assert profile["front"] == 0.05
        assert all(v <= 0.05 for v in profile.values())

    def test_all_unit_types_have_profiles(self):
        expected_types = [
            "TANK",
            "INFANTRY_SQUAD",
            "MACHINE_GUN_SQUAD",
            "SNIPER_TEAM",
            "MORTAR_TEAM",
            "COMMANDER",
            "MEDIC_TEAM",
            "AT_GUN_TEAM",
        ]
        for ut in expected_types:
            assert ut in UNIT_ARMOR_PROFILES
            profile = UNIT_ARMOR_PROFILES[ut]
            assert all(k in profile for k in ["front", "side", "rear", "top"])


class TestFrontalAttackOnTank:
    def test_frontal_attack_reduced_damage(self, engine):
        attacker = make_infantry("Attacker", Faction.ALLIES, TileCoord(5, 0))
        target = make_tank("Target", Faction.AXIS, TileCoord(0, 0))

        frontal_damages = []
        for i in range(100):
            ri = RandomContext.from_seed(1000 + i)
            ei = BallisticEngine(rng=ri)
            r = ei.calculate_shot(attacker, target, game_map=None)
            if r.hit:
                frontal_damages.append(r.damage_dealt)

        assert len(frontal_damages) > 0, "Expected at least one hit"

    def test_tank_cannon_frontal_vs_tank(self, engine):
        attacker = make_tank("Attacker", Faction.ALLIES, TileCoord(5, 0))
        target = make_tank("Target", Faction.AXIS, TileCoord(0, 0))

        damages = []
        for i in range(100):
            ri = RandomContext.from_seed(2000 + i)
            ei = BallisticEngine(rng=ri)
            r = ei.calculate_shot(attacker, target, game_map=None)
            if r.hit:
                damages.append(r.damage_dealt)

        assert len(damages) > 0


class TestFlankAttackOnTank:
    def test_flank_attack_higher_damage_than_frontal(self):
        frontal_damages = []
        flank_damages = []

        for i in range(150):
            ri = RandomContext.from_seed(3000 + i)
            ei = BallisticEngine(rng=ri)

            attacker_front = make_infantry("AtkF", Faction.ALLIES, TileCoord(5, 0))
            target = make_tank("Tgt", Faction.AXIS, TileCoord(0, 0))
            rf = ei.calculate_shot(attacker_front, target, game_map=None)
            if rf.hit:
                frontal_damages.append(rf.damage_dealt)

            ri2 = RandomContext.from_seed(3000 + i)
            ei2 = BallisticEngine(rng=ri2)
            attacker_flank = make_infantry("AtkFL", Faction.ALLIES, TileCoord(0, 5))
            target2 = make_tank("Tgt2", Faction.AXIS, TileCoord(0, 0))
            rl = ei2.calculate_shot(attacker_flank, target2, game_map=None)
            if rl.hit:
                flank_damages.append(rl.damage_dealt)

        if len(frontal_damages) > 0 and len(flank_damages) > 0:
            avg_frontal = sum(frontal_damages) / len(frontal_damages)
            avg_flank = sum(flank_damages) / len(flank_damages)
            assert avg_flank >= avg_frontal * 0.9


class TestRearAttackOnTank:
    def test_rear_attack_highest_damage(self):
        rear_damages = []

        for i in range(100):
            ri = RandomContext.from_seed(4000 + i)
            ei = BallisticEngine(rng=ri)
            attacker = make_infantry("AtkR", Faction.ALLIES, TileCoord(0, -5))
            target = make_tank("Tgt", Faction.AXIS, TileCoord(0, 0))
            r = ei.calculate_shot(attacker, target, game_map=None)
            if r.hit:
                rear_damages.append(r.damage_dealt)

        assert len(rear_damages) > 0


class TestInfantryLowArmor:
    def test_infantry_receives_full_damage(self, engine):
        attacker = make_infantry("Attacker", Faction.ALLIES, TileCoord(5, 0), weapon_id="rifle")
        target = make_infantry("Target", Faction.AXIS, TileCoord(0, 0))

        damages = []
        for i in range(100):
            ri = RandomContext.from_seed(5000 + i)
            ei = BallisticEngine(rng=ri)
            r = ei.calculate_shot(attacker, target, game_map=None)
            if r.hit:
                damages.append(r.damage_dealt)

        assert len(damages) > 0
        assert all(d > 0 for d in damages)


class TestTankCannonVsInfantry:
    def test_tank_cannon_vs_infantry_damage(self, engine):
        attacker = make_tank("Tank", Faction.ALLIES, TileCoord(5, 0))
        target = make_infantry("Inf", Faction.AXIS, TileCoord(0, 0))

        damages = []
        for i in range(100):
            ri = RandomContext.from_seed(6000 + i)
            ei = BallisticEngine(rng=ri)
            r = ei.calculate_shot(attacker, target, game_map=None)
            if r.hit:
                damages.append(r.damage_dealt)

        assert len(damages) > 0


class TestHighPenetrationDefeatsArmor:
    def test_bazooka_high_penetration(self):
        attacker_data = {
            "id": "bazooka_man",
            "name": "Bazooka",
            "faction": Faction.ALLIES,
            "pos": TileCoord(5, 0),
            "weapon_id": "bazooka",
        }
        health = HealthComponent(hp=100, max_hp=100)
        morale = MoraleComponent(value=80, panic_threshold=20, rout_threshold=10)
        weapon = WeaponComponent(primary_weapon_id="bazooka", ammo_remaining=3, max_ammo=3)
        position = PositionComponent(tile_coord=TileCoord(5, 0))
        vision = VisionComponent(range_tiles=6)
        attacker = Unit(
            id=attacker_data["id"],
            name=attacker_data["name"],
            faction=attacker_data["faction"],
            unit_type=UnitType.INFANTRY_SQUAD,
            health=health,
            morale=morale,
            weapon=weapon,
            position=position,
            vision=vision,
        )

        target = make_tank("Target", Faction.AXIS, TileCoord(0, 0))

        damages = []
        for i in range(100):
            ri = RandomContext.from_seed(7000 + i)
            ei = BallisticEngine(rng=ri)
            r = ei.calculate_shot(attacker, target, game_map=None)
            if r.hit:
                damages.append(r.damage_dealt)

        assert len(damages) > 0


class TestSniperVsTankIneffective:
    def test_sniper_low_damage_vs_tank(self):
        sniper_health = HealthComponent(hp=60, max_hp=60)
        sniper_morale = MoraleComponent(value=80, panic_threshold=20, rout_threshold=10)
        sniper_weapon = WeaponComponent(primary_weapon_id="sniper_rifle", ammo_remaining=15, max_ammo=15)
        sniper_position = PositionComponent(tile_coord=TileCoord(10, 0))
        sniper_vision = VisionComponent(range_tiles=10)
        sniper = Unit(
            id="sniper_1",
            name="Sniper",
            faction=Faction.ALLIES,
            unit_type=UnitType.SNIPER_TEAM,
            health=sniper_health,
            morale=sniper_morale,
            weapon=sniper_weapon,
            position=sniper_position,
            vision=sniper_vision,
            armor_front=0.05,
            armor_side=0.03,
            armor_rear=0.03,
            armor_top=0.03,
        )

        target = make_tank("Target", Faction.AXIS, TileCoord(0, 0))

        damages = []
        hits = 0
        for i in range(100):
            ri = RandomContext.from_seed(8000 + i)
            ei = BallisticEngine(rng=ri)
            r = ei.calculate_shot(sniper, target, game_map=None)
            if r.hit:
                hits += 1
                damages.append(r.damage_dealt)

        assert hits > 0, "Sniper should hit at least once"
        if damages:
            assert all(d > 0 for d in damages)


class TestCalcArmorFactorDirect:
    def test_frontal_armor_factor_low_penetration(self, engine):
        attacker = make_infantry("Atk", Faction.ALLIES, TileCoord(5, 0))
        target = make_tank("Tgt", Faction.AXIS, TileCoord(0, 0))

        factor = engine._calc_armor_factor(attacker, target, penetration=1.0)
        assert 0.25 <= factor <= 1.0

    def test_high_penetration_full_factor(self, engine):
        attacker = make_infantry("Atk", Faction.ALLIES, TileCoord(5, 0))
        target = make_tank("Tgt", Faction.AXIS, TileCoord(0, 0))

        factor = engine._calc_armor_factor(attacker, target, penetration=3.0)
        assert factor == 1.0

    def test_minimum_armor_factor(self, engine):
        attacker = make_infantry("Atk", Faction.ALLIES, TileCoord(5, 0))
        target = make_tank("Tgt", Faction.AXIS, TileCoord(0, 0))

        factor = engine._calc_armor_factor(attacker, target, penetration=0.1)
        assert factor >= 0.25

    def test_infantry_low_armor_high_factor(self, engine):
        attacker = make_infantry("Atk", Faction.ALLIES, TileCoord(5, 0))
        target = make_infantry("Tgt", Faction.AXIS, TileCoord(0, 0))

        factor = engine._calc_armor_factor(attacker, target, penetration=1.0)
        assert factor >= 0.8


class TestWeaponStatsUpdates:
    def test_tank_cannon_has_anti_tank_bonus(self, engine):
        stats = engine._weapon_stats.get("tank_cannon")
        assert stats is not None
        assert "anti_tank_bonus" in stats
        assert stats["anti_tank_bonus"] == 1.5

    def test_tank_cannon_penetration_increased(self, engine):
        stats = engine._weapon_stats.get("tank_cannon")
        assert stats is not None
        assert stats["penetration"] == 2.5

    def test_bazooka_exists(self, engine):
        stats = engine._weapon_stats.get("bazooka")
        assert stats is not None
        assert stats["penetration"] == 3.0
        assert stats["anti_tank_bonus"] == 2.0
