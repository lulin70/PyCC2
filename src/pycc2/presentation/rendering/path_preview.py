"""Path Preview System - Show predicted movement path with danger assessment."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.systems.los_system import LOSSystem
    from pycc2.presentation.rendering.camera import Camera


class PathDangerLevel(Enum):
    """Danger level for path segments."""

    SAFE = auto()  # Green - no enemy LOS
    WARNING = auto()  # Yellow - partial exposure
    DANGER = auto()  # Red - in enemy LOS


@dataclass
class PathSegment:
    """A segment of the path with danger assessment."""

    start: tuple[int, int]
    end: tuple[int, int]
    danger: PathDangerLevel = PathDangerLevel.SAFE
    estimated_time: float = 0.0  # seconds to traverse


@dataclass
class PreviewPath:
    """Complete path preview data."""

    segments: list[PathSegment] = field(default_factory=list)
    total_distance: int = 0
    total_time: float = 0.0
    is_valid: bool = True


@dataclass
class PathPreview:
    """Move command path preview system.

    Features:
    - A* path calculation with visualization
    - Danger assessment (enemy LOS detection)
    - Color-coded path rendering (green=safe, red=dangerous)
    - Time estimation display

    CC2 Behavior:
    - Shows dashed line for planned movement route
    - Red segments indicate exposure to enemy fire
    - Green segments are safe from observation
    - Each waypoint shows estimated arrival time
    """

    SHOW_DELAY: float = 0.3  # seconds before showing preview

    def __init__(
        self,
        pathfinder,
        los_system: LOSSystem | None = None,
    ):
        """Initialize the PathPreview."""
        self.pathfinder = pathfinder
        self.los_system = los_system
        self._current_path: PreviewPath | None = None
        self._show_timer: float = 0.0
        self._visible: bool = False
        self._last_start: tuple[int, int] | None = None
        self._last_end: tuple[int, int] | None = None

    def calculate_path(
        self,
        unit: Unit,
        target_pos: tuple[int, int],
        game_map: GameMap,
        enemy_units: list[Unit] | None = None,
    ) -> PreviewPath:
        """Calculate path from unit position to target.

        Args:
            unit: The moving unit
            target_pos: Target tile coordinates (x, y)
            game_map: Game map for pathfinding
            enemy_units: List of enemy units for danger assessment

        Returns:
            PreviewPath with segments and danger levels

        """
        from pycc2.domain.value_objects.tile_coord import TileCoord

        start = TileCoord(
            int(unit.position_component.x),
            int(unit.position_component.y),
        )
        goal = TileCoord(target_pos[0], target_pos[1])

        raw_path = self.pathfinder.find_path(start, goal, game_map)

        if not raw_path:
            return PreviewPath(is_valid=False, segments=[], total_distance=0)

        if len(raw_path) == 1:
            return PreviewPath(is_valid=True, segments=[], total_distance=0)

        segments: list[PathSegment] = []

        for i in range(len(raw_path) - 1):
            seg_start = (raw_path[i].x, raw_path[i].y)
            seg_end = (raw_path[i + 1].x, raw_path[i + 1].y)

            danger = self._assess_segment_danger(seg_end, enemy_units, game_map)

            speed = getattr(unit, "movement_speed", 3.0)  # tiles per second
            dist = math.sqrt((seg_end[0] - seg_start[0]) ** 2 + (seg_end[1] - seg_start[1]) ** 2)
            time_est = dist / speed if speed > 0 else 1.0

            segments.append(
                PathSegment(
                    start=seg_start,
                    end=seg_end,
                    danger=danger,
                    estimated_time=time_est,
                )
            )

        total_dist = len(raw_path) - 1
        total_time = sum(seg.estimated_time for seg in segments)

        return PreviewPath(
            segments=segments,
            total_distance=total_dist,
            total_time=total_time,
            is_valid=True,
        )

    def _assess_segment_danger(
        self,
        position: tuple[int, int],
        enemy_units: list[Unit] | None,
        game_map: GameMap,
    ) -> PathDangerLevel:
        """Assess if a path segment is in enemy LOS."""
        if not enemy_units or not self.los_system:
            return PathDangerLevel.SAFE

        from pycc2.domain.value_objects.tile_coord import TileCoord

        pos = TileCoord(position[0], position[1])

        danger_count = 0
        for enemy in enemy_units:
            can_see, _ = self.los_system.check_los(enemy.position.tile_coord, pos)
            if can_see:
                danger_count += 1

        if danger_count == 0:
            return PathDangerLevel.SAFE
        elif danger_count <= 2:
            return PathDangerLevel.WARNING
        else:
            return PathDangerLevel.DANGER

    def update_show_timer(self, dt: float) -> None:
        """Update visibility timer."""
        if not self._visible:
            self._show_timer += dt
            if self._show_timer >= self.SHOW_DELAY:
                self._visible = True

    def reset_preview(self) -> None:
        """Reset preview state."""
        self._current_path = None
        self._show_timer = 0.0
        self._visible = False
        self._last_start = None
        self._last_end = None

    def set_current_path(self, path: PreviewPath) -> None:
        """Set the current preview path."""
        self._current_path = path
        self._visible = True
        self._show_timer = 0.0

    @property
    def is_visible(self) -> bool:
        """Get the is visible."""
        return self._visible and self._current_path is not None

    @property
    def current_path(self) -> PreviewPath | None:
        """Get the current path."""
        return self._current_path

    def render(
        self,
        surface,
        camera: Camera,
        path: PreviewPath | None = None,
    ) -> None:
        """Render path preview on surface.

        Draws dashed lines with color coding:
        - Green (#00FF00): Safe segments
        - Yellow (#FFFF00): Warning segments
        - Red (#FF0000): Dangerous segments

        Also shows estimated time at waypoints.
        """
        if not path or (hasattr(path, "is_visible") and not path.is_visible):
            return

        render_path = path or self._current_path
        if not render_path or not render_path.segments:
            return

        color_map = {
            PathDangerLevel.SAFE: (0, 255, 0, 180),  # Green
            PathDangerLevel.WARNING: (255, 255, 0, 180),  # Yellow
            PathDangerLevel.DANGER: (255, 0, 0, 180),  # Red
        }

        try:
            import pygame

            for i, segment in enumerate(render_path.segments):
                color = color_map.get(segment.danger, (0, 255, 0, 180))

                start_screen = camera.world_to_screen(_vec2(segment.start))
                end_screen = camera.world_to_screen(_vec2(segment.end))

                self._draw_dashed_line(
                    surface,
                    start_screen,
                    end_screen,
                    color,
                    dash_length=10,
                    gap_length=5,
                )

                if i % 3 == 0:  # Show time every 3rd segment
                    time_text = f"{segment.estimated_time:.1f}s"
                    font = pygame.font.SysFont("arial", 12)
                    text_surf = font.render(time_text, True, (255, 255, 255))
                    surface.blit(text_surf, (end_screen[0] + 5, end_screen[1] - 5))

        except (pygame.error, ValueError, TypeError) as e:
            logging.debug("Path preview rendering failed: %s", e)

    @staticmethod
    def _draw_dashed_line(
        surface,
        start: tuple[float, float],
        end: tuple[float, float],
        color: tuple[int, ...],
        dash_length: int = 10,
        gap_length: int = 5,
    ) -> None:
        """Draw a dashed line between two points."""
        try:
            import math

            import pygame

            dx = end[0] - start[0]
            dy = end[1] - start[1]
            distance = math.sqrt(dx * dx + dy * dy)

            if distance == 0:
                return

            dashes = int(distance / (dash_length + gap_length))

            for i in range(dashes):
                start_frac = i * (dash_length + gap_length) / distance
                end_frac = min((i * (dash_length + gap_length) + dash_length) / distance, 1.0)

                x1 = start[0] + dx * start_frac
                y1 = start[1] + dy * start_frac
                x2 = start[0] + dx * end_frac
                y2 = start[1] + dy * end_frac

                pygame.draw.line(surface, color[:3], (x1, y1), (x2, y2), 2)
        except (pygame.error, ValueError, TypeError) as e:
            logging.debug("Dashed line draw failed: %s", e)

    def estimate_total_time(self, path: PreviewPath | None = None) -> float:
        """Estimate total movement time for path."""
        p = path or self._current_path
        if not p:
            return 0.0
        return p.total_time


def _vec2(pos: tuple[int, int]):
    """Helper to create Vec2 from tuple."""
    from pycc2.domain.value_objects.vec2 import Vec2

    return Vec2(float(pos[0]), float(pos[1]))
