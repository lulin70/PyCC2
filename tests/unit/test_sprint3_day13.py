"""Sprint 3 Day 13 Tests - FUNC-06 Combat System.

Tests for:
- Combat system (auto-attack, damage, death)
- Life bar UI rendering
- Attack range and cooldown mechanics
"""

import pytest
import pygame

from pycc2.domain.systems.combat_system import (
    CombatSystem,
    SimpleCombatUnit,
    CombatState,
)
from pycc2.presentation.ui.life_bar_ui import (
    LifeBarUI,
    LifeBarUIExtended,
)


class TestSimpleCombatUnit:
    """Test SimpleCombatUnit entity."""
    
    def test_unit_creation(self):
        """Test creating combat unit."""
        unit = SimpleCombatUnit(
            id="unit1",
            faction="PLAYER",
            position_x=0.0,
            position_y=0.0,
            hp=100,
            max_hp=100,
        )
        
        assert unit.id == "unit1"
        assert unit.is_alive()
        assert unit.combat_state == CombatState.IDLE
    
    def test_unit_is_enemy(self):
        """Test enemy detection."""
        unit1 = SimpleCombatUnit("u1", "PLAYER", 0.0, 0.0, 100, 100)
        unit2 = SimpleCombatUnit("u2", "ENEMY", 50.0, 0.0, 100, 100)
        unit3 = SimpleCombatUnit("u3", "PLAYER", 100.0, 0.0, 100, 100)
        
        assert unit1.is_enemy(unit2)
        assert not unit1.is_enemy(unit3)
    
    def test_unit_distance_calculation(self):
        """Test distance calculation between units."""
        unit1 = SimpleCombatUnit("u1", "PLAYER", 0.0, 0.0, 100, 100)
        unit2 = SimpleCombatUnit("u2", "ENEMY", 30.0, 40.0, 100, 100)
        
        distance = unit1.distance_to(unit2)
        assert abs(distance - 50.0) < 0.1  # 3-4-5 triangle
    
    def test_unit_can_attack_validation(self):
        """Test can_attack() validation logic."""
        attacker = SimpleCombatUnit("u1", "PLAYER", 0.0, 0.0, 100, 100, attack_range=100.0)
        
        # Enemy in range
        target_in_range = SimpleCombatUnit("u2", "ENEMY", 50.0, 0.0, 100, 100)
        assert attacker.can_attack(target_in_range)
        
        # Enemy out of range
        target_far = SimpleCombatUnit("u3", "ENEMY", 150.0, 0.0, 100, 100)
        assert not attacker.can_attack(target_far)
        
        # Ally (can't attack)
        ally = SimpleCombatUnit("u4", "PLAYER", 50.0, 0.0, 100, 100)
        assert not attacker.can_attack(ally)
        
        # Cooldown not ready
        attacker.cooldown_timer = 0.5
        assert not attacker.can_attack(target_in_range)
    
    def test_unit_take_damage_and_death(self):
        """Test damage and death mechanics."""
        unit = SimpleCombatUnit("u1", "PLAYER", 0.0, 0.0, 100, 100)
        
        # Take damage (not lethal)
        died = unit.take_damage(30)
        assert not died
        assert unit.hp == 70
        assert unit.is_alive()
        
        # Take lethal damage
        died = unit.take_damage(80)
        assert died
        assert unit.hp == 0
        assert not unit.is_alive()
        assert unit.combat_state == CombatState.DEAD


class TestCombatSystem:
    """Test CombatSystem logic."""
    
    def test_combat_system_add_remove_units(self):
        """Test adding and removing units."""
        combat = CombatSystem()
        unit = SimpleCombatUnit("u1", "PLAYER", 0.0, 0.0, 100, 100)
        
        combat.add_unit(unit)
        assert len(combat.units) == 1
        
        removed = combat.remove_unit("u1")
        assert removed
        assert len(combat.units) == 0
    
    def test_find_nearest_enemy(self):
        """Test finding nearest enemy in range."""
        combat = CombatSystem()
        
        attacker = SimpleCombatUnit("u1", "PLAYER", 0.0, 0.0, 100, 100, attack_range=100.0)
        enemy1 = SimpleCombatUnit("e1", "ENEMY", 30.0, 0.0, 100, 100)
        enemy2 = SimpleCombatUnit("e2", "ENEMY", 60.0, 0.0, 100, 100)
        
        combat.add_unit(attacker)
        combat.add_unit(enemy1)
        combat.add_unit(enemy2)
        
        nearest = combat.find_nearest_enemy(attacker)
        assert nearest is not None
        assert nearest.id == "e1"  # Closer than e2
    
    def test_execute_attack_damages_target(self):
        """Test execute_attack applies damage and cooldown."""
        combat = CombatSystem()
        
        attacker = SimpleCombatUnit("u1", "PLAYER", 0.0, 0.0, 100, 100, attack_damage=20, attack_cooldown=1.0)
        target = SimpleCombatUnit("e1", "ENEMY", 50.0, 0.0, 100, 100)
        
        combat.add_unit(attacker)
        combat.add_unit(target)
        
        # Execute attack
        combat.execute_attack(attacker, target)
        
        # Verify damage
        assert target.hp == 80
        
        # Verify cooldown
        assert attacker.cooldown_timer == 1.0
        
        # Verify notification
        assert len(combat.attack_notifications) == 1
        assert combat.attack_notifications[0] == ("u1", "e1", 20)
    
    def test_execute_attack_kills_target(self):
        """Test execute_attack handles target death."""
        combat = CombatSystem()
        
        attacker = SimpleCombatUnit("u1", "PLAYER", 0.0, 0.0, 100, 100, attack_damage=100)
        target = SimpleCombatUnit("e1", "ENEMY", 50.0, 0.0, 50, 100)  # Only 50 HP
        
        combat.add_unit(attacker)
        combat.add_unit(target)
        
        # Execute lethal attack
        combat.execute_attack(attacker, target)
        
        # Verify death
        assert not target.is_alive()
        assert len(combat.death_notifications) == 1
        assert combat.death_notifications[0] == "e1"
    
    def test_update_unit_combat_acquires_target(self):
        """Test update_unit_combat finds and attacks nearest enemy."""
        combat = CombatSystem()
        
        attacker = SimpleCombatUnit("u1", "PLAYER", 0.0, 0.0, 100, 100, attack_range=100.0)
        enemy = SimpleCombatUnit("e1", "ENEMY", 50.0, 0.0, 100, 100)
        
        combat.add_unit(attacker)
        combat.add_unit(enemy)
        
        # Update (should find target)
        combat.update_unit_combat(attacker, delta_time=0.016)
        
        # Verify target acquired
        assert attacker.current_target_id == "e1"
        assert attacker.combat_state == CombatState.ATTACKING
    
    def test_update_full_combat_cycle(self):
        """Test full update cycle with cooldown."""
        combat = CombatSystem()
        
        # Setup: 1 player vs 1 enemy (enemy has 0 attack range, won't counter-attack)
        p1 = SimpleCombatUnit("p1", "PLAYER", 0.0, 0.0, 100, 100, attack_damage=30, attack_cooldown=0.5)
        e1 = SimpleCombatUnit("e1", "ENEMY", 50.0, 0.0, 100, 100, attack_range=0.0)  # Can't attack back
        
        combat.add_unit(p1)
        combat.add_unit(e1)
        
        # Frame 1: Initial attack (only p1 attacks)
        combat.update(delta_time=0.016)
        assert len(combat.attack_notifications) == 1
        assert combat.attack_notifications[0][0] == "p1"  # p1 attacked
        assert p1.cooldown_timer == 0.5
        
        # Frames 2-31: Cooldown period (30 frames × 0.016s = 0.48s)
        for _ in range(30):
            combat.update(delta_time=0.016)
            assert len(combat.attack_notifications) == 0  # No attack during cooldown
        
        # Frame 32: Cooldown expires (0.48 + 0.016 = 0.496s < 0.5s, need one more)
        combat.update(delta_time=0.016)
        if len(combat.attack_notifications) == 0:
            # Need one more frame
            combat.update(delta_time=0.016)
        assert len(combat.attack_notifications) == 1  # Second attack
        assert p1.cooldown_timer == 0.5  # Cooldown reset
    
    def test_combat_system_gets_alive_dead_units(self):
        """Test get_alive_units and get_dead_units filters."""
        combat = CombatSystem()
        
        alive1 = SimpleCombatUnit("u1", "PLAYER", 0.0, 0.0, 100, 100)
        alive2 = SimpleCombatUnit("u2", "PLAYER", 10.0, 0.0, 80, 100)
        dead = SimpleCombatUnit("u3", "PLAYER", 20.0, 0.0, 0, 100, combat_state=CombatState.DEAD)
        
        combat.add_unit(alive1)
        combat.add_unit(alive2)
        combat.add_unit(dead)
        
        alive_units = combat.get_alive_units()
        dead_units = combat.get_dead_units()
        
        assert len(alive_units) == 2
        assert len(dead_units) == 1
        assert dead in dead_units


class TestLifeBarUI:
    """Test LifeBarUI rendering."""
    
    @pytest.fixture
    def screen(self):
        """Create pygame screen surface."""
        pygame.init()
        return pygame.Surface((800, 600))
    
    def test_life_bar_ui_initialization(self):
        """Test LifeBarUI initialization."""
        life_bar = LifeBarUI(bar_width=50, bar_height=5, offset_y=-25)
        
        assert life_bar.bar_width == 50
        assert life_bar.bar_height == 5
        assert life_bar.offset_y == -25
    
    def test_get_hp_color(self):
        """Test HP color calculation."""
        life_bar = LifeBarUI()
        
        # High HP (>66%)
        color_high = life_bar.get_hp_color(0.8)
        assert color_high == (0, 255, 0)  # Green
        
        # Medium HP (33-66%)
        color_medium = life_bar.get_hp_color(0.5)
        assert color_medium == (255, 255, 0)  # Yellow
        
        # Low HP (<33%)
        color_low = life_bar.get_hp_color(0.2)
        assert color_low == (255, 0, 0)  # Red
    
    def test_render_life_bar_without_crash(self, screen):
        """Test render_life_bar executes without errors."""
        life_bar = LifeBarUI()
        
        # Should not raise exception
        life_bar.render_life_bar(screen, unit_screen_x=400, unit_screen_y=300, hp=50, max_hp=100)
    
    def test_render_batch_multiple_units(self, screen):
        """Test render_batch renders multiple units."""
        life_bar = LifeBarUI()
        
        units = [
            (100, 100, 80, 100),
            (200, 150, 50, 100),
            (300, 200, 20, 100),
        ]
        
        # Should not raise exception
        life_bar.render_batch(screen, units)
    
    def test_extended_life_bar_with_text(self, screen):
        """Test LifeBarUIExtended with HP text."""
        life_bar = LifeBarUIExtended(show_text=True, font_size=14)
        
        assert life_bar.show_text
        assert life_bar.font is not None
        
        # Should not raise exception
        life_bar.render_life_bar(screen, 400, 300, 75, 100)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
