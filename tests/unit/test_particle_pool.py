from __future__ import annotations

import pytest

from pycc2.presentation.rendering.animation_system import ParticleEmitter
from pycc2.presentation.rendering.particle_pool import ParticlePool


class TestParticlePoolInit:
    def test_preallocate_creates_n_particles(self):
        pool = ParticlePool(preallocate=50)
        assert pool.pool_size == 50
        assert pool.active_count == 0

    def test_default_preallocation(self):
        pool = ParticlePool()
        assert pool.pool_size == 100
        assert pool.active_count == 0


class TestParticlePoolAcquire:
    def test_acquire_returns_particle_object(self):
        pool = ParticlePool(preallocate=10)
        p = pool.acquire()
        assert p is not None
        assert hasattr(p, 'x')
        assert hasattr(p, 'y')
        assert hasattr(p, 'life')
        assert pool.active_count == 1
        assert pool.pool_size == 9

    def test_acquire_reduces_pool(self):
        pool = ParticlePool(preallocate=5)
        pool.acquire()
        assert pool.pool_size == 4
        assert pool.active_count == 1

    def test_acquired_particle_has_settable_fields(self):
        pool = ParticlePool(preallocate=10)
        p = pool.acquire()
        p.x = 10.0
        p.y = 20.0
        p.vx = 1.0
        p.vy = 2.0
        p.life = 30
        p.max_life = 30
        p.size = 3.0
        p.color = (255, 0, 0)
        p.alpha_start = 220
        p.gravity = 0.5
        p.friction = 0.95
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.life == 30


class TestParticlePoolRelease:
    def test_release_returns_particle_to_pool(self):
        pool = ParticlePool(preallocate=5)
        p = pool.acquire()
        assert pool.active_count == 1
        pool.release(p)
        assert pool.active_count == 0
        assert pool.pool_size == 5

    def test_release_resets_life_field(self):
        pool = ParticlePool(preallocate=5)
        p = pool.acquire()
        p.life = 30
        pool.release(p)
        assert p.life == 0


class TestParticlePoolExhaustion:
    def test_pool_grows_if_exhausted(self):
        pool = ParticlePool(preallocate=2)
        pool.acquire()
        pool.acquire()
        p3 = pool.acquire()
        assert pool.active_count == 3
        assert pool.pool_size == 0
        assert p3 is not None


class TestParticlePoolActiveCount:
    def test_active_count_tracks_acquisitions(self):
        pool = ParticlePool(preallocate=10)
        assert pool.active_count == 0
        particles = []
        for _ in range(5):
            particles.append(pool.acquire())
        assert pool.active_count == 5

        for p in particles[:3]:
            pool.release(p)
        assert pool.active_count == 2


class TestParticlePoolUpdate:
    def test_update_processes_physics_and_releases_dead(self):
        emitter = ParticleEmitter()
        pool = ParticlePool(preallocate=20)

        p_alive = pool.acquire()
        p_alive.x, p_alive.y = 0.0, 0.0
        p_alive.vx, p_alive.vy = 5.0, 0.0
        p_alive.life = 10
        p_alive.max_life = 10
        p_alive.size = 2.0
        p_alive.color = (255, 200, 50)
        p_alive.gravity = 0.0
        p_alive.friction = 1.0

        p_dead = pool.acquire()
        p_dead.x, p_dead.y = 0.0, 0.0
        p_dead.vx, p_dead.vy = 0.0, 0.0
        p_dead.life = 0
        p_dead.max_life = 1
        p_dead.size = 1.0
        p_dead.color = (255, 255, 255)

        emitter.particles = [p_alive, p_dead]
        initial_active = pool.active_count

        pool.update(emitter)

        assert len(emitter.particles) == 1
        assert pool.active_count == initial_active - 1

    def test_update_applies_friction_and_gravity(self):
        emitter = ParticleEmitter()
        pool = ParticlePool(preallocate=10)

        p = pool.acquire()
        p.x, p.y = 0.0, 0.0
        p.vx, p.vy = 10.0, 0.0
        p.life = 5
        p.max_life = 5
        p.size = 2.0
        p.color = (255, 200, 50)
        p.gravity = 1.0
        p.friction = 0.9
        emitter.particles = [p]

        pool.update(emitter)

        updated = emitter.particles[0]
        assert updated.vx == pytest.approx(9.0)
        assert updated.vy == pytest.approx(1.0)
        assert updated.x == pytest.approx(9.0)
        assert updated.y == pytest.approx(1.0)


class TestParticlePoolIntegrationWithEmitter:
    def test_emitter_works_without_pool(self):
        emitter = ParticleEmitter()
        assert emitter._pool is None
        emitter.emit_muzzle_flash(0, 0, 0, count=5)
        assert len(emitter.particles) == 5
        for _ in range(15):
            emitter.update()
        assert len(emitter.particles) == 0

    def test_emitter_with_pool_still_emits_particles(self):
        pool = ParticlePool(preallocate=50)
        emitter = ParticleEmitter(pool=pool)
        assert emitter._pool is pool
        emitter.emit_muzzle_flash(0, 0, 0, count=8)
        assert len(emitter.particles) == 8

    def test_emitter_with_pool_delegates_update(self):
        pool = ParticlePool(preallocate=50)
        emitter = ParticleEmitter(pool=pool)
        emitter.emit_muzzle_flash(0, 0, 0, count=5)
        total_before = pool.active_count + pool.pool_size
        emitter.update()
        total_after = pool.active_count + pool.pool_size
        assert total_after == total_before

    def test_all_emit_methods_work_with_pool(self):
        pool = ParticlePool(preallocate=100)
        emitter = ParticleEmitter(pool=pool)
        emitter.emit_muzzle_flash(0, 0, 0, count=3)
        emitter.emit_blood(0, 0, count=3)
        emitter.emit_smoke(0, 0, count=2)
        emitter.emit_debris(0, 0, count=2)
        emitter.emit_sparks(0, 0, 0, count=2)
        emitter.emit_explosion_ring(0, 0)
        assert len(emitter.particles) == 3 + 3 + 2 + 2 + 2 + 16

    def test_pooled_particles_are_reused_after_death(self):
        pool = ParticlePool(preallocate=10)
        emitter = ParticleEmitter(pool=pool)
        initial_pool = pool.pool_size
        emitter.emit_muzzle_flash(0, 0, 0, count=5)
        assert pool.active_count == 5
        for _ in range(20):
            emitter.update()
        assert pool.active_count == 0
        assert pool.pool_size >= initial_pool
