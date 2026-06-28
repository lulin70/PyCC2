"""Tests for CounterattackAI — strategic counterattack after reinforcement."""

from __future__ import annotations

import numpy as np

from pycc2.domain.ai.counterattack_ai import CounterattackAI
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord

# ---------------------------------------------------------------------------
# Helpers — real components, no mocks
# ---------------------------------------------------------------------------


def _make_unit(
    uid: str = "u1",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    x: int = 10,
    y: int = 10,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 80,
) -> Unit:
    return Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )


def _make_map(w: int = 40, h: int = 30) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    return GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)


def _make_context(
    friendly: list[Unit] | None = None,
    enemy: list[Unit] | None = None,
    game_map: GameMap | None = None,
    tick: int = 1,
) -> TacticalContext:
    return TacticalContext(
        friendly_units=friendly or [],
        enemy_units=enemy or [],
        game_map=game_map or _make_map(),
        current_tick=tick,
    )


# ---------------------------------------------------------------------------
# Test: evaluate — high score when force ratio is favorable
# ---------------------------------------------------------------------------


class TestEvaluateHighScoreFavorable:
    def test_evaluate_high_score_when_force_ratio_favorable(self):
        """3 friendlies vs 2 enemies → force_ratio 1.5 > 1.2 → score > 0.7."""
        ai = CounterattackAI()
        friendlies = [
            _make_unit("f1", x=10, y=10),
            _make_unit("f2", x=11, y=10),
            _make_unit("f3", x=12, y=10),
        ]
        # Enemies far away so offensive-posture bonus does not apply
        enemies = [
            _make_unit("e1", faction=Faction.AXIS, x=30, y=10),
            _make_unit("e2", faction=Faction.AXIS, x=31, y=10),
        ]
        ctx = _make_context(friendly=friendlies, enemy=enemies)
        score = ai.evaluate(ctx)
        assert score > 0.7


# ---------------------------------------------------------------------------
# Test: evaluate — zero when outnumbered
# ---------------------------------------------------------------------------


class TestEvaluateZeroWhenOutnumbered:
    def test_evaluate_zero_when_outnumbered(self):
        """2 friendlies vs 3 enemies → force_ratio 0.67 < 1.0 → score == 0.0."""
        ai = CounterattackAI()
        friendlies = [
            _make_unit("f1", x=10, y=10),
            _make_unit("f2", x=11, y=10),
        ]
        enemies = [
            _make_unit("e1", faction=Faction.AXIS, x=30, y=10),
            _make_unit("e2", faction=Faction.AXIS, x=31, y=10),
            _make_unit("e3", faction=Faction.AXIS, x=32, y=10),
        ]
        ctx = _make_context(friendly=friendlies, enemy=enemies)
        assert ai.evaluate(ctx) == 0.0


# ---------------------------------------------------------------------------
# Test: execute — targets the weakest enemy
# ---------------------------------------------------------------------------


class TestExecuteTargetsWeakestEnemy:
    def test_execute_targets_weakest_enemy(self):
        """COUNTER_ATTACK intents must target the lowest-HP enemy."""
        ai = CounterattackAI()
        friendlies = [
            _make_unit("f1", x=10, y=10),
            _make_unit("f2", x=11, y=10),
            _make_unit("f3", x=12, y=10),
        ]
        enemies = [
            _make_unit("e1", faction=Faction.AXIS, x=20, y=10, hp=80, max_hp=100),
            _make_unit("e2", faction=Faction.AXIS, x=21, y=10, hp=20, max_hp=100),  # weakest
            _make_unit("e3", faction=Faction.AXIS, x=22, y=10, hp=50, max_hp=100),
        ]
        ctx = _make_context(friendly=friendlies, enemy=enemies)

        intents = ai.execute(ctx)
        counter_intents = [i for i in intents if i.tactic_type == TacticType.COUNTER_ATTACK]

        assert len(counter_intents) >= 1
        # Every counterattack intent must target the weakest enemy (e2, hp=20)
        for intent in counter_intents:
            assert intent.target_unit_id == "e2"
        # Sanity: e2 really is the weakest by HP
        weakest = min(enemies, key=lambda e: e.health.hp)
        assert weakest.id == "e2"


# ---------------------------------------------------------------------------
# Test: execute — limits attackers to 3
# ---------------------------------------------------------------------------


class TestExecuteLimitsAttackers:
    def test_execute_limits_attackers_to_3(self):
        """Even with many eligible friendlies, at most 3 COUNTER_ATTACK intents."""
        ai = CounterattackAI()
        friendlies = [
            _make_unit(f"f{i}", x=10 + i, y=10) for i in range(5)
        ]
        enemies = [
            _make_unit("e1", faction=Faction.AXIS, x=30, y=10, hp=40, max_hp=100),
            _make_unit("e2", faction=Faction.AXIS, x=31, y=10, hp=80, max_hp=100),
        ]
        ctx = _make_context(friendly=friendlies, enemy=enemies)

        intents = ai.execute(ctx)
        counter_intents = [i for i in intents if i.tactic_type == TacticType.COUNTER_ATTACK]

        assert len(counter_intents) <= 3
        assert len(counter_intents) == 3  # all 5 eligible, capped at 3

        # Extra eligible units should be assigned flanking instead
        flanking_intents = [i for i in intents if i.tactic_type == TacticType.FLANKING]
        assert len(flanking_intents) >= 1


# ---------------------------------------------------------------------------
# Test: evaluate — morale bonus
# ---------------------------------------------------------------------------


class TestEvaluateMoraleBonus:
    def test_morale_bonus(self):
        """Average friendly morale > 50 should yield a higher score than <= 50."""
        ai = CounterattackAI()

        # High-morale force (avg = 80 > 50 → +0.1 bonus)
        high_morale_friendlies = [
            _make_unit("h1", x=10, y=10, morale=80),
            _make_unit("h2", x=11, y=10, morale=80),
            _make_unit("h3", x=12, y=10, morale=80),
        ]
        # Low-morale force (avg = 30 <= 50 → no bonus)
        low_morale_friendlies = [
            _make_unit("l1", x=10, y=10, morale=30),
            _make_unit("l2", x=11, y=10, morale=30),
            _make_unit("l3", x=12, y=10, morale=30),
        ]
        enemies = [
            _make_unit("e1", faction=Faction.AXIS, x=30, y=10),
            _make_unit("e2", faction=Faction.AXIS, x=31, y=10),
        ]

        # Same enemy disposition → identical force ratio & posture
        ctx_high = _make_context(friendly=high_morale_friendlies, enemy=enemies)
        ctx_low = _make_context(friendly=low_morale_friendlies, enemy=enemies)

        score_high = ai.evaluate(ctx_high)
        score_low = ai.evaluate(ctx_low)

        assert score_high > score_low
        assert score_high >= 0.9   # 0.8 base + 0.1 morale bonus
        assert score_low <= 0.8    # 0.8 base, no morale bonus
