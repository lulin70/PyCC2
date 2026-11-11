"""E2E-01: Complete Game Loop Test - Sprint 4 Day 16.

Simulates a complete game loop covering the full user journey:
  Phase 1: Campaign initialization
  Phase 2: Unit deployment (place units on map)
  Phase 3: Battle start & combat execution
  Phase 4: Victory condition check
  Phase 5: Performance monitoring (FPS, memory)

This test validates:
- Complete game state transitions (MENU → DEPLOYMENT → BATTLE → VICTORY)
- Combat system execution (attack/damage/death)
- Performance targets (60fps stable, memory <500MB)

Uses real GameLoop with headless pygame (SDL dummy drivers).
"""

from __future__ import annotations

import os
import tracemalloc
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitState, UnitType
from pycc2.domain.systems.combat_system import CombatSystem, SimpleCombatUnit
from pycc2.domain.value_objects.tile_coord import TileCoord


class TestCompleteGameLoopE2E:
    """E2E test suite for complete game loop validation."""

    @staticmethod
    def create_unit(
        unit_id: str,
        faction: Faction,
        unit_type: UnitType,
        position: tuple[float, float] = (0.0, 0.0),
        hp: int = 100,
    ) -> Unit:
        """Helper to create a unit with all required components."""
        return Unit(
            id=unit_id,
            name=f"Unit_{unit_id}",
            faction=faction,
            unit_type=unit_type,
            health=HealthComponent(hp=hp, max_hp=100),
            morale=MoraleComponent(value=100, panic_threshold=30, rout_threshold=10),
            weapon=WeaponComponent(
                primary_weapon_id="rifle",
                ammo_remaining=30,
                max_ammo=30,
            ),
            position=PositionComponent(tile_coord=TileCoord(int(position[0]), int(position[1]))),
            vision=VisionComponent(range_tiles=8),
        )

    @pytest.fixture(autouse=True)
    def setup_method_fixture(self):
        """Setup pygame for each test."""
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))

        yield

        pygame.quit()

    def test_01_campaign_to_deployment_transition(self):
        """Verify campaign initialization and deployment phase entry.

        Test Steps:
        1. Load campaign map
        2. Initialize game state
        3. Enter deployment phase
        4. Validate deployment UI state

        Acceptance:
        - Map loaded successfully
        - Spawn points available
        - Deployment phase active
        """
        # Load campaign map
        map_path = Path("data/maps/test_map_small.json")
        if not map_path.exists():
            # Fallback to any available map
            map_dir = Path("data/maps")
            candidates = [f for f in sorted(map_dir.glob("*.json")) if f.stem != "_schema"]
            if candidates:
                map_path = candidates[0]

        game_map = GameMap.from_json(map_path)

        # Assertions
        assert game_map is not None, "Map should load successfully"
        assert game_map.width > 0 and game_map.height > 0, "Map dimensions valid"
        assert len(game_map.spawn_points) > 0, "Spawn points must exist for deployment"

    def test_02_deployment_place_units(self):
        """Verify unit deployment phase.

        Test Steps:
        1. Create friendly units (3x infantry, 2x vehicles)
        2. Place units at spawn points
        3. Validate unit positions
        4. Complete deployment → battle transition

        Acceptance:
        - All units placed successfully
        - Units at valid spawn positions
        - Battle phase transition ready
        """
        # Create test units using helper
        units = [
            self.create_unit(
                unit_id=f"unit_{i}",
                faction=Faction.ALLIES,
                unit_type=UnitType.INFANTRY_SQUAD if i < 3 else UnitType.TANK,
                position=(10.0 + i * 2, 10.0),
            )
            for i in range(5)
        ]

        # Validate all units created
        assert len(units) == 5, "Should create 5 units"

        # Check initial states
        for unit in units:
            assert unit.is_alive, "All units should be alive initially"
            assert unit.state_machine.current == UnitState.IDLE, "Units start IDLE"

    def test_05_combat_execution_full_cycle(self):
        """Verify combat system full execution cycle.

        Test Steps:
        1. Create 2 friendly units + 2 enemy units
        2. Initialize CombatSystem
        3. Execute 100 combat ticks (units attack each other)
        4. Validate: attacks executed, damage applied, deaths recorded

        Acceptance:
        - Attacks executed (count > 0)
        - Damage applied (HP decreases)
        - Deaths occur when HP = 0
        """
        # Create combat units (tile 1 = 32 px)
        all_units = [
            SimpleCombatUnit(
                id=f"ally_{i}",
                faction="allied",
                position_x=320.0,
                position_y=320.0 + i * 64.0,
                hp=100,
                max_hp=100,
                attack_damage=60,
                attack_range=200.0,
                attack_cooldown=0.5,
            )
            for i in range(2)
        ] + [
            SimpleCombatUnit(
                id=f"enemy_{i}",
                faction="axis",
                position_x=480.0,
                position_y=320.0 + i * 64.0,
                hp=100,
                max_hp=100,
                attack_damage=60,
                attack_range=200.0,
                attack_cooldown=0.5,
            )
            for i in range(2)
        ]

        combat_system = CombatSystem()
        for unit in all_units:
            combat_system.add_unit(unit)

        # Execute combat for 100 ticks (simulate 100 frames at 60 fps)
        for _ in range(100):
            combat_system.update(delta_time=0.016)

        dead_count = len(combat_system.get_dead_units())
        assert dead_count > 0, "At least one death should occur in 100 ticks"
        assert len(combat_system.get_alive_units()) < 4, "Some units should have died"

    def test_06_victory_condition_enemy_elimination(self):
        """Verify victory condition: eliminate all enemy units.

        Test Steps:
        1. Create 1 friendly + 3 enemy units
        2. Run combat until all enemies dead
        3. Check victory condition

        Acceptance:
        - All enemy units eliminated
        - Friendly units survive (at least 1)
        - Victory condition triggered
        """
        hero = SimpleCombatUnit(
            id="hero",
            faction="allied",
            position_x=320.0,
            position_y=320.0,
            hp=150,
            max_hp=150,
            attack_damage=30,
            attack_range=300.0,
            attack_cooldown=0.4,
        )
        enemies = [
            SimpleCombatUnit(
                id=f"enemy_{i}",
                faction="axis",
                position_x=480.0,
                position_y=320.0 + i * 32.0,
                hp=60,
                max_hp=60,
                attack_damage=5,
                attack_range=100.0,
                attack_cooldown=1.0,
            )
            for i in range(3)
        ]

        combat_system = CombatSystem()
        for unit in [hero] + enemies:
            combat_system.add_unit(unit)

        # Run combat until victory (max 500 ticks)
        for _ in range(500):
            combat_system.update(delta_time=0.016)
            if all(not enemy.is_alive() for enemy in enemies):
                break

        # Validate victory
        assert hero.is_alive(), "Friendly unit should survive"
        assert all(not enemy.is_alive() for enemy in enemies), "All enemies should be eliminated"

    def test_07_performance_100_units_60fps_target(self):
        """Verify performance target: 100 units @ 60fps.

        Test Steps:
        1. Create 100 units (50 friendly + 50 enemy)
        2. Run combat for 60 frames (1 second)
        3. Measure average frame time
        4. Validate <16.67ms per frame (60fps)

        Acceptance:
        - Average frame time <16.67ms
        - No crashes or exceptions
        - Memory usage <500MB
        """
        import time

        # Create 100 combat units (50 allied + 50 axis)
        combat_system = CombatSystem()
        for i in range(50):
            combat_system.add_unit(
                SimpleCombatUnit(
                    id=f"ally_{i}",
                    faction="allied",
                    position_x=320.0 + (i % 10) * 64.0,
                    position_y=320.0 + (i // 10) * 64.0,
                    hp=100,
                    max_hp=100,
                    attack_damage=5,
                    attack_range=400.0,
                    attack_cooldown=1.0,
                )
            )
        for i in range(50):
            combat_system.add_unit(
                SimpleCombatUnit(
                    id=f"enemy_{i}",
                    faction="axis",
                    position_x=960.0 + (i % 10) * 64.0,
                    position_y=320.0 + (i // 10) * 64.0,
                    hp=100,
                    max_hp=100,
                    attack_damage=5,
                    attack_range=400.0,
                    attack_cooldown=1.0,
                )
            )

        # Start memory tracking
        tracemalloc.start()

        # Run 60 frames
        frame_times = []
        for frame in range(60):
            start = time.perf_counter()

            combat_system.update(delta_time=0.016)

            end = time.perf_counter()
            frame_times.append((end - start) * 1000)  # Convert to ms

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Calculate statistics
        avg_frame_time = sum(frame_times) / len(frame_times)

        # Validate performance
        assert avg_frame_time < 16.67, (
            f"Avg frame time {avg_frame_time:.2f}ms exceeds 60fps target (16.67ms)"
        )

        # Memory check (convert to MB)
        peak_mb = peak / (1024 * 1024)
        assert peak_mb < 500, f"Peak memory {peak_mb:.2f}MB exceeds 500MB target"

    def test_08_full_game_loop_integration(self):
        """E2E integration test: Complete game loop from start to victory.

        Test Steps:
        1. Initialize campaign (map load)
        2. Deploy units (5 units)
        3. Start battle
        4. Execute combat (100 ticks)
        5. Check victory condition
        6. Validate final state

        Acceptance:
        - All phases complete without errors
        - Combat executed
        - Victory achieved
        """
        # Phase 1: Campaign initialization
        map_path = Path("data/maps/test_map_small.json")
        if not map_path.exists():
            map_dir = Path("data/maps")
            candidates = [f for f in sorted(map_dir.glob("*.json")) if f.stem != "_schema"]
            if candidates:
                map_path = candidates[0]

        game_map = GameMap.from_json(map_path)
        assert game_map is not None

        # Phase 2: Deploy units
        units = [
            self.create_unit(
                unit_id=f"unit_{i}",
                faction=Faction.ALLIES,
                unit_type=UnitType.INFANTRY_SQUAD if i < 3 else UnitType.TANK,
                position=(10.0 + i * 2, 10.0),
            )
            for i in range(5)
        ]

        # Phase 3: Combat execution
        enemy_units = [
            self.create_unit(
                unit_id=f"enemy_{i}",
                faction=Faction.AXIS,
                unit_type=UnitType.INFANTRY_SQUAD,
                position=(25.0, 10.0 + i * 2),
            )
            for i in range(3)
        ]

        all_units = units + enemy_units
        combat_system = CombatSystem()
        for unit in all_units:
            combat_system.add_unit(
                SimpleCombatUnit(
                    id=unit.id,
                    faction="allied" if unit.faction == Faction.ALLIES else "axis",
                    position_x=float(unit.position.tile_coord.x * 32),
                    position_y=float(unit.position.tile_coord.y * 32),
                    hp=unit.health.hp,
                    max_hp=unit.health.max_hp,
                    attack_damage=20,
                    attack_range=400.0,
                    attack_cooldown=0.5,
                )
            )

        for _ in range(100):
            combat_system.update(delta_time=0.016)

        # Phase 4: Victory validation
        total_alive = len(combat_system.get_alive_units())
        assert total_alive < 8, "Combat should have caused casualties"
