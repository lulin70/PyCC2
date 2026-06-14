"""
Unit Tests for MeleeCombatSystem

Tests melee engagement conditions, damage resolution,
weapon selection, hit chance calculation, and counter-attack mechanics.
"""

import pytest
from unittest.mock import Mock

from pycc2.domain.ai.melee_combat import (
    MeleeCombatSystem,
    MeleeCombatAI,
    MeleeWeaponType,
    MeleeResult,
    BAYONET_DAMAGE,
    BUTT_STROKE_DAMAGE,
    FISTS_DAMAGE,
    BASE_HIT_CHANCE,
    CHARGE_BONUS,
    WOUNDED_PENALTY,
    COUNTER_ATTACK_RATIO,
)
from pycc2.domain.entities.unit import Faction, UnitType
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.value_objects.tile_coord import TileCoord


# ===========================================================================
# Stub helpers
# ===========================================================================

def _make_unit(unit_id, faction=Faction.ALLIES, unit_type=UnitType.INFANTRY_SQUAD,
               tile_x=5, tile_y=5, alive=True, can_act=True,
               ammo_ratio=0.02, hp_ratio=1.0):
    """Create a mock unit for melee testing."""
    unit = Mock()
    unit.id = unit_id
    unit.name = unit_id
    unit.faction = faction
    unit.unit_type = unit_type
    unit.is_alive = alive
    unit.can_act = can_act

    # Position
    pos = Mock()
    pos.tile_coord = TileCoord(tile_x, tile_y)
    unit.position = pos
    unit.position_component = pos

    # Health
    health = Mock()
    health.hp_ratio = hp_ratio
    health.hp = 100
    health.max_hp = 100
    health.heal = Mock()
    unit.health = health

    # Weapon (low ammo for melee)
    weapon = Mock()
    weapon.ammo_ratio = ammo_ratio
    unit.weapon = weapon

    # Fatigue
    unit.fatigue = None

    # Veterancy
    unit.veterancy = None

    # Take damage
    unit.take_damage = Mock()

    return unit


# ===========================================================================
# Tests — Melee Weapon Selection
# ===========================================================================

@pytest.mark.unit
class TestMeleeWeaponSelection:
    """Test get_melee_weapon for different unit types."""

    def test_infantry_gets_bayonet(self):
        unit = _make_unit("u1", unit_type=UnitType.INFANTRY_SQUAD)
        assert MeleeCombatSystem.get_melee_weapon(unit) == MeleeWeaponType.BAYONET

    def test_commander_gets_bayonet(self):
        unit = _make_unit("u1", unit_type=UnitType.COMMANDER)
        assert MeleeCombatSystem.get_melee_weapon(unit) == MeleeWeaponType.BAYONET

    def test_sniper_gets_bayonet(self):
        unit = _make_unit("u1", unit_type=UnitType.SNIPER_TEAM)
        assert MeleeCombatSystem.get_melee_weapon(unit) == MeleeWeaponType.BAYONET

    def test_mg_gets_butt_stroke(self):
        unit = _make_unit("u1", unit_type=UnitType.MACHINE_GUN_SQUAD)
        assert MeleeCombatSystem.get_melee_weapon(unit) == MeleeWeaponType.BUTT_STROKE

    def test_medic_gets_fists(self):
        unit = _make_unit("u1", unit_type=UnitType.MEDIC_TEAM)
        assert MeleeCombatSystem.get_melee_weapon(unit) == MeleeWeaponType.FISTS


# ===========================================================================
# Tests — Weapon Damage
# ===========================================================================

@pytest.mark.unit
class TestWeaponDamage:
    """Test get_weapon_damage for melee weapon types."""

    def test_bayonet_damage(self):
        assert MeleeCombatSystem.get_weapon_damage(MeleeWeaponType.BAYONET) == BAYONET_DAMAGE

    def test_butt_stroke_damage(self):
        assert MeleeCombatSystem.get_weapon_damage(MeleeWeaponType.BUTT_STROKE) == BUTT_STROKE_DAMAGE

    def test_fists_damage(self):
        assert MeleeCombatSystem.get_weapon_damage(MeleeWeaponType.FISTS) == FISTS_DAMAGE

    def test_bayonet_highest_damage(self):
        assert BAYONET_DAMAGE > BUTT_STROKE_DAMAGE > FISTS_DAMAGE


# ===========================================================================
# Tests — Hit Chance Calculation
# ===========================================================================

@pytest.mark.unit
class TestHitChanceCalculation:
    """Test calculate_hit_chance with various modifiers."""

    def test_base_hit_chance(self):
        unit = _make_unit("u1")
        chance = MeleeCombatSystem.calculate_hit_chance(unit)
        assert chance == BASE_HIT_CHANCE

    def test_charge_bonus(self):
        unit = _make_unit("u1")
        chance = MeleeCombatSystem.calculate_hit_chance(unit, is_charging=True)
        assert chance == BASE_HIT_CHANCE + CHARGE_BONUS

    def test_wounded_penalty(self):
        unit = _make_unit("u1", hp_ratio=0.5)
        chance = MeleeCombatSystem.calculate_hit_chance(unit)
        assert chance == BASE_HIT_CHANCE - WOUNDED_PENALTY

    def test_hit_chance_clamped_min(self):
        unit = _make_unit("u1", hp_ratio=0.01)
        chance = MeleeCombatSystem.calculate_hit_chance(unit)
        assert chance >= 0.1

    def test_hit_chance_clamped_max(self):
        unit = _make_unit("u1")
        chance = MeleeCombatSystem.calculate_hit_chance(unit, is_charging=True)
        assert chance <= 0.95


# ===========================================================================
# Tests — Melee Resolution
# ===========================================================================

@pytest.mark.unit
class TestMeleeResolution:
    """Test resolve_melee method."""

    def test_melee_hit_deals_damage(self):
        import random
        random.seed(42)
        attacker = _make_unit("a1", tile_x=5, tile_y=5)
        defender = _make_unit("d1", tile_x=5, tile_y=6)

        result = MeleeCombatSystem.resolve_melee(attacker, defender)
        assert isinstance(result, MeleeResult)
        assert result.attacker_id == "a1"
        assert result.defender_id == "d1"

    def test_melee_counter_attack(self):
        """Counter-attack can happen when defender survives."""
        import random
        random.seed(42)
        attacker = _make_unit("a1", tile_x=5, tile_y=5)
        defender = _make_unit("d1", tile_x=5, tile_y=6)

        result = MeleeCombatSystem.resolve_melee(attacker, defender)
        # Counter damage should be at most 50% of base
        if result.counter_hit:
            assert result.counter_damage <= int(BAYONET_DAMAGE * COUNTER_ATTACK_RATIO)

    def test_melee_result_structure(self):
        import random
        random.seed(42)
        attacker = _make_unit("a1", tile_x=5, tile_y=5)
        defender = _make_unit("d1", tile_x=5, tile_y=6)

        result = MeleeCombatSystem.resolve_melee(attacker, defender)
        assert hasattr(result, "hit")
        assert hasattr(result, "damage")
        assert hasattr(result, "counter_hit")
        assert hasattr(result, "counter_damage")
        assert hasattr(result, "attacker_weapon")


# ===========================================================================
# Tests — Can Melee
# ===========================================================================

@pytest.mark.unit
class TestCanMelee:
    """Test can_melee engagement conditions."""

    def test_can_melee_when_adjacent_and_low_ammo(self):
        unit = _make_unit("u1", tile_x=5, tile_y=5, ammo_ratio=0.02)
        enemy = _make_unit("e1", tile_x=5, tile_y=6, alive=True)
        assert MeleeCombatSystem.can_melee(unit, enemy) is True

    def test_cannot_melee_with_ammo(self):
        unit = _make_unit("u1", tile_x=5, tile_y=5, ammo_ratio=0.5)
        enemy = _make_unit("e1", tile_x=5, tile_y=6, alive=True)
        assert MeleeCombatSystem.can_melee(unit, enemy) is False

    def test_cannot_melee_too_far(self):
        unit = _make_unit("u1", tile_x=5, tile_y=5, ammo_ratio=0.02)
        enemy = _make_unit("e1", tile_x=10, tile_y=10, alive=True)
        assert MeleeCombatSystem.can_melee(unit, enemy) is False

    def test_cannot_melee_dead_enemy(self):
        unit = _make_unit("u1", tile_x=5, tile_y=5, ammo_ratio=0.02)
        enemy = _make_unit("e1", tile_x=5, tile_y=6, alive=False)
        assert MeleeCombatSystem.can_melee(unit, enemy) is False

    def test_cannot_melee_if_cannot_act(self):
        unit = _make_unit("u1", tile_x=5, tile_y=5, ammo_ratio=0.02, can_act=False)
        enemy = _make_unit("e1", tile_x=5, tile_y=6, alive=True)
        assert MeleeCombatSystem.can_melee(unit, enemy) is False

    def test_tank_cannot_melee(self):
        unit = _make_unit("u1", unit_type=UnitType.TANK, tile_x=5, tile_y=5, ammo_ratio=0.02)
        enemy = _make_unit("e1", tile_x=5, tile_y=6, alive=True)
        assert MeleeCombatSystem.can_melee(unit, enemy) is False


# ===========================================================================
# Tests — MeleeCombatAI
# ===========================================================================

@pytest.mark.unit
class TestMeleeCombatAI:
    """Test MeleeCombatAI evaluate and execute."""

    def test_evaluate_zero_when_no_candidates(self):
        ai = MeleeCombatAI()
        context = TacticalContext(
            friendly_units=[_make_unit("u1", ammo_ratio=0.5)],
            enemy_units=[_make_unit("e1", faction=Faction.AXIS)],
            game_map=Mock(),
            current_tick=100,
        )
        assert ai.evaluate(context) == 0.0

    def test_evaluate_nonzero_with_candidates(self):
        ai = MeleeCombatAI()
        friendly = _make_unit("u1", ammo_ratio=0.02, tile_x=5, tile_y=5)
        enemy = _make_unit("e1", faction=Faction.AXIS, tile_x=5, tile_y=6)
        context = TacticalContext(
            friendly_units=[friendly],
            enemy_units=[enemy],
            game_map=Mock(),
            current_tick=100,
        )
        score = ai.evaluate(context)
        assert score > 0.0

    def test_execute_returns_melee_intents(self):
        ai = MeleeCombatAI()
        friendly = _make_unit("u1", ammo_ratio=0.02, tile_x=5, tile_y=5)
        enemy = _make_unit("e1", faction=Faction.AXIS, tile_x=5, tile_y=6)
        context = TacticalContext(
            friendly_units=[friendly],
            enemy_units=[enemy],
            game_map=Mock(),
            current_tick=100,
        )
        intents = ai.execute(context)
        assert len(intents) >= 1
        assert intents[0].tactic_type == TacticType.MELEE_ATTACK

    def test_execute_empty_when_no_candidates(self):
        ai = MeleeCombatAI()
        context = TacticalContext(
            friendly_units=[_make_unit("u1", ammo_ratio=0.5)],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        intents = ai.execute(context)
        assert intents == []
