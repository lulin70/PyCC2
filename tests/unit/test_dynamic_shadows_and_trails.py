"""
Tests for Dynamic Shadow System and Projectile Trail System.
"""

import math
import pygame
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame.init()


class TestDynamicShadowSystem:
    def test_init(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem(tile_size=48)
        assert dss.TILE_SIZE == 48

    def test_set_time_of_day(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem()
        dss.set_time_of_day(0.75)
        assert dss._time_of_day == 0.75

    def test_set_time_of_day_clamped(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem()
        dss.set_time_of_day(1.5)
        assert dss._time_of_day == 1.0
        dss.set_time_of_day(-0.5)
        assert dss._time_of_day == 0.0

    def test_shadow_direction_at_noon(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem()
        dss.set_time_of_day(0.5)
        dx, dy = dss.get_shadow_direction()
        assert abs(dx) <= 1.0
        assert abs(dy) <= 1.0

    def test_shadow_direction_normalized(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem()
        for tod in [0.1, 0.3, 0.5, 0.7, 0.9]:
            dss.set_time_of_day(tod)
            dx, dy = dss.get_shadow_direction()
            length = math.sqrt(dx * dx + dy * dy)
            assert abs(length - 1.0) < 0.01, f"Direction not normalized at tod={tod}"

    def test_shadow_length_multiplier_range(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem()
        for tod in [0.2, 0.3, 0.5, 0.7, 0.8]:
            dss.set_time_of_day(tod)
            mult = dss.get_shadow_length_multiplier()
            assert dss.MIN_SHADOW_LENGTH <= mult <= dss.MAX_SHADOW_LENGTH

    def test_shadow_alpha_night(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem()
        dss.set_time_of_day(0.1)
        assert dss.get_shadow_alpha() == dss.NIGHT_ALPHA

    def test_shadow_alpha_noon(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem()
        dss.set_time_of_day(0.5)
        assert dss.get_shadow_alpha() == dss.NOON_ALPHA

    def test_shadow_alpha_dawn(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem()
        dss.set_time_of_day(0.25)
        assert dss.get_shadow_alpha() == dss.DAWN_DUSK_ALPHA

    def test_render_building_shadow_no_crash(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem()
        dss.set_time_of_day(0.5)
        surface = pygame.Surface((200, 200), pygame.SRCALPHA)
        dss.render_building_shadow(surface, 50, 50, 48, 48)

    def test_render_tree_shadow_no_crash(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem()
        dss.set_time_of_day(0.5)
        surface = pygame.Surface((200, 200), pygame.SRCALPHA)
        dss.render_tree_shadow(surface, 100, 100, tree_radius=12)

    def test_render_unit_shadow_no_crash(self):
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
        dss = DynamicShadowSystem()
        dss.set_time_of_day(0.5)
        surface = pygame.Surface((200, 200), pygame.SRCALPHA)
        dss.render_unit_shadow(surface, 80, 80, unit_width=16, unit_height=16)
        dss.render_unit_shadow(surface, 80, 80, unit_width=32, unit_height=32, is_vehicle=True)


class TestProjectileTrailSystem:
    def test_init(self):
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
        pts = ProjectileTrailSystem()
        assert pts.count() == 0

    def test_add_bullet_trail(self):
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
        pts = ProjectileTrailSystem()
        pts.add_bullet_trail(0, 0, 100, 50)
        assert pts.count() == 1

    def test_add_shell_trail(self):
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
        pts = ProjectileTrailSystem()
        pts.add_shell_trail(0, 0, 200, 100)
        assert pts.count() == 1

    def test_add_rocket_trail(self):
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
        pts = ProjectileTrailSystem()
        pts.add_rocket_trail(0, 0, 150, 75)
        assert pts.count() == 1

    def test_add_mortar_trail(self):
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
        pts = ProjectileTrailSystem()
        pts.add_mortar_trail(0, 0, 300, 150)
        assert pts.count() == 1

    def test_max_trails_limit(self):
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
        pts = ProjectileTrailSystem(max_trails=5)
        for i in range(10):
            pts.add_bullet_trail(i * 10, 0, i * 10 + 50, 50)
        assert pts.count() <= 5

    def test_update_removes_expired(self):
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
        pts = ProjectileTrailSystem()
        pts.add_bullet_trail(0, 0, 100, 50)
        pts.update(1.0)
        assert pts.count() == 0

    def test_update_keeps_active(self):
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
        pts = ProjectileTrailSystem()
        pts.add_bullet_trail(0, 0, 100, 50)
        pts.update(0.01)
        assert pts.count() == 1

    def test_render_no_crash(self):
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
        pts = ProjectileTrailSystem()
        pts.add_bullet_trail(10, 10, 100, 50)
        pts.add_shell_trail(20, 20, 200, 100)
        surface = pygame.Surface((300, 200), pygame.SRCALPHA)
        pts.render(surface)

    def test_clear(self):
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
        pts = ProjectileTrailSystem()
        pts.add_bullet_trail(0, 0, 100, 50)
        pts.add_shell_trail(0, 0, 200, 100)
        pts.clear()
        assert pts.count() == 0

    def test_mortar_trail_has_arc(self):
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrail
        trail = ProjectileTrail(0, 100, 200, 100, "mortar", 0.5)
        assert len(trail._particles) == 15
        mid_particle = trail._particles[len(trail._particles) // 2]
        assert mid_particle["y"] < 100, "Mortar trail should arc upward"
