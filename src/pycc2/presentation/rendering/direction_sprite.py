"""Direction Sprite System - 8-directional sprite rotation for CC2 units."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class Direction(Enum):
    """8 compass directions for unit facing."""
    NORTH = 0
    NORTHEAST = 1
    EAST = 2
    SOUTHEAST = 3
    SOUTH = 4
    SOUTHWEST = 5
    WEST = 6
    NORTHWEST = 7

    @classmethod
    def from_angle(cls, angle: float) -> "Direction":
        """
        Convert angle in degrees to Direction.

        Args:
            angle: Angle in degrees (0=East, 90=South, 180=West, 270=North)

        Returns:
            Nearest Direction enum value
        """
        normalized = (angle + 360) % 360

        sector_size = 45.0 / 2.0
        adjusted = (normalized + sector_size) % 360
        index = int(adjusted / 45.0) % 8

        direction_map = {
            0: Direction.EAST,
            1: Direction.SOUTHEAST,
            2: Direction.SOUTH,
            3: Direction.SOUTHWEST,
            4: Direction.WEST,
            5: Direction.NORTHWEST,
            6: Direction.NORTH,
            7: Direction.NORTHEAST,
        }
        return direction_map[index]

    def to_angle(self) -> float:
        """Convert Direction to angle in degrees (CC2 convention: 0=East, 90=South)."""
        angles = {
            Direction.EAST: 0.0,
            Direction.SOUTHEAST: 45.0,
            Direction.SOUTH: 90.0,
            Direction.SOUTHWEST: 135.0,
            Direction.WEST: 180.0,
            Direction.NORTHWEST: 225.0,
            Direction.NORTH: 270.0,
            Direction.NORTHEAST: 315.0,
        }
        return angles[self]

    def to_unit_facing(self) -> float:
        """
        Convert to unit facing angle (CC2 convention).

        0=East, 90=South, 180=West, 270=North
        """
        return self.to_angle()


@dataclass(slots=True)
class SpriteFrame:
    """Single frame of a sprite animation."""
    surface: pygame.Surface
    direction: Direction
    frame_index: int = 0
    duration_ms: int = 100


@dataclass
class DirectionSpriteSet:
    """
    Complete set of sprites for all 8 directions.

    Structure:
    {
        Direction.NORTH: [frame0, frame1, ...],
        Direction.NORTHEAST: [frame0, frame1, ...],
        ...
    }
    """
    base_sprite_path: str = ""
    sprite_size: tuple[int, int] = (32, 32)
    directions: dict[Direction, list[pygame.Surface]] = field(default_factory=dict)
    is_loaded: bool = False

    def load_from_spritesheet(
        self,
        filepath: str,
        sprite_size: tuple[int, int] = (32, 32),
        directions_count: int = 8,
        frames_per_direction: int = 1,
    ) -> bool:
        """
        Load directional sprites from a spritesheet image.

        Expected layout:
        - Rows: Directions (N, NE, E, SE, S, SW, W, NW)
        - Columns: Animation frames per direction

        Args:
            filepath: Path to spritesheet PNG
            sprite_size: Size of each individual sprite (width, height)
            directions_count: Number of directions (default 8)
            frames_per_direction: Frames per direction (default 1)

        Returns:
            True if loaded successfully
        """
        try:
            sheet = pygame.image.load(filepath).convert_alpha()
            self.base_sprite_path = filepath
            self.sprite_size = sprite_size

            sheet_width, sheet_height = sheet.get_size()
            cols = sheet_width // sprite_size[0]
            rows = sheet_height // sprite_size[1]

            for dir_idx in range(min(directions_count, rows)):
                direction = list(Direction)[dir_idx % 8]
                frames = []

                for frame_idx in range(min(frames_per_direction, cols)):
                    x = frame_idx * sprite_size[0]
                    y = dir_idx * sprite_size[1]

                    sprite = pygame.Surface(sprite_size, pygame.SRCALPHA)
                    sprite.blit(
                        sheet,
                        (0, 0),
                        (x, y, sprite_size[0], sprite_size[1]),
                    )
                    frames.append(sprite)

                if frames:
                    self.directions[direction] = frames

            self.is_loaded = len(self.directions) > 0
            return self.is_loaded

        except Exception as e:
            print(f"[DirectionSprite] Error loading {filepath}: {e}")
            return False

    def generate_procedural_variants(
        self,
        base_surface: pygame.Surface,
        flip_horizontal: bool = True,
        rotate_90: bool = True,
    ) -> None:
        """
        Generate 8-direction variants from a single base sprite.

        Uses flipping and rotation when full spritesheet unavailable.
        Quality lower than true multi-direction art but functional.

        Args:
            base_surface: Base sprite facing EAST
            flip_horizontal: Generate W variants by flipping E
            rotate_90: Generate N/S by rotating (may look odd for asymmetric sprites)
        """
        self.sprite_size = base_surface.get_size()

        self.directions[Direction.EAST] = [base_surface]

        if flip_horizontal:
            west_sprite = pygame.transform.flip(base_surface, True, False)
            self.directions[Direction.WEST] = [west_sprite]

        if rotate_90:
            north_sprite = pygame.transform.rotate(base_surface, 90)
            south_sprite = pygame.transform.rotate(base_surface, 270)
            self.directions[Direction.NORTH] = [north_sprite]
            self.directions[Direction.SOUTH] = [south_sprite]

            ne_sprite = pygame.transform.rotate(base_surface, 45)
            se_sprite = pygame.transform.rotate(base_surface, 315)
            nw_sprite = pygame.transform.flip(ne_sprite, True, False)
            sw_sprite = pygame.transform.flip(se_sprite, True, False)

            self.directions[Direction.NORTHEAST] = [ne_sprite]
            self.directions[Direction.SOUTHEAST] = [se_sprite]
            self.directions[Direction.NORTHWEST] = [nw_sprite]
            self.directions[Direction.SOUTHWEST] = [sw_sprite]

        self.is_loaded = len(self.directions) == 8

    def get_sprite(
        self,
        direction: Direction,
        frame_index: int = 0,
    ) -> pygame.Surface | None:
        """
        Get sprite surface for specific direction and frame.

        Args:
            direction: Facing direction
            frame_index: Animation frame index

        Returns:
            Pygame Surface or None if not loaded
        """
        frames = self.directions.get(direction)
        if not frames:
            closest = self._find_closest_direction(direction)
            frames = self.directions.get(closest)
            if not frames:
                return None

        frame_index = frame_index % len(frames)
        return frames[frame_index]

    def _find_closest_direction(self, direction: Direction) -> Direction | None:
        """Find closest available direction if exact one missing."""
        if not self.directions:
            return None

        available = list(self.directions.keys())
        target_angle = direction.to_angle()

        closest = min(
            available,
            key=lambda d: min(
                abs(d.to_angle() - target_angle),
                abs(d.to_angle() - target_angle + 360),
                abs(d.to_angle() - target_angle - 360),
            ),
        )
        return closest


class DirectionSpriteManager:
    """
    Manages loading and caching of directional sprites for all unit types.

    Singleton-style manager accessible throughout the rendering pipeline.
    """

    _instance: "DirectionSpriteManager | None" = None
    _cache: dict[str, DirectionSpriteSet] = {}

    def __new__(cls) -> "DirectionSpriteManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "DirectionSpriteManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_unit_sprites(
        self,
        unit_type: str,
        faction: str,
        sprite_path: str | None = None,
    ) -> DirectionSpriteSet:
        """
        Load or retrieve cached sprites for a unit type.

        Args:
            unit_type: Type identifier (e.g., 'rifleman', 'tank')
            faction: 'allies' or 'axis'
            sprite_path: Optional explicit path to spritesheet

        Returns:
            DirectionSpriteSet with loaded sprites
        """
        cache_key = f"{faction}_{unit_type}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        sprite_set = DirectionSpriteSet()

        if sprite_path:
            sprite_set.load_from_spritesheet(sprite_path)
        else:
            default_path = (
                f"assets/sprites/units/{faction}/{unit_type}.png"
            )
            try:
                sprite_set.load_from_spritesheet(default_path)
            except Exception:
                pass

        if not sprite_set.is_loaded:
            self._generate_placeholder(sprite_set, unit_type, faction)

        self._cache[cache_key] = sprite_set
        return sprite_set

    def _generate_placeholder(
        self,
        sprite_set: DirectionSpriteSet,
        unit_type: str,
        faction: str,
    ) -> None:
        """Generate placeholder colored squares for missing sprites."""
        size = (32, 32)
        color = (0, 100, 200) if faction == "allies" else (200, 50, 50)

        base = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(base, color, base.get_rect(), border_radius=4)
        pygame.draw.rect(base, (255, 255, 255), base.get_rect(), width=2, border_radius=4)

        font = pygame.font.Font(None, 16)
        label = font.render(unit_type[:3].upper(), True, (255, 255, 255))
        label_rect = label.get_rect(center=(size[0] // 2, size[1] // 2))
        base.blit(label, label_rect)

        sprite_set.generate_procedural_variants(base)

    def get_sprite_for_unit(
        self,
        unit: "Unit",
        direction: Direction | None = None,
        frame_index: int = 0,
    ) -> pygame.Surface | None:
        """
        Get the appropriate sprite for a unit's current state.

        Args:
            unit: The game unit
            direction: Override direction (else use unit.facing)
            frame_index: Animation frame

        Returns:
            Pygame Surface or None
        """
        if direction is None:
            direction = Direction.from_angle(getattr(unit, 'facing', 0))

        unit_type = getattr(unit, 'unit_type', None)
        if unit_type is None:
            unit_type = type(unit).__name__.lower().replace('squad', '')

        faction_name = getattr(unit, 'faction', None)
        if faction_name is None:
            faction_name = "allies"
        else:
            faction_name = faction_name.name.lower() if hasattr(faction_name, 'name') else str(faction_name).lower()

        sprite_set = self.load_unit_sprites(
            unit_type=str(unit_type),
            faction=faction_name,
        )

        return sprite_set.get_sprite(direction, frame_index)

    def clear_cache(self) -> None:
        """Clear all cached sprite sets."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        return len(self._cache)
