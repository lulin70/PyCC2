"""v0.3.2-A4: 性能profiling脚本 - 识别渲染管线热点路径"""

import cProfile
import io
import os
import pstats
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pygame

pygame.init()

from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
from pycc2.presentation.rendering.particle_system import TopDownParticleSystem


def profile_particle_system():
    """粒子系统性能分析（最可能的瓶颈）"""
    ps = TopDownParticleSystem(max_particles=256)
    screen = pygame.Surface((1024, 768))

    # 生成各种粒子
    for i in range(30):
        ps.spawn_explosion_ring(x=400 + i * 5, y=300)
        ps.spawn_smoke_cloud(x=420 + i * 3, y=320)
        ps.spawn_muzzle_flash(x=200 + i * 10, y=200, direction=0)
        ps.spawn_dirt_splash(x=500, y=400)

    # 预热
    for _ in range(5):
        ps.update(16)
        ps.render(screen)

    pr = cProfile.Profile()
    pr.enable()

    iterations = 120
    t0 = time.perf_counter()
    for _ in range(iterations):
        ps.update(16)
        ps.render(screen)
    elapsed = time.perf_counter() - t0

    pr.disable()

    print(f"\n{'=' * 60}")
    print(
        f"粒子系统 profiling: {iterations}帧, 耗时{elapsed:.3f}s ({iterations / elapsed:.1f} FPS)"
    )
    print(f"{'=' * 60}")

    s = io.StringIO()
    stats = pstats.Stats(pr, stream=s).sort_stats("tottime")
    stats.print_stats(25)
    print(s.getvalue())


def profile_sprite_generation():
    """精灵生成性能分析"""
    renderer = EnhancedRenderer(seed=42)

    pr = cProfile.Profile()
    pr.enable()

    for _ in range(100):
        renderer._draw_tree_oak(pygame.Surface((48, 48)), variant=1)
        renderer._draw_bush_small(pygame.Surface((48, 48)), variant=2)
        renderer._draw_crater_small(pygame.Surface((48, 48)), variant=0)
        renderer._draw_sandbag(pygame.Surface((48, 48)), variant=1)

    pr.disable()

    s = io.StringIO()
    stats = pstats.Stats(pr, stream=s).sort_stats("tottime")
    stats.print_stats(15)
    print("\n=== 精灵生成热点 (100次迭代) ===")
    print(s.getvalue())


if __name__ == "__main__":
    profile_particle_system()
