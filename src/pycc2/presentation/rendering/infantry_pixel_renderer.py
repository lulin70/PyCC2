"""Infantry Pixel Renderer facade.

Provides backward-compatible ``InfantryPixelRenderer`` and ``InfantryAnimator``
classes that delegate to submodule-level functions split out during Phase 2 P0-1
(2026-07-04):

  - ``infantry_sprite_generator``: create_infantry_sprite / apply_wounded_overlay /
    create_infantry_animation_sheet + direction params + anim state mapping
  - ``infantry_weapon_drawing``: _draw_infantry_weapon + _get_weapon_position
  - ``infantry_pose_drawing``: _draw_infantry_prone_topdown + _draw_infantry_death_topdown
  - ``infantry_animator``: InfantryAnimator class

Public API is preserved: ``InfantryPixelRenderer.create_infantry_sprite(...)``,
``InfantryPixelRenderer.apply_wounded_overlay(...)``,
``InfantryPixelRenderer.create_infantry_animation_sheet(...)``, and
``from pycc2.presentation.rendering.infantry_pixel_renderer import InfantryAnimator``
all continue to work unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycc2.domain.entities.unit import Faction
from pycc2.domain.value_objects.direction import Direction
from pycc2.presentation.rendering.infantry_animator import InfantryAnimator
from pycc2.presentation.rendering.infantry_pose_drawing import (
    _draw_infantry_death_topdown,
    _draw_infantry_prone_topdown,
)
from pycc2.presentation.rendering.infantry_sprite_generator import (
    _anim_state_to_params,
    _get_infantry_direction_params,
    _get_isometric_offset,
    apply_wounded_overlay,
    create_infantry_animation_sheet,
    create_infantry_sprite,
)
from pycc2.presentation.rendering.infantry_weapon_drawing import (
    _draw_infantry_weapon,
    _get_weapon_position,
)
from pycc2.presentation.rendering.pixel_artist_enums import InfantryAnimState, InfantryType

if TYPE_CHECKING:
    import pygame

__all__ = ["InfantryPixelRenderer", "InfantryAnimator"]


class InfantryPixelRenderer:
    """Infantry sprite renderer facade — delegates to submodule-level functions.

    All 10 @staticmethod entries preserve original signatures and forward
    to standalone functions in infantry_sprite_generator / infantry_weapon_drawing
    / infantry_pose_drawing. InfantryAnimator is re-exported from
    infantry_animator for backward compatibility.
    """

    ISOMETRIC_ANGLE = 30
    PIXEL_SCALE = 1

    # ------------------------------------------------------------------ #
    #  Public infantry sprite API
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_infantry_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
        infantry_type: InfantryType | None = None,
    ):
        return create_infantry_sprite(
            direction=direction,
            faction=faction,
            state=state,
            frame=frame,
            infantry_type=infantry_type,
        )

    @staticmethod
    def apply_wounded_overlay(surface, hp_ratio: float) -> pygame.Surface:
        return apply_wounded_overlay(surface, hp_ratio)

    # ------------------------------------------------------------------ #
    #  Direction parameter system
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_infantry_direction_params(direction: Direction) -> dict:
        return _get_infantry_direction_params(direction)

    @staticmethod
    def _get_isometric_offset(direction: Direction) -> tuple:
        return _get_isometric_offset(direction)

    @staticmethod
    def _get_weapon_position(direction: Direction, cx, cy) -> tuple:
        return _get_weapon_position(direction, cx, cy)

    # ------------------------------------------------------------------ #
    #  Infantry-type-specific weapon drawing
    # ------------------------------------------------------------------ #

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
        return _draw_infantry_weapon(
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

    # ------------------------------------------------------------------ #
    #  Special state drawing methods
    # ------------------------------------------------------------------ #

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
        return _draw_infantry_prone_topdown(
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
        return _draw_infantry_death_topdown(
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

    # ------------------------------------------------------------------ #
    #  Animation sheet generation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _anim_state_to_params(anim_state: InfantryAnimState) -> tuple[str, int]:
        return _anim_state_to_params(anim_state)

    @staticmethod
    def create_infantry_animation_sheet(
        faction: Faction,
        infantry_type: InfantryType | None = None,
    ):
        return create_infantry_animation_sheet(faction=faction, infantry_type=infantry_type)


# ====================================================================== #
#  InfantryAnimator - re-exported from infantry_animator submodule
# ====================================================================== #
