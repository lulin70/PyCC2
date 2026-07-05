"""动画系统模块，提供单位动画、屏幕震动与粒子发射能力。"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .particle_pool import ParticlePool as ExternalParticlePool


class AnimationType(Enum):
    """单位动画类型枚举，描述待机、行走、射击等动作。"""

    IDLE = auto()
    WALK = auto()
    SHOOT = auto()
    RELOAD = auto()
    DEATH = auto()
    HIT_REACT = auto()


@dataclass(slots=True)
class AnimationState:
    """单个动画实例的运行时状态，包括帧、偏移与缩放等。"""

    anim_type: AnimationType = AnimationType.IDLE
    frame: int = 0
    duration_ticks: int = 30
    loop: bool = True
    offset_x: float = 0.0
    offset_y: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    alpha: int = 255
    rotation: float = 0.0
    color_mod: tuple[int, int, int] | None = None

    def reset(self, new_type: AnimationType | None = None) -> None:
        """Reset internal state."""
        if new_type:
            self.anim_type = new_type
        self.frame = 0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.alpha = 255
        self.rotation = 0.0
        self.color_mod = None


class UnitAnimator:
    """单位动画驱动器，按动画类型切换并更新动画状态。"""

    CONFIGS: dict[AnimationType, dict[str, int | bool]] = {
        AnimationType.IDLE: {"duration": 60, "loop": True},
        AnimationType.WALK: {"duration": 20, "loop": True},
        AnimationType.SHOOT: {"duration": 12, "loop": False},
        AnimationType.RELOAD: {"duration": 45, "loop": False},
        AnimationType.DEATH: {"duration": 18, "loop": False},
        AnimationType.HIT_REACT: {"duration": 8, "loop": False},
    }

    def __init__(self):
        """初始化动画器，默认处于待机状态。"""
        self.state = AnimationState()
        self._prev_type = AnimationType.IDLE

    def set_animation(self, anim_type: AnimationType) -> None:
        """Set the animation."""
        if anim_type != self._prev_type:
            config = self.CONFIGS.get(anim_type, self.CONFIGS[AnimationType.IDLE])
            self.state.reset(anim_type)
            self.state.duration_ticks = config["duration"]
            self.state.loop = bool(config["loop"])
            self._prev_type = anim_type

    def update(self) -> bool:
        """Update internal state."""
        self.state.frame += 1
        progress = self.state.frame / max(self.state.duration_ticks, 1)

        match self.state.anim_type:
            case AnimationType.IDLE:
                t = self.state.frame * 0.1
                self.state.offset_y = math.sin(t) * 1.0

            case AnimationType.WALK:
                t = self.state.frame * 0.5
                self.state.offset_y = abs(math.sin(t)) * 3.0
                self.state.offset_x = math.sin(t * 0.7) * 0.5

            case AnimationType.SHOOT:
                if progress < 0.3:
                    kick = math.sin(progress / 0.3 * math.pi) * 4.0
                    self.state.offset_y = -kick
                    self.state.scale_y = 1.0 + kick * 0.02
                else:
                    recovery = (progress - 0.3) / 0.7
                    self.state.offset_y = -4.0 * (1 - recovery)
                    self.state.scale_y = 1.0 + 0.08 * (1 - recovery)

            case AnimationType.DEATH:
                self.state.rotation = progress * 15
                self.state.scale_y = 1.0 - progress * 0.2
                self.state.scale_x = 1.0 - progress * 0.1
                self.state.offset_y = progress * 4.0
                self.state.alpha = int(255 * (1.0 - progress))
                self.state.color_mod = (192, 32, 32)

            case AnimationType.HIT_REACT:
                if progress < 0.5:
                    self.state.color_mod = (255, 255, 255)
                    self.state.offset_x = math.sin(progress * 20) * 2.0
                else:
                    self.state.color_mod = None
                    self.state.offset_x = 0.0

            case AnimationType.RELOAD:
                self.state.offset_y = math.sin(progress * math.pi * 2) * 1.5
                self.state.scale_x = 1.0 + math.sin(progress * math.pi * 4) * 0.03

        if not self.state.loop and self.state.frame >= self.state.duration_ticks:
            if self.state.anim_type in (AnimationType.DEATH,):
                return False
            self.set_animation(AnimationType.IDLE)
            return True
        return True

    @property
    def is_alive(self) -> bool:
        """Get the is alive."""
        return (
            self.state.anim_type != AnimationType.DEATH
            or self.state.frame < self.state.duration_ticks
        )


class ScreenShake:
    """屏幕震动效果，按强度衰减生成偏移量。"""

    def __init__(self):
        """初始化震动偏移、强度与剩余持续时间。"""
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0
        self._intensity: float = 0.0
        self._decay: float = 0.88
        self._ticks_remaining: int = 0

    def trigger(self, intensity: float = 3.0, duration_ticks: int = 5) -> None:
        """Trigger an effect."""
        self._intensity = min(intensity, 20.0)
        self._ticks_remaining = duration_ticks

    def update(self) -> tuple[float, float]:
        """Update internal state."""
        if self._ticks_remaining <= 0:
            self._offset_x = 0.0
            self._offset_y = 0.0
            return (0.0, 0.0)

        self._offset_x = (random.random() - 0.5) * 2 * self._intensity
        self._offset_y = (random.random() - 0.5) * 2 * self._intensity
        self._intensity *= self._decay
        self._ticks_remaining -= 1
        return (self._offset_x, self._offset_y)

    @property
    def is_active(self) -> bool:
        """Get the is active."""
        return self._ticks_remaining > 0


class ParticleEmitter:
    """粒子发射器，按粒子类型生成并管理粒子生命周期。"""

    class ParticleType(Enum):
        MUZZLE_FLASH = auto()
        BLOOD = auto()
        SMOKE = auto()
        DEBRIS = auto()
        SHELL_CASING = auto()
        SPARK = auto()
        DIRT = auto()
        EXPLOSION_RING = auto()
        EXPLOSION_LARGE = auto()
        EXPLOSION_AP = auto()
        BLOOD_SPLATTER = auto()
        DIRT_KICKUP = auto()
        MUZZLE_FLASH_BURST = auto()
        EXPLOSION_CORE = auto()
        SMOKE_SCREEN = auto()

    PRESETS: dict[str, dict[str, Any]] = {
        "rifle_fire": {
            "count": 3,
            "speed": (3, 6),
            "life": (8, 12),
            "size": (2, 4),
            "color": (255, 200, 50),
            "spread": 15,
            "gravity": 0.1,
            "fade": True,
        },
        "tank_explosion": {
            "count": 40,
            "speed": (4, 12),
            "life": (30, 50),
            "size": (4, 12),
            "color": (255, 150, 30),
            "spread": 360,
            "gravity": 0.05,
            "fade": True,
            "has_secondary": True,
        },
        "mortar_impact": {
            "count": 25,
            "speed": (3, 10),
            "life": (25, 40),
            "size": (3, 8),
            "color": (200, 100, 20),
            "spread": 360,
            "gravity": 0.15,
            "fade": True,
            "dirt_kick": True,
        },
        "blood_hit": {
            "count": 8,
            "speed": (2, 5),
            "life": (15, 25),
            "size": (2, 5),
            "color": (180, 30, 20),
            "spread": 90,
            "gravity": 0.2,
            "fade": True,
        },
        "muzzle_flash": {
            "count": 3,
            "speed": (8, 20),
            "life": (1, 2),
            "size": (4, 6),
            "color": (255, 255, 128),
            "spread": 10,
            "gravity": 0,
            "fade": True,
            "additive": True,
        },
    }

    @dataclass
    class Particle:
        type: ParticleEmitter.ParticleType
        x: float
        y: float
        vx: float
        vy: float
        life: int
        max_life: int
        size: float
        color: tuple[int, int, int]
        alpha_start: int = 255
        gravity: float = 0.3
        friction: float = 0.98
        rotation: float = 0.0
        rot_speed: float = 0.0
        size_x: float | None = None
        size_y: float | None = None

        @property
        def progress(self) -> float:
            """Get the progress."""
            return 1.0 - (self.life / max(self.max_life, 1))

        @property
        def alpha(self) -> int:
            """Get the alpha."""
            return int(self.alpha_start * (1.0 - self.progress))

    def __init__(self, pool: ExternalParticlePool | None = None):
        """初始化粒子列表与可选的粒子池。"""
        self.particles: list[ParticleEmitter.Particle] = []
        self._rng_seed: int = 42
        self._pool: ExternalParticlePool | None = pool

    def _add_particle(self, **kwargs) -> None:
        """Add a particle, using pool when available."""
        if self._pool is not None:
            p = self._pool.acquire()
            for key, value in kwargs.items():
                setattr(p, key, value)
            self.particles.append(p)
        else:
            self.particles.append(self.Particle(**kwargs))

    def emit_muzzle_flash(self, x: float, y: float, direction: float, count: int = 3) -> None:
        """Emit muzzle flash."""
        for i in range(count):
            spread = random.uniform(-0.15, 0.15)
            angle = direction + spread
            speed = random.uniform(8, 20)
            flash_colors = [(255, 255, 128), (255, 240, 80), (255, 200, 50)]
            color = flash_colors[min(i, len(flash_colors) - 1)]
            self._add_particle(
                type=self.ParticleType.MUZZLE_FLASH,
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(1, 2),
                max_life=2,
                size_x=6.0 + random.uniform(-1, 1),
                size_y=4.0 + random.uniform(-0.5, 0.5),
                size=5.0,
                color=color,
                alpha_start=255,
                gravity=0,
                friction=0.85,
            )

    def emit_blood(self, x: float, y: float, count: int = 10) -> None:
        """Emit blood."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(15, 50)
            self._add_particle(
                type=self.ParticleType.BLOOD,
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 10,
                life=random.randint(15, 30),
                max_life=30,
                size=random.uniform(1, 4),
                color=random.choice(
                    [
                        (139, 0, 0),
                        (160, 0, 0),
                        (120, 0, 0),
                        (180, 30, 30),
                        (100, 0, 0),
                    ]
                ),
                alpha_start=220,
                gravity=0.5,
                friction=0.95,
            )

    def emit_smoke(self, x: float, y: float, count: int = 5) -> None:
        """Emit smoke."""
        for _ in range(count):
            self._add_particle(
                type=self.ParticleType.SMOKE,
                x=x + random.uniform(-5, 5),
                y=y + random.uniform(-3, 3),
                vx=random.uniform(-3, 3),
                vy=random.uniform(-20, -10),
                life=random.randint(25, 45),
                max_life=45,
                size=random.uniform(4, 12),
                color=random.choice([(80, 80, 80), (100, 100, 100), (60, 60, 60)]),
                alpha_start=150,
                gravity=-0.15,
                friction=0.96,
            )

    def emit_debris(self, x: float, y: float, count: int = 6) -> None:
        """Emit debris."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(25, 70)
            self._add_particle(
                type=self.ParticleType.DEBRIS,
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 15,
                life=random.randint(18, 35),
                max_life=35,
                size=random.uniform(2, 5),
                color=random.choice([(101, 67, 33), (139, 90, 43), (80, 50, 20)]),
                alpha_start=255,
                gravity=0.6,
                friction=0.92,
                rot_speed=random.uniform(-8, 8),
            )

    def emit_sparks(self, x: float, y: float, direction: float, count: int = 4) -> None:
        """Emit sparks."""
        base_angle = direction + math.pi + random.uniform(-0.5, 0.5)
        spark_colors = [(255, 255, 200), (255, 255, 255), (255, 240, 100), (255, 220, 50)]
        for i in range(count):
            angle = base_angle + random.uniform(-0.8, 0.8)
            speed = random.uniform(2, 3)
            self._add_particle(
                type=self.ParticleType.SPARK,
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(3, 5),
                max_life=5,
                size=random.uniform(2, 3),
                color=spark_colors[min(i, len(spark_colors) - 1)],
                alpha_start=255,
                gravity=0.15,
                friction=0.92,
            )

    def emit_explosion_ring(self, x: float, y: float) -> None:
        """Emit explosion ring."""
        for i in range(16):
            angle = (i / 16) * 2 * math.pi
            self._add_particle(
                type=self.ParticleType.EXPLOSION_RING,
                x=x,
                y=y,
                vx=math.cos(angle) * 60,
                vy=math.sin(angle) * 60,
                life=12,
                max_life=12,
                size=4,
                color=(255, 200, 100),
                alpha_start=200,
                gravity=0.0,
                friction=0.88,
            )

    def emit_explosion_core(self, x: float, y: float, count: int = 12, life: int = 12) -> None:
        """Emit explosion core."""
        for i in range(count):
            angle = random.uniform(0, 2 * math.pi)
            progress = i / max(count - 1, 1)
            speed = random.uniform(8, 25)
            core_colors = [(255, 208, 0), (255, 96, 0), (255, 32, 0)]
            color_idx = min(int(progress * len(core_colors)), len(core_colors) - 1)
            size = 8 + progress * 17
            self._add_particle(
                type=self.ParticleType.EXPLOSION_CORE,
                x=x + random.uniform(-3, 3),
                y=y + random.uniform(-3, 3),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(int(life * 0.7), life),
                max_life=life,
                size=size + random.uniform(-2, 2),
                color=core_colors[color_idx],
                alpha_start=255,
                gravity=-0.08,
                friction=0.94,
            )

    def emit_explosion_smoke_cloud(
        self, x: float, y: float, count: int = 8, life: int = 40
    ) -> None:
        """Emit explosion smoke cloud."""
        for _ in range(count):
            self._add_particle(
                type=self.ParticleType.SMOKE,
                x=x + random.uniform(-10, 10),
                y=y + random.uniform(-6, 6),
                vx=random.uniform(-4, 4),
                vy=random.uniform(-20, -8),
                life=random.randint(int(life * 0.7), life),
                max_life=life,
                size=random.uniform(8, 20),
                color=random.choice([(80, 80, 80), (100, 100, 100), (70, 70, 70), (60, 65, 60)]),
                alpha_start=180,
                gravity=-0.12,
                friction=0.97,
            )

    def emit_smoke_screen(self, x: float, y: float, radius: float = 144.0) -> None:
        """Emit smoke screen."""
        count = 18
        for i in range(count):
            jagged_factor = random.uniform(0.6, 1.4)
            angle = (i / count) * 2 * math.pi + random.uniform(-0.3, 0.3)
            offset_dist = radius * 0.35 * jagged_factor
            offset_x = math.cos(angle) * offset_dist
            offset_y = math.sin(angle) * offset_dist * 0.7
            self._add_particle(
                type=self.ParticleType.SMOKE_SCREEN,
                x=x + offset_x,
                y=y + offset_y,
                vx=random.uniform(-1.5, 1.5),
                vy=random.uniform(-3, -0.5),
                life=450,
                max_life=450,
                size=radius * (0.35 + random.uniform(-0.05, 0.05)) * jagged_factor,
                color=(192, 200, 192),
                alpha_start=random.randint(170, 200),
                gravity=-0.01,
                friction=0.995,
            )

    def emit_death_puff(self, x: float, y: float, is_vehicle: bool = False) -> None:
        """Emit death puff."""
        if is_vehicle:
            puff_count = 16
            max_size = 30
            puff_life = 25
        else:
            puff_count = 6
            max_size = 15
            puff_life = 12
        for i in range(puff_count):
            angle = random.uniform(0, 2 * math.pi)
            progress = i / max(puff_count - 1, 1)
            size = 5 + progress * (max_size - 5)
            self._add_particle(
                type=self.ParticleType.SMOKE,
                x=x + random.uniform(-4, 4),
                y=y + random.uniform(-3, 3),
                vx=math.cos(angle) * random.uniform(3, 8 if is_vehicle else 4),
                vy=math.sin(angle) * random.uniform(2, 6 if is_vehicle else 3)
                - (2 if is_vehicle else 1),
                life=random.randint(int(puff_life * 0.7), puff_life),
                max_life=puff_life,
                size=size,
                color=(192, 32, 32),
                alpha_start=220,
                gravity=-0.05 if is_vehicle else 0.02,
                friction=0.95,
            )

    def update(self) -> None:
        """Update internal state."""
        if self._pool is not None:
            self._pool.update(self)
            return
        alive = []
        for p in self.particles:
            p.vx *= p.friction
            p.vy *= p.friction
            p.vy += p.gravity
            p.x += p.vx
            p.y += p.vy
            p.rotation += p.rot_speed
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def clear(self) -> None:
        """Clear internal state."""
        self.particles.clear()

    def emit_preset(self, name: str, x: float, y: float, direction: float = 0.0) -> int:
        """Emit particles using a preset configuration. Returns count of emitted particles."""
        preset = self.PRESETS.get(name)
        if not preset:
            return 0

        count = preset["count"]
        speed_range = preset["speed"]
        life_range = preset["life"]
        size_range = preset["size"]
        color = preset["color"]
        spread = preset["spread"]
        gravity = preset.get("gravity", 0.3)

        for _ in range(count):
            angle_offset = random.uniform(-spread / 2, spread / 2) * (math.pi / 180)
            angle = direction + angle_offset
            speed = random.uniform(speed_range[0], speed_range[1])

            self._add_particle(
                type=self.ParticleType.SPARK,
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(life_range[0], life_range[1]),
                max_life=life_range[1],
                size=random.uniform(size_range[0], size_range[1]),
                color=color,
                alpha_start=255,
                gravity=gravity,
                friction=0.95 if gravity > 0 else 0.98,
            )

        return count
