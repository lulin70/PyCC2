"""
Minimap Component

Renders a tactical minimap showing unit positions and terrain overview.
"""

from pygame import Rect, Surface, draw
import pygame

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.presentation.rendering.display_config import DisplayConfig
from pycc2.presentation.rendering.visual_spec import VisualSpec


class Minimap:
    """Tactical minimap component with enhanced terrain and unit visualization."""

    def __init__(self, display_config: DisplayConfig | None = None, size: int | None = None):
        self._dc = display_config or DisplayConfig()
        self.size = size or int(160 * self._dc.ui_scale)
        self.spec = VisualSpec()
        self._surface: Surface | None = None
        self._units: list[Unit] = []
        self._game_map: GameMap | None = None
        self._render_x: int = 0
        self._render_y: int = 0
        self._is_isometric: bool = False
        self._selected_unit_id: str | None = None
        self._camera_viewport: tuple[float, float, float, float] | None = None  # (x, y, w, h) in world coords

    def set_map(self, game_map: GameMap) -> None:
        """Set the game map for rendering."""
        self._game_map = game_map

    def set_projection_mode(self, is_isometric: bool) -> None:
        """Set the minimap projection mode."""
        self._is_isometric = is_isometric

    def update_units(self, units: list[Unit]) -> None:
        """Update unit positions for minimap display."""
        self._units = units

    def set_selected_unit(self, unit_id: str | None) -> None:
        """Set the currently selected unit ID for highlight rendering."""
        self._selected_unit_id = unit_id

    def set_camera_viewport(self, viewport: tuple[float, float, float, float] | None) -> None:
        """Set camera viewport rectangle in world coordinates (x, y, width, height)."""
        self._camera_viewport = viewport

    def render(self, surface: Surface, x: int, y: int) -> None:
        """Render minimap at screen position (x, y)."""
        self._render_x = x
        self._render_y = y

        if not self._surface or self._surface.get_size() != (self.size, self.size):
            self._surface = Surface((self.size, self.size))

        self._surface.fill(self.spec.minimap_background_color)

        if self._game_map:
            self._draw_terrain()

        self._draw_units()
        self._draw_camera_viewport()
        draw.rect(
            self._surface, self.spec.minimap_border_color, Rect(0, 0, self.size, self.size), 1
        )
        surface.blit(self._surface, (x, y))

    def _draw_terrain(self) -> None:
        """Draw simplified terrain on minimap."""
        if not self._game_map or not self._surface:
            return

        if self._is_isometric:
            self._draw_terrain_isometric()
        else:
            self._draw_terrain_orthographic()

    def _draw_terrain_orthographic(self) -> None:
        """Draw simplified terrain on minimap (orthographic/square tiles)."""
        if not self._game_map or not self._surface:
            return
        map_width = self._game_map.width
        map_height = self._game_map.height
        tile_w = self.size / map_width
        tile_h = self.size / map_height

        for y in range(map_height):
            for x in range(map_width):
                terrain = self._game_map.get_terrain(TileCoord(x, y))
                color = self.spec.get_terrain_color(terrain)
                rect = Rect(int(x * tile_w), int(y * tile_h), int(tile_w) + 1, int(tile_h) + 1)
                draw.rect(self._surface, color, rect)

    def _draw_terrain_isometric(self) -> None:
        """Draw simplified terrain on minimap (isometric/diamond tiles)."""
        if not self._game_map or not self._surface:
            return
        from pycc2.presentation.rendering.isometric_transform import TILE_W, TILE_H

        map_width = self._game_map.width
        map_height = self._game_map.height

        # Scale factor: fit the isometric map into the minimap size
        # Isometric map bounding box: width = (w+h)*TILE_W/2, height = (w+h)*TILE_H/2
        iso_total_w = (map_width + map_height) * TILE_W / 2
        iso_total_h = (map_width + map_height) * TILE_H / 2
        scale = min(self.size / iso_total_w, self.size / iso_total_h) if iso_total_w > 0 and iso_total_h > 0 else 1.0

        # Offset to center the isometric map in the minimap
        offset_x = (self.size - iso_total_w * scale) / 2
        offset_y = (self.size - iso_total_h * scale) / 2

        for y in range(map_height):
            for x in range(map_width):
                terrain = self._game_map.get_terrain(TileCoord(x, y))
                color = self.spec.get_terrain_color(terrain)

                # Isometric center position
                cx = ((x - y) * TILE_W / 2 + iso_total_w / 2) * scale + offset_x
                cy = ((x + y) * TILE_H / 2) * scale + offset_y

                # Small diamond
                half_w = TILE_W / 2 * scale
                half_h = TILE_H / 2 * scale
                points = [
                    (int(cx), int(cy - half_h)),  # top
                    (int(cx + half_w), int(cy)),   # right
                    (int(cx), int(cy + half_h)),   # bottom
                    (int(cx - half_w), int(cy)),   # left
                ]
                draw.polygon(self._surface, color, points)

    def _draw_units(self) -> None:
        """Draw unit dots on minimap with selection highlight."""
        if not self._game_map or not self._surface:
            return
        dot_radius = max(2, min(3, self.size // 50))

        for unit in self._units:
            norm_x = unit.position.tile_coord.x / max(1, self._game_map.width)
            norm_y = unit.position.tile_coord.y / max(1, self._game_map.height)
            dot_x = int(norm_x * self.size)
            dot_y = int(norm_y * self.size)

            if unit.faction == Faction.ALLIES:
                color = self.spec.allied_unit_color
            else:
                color = self.spec.axis_unit_color

            # Draw unit dot
            draw.circle(self._surface, color, (dot_x, dot_y), dot_radius)

            # R9: Draw unit facing direction indicator
            facing = getattr(unit, 'facing', 0.0)
            if facing != 0.0 or True:  # Always draw direction
                import math
                facing_rad = math.radians(getattr(unit, 'facing', 0.0))
                dir_len = dot_radius + 3
                end_x = int(dot_x + math.cos(facing_rad) * dir_len)
                end_y = int(dot_y + math.sin(facing_rad) * dir_len)
                draw.line(self._surface, color, (dot_x, dot_y), (end_x, end_y), 1)

            # Draw selection highlight ring for selected unit
            if self._selected_unit_id and unit.unit_id == self._selected_unit_id:
                highlight_radius = dot_radius + 2
                draw.circle(self._surface, self.spec.selection_color, (dot_x, dot_y), highlight_radius, 1)

    def _draw_camera_viewport(self) -> None:
        """Draw camera viewport rectangle on minimap."""
        if not self._game_map or not self._surface or not self._camera_viewport:
            return

        vp_x, vp_y, vp_w, vp_h = self._camera_viewport
        map_width = self._game_map.width * 32  # Assuming 32px tile size
        map_height = self._game_map.height * 32

        # Convert world coordinates to minimap coordinates
        mini_x = int((vp_x / max(1, map_width)) * self.size)
        mini_y = int((vp_y / max(1, map_height)) * self.size)
        mini_w = int((vp_w / max(1, map_width)) * self.size)
        mini_h = int((vp_h / max(1, map_height)) * self.size)

        # Draw semi-transparent viewport rectangle
        viewport_color = (255, 255, 255, 100)
        viewport_surface = Surface((mini_w, mini_h), pygame.SRCALPHA)
        viewport_surface.fill(viewport_color)
        self._surface.blit(viewport_surface, (mini_x, mini_y), special_flags=pygame.BLEND_RGBA_ADD)

        # Draw viewport border
        draw.rect(self._surface, (255, 255, 255), Rect(mini_x, mini_y, mini_w, mini_h), 1)

    def contains_point(self, screen_pos: tuple[int, int]) -> bool:
        """Check if a screen position is within the minimap area."""
        return (
            self._render_x <= screen_pos[0] < self._render_x + self.size
            and self._render_y <= screen_pos[1] < self._render_y + self.size
        )

    def handle_click(self, screen_pos: tuple[int, int], camera: object) -> bool:
        """Handle a click on the minimap.

        Converts screen position to minimap position, then to world position,
        and centers the camera on that world position.

        Returns True if the click was handled (was within minimap).
        """
        if not self._game_map or not self.contains_point(screen_pos):
            return False

        # Convert screen position to minimap-local position
        mini_x = screen_pos[0] - self._render_x
        mini_y = screen_pos[1] - self._render_y

        # Convert minimap position to world position (in pixels)
        map_width = self._game_map.width
        map_height = self._game_map.height
        world_x = (mini_x / self.size) * map_width * 32  # 32 = tile size
        world_y = (mini_y / self.size) * map_height * 32

        # Center camera on the world position
        from pycc2.domain.value_objects.vec2 import Vec2
        camera.focus_on(Vec2(world_x, world_y))
        return True

    def world_to_minimap(
        self, world_x: float, world_y: float, map_width: int, map_height: int
    ) -> tuple:
        """Convert world coordinates to minimap coordinates."""
        mini_x = int((world_x / map_width) * self.size)
        mini_y = int((world_y / map_height) * self.size)
        return (mini_x, mini_y)

    def cleanup(self) -> None:
        """Clean up resources."""
        self._surface = None
