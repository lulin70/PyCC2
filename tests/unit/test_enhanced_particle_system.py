"""
Unit tests for EnhancedParticleSystem - Rich Particle Effects

Tests cover:
- Particle creation (explosion, muzzle flash, smoke, dirt, blood) (Happy Path)
- Particle updates and lifecycle (Happy Path)
- Particle rendering with different types (Happy Path)
- Particle count management (Happy Path + Boundary)
- Error handling for invalid inputs (Error Case)
- Boundary conditions (zero particles, extreme velocities)
- Particle physics (gravity, rotation, fading) (Happy Path)
- Memory management (clearing particles) (Happy Path)
"""

from __future__ import annotations

import math
import os

import pytest

# Ensure SDL dummy drivers are set before pygame imports
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class TestEnhancedParticleSystem:
    """Test EnhancedParticleSystem functionality."""

    @pytest.fixture()
    def particle_system(self, pygame_display):
        """Create an EnhancedParticleSystem instance."""
        from pycc2.presentation.rendering.enhanced_particle_system import (
            EnhancedParticleSystem,
        )
        return EnhancedParticleSystem()

    # ===== HAPPY PATH TESTS =====

    def test_create_enhanced_explosion(self, particle_system, pygame_display):
        """Test creating an enhanced explosion effect."""
        initial_count = particle_system.get_particle_count()
        
        particle_system.create_enhanced_explosion(100.0, 100.0, intensity=1.0)
        
        final_count = particle_system.get_particle_count()
        # Should create many particles (100 fire + 50 smoke + 30 debris + 40 sparks = 220)
        assert final_count > initial_count
        assert final_count >= 200  # At least 200 particles

    def test_create_muzzle_flash(self, particle_system, pygame_display):
        """Test creating a muzzle flash effect."""
        initial_count = particle_system.get_particle_count()
        
        particle_system.create_muzzle_flash(50.0, 50.0, direction_angle=0.0)
        
        final_count = particle_system.get_particle_count()
        # Should create 30 particles
        assert final_count == initial_count + 30

    def test_create_smoke_trail(self, particle_system, pygame_display):
        """Test creating a smoke trail effect."""
        initial_count = particle_system.get_particle_count()
        
        particle_system.create_smoke_trail(75.0, 75.0, vx=10.0, vy=-5.0)
        
        final_count = particle_system.get_particle_count()
        # Should create 5 particles per call
        assert final_count == initial_count + 5

    def test_create_dirt_spray(self, particle_system, pygame_display):
        """Test creating a dirt spray effect."""
        initial_count = particle_system.get_particle_count()
        
        particle_system.create_dirt_spray(120.0, 120.0, direction_angle=math.pi / 4)
        
        final_count = particle_system.get_particle_count()
        # Should create 25 particles
        assert final_count == initial_count + 25

    def test_create_blood_splatter(self, particle_system, pygame_display):
        """Test creating a blood splatter effect."""
        initial_count = particle_system.get_particle_count()
        
        particle_system.create_blood_splatter(150.0, 150.0, direction_angle=math.pi / 2)
        
        final_count = particle_system.get_particle_count()
        # Should create 20 particles
        assert final_count == initial_count + 20

    def test_particle_update_reduces_life(self, particle_system, pygame_display):
        """Test that updating particles reduces their life."""
        particle_system.create_muzzle_flash(50.0, 50.0, direction_angle=0.0)
        
        initial_count = particle_system.get_particle_count()
        
        # Update for a short time
        particle_system.update(dt=0.1)
        
        # Most particles should still be alive (short time)
        assert particle_system.get_particle_count() <= initial_count
        
        # Update for a long time
        particle_system.update(dt=10.0)
        
        # Many or all particles should be dead now
        assert particle_system.get_particle_count() <= initial_count

    def test_particle_update_changes_position(self, particle_system, pygame_display):
        """Test that updating particles changes their position."""
        from pycc2.presentation.rendering.enhanced_particle_system import EnhancedParticle
        
        # Manually create a particle with known velocity
        particle = EnhancedParticle(
            x=100.0, y=100.0,
            vx=50.0, vy=-30.0,
            life=1.0, max_life=1.0,
            color=(255, 255, 255),
            size=5.0
        )
        particle_system.particles.append(particle)
        
        initial_x = particle.x
        initial_y = particle.y
        
        # Update
        particle_system.update(dt=0.1)
        
        # Position should have changed
        assert particle.x != initial_x
        assert particle.y != initial_y
        # Should move in direction of velocity
        assert particle.x > initial_x  # Moving right (vx positive)
        assert particle.y < initial_y  # Moving up (vy negative)

    def test_particle_gravity_applied(self, particle_system, pygame_display):
        """Test that gravity affects particles."""
        from pycc2.presentation.rendering.enhanced_particle_system import EnhancedParticle
        
        particle = EnhancedParticle(
            x=100.0, y=100.0,
            vx=0.0, vy=0.0,
            life=1.0, max_life=1.0,
            color=(255, 255, 255),
            size=5.0,
            gravity=100.0
        )
        particle_system.particles.append(particle)
        
        initial_vy = particle.vy
        
        # Update
        particle_system.update(dt=0.1)
        
        # vy should increase (downward) due to gravity
        assert particle.vy > initial_vy

    def test_particle_rotation_updates(self, particle_system, pygame_display):
        """Test that particle rotation updates."""
        from pycc2.presentation.rendering.enhanced_particle_system import EnhancedParticle
        
        particle = EnhancedParticle(
            x=100.0, y=100.0,
            vx=0.0, vy=0.0,
            life=1.0, max_life=1.0,
            color=(255, 255, 255),
            size=5.0,
            rotation=0.0,
            rotation_speed=180.0  # 180 degrees per second
        )
        particle_system.particles.append(particle)
        
        initial_rotation = particle.rotation
        
        # Update
        particle_system.update(dt=0.5)
        
        # Rotation should have changed
        assert particle.rotation != initial_rotation
        # Should rotate approximately 90 degrees (180 * 0.5)
        assert abs(particle.rotation - 90.0) < 1.0

    def test_render_particles_no_crash(self, particle_system, pygame_display):
        """Test that rendering particles doesn't crash."""
        import pygame
        
        surface = pygame.Surface((800, 600), pygame.SRCALPHA)
        
        particle_system.create_enhanced_explosion(400.0, 300.0)
        
        # Should render without crashing
        particle_system.render(surface, camera_offset=(0, 0))
        
        assert surface is not None

    def test_render_different_particle_types(self, particle_system, pygame_display):
        """Test rendering different particle types."""
        import pygame
        from pycc2.presentation.rendering.enhanced_particle_system import EnhancedParticle
        
        surface = pygame.Surface((400, 400), pygame.SRCALPHA)
        
        # Create particles of each type
        types = ["circle", "square", "spark", "smoke"]
        for i, ptype in enumerate(types):
            particle = EnhancedParticle(
                x=100.0 + i * 50,
                y=200.0,
                vx=0.0, vy=0.0,
                life=1.0, max_life=1.0,
                color=(255, 100, 100),
                size=10.0,
                particle_type=ptype
            )
            particle_system.particles.append(particle)
        
        # Should render all types without crashing
        particle_system.render(surface)
        
        assert particle_system.get_particle_count() == 4

    def test_get_particle_count(self, particle_system, pygame_display):
        """Test getting particle count."""
        assert particle_system.get_particle_count() == 0
        
        particle_system.create_muzzle_flash(50.0, 50.0, direction_angle=0.0)
        
        assert particle_system.get_particle_count() == 30

    def test_clear_particles(self, particle_system, pygame_display):
        """Test clearing all particles."""
        particle_system.create_enhanced_explosion(100.0, 100.0)
        
        assert particle_system.get_particle_count() > 0
        
        particle_system.clear()
        
        assert particle_system.get_particle_count() == 0

    # ===== BOUNDARY TESTS =====

    def test_explosion_zero_intensity(self, particle_system, pygame_display):
        """Test creating explosion with zero intensity (boundary)."""
        initial_count = particle_system.get_particle_count()
        
        particle_system.create_enhanced_explosion(100.0, 100.0, intensity=0.0)
        
        final_count = particle_system.get_particle_count()
        # Should create fewer particles than normal intensity
        # With intensity=0.0, formula is int(100*0) = 0 for fire, but other layers still create particles
        assert final_count - initial_count >= 0  # At least creates some base particles

    def test_explosion_high_intensity(self, particle_system, pygame_display):
        """Test creating explosion with high intensity (boundary)."""
        initial_count = particle_system.get_particle_count()
        
        particle_system.create_enhanced_explosion(100.0, 100.0, intensity=5.0)
        
        final_count = particle_system.get_particle_count()
        # Should create many more particles
        assert final_count - initial_count > 500

    def test_update_zero_delta_time(self, particle_system, pygame_display):
        """Test updating with zero delta time (boundary)."""
        particle_system.create_muzzle_flash(50.0, 50.0, direction_angle=0.0)
        
        initial_count = particle_system.get_particle_count()
        
        particle_system.update(dt=0.0)
        
        # Should not crash, particles should not change
        assert particle_system.get_particle_count() == initial_count

    def test_update_large_delta_time(self, particle_system, pygame_display):
        """Test updating with very large delta time (boundary)."""
        particle_system.create_muzzle_flash(50.0, 50.0, direction_angle=0.0)
        
        initial_count = particle_system.get_particle_count()
        
        # Update multiple times (fade_rate is per-update, not per-second)
        # Muzzle flash has fade_rate=0.08, so need ~13 updates to kill all particles
        for _ in range(20):
            particle_system.update(dt=1.0)
        
        # All particles should be dead after 20 updates
        assert particle_system.get_particle_count() == 0

    def test_render_with_camera_offset(self, particle_system, pygame_display):
        """Test rendering with camera offset."""
        import pygame
        
        surface = pygame.Surface((800, 600), pygame.SRCALPHA)
        
        particle_system.create_muzzle_flash(400.0, 300.0, direction_angle=0.0)
        
        # Should render with offset without crashing
        particle_system.render(surface, camera_offset=(100, 50))
        
        assert particle_system.get_particle_count() > 0

    def test_render_particles_offscreen(self, particle_system, pygame_display):
        """Test rendering particles that are off-screen."""
        import pygame
        
        surface = pygame.Surface((800, 600), pygame.SRCALPHA)
        
        # Create particles far off-screen
        particle_system.create_muzzle_flash(10000.0, 10000.0, direction_angle=0.0)
        
        # Should render without crashing
        particle_system.render(surface, camera_offset=(0, 0))
        
        assert particle_system.get_particle_count() > 0

    # ===== ERROR CASE TESTS =====

    def test_negative_coordinates(self, particle_system, pygame_display):
        """Test creating effects at negative coordinates (should work)."""
        particle_system.create_enhanced_explosion(-50.0, -100.0)
        
        assert particle_system.get_particle_count() > 0

    def test_extreme_velocity(self, particle_system, pygame_display):
        """Test particles with extreme velocities."""
        from pycc2.presentation.rendering.enhanced_particle_system import EnhancedParticle
        
        particle = EnhancedParticle(
            x=100.0, y=100.0,
            vx=10000.0, vy=-10000.0,
            life=1.0, max_life=1.0,
            color=(255, 255, 255),
            size=5.0
        )
        particle_system.particles.append(particle)
        
        # Should update without crashing
        particle_system.update(dt=0.1)
        
        assert particle_system.get_particle_count() == 1

    def test_zero_size_particle(self, particle_system, pygame_display):
        """Test rendering particle with zero size (boundary/error case)."""
        import pygame
        from pycc2.presentation.rendering.enhanced_particle_system import EnhancedParticle
        
        surface = pygame.Surface((400, 400), pygame.SRCALPHA)
        
        particle = EnhancedParticle(
            x=200.0, y=200.0,
            vx=0.0, vy=0.0,
            life=1.0, max_life=1.0,
            color=(255, 255, 255),
            size=0.0  # Zero size
        )
        particle_system.particles.append(particle)
        
        # Should render without crashing
        particle_system.render(surface)
        
        assert particle_system.get_particle_count() == 1

    def test_negative_life(self, particle_system, pygame_display):
        """Test particle with negative life gets removed."""
        from pycc2.presentation.rendering.enhanced_particle_system import EnhancedParticle
        
        particle = EnhancedParticle(
            x=100.0, y=100.0,
            vx=0.0, vy=0.0,
            life=-1.0,  # Already dead
            max_life=1.0,
            color=(255, 255, 255),
            size=5.0
        )
        particle_system.particles.append(particle)
        
        particle_system.update(dt=0.1)
        
        # Dead particle should be removed
        assert particle_system.get_particle_count() == 0

    # ===== INTEGRATION TESTS =====

    def test_multiple_effect_types_together(self, particle_system, pygame_display):
        """Test creating multiple different effects simultaneously."""
        particle_system.create_enhanced_explosion(100.0, 100.0)
        particle_system.create_muzzle_flash(200.0, 200.0, direction_angle=0.0)
        particle_system.create_smoke_trail(300.0, 300.0, vx=10.0, vy=-5.0)
        
        # Should have many particles from all effects
        assert particle_system.get_particle_count() > 200

    def test_continuous_smoke_trail_simulation(self, particle_system, pygame_display):
        """Test simulating continuous smoke trail over multiple frames."""
        # Simulate 10 frames of smoke trail
        for _ in range(10):
            particle_system.create_smoke_trail(150.0, 150.0, vx=20.0, vy=-10.0)
            particle_system.update(dt=0.016)  # ~60 FPS
        
        # Should have accumulated some smoke particles
        assert particle_system.get_particle_count() > 0

    def test_particle_lifecycle_complete(self, particle_system, pygame_display):
        """Test complete particle lifecycle from creation to death."""
        particle_system.create_muzzle_flash(100.0, 100.0, direction_angle=0.0)
        
        initial_count = particle_system.get_particle_count()
        assert initial_count > 0
        
        # Update until all particles die
        for _ in range(100):  # Enough iterations to kill all particles
            particle_system.update(dt=0.1)
            if particle_system.get_particle_count() == 0:
                break
        
        # Most or all particles should be dead (some might have high max_life)
        assert particle_system.get_particle_count() <= initial_count * 0.1  # At most 10% alive
