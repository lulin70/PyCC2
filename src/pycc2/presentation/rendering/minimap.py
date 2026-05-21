"""
Minimap Component

Renders a tactical minimap showing unit positions and terrain overview.
"""

from pygame import Rect, Surface, draw

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.presentation.rendering.display_config import DisplayConfig
from pycc2.presentation.rendering.visual_spec import VisualSpec


class Minimap:
    """Tactical minimap component."""

    def __init__(self, display_config: DisplayConfig | None = None, size: int | None = None):
        self._dc = display_config or DisplayConfig()
        self.size = size or int(160 * self._dc.ui_scale)
        self.spec = VisualSpec()
        self._surface: Surface | None = None
        self._units: list[Unit] = []
        self._game_map: GameMap | None = None
        self._render_x: int = 0
        self._render_y: int = 0

    def set_map(self, game_map: GameMap) -> None:
        """Set the game map for rendering."""
        self._game_map = game_map

    def update_units(self, units: list[Unit]) -> None:
        """Update unit positions for minimap display."""
        self._units = units

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
        draw.rect(
            self._surface, self.spec.minimap_border_color, Rect(0, 0, self.size, self.size), 1
        )
        surface.blit(self._surface, (x, y))

    def _draw_terrain(self) -> None:
        """Draw simplified terrain on minimap."""
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

    def _draw_units(self) -> None:
        """Draw unit dots on minimap."""
        if not self._game_map or not self._surface:
            return
        dot_radius = max(2, min(3, self.size // 50))

        for unit in self._units:
            norm_x = unit.position.tile_coord.x / self._game_map.width
            norm_y = unit.position.tile_coord.y / self._game_map.height
            dot_x = int(norm_x * self.size)
            dot_y = int(norm_y * self.size)

            if unit.faction == Faction.ALLIES:
                color = self.spec.allied_unit_color
            else:
                color = self.spec.axis_unit_color

            draw.circle(self._surface, color, (dot_x, dot_y), dot_radius)

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
