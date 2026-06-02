"""
Camera Effects System - Cinematic visual feedback for combat events.

Provides 5 camera effect types for immersive gameplay:
1. SHAKE - Screen vibration (existing, enhanced)
2. ZOOM_IMPACT - Sniper/explosion zoom (quick zoom out + slow recover)
3. SLOW_MOTION - Time dilation for key moments (kill shots)
4. PUSH_PULL - Dramatic camera push-pull movement (big explosions)
5. SCREEN_FREEZE - Dramatic pause (victory moments)

All effects managed by EffectStack with priority queuing.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
import math
import random
from typing import List, Optional, Tuple


class EffectType(Enum):
    """Camera effect type enumeration."""
    SHAKE = auto()
    ZOOM_IMPACT = auto()
    SLOW_MOTION = auto()
    PUSH_PULL = auto()
    SCREEN_FREEZE = auto()


@dataclass
class CameraEffect:
    """Single camera effect configuration and state."""
    effect_type: EffectType
    intensity: float = 1.0
    duration: float = 0.3
    elapsed: float = 0.0
    easing: str = "ease_out"
    priority: int = 0
    
    # Type-specific parameters
    zoom_factor: float = 0.8
    time_scale: float = 0.3
    push_distance: float = 20.0
    recover_duration: float = 0.5

    def is_complete(self) -> bool:
        return self.elapsed >= self.duration

    def get_progress(self) -> float:
        if self.duration <= 0:
            return 1.0
        return min(1.0, self.elapsed / self.duration)

    def apply_easing(self, t: float) -> float:
        if self.easing == "linear":
            return t
        elif self.easing == "ease_in":
            return t * t
        elif self.easing == "ease_out":
            return 1.0 - (1.0 - t) * (1.0 - t)
        elif self.easing == "ease_in_out":
            if t < 0.5:
                return 2 * t * t
            else:
                return 1.0 - pow(-2 * t + 2, 2) / 2
        elif self.easing == "elastic":
            if t == 0 or t == 1:
                return t
            return pow(2, -10 * t) * math.sin((t * 10 - 10.75) * (2 * math.pi / 3)) + 1
        elif self.easing == "bounce":
            n = 7
            if t == 0 or t == 1:
                return t
            return pow(2, -10 * t) * abs(math.sin(t * 10 * math.pi)) + 1
        else:
            return t

    def get_offset(self) -> Tuple[float, float]:
        """Calculate current offset based on effect type and progress."""
        progress = self.apply_easing(self.get_progress())
        
        if self.effect_type == EffectType.SHAKE:
            shake_x = (random.random() - 0.5) * 2 * self.intensity * (1 - progress)
            shake_y = (random.random() - 0.5) * 2 * self.intensity * (1 - progress)
            return (shake_x, shake_y)

        elif self.effect_type == EffectType.PUSH_PULL:
            if progress < 0.5:
                push_progress = progress * 2
                offset = self.push_distance * push_progress * self.intensity
                return (offset, offset)
            else:
                pull_progress = (progress - 0.5) * 2
                offset = self.push_distance * (1 - pull_progress) * self.intensity
                return (-offset * 0.5, -offset * 0.5)

        elif self.effect_type == EffectType.ZOOM_IMPACT:
            return (0.0, 0.0)

        elif self.effect_type == EffectType.SLOW_MOTION:
            return (0.0, 0.0)

        elif self.effect_type == EffectType.SCREEN_FREEZE:
            return (0.0, 0.0)

        return (0.0, 0.0)


class EffectStack:
    """Manages multiple simultaneous camera effects with priority queuing."""

    def __init__(self, max_effects: int = 8):
        self._effects: List[CameraEffect] = []
        self._max_effects = max_effects

    def push(self, effect: CameraEffect) -> None:
        """Add new effect, sorted by priority."""
        self._effects.append(effect)
        self._effects.sort(key=lambda e: e.priority, reverse=True)
        while len(self._effects) > self._max_effects:
            self._effects.pop()

    def update(self, dt: float) -> None:
        """Update all effects by dt seconds."""
        for e in self._effects:
            e.elapsed += dt
        self._effects = [e for e in self._effects if e.elapsed < e.duration]

    def clear(self) -> None:
        """Remove all effects."""
        self._effects.clear()

    def is_empty(self) -> bool:
        return len(self._effects) == 0

    def get_total_offset(self) -> Tuple[float, float]:
        """Calculate combined offset from all active effects."""
        total_x = 0.0
        total_y = 0.0
        
        for effect in self._effects:
            ox, oy = effect.get_offset()
            total_x += ox
            total_y += oy
            
        return (total_x, total_y)

    def get_zoom_multiplier(self) -> float:
        """Get combined zoom multiplier from ZOOM_IMPACT effects."""
        zoom_mult = 1.0
        
        for effect in self._effects:
            if effect.effect_type == EffectType.ZOOM_IMPACT:
                progress = effect.apply_easing(effect.get_progress())
                if progress < 0.5:
                    zoom_mult *= effect.zoom_factor + (1.0 - effect.zoom_factor) * (progress * 2)
                else:
                    zoom_mult *= 1.0 - (1.0 - effect.zoom_factor) * ((progress - 0.5) * 2)
                    
        return max(0.5, min(2.0, zoom_mult))

    def get_time_scale(self) -> float:
        """Get time scale from SLOW_MOTION effects (lowest wins)."""
        time_scale = 1.0
        
        for effect in self._effects:
            if effect.effect_type == EffectType.SLOW_MOTION:
                time_scale = min(time_scale, effect.time_scale)
                
        return max(0.1, time_scale)

    def is_frozen(self) -> bool:
        """Check if any SCREEN_FREEZE effect is active."""
        return any(
            e.effect_type == EffectType.SCREEN_FREEZE 
            for e in self._effects
            if not e.is_complete()
        )

    def __len__(self) -> int:
        return len(self._effects)


# Convenience factory functions for common effects

def create_shake(intensity: float = 3.0, duration: float = 0.15, priority: int = 5) -> CameraEffect:
    """Create a screen shake effect."""
    return CameraEffect(
        effect_type=EffectType.SHAKE,
        intensity=intensity,
        duration=duration,
        easing="ease_out",
        priority=priority
    )


def create_zoom_impact(
    zoom_factor: float = 0.8,
    duration: float = 0.15,
    recover: float = 0.5,
    priority: int = 10
) -> CameraEffect:
    """Create a zoom impact effect (quick zoom out + slow recover)."""
    return CameraEffect(
        effect_type=EffectType.ZOOM_IMPACT,
        intensity=zoom_factor,
        duration=duration + recover,
        easing="ease_in_out",
        priority=priority,
        zoom_factor=zoom_factor,
        recover_duration=recover
    )


def create_slow_motion(
    time_scale: float = 0.3,
    duration: float = 1.0,
    priority: int = 15
) -> CameraEffect:
    """Create a slow motion effect."""
    return CameraEffect(
        effect_type=EffectType.SLOW_MOTION,
        intensity=time_scale,
        duration=duration,
        easing="ease_in_out",
        priority=priority,
        time_scale=time_scale
    )


def create_push_pull(
    distance: float = 30.0,
    duration: float = 0.4,
    priority: int = 8
) -> CameraEffect:
    """Create a push-pull camera effect."""
    return CameraEffect(
        effect_type=EffectType.PUSH_PULL,
        intensity=1.0,
        duration=duration,
        easing="ease_out",
        priority=priority,
        push_distance=distance
    )


def create_screen_freeze(duration: float = 0.3, priority: int = 20) -> CameraEffect:
    """Create a screen freeze effect."""
    return CameraEffect(
        effect_type=EffectType.SCREEN_FREEZE,
        intensity=1.0,
        duration=duration,
        easing="linear",
        priority=priority
    )
