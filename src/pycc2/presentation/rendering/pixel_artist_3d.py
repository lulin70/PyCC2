"""
CC2-style Orthographic Top-Down Pixel Art Generator (Facade)

This module serves as the public API facade for pixel art generation.
Heavy subsystems have been extracted to dedicated modules:
- Tank sprite generation -> tank_pixel_renderer.TankPixelRenderer
- Infantry sprite generation -> infantry_pixel_renderer.InfantryPixelRenderer
- Vehicle sprite generation -> vehicle_pixel_renderer.VehiclePixelRenderer
- Environment sprite generation -> environment_pixel_renderer.EnvironmentPixelRenderer

Remaining in this file:
- Delegation wrappers preserving backward-compatible PixelArtist3D API
- Module-level convenience functions
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Import domain value objects
from pycc2.domain.entities.unit import Faction
from pycc2.domain.value_objects.direction import Direction
from pycc2.presentation.rendering.environment_pixel_renderer import (
    EnvironmentPixelRenderer,
)
from pycc2.presentation.rendering.infantry_pixel_renderer import (
    InfantryAnimator as _InfantryAnimator,
)
from pycc2.presentation.rendering.infantry_pixel_renderer import (
    InfantryPixelRenderer,
)
from pycc2.presentation.rendering.pixel_artist_enums import (
    InfantryAnimState,
    InfantryType,
    TankType,
)
from pycc2.presentation.rendering.tank_pixel_renderer import TankPixelRenderer
from pycc2.presentation.rendering.vehicle_pixel_renderer import (
    VehiclePixelRenderer,
)

if TYPE_CHECKING:
    pass


class PixelArtist3D:
    """
    CC2-style orthographic top-down pixel art generator facade.

    This class delegates to specialized renderers while maintaining
    the original public API for backward compatibility.

    Extracted subsystems:
    - TankPixelRenderer: tanks, turrets, rotation cache, faction insignia
    - InfantryPixelRenderer: infantry sprites, animation, direction params
    - VehiclePixelRenderer: halftrack, jeep, AT gun, mortar team
    - EnvironmentPixelRenderer: trees, buildings

    Remaining (in this file): delegation wrappers only.
    """

    ISOMETRIC_ANGLE = 30
    PIXEL_SCALE = 1

    # ===== Rotation Pre-cache (delegates to TankPixelRenderer) =====
    _rotation_cache: dict[tuple, pygame.Surface] = {}
    _PRECACHE_ANGLES = [i * 15 for i in range(24)]

    # ------------------------------------------------------------------ #
    #  Rotation cache API — delegates to TankPixelRenderer
    # ------------------------------------------------------------------ #

    @classmethod
    def _get_rotated_surface(cls, base: pygame.Surface, angle: float) -> pygame.Surface:
        """Cached rotation operation. Delegates to TankPixelRenderer."""
        return TankPixelRenderer.get_rotated_surface(base, angle)

    @classmethod
    def precache_tank_rotations(cls):
        """Pre-cache common rotation angles for all tank types. Delegates to TankPixelRenderer."""
        return TankPixelRenderer.precache_tank_rotations()

    @classmethod
    def clear_rotation_cache(cls):
        """Clear rotation cache. Delegates to TankPixelRenderer."""
        return TankPixelRenderer.clear_rotation_cache()

    # ------------------------------------------------------------------ #
    #  Infantry API — delegates to InfantryPixelRenderer
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_infantry_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
        infantry_type: InfantryType | None = None,
    ):
        """Create an infantry sprite (24x24 px). Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer.create_infantry_sprite(
            direction,
            faction,
            state,
            frame,
            infantry_type,
        )

    @staticmethod
    def apply_wounded_overlay(surface, hp_ratio: float) -> pygame.Surface:
        """Apply wounded visual overlay based on HP ratio. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer.apply_wounded_overlay(surface, hp_ratio)

    @staticmethod
    def _get_direction_params(direction: Direction) -> dict:
        """Get direction-specific visual parameters. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._get_infantry_direction_params(direction)

    @staticmethod
    def _get_isometric_offset(direction: Direction) -> tuple:
        """Calculate pseudo-3D direction offset. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._get_isometric_offset(direction)

    @staticmethod
    def _get_weapon_position(direction, cx, cy) -> tuple:
        """Calculate weapon position by direction. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._get_weapon_position(direction, cx, cy)

    @staticmethod
    def _draw_infantry_weapon(
        surface,
        direction,
        infantry_type,
        cx,
        cy,
        weapon_color,
        weapon_metal,
        weapon_wood,
        equip_color,
        equip_dark,
    ):
        """Draw differentiated weapon by infantry type. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._draw_infantry_weapon(
            surface,
            direction,
            infantry_type,
            cx,
            cy,
            weapon_color,
            weapon_metal,
            weapon_wood,
            equip_color,
            equip_dark,
        )

    @staticmethod
    def _draw_infantry_prone_topdown(
        surface,
        direction,
        state,
        frame,
        palette,
        infantry_type,
        body_color,
        weapon_color,
        weapon_metal,
        boots_color,
    ):
        """Draw prone soldier top-down. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._draw_infantry_prone_topdown(
            surface,
            direction,
            state,
            frame,
            palette,
            infantry_type,
            body_color,
            weapon_color,
            weapon_metal,
            boots_color,
        )

    @staticmethod
    def _draw_infantry_death_topdown(
        surface,
        direction,
        frame,
        palette,
        infantry_type,
        body_color,
        helmet_color,
        weapon_color,
        boots_color,
    ):
        """Draw death animation top-down. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._draw_infantry_death_topdown(
            surface,
            direction,
            frame,
            palette,
            infantry_type,
            body_color,
            helmet_color,
            weapon_color,
            boots_color,
        )

    @staticmethod
    def _anim_state_to_params(anim_state: InfantryAnimState) -> tuple[str, int]:
        """Convert InfantryAnimState to (state, frame). Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer._anim_state_to_params(anim_state)

    @staticmethod
    def create_infantry_animation_sheet(
        faction: Faction,
        infantry_type: InfantryType | None = None,
    ):
        """Generate full animation frame sprite sheet. Delegates to InfantryPixelRenderer."""
        return InfantryPixelRenderer.create_infantry_animation_sheet(faction, infantry_type)

    # ------------------------------------------------------------------ #
    #  Tank API — delegates to TankPixelRenderer
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_tank_sprite(
        direction: Direction,
        faction: Faction,
        turret_direction: Direction | None = None,
        state: str = "idle",
        frame: int = 0,
        tank_type: TankType | None = None,
    ):
        """Create a tank sprite. Delegates to TankPixelRenderer."""
        return TankPixelRenderer.create_tank_sprite(
            direction,
            faction,
            turret_direction,
            state,
            frame,
            tank_type,
        )

    @staticmethod
    def create_turret_overlay(
        faction: Faction,
        turret_direction: Direction,
        tank_type: TankType | None = None,
    ):
        """Create standalone turret overlay sprite. Delegates to TankPixelRenderer."""
        return TankPixelRenderer.create_turret_overlay(faction, turret_direction, tank_type)

    @staticmethod
    def _draw_sherman_m4(surface, direction, turret_direction, state, frame, tp, cx, cy):
        """Draw Sherman M4. Delegates to TankPixelRenderer."""
        return TankPixelRenderer._draw_sherman_m4(
            surface, direction, turret_direction, state, frame, tp, cx, cy
        )

    @staticmethod
    def _draw_panther_ausfg(surface, direction, turret_direction, state, frame, tp, cx, cy):
        """Draw Panther Ausf.G. Delegates to TankPixelRenderer."""
        return TankPixelRenderer._draw_panther_ausfg(
            surface, direction, turret_direction, state, frame, tp, cx, cy
        )

    @staticmethod
    def _draw_tiger_i(surface, direction, turret_direction, state, frame, tp, cx, cy):
        """Draw Tiger I. Delegates to TankPixelRenderer."""
        return TankPixelRenderer._draw_tiger_i(
            surface, direction, turret_direction, state, frame, tp, cx, cy
        )

    @staticmethod
    def _draw_star(surface, cx, cy, radius, color):
        """Draw five-pointed star (Allied insignia). Delegates to TankPixelRenderer."""
        return TankPixelRenderer._draw_star(surface, cx, cy, radius, color)

    @staticmethod
    def _draw_iron_cross(surface, cx, cy, color):
        """Draw iron cross (Axis insignia). Delegates to TankPixelRenderer."""
        return TankPixelRenderer._draw_iron_cross(surface, cx, cy, color)

    # ================================================================== #
    #  VEHICLE SPRITES — delegates to VehiclePixelRenderer
    # ================================================================== #

    @staticmethod
    def create_halftrack_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """Create a half-track sprite. Delegates to VehiclePixelRenderer."""
        return VehiclePixelRenderer.create_halftrack_sprite(direction, faction, state, frame)

    @staticmethod
    def create_jeep_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """Create a jeep/scout car sprite. Delegates to VehiclePixelRenderer."""
        return VehiclePixelRenderer.create_jeep_sprite(direction, faction, state, frame)

    @staticmethod
    def create_at_gun_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """Create an anti-tank gun sprite. Delegates to VehiclePixelRenderer."""
        return VehiclePixelRenderer.create_at_gun_sprite(direction, faction, state, frame)

    @staticmethod
    def create_mortar_team_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """Create a mortar team sprite. Delegates to VehiclePixelRenderer."""
        return VehiclePixelRenderer.create_mortar_team_sprite(direction, faction, state, frame)

    # ================================================================== #
    #  ENVIRONMENT SPRITES — delegates to EnvironmentPixelRenderer
    # ================================================================== #

    @staticmethod
    def create_tree_sprite(variant: int = 0, size: str = "medium"):
        """Create a tree sprite. Delegates to EnvironmentPixelRenderer."""
        return EnvironmentPixelRenderer.create_tree_sprite(variant, size)

    @staticmethod
    def create_building_sprite(building_type: str = "house", variant: int = 0):
        """Create a building sprite. Delegates to EnvironmentPixelRenderer."""
        return EnvironmentPixelRenderer.create_building_sprite(building_type, variant)


# Re-export InfantryAnimator from its new home for backward compatibility
InfantryAnimator = _InfantryAnimator


# ====================================================================== #
#  Module-level convenience functions (unchanged API)
# ====================================================================== #


def create_cc2_infantry_sprite(
    direction: int,
    faction: str = "allies",
    state: str = "idle",
    frame: int = 0,
    infantry_type: str = "rifleman",
):
    """
    Convenience function: create a CC2-style infantry sprite.

    Args:
        direction: 0-7 (N, NE, E, SE, S, SW, W, NW)
        faction: "allies" or "axis"
        state: idle/walk/shoot/die/hit
        frame: Animation frame number
        infantry_type: rifleman/mg/at/officer/sniper/medic/engineer/scout

    Returns:
        pygame.Surface (24x24)
    """
    dir_enum = list(Direction)[direction % 8]
    faction_enum = Faction.ALLIES if faction == "allies" else Faction.AXIS
    type_map = {t.value: t for t in InfantryType}
    type_enum = type_map.get(infantry_type, InfantryType.RIFLEMAN)
    return InfantryPixelRenderer.create_infantry_sprite(
        dir_enum, faction_enum, state, frame, type_enum
    )


def create_cc2_tank_sprite(
    direction: int,
    faction: str = "allies",
    turret_direction: int | None = None,
    state: str = "idle",
    frame: int = 0,
):
    """
    Convenience function: create a CC2-style tank sprite.

    Args:
        direction: Hull facing 0-7
        faction: "allies" or "axis"
        turret_direction: Turret facing 0-7 (optional)
        state: idle/move/shoot
        frame: Animation frame number

    Returns:
        pygame.Surface (36x36)
    """
    dir_enum = list(Direction)[direction % 8]
    faction_enum = Faction.ALLIES if faction == "allies" else Faction.AXIS
    turret_enum = list(Direction)[turret_direction % 8] if turret_direction is not None else None
    return TankPixelRenderer.create_tank_sprite(dir_enum, faction_enum, turret_enum, state, frame)


if __name__ == "__main__":
    import pygame

    pygame.init()

    logger.info("CC2 45° Isometric Pixel Artist - Test Generation")
    logger.info("=" * 50)

    test_surface = pygame.Surface((400, 300), pygame.SRCALPHA)
    test_surface.fill((40, 80, 28))

    directions = list(Direction)
    for i, direction in enumerate(directions):
        sprite = PixelArtist3D.create_infantry_sprite(
            direction=direction,
            faction=Faction.ALLIES,
            state="idle",
            frame=0,
        )
        x = (i % 4) * 90 + 20
        y = (i // 4) * 100 + 20
        test_surface.blit(sprite, (x, y))

        font = pygame.font.Font(None, 16)
        text = font.render(direction.name[:2], True, (240, 220, 40))
        test_surface.blit(text, (x + 6, y + 26))

    tank_sprite = PixelArtist3D.create_tank_sprite(
        direction=Direction.SOUTH,
        faction=Faction.ALLIES,
        state="idle",
    )
    test_surface.blit(tank_sprite, (320, 200))

    tree_sprite = PixelArtist3D.create_tree_sprite(variant=0)
    test_surface.blit(tree_sprite, (350, 240))

    building_sprite = PixelArtist3D.create_building_sprite(building_type="house")
    test_surface.blit(building_sprite, (180, 200))

    import tempfile as _tf

    _preview_path = str(Path(_tf.gettempdir()) / "cc2_style_preview.png")
    pygame.image.save(test_surface, _preview_path)
    logger.info("Preview saved to %s", _preview_path)
    logger.info("   Generated %d infantry sprites + tank + tree + building", len(directions))

    pygame.quit()
