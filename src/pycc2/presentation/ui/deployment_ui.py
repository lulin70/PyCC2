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

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

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
# ENUMS & DATA CLASSES
# ========================================================================


class DeploymentPhase(Enum):
    """Phases of the deployment workflow."""

    PLANNING = auto()
    DEPLOYING = auto()
    READY = auto()
    ACTIVE = auto()


class ZoneType(Enum):
    """Map zone classification during deployment."""

    FRIENDLY = auto()
    NO_MANS_LAND = auto()
    ENEMY_CONTROLLED = auto()


# Unit category for roster grouping
class UnitCategory(Enum):
    INFANTRY = "infantry"
    SUPPORT = "support"
    ARMOR = "vehicle"
    RECON = "recon"


# Category display labels and icons
_CATEGORY_INFO: dict[UnitCategory, tuple[str, str]] = {
    UnitCategory.INFANTRY: ("INFANTRY", "♟"),
    UnitCategory.SUPPORT: ("SUPPORT (MG/AT)", "⚔"),
    UnitCategory.ARMOR: ("ARMOR", "▣"),
    UnitCategory.RECON: ("RECON", "◉"),
}

# Mapping from unit_type string to UnitCategory
_UNIT_TYPE_TO_CATEGORY: dict[str, UnitCategory] = {
    "infantry": UnitCategory.INFANTRY,
    "support": UnitCategory.SUPPORT,
    "vehicle": UnitCategory.ARMOR,
    "recon": UnitCategory.RECON,
}


# Terrain type constants (mirrors TerrainType int values for standalone use)
TERRAIN_OPEN = 0
TERRAIN_ROAD = 1
TERRAIN_GRASS = 2
TERRAIN_WOODS = 3
TERRAIN_BUILDING_ENTERABLE = 4
TERRAIN_BUILDING_SOLID = 5
TERRAIN_WATER = 6
TERRAIN_HEDGE = 7
TERRAIN_WALL = 8
TERRAIN_ROUGH = 9
TERRAIN_SHALLOW = 10
TERRAIN_BRIDGE = 11
TERRAIN_CRATER = 12
TERRAIN_SWAMP = 13

_BUILDING_TERRAINS = {TERRAIN_BUILDING_ENTERABLE, TERRAIN_BUILDING_SOLID}
_DEEP_WATER_TERRAINS = {TERRAIN_WATER}
_SHALLOW_WATER_TERRAINS = {TERRAIN_SHALLOW}
_IMPASSABLE_TERRAINS = {TERRAIN_BUILDING_SOLID, TERRAIN_WATER, TERRAIN_WALL}


@dataclass
class DeploymentUnit:
    """A single deployable unit entry in the roster."""

    unit_template_id: str
    display_name: str
    unit_type: str  # 'infantry', 'support', 'vehicle', 'recon'
    deployment_cost: int
    position: tuple[int, int] | None = None  # None = not yet placed
    is_placed: bool = False

    @property
    def category(self) -> UnitCategory:
        return _UNIT_TYPE_TO_CATEGORY.get(self.unit_type, UnitCategory.INFANTRY)


@dataclass
class DeploymentState:
    """Full state of the deployment phase for one player."""

    phase: DeploymentPhase = DeploymentPhase.PLANNING
    available_units: list[DeploymentUnit] = field(default_factory=list)
    placed_units: list[DeploymentUnit] = field(default_factory=list)
    max_infantry: int = 15  # Increased from 9 for better gameplay
    max_support: int = 10  # Increased from 6 for better gameplay
    requisition_points: int = 0
    requisition_points_spent: int = 0
    friendly_zone: list[tuple[int, int]] = field(default_factory=list)
    enemy_zone: list[tuple[int, int]] = field(default_factory=list)
    no_mans_land: list[tuple[int, int]] = field(default_factory=list)


# ========================================================================
# ZONE OVERLAY COLOURS (R, G, B, A)
# ========================================================================

_ZONE_COLORS: dict[ZoneType, tuple[int, int, int, int]] = {
    ZoneType.FRIENDLY: (0, 180, 0, 50),
    ZoneType.NO_MANS_LAND: (140, 140, 140, 40),
    ZoneType.ENEMY_CONTROLLED: (200, 40, 40, 50),
}

_ZONE_BORDER_COLORS: dict[ZoneType, tuple[int, int, int]] = {
    ZoneType.FRIENDLY: (0, 220, 0),
    ZoneType.NO_MANS_LAND: (160, 160, 160),
    ZoneType.ENEMY_CONTROLLED: (220, 60, 60),
}

_VALID_PLACEMENT_COLOR = (0, 255, 100, 70)
_INVALID_PLACEMENT_COLOR = (255, 60, 60, 50)
_SELECTED_UNIT_HIGHLIGHT = (255, 255, 0)

_ROSTER_BG = (30, 34, 42, 230)
_ROSTER_BORDER = (80, 84, 92)
_ROSTER_TEXT = (230, 230, 230)
_ROSTER_TEXT_DIM = (150, 150, 150)
_ROSTER_SELECTED_BG = (60, 90, 140, 200)
_ROSTER_PLACED_BG = (40, 70, 40, 180)
_ROSTER_CATEGORY_BG = (45, 50, 60, 200)
_ROSTER_CATEGORY_TEXT = (180, 170, 130)

_BUTTON_BG_NORMAL = (70, 74, 82)
_BUTTON_BG_HOVER = (90, 94, 102)
_BUTTON_BG_DISABLED = (45, 48, 55)
_BUTTON_BORDER = (100, 104, 112)
_BUTTON_TEXT = (220, 220, 220)
_BUTTON_TEXT_DISABLED = (120, 120, 120)
_BUTTON_ACTIVE_BG = (40, 120, 40)

_RP_COLOR = (200, 180, 100)
_RP_SPENT_COLOR = (180, 100, 100)


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

        # Roster panel geometry (LEFT side)
        self._roster_width: int = 240
        self._roster_padding: int = 6
        self._roster_item_height: int = 28
        self._roster_category_height: int = 24

        # Begin Battle button
        self._button_rect: tuple[int, int, int, int] | None = None
        self._button_hovered: bool = False

        # Pygame font cache
        self._font_small: Any = None
        self._font_normal: Any = None
        self._font_large: Any = None

        # Overlay surface cache (rebuilt when zones change)
        self._overlay_cache: Any = None
        self._overlay_tile_size: int = 0

        # Roster layout cache (rebuilt when units change)
        self._roster_layout: list[tuple[str, int]] = field(default_factory=list)
        # Each entry: ("category", -1) or ("unit", index)

        # === Drag-and-drop state (Issue 3) ===
        self._dragging_unit: DeploymentUnit | None = None
        self._dragging_unit_index: int | None = None
        self._drag_start_pos: tuple[int, int] | None = None
        self._drag_current_pos: tuple[int, int] | None = None
        self._ghost_surface: Any = None  # Pre-rendered ghost sprite
        self._is_dragging: bool = False

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
        """Handle a right-click to remove a placed unit from the map.

        Returns ``"remove_unit:<x>,<y>"`` or None.
        """
        if self._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return None

        # Right-click on roster → deselect
        if screen_x < self._roster_width:
            self._selected_unit_index = None
            return None

        # Right-click on map → remove unit
        map_pos = self.screen_to_map(
            screen_x, screen_y, map_offset_x, map_offset_y, tile_size
        )
        if map_pos is None:
            return None

        map_x, map_y = map_pos
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
        except Exception as e:
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
        if terrain == TERRAIN_WATER or terrain == TERRAIN_BUILDING_SOLID:
            return False

        # Check 3: Everything else is ALLOWED!
        # No more restrictions on roads, rough terrain, buildings, hedges, etc.
        return True

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

        infantry_count = sum(
            1 for u in self._state.placed_units if u.unit_type == "infantry"
        )
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
        }

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(
        self,
        screen: Any,
        font: Any,
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

        # 1. Zone overlays (using RENDERING offset)
        self._render_zone_overlays(screen, actual_map_offset_x, actual_map_offset_y, tile_size)

        # 2. Valid placement highlights (when a unit is selected)
        if self._selected_unit_index is not None:
            self._render_placement_highlights(
                screen, actual_map_offset_x, actual_map_offset_y, tile_size
            )

        # 3. Placed unit markers (using RENDERING offset)
        self._render_placed_units(screen, actual_map_offset_x, actual_map_offset_y, tile_size)

        # 4. Force pool panel (left side) - drawn at (0, 0)
        self._render_roster(screen)

        # 5. Requisition points counter (TOP of screen - prominent location)
        self._render_requisition_points(screen)

        # 6. Start Battle button (at bottom of roster panel)
        self._render_start_battle_button(screen)

        # 7. Unit details panel (right side) - when unit selected
        if self._selected_unit_index is not None:
            self._render_unit_details_panel(screen)

        # 8. Drag-and-drop visual feedback (using CLICK DETECTION offset for proper alignment)
        self._render_drag_feedback(screen, click_map_offset_x, click_map_offset_y, tile_size)

    # ------------------------------------------------------------------
    # Internal – zone overlays
    # ------------------------------------------------------------------

    def _render_zone_overlays(
        self,
        screen: Any,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        if self._zone_map is None:
            return

        # Build / rebuild overlay cache if tile size changed
        if self._overlay_cache is None or self._overlay_tile_size != ts:
            total_w = self._map_width * ts
            total_h = self._map_height * ts
            overlay = pygame.Surface((total_w, total_h), pygame.SRCALPHA)

            for y in range(self._map_height):
                for x in range(self._map_width):
                    zone = self._zone_map[y][x]
                    color = _ZONE_COLORS[zone]
                    rect = pygame.Rect(x * ts, y * ts, ts, ts)
                    pygame.draw.rect(overlay, color, rect)

                    # Draw thin zone border for friendly and enemy
                    if zone in (ZoneType.FRIENDLY, ZoneType.ENEMY_CONTROLLED):
                        border_color = _ZONE_BORDER_COLORS[zone]
                        pygame.draw.rect(overlay, (*border_color, 80), rect, 1)

            self._overlay_cache = overlay
            self._overlay_tile_size = ts

        screen.blit(self._overlay_cache, (ox, oy))

    # ------------------------------------------------------------------
    # Internal – placement highlights
    # ------------------------------------------------------------------

    def _render_placement_highlights(
        self,
        screen: Any,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        if self._selected_unit_index is None:
            return
        if self._selected_unit_index >= len(self._state.available_units):
            return

        unit = self._state.available_units[self._selected_unit_index]
        if unit.is_placed:
            return

        # Skip if not enough requisition points
        if unit.deployment_cost > self.requisition_remaining:
            return

        highlight_surf = pygame.Surface((ts, ts), pygame.SRCALPHA)

        for y in range(self._map_height):
            for x in range(self._map_width):
                terrain = self._get_terrain_at(x, y)
                if self.can_place_at(unit, x, y, terrain):
                    # Check not already occupied
                    occupied = any(
                        pu.position == (x, y) for pu in self._state.placed_units
                    )
                    if not occupied:
                        highlight_surf.fill(_VALID_PLACEMENT_COLOR)
                        screen.blit(highlight_surf, (ox + x * ts, oy + y * ts))

    # ------------------------------------------------------------------
    # Internal – placed unit markers
    # ------------------------------------------------------------------

    def _render_placed_units(
        self,
        screen: Any,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        """Render placed units with DISTINCT SHAPES for each type (CC2 style)."""
        for pu in self._state.placed_units:
            if pu.position is None:
                continue
            px, py = pu.position
            cx = ox + px * ts + ts // 2
            cy = oy + py * ts + ts // 2

            # Base size depends on unit type
            if pu.unit_type == "vehicle":
                radius = max(ts // 2, 8)  # Larger for vehicles
            elif pu.unit_type == "recon":
                radius = max(ts // 4, 4)  # Smaller for recon
            else:
                radius = max(ts // 3, 5)  # Normal for infantry/support

            # Draw shape based on unit type
            if pu.unit_type == "infantry":
                # CIRCLE - Infantry (green tones)
                color = (80, 200, 80)
                pygame.draw.circle(screen, color, (cx, cy), radius)
                pygame.draw.circle(screen, (255, 255, 255), (cx, cy), radius, 2)
                
                # Add soldier icon hint (small dot in center)
                pygame.draw.circle(screen, (40, 120, 40), (cx, cy), radius // 3)
                
            elif pu.unit_type == "support":
                # TRIANGLE - Support/MG/AT (blue tones)
                color = (100, 180, 220)
                points = []
                for i in range(3):
                    angle = math.pi / 3 * 2 * i - math.pi / 2
                    x = cx + int(radius * math.cos(angle))
                    y = cy + int(radius * math.sin(angle))
                    points.append((x, y))
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, (255, 255, 255), points, 2)
                
            elif pu.unit_type == "vehicle":
                # HEXAGON/DIAMOND - Armor/Tanks (orange/yellow tones)
                color = (220, 180, 50)
                points = []
                for i in range(6):
                    angle = math.pi / 3 * i
                    x = cx + int(radius * math.cos(angle))
                    y = cy + int(radius * math.sin(angle))
                    points.append((x, y))
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, (255, 220, 100), points, 2)
                
                # Add tank turret hint (small circle on top)
                pygame.draw.circle(screen, (180, 140, 30), (cx, cy - radius // 3), radius // 3)
                
            elif pu.unit_type == "recon":
                # SMALL DIAMOND - Recon/Sniper (purple tones)
                color = (180, 140, 220)
                half = radius // 2
                points = [
                    (cx, cy - radius),
                    (cx + half, cy),
                    (cx, cy + radius),
                    (cx - half, cy),
                ]
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, (220, 180, 255), points, 1)
            else:
                # DEFAULT: Square for unknown types
                color = (200, 200, 200)
                rect = pygame.Rect(cx - radius//2, cy - radius//2, radius, radius)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (255, 255, 255), rect, 1)

            # Unit label (abbreviated name)
            if self._font_small and ts >= 16:
                label_text = pu.display_name[:4] if len(pu.display_name) > 4 else pu.display_name
                label = self._font_small.render(label_text, True, (255, 255, 255))
                label_x = cx - label.get_width() // 2
                label_y = cy + radius + 2
                # Background for readability
                bg_rect = pygame.Rect(label_x - 2, label_y - 1, label.get_width() + 4, label.get_height() + 2)
                pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect, border_radius=2)
                screen.blit(label, (label_x, label_y))

    # ------------------------------------------------------------------
    # Internal – force pool panel (LEFT side)
    # ------------------------------------------------------------------

    def _rebuild_roster_layout(self) -> None:
        """Rebuild the roster layout with category headers."""
        self._roster_layout = []

        # Group units by category
        categories_order = [UnitCategory.INFANTRY, UnitCategory.SUPPORT, UnitCategory.ARMOR, UnitCategory.RECON]
        units_by_category: dict[UnitCategory, list[int]] = {cat: [] for cat in categories_order}

        for i, unit in enumerate(self._state.available_units):
            cat = unit.category
            units_by_category[cat].append(i)

        for cat in categories_order:
            indices = units_by_category[cat]
            if not indices:
                continue
            self._roster_layout.append(("category", cat))
            for idx in indices:
                self._roster_layout.append(("unit", idx))

    def _render_roster(self, screen: Any) -> None:
        roster_h = self.height

        # Background
        panel_surf = pygame.Surface((self._roster_width, roster_h), pygame.SRCALPHA)
        pygame.draw.rect(
            panel_surf,
            _ROSTER_BG,
            (0, 0, self._roster_width, roster_h),
            border_radius=0,
        )
        pygame.draw.rect(
            panel_surf,
            _ROSTER_BORDER,
            (0, 0, self._roster_width, roster_h),
            width=1,
        )

        # Title
        if self._font_normal:
            title = self._font_normal.render("FORCE POOL", True, _ROSTER_TEXT)
            panel_surf.blit(title, (self._roster_padding, 8))

        # DISABLED: RP header moved to TOP of screen (more prominent)
        # self._render_rp_header(panel_surf)

        # Scrollable unit list with category headers (start right after title)
        y_offset = 30  # Start early, no RP header taking space
        for entry_type, entry_data in self._roster_layout:
            if entry_type == "category":
                cat: UnitCategory = entry_data
                label_text, icon = _CATEGORY_INFO[cat]
                cat_rect = pygame.Rect(
                    self._roster_padding,
                    y_offset,
                    self._roster_width - 2 * self._roster_padding,
                    self._roster_category_height,
                )
                pygame.draw.rect(panel_surf, _ROSTER_CATEGORY_BG, cat_rect, border_radius=3)
                if self._font_small:
                    cat_label = self._font_small.render(
                        f" {icon} {label_text}", True, _ROSTER_CATEGORY_TEXT
                    )
                    panel_surf.blit(cat_label, (cat_rect.x + 2, cat_rect.y + 4))
                y_offset += self._roster_category_height + 2

            elif entry_type == "unit":
                idx: int = entry_data
                unit = self._state.available_units[idx]
                item_rect = pygame.Rect(
                    self._roster_padding,
                    y_offset,
                    self._roster_width - 2 * self._roster_padding,
                    self._roster_item_height,
                )

                # Background
                if idx == self._selected_unit_index:
                    bg = _ROSTER_SELECTED_BG
                elif unit.is_placed:
                    bg = _ROSTER_PLACED_BG
                else:
                    bg = (50, 54, 62, 150)

                pygame.draw.rect(panel_surf, bg, item_rect, border_radius=4)

                # Text
                if self._font_small:
                    name_color = _ROSTER_TEXT if not unit.is_placed else _ROSTER_TEXT_DIM
                    prefix = "✓ " if unit.is_placed else "  "
                    text = f"{prefix}{unit.display_name}"
                    label = self._font_small.render(text, True, name_color)
                    panel_surf.blit(label, (item_rect.x + 4, item_rect.y + 6))

                    # Cost
                    cost_text = f"{unit.deployment_cost}pts"
                    cost_color = _RP_COLOR if not unit.is_placed else _RP_SPENT_COLOR
                    cost_label = self._font_small.render(cost_text, True, cost_color)
                    panel_surf.blit(
                        cost_label,
                        (item_rect.right - cost_label.get_width() - 4, item_rect.y + 6),
                    )

                y_offset += self._roster_item_height + 2

        screen.blit(panel_surf, (0, 0))

    # ------------------------------------------------------------------
    # Internal – requisition points HEADER with progress bar (Issue 2)
    # ------------------------------------------------------------------

    def _render_rp_header(self, panel_surf: Any) -> None:
        """Render prominent requisition points display with visual progress bar."""
        if not _pygame_available or panel_surf is None:
            return

        remaining = self.requisition_remaining
        total = self._state.requisition_points

        if total <= 0:
            return

        # Section background
        header_bg_y = 32
        header_h = 80
        pygame.draw.rect(
            panel_surf,
            (40, 44, 52, 240),
            (4, header_bg_y, self._roster_width - 8, header_h),
            border_radius=6,
        )
        pygame.draw.rect(
            panel_surf,
            (70, 74, 82),
            (4, header_bg_y, self._roster_width - 8, header_h),
            width=1,
            border_radius=6,
        )

        # "REQUISITION POINTS" label
        if self._font_small:
            label = self._font_small.render("REQUISITION POINTS", True, (180, 170, 130))
            panel_surf.blit(label, (self._roster_padding + 4, header_bg_y + 6))

        # Large RP value: "RP: 850 / 1200"
        if self._font_large:
            rp_text = f"RP: {remaining} / {total}"

            # Color based on remaining percentage
            ratio = remaining / total
            if ratio > 0.5:
                rp_color = (100, 220, 100)      # Green - plenty
            elif ratio > 0.25:
                rp_color = (230, 200, 80)       # Yellow - getting low
            elif ratio > 0:
                rp_color = (230, 140, 80)       # Orange - very low
            else:
                rp_color = (230, 80, 80)        # Red - over budget!

            rp_label = self._font_large.render(rp_text, True, rp_color)
            panel_surf.blit(rp_label, (self._roster_padding + 4, header_bg_y + 26))

        # === Visual Progress Bar (200px wide, 20px tall) ===
        bar_x = self._roster_padding + 4
        bar_y = header_bg_y + 58
        bar_w = min(200, self._roster_width - 16)
        bar_h = 20

        # Bar background (dark)
        pygame.draw.rect(
            panel_surf,
            (30, 30, 35),
            (bar_x, bar_y, bar_w, bar_h),
            border_radius=4,
        )

        # Calculate filled width
        spent = total - remaining
        fill_ratio = min(1.0, max(0.0, spent / total)) if total > 0 else 0
        fill_w = int(bar_w * fill_ratio)

        if fill_w > 0:
            # Bar color based on remaining ratio
            ratio = remaining / total if total > 0 else 0
            if ratio > 0.5:
                bar_color = (60, 180, 60)       # Green
                bar_border = (80, 220, 80)
            elif ratio > 0.25:
                bar_color = (200, 180, 50)      # Yellow
                bar_border = (230, 210, 70)
            elif ratio > 0:
                bar_color = (210, 130, 50)      # Orange
                bar_border = (240, 160, 70)
            else:
                bar_color = (200, 60, 60)       # Red
                bar_border = (230, 90, 90)

            # Filled portion
            pygame.draw.rect(
                panel_surf,
                bar_color,
                (bar_x, bar_y, fill_w, bar_h),
                border_radius=4,
            )

            # Shine effect (lighter top edge)
            if fill_w > 2:
                pygame.draw.line(
                    panel_surf,
                    bar_border,
                    (bar_x + 1, bar_y + 1),
                    (bar_x + fill_w - 1, bar_y + 1),
                    2,
                )

        # Border around entire bar
        pygame.draw.rect(
            panel_surf,
            (90, 94, 102),
            (bar_x, bar_y, bar_w, bar_h),
            width=1,
            border_radius=4,
        )

    # ------------------------------------------------------------------
    # Internal – requisition points (original simple version, now supplemental)
    # ------------------------------------------------------------------

    def _render_requisition_points(self, screen: Any) -> None:
        """Render a prominent RP counter at the top of the screen (above roster panel)."""
        if not _pygame_available or screen is None:
            return

        remaining = self.requisition_remaining
        total = self._state.requisition_points

        if total <= 0 or not self._font_large:
            return

        # Create a prominent top bar for RP display
        bar_height = 50
        bar_y = 5  # Near top of screen

        # Background panel
        panel_w = min(350, self._roster_width + 20)
        panel_x = (self._roster_width - panel_w) // 2 + 5
        if panel_x < 0:
            panel_x = 5

        # Semi-transparent background
        bg_surf = pygame.Surface((panel_w, bar_height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (30, 35, 45, 230), (0, 0, panel_w, bar_height), border_radius=8)
        pygame.draw.rect(bg_surf, (80, 85, 100), (0, 0, panel_w, bar_height), width=2, border_radius=8)

        # "REQUISITION POINTS" label (small, top)
        if self._font_small:
            label = self._font_small.render("◆ REQUISITION POINTS", True, (200, 190, 140))
            bg_surf.blit(label, ((panel_w - label.get_width()) // 2, 6))

        # Large RP value: "850 / 1200"
        rp_text = f"⬢ {remaining} / {total}"

        # Color based on remaining percentage
        ratio = remaining / total if total > 0 else 0
        if ratio > 0.6:
            rp_color = (100, 230, 100)      # Green - plenty
        elif ratio > 0.3:
            rp_color = (240, 220, 80)       # Yellow - getting low
        elif ratio > 0.1:
            rp_color = (245, 150, 70)       # Orange - very low
        elif ratio > 0:
            rp_color = (245, 90, 90)        # Red - critical!
        else:
            rp_color = (255, 60, 60)        # Dark red - over budget!

        rp_label = self._font_large.render(rp_text, True, rp_color)
        bg_surf.blit(rp_label, ((panel_w - rp_label.get_width()) // 2, 26))

        # Blit to screen
        screen.blit(bg_surf, (panel_x, bar_y))

    # ------------------------------------------------------------------
    # Internal – unit counts
    # ------------------------------------------------------------------

    def _render_unit_counts(self, screen: Any) -> None:
        infantry_count = sum(
            1 for u in self._state.placed_units if u.unit_type == "infantry"
        )
        support_count = sum(
            1 for u in self._state.placed_units if u.unit_type in ("support", "vehicle")
        )

        if not self._font_normal:
            return

        inf_color = _ROSTER_TEXT if infantry_count < self._state.max_infantry else _RP_SPENT_COLOR
        sup_color = _ROSTER_TEXT if support_count < self._state.max_support else _RP_SPENT_COLOR

        inf_label = self._font_small.render(
            f"Infantry: {infantry_count}/{self._state.max_infantry}", True, inf_color
        )
        sup_label = self._font_small.render(
            f"Support: {support_count}/{self._state.max_support}", True, sup_color
        )

        screen.blit(inf_label, (self._roster_padding, self.height - 75))
        screen.blit(sup_label, (self._roster_padding + 110, self.height - 75))

    # ------------------------------------------------------------------
    # Internal – Start Battle button
    # ------------------------------------------------------------------

    def _render_start_battle_button(self, screen: Any) -> None:
        """Render prominent START BATTLE button - make it VERY visible and accessible."""
        btn_w = self._roster_width - 2 * self._roster_padding
        btn_h = 52  # Extra tall for visibility
        btn_x = self._roster_padding
        
        # Position at bottom of roster panel, but ensure it's on screen
        # Leave some margin from actual screen bottom
        max_y = screen.get_height() - 70 if screen.get_height() > 0 else 500
        btn_y = min(self.height - 60, max_y)

        self._button_rect = (btn_x, btn_y, btn_w, btn_h)

        enabled = self.is_deployment_complete()

        if enabled:
            # Bright green when ready - hard to miss
            bg = (40, 160, 60) if not self._button_hovered else (50, 200, 70)
            border_color = (100, 255, 120)
            # Pulsing effect when enabled (draw attention)
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.003)) * 20
            bg = (int(40 + pulse), int(160 + pulse), 60)
        else:
            bg = (60, 60, 65)  # Dark gray when disabled
            border_color = (90, 90, 95)

        rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        
        # Draw shadow for depth
        shadow_rect = pygame.Rect(btn_x + 3, btn_y + 3, btn_w, btn_h)
        pygame.draw.rect(screen, (15, 15, 20), shadow_rect, border_radius=10)
        
        # Draw main button with gradient-like effect
        pygame.draw.rect(screen, bg, rect, border_radius=10)
        
        # Highlight top edge for 3D effect
        highlight_rect = pygame.Rect(btn_x + 2, btn_y + 2, btn_w - 4, btn_h // 3)
        highlight_color = tuple(min(255, c + 30) for c in bg) if enabled else bg
        pygame.draw.rect(screen, highlight_color, highlight_rect, border_radius=8)
        
        # Border
        pygame.draw.rect(screen, border_color, rect, width=3, border_radius=10)

        if self._font_normal:
            text_color = (255, 255, 255) if enabled else (140, 140, 145)
            
            # Large bold text
            try:
                battle_font = pygame.font.Font(None, 26)
            except Exception:
                battle_font = self._font_normal
                
            label = battle_font.render("⚔ START BATTLE", True, text_color)
            
            # Center text
            text_x = btn_x + (btn_w - label.get_width()) // 2
            text_y = btn_y + (btn_h - label.get_height()) // 2
            screen.blit(label, (text_x, text_y))

        # Show placement count hint below button
        if self._font_small:
            placed_count = len(self._state.placed_units)
            total_units = len(self._state.available_units)
            hint_text = f"Units: {placed_count} placed"
            if not enabled:
                hint_text += " (need ≥1)"
            hint_label = self._font_small.render(hint_text, True, (150, 150, 155))
            screen.blit(hint_label, (btn_x, btn_y + btn_h + 5))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_in_friendly_zone(self, x: int, y: int) -> bool:
        if self._zone_map is None:
            return False
        if not (0 <= x < self._map_width and 0 <= y < self._map_height):
            return False
        return self._zone_map[y][x] == ZoneType.FRIENDLY

    def _get_terrain_at(self, x: int, y: int) -> int:
        if self._tile_grid is None:
            return TERRAIN_OPEN
        if not (0 <= y < len(self._tile_grid) and 0 <= x < len(self._tile_grid[0])):
            return TERRAIN_OPEN
        return int(self._tile_grid[y][x])

    def _check_unit_limits(self, unit: DeploymentUnit) -> bool:
        infantry_count = sum(
            1 for u in self._state.placed_units if u.unit_type == "infantry"
        )
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
        except Exception as e:
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
            map_pos = self.screen_to_map(
                screen_x, screen_y, map_offset_x, map_offset_y, tile_size
            )

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

    def _create_ghost_surface(self, unit: DeploymentUnit) -> Any:
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
        except Exception:
            return None

    def _render_unit_details_panel(self, screen: Any) -> None:
        """Render detailed unit information panel on the RIGHT side of screen."""
        if self._selected_unit_index is None or self._selected_unit_index >= len(self._state.available_units):
            return

        unit = self._state.available_units[self._selected_unit_index]

        # Panel dimensions (right side of screen)
        panel_w = 220
        panel_h = 300
        panel_x = screen.get_width() - panel_w - 10
        panel_y = 80

        # Background
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (25, 28, 35, 240), (0, 0, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(panel_surf, (70, 75, 90), (0, 0, panel_w, panel_h), width=2, border_radius=8)

        # Title bar (simple rectangle - pygame doesn't support per-corner radius)
        title_bar_rect = pygame.Rect(0, 0, panel_w, 32)
        pygame.draw.rect(panel_surf, (40, 45, 55), title_bar_rect)

        # Unit name (title)
        if self._font_normal:
            name_text = unit.display_name[:18] + "..." if len(unit.display_name) > 18 else unit.display_name
            title_label = self._font_normal.render(name_text, True, (255, 230, 150))
            panel_surf.blit(title_label, (10, 7))

        y_offset = 40
        line_height = 22

        # Unit type badge
        if self._font_small:
            type_badge = f"[{unit.unit_type.upper()}]"
            type_color = {
                "infantry": (100, 220, 100),
                "support": (100, 180, 220),
                "vehicle": (220, 180, 50),
                "recon": (180, 140, 220)
            }.get(unit.unit_type, (200, 200, 200))
            type_label = self._font_small.render(type_badge, True, type_color)
            panel_surf.blit(type_label, (10, y_offset))
            y_offset += line_height + 5

        # Separator
        pygame.draw.line(panel_surf, (60, 65, 75), (10, y_offset), (panel_w - 10, y_offset), 1)
        y_offset += 10

        # Unit details
        details = [
            ("Cost", f"{unit.deployment_cost} RP"),
            ("Status", "PLACED" if unit.is_placed else "AVAILABLE"),
            ("Position", f"({unit.position[0]}, {unit.position[1]})" if unit.position else "None"),
            ("Category", unit.category.value if hasattr(unit.category, 'value') else str(unit.category)),
        ]

        for label, value in details:
            if self._font_small:
                # Label (left side, dimmed)
                lbl = self._font_small.render(f"{label}:", True, (160, 165, 175))
                panel_surf.blit(lbl, (10, y_offset))
                
                # Value (right side, bright)
                val = self._font_small.render(value, True, (220, 225, 235))
                panel_surf.blit(val, (120, y_offset))
                
                y_offset += line_height

        # Action buttons at bottom - SAVE BUTTON RECT FOR CLICK DETECTION!
        y_offset = panel_h - 60
        
        btn_w = panel_w - 20
        btn_h = 30
        
        if not unit.is_placed:
            btn_color = (50, 130, 70)
            btn_text = "PLACE ON MAP"
            btn_action = "place"
        else:
            btn_color = (150, 60, 60)
            btn_text = "REMOVE FROM MAP"
            btn_action = "remove"
            
        btn_rect = pygame.Rect(10, y_offset, btn_w, btn_h)
        
        # CRITICAL: Save button rect for click detection in handle_click_full!
        self._detail_panel_btn_rect = (panel_x + btn_rect.x, panel_y + btn_rect.y, btn_rect.width, btn_rect.height)
        self._detail_panel_btn_action = btn_action
        
        pygame.draw.rect(panel_surf, btn_color, btn_rect, border_radius=5)
        pygame.draw.rect(panel_surf, (100, 105, 115), btn_rect, width=1, border_radius=5)
        
        if self._font_small:
            btn_label = self._font_small.render(btn_text, True, (255, 255, 255))
            btn_x = 10 + (btn_w - btn_label.get_width()) // 2
            btn_y = y_offset + (btn_h - btn_label.get_height()) // 2
            panel_surf.blit(btn_label, (btn_x, btn_y))

        # Blit panel to screen
        screen.blit(panel_surf, (panel_x, panel_y))

    def _render_drag_feedback(
        self,
        screen: Any,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> None:
        """Render drag visual feedback: ghost unit + tile highlights."""
        if not self._is_dragging or self._drag_current_pos is None:
            return

        if not _pygame_available or screen is None:
            return

        mx, my = self._drag_current_pos

        # === 1. Highlight tile under cursor ===
        if mx >= self._roster_width and self._dragging_unit is not None:
            map_pos = self.screen_to_map(mx, my, map_offset_x, map_offset_y, tile_size)

            if map_pos is not None:
                map_x, map_y = map_pos
                terrain = self._get_terrain_at(map_x, map_y)
                can_place = self.can_place_at(self._dragging_unit, map_x, map_y, terrain)

                # Check if occupied
                occupied = any(pu.position == (map_x, map_y) for pu in self._state.placed_units)

                # Check RP budget
                enough_rp = (
                    self._dragging_unit is not None and
                    self._dragging_unit.deployment_cost <= self.requisition_remaining
                )

                is_valid = can_place and not occupied and enough_rp

                # CRITICAL FIX: Highlight box must use ACTUAL screen position (including roster width)
                # The map visually starts at x=self._roster_width, so we MUST add it here!
                tile_screen_x = self._roster_width + map_offset_x + map_x * tile_size
                tile_screen_y = map_offset_y + map_y * tile_size

                if is_valid:
                    # Green glow for valid placement
                    highlight = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                    highlight.fill((0, 255, 100, 70))
                    screen.blit(highlight, (tile_screen_x, tile_screen_y))

                    # Bright green border
                    pygame.draw.rect(screen, (0, 255, 100), (
                        tile_screen_x, tile_screen_y, tile_size, tile_size
                    ), 2)
                else:
                    # Red glow for invalid placement
                    highlight = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                    highlight.fill((255, 60, 60, 50))
                    screen.blit(highlight, (tile_screen_x, tile_screen_y))

                    # Red border
                    pygame.draw.rect(screen, (255, 80, 80), (
                        tile_screen_x, tile_screen_y, tile_size, tile_size
                    ), 2)

        # === 2. Draw ghost unit following cursor ===
        if self._ghost_surface is not None:
            ghost_x = mx - self._ghost_surface.get_width() // 2
            ghost_y = my - self._ghost_surface.get_height() // 2
            screen.blit(self._ghost_surface, (ghost_x, ghost_y))

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
        if hasattr(self, '_detail_panel_btn_rect') and self._detail_panel_btn_rect:
            btn_x, btn_y, btn_w, btn_h = self._detail_panel_btn_rect
            if (btn_x <= screen_x <= btn_x + btn_w and 
                btn_y <= screen_y <= btn_y + btn_h):
                # Button was clicked!
                action = getattr(self, '_detail_panel_btn_action', None)
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
        map_pos = self.screen_to_map(
            screen_x, screen_y, map_offset_x, map_offset_y, tile_size
        )
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

    def _ensure_fonts(self, font: Any) -> None:
        """Initialise font objects if not already done."""
        if not _pygame_available:
            return
        # CRITICAL FIX: Always create default fonts even if font param is None!
        if self._font_normal is None:
            if font is not None:
                self._font_normal = font
            else:
                # Create default normal font (was missing - caused button text to not render!)
                try:
                    self._font_normal = pygame.font.Font(None, 20)
                except Exception:
                    self._font_normal = None
        if self._font_small is None:
            try:
                self._font_small = pygame.font.Font(None, 16)
            except Exception:
                self._font_small = None
        if self._font_large is None:
            try:
                self._font_large = pygame.font.Font(None, 32)
            except Exception:
                self._font_large = None

    @staticmethod
    def _build_default_roster() -> list[DeploymentUnit]:
        """Build a default unit roster for demonstration purposes."""
        return [
            # Infantry
            DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
            DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
            DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
            DeploymentUnit("us_assault_squad", "Assault Squad", "infantry", 145),
            DeploymentUnit("us_engineer_team", "Engineer Squad", "infantry", 140),
            # Support (MG/AT)
            DeploymentUnit("us_machine_gun_team", "MG Team (M1919A4)", "support", 160),
            DeploymentUnit("us_at_team", "AT Team (Bazooka)", "support", 150),
            DeploymentUnit("us_mortar_light", "Light Mortar (60mm)", "support", 140),
            DeploymentUnit("us_mortar_heavy", "Heavy Mortar (81mm)", "support", 175),
            DeploymentUnit("us_officer", "Officer / Commander", "support", 180),
            # Armor
            DeploymentUnit("us_sherman_m4", "M4 Sherman", "vehicle", 350),
            DeploymentUnit("us_stuart_m5", "M5 Stuart", "vehicle", 220),
            # Recon
            DeploymentUnit("us_scout_team", "Scout Team", "recon", 110),
            DeploymentUnit("us_sniper_team", "Sniper Team", "recon", 140),
        ]

    @staticmethod
    def build_force_pool_from_settings(
        faction: str = "allied",
        requisition_points: int = 2000,
    ) -> list[DeploymentUnit]:
        """Build a force pool based on faction and requisition points.

        Returns a list of DeploymentUnit entries that the player can
        choose from during deployment.  The cost of each unit counts
        against the player's requisition point budget.
        """
        if faction in ("allied", "ally"):
            return [
                # Infantry
                DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
                DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
                DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
                DeploymentUnit("us_assault_squad", "Assault Squad", "infantry", 145),
                DeploymentUnit("us_engineer_team", "Engineer Squad", "infantry", 140),
                # Support (MG/AT)
                DeploymentUnit("us_machine_gun_team", "MG Team (M1919A4)", "support", 160),
                DeploymentUnit("us_at_team", "AT Team (Bazooka)", "support", 150),
                DeploymentUnit("us_mortar_light", "Light Mortar (60mm)", "support", 140),
                DeploymentUnit("us_mortar_heavy", "Heavy Mortar (81mm)", "support", 175),
                DeploymentUnit("us_officer", "Officer / Commander", "support", 180),
                # Armor
                DeploymentUnit("us_sherman_m4", "M4 Sherman", "vehicle", 350),
                DeploymentUnit("us_stuart_m5", "M5 Stuart", "vehicle", 220),
                # Recon
                DeploymentUnit("us_scout_team", "Scout Team", "recon", 110),
                DeploymentUnit("us_sniper_team", "Sniper Team", "recon", 140),
            ]
        else:
            return [
                # Infantry
                DeploymentUnit("ger_rifle_squad", "Rifle Squad", "infantry", 120),
                DeploymentUnit("ger_rifle_squad", "Rifle Squad", "infantry", 120),
                DeploymentUnit("ger_rifle_squad", "Rifle Squad", "infantry", 120),
                DeploymentUnit("ger_assault_squad", "Sturm Squad", "infantry", 145),
                DeploymentUnit("ger_pioneer_team", "Pioneer Squad", "infantry", 140),
                # Support (MG/AT)
                DeploymentUnit("ger_mg42_team", "MG42 Team", "support", 170),
                DeploymentUnit("ger_at_team", "AT Team (Panzerschreck)", "support", 155),
                DeploymentUnit("ger_mortar_light", "Light Mortar (50mm)", "support", 130),
                DeploymentUnit("ger_mortar_heavy", "Heavy Mortar (81mm)", "support", 175),
                DeploymentUnit("ger_officer", "Officer / Commander", "support", 180),
                # Armor
                DeploymentUnit("ger_panther", "Panther", "vehicle", 400),
                DeploymentUnit("ger_stug", "StuG III", "vehicle", 280),
                # Recon
                DeploymentUnit("ger_scout_team", "Scout Team", "recon", 110),
                DeploymentUnit("ger_sniper_team", "Sniper Team", "recon", 140),
            ]

    @staticmethod
    def generate_ai_deployment(
        map_data: dict,
        faction: str = "axis",
        requisition_points: int = 1500,
    ) -> list[dict]:
        """Generate AI deployment placements for the enemy side.

        Returns a list of placement dicts:
          {"unit_template_id": str, "display_name": str,
           "unit_type": str, "position": (x, y)}
        """
        map_width = map_data.get("width", 50)
        map_height = map_data.get("height", 42)
        tile_grid = map_data.get("tiles")

        # Determine enemy zone
        spawn_points = map_data.get("spawn_points", [])
        enemy_positions: list[tuple[int, int]] = []

        side_key = "axis" if faction == "axis" else "allies"

        for sp in spawn_points:
            if sp.get("side") == side_key:
                sp_x, sp_y = sp["position"]
                # Generate positions around the spawn point
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        nx, ny = sp_x + dx, sp_y + dy
                        if 0 <= nx < map_width and 0 <= ny < map_height:
                            # Check terrain is passable
                            if tile_grid is not None:
                                terrain = int(tile_grid[ny][nx])
                                if terrain in _IMPASSABLE_TERRAINS:
                                    continue
                            enemy_positions.append((nx, ny))

        # If no spawn points, use right third of map
        if not enemy_positions:
            third = map_width // 3
            for y in range(map_height):
                for x in range(map_width - third, map_width):
                    if tile_grid is not None:
                        terrain = int(tile_grid[y][x])
                        if terrain not in _IMPASSABLE_TERRAINS:
                            enemy_positions.append((x, y))
                    else:
                        enemy_positions.append((x, y))

        # Build AI force pool
        if faction in ("axis",):
            ai_units = [
                ("ger_rifle_squad", "Rifle Squad", "infantry", 120),
                ("ger_rifle_squad", "Rifle Squad", "infantry", 120),
                ("ger_rifle_squad", "Rifle Squad", "infantry", 120),
                ("ger_mg42_team", "MG42 Team", "support", 170),
                ("ger_at_team", "AT Team (Panzerschreck)", "support", 155),
                ("ger_mortar_heavy", "Heavy Mortar (81mm)", "support", 175),
                ("ger_officer", "Officer / Commander", "support", 180),
                ("ger_panther", "Panther", "vehicle", 400),
            ]
        else:
            ai_units = [
                ("us_rifle_squad", "Rifle Squad", "infantry", 120),
                ("us_rifle_squad", "Rifle Squad", "infantry", 120),
                ("us_rifle_squad", "Rifle Squad", "infantry", 120),
                ("us_machine_gun_team", "MG Team (M1919A4)", "support", 160),
                ("us_at_team", "AT Team (Bazooka)", "support", 150),
                ("us_mortar_heavy", "Heavy Mortar (81mm)", "support", 175),
                ("us_officer", "Officer / Commander", "support", 180),
                ("us_sherman_m4", "M4 Sherman", "vehicle", 350),
            ]

        # Place AI units within budget
        placements: list[dict] = []
        spent = 0
        used_positions: set[tuple[int, int]] = set()

        for template_id, name, utype, cost in ai_units:
            if spent + cost > requisition_points:
                continue
            # Find a free position
            for pos in enemy_positions:
                if pos not in used_positions:
                    used_positions.add(pos)
                    placements.append({
                        "unit_template_id": template_id,
                        "display_name": name,
                        "unit_type": utype,
                        "position": pos,
                    })
                    spent += cost
                    break

        return placements

    def update_button_hover(self, mouse_x: int, mouse_y: int) -> None:
        """Update the Start Battle button hover state based on mouse position."""
        self._button_hovered = bool(
            self._button_rect and self._is_in_button(mouse_x, mouse_y)
        )
