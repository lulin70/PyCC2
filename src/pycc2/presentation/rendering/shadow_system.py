"""
Global SE-Direction Shadow System for PyCC2

Renders consistent Southeast-pointing shadows for all game objects,
matching the authentic Close Combat 2 visual style where shadows
cast from every object (trees, units, vehicles, buildings) 
point toward the Southeast.

Shadow Parameters by Object Type:
- Infantry:    offset(+2,+1), 6×3px ellipse,  alpha=80
- Vehicle:     offset(+4,+2), hull_w×4px,      alpha=100
- Tree:        offset(+5,+3), canopy×0.7×0.4,  alpha=90
- Building:    offset(+6,+3), roof_w×0.9×6px,  alpha=70
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import pygame

logger = logging.getLogger(__name__)


class ShadowRenderer:
    """
    Renders consistent SE-direction shadows for all game objects.

    Light source direction: Northwest → shadows point Southeast.
    Uses semi-transparent ellipses with caching for performance.
    """

    # Light source direction: Northwest → shadows point Southeast
    SHADOW_OFFSET_X = 3   # pixels right per 24px unit
    SHADOW_OFFSET_Y = 2   # pixels down per 24px unit

    # Base shadow color (near-black with alpha) - DARKER for visibility
    DEFAULT_SHADOW_COLOR = (5, 5, 8)

    # Common shadow sizes to pre-render at init time
    _COMMON_SIZES = [
        (6, 3),      # Infantry
        (12, 4),     # Small vehicle
        (16, 5),     # Medium vehicle/tank
        (20, 6),     # Large vehicle
        (24, 8),     # Small building
        (32, 10),    # Medium building
        (40, 12),    # Large building
        (14, 6),     # Small tree
        (18, 8),     # Medium tree
        (22, 10),    # Large tree
    ]

    def __init__(self):
        """Initialize shadow renderer with cached shadow surfaces."""
        self._shadow_cache: dict[Tuple[int, int, int], pygame.Surface] = {}
        self._pre_render_common_shadows()
        logger.info("ShadowRenderer initialized with %d pre-cached shadows", len(self._shadow_cache))

    def _pre_render_common_shadows(self) -> None:
        """Pre-render common shadow sizes at init time for performance."""
        for width, height in self._COMMON_SIZES:
            for alpha in [55, 65, 70, 75, 110, 130, 140, 150]:  # Expanded for new alpha values
                self._get_or_create_shadow(width, height, alpha)

    def _get_or_create_shadow(self, width: int, height: int, alpha: int) -> pygame.Surface:
        """
        Get cached shadow surface or create new one.

        Args:
            width: Shadow ellipse width
            height: Shadow ellipse height
            alpha: Transparency level (0-255)

        Returns:
            Cached pygame.Surface with shadow ellipse
        """
        cache_key = (width, height, alpha)

        if cache_key not in self._shadow_cache:
            # Create new shadow surface with SRCALPHA for transparency
            shadow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            shadow_color = (*self.DEFAULT_SHADOW_COLOR, alpha)

            # Draw filled ellipse
            pygame.draw.ellipse(shadow_surf, shadow_color, (0, 0, width, height))

            self._shadow_cache[cache_key] = shadow_surf

        return self._shadow_cache[cache_key]

    def render_shadow(
        self,
        surface: pygame.Surface,
        obj_rect: Tuple[int, int, int, int],
        obj_height: int = 1,
        shadow_color: Optional[Tuple[int, int, int]] = None,
        is_hidden: bool = False
    ) -> None:
        """
        Render a SE-pointing shadow ellipse beneath an object.

        Args:
            surface: Target surface to draw on
            obj_rect: (x, y, width, height) of the object casting shadow
            obj_height: Height tier (1=infantry, 2=vehicle/tree, 3=building)
            shadow_color: Optional override color (RGB tuple)
            is_hidden: If True, reduce shadow alpha by 50% (sneaking units)
        """
        x, y, w, h = obj_rect

        # Calculate shadow parameters based on object type
        if obj_height == 1:
            # Infantry: small subtle shadow
            shadow_w, shadow_h = max(6, w // 2), 3
            offset_x, offset_y = 2, 1
            base_alpha = 130  # INCREASED from 80 for visibility
        elif obj_height == 2:
            # Vehicle/Tree: medium shadow
            shadow_w, shadow_h = max(12, int(w * 0.8)), max(4, h // 3)
            offset_x, offset_y = 4, 2
            base_alpha = 150 if obj_height == 2 else 140  # INCREASED from 100/90
        else:
            # Building: large subtle shadow
            shadow_w, shadow_h = max(24, int(w * 0.9)), 6
            offset_x, offset_y = 6, 3
            base_alpha = 110  # INCREASED from 70 for visibility

        # Reduce alpha for hidden/sneaking objects
        alpha = base_alpha // 2 if is_hidden else base_alpha

        # Get or create shadow surface
        shadow_surf = self._get_or_create_shadow(shadow_w, shadow_h, alpha)

        # Calculate shadow position (offset southeast from object base)
        shadow_x = x + offset_x
        shadow_y = y + h + offset_y - shadow_h // 2

        # Blit shadow to target surface
        surface.blit(shadow_surf, (shadow_x, shadow_y))

    def render_unit_shadow(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        unit_type: str = "infantry",
        is_hidden: bool = False
    ) -> None:
        """
        Render shadow for infantry/unit.

        Args:
            surface: Target surface
            x: Unit X position
            y: Unit Y position
            unit_type: Type of unit ("infantry", "officer", etc.)
            is_hidden: If unit is sneaking/hidden
        """
        # Infantry-sized shadow: 6×3 px ellipse, offset (+2, +1)
        shadow_w, shadow_h = 6, 3
        offset_x, offset_y = 2, 1
        alpha = 65 if is_hidden else 130  # INCREASED from 40/80

        shadow_surf = self._get_or_create_shadow(shadow_w, shadow_h, alpha)
        shadow_x = x + offset_x
        shadow_y = y + offset_y

        surface.blit(shadow_surf, (shadow_x, shadow_y))

        logger.debug("Rendered unit shadow at (%d, %d) [type=%s, hidden=%s]", 
                    shadow_x, shadow_y, unit_type, is_hidden)

    def render_vehicle_shadow(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        is_hidden: bool = False
    ) -> None:
        """
        Render shadow for tank/vehicle.

        Args:
            surface: Target surface
            x: Vehicle X position
            y: Vehicle Y position
            w: Vehicle width
            h: Vehicle height
            is_hidden: If vehicle is hidden
        """
        # Vehicle shadow: hull_w × 4 px ellipse, offset (+4, +2)
        shadow_w = max(12, int(w * 0.9))
        shadow_h = max(4, 4)
        offset_x, offset_y = 4, 2
        alpha = 75 if is_hidden else 150  # INCREASED from 50/100

        shadow_surf = self._get_or_create_shadow(shadow_w, shadow_h, alpha)
        shadow_x = x + offset_x
        shadow_y = y + h + offset_y - shadow_h // 2

        surface.blit(shadow_surf, (shadow_x, shadow_y))

        logger.debug("Rendered vehicle shadow at (%d, %d) [size=%dx%d]", 
                    shadow_x, shadow_y, shadow_w, shadow_h)

    def render_tree_shadow(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        tree_size: str = "medium",
        is_hidden: bool = False
    ) -> None:
        """
        Render shadow for tree.

        Args:
            surface: Target surface
            x: Tree X position (base)
            y: Tree Y position (base)
            tree_size: Size category ("small", "medium", "large")
            is_hidden: If tree is somehow hidden (rare)
        """
        # FIXED: Larger shadows with higher visibility
        # Tree shadow dimensions based on canopy size
        size_map = {
            "small": (18, 8),    # Increased from (14, 6)
            "medium": (24, 10),  # Increased from (18, 8)
            "large": (30, 12),   # Increased from (22, 10)
        }

        shadow_w, shadow_h = size_map.get(tree_size, (24, 10))
        offset_x, offset_y = 6, 4  # Slightly larger offset
        alpha = 100 if is_hidden else 180  # INCREASED alpha for visibility

        shadow_surf = self._get_or_create_shadow(shadow_w, shadow_h, alpha)
        shadow_x = x + offset_x
        shadow_y = y + offset_y

        surface.blit(shadow_surf, (shadow_x, shadow_y))

        logger.debug("Rendered tree shadow at (%d, %d) [size=%s]",
                    shadow_x, shadow_y, tree_size)

    def render_building_shadow(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        is_hidden: bool = False
    ) -> None:
        """
        Render shadow for building.

        Args:
            surface: Target surface
            x: Building X position
            y: Building Y position
            w: Building width
            h: Building height
            is_hidden: If building is hidden (very rare)
        """
        # FIXED: Larger offset to make shadows visible beyond building edges
        # Building shadow: roof_w × 0.9 × 8 px, offset (+8, +5)
        shadow_w = max(32, int(w * 0.95))  # Wider shadow
        shadow_h = 8  # Taller shadow for visibility
        offset_x, offset_y = 8, 5  # Larger SE offset
        alpha = 80 if is_hidden else 160  # INCREASED alpha for visibility

        shadow_surf = self._get_or_create_shadow(shadow_w, shadow_h, alpha)
        shadow_x = x + offset_x
        shadow_y = y + h + offset_y - 2  # Adjusted position

        surface.blit(shadow_surf, (shadow_x, shadow_y))

        logger.debug("Rendered building shadow at (%d, %d) [size=%dx%d]",
                    shadow_x, shadow_y, shadow_w, shadow_h)

    def clear_cache(self) -> None:
        """Clear all cached shadow surfaces."""
        cache_size = len(self._shadow_cache)
        self._shadow_cache.clear()
        logger.info("Shadow cache cleared (removed %d entries)", cache_size)

    def get_cache_stats(self) -> dict:
        """Return statistics about the shadow cache."""
        return {
            "cached_shadows": len(self._shadow_cache),
            "common_sizes_pre_rendered": len(self._COMMON_SIZES) * 4,  # 4 alpha levels
        }
