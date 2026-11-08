"""Combat System Integration Tests - Sprint 3 Day 14 TEST-06.

End-to-end and edge-case tests for combat system integration.
Covers complete battle scenarios, boundary conditions, and multi-unit combat.
"""

import pytest
from pycc2.domain.systems.combat_system import (
    CombatSystem,
    SimpleCombatUnit,
    CombatState,
)


class TestCombatIntegrationE2E:
    """End-to-end combat integration tests."""
    
    def test_complete_battle_scenario_two_factions(self):
        """Test complete battle: 2 red units vs 2 blue units until all one faction dies."""
        system = CombatSystem()
        
        # Red faction (weaker, will lose)
        red1 = SimpleCombatUnit(
            id="red1",
            faction="red",
            position_x=0.0,
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=10,
            attack_range=150.0,
            attack_cooldown=1.0,
        )
        red2 = SimpleCombatUnit(
            id="red2",
            faction="red",
            position_x=20.0,
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=10,
            attack_range=150.0,
            attack_cooldown=1.0,
        )
        
        # Blue faction (stronger, will win)
        blue1 = SimpleCombatUnit(
            id="blue1",
            faction="blue",
            position_x=100.0,
            position_y=0.0,
            hp=80,
            max_hp=80,
            attack_damage=15,
            attack_range=150.0,
            attack_cooldown=1.0,
        )
        blue2 = SimpleCombatUnit(
            id="blue2",
            faction="blue",
            position_x=120.0,
            position_y=0.0,
            hp=80,
            max_hp=80,
            attack_damage=15,
            attack_range=150.0,
            attack_cooldown=1.0,
        )
        
        system.add_unit(red1)
        system.add_unit(red2)
        system.add_unit(blue1)
        system.add_unit(blue2)
        
        # Simulate battle (max 50 iterations = 50 seconds)
        for _ in range(50):
            system.update(delta_time=1.0)
            
            red_alive = [u for u in system.get_alive_units() if u.faction == "red"]
            blue_alive = [u for u in system.get_alive_units() if u.faction == "blue"]
            
            # Stop when one faction is eliminated
            if not red_alive or not blue_alive:
                break
        
        # Assert: Red faction should be eliminated (weaker)
        red_survivors = [u for u in system.get_alive_units() if u.faction == "red"]
        blue_survivors = [u for u in system.get_alive_units() if u.faction == "blue"]
        
        assert len(red_survivors) == 0, "Red faction should be eliminated"
        assert len(blue_survivors) > 0, "Blue faction should survive"
        
        # Assert: Both blue units should have taken damage
        assert blue1.hp < blue1.max_hp or blue2.hp < blue2.max_hp
    
    def test_single_unit_vs_multiple_enemies(self):
        """Test single unit fighting multiple enemies (should lose)."""
        system = CombatSystem()
        
        # Single defender
        defender = SimpleCombatUnit(
            id="defender",
            faction="defender",
            position_x=50.0,
            position_y=50.0,
            hp=100,
            max_hp=100,
            attack_damage=10,
            attack_range=100.0,
            attack_cooldown=1.0,
        )
        
        # Three attackers
        attackers = [
            SimpleCombatUnit(
                id=f"attacker{i}",
                faction="attacker",
                position_x=50.0 + i * 20.0,
                position_y=100.0,
                hp=50,
                max_hp=50,
                attack_damage=15,
                attack_range=100.0,
                attack_cooldown=1.0,
            )
            for i in range(3)
        ]
        
        system.add_unit(defender)
        for atk in attackers:
            system.add_unit(atk)
        
        # Simulate battle
        for _ in range(30):
            system.update(delta_time=1.0)
            if not defender.is_alive():
                break
        
        # Assert: Defender should be killed by 3v1
        assert not defender.is_alive()
        assert defender.combat_state == CombatState.DEAD
        
        # Assert: At least one attacker should survive
        survivors = [a for a in attackers if a.is_alive()]
        assert len(survivors) > 0
    
    def test_combat_with_unit_reinforcements(self):
        """Test adding new units mid-combat."""
        system = CombatSystem()
        
        # Initial combatants
        red = SimpleCombatUnit(
            id="red",
            faction="red",
            position_x=0.0,
            position_y=0.0,
            hp=60,
            max_hp=60,
            attack_damage=10,
            attack_range=120.0,
            attack_cooldown=1.0,
        )
        blue = SimpleCombatUnit(
            id="blue",
            faction="blue",
            position_x=100.0,
            position_y=0.0,
            hp=60,
            max_hp=60,
            attack_damage=10,
            attack_range=120.0,
            attack_cooldown=1.0,
        )
        
        system.add_unit(red)
        system.add_unit(blue)
        
        # Fight for 3 seconds
        for _ in range(3):
            system.update(delta_time=1.0)
        
        # Add reinforcement for blue
        reinforcement = SimpleCombatUnit(
            id="blue_reinforcement",
            faction="blue",
            position_x=110.0,
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=15,
            attack_range=120.0,
            attack_cooldown=1.0,
        )
        system.add_unit(reinforcement)
        
        # Continue battle
        for _ in range(20):
            system.update(delta_time=1.0)
            if not red.is_alive():
                break
        
        # Assert: Red should be killed (outnumbered after reinforcement)
        assert not red.is_alive()
        assert blue.is_alive() or reinforcement.is_alive()
    
    def test_simultaneous_kills(self):
        """Test two units killing each other simultaneously (edge case)."""
        system = CombatSystem()
        
        # Two units with same stats
        unit1 = SimpleCombatUnit(
            id="unit1",
            faction="faction1",
            position_x=0.0,
            position_y=0.0,
            hp=15,  # Dies in 1 hit
            max_hp=15,
            attack_damage=15,
            attack_range=100.0,
            attack_cooldown=1.0,
        )
        unit2 = SimpleCombatUnit(
            id="unit2",
            faction="faction2",
            position_x=50.0,
            position_y=0.0,
            hp=15,  # Dies in 1 hit
            max_hp=15,
            attack_damage=15,
            attack_range=100.0,
            attack_cooldown=1.0,
        )
        
        system.add_unit(unit1)
        system.add_unit(unit2)
        
        # Update until at least one dies
        for _ in range(10):
            system.update(delta_time=1.0)
            if not unit1.is_alive() or not unit2.is_alive():
                break
        
        # Assert: At least one should be dead (mutual combat)
        assert not unit1.is_alive() or not unit2.is_alive()
        alive_units = system.get_alive_units()
        # In mutual combat, both may die or one survives
        assert len(alive_units) <= 1


class TestCombatBoundaryConditions:
    """Boundary and edge case tests."""
    
    def test_attack_out_of_range(self):
        """Test units cannot attack beyond range."""
        system = CombatSystem()
        
        attacker = SimpleCombatUnit(
            id="attacker",
            faction="red",
            position_x=0.0,
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=20,
            attack_range=50.0,  # Short range
            attack_cooldown=1.0,
        )
        target = SimpleCombatUnit(
            id="target",
            faction="blue",
            position_x=200.0,  # Far away
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=10,
            attack_range=50.0,
            attack_cooldown=1.0,
        )
        
        system.add_unit(attacker)
        system.add_unit(target)
        
        # Update combat (should not attack due to range)
        for _ in range(5):
            system.update(delta_time=1.0)
        
        # Assert: No damage dealt (out of range)
        assert target.hp == target.max_hp
        assert attacker.hp == attacker.max_hp
        assert attacker.combat_state == CombatState.IDLE
    
    def test_friendly_fire_prevention(self):
        """Test units do not attack allies."""
        system = CombatSystem()
        
        ally1 = SimpleCombatUnit(
            id="ally1",
            faction="team_blue",
            position_x=0.0,
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=999,  # High damage
            attack_range=100.0,
            attack_cooldown=1.0,
        )
        ally2 = SimpleCombatUnit(
            id="ally2",
            faction="team_blue",  # Same faction
            position_x=50.0,
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=999,
            attack_range=100.0,
            attack_cooldown=1.0,
        )
        
        system.add_unit(ally1)
        system.add_unit(ally2)
        
        # Update combat (should not attack each other)
        for _ in range(10):
            system.update(delta_time=1.0)
        
        # Assert: No damage dealt (allies)
        assert ally1.hp == ally1.max_hp
        assert ally2.hp == ally2.max_hp
        assert ally1.combat_state == CombatState.IDLE
        assert ally2.combat_state == CombatState.IDLE
    
    def test_dead_unit_cannot_attack(self):
        """Test dead units stop attacking."""
        system = CombatSystem()
        
        attacker = SimpleCombatUnit(
            id="attacker",
            faction="red",
            position_x=0.0,
            position_y=0.0,
            hp=0,  # Already dead
            max_hp=50,
            attack_damage=20,
            attack_range=100.0,
            attack_cooldown=1.0,
            combat_state=CombatState.DEAD,
        )
        target = SimpleCombatUnit(
            id="target",
            faction="blue",
            position_x=50.0,
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=10,
            attack_range=100.0,
            attack_cooldown=1.0,
        )
        
        system.add_unit(attacker)
        system.add_unit(target)
        
        # Update combat
        for _ in range(5):
            system.update(delta_time=1.0)
        
        # Assert: Dead unit cannot attack
        assert target.hp == target.max_hp
        assert len(system.attack_notifications) == 0
    
    def test_attack_cooldown_enforcement(self):
        """Test attack cooldown prevents rapid attacks."""
        system = CombatSystem()
        
        attacker = SimpleCombatUnit(
            id="attacker",
            faction="red",
            position_x=0.0,
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=10,
            attack_range=100.0,
            attack_cooldown=2.0,  # 2 second cooldown
        )
        target = SimpleCombatUnit(
            id="target",
            faction="blue",
            position_x=50.0,
            position_y=0.0,
            hp=100,
            max_hp=100,
            attack_damage=0,  # Cannot counterattack
            attack_range=0.0,
            attack_cooldown=1.0,
        )
        
        system.add_unit(attacker)
        system.add_unit(target)
        
        # Update with enough time for first attack
        system.update(delta_time=2.0)
        hp_after_first = target.hp
        
        # Update with insufficient time (cooldown not ready)
        system.update(delta_time=0.5)
        hp_after_short_wait = target.hp
        
        # Assert: First attack landed, second did not
        assert hp_after_first == 90, f"First attack should deal damage: {hp_after_first}"
        assert hp_after_short_wait == 90, f"No damage during cooldown: {hp_after_short_wait}"
        
        # Update with sufficient time for second attack
        system.update(delta_time=2.0)
        hp_after_second = target.hp
        
        # Assert: Second attack landed
        assert hp_after_second == 80, f"Second attack should deal damage: {hp_after_second}"
    
    def test_empty_combat_system(self):
        """Test combat system with no units."""
        system = CombatSystem()
        
        # Update empty system (should not crash)
        system.update(delta_time=1.0)
        
        # Assert: No crashes, no notifications
        assert len(system.get_alive_units()) == 0
        assert len(system.attack_notifications) == 0
        assert len(system.death_notifications) == 0
    
    def test_single_unit_alone(self):
        """Test single unit with no enemies."""
        system = CombatSystem()
        
        loner = SimpleCombatUnit(
            id="loner",
            faction="lonely",
            position_x=50.0,
            position_y=50.0,
            hp=50,
            max_hp=50,
            attack_damage=10,
            attack_range=100.0,
            attack_cooldown=1.0,
        )
        
        system.add_unit(loner)
        
        # Update combat (should remain idle)
        for _ in range(10):
            system.update(delta_time=1.0)
        
        # Assert: Unit remains idle with full HP
        assert loner.hp == loner.max_hp
        assert loner.combat_state == CombatState.IDLE
        assert loner.current_target_id is None
    
    def test_target_dies_mid_combat(self):
        """Test attacker switches target when current target dies."""
        system = CombatSystem()
        
        attacker = SimpleCombatUnit(
            id="attacker",
            faction="red",
            position_x=50.0,
            position_y=50.0,
            hp=100,
            max_hp=100,
            attack_damage=30,
            attack_range=150.0,
            attack_cooldown=1.0,
        )
        
        # Two weak targets
        target1 = SimpleCombatUnit(
            id="target1",
            faction="blue",
            position_x=100.0,
            position_y=50.0,
            hp=15,  # Dies in 1 hit
            max_hp=15,
            attack_damage=0,
            attack_range=0.0,
            attack_cooldown=1.0,
        )
        target2 = SimpleCombatUnit(
            id="target2",
            faction="blue",
            position_x=120.0,
            position_y=50.0,
            hp=15,  # Dies in 1 hit
            max_hp=15,
            attack_damage=0,
            attack_range=0.0,
            attack_cooldown=1.0,
        )
        
        system.add_unit(attacker)
        system.add_unit(target1)
        system.add_unit(target2)
        
        # Track deaths across frames
        total_deaths = set()
        
        # Simulate combat until both targets dead
        for _ in range(10):
            system.update(delta_time=1.0)
            total_deaths.update(system.death_notifications)
            if not target1.is_alive() and not target2.is_alive():
                break
        
        # Assert: Both targets should be dead
        assert not target1.is_alive()
        assert not target2.is_alive()
        
        # Assert: Attacker should have killed both (switched targets)
        assert "target1" in total_deaths
        assert "target2" in total_deaths


class TestCombatNotifications:
    """Test combat event notification system."""
    
    def test_attack_notifications_recorded(self):
        """Test attack events are recorded correctly."""
        system = CombatSystem()
        
        attacker = SimpleCombatUnit(
            id="attacker",
            faction="red",
            position_x=0.0,
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=15,
            attack_range=100.0,
            attack_cooldown=1.0,
        )
        target = SimpleCombatUnit(
            id="target",
            faction="blue",
            position_x=50.0,
            position_y=0.0,
            hp=100,
            max_hp=100,
            attack_damage=0,  # Cannot counterattack
            attack_range=0.0,  # No range
            attack_cooldown=1.0,
        )
        
        system.add_unit(attacker)
        system.add_unit(target)
        
        # Update: attack should occur
        system.update(delta_time=1.0)
        
        # Assert: Attack notification recorded (notifications cleared each frame)
        assert len(system.attack_notifications) >= 1
        # Find attacker's notification
        attacker_notif = [n for n in system.attack_notifications if n[0] == "attacker"]
        assert len(attacker_notif) == 1
        notification = attacker_notif[0]
        assert notification[1] == "target"    # target_id
        assert notification[2] == 15          # damage
    
    def test_death_notifications_recorded(self):
        """Test death events are recorded correctly."""
        system = CombatSystem()
        
        attacker = SimpleCombatUnit(
            id="killer",
            faction="red",
            position_x=0.0,
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=100,  # Instant kill
            attack_range=100.0,
            attack_cooldown=1.0,
        )
        victim = SimpleCombatUnit(
            id="victim",
            faction="blue",
            position_x=50.0,
            position_y=0.0,
            hp=50,
            max_hp=50,
            attack_damage=0,
            attack_range=0.0,  # Cannot counterattack
            attack_cooldown=1.0,
        )
        
        system.add_unit(attacker)
        system.add_unit(victim)
        
        # Update: attack and kill in one frame
        death_recorded = False
        for _ in range(5):
            system.update(delta_time=1.0)
            if "victim" in system.death_notifications:
                death_recorded = True
                break
        
        # Assert: Death notification recorded and victim is dead
        assert death_recorded, "Death notification should be recorded"
        assert not victim.is_alive()

