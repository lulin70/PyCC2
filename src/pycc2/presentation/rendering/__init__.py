"""
Rendering Subsystem [REFACTORED 2026-05]

Provides rendering abstraction and implementations for the game display.

REFACTORED MODULE STRUCTURE:
The monolithic enhanced_renderer.py has been split into specialized modules:
- enhanced_renderer.py: Main coordinator (EnhancedRenderer class)
- sprite_generator.py: Programmatic sprite generation (SpriteGenerator)
- particle_system.py: Particle effects (TopDownParticleSystem)
- lighting_system.py: Lighting config and effects (TopDownLightingConfig, LightingSystem)
- terrain_renderer.py: Terrain rendering (TerrainRenderer)
- unit_renderer.py: Unit rendering (UnitRenderer)
- decoration_renderer.py: Map decorations (DecorationRenderer)

All public APIs remain backward-compatible.
Import from this package or directly from submodules as needed.
"""

from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.enhanced_renderer import (
    EnhancedRenderer,
    TopDownLightingConfig,       # Re-exported from lighting_system
    SpriteGenerator,             # Re-exported from sprite_generator
    TopDownParticleSystem,        # Re-exported from particle_system
    PaletteGenerator,            # Color palette generation utility
    ProceduralTextureGenerator,  # Procedural texture creation
    TerrainTileCache,            # Terrain tile caching system
    CC2_TERRAIN_PALETTE,         # CC2 terrain color palette constants
    TERRAIN_PALETTE_MAP,         # Terrain ID to palette mapping
)
from pycc2.presentation.rendering.sprite_generator import SpriteGenerator as SG
from pycc2.presentation.rendering.particle_system import TopDownParticleSystem as PS
from pycc2.presentation.rendering.lighting_system import (
    TopDownLightingConfig as TLC,
    LightingSystem,
)
from pycc2.presentation.rendering.terrain_renderer import TerrainRenderer
from pycc2.presentation.rendering.unit_renderer import UnitRenderer
from pycc2.presentation.rendering.decoration_renderer import DecorationRenderer
from pycc2.presentation.rendering.hud import HUDManager
from pycc2.presentation.rendering.minimap import Minimap
from pycc2.presentation.rendering.renderer import IRenderer
from pycc2.presentation.rendering.visual_spec import VisualSpec

__all__ = [
    # Core renderer
    "EnhancedRenderer",
    "IRenderer",

    # Camera & utilities
    "Camera",
    "VisualSpec",

    # UI Components
    "HUDManager",
    "Minimap",

    # Refactored sub-modules (new architecture)
    "SpriteGenerator",
    "TopDownParticleSystem",
    "TopDownLightingConfig",
    "LightingSystem",
    "TerrainRenderer",
    "UnitRenderer",
    "DecorationRenderer",

    # Supporting classes (backward compatible)
    "PaletteGenerator",
    "ProceduralTextureGenerator",
    "TerrainTileCache",
    "CC2_TERRAIN_PALETTE",
    "TERRAIN_PALETTE_MAP",
]
