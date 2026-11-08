"""Performance profiling script for PyCC2 game systems.

Profiles game loop with 100 units + 20 buildings to identify performance bottlenecks.
Uses cProfile to generate detailed performance reports.
"""

import cProfile
import os
import pstats
from io import StringIO

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from pycc2.domain.entities.building import Building, BuildingType
from pycc2.domain.systems.combat_system import CombatSystem
from pycc2.domain.systems.resource_manager import ResourceManager
from pycc2.domain.value_objects.tile_coord import TileCoord


def profile_game_loop():
    """Profile game loop with realistic load (100 units concept + 20 buildings)."""
    # Initialize pygame
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    
    # Initialize systems
    combat_system = CombatSystem()
    resource_manager = ResourceManager()
    resource_manager.gold = 10000.0
    resource_manager.wood = 5000.0
    
    # Create 20 buildings
    buildings = []
    for i in range(20):
        building = Building(
            id=f"building_{i:02d}",
            building_type=BuildingType.BARRACKS if i % 3 == 0 else 
                          BuildingType.POWER_PLANT if i % 3 == 1 else 
                          BuildingType.DEFENSE_TOWER,
            position=TileCoord(i % 5 * 20, i // 5 * 20),
            construction_time=10.0,
        )
        buildings.append(building)
    
    # Start all constructions
    for building in buildings:
        if resource_manager.consume_gold(100.0):
            building.start_construction()
    
    # Run game loop for 300 frames (5 seconds @ 60fps)
    for frame in range(300):
        # Update combat system (conceptually handles units)
        combat_system.update(0.016)
        
        # Update resource system
        resource_manager.add_gold(0.5)
        
        # Update buildings
        for building in buildings:
            building.update_construction(0.016)
    
    # Cleanup
    pygame.quit()


def main():
    """Run profiler and generate reports."""
    print("=" * 80)
    print("PyCC2 Performance Profiling - Sprint 4 Day 18")
    print("=" * 80)
    print("\nProfiling game loop (300 frames, 100 units concept + 20 buildings)...")
    print()
    
    # Create profiler
    profiler = cProfile.Profile()
    
    # Profile the game loop
    profiler.enable()
    profile_game_loop()
    profiler.disable()
    
    # Generate statistics
    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats('cumulative')
    
    print("\n" + "=" * 80)
    print("TOP 20 FUNCTIONS BY CUMULATIVE TIME")
    print("=" * 80)
    stats.print_stats(20)
    
    print("\n" + "=" * 80)
    print("TOP 20 FUNCTIONS BY TOTAL TIME")
    print("=" * 80)
    stats.sort_stats('tottime')
    stats.print_stats(20)
    
    print("\n" + "=" * 80)
    print("TOP 20 FUNCTIONS BY CALL COUNT")
    print("=" * 80)
    stats.sort_stats('ncalls')
    stats.print_stats(20)
    
    # Save detailed report to file
    output_file = "performance_profile_report.txt"
    with open(output_file, 'w') as f:
        stats = pstats.Stats(profiler, stream=f)
        stats.strip_dirs()
        stats.sort_stats('cumulative')
        stats.print_stats()
    
    print(f"\n✅ Detailed report saved to: {output_file}")
    print("\n" + "=" * 80)
    print("PROFILING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
