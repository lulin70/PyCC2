"""Game Loop Rendering Mixin — extracted from game_loop.py (P5-1 batch 2).

Contains the rendering methods used by the GameLoop facade:
  - _apply_camera_effects: apply cinematic shake/zoom and return offset
  - _render_scene: shared render pipeline for deployment and battle phases

This is a mixin — do not instantiate directly. The facade GameLoop class
inherits this mixin and provides all required attributes via its dataclass
fields. Class-level attribute declarations below tell mypy which facade
fields the mixin methods rely on.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pycc2.domain.interfaces import (
    IDeploymentManager,
    IEffectStack,
    IHUDManager,
    ILightingRenderer,
    IRenderPipeline,
    IVictoryManager,
    IWeatherRenderer,
    IWeatherState,
)
from pycc2.services.game_loop_types import GameState

if TYPE_CHECKING:
    from pycc2.domain.interfaces.display_config import DisplayConfig

logger = logging.getLogger(__name__)


class GameLoopRenderingMixin:
    """Rendering methods for GameLoop. Inherited by the facade, not instantiated."""

    # -- Facade attributes used by rendering methods (no defaults; set by GameLoop) --
    state: GameState
    display_config: DisplayConfig | None
    use_full_hud: bool
    _effect_stack: IEffectStack | None
    _render_pipeline: IRenderPipeline | None
    _victory_manager: IVictoryManager | None
    _weather_renderer: IWeatherRenderer | None
    _weather_state: IWeatherState | None
    _lighting_renderer: ILightingRenderer | None
    _day_night_time: float | None
    _deployment_manager: IDeploymentManager | None
    _hud_manager: IHUDManager | None

    def _apply_camera_effects(self, time_speed: float) -> tuple[float, float]:
        """Apply cinematic camera effects and return the offset for later restoration."""
        camera_offset = (0.0, 0.0)
        if self._effect_stack is not None and not self._effect_stack.is_empty():
            camera_offset = self._effect_stack.get_total_offset()
            if camera_offset != (0.0, 0.0):
                from pycc2.domain.value_objects.vec2 import Vec2

                self.state.camera.position = Vec2(
                    self.state.camera.position.x + camera_offset[0],
                    self.state.camera.position.y + camera_offset[1],
                )

            # Apply slow-motion time scale from EffectStack
            time_scale = self._effect_stack.get_time_scale()
            if time_scale < 1.0:
                time_speed *= time_scale

        return camera_offset

    def _render_scene(self, screen, alpha: float) -> None:
        """Render the game scene — shared by both deployment and battle phases.

        This method eliminates the code duplication between deployment and battle
        rendering by extracting the common render pipeline + weather/lighting steps,
        then branching only for the phase-specific UI overlay.

        TD-039: Render failures degrade to skipping this frame (game continues
        running without visual update) instead of crashing the whole game.
        """
        if self._render_pipeline is None:
            return
        try:
            # Step 1: Render map and units (common to both phases)
            victory = self._victory_manager
            self._render_pipeline.render(
                game_map=self.state.game_map,
                units=self.state.units,
                camera=self.state.camera,
                alpha=alpha,
                selected_unit_ids=self.state.selected_unit_ids,
                debug_mode=self.state.debug_mode,
                paused=self.state.paused,
                tick=self.state.tick,
                show_post_battle=victory.show_post_battle if victory else False,
                game_result=victory.game_result if victory else None,
                battle_stats=victory.battle_stats if victory else None,
            )

            # Step 2: Render weather/lighting effects (common to both phases)
            if self._weather_renderer is not None and self._weather_state is not None:
                self._weather_renderer.render(screen, self.state.camera, self._weather_state)
            if self._lighting_renderer is not None and self._day_night_time is not None:
                self._lighting_renderer.render(screen, self._day_night_time)

            # Step 3: Phase-specific UI overlay
            dm = self._deployment_manager
            if dm is not None and dm.is_active and dm.deployment_ui is not None:
                # Deployment phase: render deployment UI
                deployment_ui = dm.deployment_ui
                dc = self.display_config
                tile_size = dc.base_tile_size if dc else 16
                deployment_ui.render(
                    screen,
                    font=None,
                    map_offset_x=0,
                    map_offset_y=0,
                    tile_size=tile_size,
                )
            else:
                # Battle phase: render CC2 unified bottom HUD panel
                if self._hud_manager:
                    self._hud_manager.render(screen, self.state.camera, self.state)
                elif self.use_full_hud:
                    # HUD expected but missing — log warning for debugging
                    logger.warning(
                        "[HUD] Battle phase active but _hud_manager is None. "
                        "Check GameLoopAssembler._init_hud() completed successfully.",
                    )
        except Exception:
            # TD-039: Render failure degrades to skipping this frame.
            # Log error and continue — do not propagate the exception
            # (a single render bug should not crash the whole game).
            logger.error(
                "Render failed, skipping this frame",
                exc_info=True,
            )


__all__ = ["GameLoopRenderingMixin"]
