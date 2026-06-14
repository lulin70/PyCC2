"""Sprite Cache Manager — manages sprite generation and caching.

Extracted from SpriteRenderer to isolate sprite lifecycle concerns:
- Unit sprite generation (procedural + asset loading)
- Terrain tile generation
- Sprite cache lookup and fallback
- AssetLoader integration

Created: Refactoring — SpriteRenderer responsibility separation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame
from pygame import Surface, transform

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.interfaces.display_config import DisplayConfig


class SpriteCacheManager:
    """Manages sprite generation, caching, and lookup.

    Responsibilities:
    - Pre-generate unit sprites for all faction × type × direction combos
    - Pre-generate terrain tiles
    - Provide sprite lookup with fallback chain
    - Integrate with AssetLoader for PNG sprite loading
    """

    TILE_SIZE: int = 48
    SPRITE_SIZE: int = 32

    def __init__(self, display_config: DisplayConfig | None = None):
        from pycc2.domain.interfaces.display_config import DisplayConfig as DC
        from pycc2.presentation.rendering.asset_loader import AssetLoader
        from pycc2.presentation.rendering.tile_cache import TileCache

        self._display_config: DisplayConfig = display_config or DC()
        self._sprite_cache: dict[str, Surface] = {}
        self._terrain_cache: dict[int, Surface] = {}
        self._tile_cache: TileCache = TileCache()
        self._asset_loader: AssetLoader = AssetLoader()

        self._generate_all_sprites()
        self._generate_terrain_tiles()

    # ====== Public API ======

    def get_unit_sprite(
        self,
        faction: str,
        unit_type: str,
        direction: int,
        sprite_size: int | None = None,
    ) -> Surface | None:
        """Look up a cached unit sprite with fallback chain.

        Returns None if no sprite found in cache.
        """
        sz = sprite_size or self.SPRITE_SIZE
        base_key = f"{faction}_{unit_type}_d{direction}"
        return (
            self._sprite_cache.get(base_key)
            or self._sprite_cache.get(f"{base_key}_{sz}")
            or self._sprite_cache.get(f"{faction}_{unit_type}_d0")
            or self._sprite_cache.get(f"{faction}_{unit_type}_d0_{sz}")
            or None
        )

    def create_unit_sprite(
        self,
        faction: str,
        unit_type: str,
        direction: int,
        turret_direction: int | None = None,
        state: str = "idle",
    ) -> Surface:
        """Create a unit sprite — priority: AssetLoader > PixelArtist3D > legacy procedural."""
        # Try loading from assets
        loaded_sprite = self._asset_loader.load_unit_sprite(
            faction=faction,
            unit_type=unit_type,
            direction=direction,
            size=self.SPRITE_SIZE,
        )
        if loaded_sprite is not None:
            logger.info(f"[SPRITE] ✅ Loaded PNG: {faction}_{unit_type}_d{direction}")
            return loaded_sprite

        # Try CC2 pixel art generator
        try:
            from pycc2.domain.entities.unit import Faction
            from pycc2.domain.value_objects.direction import Direction
            from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D

            dir_enum = list(Direction)[direction] if direction < 8 else Direction.SOUTH
            _FACTION_MAP = {
                "allies": Faction.ALLIES,
                "american": Faction.AMERICAN,
                "british": Faction.BRITISH,
                "polish": Faction.POLISH,
                "axis": Faction.AXIS,
                "german": Faction.GERMAN,
            }
            fac_enum = _FACTION_MAP.get(faction, Faction.ALLIES)

            if unit_type in ("TANK",):
                turret_enum = None
                if turret_direction is not None:
                    turret_enum = list(Direction)[turret_direction % 8]
                cc2_sprite = PixelArtist3D.create_tank_sprite(
                    direction=dir_enum, faction=fac_enum,
                    turret_direction=turret_enum, state="idle", frame=0,
                )
            elif unit_type in ("HALFTRACK",):
                cc2_sprite = PixelArtist3D.create_halftrack_sprite(
                    direction=dir_enum, faction=fac_enum, state="idle", frame=0,
                )
            elif unit_type in ("JEEP", "SCOUT_CAR"):
                cc2_sprite = PixelArtist3D.create_jeep_sprite(
                    direction=dir_enum, faction=fac_enum, state="idle", frame=0,
                )
            elif unit_type in ("AT_GUN_TEAM",):
                cc2_sprite = PixelArtist3D.create_at_gun_sprite(
                    direction=dir_enum, faction=fac_enum, state="idle", frame=0,
                )
            elif unit_type in ("MORTAR_TEAM",):
                cc2_sprite = PixelArtist3D.create_mortar_team_sprite(
                    direction=dir_enum, faction=fac_enum, state="idle", frame=0,
                )
            else:
                cc2_sprite = PixelArtist3D.create_infantry_sprite(
                    direction=dir_enum, faction=fac_enum, state=state, frame=0,
                )

            logger.info(f"[SPRITE] ✅ Generated CC2 pixel art: {faction}_{unit_type}_d{direction}")
            return cc2_sprite

        except Exception as e:
            logger.warning(f"[SPRITE] ❌ CC2 generation failed: {e}, using legacy fallback")

        # Fallback: legacy procedural generator
        from pycc2.presentation.rendering.pixel_artist import create_unit_sprite

        logger.info(f"[SPRITE] ⚠️  Fallback to legacy procedural: {faction}_{unit_type}_d{direction}")
        canvas = create_unit_sprite(
            faction=faction, unit_type=unit_type,
            direction=direction, size=self.SPRITE_SIZE, state=state,
        )
        return canvas.to_surface()

    def get_terrain_tile(self, tile_id: int, size: int) -> Surface | None:
        """Get a scaled terrain tile from the tile cache."""
        return self._tile_cache.get_tile(tile_id, size)

    @property
    def sprite_cache(self) -> dict[str, Surface]:
        """Direct access to sprite cache (for initialize PNG overlay)."""
        return self._sprite_cache

    @property
    def terrain_cache(self) -> dict[int, Surface]:
        """Direct access to terrain cache."""
        return self._terrain_cache

    @property
    def tile_cache(self):
        """Direct access to tile cache."""
        return self._tile_cache

    @property
    def asset_loader(self):
        """Direct access to asset loader."""
        return self._asset_loader

    def initialize_png_sprites(self) -> None:
        """Copy AssetLoader PNG sprites into sprite cache, overriding procedural ones."""
        if hasattr(self._asset_loader, "_sprite_cache"):
            png_count = 0
            for key, sprite_surface in self._asset_loader._sprite_cache.items():
                self._sprite_cache[key] = sprite_surface
                png_count += 1
            logger.debug("Copied %d PNG sprites from AssetLoader cache", png_count)
        else:
            logger.warning("AssetLoader has no _sprite_cache, using procedural sprites")

    def clear(self) -> None:
        """Clear all caches."""
        self._sprite_cache.clear()
        self._terrain_cache.clear()
        self._tile_cache.invalidate()

    # ====== Private: sprite generation ======

    def _generate_all_sprites(self) -> None:
        """Pre-generate all unit type sprites (8 directions × 3 factions)."""
        for faction in ["allies", "axis", "polish"]:
            for unit_type_name in [
                "INFANTRY_SQUAD",
                "MACHINE_GUN_SQUAD",
                "COMMANDER",
                "TANK",
                "HALFTRACK",
                "JEEP",
                "SCOUT_CAR",
                "SNIPER_TEAM",
                "MEDIC_TEAM",
                "AT_GUN_TEAM",
                "MORTAR_TEAM",
            ]:
                for direction in range(8):
                    key = f"{faction}_{unit_type_name}_d{direction}"
                    sprite = self.create_unit_sprite(faction, unit_type_name, direction)
                    self._sprite_cache[key] = sprite

                # Generate default direction (d0=North) fallback
                default_key = f"{faction}_{unit_type_name}_d0"
                if default_key not in self._sprite_cache:
                    self._sprite_cache[default_key] = self.create_unit_sprite(
                        faction, unit_type_name, 0,
                    )

    def _generate_terrain_tiles(self) -> None:
        """Generate terrain tiles — priority: assets > procedural."""
        from pycc2.presentation.rendering.pixel_artist import create_terrain_tile

        for tid in range(22):
            loaded_tile = self._asset_loader.load_terrain_tile(tid, size=self.TILE_SIZE)
            if loaded_tile is not None:
                self._terrain_cache[tid] = loaded_tile
            else:
                canvas = create_terrain_tile(tid, size=self.TILE_SIZE)
                self._terrain_cache[tid] = canvas.to_surface()
