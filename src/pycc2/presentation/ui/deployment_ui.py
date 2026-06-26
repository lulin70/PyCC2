"""
Deployment Phase UI — CC2 Pre-Battle Deployment System

Implements the pre-battle deployment interface where players select units
from a force pool and place them on the map within friendly zones before
battle begins.

Zones:
  - FRIENDLY (green overlay): player can deploy units here
  - NO_MANS_LAND (gray overlay): contested, cannot deploy
  - ENEMY_CONTROLLED (red overlay): enemy territory, cannot deploy

Placement rules:
  - Tanks cannot deploy in buildings
  - Infantry cannot deploy in deep water
  - Max 9 infantry + 6 support units
  - Units must be within FRIENDLY zone
  - Right-click on a placed unit to remove it
"""

from __future__ import annotations

import logging
from dataclasses import field

logger = logging.getLogger(__name__)

# Import extracted modules (SRP refactoring v0.3.29)
from pycc2.domain.entities.game_map import GameMap
from pycc2.presentation.rendering.camera import Camera

# Import extracted subsystems (SRP refactoring v0.3.31)
from pycc2.presentation.ui.deployment_drag_drop import DeploymentDragDrop
from pycc2.presentation.ui.deployment_factory import (
    build_default_roster,
    build_force_pool_from_settings,
    generate_ai_deployment,
)
from pycc2.presentation.ui.deployment_input_router import DeploymentInputRouter
from pycc2.presentation.ui.deployment_los import DeploymentLOSSystem

# Import extracted models and constants
from pycc2.presentation.ui.deployment_models import (
    TERRAIN_OPEN,
    DeploymentPhase,
    DeploymentState,
    DeploymentUnit,
    UnitCategory,
    ZoneType,
)
from pycc2.presentation.ui.deployment_orders import DeploymentOrders
from pycc2.presentation.ui.deployment_placement import DeploymentPlacementService
from pycc2.presentation.ui.deployment_renderer import DeploymentRenderer
from pycc2.presentation.ui.deployment_zone_builder import DeploymentZoneBuilder

# ---------------------------------------------------------------------------
# Pygame – imported lazily so the module can be imported in headless tests
# ---------------------------------------------------------------------------
_pygame_available: bool = False
try:
    import pygame

    _pygame_available = True
except ImportError:
    pygame = None  # type: ignore[assignment]


# ========================================================================
# DEPLOYMENT UI
# ========================================================================


class DeploymentUI:
    """
    Pre-battle deployment interface.

    Renders zone overlays, a force pool panel on the left, and a
    "Start Battle" button.  Interaction model: click a unit in the
    force pool to select it, then click a valid map tile to place it.
    Right-click a placed unit on the map to remove it.
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, width: int = 800, height: int = 600) -> None:
        self.width = width
        self.height = height

        # Internal state
        self._state = DeploymentState()
        self._selected_unit_index: int | None = None
        self._map_width: int = 0
        self._map_height: int = 0
        self._tile_grid: list[list[int]] | None = None
        self._zone_map: list[list[ZoneType]] | None = None
        self._faction: str = "ally"

        # Victory locations for LOS preview (G5)
        self._victory_locations: list[dict] = []  # [{"id": str, "position": (x,y), "value": int}]

        # Roster panel geometry (LEFT side)
        self._roster_width: int = 240
        self._roster_padding: int = 6
        self._roster_item_height: int = 28
        self._roster_category_height: int = 24

        # Begin Battle button
        self._button_rect: tuple[int, int, int, int] | None = None
        self._button_hovered: bool = False

        # Pygame font cache
        self._font_small: pygame.font.Font | None = None
        self._font_normal: pygame.font.Font | None = None
        self._font_large: pygame.font.Font | None = None

        # Overlay surface cache (rebuilt when zones change)
        self._overlay_cache: pygame.Surface | None = None
        self._overlay_tile_size: int = 0

        # Roster layout cache (rebuilt when units change)
        self._roster_layout: list[tuple[str, UnitCategory | int]] = field(default_factory=list)
        # Each entry: ("category", category) or ("unit", index)

        # === Drag-and-drop state (Issue 3) — extracted to DeploymentDragDrop ===
        self._drag_drop = DeploymentDragDrop()

        # === Pre-battle orders (GAP-8) — extracted to DeploymentOrders ===
        self._orders = DeploymentOrders()

        # Extracted subsystems (SRP v0.3.29)
        self._los_system = DeploymentLOSSystem(
            get_tile_grid=lambda: self._tile_grid,
            get_terrain_at=self._get_terrain_at,
            get_victory_locations=lambda: self._victory_locations,
            get_state=lambda: self._state,
            get_selected_index=lambda: self._selected_unit_index,
        )

        # Extracted renderer (SRP v0.3.30)
        self._renderer = DeploymentRenderer(self)

        # Extracted zone builder (SRP v0.3.32)
        self._zone_builder = DeploymentZoneBuilder(self)

        # Extracted placement service (SRP v0.3.32)
        self._placement = DeploymentPlacementService(self)

        # Extracted input router (SRP v0.3.32)
        self._input_router = DeploymentInputRouter(self)

        # Renderer-managed UI state (retained for backward compatibility)
        self._detail_panel_btn_rect: tuple[int, int, int, int] | None = None
        self._detail_panel_btn_action: str | None = None
        self._highlight_surface_cache: dict[int, pygame.Surface] = {}

    # ------------------------------------------------------------------
    # Delegated attributes for renderer compatibility
    # ------------------------------------------------------------------

    @property
    def _dragging_unit(self) -> DeploymentUnit | None:
        return self._drag_drop._dragging_unit

    @_dragging_unit.setter
    def _dragging_unit(self, value: DeploymentUnit | None) -> None:
        self._drag_drop._dragging_unit = value

    @property
    def _dragging_unit_index(self) -> int | None:
        return self._drag_drop._dragging_unit_index

    @_dragging_unit_index.setter
    def _dragging_unit_index(self, value: int | None) -> None:
        self._drag_drop._dragging_unit_index = value

    @property
    def _drag_start_pos(self) -> tuple[int, int] | None:
        return self._drag_drop._drag_start_pos

    @_drag_start_pos.setter
    def _drag_start_pos(self, value: tuple[int, int] | None) -> None:
        self._drag_drop._drag_start_pos = value

    @property
    def _drag_current_pos(self) -> tuple[int, int] | None:
        return self._drag_drop._drag_current_pos

    @_drag_current_pos.setter
    def _drag_current_pos(self, value: tuple[int, int] | None) -> None:
        self._drag_drop._drag_current_pos = value

    @property
    def _is_dragging(self) -> bool:
        return self._drag_drop._is_dragging

    @_is_dragging.setter
    def _is_dragging(self, value: bool) -> None:
        self._drag_drop._is_dragging = value

    @property
    def _ghost_surface(self) -> pygame.Surface | None:
        return self._drag_drop._ghost_surface

    @_ghost_surface.setter
    def _ghost_surface(self, value: pygame.Surface | None) -> None:
        self._drag_drop._ghost_surface = value

    def _create_ghost_surface(self, unit: DeploymentUnit) -> pygame.Surface | None:
        return self._drag_drop._create_ghost_surface(unit, self)

    @property
    def _pending_orders(self) -> dict[str, tuple[int, int]]:
        return self._orders._pending_orders

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> DeploymentState:
        """Return the current deployment state (read-only reference)."""
        return self._state

    @property
    def selected_unit_index(self) -> int | None:
        """Index of the currently selected roster unit, or None."""
        return self._selected_unit_index

    @property
    def requisition_remaining(self) -> int:
        """Remaining requisition points."""
        return self._state.requisition_points - self._state.requisition_points_spent

    def start_deployment(self, map_data: dict, faction: str = "ally") -> None:
        """Initialize deployment phase with map zones and unit roster.

        Delegates to DeploymentZoneBuilder.
        """
        self._zone_builder.start_deployment(map_data, faction)

    def start_deployment_with_settings(
        self,
        map_data: dict,
        faction: str = "ally",
        requisition_points: int = 2000,
        max_infantry: int = 9,
        max_support: int = 6,
        force_pool: list[DeploymentUnit] | None = None,
    ) -> None:
        """Initialize deployment with game settings controlling the force pool.

        Delegates to DeploymentZoneBuilder.
        """
        self._zone_builder.start_deployment_with_settings(
            map_data, faction, requisition_points, max_infantry, max_support, force_pool
        )

    def handle_click(self, x: int, y: int) -> str | None:
        """Handle a mouse click at screen coordinates (x, y).

        Delegates to DeploymentInputRouter.
        """
        return self._input_router.handle_click(x, y)

    def handle_right_click(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> str | None:
        """Handle a right-click during deployment.

        Delegates to DeploymentOrders for order placement logic.

        Behaviour (GAP-8):
          - If a placed unit is selected, right-click on the map sets a
            pending move order for that unit.
          - If no placed unit is selected, right-click on a placed unit
            selects it for ordering.
          - Right-click on roster deselects.

        Returns an action string or None:
          - ``"set_order:<unit_id>,<tx>,<ty>"`` – pending move order set
          - ``"select_placed_unit:<x>,<y>"`` – placed unit selected for ordering
          - ``"remove_unit:<x>,<y>"`` – placed unit removed (no unit selected)
          - ``None`` – click did nothing
        """
        return self._orders.handle_right_click(screen_x, screen_y, self)

    def place_unit(self, unit_index: int, map_x: int, map_y: int) -> bool:
        """Place a unit at the given map tile position.

        Delegates to DeploymentPlacementService.
        Returns True if placement succeeded.
        """
        return self._placement.place_unit(unit_index, map_x, map_y)

    def remove_unit(self, map_x: int, map_y: int) -> bool:
        """Remove a placed unit at the given map position, returning it to roster.

        Delegates to DeploymentPlacementService.
        Returns True if a unit was removed.
        """
        return self._placement.remove_unit(map_x, map_y)

    def can_place_at(self, unit: DeploymentUnit, map_x: int, map_y: int, terrain: int) -> bool:
        """Check if *unit* can be placed at (map_x, map_y) with the given terrain value.

        Delegates to DeploymentPlacementService.
        """
        return self._placement.can_place_at(unit, map_x, map_y, terrain)

    def is_deployment_complete(self) -> bool:
        """Check if at least one unit is placed (minimum to begin battle)."""
        return len(self._state.placed_units) >= 1

    def begin_battle(self) -> dict:
        """Finalize deployment and return placement data.

        Returns a dict with:
          - ``phase``: ``DeploymentPhase.ACTIVE``
          - ``placements``: list of {unit_template_id, position}
          - ``infantry_count`` / ``support_count``
          - ``requisition_spent`` / ``requisition_remaining``
        """
        self._state.phase = DeploymentPhase.ACTIVE

        infantry_count = sum(1 for u in self._state.placed_units if u.unit_type == "infantry")
        support_count = sum(
            1 for u in self._state.placed_units if u.unit_type in ("support", "vehicle")
        )

        placements = [
            {
                "unit_template_id": u.unit_template_id,
                "display_name": u.display_name,
                "unit_type": u.unit_type,
                "position": u.position,
            }
            for u in self._state.placed_units
        ]

        return {
            "phase": self._state.phase,
            "placements": placements,
            "infantry_count": infantry_count,
            "support_count": support_count,
            "requisition_spent": self._state.requisition_points_spent,
            "requisition_remaining": self.requisition_remaining,
            "pending_orders": self._orders.get_orders_for_battle(),  # GAP-8: include pre-battle orders
        }

    # ------------------------------------------------------------------
    # Pre-battle orders (GAP-8) — delegated to DeploymentOrders
    # ------------------------------------------------------------------

    def set_pending_order(self, unit_template_id: str, target_x: int, target_y: int) -> None:
        """Set a pending movement order for a deployed unit.

        The unit will move toward (target_x, target_y) when battle begins.
        """
        self._orders.set_pending_order(unit_template_id, target_x, target_y)

    def get_pending_order(self, unit_template_id: str) -> tuple[int, int] | None:
        """Return the pending order target for a unit, or None."""
        return self._orders.get_pending_order(unit_template_id)

    def clear_pending_order(self, unit_template_id: str) -> None:
        """Remove a pending order for a unit."""
        self._orders.clear_pending_order(unit_template_id)

    @property
    def pending_orders(self) -> dict[str, tuple[int, int]]:
        """Return a copy of all pending orders."""
        return self._orders.pending_orders

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(
        self,
        screen: pygame.Surface,
        font: pygame.font.Font,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> None:
        """Render the deployment UI overlay on the game screen.

        CRITICAL: Map area starts at x=self._roster_width (right of roster panel).
        - For RENDERING: use actual_map_offset_x (includes roster width)
        - For CLICK DETECTION: use original map_offset_x (screen_to_map adds roster width internally)

        Parameters
        ----------
        screen : pygame.Surface
        font : pygame.font.Font
        map_offset_x, map_offset_y : int
            Pixel offset of the map's top-left corner on *screen*.
        tile_size : int
            Pixel size of one map tile.
        """
        if not _pygame_available or screen is None:
            return

        self._ensure_fonts(font)

        # CRITICAL: Two different offsets needed!
        # 1. For rendering: map visual position (right of roster)
        actual_map_offset_x = self._roster_width + map_offset_x
        actual_map_offset_y = map_offset_y

        # 2. For click detection: pass original values (screen_to_map adds roster width internally)
        click_map_offset_x = map_offset_x
        click_map_offset_y = map_offset_y

        r = self._renderer

        # 1. Zone overlays (using RENDERING offset)
        r._render_zone_overlays(screen, actual_map_offset_x, actual_map_offset_y, tile_size)

        # 2. Valid placement highlights (when a unit is selected)
        if self._selected_unit_index is not None:
            r._render_placement_highlights(
                screen, actual_map_offset_x, actual_map_offset_y, tile_size
            )

        # 3. Placed unit markers (using RENDERING offset)
        r._render_placed_units(screen, actual_map_offset_x, actual_map_offset_y, tile_size)

        # 3.5. Pending order arrows (GAP-8)
        r._render_pending_orders(screen, actual_map_offset_x, actual_map_offset_y, tile_size)

        # 3.6. LOS preview lines from placed/selected units to VLs (G5)
        r._render_los_preview(screen, actual_map_offset_x, actual_map_offset_y, tile_size)

        # 4. Force pool panel (left side) - drawn at (0, 0)
        r._render_roster(screen)

        # 5. Requisition points counter (TOP of screen - prominent location)
        r._render_requisition_points(screen)

        # 6. Start Battle button (at bottom of roster panel)
        r._render_start_battle_button(screen)

        # 7. Unit details panel (right side) - when unit selected
        if self._selected_unit_index is not None:
            r._render_unit_details_panel(screen)

        # 8. Drag-and-drop visual feedback (using CLICK DETECTION offset for proper alignment)
        r._render_drag_feedback(screen, click_map_offset_x, click_map_offset_y, tile_size)

    def render_deployment_zones(
        self,
        surface: pygame.Surface,
        camera: Camera,
        game_map: GameMap,
        tile_size: int = 48,
    ) -> None:
        """Render deployment zone overlays on the map using camera/game_map objects.

        This is an alternative rendering entry point that works with external
        camera and game_map objects, suitable for integration with the main
        game loop's render pipeline.

        Parameters
        ----------
        surface : pygame.Surface
            The screen surface to draw on.
        camera : object
            Camera with ``offset_x`` / ``offset_y`` attributes.
        game_map : object
            Map with ``width``, ``height`` attributes.
        tile_size : int
            Pixel size per tile (default 48).
        """
        return self._renderer.render_deployment_zones(surface, camera, game_map, tile_size)

    def handle_deployment_drag(
        self,
        event: pygame.event.Event,
        camera: Camera,
        game_map: GameMap,
        tile_size: int = 48,
    ) -> None:
        """Handle drag-drop deployment interaction using pygame events directly.

        This is an alternative input entry point that works with raw pygame
        events and external camera/game_map objects.

        Parameters
        ----------
        event : pygame.event.Event
            The pygame event to process.
        camera : object
            Camera with ``offset_x`` / ``offset_y`` attributes.
        game_map : object
            Map with ``width``, ``height`` attributes.
        tile_size : int
            Pixel size per tile (default 48).
        """
        return self._renderer.handle_deployment_drag(event, camera, game_map, tile_size)

    # ------------------------------------------------------------------
    # Internal – LOS hit probability estimation (G5)
    # ------------------------------------------------------------------

    def _estimate_deployment_hit_probability(
        self,
        src_x: int,
        src_y: int,
        dst_x: int,
        dst_y: int,
        distance: float,
        unit: DeploymentUnit,
    ) -> float:
        """Delegate to DeploymentLOSSystem for hit probability estimation."""
        return self._renderer._estimate_deployment_hit_probability(
            src_x,
            src_y,
            dst_x,
            dst_y,
            distance,
            unit,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_zone_at(self, x: int, y: int) -> ZoneType:
        """Return the ZoneType at the given tile coordinates."""
        if self._zone_map is None:
            return ZoneType.NO_MANS_LAND
        if not (0 <= x < self._map_width and 0 <= y < self._map_height):
            return ZoneType.NO_MANS_LAND
        return self._zone_map[y][x]

    def _get_terrain_at(self, x: int, y: int) -> int:
        if self._tile_grid is None:
            return TERRAIN_OPEN
        if not (0 <= y < len(self._tile_grid) and 0 <= x < len(self._tile_grid[0])):
            return TERRAIN_OPEN
        return int(self._tile_grid[y][x])

    def _is_in_button(self, x: int, y: int) -> bool:
        """Delegate to DeploymentInputRouter."""
        return self._input_router._is_in_button(x, y)

    def _roster_index_at(self, click_x: int, click_y: int) -> int | None:
        """Delegate to DeploymentInputRouter."""
        return self._input_router._roster_index_at(click_x, click_y)

    def screen_to_map(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> tuple[int, int] | None:
        """Convert screen coordinates to map tile coordinates.

        Accounts for the roster panel on the left side.
        Returns (map_x, map_y) or None if outside the map.
        """
        # CRITICAL FIX: Adjust for roster panel width (this was causing click misalignment!)
        local_x = screen_x - self._roster_width - map_offset_x
        local_y = screen_y - map_offset_y

        if tile_size <= 0:
            return None

        # Only process clicks in the MAP area (right of roster)
        if local_x < 0:
            return None

        map_x = local_x // tile_size
        map_y = local_y // tile_size

        if 0 <= map_x < self._map_width and 0 <= map_y < self._map_height:
            return (map_x, map_y)
        return None

    # ========================================================================
    # DRAG-AND-DROP SUPPORT (Issue 3) — delegated to DeploymentDragDrop
    # ========================================================================

    def handle_mouse_down(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> str | None:
        """Handle mouse button DOWN - start drag from roster unit.

        Delegates to DeploymentDragDrop.
        """
        return self._drag_drop.handle_mouse_down(screen_x, screen_y, self)

    def handle_mouse_move(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> None:
        """Handle mouse movement while dragging - update ghost position.

        Delegates to DeploymentDragDrop.
        """
        self._drag_drop.handle_mouse_move(screen_x, screen_y)

    def handle_mouse_up(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> str | None:
        """Handle mouse button UP - complete drag (place or cancel).

        Delegates to DeploymentDragDrop.
        """
        return self._drag_drop.handle_mouse_up(screen_x, screen_y, self)

    def _clear_drag_state(self) -> None:
        """Clear all drag-and-drop state. Delegates to DeploymentDragDrop."""
        self._drag_drop.clear_drag_state()

    def handle_click_full(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
        right_click: bool = False,
    ) -> str | None:
        """Full click handler that converts screen coords to map coords automatically.

        Delegates to DeploymentInputRouter.
        This is the preferred entry point for integration with the game loop.
        Supports both left-click (place/select) and right-click (remove).
        """
        return self._input_router.handle_click_full(
            screen_x, screen_y, map_offset_x, map_offset_y, tile_size, right_click
        )

    def _ensure_fonts(self, font: pygame.font.Font) -> None:
        """Initialise font objects if not already done."""
        return self._renderer._ensure_fonts(font)

    @staticmethod
    def _build_default_roster() -> list[DeploymentUnit]:
        """Delegate to deployment_factory.build_default_roster."""
        return build_default_roster()

    @staticmethod
    def build_force_pool_from_settings(
        faction: str = "allied",
        requisition_points: int = 2000,
    ) -> list[DeploymentUnit]:
        """Delegate to deployment_factory.build_force_pool_from_settings."""
        return build_force_pool_from_settings(faction, requisition_points)

    @staticmethod
    def generate_ai_deployment(
        map_data: dict,
        faction: str = "axis",
        requisition_points: int = 1500,
    ) -> list[dict]:
        """Delegate to deployment_factory.generate_ai_deployment."""
        return generate_ai_deployment(map_data, faction, requisition_points)

    def update_button_hover(self, mouse_x: int, mouse_y: int) -> None:
        """Update the Start Battle button hover state based on mouse position."""
        self._button_hovered = bool(self._button_rect and self._is_in_button(mouse_x, mouse_y))
