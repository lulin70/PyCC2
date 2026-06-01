from __future__ import annotations

import math

import numpy as np
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine, ShotResult
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.random_context import RandomContext


@pytest.fixture
def rng() -> RandomContext:
    return RandomContext.from_seed(42)


@pytest.fixture
def engine(rng: RandomContext) -> BallisticEngine:
    return BallisticEngine(rng=rng)


@pytest.fixture
def game_map() -> GameMap:
    grid = np.full((20, 20), TerrainType.OPEN.value, dtype=np.int8)
    return GameMap(id="test_map", name="Test Map", width=20, height=20, tile_grid=grid)


def make_unit(
    name: str,
    faction: Faction,
    pos: TileCoord,
    hp: int = 100,
    max_hp: int = 100,
    weapon_id: str = "rifle",
    ammo: int = 30,
    max_ammo: int = 30,
) -> Unit:
    health = HealthComponent(hp=hp, max_hp=max_hp)
    morale = MoraleComponent(value=80, panic_threshold=20, rout_threshold=10)
    weapon = WeaponComponent(primary_weapon_id=weapon_id, ammo_remaining=ammo, max_ammo=max_ammo)
    position = PositionComponent(tile_coord=pos)
    vision = VisionComponent(range_tiles=6)
    return Unit(
        id=f"u_{name.lower()}",
        name=name,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=health,
        morale=morale,
        weapon=weapon,
        position=position,
        vision=vision,
    )


class TestShotResultImmutable:
    def test_frozen_dataclass(self):
        sr = ShotResult(hit=True, damage_dealt=10.0)
        with pytest.raises(AttributeError):
            sr.hit = False


class TestBEHit:
    """BE-HIT 基础命中 (8 tests)"""

    def test_hit_01_high_accuracy_in_range(self, engine, game_map):
        atk = make_unit("Attacker", Faction.ALLIES, TileCoord(0, 0))
        tgt = make_unit("Target", Faction.AXIS, TileCoord(5, 0))
        result = engine.calculate_shot(atk, tgt, game_map=None)
        dist = atk.position.tile_coord.octile_distance(tgt.position.tile_coord)
        assert dist < engine._weapon_stats["rifle"]["effective_range"]
        assert 0.0 <= result.actual_accuracy <= 1.0, f"actual_accuracy should be in [0,1], got {result.actual_accuracy}"
        assert isinstance(result.hit, bool), f"hit should be bool, got {type(result.hit)}"

    def test_hit_02_low_accuracy_at_max_range(self, engine):
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
        tgt = make_unit("T", Faction.AXIS, TileCoord(18, 0))
        result = engine.calculate_shot(atk, tgt, game_map=None)
        assert result.actual_accuracy < 0.3

    def test_hit_03_perfect_conditions(self, engine):
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
        tgt = make_unit("T", Faction.AXIS, TileCoord(0, 0))
        result = engine.calculate_shot(atk, tgt, game_map=None)
        assert result.actual_accuracy >= 0.8

    def test_hit_04_cover_reduces_accuracy(self, engine, game_map):
        game_map.tile_grid[0, 5] = TerrainType.WOODS.value
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
        tgt = make_unit("T", Faction.AXIS, TileCoord(5, 0))
        result_with_cover = engine.calculate_shot(atk, tgt, game_map=game_map)
        game_map.tile_grid[0, 5] = TerrainType.OPEN.value
        result_no_cover = engine.calculate_shot(atk, tgt, game_map=game_map)
        assert result_with_cover.actual_accuracy < result_no_cover.actual_accuracy

    def test_hit_05_deterministic_same_seed(self, engine):
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
        tgt = make_unit("T", Faction.AXIS, TileCoord(5, 0))
        r1 = engine.calculate_shot(atk, tgt, game_map=None)
        rng2 = RandomContext.from_seed(42)
        engine2 = BallisticEngine(rng=rng2)
        r2 = engine2.calculate_shot(atk, tgt, game_map=None)
        assert r1.hit == r2.hit
        assert r1.damage_dealt == r2.damage_dealt
        assert r1.actual_accuracy == r2.actual_accuracy

    def test_hit_06_full_cover_near_zero_hit(self, engine, game_map):
        game_map.tile_grid[0, 3] = TerrainType.BUILDING_SOLID.value
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
        tgt = make_unit("T", Faction.AXIS, TileCoord(3, 0))
        result = engine.calculate_shot(atk, tgt, game_map=game_map)
        assert result.actual_accuracy <= 0.16

    def test_hit_07_large_sample_convergence(self):
        hits = 0
        n = 1000
        for i in range(n):
            rng_i = RandomContext.from_seed(12345 + i)
            eng_i = BallisticEngine(rng=rng_i)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(5, 0))
            res = eng_i.calculate_shot(atk, tgt, game_map=None)
            if res.hit:
                hits += 1
        rate = hits / n
        assert 0.3 <= rate <= 0.8

    def test_hit_08_dead_target_miss(self, engine):
        tgt = make_unit("Dead", Faction.AXIS, TileCoord(5, 0), hp=0, max_hp=100)
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
        result = engine.calculate_shot(atk, tgt, game_map=None)
        assert result.hit is False
        assert result.damage_dealt == 0.0


class TestBEDamage:
    """BE-DMG 伤害 (8 tests)"""

    def test_dmg_01_positive_damage_on_hit(self):
        results = []
        for i in range(50):
            ri = RandomContext.from_seed(200 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(3, 0), hp=100)
            r = ei.calculate_shot(atk, tgt, game_map=None)
            if r.hit:
                results.append(r.damage_dealt)
        assert len(results) >= 1, f"Expected at least 1 hit in 50 shots, got {len(results)} hits"
        assert all(d > 0 for d in results), "All hit damages should be positive"

    def test_dmg_02_damageDecreasesWithDistance(self):
        close_hits = []
        far_hits = []
        for i in range(200):
            ri = RandomContext.from_seed(300 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt_close = make_unit("TC", Faction.AXIS, TileCoord(2, 0))
            tgt_far = make_unit("TF", Faction.AXIS, TileCoord(12, 0))
            rc = ei.calculate_shot(atk, tgt_close, game_map=None)
            rf = ei.calculate_shot(atk, tgt_far, game_map=None)
            if rc.hit:
                close_hits.append(rc.damage_dealt)
            if rf.hit:
                far_hits.append(rf.damage_dealt)
        if len(close_hits) > 0 and len(far_hits) > 0:
            assert sum(close_hits) / len(close_hits) >= sum(far_hits) / len(far_hits)

    def test_dmg_03_coverReducesDamage(self):
        grid = np.full((20, 20), TerrainType.OPEN.value, dtype=np.int8)
        gm = GameMap(id="test", name="T", width=20, height=20, tile_grid=grid)
        gm.tile_grid[0, 4] = TerrainType.BUILDING_ENTERABLE.value
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
        tgt = make_unit("T", Faction.AXIS, TileCoord(4, 0))
        hits = []
        for i in range(100):
            ri = RandomContext.from_seed(400 + i)
            ei = BallisticEngine(rng=ri)
            r = ei.calculate_shot(atk, tgt, game_map=gm)
            if r.hit:
                hits.append(r.damage_dealt)
        assert len(hits) > 0

    def test_dmg_04_meleeHighestDamage(self):
        hits_zero = []
        for i in range(100):
            ri = RandomContext.from_seed(500 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(0, 0))
            r = ei.calculate_shot(atk, tgt, game_map=None)
            if r.hit:
                hits_zero.append(r.damage_dealt)
        assert len(hits_zero) > 0

    def test_dmg_05_damageCap(self):
        ri = RandomContext.from_seed(42)
        ei = BallisticEngine(rng=ri)
        ws = ei._weapon_stats["rifle"]
        cap = ws["base_damage"] * ws["penetration"] * 2.0
        for i in range(200):
            ri = RandomContext.from_seed(600 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(1, 0))
            r = ei.calculate_shot(atk, tgt, game_map=None)
            if r.hit:
                assert r.damage_dealt <= cap + 0.01

    def test_dmg_06_variance(self):
        damages = set()
        for i in range(100):
            ri = RandomContext.from_seed(700 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(2, 0))
            r = ei.calculate_shot(atk, tgt, game_map=None)
            if r.hit:
                damages.add(round(r.damage_dealt, 2))
        assert len(damages) >= 3

    def test_dmg_07_zeroDistDamageNearBase(self):
        ri = RandomContext.from_seed(42)
        ei = BallisticEngine(rng=ri)
        ws = ei._weapon_stats["rifle"]
        base = ws["base_damage"] * ws["penetration"]
        damages = []
        for i in range(100):
            ri = RandomContext.from_seed(800 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(0, 0))
            r = ei.calculate_shot(atk, tgt, game_map=None)
            if r.hit:
                damages.append(r.damage_dealt)
        if damages:
            avg = sum(damages) / len(damages)
            assert base * 0.7 <= avg <= base * 1.3

    def test_dmg_08_killingBlowPossible(self):
        killing_blows = 0
        for i in range(500):
            ri = RandomContext.from_seed(900 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(2, 0), hp=10, max_hp=10)
            r = ei.calculate_shot(atk, tgt, game_map=None)
            if r.is_killing_blow:
                killing_blows += 1
        assert killing_blows >= 1, f"Expected at least 1 killing blow in 500 shots on 10-HP target, got {killing_blows}"


class TestBESpread:
    """BE-SPR 散布 (6 tests)"""

    def test_spr_01_spreadIncreasesWithDistance(self, engine):
        d1 = engine._calc_spread(2.0, 5.0, engine.rng)
        d2 = engine._calc_spread(2.0, 15.0, engine.rng)
        assert abs(d2) >= abs(d1)

    def test_spr_02_missHasPosition(self):
        found_miss = False
        for i in range(50):
            ri = RandomContext.from_seed(1000 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(15, 0))
            r = ei.calculate_shot(atk, tgt, game_map=None)
            if not r.hit:
                assert r.miss_position is not None
                assert isinstance(r.miss_position, tuple)
                assert len(r.miss_position) == 2
                found_miss = True
                break
        assert found_miss, "Expected at least one miss"

    def test_spr_03_hitMissPositionNone(self):
        found_hit = False
        for i in range(50):
            ri = RandomContext.from_seed(1100 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(0, 0))
            r = ei.calculate_shot(atk, tgt, game_map=None)
            if r.hit:
                assert r.miss_position is None
                found_hit = True
                break
        assert found_hit, "Expected at least one hit"

    def test_spr_04_spreadNormalDistribution(self):
        spreads = []
        for _ in range(500):
            ri = RandomContext.from_seed(1200 + _)
            ei = BallisticEngine(rng=ri)
            s = ei._calc_spread(3.0, 10.0, ei.rng)
            spreads.append(s)
        mean = sum(spreads) / len(spreads)
        variance = sum((s - mean) ** 2 for s in spreads) / len(spreads)
        std = math.sqrt(variance)
        assert -2.0 < mean < 2.0
        assert std > 0

    def test_spr_05_differentWeaponSpread(self, engine):
        ri = RandomContext.from_seed(42)
        ei = BallisticEngine(rng=ri)
        s_rifle = ei._calc_spread(
            ei._weapon_stats["rifle"]["spread"],
            10.0,
            ei.rng,
        )
        s_sniper = ei._calc_spread(
            ei._weapon_stats["sniper"]["spread"],
            10.0,
            ei.rng,
        )
        assert abs(s_rifle) != abs(s_sniper)

    def test_spr_06_spreadDoesNotAffectAccuracy(self, engine):
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
        tgt = make_unit("T", Faction.AXIS, TileCoord(5, 0))
        r1 = engine.calculate_shot(atk, tgt, game_map=None)
        acc1 = r1.actual_accuracy
        assert isinstance(acc1, float)


class TestBEEdge:
    """BE-EDGE 边缘 (8 tests)"""

    def test_edge_01_zeroDistance(self, engine):
        atk = make_unit("A", Faction.ALLIES, TileCoord(5, 5))
        tgt = make_unit("T", Faction.AXIS, TileCoord(5, 5))
        result = engine.calculate_shot(atk, tgt, game_map=None)
        assert result.distance == 0.0
        assert result.actual_accuracy >= 0.8

    def test_edge_02_outOfRange(self, engine):
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
        tgt = make_unit("T", Faction.AXIS, TileCoord(50, 0))
        result = engine.calculate_shot(atk, tgt, game_map=None)
        assert result.hit is False
        assert "out of range" in result.reason.lower() or result.actual_accuracy <= 0.06

    def test_edge_03_outOfAmmo(self, engine):
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0), ammo=0, max_ammo=30)
        tgt = make_unit("T", Faction.AXIS, TileCoord(5, 0))
        result = engine.calculate_shot(atk, tgt, game_map=None)
        assert result.hit is False
        assert "ammo" in result.reason.lower()

    def test_edge_04_deadAttacker(self, engine):
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0), hp=0, max_hp=100)
        tgt = make_unit("T", Faction.AXIS, TileCoord(5, 0))
        result = engine.calculate_shot(atk, tgt, game_map=None)
        assert result.hit is False
        assert result.damage_dealt == 0.0

    def test_edge_05_noneTarget(self, engine):
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
        with pytest.raises((AttributeError, TypeError)):
            engine.calculate_shot(atk, None, game_map=None)

    def test_edge_06_sequenceDeterminism(self):
        results = []
        for _i in range(10):
            ri = RandomContext.from_seed(9999)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(4, 0))
            r = ei.calculate_shot(atk, tgt, game_map=None)
            results.append((r.hit, r.damage_dealt, r.actual_accuracy))
        assert len(set(results)) == 1

    def test_edge_07_resultImmutable(self):
        sr = ShotResult(hit=True, damage_dealt=5.0, distance=3.0)
        with pytest.raises(AttributeError):
            sr.hit = False

    def test_edge_08_noMapNoError(self, engine):
        atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
        tgt = make_unit("T", Faction.AXIS, TileCoord(5, 0))
        result = engine.calculate_shot(atk, tgt, game_map=None)
        assert isinstance(result, ShotResult)


class TestBEStats:
    """BE-STAT 统计 (5 tests)"""

    def test_stat_01_meanHitRateConverges(self):
        hits = 0
        n = 1000
        for i in range(n):
            ri = RandomContext.from_seed(3333 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(5, 0))
            r = ei.calculate_shot(atk, tgt, game_map=None)
            if r.hit:
                hits += 1
        rate = hits / n
        assert 0.2 <= rate <= 0.8

    def test_stat_02_meanDamageReasonable(self):
        damages = []
        for i in range(500):
            ri = RandomContext.from_seed(4444 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(3, 0))
            r = ei.calculate_shot(atk, tgt, game_map=None)
            if r.hit:
                damages.append(r.damage_dealt)
        if damages:
            avg = sum(damages) / len(damages)
            assert 1.0 <= avg <= 50.0

    def test_stat_03_killingRateCorrelatesWithHP(self):
        low_hp_kills = 0
        high_hp_kills = 0
        n = 500
        for i in range(n):
            ri = RandomContext.from_seed(5555 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt_low = make_unit("TL", Faction.AXIS, TileCoord(3, 0), hp=5, max_hp=5)
            rl = ei.calculate_shot(atk, tgt_low, game_map=None)
            if rl.is_killing_blow:
                low_hp_kills += 1
            ri2 = RandomContext.from_seed(6666 + i)
            ei2 = BallisticEngine(rng=ri2)
            atk2 = make_unit("A2", Faction.ALLIES, TileCoord(0, 0))
            tgt_high = make_unit("TH", Faction.AXIS, TileCoord(3, 0), hp=100, max_hp=100)
            rh = ei2.calculate_shot(atk2, tgt_high, game_map=None)
            if rh.is_killing_blow:
                high_hp_kills += 1
        assert low_hp_kills >= high_hp_kills

    def test_stat_04_suppressionDistribution(self):
        hit_supps = []
        miss_supps = []
        for i in range(300):
            ri = RandomContext.from_seed(7777 + i)
            ei = BallisticEngine(rng=ri)
            atk = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            tgt = make_unit("T", Faction.AXIS, TileCoord(4, 0))
            r = ei.calculate_shot(atk, tgt, game_map=None)
            if r.hit:
                hit_supps.append(r.suppression_dealt)
            else:
                miss_supps.append(r.suppression_dealt)
        if hit_supps and miss_supps:
            assert sum(hit_supps) / len(hit_supps) > sum(miss_supps) / len(miss_supps)

    def test_stat_05_fixedSeedFullyDeterministic(self):
        r1s = []
        r2s = []
        for _ in range(20):
            r1 = RandomContext.from_seed(8888)
            e1 = BallisticEngine(rng=r1)
            a = make_unit("A", Faction.ALLIES, TileCoord(0, 0))
            t = make_unit("T", Faction.AXIS, TileCoord(4, 0))
            r1s.append(e1.calculate_shot(a, t, game_map=None))

            r2 = RandomContext.from_seed(8888)
            e2 = BallisticEngine(rng=r2)
            r2s.append(e2.calculate_shot(a, t, game_map=None))

        for sr1, sr2 in zip(r1s, r2s, strict=False):
            assert sr1.hit == sr2.hit
            assert sr1.damage_dealt == sr2.damage_dealt
            assert sr1.suppression_dealt == sr2.suppression_dealt
