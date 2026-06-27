"""Spritesheet Parser - Advanced spritesheet analysis and frame extraction for CC2.

Supports multiple layout formats:
- Row-major: Directions in rows, frames in columns (default)
- Column-major: Directions in columns, frames in rows
- Grid: Custom NxM grid with direction mapping
- Auto-detect: Analyzes transparency to determine layout
"""

# PLANNED: Not yet wired into game loop — reserved for future feature

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

import numpy as np
import pygame

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.value_objects.direction import Direction
    from pycc2.presentation.rendering.direction_sprite import DirectionSpriteSet


class SpritesheetLayout(Enum):
    """Common spritesheet layout formats."""

    ROW_MAJOR = auto()  # 8 rows x N cols (directions x frames)
    COLUMN_MAJOR = auto()  # N rows x 8 cols (frames x directions)
    GRID_4X2 = auto()  # 4 rows x 2 cols for 8 directions
    GRID_2X4 = auto()  # 2 rows x 4 cols
    SINGLE_ROW = auto()  # 1 row x 8 cols
    AUTO_DETECT = auto()


@dataclass(slots=True)
class FrameInfo:
    """Metadata about a single extracted frame."""

    rect: pygame.Rect
    direction_index: int
    frame_index: int
    has_content: bool = True


@dataclass
class SpritesheetConfig:
    """Configuration for spritesheet parsing."""

    sprite_size: tuple[int, int] = (64, 64)
    layout: SpritesheetLayout = SpritesheetLayout.ROW_MAJOR
    directions_count: int = 8
    frames_per_direction: int = 1
    padding: tuple[int, int] = (0, 0)
    direction_order: list[int] = field(default_factory=lambda: list(range(8)))


class SpritesheetParser:
    """Advanced spritesheet parser with auto-detection capabilities.

    Features:
    - Automatic layout detection via transparency analysis
    - Support for irregular grids and padding
    - Content-aware frame extraction (skips empty frames)
    - Direction mapping customization
    - Performance-optimized batch extraction
    """

    def __init__(
        self,
        image_path: str | None = None,
        config: SpritesheetConfig | None = None,
    ):
        self.config = config or SpritesheetConfig()
        self._image: pygame.Surface | None = None
        self._image_array: np.ndarray | None = None
        self._frames: list[FrameInfo] = []
        self._is_loaded = False

        if image_path:
            self.load(image_path)

    def load(self, image_path: str) -> bool:
        """Load spritesheet from file path."""
        try:
            self._image = pygame.image.load(image_path).convert_alpha()
            self._image_array = pygame.surfarray.array_alpha(self._image)

            if self.config.layout == SpritesheetLayout.AUTO_DETECT:
                self._auto_detect_layout()

            self._extract_all_frames()
            self._is_loaded = len(self._frames) > 0

            logger.info("[SpritesheetParser] Loaded %s", image_path)
            logger.info("   Size: %s", self._image.get_size())
            logger.info("   Detected %d frames", len(self._frames))
            logger.info("   Layout: %s", self.config.layout.name)

            return self._is_loaded

        except (pygame.error, ValueError, OSError) as e:
            logger.error("[SpritesheetParser] Error loading %s: %s", image_path, e)
            return False

    def _auto_detect_layout(self) -> None:
        """Automatically detect spritesheet layout from image analysis."""
        if self._image_array is None:
            return

        height, width = self._image_array.shape

        # Find content boundaries
        non_empty_rows = np.where(self._image_array.max(axis=1) > 0)[0]
        non_empty_cols = np.where(self._image_array.max(axis=0) > 0)[0]

        if len(non_empty_rows) == 0 or len(non_empty_cols) == 0:
            self.config.layout = SpritesheetLayout.ROW_MAJOR
            return

        content_top = non_empty_rows[0]
        content_bottom = non_empty_rows[-1]
        content_left = non_empty_cols[0]
        content_right = non_empty_cols[-1]

        content_height = content_bottom - content_top + 1
        content_width = content_right - content_left + 1

        # Detect horizontal gaps (row separators)
        row_gaps = self._find_horizontal_gaps()
        col_gaps = self._find_vertical_gaps()

        # Heuristic: if we find ~7 horizontal gaps, it's likely row-major 8-direction
        if len(row_gaps) >= 6 and len(row_gaps) <= 9:
            self.config.layout = SpritesheetLayout.ROW_MAJOR
            # Estimate sprite size
            if len(row_gaps) > 0:
                avg_row_height = content_height // (len(row_gaps) + 1)
                self.config.sprite_size = (content_width, avg_row_height)

        elif len(col_gaps) >= 6 and len(col_gaps) <= 9:
            self.config.layout = SpritesheetLayout.COLUMN_MAJOR
            if len(col_gaps) > 0:
                avg_col_width = content_width // (len(col_gaps) + 1)
                self.config.sprite_size = (avg_col_width, content_height)

        else:
            # Default to row-major with estimated size
            # Try common ratios
            aspect_ratio = width / height

            if aspect_ratio > 2.0:  # Wide image - likely single row or column-major
                self.config.layout = SpritesheetLayout.SINGLE_ROW
                self.config.sprite_size = (width // 8, height)
            elif aspect_ratio < 0.5:  # Tall image - likely single column
                self.config.layout = SpritesheetLayout.ROW_MAJOR
                self.config.sprite_size = (width, height // 8)
            else:
                # Square-ish - could be grid
                self.config.layout = SpritesheetLayout.ROW_MAJOR
                self.config.sprite_size = (width // math.sqrt(8), height // math.sqrt(8))

    def _find_horizontal_gaps(self, min_gap_size: int = 5) -> list[int]:
        """Find y-coordinates of horizontal transparent gaps."""
        if self._image_array is None:
            return []

        gaps = []
        in_gap = False
        gap_start = 0

        for y in range(self._image_array.shape[0]):
            is_transparent = self._image_array[y].max() == 0

            if is_transparent and not in_gap:
                gap_start = y
                in_gap = True
            elif not is_transparent and in_gap:
                if y - gap_start >= min_gap_size:
                    gaps.append((gap_start + y) // 2)  # Center of gap
                in_gap = False

        return gaps

    def _find_vertical_gaps(self, min_gap_size: int = 5) -> list[int]:
        """Find x-coordinates of vertical transparent gaps."""
        if self._image_array is None:
            return []

        gaps = []
        in_gap = False
        gap_start = 0

        for x in range(self._image_array.shape[1]):
            is_transparent = self._image_array[:, x].max() == 0

            if is_transparent and not in_gap:
                gap_start = x
                in_gap = True
            elif not is_transparent and in_gap:
                if x - gap_start >= min_gap_size:
                    gaps.append((gap_start + x) // 2)
                in_gap = False

        return gaps

    def _extract_all_frames(self) -> None:
        """Extract all frames based on configured layout."""
        if self._image is None:
            return

        self._frames.clear()

        sw, sh = self.config.sprite_size
        pad_x, pad_y = self.config.padding

        if self.config.layout == SpritesheetLayout.ROW_MAJOR:
            self._extract_row_major(sw, sh, pad_x, pad_y)
        elif self.config.layout == SpritesheetLayout.COLUMN_MAJOR:
            self._extract_column_major(sw, sh, pad_x, pad_y)
        elif self.config.layout == SpritesheetLayout.SINGLE_ROW:
            self._extract_single_row(sw, sh, pad_x, pad_y)
        else:
            # Default to row-major
            self._extract_row_major(sw, sh, pad_x, pad_y)

    def _extract_row_major(self, sprite_w: int, sprite_h: int, pad_x: int, pad_y: int) -> None:
        """Extract frames in row-major order (rows=directions, cols=frames)."""
        if self._image is None:
            return
        sheet_w, sheet_h = self._image.get_size()

        max_dirs = min(self.config.directions_count, sheet_h // (sprite_h + pad_y))
        max_frames = sheet_w // (sprite_w + pad_x)

        for dir_idx in range(max_dirs):
            for frame_idx in range(min(self.config.frames_per_direction, max_frames)):
                x = frame_idx * (sprite_w + pad_x)
                y = dir_idx * (sprite_h + pad_y)

                rect = pygame.Rect(x, y, sprite_w, sprite_h)
                has_content = self._check_frame_content(rect)

                self._frames.append(
                    FrameInfo(
                        rect=rect,
                        direction_index=dir_idx,
                        frame_index=frame_idx,
                        has_content=has_content,
                    )
                )

    def _extract_column_major(self, sprite_w: int, sprite_h: int, pad_x: int, pad_y: int) -> None:
        """Extract frames in column-major order (cols=directions, rows=frames)."""
        if self._image is None:
            return
        sheet_w, sheet_h = self._image.get_size()

        max_dirs = min(self.config.directions_count, sheet_w // (sprite_w + pad_x))
        max_frames = sheet_h // (sprite_h + pad_y)

        for dir_idx in range(max_dirs):
            for frame_idx in range(min(self.config.frames_per_direction, max_frames)):
                x = dir_idx * (sprite_w + pad_x)
                y = frame_idx * (sprite_h + pad_y)

                rect = pygame.Rect(x, y, sprite_w, sprite_h)
                has_content = self._check_frame_content(rect)

                self._frames.append(
                    FrameInfo(
                        rect=rect,
                        direction_index=dir_idx,
                        frame_index=frame_idx,
                        has_content=has_content,
                    )
                )

    def _extract_single_row(self, sprite_w: int, sprite_h: int, pad_x: int, pad_y: int) -> None:
        """Extract frames from a single row layout."""
        if self._image is None:
            return
        sheet_w, sheet_h = self._image.get_size()

        max_frames = min(
            self.config.directions_count * self.config.frames_per_direction,
            sheet_w // (sprite_w + pad_x),
        )

        for i in range(max_frames):
            dir_idx = i // max(1, self.config.frames_per_direction)
            frame_idx = i % max(1, self.config.frames_per_direction)

            x = i * (sprite_w + pad_x)
            y = 0

            rect = pygame.Rect(x, y, sprite_w, sprite_h)
            has_content = self._check_frame_content(rect)

            self._frames.append(
                FrameInfo(
                    rect=rect,
                    direction_index=dir_idx,
                    frame_index=frame_idx,
                    has_content=has_content,
                )
            )

    def _check_frame_content(self, rect: pygame.Rect) -> bool:
        """Check if a frame region contains non-transparent pixels."""
        if self._image_array is None:
            return False

        x, y, w, h = rect

        # Bounds check
        if x < 0 or y < 0:
            return False
        if x + w > self._image_array.shape[1] or y + h > self._image_array.shape[0]:
            return False

        region = self._image_array[y : y + h, x : x + w]
        return region.max() > 0

    def get_frame(
        self,
        direction: Direction,
        frame_index: int = 0,
    ) -> pygame.Surface | None:
        """Get sprite surface for specific direction and frame.

        Args:
            direction: Facing direction (Direction enum)
            frame_index: Animation frame index (default 0)

        Returns:
            Pygame Surface or None if not found

        """
        if not self._is_loaded or self._image is None:
            return None

        dir_idx = direction.value if isinstance(direction, Enum) else direction

        # Find matching frame
        for frame_info in self._frames:
            if (
                frame_info.direction_index == dir_idx
                and frame_info.frame_index == frame_index
                and frame_info.has_content
            ):
                return self._extract_surface(frame_info.rect)

        # Fallback: find closest direction
        return self._get_closest_frame(dir_idx, frame_index)

    def _get_closest_frame(self, target_dir: int, frame_index: int) -> pygame.Surface | None:
        """Find closest available frame if exact match missing."""
        available_dirs = set(f.direction_index for f in self._frames if f.has_content)

        if not available_dirs:
            return None

        # Find closest direction (circular distance)
        best_dir = min(
            available_dirs,
            key=lambda d: min(
                abs(d - target_dir),
                abs(d - target_dir + 8),
                abs(d - target_dir - 8),
            ),
        )

        for frame_info in self._frames:
            if (
                frame_info.direction_index == best_dir
                and frame_info.frame_index == frame_index
                and frame_info.has_content
            ):
                return self._extract_surface(frame_info.rect)

        return None

    def _extract_surface(self, rect: pygame.Rect) -> pygame.Surface:
        """Extract a surface region from the spritesheet."""
        if self._image is None:
            raise RuntimeError("No image loaded")

        sprite = pygame.Surface(rect.size, pygame.SRCALPHA)
        sprite.blit(self._image, (0, 0), rect)
        return sprite

    def get_all_directions(
        self,
        frame_index: int = 0,
    ) -> dict[int, pygame.Surface]:
        """Get all direction frames at specified frame index.

        Args:
            frame_index: Animation frame index

        Returns:
            Dict mapping direction index to Surface

        """
        result = {}

        for frame_info in self._frames:
            if (
                frame_info.frame_index == frame_index
                and frame_info.has_content
                and frame_info.direction_index not in result
            ):
                result[frame_info.direction_index] = self._extract_surface(frame_info.rect)

        return result

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def directions_found(self) -> int:
        return len(set(f.direction_index for f in self._frames if f.has_content))

    @property
    def sprite_size(self) -> tuple[int, int]:
        return self.config.sprite_size

    def get_analysis_report(self) -> str:
        """Generate human-readable analysis report."""
        if not self._is_loaded or self._image is None:
            return "No spritesheet loaded"

        lines = [
            "Spritesheet Analysis Report",
            "=" * 50,
            f"Image Size: {self._image.get_size()}",
            f"Detected Layout: {self.config.layout.name}",
            f"Sprite Size: {self.config.sprite_size}",
            "",
            f"Total Frames Extracted: {len(self._frames)}",
            f"Directions Found: {self.directions_found}",
            f"Frames per Direction: ~{len(self._frames) // max(1, self.directions_found)}",
            "",
            f"Content Frames: {sum(1 for f in self._frames if f.has_content)}",
            f"Empty Frames: {sum(1 for f in self._frames if not f.has_content)}",
        ]

        return "\n".join(lines)


def create_direction_sprite_set_from_spritesheet(
    image_path: str,
    sprite_size: tuple[int, int] | None = None,
    layout: SpritesheetLayout = SpritesheetLayout.AUTO_DETECT,
) -> DirectionSpriteSet:
    """Convenience function to create a DirectionSpriteSet from a spritesheet.

    Args:
        image_path: Path to spritesheet PNG
        sprite_size: Optional override for sprite dimensions
        layout: Layout format (auto-detect by default)

    Returns:
        Populated DirectionSpriteSet ready for use

    """
    from pycc2.domain.value_objects.direction import Direction
    from pycc2.presentation.rendering.direction_sprite import DirectionSpriteSet

    config = SpritesheetConfig()

    if sprite_size:
        config.sprite_size = sprite_size
    config.layout = layout

    parser = SpritesheetParser(image_path, config)

    if not parser.is_loaded:
        return DirectionSpriteSet()

    sprite_set = DirectionSpriteSet()
    sprite_set.base_sprite_path = image_path
    sprite_set.sprite_size = parser.sprite_size

    # Map frames to DirectionSpriteSet format
    for dir_idx, surface in parser.get_all_directions().items():
        direction = list(Direction)[dir_idx % 8]
        sprite_set.directions[direction] = [surface]

    sprite_set.is_loaded = len(sprite_set.directions) > 0

    return sprite_set
