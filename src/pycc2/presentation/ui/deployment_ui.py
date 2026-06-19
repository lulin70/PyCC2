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
import math
from dataclasses import field

logger = logging.getLogger(__name__)

# Import extracted modules (SRP refactoring v0.3.29)
from pycc2.domain.entities.game_map import GameMap
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.ui.deployment_factory import (
    build_default_roster,
    build_force_pool_from_settings,
    generate_ai_deployment,
)
from pycc2.presentation.ui.deployment_los import DeploymentLOSSystem

# Import extracted models and constants
from pycc2.presentation.ui.deployment_models import (
    TERRAIN_BUILDING_SOLID,
    # Constants (backward compatible aliases)
    TERRAIN_OPEN,
    TERRAIN_WATER,
    DeploymentPhase,
    DeploymentState,
    DeploymentUnit,
    ZoneType,
)
from pycc2.presentation.ui.deployment_renderer import DeploymentRenderer

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
        self._overlay_cache: dict[str, pygame.Surface] | None = None
        self._overlay_tile_size: int = 0

        # Roster layout cache (rebuilt when units change)
        self._roster_layout: list[tuple[str, int]] = field(default_factory=list)
        # Each entry: ("category", -1) or ("unit", index)

        # === Drag-and-drop state (Issue 3) ===
        self._dragging_unit: DeploymentUnit | None = None
        self._dragging_unit_index: int | None = None
        self._drag_start_pos: tuple[int, int] | None = None
        self._drag_current_pos: tuple[int, int] | None = None
        self._ghost_surface: pygame.Surface | None = None  # Pre-rendered ghost sprite
        self._is_dragging: bool = False

        # === Pre-battle orders (GAP-8) ===
        self._pending_orders: dict[
            str, tuple[int, int]
        ] = {}  # unit_template_id -> (target_x, target_y)
        self._selected_placed_unit: DeploymentUnit | None = None  # For setting orders
        self._highlight_surface_cache: dict[int, pygame.Surface] = {}

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

        Parameters
        ----------
        map_data : dict
            Must contain keys:
              - ``width`` (int): map tile width
              - ``height`` (int): map tile height
              - ``tiles`` (list[list[int]]): 2-D terrain grid
            May contain:
              - ``friendly_zone`` / ``enemy_zone`` / ``no_mans_land``:
                lists of (x, y) tuples
              - ``spawn_points``: list of spawn point dicts with
                ``side`` and ``position`` keys
        faction : str
            ``"ally"`` or ``"axis"`` – determines which side's zones are
            used as FRIENDLY.
        """
        self._map_width = map_data.get("width", 50)
        self._map_height = map_data.get("height", 42)
        self._tile_grid = map_data.get("tiles")
        self._faction = faction

        # Build zone map from explicit zones or spawn_points -----------
        friendly = set(map_data.get("friendly_zone", []))
        enemy = set(map_data.get("enemy_zone", []))
        nml = set(map_data.get("no_mans_land", []))

        # If no explicit zones, try building from spawn_points
        if not friendly and not enemy and not nml:
            spawn_points = map_data.get("spawn_points", [])
            if spawn_points:
                friendly, enemy, nml = self._zones_from_spawn_points(spawn_points)

        # Default: left third = friendly, right third = enemy, middle = NML
        if not friendly and not enemy and not nml:
            third = self._map_width // 3
            for y in range(self._map_height):
                for x in range(self._map_width):
                    if x < third:
                        friendly.add((x, y))
                    elif x >= self._map_width - third:
                        enemy.add((x, y))
                    else:
                        nml.add((x, y))

        # Swap for axis faction
        if faction == "axis":
            friendly, enemy = enemy, friendly

        self._state.friendly_zone = sorted(friendly)
        self._state.enemy_zone = sorted(enemy)
        self._state.no_mans_land = sorted(nml)

        self._zone_map = []
        for y in range(self._map_height):
            row: list[ZoneType] = []
            for x in range(self._map_width):
                if (x, y) in friendly:
                    row.append(ZoneType.FRIENDLY)
                elif (x, y) in enemy:
                    row.append(ZoneType.ENEMY_CONTROLLED)
                else:
                    row.append(ZoneType.NO_MANS_LAND)
            self._zone_map.append(row)

        # Build default unit roster --------------------------------------
        self._state.available_units = self._build_default_roster()
        self._state.placed_units = []
        self._state.phase = DeploymentPhase.DEPLOYING
        self._selected_unit_index = None

        # Default requisition points
        if self._state.requisition_points <= 0:
            self._state.requisition_points = 2000
        self._state.requisition_points_spent = 0

        # Store victory locations for LOS preview (G5)
        self._victory_locations = map_data.get("victory_locations", [])

        # Rebuild roster layout
        self._rebuild_roster_layout()

        # Invalidate overlay cache
        self._overlay_cache = None

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

        Parameters
        ----------
        map_data : dict
            Map data (same as ``start_deployment``).
        faction : str
            Player faction.
        requisition_points : int
            Total requisition points available.
        max_infantry, max_support : int
            Maximum units per category.
        force_pool : list[DeploymentUnit] | None
            Custom force pool; if None, default roster is built.
        """
        self._state.requisition_points = requisition_points
        self._state.max_infantry = max_infantry
        self._state.max_support = max_support
        self._state.requisition_points_spent = 0

        # Initialize zones via the base method
        self.start_deployment(map_data, faction)

        # Override roster if custom force pool provided
        if force_pool is not None:
            self._state.available_units = force_pool
            self._rebuild_roster_layout()

    def _zones_from_spawn_points(
        self, spawn_points: list[dict]
    ) -> tuple[set[tuple[int, int]], set[tuple[int, int]], set[tuple[int, int]]]:
        """Build deployment zones from map spawn_points data.

        Uses spawn point positions as centers and expands outward to
        create deployment zones covering roughly 1/3 of the map each.
        """
        friendly: set[tuple[int, int]] = set()
        enemy: set[tuple[int, int]] = set()
        nml: set[tuple[int, int]] = set()

        ally_spawns = [sp for sp in spawn_points if sp.get("side") == "allies"]
        axis_spawns = [sp for sp in spawn_points if sp.get("side") == "axis"]

        # Determine zone boundaries based on spawn positions
        if ally_spawns and axis_spawns:
            ally_center_x = sum(sp["position"][0] for sp in ally_spawns) // len(ally_spawns)
            axis_center_x = sum(sp["position"][0] for sp in axis_spawns) // len(axis_spawns)

            # Ensure ally is left, axis is right
            if ally_center_x > axis_center_x:
                ally_center_x, axis_center_x = axis_center_x, ally_center_x

            # Create zones: ally left portion, axis right portion, NML middle
            ally_boundary = (ally_center_x + axis_center_x) // 3
            axis_boundary = 2 * (ally_center_x + axis_center_x) // 3

            for y in range(self._map_height):
                for x in range(self._map_width):
                    if x <= ally_boundary:
                        friendly.add((x, y))
                    elif x >= axis_boundary:
                        enemy.add((x, y))
                    else:
                        nml.add((x, y))
        else:
            # Fallback to default thirds
            third = self._map_width // 3
            for y in range(self._map_height):
                for x in range(self._map_width):
                    if x < third:
                        friendly.add((x, y))
                    elif x >= self._map_width - third:
                        enemy.add((x, y))
                    else:
                        nml.add((x, y))

        return friendly, enemy, nml

    def handle_click(self, x: int, y: int) -> str | None:
        """Handle a mouse click at screen coordinates (x, y).

        Returns an action string or None:
          - ``"select_unit:<index>"`` – roster unit selected
          - ``"place_unit:<index>"`` – unit placed on map
          - ``"remove_unit:<x>,<y>"`` – placed unit removed
          - ``"begin_battle"`` – player confirmed deployment
          - ``None`` – click did nothing
        """
        if self._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return None

        # Check Begin Battle button first
        if self._button_rect and self._is_in_button(x, y):
            if self.is_deployment_complete():
                return "begin_battle"
            return None

        # Check roster panel click (LEFT side)
        if x < self._roster_width:
            idx = self._roster_index_at(x, y)
            if idx is not None and 0 <= idx < len(self._state.available_units):
                unit = self._state.available_units[idx]
                if not unit.is_placed:
                    self._selected_unit_index = idx
                    return f"select_unit:{idx}"
            return None

        # Map click – either place or remove
        return self._handle_map_click(x, y)

    def handle_right_click(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> str | None:
        """Handle a right-click during deployment.

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
        if self._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return None

        # Right-click on roster → deselect
        if screen_x < self._roster_width:
            self._selected_unit_index = None
            self._selected_placed_unit = None
            return None

        # Right-click on map
        map_pos = self.screen_to_map(screen_x, screen_y, map_offset_x, map_offset_y, tile_size)
        if map_pos is None:
            return None

        map_x, map_y = map_pos

        # If a placed unit is selected, set a pending move order
        if self._selected_placed_unit is not None and self._selected_placed_unit.is_placed:
            # Set the pending order
            self.set_pending_order(self._selected_placed_unit.unit_template_id, map_x, map_y)
            result = f"set_order:{self._selected_placed_unit.unit_template_id},{map_x},{map_y}"
            return result

        # Otherwise, try to select a placed unit at this position
        for pu in self._state.placed_units:
            if pu.position == (map_x, map_y):
                self._selected_placed_unit = pu
                # Also find and set the roster index for the detail panel
                for i, au in enumerate(self._state.available_units):
                    if au is pu:
                        self._selected_unit_index = i
                        break
                return f"select_placed_unit:{map_x},{map_y}"

        # No placed unit selected and no unit at click position → remove (legacy behavior)
        if self.remove_unit(map_x, map_y):
            return f"remove_unit:{map_x},{map_y}"

        return None

    def place_unit(self, unit_index: int, map_x: int, map_y: int) -> bool:
        """Place a unit at the given map tile position.

        Returns True if placement succeeded.
        """
        if self._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return False

        if unit_index < 0 or unit_index >= len(self._state.available_units):
            return False

        unit = self._state.available_units[unit_index]

        # Already placed somewhere else?
        if unit.is_placed:
            return False

        # Check requisition points
        if unit.deployment_cost > self.requisition_remaining:
            return False

        # Check zone
        if not self._is_in_friendly_zone(map_x, map_y):
            return False

        # Check terrain
        terrain = self._get_terrain_at(map_x, map_y)
        if not self.can_place_at(unit, map_x, map_y, terrain):
            return False

        # Check unit count limits
        if not self._check_unit_limits(unit):
            return False

        # Check tile not already occupied
        for pu in self._state.placed_units:
            if pu.position == (map_x, map_y):
                return False

        # Place the unit (with defensive checks)
        try:
            unit.position = (map_x, map_y)
            unit.is_placed = True
            self._state.placed_units.append(unit)
            self._state.requisition_points_spent += unit.deployment_cost
        except (AttributeError, ValueError, TypeError):
            # If placement fails, rollback
            unit.position = None
            unit.is_placed = False
            return False

        # Clear selection after placing
        self._selected_unit_index = None

        # Auto-transition to READY when at least one unit placed
        if self._state.phase == DeploymentPhase.DEPLOYING and self._state.placed_units:
            self._state.phase = DeploymentPhase.READY

        return True

    def remove_unit(self, map_x: int, map_y: int) -> bool:
        """Remove a placed unit at the given map position, returning it to roster.

        Returns True if a unit was removed.
        """
        for i, pu in enumerate(self._state.placed_units):
            if pu.position == (map_x, map_y):
                # Refund requisition points
                self._state.requisition_points_spent -= pu.deployment_cost
                pu.position = None
                pu.is_placed = False
                self._state.placed_units.pop(i)

                # Revert phase if no units left
                if not self._state.placed_units:
                    self._state.phase = DeploymentPhase.DEPLOYING

                return True
        return False

    def can_place_at(self, unit: DeploymentUnit, map_x: int, map_y: int, terrain: int) -> bool:
        """Check if *unit* can be placed at (map_x, map_y) with the given terrain value.

        ULTRA-RELAXED RULES for maximum gameplay flexibility:
        - ONLY block deep water and solid buildings (truly impassable)
        - ALL other terrains are allowed (roads, bridges, rough, hedges, etc.)
        """
        # Check 1: Must be in friendly zone
        if not self._is_in_friendly_zone(map_x, map_y):
            return False

        # Check 2: Only truly impassable terrains are blocked
        # Check 3: Everything else is ALLOWED!
        # No more restrictions on roads, rough terrain, buildings, hedges, etc.
        return terrain not in (TERRAIN_WATER, TERRAIN_BUILDING_SOLID)

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
            "pending_orders": dict(self._pending_orders),  # GAP-8: include pre-battle orders
        }

    # ------------------------------------------------------------------
    # Pre-battle orders (GAP-8)
    # ------------------------------------------------------------------

    def set_pending_order(self, unit_template_id: str, target_x: int, target_y: int) -> None:
        """Set a pending movement order for a deployed unit.

        The unit will move toward (target_x, target_y) when battle begins.
        """
        self._pending_orders[unit_template_id] = (target_x, target_y)

    def get_pending_order(self, unit_template_id: str) -> tuple[int, int] | None:
        """Return the pending order target for a unit, or None."""
        return self._pending_orders.get(unit_template_id)

    def clear_pending_order(self, unit_template_id: str) -> None:
        """Remove a pending order for a unit."""
        self._pending_orders.pop(unit_template_id, None)

    @property
    def pending_orders(self) -> dict[str, tuple[int, int]]:
        """Return a copy of all pending orders."""
        return dict(self._pending_orders)

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
    # Internal – zone overlays
    # ------------------------------------------------------------------

    def _render_zone_overlays(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        return self._renderer._render_zone_overlays(screen, ox, oy, ts)

    # ------------------------------------------------------------------
    # Internal – placement highlights
    # ------------------------------------------------------------------

    def _render_placement_highlights(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        return self._renderer._render_placement_highlights(screen, ox, oy, ts)

    # ------------------------------------------------------------------
    # Internal – placed unit markers
    # ------------------------------------------------------------------

    def _render_placed_units(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        """Render placed units with DISTINCT SHAPES for each type (CC2 style)."""
        return self._renderer._render_placed_units(screen, ox, oy, ts)

    # ------------------------------------------------------------------
    # Internal – pending order arrows (GAP-8)
    # ------------------------------------------------------------------

    def _render_pending_orders(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        """Render arrows from placed units to their pending move targets."""
        return self._renderer._render_pending_orders(screen, ox, oy, ts)

    # ------------------------------------------------------------------
    # Internal – LOS preview lines (G5)
    # ------------------------------------------------------------------

    # LOS preview color constants (matching AttackLineSystem 4-color scheme)
    _LOS_COLOR_HIGH: tuple[int, int, int, int] = (0, 255, 0, 160)  # Green (60-100% hit)
    _LOS_COLOR_MODERATE: tuple[int, int, int, int] = (255, 255, 0, 160)  # Yellow (30-59% hit)
    _LOS_COLOR_LOW: tuple[int, int, int, int] = (255, 50, 50, 160)  # Red (10-29% hit)
    _LOS_COLOR_IMPOSSIBLE: tuple[int, int, int, int] = (0, 0, 0, 160)  # Black (0-9% hit)
    _LOS_DEFAULT_RANGE: int = 15  # Default visual range in tiles

    def _render_los_preview(self, screen, ox: int, oy: int, ts: int) -> None:
        """Delegate to DeploymentLOSSystem for LOS preview rendering."""
        return self._renderer._render_los_preview(screen, ox, oy, ts)

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

    def _hit_probability_to_los_color(self, hit_prob: float) -> tuple[int, int, int, int]:
        """Delegate to DeploymentLOSSystem for probability→color mapping."""
        return self._renderer._hit_probability_to_los_color(hit_prob)

    @staticmethod
    def _draw_dashed_line(
        surface,
        color: tuple[int, int, int, int],
        start: tuple[int, int],
        end: tuple[int, int],
        dash_length: int = 6,
        gap_length: int = 4,
    ) -> None:
        """Delegate to DeploymentLOSSystem.draw_dashed_line (via rendering_utils)."""
        return DeploymentRenderer._draw_dashed_line(
            surface, color, start, end, dash_length=dash_length, gap_length=gap_length
        )

    @staticmethod
    def _draw_arrowhead(
        surface,
        color: tuple[int, int, int],
        start: tuple[int, int],
        end: tuple[int, int],
        size: int = 8,
    ) -> None:
        """Delegate to DeploymentLOSSystem.draw_arrowhead."""
        return DeploymentRenderer._draw_arrowhead(surface, color, start, end, size)

    # ------------------------------------------------------------------
    # Internal – force pool panel (LEFT side)
    # ------------------------------------------------------------------

    def _rebuild_roster_layout(self) -> None:
        """Rebuild the roster layout with category headers."""
        return self._renderer._rebuild_roster_layout()

    def _render_roster(self, screen: pygame.Surface) -> None:
        return self._renderer._render_roster(screen)

    # ------------------------------------------------------------------
    # Internal – requisition points HEADER with progress bar (Issue 2)
    # ------------------------------------------------------------------

    def _render_rp_header(self, panel_surf: pygame.Surface) -> None:
        """Render prominent requisition points display with visual progress bar."""
        return self._renderer._render_rp_header(panel_surf)

    # ------------------------------------------------------------------
    # Internal – requisition points (original simple version, now supplemental)
    # ------------------------------------------------------------------

    def _render_requisition_points(self, screen: pygame.Surface) -> None:
        """Render a prominent RP counter at the top of the screen (above roster panel)."""
        return self._renderer._render_requisition_points(screen)

    # ------------------------------------------------------------------
    # Internal – unit counts
    # ------------------------------------------------------------------

    def _render_unit_counts(self, screen: pygame.Surface) -> None:
        return self._renderer._render_unit_counts(screen)

    # ------------------------------------------------------------------
    # Internal – Start Battle button
    # ------------------------------------------------------------------

    def _render_start_battle_button(self, screen: pygame.Surface) -> None:
        """Render prominent START BATTLE button - make it VERY visible and accessible."""
        return self._renderer._render_start_battle_button(screen)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_in_friendly_zone(self, x: int, y: int) -> bool:
        if self._zone_map is None:
            return False
        if not (0 <= x < self._map_width and 0 <= y < self._map_height):
            return False
        return self._zone_map[y][x] == ZoneType.FRIENDLY

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

    def _check_unit_limits(self, unit: DeploymentUnit) -> bool:
        infantry_count = sum(1 for u in self._state.placed_units if u.unit_type == "infantry")
        support_count = sum(
            1 for u in self._state.placed_units if u.unit_type in ("support", "vehicle")
        )

        if unit.unit_type == "infantry":
            return infantry_count < self._state.max_infantry
        elif unit.unit_type in ("support", "vehicle"):
            return support_count < self._state.max_support
        elif unit.unit_type == "recon":
            return infantry_count < self._state.max_infantry
        return False

    def _is_in_button(self, x: int, y: int) -> bool:
        if self._button_rect is None:
            return False
        bx, by, bw, bh = self._button_rect
        return bx <= x <= bx + bw and by <= y <= by + bh

    def _roster_index_at(self, click_x: int, click_y: int) -> int | None:
        """Return the roster unit index at screen coords, or None."""
        if click_x < self._roster_padding or click_x > self._roster_width - self._roster_padding:
            return None

        # Walk the layout to find which unit was clicked
        y_offset = 36
        for entry_type, entry_data in self._roster_layout:
            if entry_type == "category":
                h = self._roster_category_height + 2
                if y_offset <= click_y < y_offset + h:
                    return None  # Clicked on category header
                y_offset += h
            elif entry_type == "unit":
                h = self._roster_item_height + 2
                if y_offset <= click_y < y_offset + h:
                    return entry_data  # Return the unit index
                y_offset += h

        return None

    def _handle_map_click(self, screen_x: int, screen_y: int) -> str | None:
        """Handle a click on the map area. Requires map_offset/tile_size context."""
        return None

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
    # DRAG-AND-DROP SUPPORT (Issue 3)
    # ========================================================================

    def handle_mouse_down(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> str | None:
        """Handle mouse button DOWN - start drag from roster unit."""
        if self._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return None

        # Only start drag from roster panel (left side)
        if screen_x >= self._roster_width:
            return None

        # Find which roster unit was clicked
        idx = self._roster_index_at(screen_x, screen_y)
        if idx is None or idx < 0 or idx >= len(self._state.available_units):
            return None

        unit = self._state.available_units[idx]

        # Can't drag already-placed units
        if unit.is_placed:
            return None

        # Start dragging this unit
        self._dragging_unit = unit
        self._dragging_unit_index = idx
        self._drag_start_pos = (screen_x, screen_y)
        self._drag_current_pos = (screen_x, screen_y)
        self._is_dragging = True

        # Create ghost surface ONCE (not every frame)
        try:
            self._ghost_surface = self._create_ghost_surface(unit)
        except (pygame.error, ValueError, TypeError):
            self._ghost_surface = None  # Safe fallback

        # Select the unit (for placement highlights)
        self._selected_unit_index = idx

        return f"drag_start:{idx}"

    def handle_mouse_move(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> None:
        """Handle mouse movement while dragging - update ghost position."""
        if not self._is_dragging or self._dragging_unit is None:
            return

        self._drag_current_pos = (screen_x, screen_y)

    def handle_mouse_up(
        self,
        screen_x: int,
        screen_y: int,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> str | None:
        """Handle mouse button UP - complete drag (place or cancel)."""
        if not self._is_dragging or self._dragging_unit is None:
            return None

        result = None

        # Try to place at current position if over map
        if screen_x >= self._roster_width:
            map_pos = self.screen_to_map(screen_x, screen_y, map_offset_x, map_offset_y, tile_size)

            if map_pos is not None and self._dragging_unit_index is not None:
                map_x, map_y = map_pos

                # Check if valid placement
                terrain = self._get_terrain_at(map_x, map_y)
                can_place = (
                    self.can_place_at(self._dragging_unit, map_x, map_y, terrain)
                    and not any(pu.position == (map_x, map_y) for pu in self._state.placed_units)
                    and self._dragging_unit.deployment_cost <= self.requisition_remaining
                )

                if can_place:
                    # SUCCESS: Place the unit
                    if self.place_unit(self._dragging_unit_index, map_x, map_y):
                        result = f"place_unit:{self._dragging_unit_index}"
                    else:
                        result = "place_failed"
                else:
                    # Invalid zone - cancel with feedback
                    result = "invalid_placement"
        else:
            # Dropped back on roster or off-map - just cancel
            result = "drag_cancelled"

        # Clear drag state
        self._clear_drag_state()

        return result

    def _clear_drag_state(self) -> None:
        """Clear all drag-and-drop state."""
        self._dragging_unit = None
        self._dragging_unit_index = None
        self._drag_start_pos = None
        self._drag_current_pos = None
        self._ghost_surface = None
        self._is_dragging = False
        # Don't clear selection - let user click again if needed

    def _create_ghost_surface(self, unit: DeploymentUnit) -> pygame.Surface | None:
        """Create a semi-transparent ghost sprite for dragged unit."""
        if not _pygame_available:
            return None

        try:
            size = 48
            ghost = pygame.Surface((size, size), pygame.SRCALPHA)

            # Unit type colors (matching placed units)
            type_colors = {
                "vehicle": (220, 180, 50),
                "support": (100, 180, 220),
                "recon": (180, 140, 220),
                "infantry": (80, 220, 80),
            }
            color = type_colors.get(unit.unit_type, (200, 200, 200))

            # Draw hexagon shape (like placed units)
            cx, cy = size // 2, size // 2
            radius = size // 3
            points = []
            for i in range(6):
                angle = math.pi / 3 * i - math.pi / 6
                x = cx + int(radius * math.cos(angle))
                y = cy + int(radius * math.sin(angle))
                points.append((x, y))

            # Semi-transparent fill (alpha=150)
            ghost.fill((0, 0, 0, 0))
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.polygon(s, (*color, 150), points)
            pygame.draw.polygon(s, (*color, 200), points, 2)
            ghost.blit(s, (0, 0))

            # Add unit name label
            if self._font_small:
                label = self._font_small.render(unit.display_name[:4], True, (255, 255, 255, 200))
                label.set_alpha(200)
                ghost.blit(label, (cx - label.get_width() // 2, cy - radius - 12))

            return ghost
        except (pygame.error, ValueError, TypeError) as e:
            logging.debug("Ghost surface rendering failed: %s", e)
            return None

    def _render_unit_details_panel(self, screen: pygame.Surface) -> None:
        """Render detailed unit information panel on the RIGHT side of screen."""
        return self._renderer._render_unit_details_panel(screen)

    def _render_drag_feedback(
        self,
        screen: pygame.Surface,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> None:
        """Render drag visual feedback: ghost unit + tile highlights."""
        return self._renderer._render_drag_feedback(screen, map_offset_x, map_offset_y, tile_size)

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

        This is the preferred entry point for integration with the game loop.
        Supports both left-click (place/select) and right-click (remove).
        """
        if self._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return None

        # Handle right-click for removal
        if right_click:
            return self.handle_right_click(
                screen_x, screen_y, map_offset_x, map_offset_y, tile_size
            )

        # Check Start Battle button
        if self._button_rect and self._is_in_button(screen_x, screen_y):
            if self.is_deployment_complete():
                return "begin_battle"
            return None

        # Check detail panel button (PLACE ON MAP / REMOVE FROM MAP)
        if hasattr(self, "_detail_panel_btn_rect") and self._detail_panel_btn_rect:
            btn_x, btn_y, btn_w, btn_h = self._detail_panel_btn_rect
            if btn_x <= screen_x <= btn_x + btn_w and btn_y <= screen_y <= btn_y + btn_h:
                # Button was clicked!
                action = getattr(self, "_detail_panel_btn_action", None)
                if action == "remove" and self._selected_unit_index is not None:
                    # Execute remove
                    unit = self._state.available_units[self._selected_unit_index]
                    if unit.is_placed and unit.position is not None:
                        pos_x, pos_y = unit.position[0], unit.position[1]
                        self.remove_unit(pos_x, pos_y)
                        return f"detail_panel_remove:{pos_x},{pos_y}"
                elif action == "place" and self._selected_unit_index is not None:
                    # For place, just return - the user should drag to map
                    return "detail_panel_place_requested"

        # Check roster panel (LEFT side)
        if screen_x < self._roster_width:
            idx = self._roster_index_at(screen_x, screen_y)
            if idx is not None and 0 <= idx < len(self._state.available_units):
                unit = self._state.available_units[idx]
                if not unit.is_placed:
                    # Select unplaced unit for deployment
                    self._selected_unit_index = idx
                    return f"select_unit:{idx}"
                else:
                    # Click placed unit in roster → just select it (DO NOT auto-remove)
                    # This prevents accidental removal. User must right-click to remove.
                    self._selected_unit_index = idx
                    return f"view_placed_unit:{idx}"
            return None

        # Map click
        map_pos = self.screen_to_map(screen_x, screen_y, map_offset_x, map_offset_y, tile_size)
        if map_pos is None:
            return None

        map_x, map_y = map_pos

        # If a unit is selected, try to place
        if self._selected_unit_index is not None:
            if self.place_unit(self._selected_unit_index, map_x, map_y):
                return f"place_unit:{self._selected_unit_index}"
            return None

        # Otherwise, try to remove a placed unit at this position
        if self.remove_unit(map_x, map_y):
            return f"remove_unit:{map_x},{map_y}"

        return None

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
