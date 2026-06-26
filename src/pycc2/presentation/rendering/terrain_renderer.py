"""Terrain Renderer compatibility shim for CC2-Style Maps.

The original monolithic TerrainRenderer has been split:
- terrain_rendering_system.py : core terrain tile drawing and caching
- terrain_edge_helpers (inline in terrain_rendering_system.py) :
  transitions, edge smoothing, border debug overlays

This module now exposes the module-level enhanced-terrain feature flag
and a thin TerrainRenderer shim so existing imports and shutdown cache
invalidation continue to work.
"""

from __future__ import annotations

from pycc2.presentation.rendering.render_context import RenderContext

# Enhanced rendering feature flag
_ENHANCED_TERRAIN_AVAILABLE = False
try:
    from config.rendering_features import is_enhanced_terrain_enabled

    _ENHANCED_TERRAIN_AVAILABLE = True
    if is_enhanced_terrain_enabled():
        from pycc2.presentation.rendering.enhanced_terrain_generator import (  # noqa: F401
            generate_enhanced_dirt,
            generate_enhanced_grass,
        )
except ImportError:
    _ENHANCED_TERRAIN_AVAILABLE = False


class TerrainRenderer:
    """Backward-compatible terrain renderer shim.

    The real terrain rendering implementation lives in
    TerrainRenderingSystem. This class is kept only for imports and
    the cache attributes accessed by EnhancedRenderer.shutdown().
    """

    def __init__(self, ctx: RenderContext):
        self._ctx = ctx
        self._transition_cache: dict = {}
        self._edge_smooth_cache: dict = {}
