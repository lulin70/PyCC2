from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.value_objects.vec2 import Vec2


@dataclass(slots=True)
class Camera:
    position: Vec2
    zoom: float = 1.0
    viewport_width: int = 1280
    viewport_height: int = 720

    MIN_ZOOM: float = 0.25
    MAX_ZOOM: float = 4.0

    def world_to_screen(self, world_pos: Vec2) -> tuple[float, float]:
        screen_x = (world_pos.x - self.position.x) * self.zoom + self.viewport_width / 2
        screen_y = (world_pos.y - self.position.y) * self.zoom + self.viewport_height / 2
        return (screen_x, screen_y)

    def screen_to_world(self, screen_pos: tuple[float, float]) -> Vec2:
        from pycc2.domain.value_objects.vec2 import Vec2

        world_x = (screen_pos[0] - self.viewport_width / 2) / self.zoom + self.position.x
        world_y = (screen_pos[1] - self.viewport_height / 2) / self.zoom + self.position.y
        return Vec2(world_x, world_y)

    @property
    def view_bounds(self) -> tuple[Vec2, Vec2]:
        from pycc2.domain.value_objects.vec2 import Vec2

        half_w = self.viewport_width / (2 * self.zoom)
        half_h = self.viewport_height / (2 * self.zoom)
        top_left = Vec2(self.position.x - half_w, self.position.y - half_h)
        bottom_right = Vec2(self.position.x + half_w, self.position.y + half_h)
        return (top_left, bottom_right)

    def move(self, dx: float, dy: float) -> None:
        from pycc2.domain.value_objects.vec2 import Vec2

        delta = Vec2(dx / self.zoom, dy / self.zoom)
        self.position = self.position + delta

    def set_position(self, pos: Vec2) -> None:
        self.position = pos

    def adjust_zoom(
        self,
        factor: float,
        anchor: tuple[float, float] | None = None,
    ) -> None:
        new_zoom = max(
            self.MIN_ZOOM,
            min(self.MAX_ZOOM, self.zoom * factor),
        )
        if anchor is not None and new_zoom != self.zoom:
            mouse_world = self.screen_to_world(anchor)
            center = (self.viewport_width / 2, self.viewport_height / 2)
            offset_to_anchor = (anchor[0] - center[0], anchor[1] - center[1])
            new_pos_x = mouse_world.x - offset_to_anchor[0] / new_zoom
            new_pos_y = mouse_world.y - offset_to_anchor[1] / new_zoom
            from pycc2.domain.value_objects.vec2 import Vec2

            self.position = Vec2(new_pos_x, new_pos_y)
        self.zoom = new_zoom

    def constrain_to_map(
        self,
        map_width_pixels: float,
        map_height_pixels: float,
    ) -> None:
        from pycc2.domain.value_objects.vec2 import Vec2

        # Calculate minimum zoom so the map fills the screen
        min_zoom_for_fill = max(
            self.viewport_width / map_width_pixels,
            self.viewport_height / map_height_pixels,
        )
        # Update MIN_ZOOM dynamically so user can't zoom out beyond map fill
        self.MIN_ZOOM = min_zoom_for_fill

        # Clamp current zoom
        if self.zoom < self.MIN_ZOOM:
            self.zoom = self.MIN_ZOOM

        view_w = self.viewport_width / self.zoom
        view_h = self.viewport_height / self.zoom

        # Clamp position so viewport stays within map bounds
        min_x = view_w / 2
        max_x = map_width_pixels - view_w / 2
        min_y = view_h / 2
        max_y = map_height_pixels - view_h / 2

        # If map is exactly viewport-sized, center it
        if max_x <= min_x:
            clamped_x = map_width_pixels / 2
        else:
            clamped_x = max(min_x, min(max_x, self.position.x))

        if max_y <= min_y:
            clamped_y = map_height_pixels / 2
        else:
            clamped_y = max(min_y, min(max_y, self.position.y))

        self.position = Vec2(clamped_x, clamped_y)

    def focus_on(self, target: Vec2, immediate: bool = True) -> None:
        if immediate:
            self.position = target

    def reset(self) -> None:
        from pycc2.domain.value_objects.vec2 import Vec2

        self.position = Vec2(0.0, 0.0)
        self.zoom = 1.0
