"""UX Feature Tests - Test sound effects, particles, UI response, and tutorial system.

Test Coverage:
1. Sound Effect Manager (16 effect types)
2. Particle System (5 effect types)
3. UI Response Monitor (performance tracking)
4. Tutorial System (12 steps)
"""

import time

import pytest

from pycc2.infrastructure.audio.sound_effect_manager import SoundEffectManager, SoundEffectType
from pycc2.infrastructure.visual.particle_system import (
    Particle,
    ParticleEffect,
    ParticleSystem,
    ParticleType,
)
from pycc2.presentation.ui.tutorial_system import TutorialHintSystem, TutorialStep, TutorialSystem
from pycc2.presentation.ui.ui_response_monitor import UIResponseMonitor, UIResponseOptimizer

# =============================================================================
# Test 1: Sound Effect Manager
# =============================================================================


def test_01_sound_effect_manager_initialization():
    """Test sound effect manager initialization."""
    manager = SoundEffectManager()
    assert manager._volume == 0.7
    assert len(manager._sound_cache) == 0


def test_02_sound_effect_volume_control():
    """Test volume control."""
    manager = SoundEffectManager()

    # Set volume
    manager.set_volume(0.5)
    assert manager._volume == 0.5

    # Clamp to [0, 1]
    manager.set_volume(1.5)
    assert manager._volume == 1.0

    manager.set_volume(-0.5)
    assert manager._volume == 0.0


def test_03_sound_effect_caching():
    """Test sound effect caching."""
    manager = SoundEffectManager()

    # Generate effect (should cache)
    manager.play_effect(SoundEffectType.UI_CLICK)
    assert SoundEffectType.UI_CLICK in manager._sound_cache

    # Second call should use cache
    cache_size_before = len(manager._sound_cache)
    manager.play_effect(SoundEffectType.UI_CLICK)
    assert len(manager._sound_cache) == cache_size_before


def test_04_all_sound_effects_generate():
    """Test all sound effect types can be generated."""
    manager = SoundEffectManager()

    for effect_type in SoundEffectType:
        manager.play_effect(effect_type)
        assert effect_type in manager._sound_cache

    # Should have generated all 16 effect types
    assert len(manager._sound_cache) == 16


# =============================================================================
# Test 2: Particle System
# =============================================================================


def test_05_particle_initialization():
    """Test particle initialization."""
    particle = Particle(
        x=100.0,
        y=200.0,
        vx=50.0,
        vy=-100.0,
        life=1.0,
        max_life=1.0,
        color=(255, 0, 0),
        size=5.0,
    )

    assert particle.x == 100.0
    assert particle.y == 200.0
    assert particle.vx == 50.0
    assert particle.vy == -100.0
    assert particle.life == 1.0


def test_06_particle_update():
    """Test particle update (gravity and lifetime)."""
    particle = Particle(
        x=0.0, y=0.0, vx=100.0, vy=-100.0, life=1.0, max_life=1.0, color=(255, 0, 0), size=5.0
    )

    dt = 0.1
    alive = particle.update(dt)

    # Position should update
    assert particle.x == pytest.approx(10.0, abs=0.1)  # 100 * 0.1
    assert particle.y < 0  # Moving upward initially (vy = -100)

    # Gravity should apply
    assert particle.vy > -100  # Gravity increases vy

    # Lifetime should decrease
    assert particle.life == pytest.approx(0.9, abs=0.01)
    assert alive is True

    # Particle should die after lifetime expires
    for _ in range(15):
        alive = particle.update(dt)

    assert alive is False


def test_07_particle_effect_spawn():
    """Test particle effect spawning."""
    effect = ParticleEffect(100.0, 200.0, ParticleType.EXPLOSION_SMALL)

    # Should spawn 20 particles for small explosion
    assert len(effect.particles) == 20

    # All particles should radiate from center
    for particle in effect.particles:
        assert particle.life > 0
        assert particle.max_life > 0


def test_08_particle_effect_update():
    """Test particle effect update."""
    effect = ParticleEffect(0.0, 0.0, ParticleType.EXPLOSION_SMALL)

    initial_count = len(effect.particles)
    assert initial_count > 0

    # Update for 1 second (particles should die)
    for _ in range(100):
        alive = effect.update(0.01)
        if not alive:
            break

    # All particles should be dead
    assert len(effect.particles) == 0


def test_09_particle_system_management():
    """Test particle system effect management."""
    system = ParticleSystem()

    # Spawn multiple effects
    system.spawn_effect(0, 0, ParticleType.EXPLOSION_SMALL)
    system.spawn_effect(100, 100, ParticleType.EXPLOSION_LARGE)
    system.spawn_effect(200, 200, ParticleType.BUILDING_CONSTRUCT)

    assert len(system.effects) == 3

    # Update until all effects die
    for _ in range(150):
        system.update(0.01)

    # All effects should be removed
    assert len(system.effects) == 0


def test_10_all_particle_types():
    """Test all particle effect types."""
    system = ParticleSystem()

    for particle_type in ParticleType:
        system.spawn_effect(0, 0, particle_type)

    # Should have 5 effect types
    assert len(system.effects) == 5


# =============================================================================
# Test 3: UI Response Monitor
# =============================================================================


def test_11_ui_response_monitor_initialization():
    """Test UI response monitor initialization."""
    monitor = UIResponseMonitor()

    assert monitor._current_interaction is None
    assert len(monitor._metrics) == 0
    assert monitor.get_average_response_time() == 0.0


def test_12_ui_response_timing():
    """Test UI response time measurement."""
    monitor = UIResponseMonitor()

    # Start interaction
    monitor.start_interaction("button_click")
    time.sleep(0.02)  # 20ms

    # End interaction
    duration = monitor.end_interaction()

    assert duration >= 20.0  # Should be at least 20ms
    assert duration < 50.0  # Should be under target
    assert len(monitor._metrics) == 1


def test_13_ui_response_performance_warning():
    """Test performance warning for slow interactions (capture stdout)."""
    monitor = UIResponseMonitor()

    # Simulate slow interaction
    monitor.start_interaction("slow_operation")
    time.sleep(0.06)  # 60ms (exceeds 50ms target)

    duration = monitor.end_interaction()

    assert duration > monitor.TARGET_MS  # Should exceed target


def test_14_ui_response_average():
    """Test average response time calculation."""
    monitor = UIResponseMonitor()

    # Record multiple interactions
    for i in range(5):
        monitor.start_interaction(f"test_{i}")
        time.sleep(0.01)  # 10ms
        monitor.end_interaction()

    avg = monitor.get_average_response_time()
    assert avg >= 10.0  # Should be at least 10ms
    assert avg < 50.0  # Should be under target


def test_15_ui_response_compliance_rate():
    """Test compliance rate calculation."""
    monitor = UIResponseMonitor()

    # 3 fast interactions
    for i in range(3):
        monitor.start_interaction(f"fast_{i}")
        time.sleep(0.01)  # 10ms
        monitor.end_interaction()

    # 1 slow interaction
    monitor.start_interaction("slow")
    time.sleep(0.06)  # 60ms
    monitor.end_interaction()

    compliance = monitor.get_compliance_rate()
    assert compliance == 75.0  # 3/4 = 75%


def test_16_ui_optimizer_debounce():
    """Test debounce decorator."""
    call_count = [0]

    @UIResponseOptimizer.debounce
    def test_func():
        call_count[0] += 1

    # Call multiple times rapidly
    test_func()
    test_func()
    test_func()

    # Only first call should execute
    assert call_count[0] == 1

    # Wait for debounce delay
    time.sleep(0.15)
    test_func()

    # Second call should execute
    assert call_count[0] == 2


def test_17_ui_optimizer_throttle():
    """Test throttle decorator."""
    call_count = [0]

    @UIResponseOptimizer.throttle
    def test_func():
        call_count[0] += 1

    # Call multiple times rapidly
    for _ in range(10):
        test_func()
        time.sleep(0.005)  # 5ms between calls

    # Should throttle to ~60fps (16.67ms interval)
    # In 50ms, should allow ~3 calls
    assert call_count[0] <= 5


# =============================================================================
# Test 4: Tutorial System
# =============================================================================


def test_18_tutorial_system_initialization():
    """Test tutorial system initialization."""
    tutorial = TutorialSystem()

    assert tutorial.enabled is True
    assert tutorial.current_step == TutorialStep.WELCOME
    assert len(tutorial.completed_steps) == 0


def test_19_tutorial_step_advancement():
    """Test tutorial step progression."""
    tutorial = TutorialSystem()

    initial_step = tutorial.current_step
    tutorial.advance_step()

    assert tutorial.current_step != initial_step
    assert initial_step in tutorial.completed_steps


def test_20_tutorial_skip():
    """Test tutorial skip."""
    tutorial = TutorialSystem()

    tutorial.skip_tutorial()

    assert tutorial.enabled is False
    assert tutorial.current_step == TutorialStep.TUTORIAL_COMPLETE


def test_21_tutorial_reset():
    """Test tutorial reset."""
    tutorial = TutorialSystem()

    # Advance a few steps
    tutorial.advance_step()
    tutorial.advance_step()
    tutorial.advance_step()

    # Reset
    tutorial.reset()

    assert tutorial.enabled is True
    assert tutorial.current_step == TutorialStep.WELCOME
    assert len(tutorial.completed_steps) == 0


def test_22_tutorial_all_steps():
    """Test all tutorial steps are defined."""
    tutorial = TutorialSystem()

    # All steps should have messages
    for step in TutorialStep:
        assert step in tutorial._messages


def test_23_tutorial_hint_system():
    """Test tutorial hint system."""
    hints = TutorialHintSystem()

    # Show hint
    hints.show_hint("test_hint", "This is a test hint")
    assert "test_hint" in hints.hints_shown
    assert hints._current_hint == "This is a test hint"

    # Same hint shouldn't show twice
    hints.show_hint("test_hint", "This is a test hint")
    assert len(hints.hints_shown) == 1


def test_24_tutorial_hint_expiration():
    """Test hint expiration."""
    hints = TutorialHintSystem()

    hints.show_hint("test", "Test hint")
    assert hints._current_hint is not None

    # Update for 6 seconds (hint lasts 5 seconds)
    for _ in range(60):
        hints.update(0.1)

    # Hint should expire
    assert hints._current_hint is None


# =============================================================================
# Test Summary
# =============================================================================


def test_25_ux_features_summary():
    """Summary test verifying all UX features."""
    # Sound effects: 16 types
    SoundEffectManager()  # 冒烟验证构造器可用
    assert len(list(SoundEffectType)) == 16

    # Particles: 5 types
    assert len(list(ParticleType)) == 5

    # Tutorial: 10 steps (CC2-only; RTS steps removed)
    assert len(list(TutorialStep)) == 10

    # UI Response: 50ms target
    assert UIResponseMonitor.TARGET_MS == 50.0

    print("\n" + "=" * 70)
    print("UX Features Test Summary")
    print("=" * 70)
    print(f"✅ Sound Effect Types: {len(list(SoundEffectType))}")
    print(f"✅ Particle Effect Types: {len(list(ParticleType))}")
    print(f"✅ Tutorial Steps: {len(list(TutorialStep))}")
    print(f"✅ UI Response Target: {UIResponseMonitor.TARGET_MS}ms")
    print("=" * 70)
