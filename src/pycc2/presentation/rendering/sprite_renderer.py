"""Sprite renderer facade — composes the SRP-split rendering mixins.

This module is the public entry point for sprite rendering. The original
monolithic ``SpriteRenderer`` class (1178 lines) was split (D11-2 SRP refactor)
into a base plus four focused rendering mixins:

  - ``sprite_renderer_base.SpriteRendererBase``
      __init__, class constants, 13 backward-compat properties, the ``render()``
      orchestrator, spawn_*/update_* delegations, resize/shutdown.
  - ``terrain_rendering_mixin.TerrainRenderingMixin``
      ``_draw_debug_grid``, ``_generate_all_sprites``, ``_create_unit_sprite``,
      ``_generate_terrain_tiles``, ``_draw_terrain``.
  - ``vl_flag_rendering_mixin.VlFlagRenderingMixin``
      ``_draw_vl_flags``, ``_draw_vl_flag``, ``_draw_vl_edge_arrows`` (and the
      ``_VP_PULSE_*`` module constants).
  - ``unit_rendering_mixin.UnitRenderingMixin``
      ``_draw_units``, ``_draw_sprite_unit``, ``_facing_to_direction_index``,
      ``_draw_turret_overlay``.
  - ``unit_overlay_rendering_mixin.UnitOverlayRenderingMixin``
      selection rings/outlines, labels, flags, health bars, morale icons,
      and movement-mode indicators.

The facade ``SpriteRenderer`` inherits all of the above (mixin-first, base last
in MRO) and adds nothing of its own. Public API is 100% backward-compatible.
"""

from __future__ import annotations

from pycc2.presentation.rendering.sprite_renderer_base import SpriteRendererBase
from pycc2.presentation.rendering.terrain_rendering_mixin import TerrainRenderingMixin
from pycc2.presentation.rendering.unit_overlay_rendering_mixin import UnitOverlayRenderingMixin
from pycc2.presentation.rendering.unit_rendering_mixin import UnitRenderingMixin
from pycc2.presentation.rendering.vl_flag_rendering_mixin import VlFlagRenderingMixin

__all__ = ["SpriteRenderer"]


class SpriteRenderer(
    TerrainRenderingMixin,
    VlFlagRenderingMixin,
    UnitRenderingMixin,
    UnitOverlayRenderingMixin,
    SpriteRendererBase,
):
    """Main rendering coordinator — composes mixins. Public API 100% backward-compatible."""

    pass
