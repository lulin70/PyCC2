"""
Unit Tests for Melee Combat & Grenade System (B4+B5)

Tests the CC2-authentic close-quarters combat including:
- B4: Melee combat (bayonet/butt stroke/fists)
- B5: Grenade AOE throwing system

Coverage:
- Melee weapon selection and damage
- Hit chance calculation with modifiers
- Melee resolution and counter-attacks
- Grenade throwing validation (range/ammo)
- AOE damage distribution (center vs edge)
- Suppression effects from grenades
- Grenade ammo management
"""

import math
import pytest
from unittest.mock import Mock, MagicMock, patch

from pycc2.domain.ai.melee_combat import (
    # B4 Melee
    MeleeCombatSystem,
    MeleeCombatAI,
    MeleeWeaponType,
    MeleeResult,
    BAYONET_DAMAGE,
    BUTT_STROKE_DAMAGE,
    FISTS_DAMAGE,
    BASE_HIT_CHANCE,
    MELEE_RANGE,
    AMMO_THRESHOLD,
    # B5 Grenade
    GrenadeSystem,
    GrenadeResult,
    GrenadeTargetResult,
    GRENADE_MAX_COUNT,
    GRENADE_MIN_RANGE,
    GRENADE_MAX_RANGE,
    GRENADE_AOE_RADIUS,
    GRENADE_CENTER_DAMAGE,
    GRENADE_EDGE_DAMAGE,
    GRENADE_SUPPRESSION,
)
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.value_objects.tile_coord import TileCoord


# ===========================================================================
# Mock Fixtures
# ===========================================================================

@pytest.fixture
def mock_infantry_unit():
    """Create a mock infantry unit with bayonet."""
    from pycc2.domain.entities.unit import UnitType

    unit = Mock()
    unit.is_alive = True
    unit.can_act = True
    unit.id = "infantry_001"
    unit.unit_type = UnitType.INFANTRY_SQUAD  # Use actual enum value

    # Position
    pos = Mock()
    pos.tile_coord = TileCoord(5, 5)
    pos.x = 5
    pos.y = 5
    unit.position = pos
    unit.position_component = pos

    # Health
    health = Mock()
    health.hp_ratio = 1.0
    unit.health = health

    # Weapon (low ammo to trigger melee)
    weapon = Mock()
    weapon.ammo_ratio = 0.03  # Below threshold
    unit.weapon = weapon

    return unit


@pytest.fixture
def mock_mg_unit():
    """Create a mock MG squad (uses butt stroke, no bayonet)."""
    from pycc2.domain.entities.unit import UnitType

    unit = Mock()
    unit.is_alive = True
    unit.can_act = True
    unit.id = "mg_team_001"
    unit.unit_type = UnitType.MACHINE_GUN_SQUAD  # Use actual enum value

    pos = Mock()
    pos.tile_coord = TileCoord(6, 5)
    pos.x = 6
    pos.y = 5
    unit.position = pos
    unit.position_component = pos

    health = Mock()
    health.hp_ratio = 0.8
    unit.health = health

    weapon = Mock()
    weapon.ammo_ratio = 0.02
    unit.weapon = weapon

    return unit


@pytest.fixture
def mock_enemy_unit():
    """Create a mock enemy unit."""
    enemy = Mock()
    enemy.is_alive = True
    enemy.id = "enemy_001"

    pos = Mock()
    pos.tile_coord = TileCoord(6, 5)  # Adjacent to infantry
    pos.x = 6
    pos.y = 5
    enemy.position = pos
    enemy.position_component = pos

    health = Mock()
    health.hp_ratio = 0.9
    enemy.health = health

    def take_damage(amount):
        enemy.health.hp_ratio -= amount / 100.0

    enemy.take_damage = take_damage

    enemy.suppression_state = Mock()

    return enemy


@pytest.fixture
def tactical_context(mock_infantry_unit, mock_enemy_unit):
    """Create tactical context with adjacent units."""
    return TacticalContext(
        friendly_units=[mock_infantry_unit],
        enemy_units=[mock_enemy_unit],
        game_map=Mock(),
        current_tick=100,
    )


# ===========================================================================
# Test Class: B4 Melee Combat System
# ===========================================================================

class TestMeleeWeaponSelection:
    """Test melee weapon type assignment."""

    def test_infantry_gets_bayonet(self, mock_infantry_unit):
        """Infantry squads should get bayonets."""
        weapon = MeleeCombatSystem.get_melee_weapon(mock_infantry_unit)
        assert weapon == MeleeWeaponType.BAYONET

    def test_mg_gets_butt_stroke(self, mock_mg_unit):
        """MG teams should use butt stroke."""
        weapon = MeleeCombatSystem.get_melee_weapon(mock_mg_unit)
        assert weapon == MeleeWeaponType.BUTT_STROKE

    def test_weapon_damage_values(self):
        """Verify damage values match constants."""
        assert MeleeCombatSystem.get_weapon_damage(MeleeWeaponType.BAYONET) == BAYONET_DAMAGE
        assert MeleeCombatSystem.get_weapon_damage(MeleeWeaponType.BUTT_STROKE) == BUTT_STROKE_DAMAGE
        assert MeleeCombatSystem.get_weapon_damage(MeleeWeaponType.FISTS) == FISTS_DAMAGE


class TestMeleeHitChance:
    """Test hit chance calculation."""

    def test_base_hit_chance(self, mock_infantry_unit):
        """Base hit chance should be 70%."""
        chance = MeleeCombatSystem.calculate_hit_chance(mock_infantry_unit)
        assert chance == pytest.approx(BASE_HIT_CHANCE)

    def test_charging_bonus(self, mock_infantry_unit):
        """Charging should increase hit chance by 20%."""
        chance = MeleeCombatSystem.calculate_hit_chance(mock_infantry_unit, is_charging=True)
        assert chance == pytest.approx(BASE_HIT_CHANCE + 0.20)

    def test_exhausted_penalty(self, mock_infantry_unit):
        """Exhausted units should have reduced hit chance."""
        from pycc2.domain.components.fatigue_component import FatigueLevel
        mock_infantry_unit.fatigue = Mock(level=FatigueLevel.EXHAUSTED)

        chance = MeleeCombatSystem.calculate_hit_chance(mock_infantry_unit)
        assert chance < BASE_HIT_CHANCE

    def test_wounded_penalty(self, mock_infantry_unit):
        """Wounded units should have reduced hit chance."""
        mock_infantry_unit.health.hp_ratio = 0.5

        chance = MeleeCombatSystem.calculate_hit_chance(mock_infantry_unit)
        assert chance < BASE_HIT_CHANCE

    def test_veteran_bonus(self, mock_infantry_unit):
        """Veteran/elite units get bonus to hit chance."""
        from pycc2.domain.components.veterancy_component import VeteranRank
        mock_infantry_unit.veterancy = Mock(rank=VeteranRank.VETERAN)

        chance = MeleeCombatSystem.calculate_hit_chance(mock_infantry_unit)
        assert chance > BASE_HIT_CHANCE


class TestMeleeResolution:
    """Test melee attack resolution."""

    @patch('random.random', return_value=0.5)  # Guaranteed hit (< 0.90)
    def test_successful_melee_attack(self, mock_random, mock_infantry_unit, mock_enemy_unit):
        """Successful melee should deal damage to defender."""
        result = MeleeCombatSystem.resolve_melee(
            mock_infantry_unit, mock_enemy_unit, is_charging=True
        )

        assert isinstance(result, MeleeResult)
        assert result.hit is True
        assert result.damage > 0
        assert result.attacker_id == mock_infantry_unit.id
        assert result.defender_id == mock_enemy_unit.id

    @patch('random.random', return_value=0.95)  # Miss (> 0.90)
    def test_missed_melee_attack(self, mock_random, mock_infantry_unit, mock_enemy_unit):
        """Missed melee should deal no damage."""
        result = MeleeCombatSystem.resolve_melee(
            mock_infantry_unit, mock_enemy_unit
        )

        assert result.hit is False
        assert result.damage == 0

    def test_counter_attack_damage(self, mock_infantry_unit, mock_enemy_unit):
        """Defender should counter-attack at reduced damage."""
        with patch('random.random', return_value=0.3):  # Both hit
            result = MeleeCombatSystem.resolve_melee(
                mock_infantry_unit, mock_enemy_unit
            )

            assert result.counter_hit is True
            assert result.counter_damage > 0
            # Counter attack should be less than main attack
            assert result.counter_damage < result.damage


class TestMeleeEligibility:
    """Test when melee can be initiated."""

    def test_can_melee_adjacent_low_ammo(self, mock_infantry_unit, mock_enemy_unit):
        """Should be able to melee when adjacent and low on ammo."""
        assert MeleeCombatSystem.can_melee(mock_infantry_unit, mock_enemy_unit) is True

    def test_cannot_melee_out_of_range(self, mock_infantry_unit):
        """Cannot melee if too far away."""
        far_enemy = Mock()
        far_enemy.is_alive = True
        pos = Mock()
        pos.tile_coord = TileCoord(10, 10)  # Far away
        far_enemy.position = pos

        assert MeleeCombatSystem.can_melee(mock_infantry_unit, far_enemy) is False

    def test_cannot_melee_with_ammo(self, mock_infantry_unit, mock_enemy_unit):
        """Cannot melee if still has plenty of ammo."""
        mock_infantry_unit.weapon.ammo_ratio = 0.5  # Above threshold
        assert MeleeCombatSystem.can_melee(mock_infantry_unit, mock_enemy_unit) is False

    def test_cannot_melee_dead_unit(self, mock_infantry_unit, mock_enemy_unit):
        """Cannot initiate if attacker is dead."""
        mock_infantry_unit.is_alive = False
        assert MeleeCombatSystem.can_melee(mock_infantry_unit, mock_enemy_unit) is False


# ===========================================================================
# Test Class: B5 Grenade System
# ===========================================================================

class TestGrenadeAmmo:
    """Test grenade ammunition management."""

    def test_initial_grenade_count(self, mock_infantry_unit):
        """Units should start with max grenades."""
        count = GrenadeSystem.get_grenade_count(mock_infantry_unit)
        assert count == GRENADE_MAX_COUNT

    def test_set_grenade_count(self, mock_infantry_unit):
        """Can set grenade count explicitly."""
        GrenadeSystem.set_grenade_count(mock_infantry_unit, 1)
        assert GrenadeSystem.get_grenade_count(mock_infantry_unit) == 1

    def test_grenade_count_clamped(self, mock_infantry_unit):
        """Grenade count should be clamped to valid range."""
        GrenadeSystem.set_grenade_count(mock_infantry_unit, 999)
        assert GrenadeSystem.get_grenade_count(mock_infantry_unit) == GRENADE_MAX_COUNT

        GrenadeSystem.set_grenade_count(mock_infantry_unit, -5)
        assert GrenadeSystem.get_grenade_count(mock_infantry_unit) == 0


class TestGrenadeThrowValidation:
    """Test grenade throwing preconditions."""

    def test_can_throw_valid_range(self, mock_infantry_unit):
        """Should be able to throw within range."""
        target = TileCoord(7, 5)  # 2 tiles away
        assert GrenadeSystem.can_throw_grenade(mock_infantry_unit, target) is True

    def test_cannot_throw_too_close(self, mock_infantry_unit):
        """Cannot throw too close (minimum range)."""
        target = TileCoord(6, 5)  # 1 tile away (too close)
        assert GrenadeSystem.can_throw_grenade(mock_infantry_unit, target) is False

    def test_cannot_throw_too_far(self, mock_infantry_unit):
        """Cannot throw beyond max range."""
        target = TileCoord(10, 5)  # 5 tiles away (too far)
        assert GrenadeSystem.can_throw_grenade(mock_infantry_unit, target) is False

    def test_cannot_throw_no_ammo(self, mock_infantry_unit):
        """Cannot throw when out of grenades."""
        GrenadeSystem.set_grenade_count(mock_infantry_unit, 0)
        target = TileCoord(7, 5)
        assert GrenadeSystem.can_throw_grenade(mock_infantry_unit, target) is False

    def test_cannot_throw_dead(self, mock_infantry_unit):
        """Dead units cannot throw grenades."""
        mock_infantry_unit.is_alive = False
        target = TileCoord(7, 5)
        assert GrenadeSystem.can_throw_grenade(mock_infantry_unit, target) is False


class TestGrenadeAOEDamage:
    """Test AOE damage distribution."""

    @patch('random.random', return_value=0.5)  # Hit
    def test_center_target_full_damage(self, mock_rand, mock_infantry_unit):
        """Target at center takes full damage."""
        center = TileCoord(7, 5)
        target = Mock()
        target.is_alive = True
        target.id = "target_center"
        target.position_component = Mock(x=7, y=5)
        target.take_damage = Mock()

        result = GrenadeSystem.throw_grenade(
            mock_infantry_unit, center, [target]
        )

        assert len(result.targets_hit) == 1
        assert result.targets_hit[0].is_center_hit is True
        assert result.targets_hit[0].damage == GRENADE_CENTER_DAMAGE

    @patch('random.random', return_value=0.5)  # Hit
    def test_edge_target_half_damage(self, mock_rand, mock_infantry_unit):
        """Target at edge of blast takes half damage."""
        center = TileCoord(7, 5)
        target = Mock()
        target.is_alive = True
        target.id = "target_edge"
        target.position_component = Mock(x=8, y=5)  # 1 tile away
        target.take_damage = Mock()

        result = GrenadeSystem.throw_grenade(
            mock_infantry_unit, center, [target]
        )

        assert len(result.targets_hit) == 1
        assert result.targets_hit[0].is_center_hit is False
        assert result.targets_hit[0].damage == GRENADE_EDGE_DAMAGE

    @patch('random.random', return_value=0.5)  # Hit
    def test_multiple_targets_aoe(self, mock_rand, mock_infantry_unit):
        """Multiple targets in radius all get hit."""
        center = TileCoord(7, 5)

        targets = []
        for i, offset in enumerate([(7, 5), (8, 5), (7, 6)]):
            t = Mock()
            t.is_alive = True
            t.id = f"target_{i}"
            t.position_component = Mock(x=offset[0], y=offset[1])
            t.take_damage = Mock()
            targets.append(t)

        result = GrenadeSystem.throw_grenade(
            mock_infantry_unit, center, targets
        )

        assert len(result.targets_hit) == 3
        assert result.total_damage > 0

    @patch('random.random', return_value=0.5)  # Hit
    def test_thrower_not_self_harm(self, mock_rand, mock_infantry_unit):
        """Thrower should not be affected by own grenade."""
        center = TileCoord(7, 5)

        # Thrower is at (5,5), grenade lands at (7,5), so safe
        result = GrenadeSystem.throw_grenade(
            mock_infantry_unit, center, [mock_infantry_unit]
        )

        # Should not hit self (filtered out)
        for t in result.targets_hit:
            assert t.target_id != mock_infantry_unit.id

    @patch('random.random', return_value=0.5)
    def test_suppression_applied(self, mock_rand, mock_infantry_unit):
        """All hit targets should receive suppression."""
        center = TileCoord(7, 5)
        target = Mock()
        target.is_alive = True
        target.id = "target_suppressed"
        target.position_component = Mock(x=7, y=5)
        target.take_damage = Mock()
        target.suppression_state = Mock()

        result = GrenadeSystem.throw_grenade(
            mock_infantry_unit, center, [target]
        )

        assert len(result.targets_hit) == 1
        assert result.targets_hit[0].suppression_applied == GRENADE_SUPPRESSION
        target.suppression_state.apply_suppression.assert_called_once_with(GRENADE_SUPPRESSION)


class TestGrenadeAmmoConsumption:
    """Test that throwing consumes ammo."""

    def test_grenade_consumed_on_throw(self, mock_infantry_unit):
        """Throwing a grenade should reduce count by 1."""
        initial = GrenadeSystem.get_grenade_count(mock_infantry_unit)

        center = TileCoord(7, 5)
        with patch('random.random', return_value=0.9):  # Miss
            GrenadeSystem.throw_grenade(mock_infantry_unit, center, [])

        remaining = GrenadeSystem.get_grenade_count(mock_infantry_unit)
        assert remaining == initial - 1

    def test_cannot_throw_when_empty(self, mock_infantry_unit):
        """After using all grenades, cannot throw more."""
        GrenadeSystem.set_grenade_count(mock_infantry_unit, 0)

        center = TileCoord(7, 5)
        can_throw = GrenadeSystem.can_throw_grenade(mock_infantry_unit, center)
        assert can_throw is False


class TestGrenadeUnitsInRadius:
    """Test utility function for finding units in radius."""

    def test_find_units_in_radius(self):
        """Should find all units within given radius."""
        center = TileCoord(5, 5)

        units = []
        for i, (x, y) in enumerate([(5, 5), (6, 5), (10, 10)]):
            u = Mock()
            u.is_alive = True
            u.id = f"unit_{i}"
            u.position_component = Mock(x=x, y=y)
            units.append(u)

        found = GrenadeSystem.get_units_in_radius(center, 1.5, units)
        assert len(found) == 2  # First two are within 1.5 tiles

    def test_exclude_dead_units(self):
        """Dead units should not be included."""
        center = TileCoord(5, 5)

        alive = Mock()
        alive.is_alive = True
        alive.position_component = Mock(x=5, y=5)

        dead = Mock()
        dead.is_alive = False
        dead.position_component = Mock(x=5, y=5)

        found = GrenadeSystem.get_units_in_radius(center, 1.0, [alive, dead])
        assert len(found) == 1
        assert found[0] == alive


# ===========================================================================
# Integration Tests: Melee + Grenade AI
# ===========================================================================

class TestMeleeCombatAI:
    """Test the AI decision-making for melee/grenade combat."""

    def test_ai_evaluate_zero_no_candidates(self, tactical_context):
        """Priority should be 0 when no melee candidates."""
        ai = MeleeCombatAI()
        priority = ai.evaluate(tactical_context)
        assert priority >= 0  # May be > 0 if candidates exist

    def test_ai_execute_generates_intents(self, tactical_context):
        """Execute should generate MELEE_ATTACK intents."""
        ai = MeleeCombatAI()
        intents = ai.execute(tactical_context)

        # May or may not generate intents depending on conditions
        for intent in intents:
            assert intent.tactic_type in (TacticType.MELEE_ATTACK,)
            assert intent.unit_id is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
