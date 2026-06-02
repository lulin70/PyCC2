"""
Tests for Camera Effects System.
"""

import math
import pytest
from pycc2.presentation.rendering.camera_effects import (
    EffectType, CameraEffect, EffectStack,
    create_shake, create_zoom_impact, create_slow_motion,
    create_push_pull, create_screen_freeze,
)


class TestEffectType:
    def test_all_types_exist(self):
        assert EffectType.SHAKE is not None
        assert EffectType.ZOOM_IMPACT is not None
        assert EffectType.SLOW_MOTION is not None
        assert EffectType.PUSH_PULL is not None
        assert EffectType.SCREEN_FREEZE is not None

    def test_type_count(self):
        assert len(EffectType) == 5


class TestCameraEffect:
    def test_initial_state(self):
        effect = CameraEffect(effect_type=EffectType.SHAKE, duration=0.5)
        assert effect.elapsed == 0.0
        assert not effect.is_complete()

    def test_is_complete(self):
        effect = CameraEffect(effect_type=EffectType.SHAKE, duration=0.3)
        effect.elapsed = 0.3
        assert effect.is_complete()

    def test_is_not_complete_before_duration(self):
        effect = CameraEffect(effect_type=EffectType.SHAKE, duration=0.5)
        effect.elapsed = 0.3
        assert not effect.is_complete()

    def test_get_progress_zero(self):
        effect = CameraEffect(effect_type=EffectType.SHAKE, duration=1.0)
        assert effect.get_progress() == 0.0

    def test_get_progress_half(self):
        effect = CameraEffect(effect_type=EffectType.SHAKE, duration=1.0)
        effect.elapsed = 0.5
        assert abs(effect.get_progress() - 0.5) < 0.001

    def test_get_progress_full(self):
        effect = CameraEffect(effect_type=EffectType.SHAKE, duration=1.0)
        effect.elapsed = 1.0
        assert effect.get_progress() == 1.0

    def test_zero_duration_progress(self):
        effect = CameraEffect(effect_type=EffectType.SHAKE, duration=0.0)
        assert effect.get_progress() == 1.0

    def test_easing_linear(self):
        effect = CameraEffect(effect_type=EffectType.SHAKE, easing="linear")
        assert effect.apply_easing(0.0) == 0.0
        assert effect.apply_easing(0.5) == 0.5
        assert effect.apply_easing(1.0) == 1.0

    def test_easing_ease_out(self):
        effect = CameraEffect(effect_type=EffectType.SHAKE, easing="ease_out")
        assert effect.apply_easing(0.0) == 0.0
        assert effect.apply_easing(1.0) == 1.0
        assert effect.apply_easing(0.5) > 0.5

    def test_easing_ease_in(self):
        effect = CameraEffect(effect_type=EffectType.SHAKE, easing="ease_in")
        assert effect.apply_easing(0.0) == 0.0
        assert effect.apply_easing(1.0) == 1.0
        assert effect.apply_easing(0.5) < 0.5

    def test_easing_elastic_boundaries(self):
        effect = CameraEffect(effect_type=EffectType.SHAKE, easing="elastic")
        assert effect.apply_easing(0.0) == 0.0
        assert effect.apply_easing(1.0) == 1.0

    def test_shake_offset_within_range(self):
        effect = CameraEffect(
            effect_type=EffectType.SHAKE,
            intensity=5.0,
            duration=1.0,
            easing="linear",
        )
        effect.elapsed = 0.5
        ox, oy = effect.get_offset()
        assert abs(ox) <= 5.0
        assert abs(oy) <= 5.0

    def test_zoom_impact_offset_is_zero(self):
        effect = CameraEffect(effect_type=EffectType.ZOOM_IMPACT)
        ox, oy = effect.get_offset()
        assert ox == 0.0
        assert oy == 0.0

    def test_slow_motion_offset_is_zero(self):
        effect = CameraEffect(effect_type=EffectType.SLOW_MOTION)
        ox, oy = effect.get_offset()
        assert ox == 0.0
        assert oy == 0.0

    def test_screen_freeze_offset_is_zero(self):
        effect = CameraEffect(effect_type=EffectType.SCREEN_FREEZE)
        ox, oy = effect.get_offset()
        assert ox == 0.0
        assert oy == 0.0

    def test_push_pull_offset_push_phase(self):
        effect = CameraEffect(
            effect_type=EffectType.PUSH_PULL,
            push_distance=20.0,
            duration=1.0,
            easing="linear",
        )
        effect.elapsed = 0.25
        ox, oy = effect.get_offset()
        assert ox > 0
        assert oy > 0

    def test_push_pull_offset_pull_phase(self):
        effect = CameraEffect(
            effect_type=EffectType.PUSH_PULL,
            push_distance=20.0,
            duration=1.0,
            easing="linear",
        )
        effect.elapsed = 0.75
        ox, oy = effect.get_offset()
        assert ox < 0
        assert oy < 0


class TestEffectStack:
    def test_empty_stack(self):
        stack = EffectStack()
        assert stack.is_empty()
        assert len(stack) == 0

    def test_push_effect(self):
        stack = EffectStack()
        stack.push(create_shake())
        assert not stack.is_empty()
        assert len(stack) == 1

    def test_update_removes_completed(self):
        stack = EffectStack()
        effect = CameraEffect(effect_type=EffectType.SHAKE, duration=0.1)
        stack.push(effect)
        stack.update(0.2)
        assert stack.is_empty()

    def test_update_keeps_active(self):
        stack = EffectStack()
        effect = CameraEffect(effect_type=EffectType.SHAKE, duration=1.0)
        stack.push(effect)
        stack.update(0.5)
        assert len(stack) == 1

    def test_max_effects_limit(self):
        stack = EffectStack(max_effects=3)
        for i in range(5):
            stack.push(CameraEffect(
                effect_type=EffectType.SHAKE,
                duration=1.0,
                priority=i,
            ))
        assert len(stack) <= 3

    def test_priority_sorting(self):
        stack = EffectStack()
        stack.push(CameraEffect(effect_type=EffectType.SHAKE, priority=1, duration=1.0))
        stack.push(CameraEffect(effect_type=EffectType.SLOW_MOTION, priority=10, duration=1.0))
        stack.push(CameraEffect(effect_type=EffectType.ZOOM_IMPACT, priority=5, duration=1.0))
        assert stack._effects[0].effect_type == EffectType.SLOW_MOTION
        assert stack._effects[1].effect_type == EffectType.ZOOM_IMPACT
        assert stack._effects[2].effect_type == EffectType.SHAKE

    def test_get_total_offset_shake(self):
        stack = EffectStack()
        stack.push(CameraEffect(
            effect_type=EffectType.SHAKE,
            intensity=10.0,
            duration=1.0,
            easing="linear",
        ))
        ox, oy = stack.get_total_offset()
        assert isinstance(ox, float)
        assert isinstance(oy, float)

    def test_get_zoom_multiplier_no_effects(self):
        stack = EffectStack()
        assert stack.get_zoom_multiplier() == 1.0

    def test_get_zoom_multiplier_with_zoom(self):
        stack = EffectStack()
        stack.push(CameraEffect(
            effect_type=EffectType.ZOOM_IMPACT,
            zoom_factor=0.8,
            duration=1.0,
            easing="linear",
        ))
        zoom = stack.get_zoom_multiplier()
        assert 0.5 <= zoom <= 2.0

    def test_get_time_scale_no_effects(self):
        stack = EffectStack()
        assert stack.get_time_scale() == 1.0

    def test_get_time_scale_with_slow_motion(self):
        stack = EffectStack()
        stack.push(CameraEffect(
            effect_type=EffectType.SLOW_MOTION,
            time_scale=0.3,
            duration=1.0,
        ))
        assert stack.get_time_scale() == 0.3

    def test_get_time_scale_minimum_is_0_1(self):
        stack = EffectStack()
        stack.push(CameraEffect(
            effect_type=EffectType.SLOW_MOTION,
            time_scale=0.01,
            duration=1.0,
        ))
        assert stack.get_time_scale() >= 0.1

    def test_is_frozen_no_effects(self):
        stack = EffectStack()
        assert not stack.is_frozen()

    def test_is_frozen_with_freeze(self):
        stack = EffectStack()
        stack.push(CameraEffect(
            effect_type=EffectType.SCREEN_FREEZE,
            duration=1.0,
        ))
        assert stack.is_frozen()

    def test_clear(self):
        stack = EffectStack()
        stack.push(create_shake())
        stack.push(create_slow_motion())
        stack.clear()
        assert stack.is_empty()


class TestFactoryFunctions:
    def test_create_shake(self):
        effect = create_shake(intensity=5.0, duration=0.2)
        assert effect.effect_type == EffectType.SHAKE
        assert effect.intensity == 5.0
        assert effect.duration == 0.2

    def test_create_zoom_impact(self):
        effect = create_zoom_impact(zoom_factor=0.7, duration=0.1, recover=0.4)
        assert effect.effect_type == EffectType.ZOOM_IMPACT
        assert effect.zoom_factor == 0.7
        assert effect.duration == 0.5

    def test_create_slow_motion(self):
        effect = create_slow_motion(time_scale=0.2, duration=2.0)
        assert effect.effect_type == EffectType.SLOW_MOTION
        assert effect.time_scale == 0.2
        assert effect.duration == 2.0

    def test_create_push_pull(self):
        effect = create_push_pull(distance=40.0, duration=0.5)
        assert effect.effect_type == EffectType.PUSH_PULL
        assert effect.push_distance == 40.0

    def test_create_screen_freeze(self):
        effect = create_screen_freeze(duration=0.5)
        assert effect.effect_type == EffectType.SCREEN_FREEZE
        assert effect.duration == 0.5

    def test_default_priorities(self):
        shake = create_shake()
        zoom = create_zoom_impact()
        slow = create_slow_motion()
        push = create_push_pull()
        freeze = create_screen_freeze()
        assert freeze.priority > slow.priority
        assert slow.priority > zoom.priority
        assert zoom.priority > push.priority
        assert push.priority > shake.priority
