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
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pygame
from pygame import Surface

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.interfaces.display_config import DisplayConfig
    from pycc2.presentation.rendering.svg_sprite_loader import SVGSpriteLoader


# V-09 (Wave D4): Threshold for slow prewarm warning (ms).
# If prewarming exceeds this, we log a warning suggesting lazy-load fallback.
PREWARM_SLOW_THRESHOLD_MS: int = 500


@dataclass(frozen=True, slots=True)
class PrewarmResult:
    """V-09 (Wave D4): Result of SpriteCacheManager.prewarm().

    Captures timing and counts for the prewarm operation, useful for
    startup diagnostics and CI regressions detection.

    Attributes:
        elapsed_ms: Wall-clock time spent in prewarm, in milliseconds.
        sprite_count: Number of unit sprites in cache after prewarm.
        terrain_count: Number of terrain tiles in cache after prewarm.
        already_prewarmed: True if prewarm was a no-op (cache already populated).
    """

    elapsed_ms: float
    sprite_count: int
    terrain_count: int
    already_prewarmed: bool


class SpriteCacheManager:
    """Manages sprite generation, caching, and lookup.

    Responsibilities:
    - Pre-generate unit sprites for all faction × type × direction combos
    - Pre-generate terrain tiles
    - Provide sprite lookup with fallback chain
    - Integrate with AssetLoader for PNG sprite loading
    """

    TILE_SIZE: int = 48
    SPRITE_SIZE: int = 48  # Match TILE_SIZE for larger, clearer units

    def __init__(self, display_config: DisplayConfig | None = None):
        """Initialize the SpriteCacheManager."""
        from pycc2.domain.interfaces.display_config import DisplayConfig as DC
        from pycc2.presentation.rendering.asset_loader import AssetLoader
        from pycc2.presentation.rendering.cc2_sprite_loader import CC2SpriteLoader
        from pycc2.presentation.rendering.tile_cache import TileCache

        self._display_config: DisplayConfig = display_config or DC()
        self._sprite_cache: dict[str, Surface] = {}
        self._terrain_cache: dict[int, Surface] = {}
        self._tile_cache: TileCache = TileCache()
        self._asset_loader: AssetLoader = AssetLoader()

        # V-09 (Wave D4): Track prewarm state for idempotent prewarm() calls
        self._prewarmed: bool = False
        self._last_prewarm_result: PrewarmResult | None = None

        # CC2 Original Sprite Loader (NEW: 2026-06-16)
        assets_root = Path(__file__).parent.parent.parent.parent.parent / "assets"
        self._cc2_loader: CC2SpriteLoader = CC2SpriteLoader(assets_root)
        self._use_cc2_sprites: bool = self._cc2_loader.is_available()

        if self._use_cc2_sprites:
            logger.info("✅ CC2 original sprites detected - high quality mode enabled")
        else:
            logger.info("ℹ️ CC2 sprites not found - using procedural generation")

        # PixVoxel Sprite Loader (P0: 2026-07-10) — highest priority unit sprites
        from pycc2.presentation.rendering.pixvoxel_loader import PixVoxelLoader

        self._pixvoxel_loader: PixVoxelLoader = PixVoxelLoader(assets_dir=assets_root)
        self._use_pixvoxel_sprites: bool = self._pixvoxel_loader.is_available

        if self._use_pixvoxel_sprites:
            logger.info("✅ PixVoxel sprites detected - CC0 pixel art mode enabled")
        else:
            logger.info("ℹ️ PixVoxel sprites not found - falling back to SVG/procedural")

        # SVG Sprite Loader (was highest priority, now second after PixVoxel)
        from pycc2.presentation.rendering.svg_sprite_loader import SVGSpriteLoader

        self._svg_loader: SVGSpriteLoader | None = SVGSpriteLoader()
        self._use_svg_sprites: bool = self._svg_loader.is_available

        if self._use_svg_sprites:
            logger.info("✅ SVG unit sprites detected - vector art mode enabled")
            # Pre-cache all SVG sprites
            self._svg_cache = self._svg_loader.load_all(
                target_size=(self.SPRITE_SIZE, self.SPRITE_SIZE)
            )
            logger.info(
                "✅ Pre-cached %d SVG sprites for instant lookup",
                len(self._svg_cache),
            )
        else:
            self._svg_loader = None
            self._svg_cache = {}
            logger.info("ℹ️ SVG sprites not found - falling back to PNG/procedural")

        # V-09 (Wave D4): Trigger prewarm via public API for timing visibility.
        # Previously __init__ called _generate_all_sprites() + _generate_terrain_tiles()
        # directly with no timing. Now prewarm() wraps both with logger.info + threshold.
        self.prewarm()

    # ====== Public API ======

    def prewarm(
        self,
        slow_threshold_ms: int = PREWARM_SLOW_THRESHOLD_MS,
    ) -> PrewarmResult:
        """Preload all unit sprites and terrain tiles (V-09 Wave D4).

        Idempotent: if already prewarmed, returns the cached result without
        re-generating sprites. This is safe to call multiple times.

        Logs ``logger.info`` with elapsed time and sprite counts. If
        prewarming exceeds ``slow_threshold_ms``, also logs a warning
        suggesting lazy-load fallback (per Wave B-rev UX P1).

        Args:
            slow_threshold_ms: Threshold in milliseconds above which a slow
                prewarm warning is logged. Defaults to PREWARM_SLOW_THRESHOLD_MS (500ms).

        Returns:
            PrewarmResult dataclass with elapsed_ms, sprite_count, terrain_count,
            and already_prewarmed flag.
        """
        if self._prewarmed and self._last_prewarm_result is not None:
            # Idempotent: return cached result without re-running generation
            return self._last_prewarm_result

        start = time.perf_counter()
        self._generate_all_sprites()
        self._generate_terrain_tiles()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        sprite_count = len(self._sprite_cache)
        terrain_count = len(self._terrain_cache)

        logger.info(
            "SpriteCache prewarm completed: %.1fms (%d sprites, %d terrain tiles)",
            elapsed_ms,
            sprite_count,
            terrain_count,
        )

        if elapsed_ms > slow_threshold_ms:
            logger.warning(
                "SpriteCache prewarm exceeded %dms threshold (%.1fms); "
                "consider lazy-load fallback",
                slow_threshold_ms,
                elapsed_ms,
            )

        result = PrewarmResult(
            elapsed_ms=elapsed_ms,
            sprite_count=sprite_count,
            terrain_count=terrain_count,
            already_prewarmed=False,
        )
        self._prewarmed = True
        self._last_prewarm_result = result
        return result

    @property
    def last_prewarm_result(self) -> PrewarmResult | None:
        """V-09 (Wave D4): Return the last prewarm result, or None if not prewarmed."""
        return self._last_prewarm_result

    def get_unit_sprite(
        self,
        faction: str,
        unit_type: str,
        direction: int,
        sprite_size: int | None = None,
    ) -> Surface | None:
        """Look up a cached unit sprite with fallback chain.

        Falls back to create_unit_sprite() for SVG/procedural generation on cache miss.
        """
        # Normalize enum values to lowercase strings for cache key matching
        faction_str = faction.name.lower() if hasattr(faction, "name") else str(faction).lower()
        unit_type_str = unit_type.name if hasattr(unit_type, "name") else str(unit_type)

        sz = sprite_size or self.SPRITE_SIZE
        base_key = f"{faction_str}_{unit_type_str}_d{direction}"
        cached = (
            self._sprite_cache.get(base_key)
            or self._sprite_cache.get(f"{base_key}_{sz}")
            or self._sprite_cache.get(f"{faction_str}_{unit_type_str}_d0")
            or self._sprite_cache.get(f"{faction_str}_{unit_type_str}_d0_{sz}")
        )
        if cached is not None:
            return cached

        # Cache miss — generate via SVG loader or procedural (P0 fix: 2026-06-19)
        generated = self.create_unit_sprite(faction_str, unit_type_str, direction, sprite_size=sz)
        if generated is not None:
            self._sprite_cache[base_key] = generated
        return generated

    def create_unit_sprite(
        self,
        faction: str,
        unit_type: str,
        direction: int,
        turret_direction: int | None = None,
        state: str = "idle",
        sprite_size: int | None = None,
    ) -> Surface:
        """Create a unit sprite — priority: PixVoxel > SVG > CC2Original > AssetLoader > PixelArtist3D > legacy."""
        # 0. Try PixVoxel sprites (HIGHEST PRIORITY — P0: 2026-07-10)
        if self._use_pixvoxel_sprites:
            pv_sprite = self._try_pixvoxel_sprite(faction, unit_type, direction, state)
            if pv_sprite is not None:
                if sprite_size is not None and sprite_size != self.SPRITE_SIZE:
                    from pygame import transform as _tf

                    return _tf.scale(pv_sprite, (sprite_size, sprite_size))
                return pv_sprite

        # 1. Try SVG sprites
        if self._use_svg_sprites:
            svg_sprite = self._try_svg_sprite(faction, unit_type, direction, state)
            if svg_sprite is not None:
                # Scale SVG to requested size if needed
                if sprite_size is not None and sprite_size != self.SPRITE_SIZE:
                    from pygame import transform as _tf

                    return _tf.scale(svg_sprite, (sprite_size, sprite_size))
                return svg_sprite

        # 2. Try CC2 Original sprites
        if self._use_cc2_sprites:
            direction_map = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            dir_str = direction_map[direction % 8]
            cc2_sprite = self._cc2_loader.load_sprite(
                unit_type=unit_type.lower(), direction=dir_str, animation=state, frame=0
            )
            if cc2_sprite is not None:
                logger.info(f"[SPRITE] ✅✅ CC2 Original: {unit_type}_d{direction}")
                return cc2_sprite

        # 2. Try loading from assets
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
                    direction=dir_enum,
                    faction=fac_enum,
                    turret_direction=turret_enum,
                    state="idle",
                    frame=0,
                )
            elif unit_type in ("HALFTRACK",):
                cc2_sprite = PixelArtist3D.create_halftrack_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state="idle",
                    frame=0,
                )
            elif unit_type in ("JEEP", "SCOUT_CAR"):
                cc2_sprite = PixelArtist3D.create_jeep_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state="idle",
                    frame=0,
                )
            elif unit_type in ("AT_GUN_TEAM",):
                cc2_sprite = PixelArtist3D.create_at_gun_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state="idle",
                    frame=0,
                )
            elif unit_type in ("MORTAR_TEAM",):
                cc2_sprite = PixelArtist3D.create_mortar_team_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state="idle",
                    frame=0,
                )
            else:
                cc2_sprite = PixelArtist3D.create_infantry_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state=state,
                    frame=0,
                )

            if cc2_sprite is not None:
                logger.info(
                    f"[SPRITE] ✅ Generated CC2 pixel art: {faction}_{unit_type}_d{direction}"
                )
                return cc2_sprite

        except (pygame.error, ValueError, TypeError, ImportError) as e:
            logger.warning("[SPRITE] ❌ CC2 generation failed: %s, using legacy fallback", e)

        # Fallback: legacy procedural generator
        from pycc2.presentation.rendering.pixel_artist import create_unit_sprite

        logger.info(
            f"[SPRITE] ⚠️  Fallback to legacy procedural: {faction}_{unit_type}_d{direction}"
        )
        canvas = create_unit_sprite(
            faction=faction,
            unit_type=unit_type,
            direction=direction,
            size=self.SPRITE_SIZE,
            state=state,
        )
        return canvas.to_surface()

    # ====== PixVoxel sprite resolution (P0: 2026-07-10) ======

    def _try_pixvoxel_sprite(
        self,
        faction: str,
        unit_type: str,
        direction: int,
        state: str = "idle",
    ) -> Surface | None:
        """Try to load a PixVoxel CC0 sprite (highest priority when available).

        PixVoxel sprites are hand-drawn pixel art with 4 directions (N/E/S/W).
        Diagonal directions (NE/SE/SW/NW) are approximated to the nearest cardinal.
        Only idle/firing/hit/death animations are supported; other states fall through.
        """
        if state not in ("idle", "fire", "firing", "hit", "death"):
            return None

        faction_lower = faction.name.lower() if hasattr(faction, "name") else str(faction).lower()
        unit_type_str = unit_type.name if hasattr(unit_type, "name") else str(unit_type)

        sprite = self._pixvoxel_loader.load_sprite(
            unit_type=unit_type_str,
            faction=faction_lower,
            direction=direction,
            animation=state,
            frame=0,
            size=self.SPRITE_SIZE,
            use_ortho=True,
        )
        if sprite is not None:
            logger.debug(
                f"[SPRITE] ✅ PixVoxel: {faction_lower}_{unit_type_str}_d{direction}_{state}"
            )
        return sprite

    # ====== SVG sprite resolution (P0: 2026-06-19) ======

    # Map internal unit_type names to SVG posture names
    _SVG_POSTURE_MAP: dict[str, str] = {
        "INFANTRY_SQUAD": "standing",
        "RIFLE_SQUAD": "standing",
        "MACHINE_GUN_SQUAD": "standing",  # Default standing; use "mg_deployed" when deployed
        "MG_TEAM": "standing",
        "COMMANDER": "standing",
        "OFFICER": "standing",
        "SNIPER_TEAM": "prone",
        "MEDIC_TEAM": "kneeling",
        "AT_GUN_TEAM": "kneeling",
        "MORTAR_TEAM": "kneeling",
        "ENGINEER_SQUAD": "kneeling",
    }

    def _try_svg_sprite(
        self,
        faction: str,
        unit_type: str,
        direction: int,
        state: str = "idle",
        animation_frame: int | None = None,
    ) -> Surface | None:
        """Try to load an SVG sprite, with direction rotation and animation frames.

        Maps unit_type → SVG posture, looks up pre-cached base sprite,
        then rotates to face the requested direction.

        Animation support (P2):
            - Prone posture uses 4-frame cycle (f0→f1→f2→f3→f0...)
            - animation_frame 0-3 selects specific frame
            - If None, uses base prone sprite (no animation)
        """
        # Normalize faction
        faction_lower = faction.name.lower() if hasattr(faction, "name") else str(faction).lower()
        if faction_lower not in ("allies", "axis"):
            # Polish units use allies-style sprites
            if faction_lower in ("polish", "american", "british"):
                faction_lower = "allies"
            else:
                faction_lower = "axis"

        # Map unit type to posture
        unit_str = unit_type.name if hasattr(unit_type, "name") else str(unit_type)
        posture = self._SVG_POSTURE_MAP.get(unit_str, "standing")

        # Special case: MG units in deployed state
        if "mg" in unit_str.lower() and state == "deployed":
            posture = "mg_deployed"

        # Special case: prone/crawl states with animation frame support
        if state in ("prone", "crawl", "crawling"):
            posture = "prone"
            # P2: Use animation frame for prone crawling cycle
            if animation_frame is not None and 0 <= animation_frame <= 3:
                cache_key = f"{faction_lower}_{posture}_f{animation_frame}"
                base_sprite = self._svg_cache.get(cache_key)
                if base_sprite is not None:
                    return self._rotate_for_direction(base_sprite, direction)
                # Fall through to base prone if specific frame missing

        # Build cache key
        cache_key = f"{faction_lower}_{posture}"

        # Check pre-cached sprites
        base_sprite = self._svg_cache.get(cache_key)
        if base_sprite is None:
            return None

        return self._rotate_for_direction(base_sprite, direction)

    @staticmethod
    def _rotate_for_direction(base_sprite: Surface, direction: int) -> Surface:
        """Rotate sprite to face given direction.

        Direction mapping: 0=North(0°), 1=NE(45°), ..., 7=NW(315°)
        """
        if direction != 0:
            return pygame.transform.rotate(base_sprite, direction * 45)
        return base_sprite

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
                        faction,
                        unit_type_name,
                        0,
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
