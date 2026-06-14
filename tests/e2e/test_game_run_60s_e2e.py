"""E2E Test: Game 60-Second Run Test

Tests that the game can run for 60 simulated seconds without crashing:
1. Initialize pygame with dummy driver
2. Create game loop with a map
3. Create units on both sides
4. Run 1800 ticks (60 seconds at 30 UPS)
5. Each tick: update game logic
6. Every 30 ticks: simulate a random command
7. Verify no exceptions thrown
8. Verify game state is still valid after 60 seconds
"""

from __future__ import annotations

import os
import random
import traceback


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_units():
    """Create units for both sides."""
    from pycc2.domain.entities.unit import Unit, Faction, UnitType
    from pycc2.domain.components.position_component import PositionComponent
    from pycc2.domain.components.health_component import HealthComponent
    from pycc2.domain.components.vision_component import VisionComponent
    from pycc2.domain.components.weapon_component import WeaponComponent
    from pycc2.domain.components.morale_component import MoraleComponent
    from pycc2.domain.value_objects.tile_coord import TileCoord

    units = []

    # Allied units
    for i in range(3):
        units.append(Unit(
            id=f"ally_{i}",
            name=f"Allied Squad {i}",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            position=PositionComponent(tile_coord=TileCoord(2 + i, 2)),
            vision=VisionComponent(),
            health=HealthComponent(hp=100, max_hp=100),
            weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
            morale=MoraleComponent(value=75),
        ))

    # Axis units
    for i in range(3):
        units.append(Unit(
            id=f"axis_{i}",
            name=f"Axis Squad {i}",
            faction=Faction.AXIS,
            unit_type=UnitType.INFANTRY_SQUAD,
            position=PositionComponent(tile_coord=TileCoord(8 + i, 8)),
            vision=VisionComponent(),
            health=HealthComponent(hp=100, max_hp=100),
            weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
            morale=MoraleComponent(value=75),
        ))

    return units


def _create_game_state():
    """Create a minimal game state for testing."""
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.services.game_loop import GameState
    import numpy as np

    # Create a 20x15 map with open terrain
    tile_grid = np.zeros((15, 20), dtype=np.int8)
    game_map = GameMap(
        id="test_map",
        name="Test Map",
        width=20,
        height=15,
        tile_grid=tile_grid,
    )

    camera = Camera(position=None, viewport_width=800, viewport_height=600)
    units = _create_test_units()

    state = GameState(
        game_map=game_map,
        units=units,
        camera=camera,
    )

    return state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGameRun60sE2E:
    """Full E2E test: game runs for 60 simulated seconds without crashing."""

    def test_60_second_run(self):
        """Run the game for 1800 ticks (60 seconds at 30 UPS) and verify stability."""
        from pycc2.services.event_bus import EventBus
        from pycc2.services.combat_director import CombatDirector
        from pycc2.services.victory_manager import VictoryManager

        state = _create_game_state()
        event_bus = EventBus()

        # Set up combat director
        combat_director = CombatDirector(
            event_bus=event_bus,
            display_config=None,
            sound_system=None,
        )
        combat_director.initialize()

        # Set up victory manager
        victory_manager = VictoryManager()
        victory_manager.initialize(event_bus, combat_director=combat_director)

        dt = 1.0 / 30.0  # 30 UPS
        total_ticks = 1800  # 60 seconds
        errors = []
        rng = random.Random(42)  # Deterministic seed

        for tick in range(total_ticks):
            try:
                # Update unit movements
                for unit in state.units:
                    if hasattr(unit, 'update_movement_mode'):
                        unit.update_movement_mode()

                    if hasattr(unit, 'move_target') and unit.move_target is not None:
                        unit.update_movement(dt)

                # Update fatigue
                for unit in state.units:
                    if unit.fatigue is not None:
                        if unit.move_target is not None:
                            unit.fatigue.accumulate("moving")
                        else:
                            unit.fatigue.recover()

                # Update combat director
                combat_director.update(
                    units=state.units,
                    game_map=state.game_map,
                    dt=dt,
                    battle_stats=victory_manager.battle_stats,
                )

                # Every 30 ticks (~1 second), simulate a random command
                if tick % 30 == 0 and tick > 0:
                    self._simulate_random_command(state, rng)

                # Check victory conditions
                victory_manager.evaluate(state.units, tick)

                state.tick = tick

            except Exception as e:
                errors.append({
                    "tick": tick,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                })
                # Don't break — try to continue

        # Verify results
        assert len(errors) == 0, (
            f"Game encountered {len(errors)} errors during 60-second run. "
            f"First error at tick {errors[0]['tick']}: {errors[0]['error']}\n"
            f"Traceback: {errors[0]['traceback']}"
        )

        # Verify game state is still valid
        assert state.game_map is not None, "Game map should still exist"
        assert state.game_map.width == 20, "Map width should be preserved"
        assert state.game_map.height == 15, "Map height should be preserved"

        # Verify units still exist (some may have died in combat)
        assert len(state.units) > 0, "Should still have units after 60 seconds"

        # Verify camera is still valid
        assert state.camera is not None, "Camera should still exist"

    def _simulate_random_command(self, state, rng):
        """Simulate a random command on a random unit."""
        from pycc2.domain.value_objects.tile_coord import TileCoord

        alive_units = [u for u in state.units if u.is_alive]
        if not alive_units:
            return

        unit = rng.choice(alive_units)
        command = rng.choice(["move", "fast_move", "sneak", "defend", "idle"])

        if command == "move":
            # Set a random move target within map bounds
            tx = rng.randint(0, state.game_map.width - 1)
            ty = rng.randint(0, state.game_map.height - 1)
            unit.set_move_target(TileCoord(tx, ty))
        elif command in ("fast_move", "sneak", "defend"):
            unit.set_movement_mode(command)
        elif command == "idle":
            unit.set_movement_mode("normal")
            unit.move_target = None

    def test_unit_state_transitions_over_time(self):
        """Verify units can transition between states over time without errors."""
        from pycc2.domain.entities.unit import Unit, Faction, UnitType
        from pycc2.domain.components.position_component import PositionComponent
        from pycc2.domain.components.health_component import HealthComponent
        from pycc2.domain.components.vision_component import VisionComponent
        from pycc2.domain.components.weapon_component import WeaponComponent
        from pycc2.domain.components.morale_component import MoraleComponent
        from pycc2.domain.value_objects.tile_coord import TileCoord

        unit = Unit(
            id="transition_test",
            name="Transition Test Unit",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            position=PositionComponent(tile_coord=TileCoord(5, 5)),
            vision=VisionComponent(),
            health=HealthComponent(hp=100, max_hp=100),
            weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
            morale=MoraleComponent(value=75),
        )

        dt = 1.0 / 30.0
        errors = []

        for tick in range(600):  # 20 seconds
            try:
                # Cycle through movement modes
                if tick % 100 == 0:
                    modes = ["normal", "fast_move", "sneak", "defend"]
                    unit.set_movement_mode(modes[(tick // 100) % len(modes)])

                # Set and clear move targets
                if tick % 50 == 0:
                    unit.set_move_target(TileCoord(
                        5 + (tick % 10) - 5,
                        5 + (tick % 7) - 3,
                    ))
                if tick % 50 == 25:
                    unit.move_target = None

                unit.update_movement_mode()
                unit.update_movement(dt)

            except Exception as e:
                errors.append({"tick": tick, "error": str(e)})

        assert len(errors) == 0, f"Unit state transitions had {len(errors)} errors"
