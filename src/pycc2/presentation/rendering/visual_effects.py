"""
Phase 4: 视觉效果升级 - 增强粒子系统、天气效果、屏幕后处理

REFACTORED: Classes have been split into dedicated modules for maintainability.
All public APIs remain backward-compatible — import from this module still works.

Module structure:
- weather_effects.py: EnhancedWeatherSystem, WeatherType, WeatherParticle
- post_processing.py: PostProcessingEffects
- cc2_combat_effects.py: EnhancedParticleSystem, SurrenderFlagEffect,
  CC2ExplosionEffect, CC2SmokeEffect, CC2HitSparkEffect, CC2MuzzleFlashEffect
"""

from __future__ import annotations

from pycc2.presentation.rendering.cc2_combat_effects import (
    CC2ExplosionEffect,
    CC2HitSparkEffect,
    CC2MuzzleFlashEffect,
    CC2SmokeEffect,
    EnhancedParticleSystem,
    SurrenderFlagEffect,
)
from pycc2.presentation.rendering.post_processing import (
    PostProcessingEffects,
)

# Re-export all public classes for backward compatibility
from pycc2.presentation.rendering.weather_effects import (
    EnhancedWeatherSystem,
    WeatherParticle,
    WeatherType,
)

__all__ = [
    # Weather
    "WeatherType",
    "WeatherParticle",
    "EnhancedWeatherSystem",
    # Post-processing
    "PostProcessingEffects",
    # Combat effects
    "EnhancedParticleSystem",
    "SurrenderFlagEffect",
    "CC2ExplosionEffect",
    "CC2SmokeEffect",
    "CC2HitSparkEffect",
    "CC2MuzzleFlashEffect",
]
