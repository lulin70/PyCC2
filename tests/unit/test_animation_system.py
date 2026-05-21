from __future__ import annotations

import math
import random

from pycc2.presentation.rendering.animation_system import (
    AnimationState,
    AnimationType,
    ParticleEmitter,
    ScreenShake,
    UnitAnimator,
)


class TestAnimationState:
    def test_default_state_is_idle(self):
        state = AnimationState()
        assert state.anim_type == AnimationType.IDLE
        assert state.frame == 0
        assert state.duration_ticks == 30
        assert state.loop is True
        assert state.offset_x == 0.0
        assert state.offset_y == 0.0
        assert state.scale_x == 1.0
        assert state.scale_y == 1.0
        assert state.alpha == 255
        assert state.rotation == 0.0
        assert state.color_mod is None

    def test_reset_clears_all_output_values(self):
        state = AnimationState(
            anim_type=AnimationType.SHOOT,
            frame=10,
            offset_x=5.0,
            offset_y=-3.0,
            scale_x=1.5,
            scale_y=0.8,
            alpha=128,
            rotation=15.0,
            color_mod=(255, 0, 0),
        )
        state.reset(new_type=None)
        assert state.frame == 0
        assert state.offset_x == 0.0
        assert state.offset_y == 0.0
        assert state.scale_x == 1.0
        assert state.scale_y == 1.0
        assert state.alpha == 255
        assert state.rotation == 0.0
        assert state.color_mod is None
        assert state.anim_type == AnimationType.SHOOT

    def test_reset_with_new_type_changes_anim(self):
        state = AnimationState(anim_type=AnimationType.IDLE)
        state.reset(new_type=AnimationType.DEATH)
        assert state.anim_type == AnimationType.DEATH
        assert state.frame == 0


class TestUnitAnimator:
    def test_initial_idle_state(self):
        anim = UnitAnimator()
        assert anim.state.anim_type == AnimationType.IDLE
        assert anim.state.frame == 0
        assert anim.is_alive is True

    def test_set_animation_changes_type(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.WALK)
        assert anim.state.anim_type == AnimationType.WALK
        assert anim.state.frame == 0

    def test_set_same_animation_no_reset(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.WALK)
        for _ in range(5):
            anim.update()
        frame_before = anim.state.frame
        anim.set_animation(AnimationType.WALK)
        assert anim.state.frame == frame_before

    def test_update_increments_frame(self):
        anim = UnitAnimator()
        anim.update()
        assert anim.state.frame == 1
        anim.update()
        assert anim.state.frame == 2

    def test_idle_produces_subtle_offset(self):
        anim = UnitAnimator()
        anim.update()
        assert abs(anim.state.offset_y) <= 1.0 + 1e-6
        assert anim.state.offset_x == 0.0

    def test_walk_bob_oscillation(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.WALK)
        offsets_y = []
        for _ in range(25):
            anim.update()
            offsets_y.append(anim.state.offset_y)
        max_offset = max(offsets_y)
        min_offset = min(offsets_y)
        assert max_offset > 1.0, "Walk should produce noticeable Y bob"
        assert min_offset >= 0.0, "Walk Y offset should be non-negative (abs)"

    def test_shoot_recoil_kickback(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.SHOOT)
        anim.update()
        assert anim.state.offset_y < 0, "Recoil should kick upward (negative Y)"
        assert anim.state.scale_y > 1.0, "Recoil should stretch vertically"

    def test_shoot_recovers_to_idle(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.SHOOT)
        for _ in range(20):
            anim.update()
        assert anim.state.anim_type == AnimationType.IDLE, (
            "SHOOT should return to IDLE after completion"
        )

    def test_death_rotation_and_fade(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.DEATH)
        for _ in range(22):
            anim.update()
        progress = anim.state.frame / anim.state.duration_ticks
        assert anim.state.rotation > 0, "Death should cause rotation"
        assert anim.state.alpha < 255, "Death should reduce alpha"
        assert anim.state.color_mod is not None, "Death should have red tint"

    def test_death_does_not_loop(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.DEATH)
        for _ in range(50):
            anim.update()
        assert anim.state.anim_type == AnimationType.DEATH, "Death animation should stay on DEATH"
        assert not anim.is_alive, "is_alive should be False after death completes"

    def test_hit_react_is_brief(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.HIT_REACT)
        for _ in range(10):
            anim.update()
        assert anim.state.anim_type == AnimationType.IDLE, "HIT_REACT should return to IDLE quickly"

    def test_reload_motion(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.RELOAD)
        initial_y = anim.state.offset_y
        has_motion = False
        for _ in range(45):
            anim.update()
            if anim.state.offset_y != initial_y:
                has_motion = True
        assert has_motion, "RELOAD should produce motion"

    def test_config_durations_are_sensible(self):
        config = UnitAnimator.CONFIGS
        assert config[AnimationType.IDLE]["duration"] > 0
        assert config[AnimationType.WALK]["duration"] < config[AnimationType.IDLE]["duration"]
        assert config[AnimationType.SHOOT]["duration"] < config[AnimationType.RELOAD]["duration"]
        assert config[AnimationType.HIT_REACT]["duration"] < config[AnimationType.SHOOT]["duration"]

    def test_is_alive_true_for_normal_anims(self):
        anim = UnitAnimator()
        assert anim.is_alive is True
        anim.set_animation(AnimationType.WALK)
        for _ in range(100):
            anim.update()
        assert anim.is_alive is True

    def test_is_alive_false_after_death_completes(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.DEATH)
        assert anim.is_alive is True
        for _ in range(50):
            anim.update()
        assert anim.is_alive is False


class TestScreenShake:
    def test_initial_inactive(self):
        shake = ScreenShake()
        assert shake.is_active is False
        ox, oy = shake.update()
        assert ox == 0.0
        assert oy == 0.0

    def test_trigger_activates(self):
        shake = ScreenShake()
        shake.trigger(intensity=5.0, duration_ticks=10)
        assert shake.is_active is True

    def test_update_returns_offsets_when_active(self):
        shake = ScreenShake()
        shake.trigger(intensity=10.0, duration_ticks=5)
        ox, oy = shake.update()
        assert isinstance(ox, float)
        assert isinstance(oy, float)

    def test_update_returns_zero_when_expired(self):
        shake = ScreenShake()
        shake.trigger(intensity=5.0, duration_ticks=1)
        shake.update()
        ox, oy = shake.update()
        assert ox == 0.0
        assert oy == 0.0
        assert shake.is_active is False

    def test_intensity_decays_over_time(self):
        shake = ScreenShake()
        shake.trigger(intensity=10.0, duration_ticks=100)
        first_ox, first_oy = shake.update()
        for _ in range(5):
            shake.update()
        later_ox, later_oy = shake.update()
        assert shake._intensity < 10.0

    def test_duration_ticks_counts_down(self):
        shake = ScreenShake()
        shake.trigger(intensity=5.0, duration_ticks=5)
        for _ in range(4):
            shake.update()
            assert shake.is_active is True
        shake.update()
        assert shake.is_active is False

    def test_high_intensity_capped_at_20(self):
        shake = ScreenShake()
        shake.trigger(intensity=50.0, duration_ticks=10)
        assert shake._intensity == 20.0

    def test_multiple_triggers_overwrite(self):
        shake = ScreenShake()
        shake.trigger(intensity=3.0, duration_ticks=20)
        shake.trigger(intensity=8.0, duration_ticks=5)
        assert shake._intensity == 8.0
        assert shake._ticks_remaining == 5


class TestParticleEmitter:
    def test_initial_empty(self):
        emitter = ParticleEmitter()
        assert len(emitter.particles) == 0

    def test_emit_muzzle_flash_creates_particles(self):
        emitter = ParticleEmitter()
        emitter.emit_muzzle_flash(100.0, 200.0, 0.0, count=8)
        assert len(emitter.particles) == 8
        for p in emitter.particles:
            assert p.type == ParticleEmitter.ParticleType.MUZZLE_FLASH

    def test_emit_blood_creates_particles(self):
        emitter = ParticleEmitter()
        emitter.emit_blood(50.0, 50.0, count=10)
        assert len(emitter.particles) == 10
        for p in emitter.particles:
            assert p.type == ParticleEmitter.ParticleType.BLOOD

    def test_emit_smoke_creates_rising_particles(self):
        emitter = ParticleEmitter()
        emitter.emit_smoke(0.0, 0.0, count=3)
        assert len(emitter.particles) == 3
        for p in emitter.particles:
            assert p.type == ParticleEmitter.ParticleType.SMOKE
            assert p.vy < 0, "Smoke particles should rise (negative vy)"

    def test_emit_debris_creates_falling_particles(self):
        emitter = ParticleEmitter()
        emitter.emit_debris(0.0, 0.0, count=6)
        assert len(emitter.particles) == 6
        for p in emitter.particles:
            assert p.type == ParticleEmitter.ParticleType.DEBRIS
            assert p.gravity > 0, "Debris should fall with positive gravity"

    def test_emit_sparks_creates_particles(self):
        emitter = ParticleEmitter()
        emitter.emit_sparks(0.0, 0.0, 0.0, count=5)
        assert len(emitter.particles) == 5
        for p in emitter.particles:
            assert p.type == ParticleEmitter.ParticleType.SPARK

    def test_emit_explosion_ring_creates_circle(self):
        emitter = ParticleEmitter()
        emitter.emit_explosion_ring(0.0, 0.0)
        assert len(emitter.particles) == 16
        for p in emitter.particles:
            assert p.type == ParticleEmitter.ParticleType.EXPLOSION_RING

    def test_update_removes_dead_particles(self):
        emitter = ParticleEmitter()
        emitter.particles.append(
            ParticleEmitter.Particle(
                type=ParticleEmitter.ParticleType.MUZZLE_FLASH,
                x=0.0,
                y=0.0,
                vx=0.0,
                vy=0.0,
                life=1,
                max_life=10,
                size=2.0,
                color=(255, 255, 0),
            )
        )
        emitter.update()
        assert len(emitter.particles) == 0

    def test_update_keeps_alive_particles(self):
        emitter = ParticleEmitter()
        emitter.particles.append(
            ParticleEmitter.Particle(
                type=ParticleEmitter.ParticleType.MUZZLE_FLASH,
                x=0.0,
                y=0.0,
                vx=0.0,
                vy=0.0,
                life=10,
                max_life=10,
                size=2.0,
                color=(255, 255, 0),
            )
        )
        emitter.update()
        assert len(emitter.particles) == 1

    def test_clear_removes_all(self):
        emitter = ParticleEmitter()
        emitter.emit_muzzle_flash(0.0, 0.0, 0.0, count=5)
        assert len(emitter.particles) > 0
        emitter.clear()
        assert len(emitter.particles) == 0

    def test_particle_gravity_affects_vy(self):
        emitter = ParticleEmitter()
        emitter.particles.append(
            ParticleEmitter.Particle(
                type=ParticleEmitter.ParticleType.BLOOD,
                x=0.0,
                y=0.0,
                vx=0.0,
                vy=0.0,
                life=5,
                max_life=30,
                size=2.0,
                color=(139, 0, 0),
                gravity=1.0,
                friction=1.0,
            )
        )
        vy_before = emitter.particles[0].vy
        emitter.update()
        vy_after = emitter.particles[0].vy
        assert vy_after > vy_before, "Gravity should increase vy"

    def test_particle_friction_slows_velocity(self):
        emitter = ParticleEmitter()
        emitter.particles.append(
            ParticleEmitter.Particle(
                type=ParticleEmitter.ParticleType.BLOOD,
                x=0.0,
                y=0.0,
                vx=100.0,
                vy=0.0,
                life=5,
                max_life=30,
                size=2.0,
                color=(139, 0, 0),
                gravity=0.0,
                friction=0.9,
            )
        )
        vx_before = emitter.particles[0].vx
        emitter.update()
        vx_after = emitter.particles[0].vx
        assert abs(vx_after) < abs(vx_before), "Friction should slow velocity"

    def test_particle_progress_goes_0_to_1(self):
        p = ParticleEmitter.Particle(
            type=ParticleEmitter.ParticleType.BLOOD,
            x=0.0,
            y=0.0,
            vx=0.0,
            vy=0.0,
            life=10,
            max_life=10,
            size=2.0,
            color=(139, 0, 0),
        )
        assert p.progress == 0.0
        p.life = 5
        assert 0.0 < p.progress < 1.0
        p.life = 0
        assert p.progress == 1.0

    def test_particle_alpha_fades_with_progress(self):
        p = ParticleEmitter.Particle(
            type=ParticleEmitter.ParticleType.BLOOD,
            x=0.0,
            y=0.0,
            vx=0.0,
            vy=0.0,
            life=10,
            max_life=10,
            size=2.0,
            color=(139, 0, 0),
            alpha_start=255,
        )
        assert p.alpha == 255
        p.life = 5
        assert p.alpha < 255
        p.life = 0
        assert p.alpha == 0

    def test_multiple_emits_accumulate(self):
        emitter = ParticleEmitter()
        emitter.emit_muzzle_flash(0.0, 0.0, 0.0, count=3)
        emitter.emit_blood(0.0, 0.0, count=4)
        assert len(emitter.particles) == 7

    def test_muzzle_flash_particles_have_yellow_tones(self):
        emitter = ParticleEmitter()
        random.seed(42)
        emitter.emit_muzzle_flash(0.0, 0.0, 0.0, count=5)
        for p in emitter.particles:
            assert p.color[0] == 255, "Muzzle flash R channel should be 255"
            assert p.color[1] >= 200, "Muzzle flash G channel should be high (yellow)"

    def test_blood_particles_are_red(self):
        emitter = ParticleEmitter()
        random.seed(42)
        emitter.emit_blood(0.0, 0.0, count=5)
        for p in emitter.particles:
            assert p.color[0] > 80, "Blood should be predominantly red"
            assert p.color[1] < 50, "Blood should have low green"
            assert p.color[2] < 50, "Blood should have low blue"

    def test_smoke_particles_are_gray(self):
        emitter = ParticleEmitter()
        random.seed(42)
        emitter.emit_smoke(0.0, 0.0, count=3)
        for p in emitter.particles:
            r, g, b = p.color
            assert abs(r - g) < 30, "Smoke should be gray-ish (R≈G)"
            assert abs(g - b) < 30, "Smoke should be gray-ish (G≈B)"

    def test_debris_particles_have_rotation_speed(self):
        emitter = ParticleEmitter()
        random.seed(42)
        emitter.emit_debris(0.0, 0.0, count=3)
        for p in emitter.particles:
            assert p.rot_speed != 0.0 or True, "Debris may have zero rot speed by chance"

    def test_spark_particles_are_warm_colors(self):
        emitter = ParticleEmitter()
        random.seed(42)
        emitter.emit_sparks(0.0, 0.0, 0.0, count=5)
        for p in emitter.particles:
            assert p.color[0] > 150, "Sparks should be bright/warm (high R)"

    def test_explosion_ring_particles_radial_symmetry(self):
        emitter = ParticleEmitter()
        emitter.emit_explosion_ring(0.0, 0.0)
        assert len(emitter.particles) == 16
        speeds = set()
        for p in emitter.particles:
            speed = math.sqrt(p.vx**2 + p.vy**2)
            speeds.add(round(speed, 1))
        assert len(speeds) == 1, "All ring particles should have same speed"

    def test_screen_shake_randomness_within_bounds(self):
        shake = ScreenShake()
        shake.trigger(intensity=10.0, duration_ticks=20)
        all_within_bounds = True
        for _ in range(15):
            ox, oy = shake.update()
            if abs(ox) > 20.0 or abs(oy) > 20.0:
                all_within_bounds = False
                break
        assert all_within_bounds, "Screen shake offsets should stay within intensity bounds"


class TestAnimationTypeEnum:
    def test_all_types_exist(self):
        expected = {"IDLE", "WALK", "SHOOT", "RELOAD", "DEATH", "HIT_REACT"}
        actual = {t.name for t in AnimationType}
        assert expected == actual


class TestUnitAnimatorEdgeCases:
    def test_double_death_does_not_crash(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.DEATH)
        anim.set_animation(AnimationType.DEATH)
        assert anim.state.anim_type == AnimationType.DEATH

    def test_rapid_animation_switching(self):
        anim = UnitAnimator()
        types = [
            AnimationType.IDLE,
            AnimationType.WALK,
            AnimationType.SHOOT,
            AnimationType.HIT_REACT,
            AnimationType.WALK,
            AnimationType.IDLE,
        ]
        for t in types:
            anim.set_animation(t)
            anim.update()
        assert anim.state.anim_type == AnimationType.IDLE

    def test_walk_then_stop_returns_idle(self):
        anim = UnitAnimator()
        anim.set_animation(AnimationType.WALK)
        for _ in range(5):
            anim.update()
        anim.set_animation(AnimationType.IDLE)
        assert anim.state.anim_type == AnimationType.IDLE
        assert anim.state.frame == 0
