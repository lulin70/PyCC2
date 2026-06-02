from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .animation_system import ParticleEmitter


class ParticlePool:
    """Object pool for Particle dataclass objects to reduce GC pressure."""

    def __init__(self, preallocate: int = 100):
        self._pool: list[object] = []
        self._active_count: int = 0
        for _ in range(preallocate):
            self._pool.append(self._new_particle())

        self._dict_pool: list[dict] = []
        self._dict_active_count: int = 0

    def _new_particle(self):
        from .animation_system import ParticleEmitter

        return ParticleEmitter.Particle(
            type=ParticleEmitter.ParticleType.SPARK,
            x=0.0,
            y=0.0,
            vx=0.0,
            vy=0.0,
            life=0,
            max_life=1,
            size=1.0,
            color=(255, 255, 255),
        )

    def acquire(self):
        if self._pool:
            p = self._pool.pop()
        else:
            p = self._new_particle()
        self._active_count += 1
        return p

    def release(self, particle) -> None:
        self._active_count -= 1
        particle.life = 0
        self._pool.append(particle)

    def acquire_dict(self) -> dict:
        if self._dict_pool:
            d = self._dict_pool.pop()
        else:
            d = {}
        self._dict_active_count += 1
        return d

    def release_dict(self, d: dict) -> None:
        self._dict_active_count -= 1
        d.clear()
        self._dict_pool.append(d)

    def update(self, emitter: ParticleEmitter) -> None:
        alive = []
        for p in emitter.particles:
            p.vx *= p.friction
            p.vy *= p.friction
            p.vy += p.gravity
            p.x += p.vx
            p.y += p.vy
            p.rotation += p.rot_speed
            p.life -= 1
            if p.life > 0:
                alive.append(p)
            else:
                self.release(p)
        emitter.particles = alive

    @property
    def active_count(self) -> int:
        return self._active_count

    @property
    def pool_size(self) -> int:
        return len(self._pool)

    @property
    def dict_active_count(self) -> int:
        return self._dict_active_count

    @property
    def dict_pool_size(self) -> int:
        return len(self._dict_pool)
