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
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
from pycc2.presentation.rendering.sprite_generator import SpriteGenerator as SpriteGenerator
from pycc2.presentation.rendering.particle_system import TopDownParticleSystem as TopDownParticleSystem
from pycc2.presentation.rendering.lighting_system import (
    TopDownLightingConfig as TopDownLightingConfig,
    LightingSystem,
)
from pycc2.presentation.rendering.palette_generator import PaletteGenerator as PaletteGenerator
from pycc2.presentation.rendering.procedural_texture_generator import ProceduralTextureGenerator as ProceduralTextureGenerator
from pycc2.presentation.rendering.terrain_tile_cache import (
    TerrainTileCache as TerrainTileCache,
    CC2_TERRAIN_PALETTE as CC2_TERRAIN_PALETTE,
    TERRAIN_PALETTE_MAP as TERRAIN_PALETTE_MAP,
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
