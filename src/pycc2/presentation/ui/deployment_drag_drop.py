"""Deployment Drag-and-Drop System — Unit Dragging from Roster to Map

Extracted from deployment_ui.py (SRP refactoring).
Manages all drag-and-drop state and interaction logic for deploying units
by dragging them from the force pool panel onto the map.
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

# Import models
from pycc2.presentation.ui.deployment_models import DeploymentPhase, DeploymentUnit

# ---------------------------------------------------------------------------
# Pygame – imported lazily so the module can be imported in headless tests
# ---------------------------------------------------------------------------
_pygame_available: bool = False
try:
    import pygame

    _pygame_available = True
except ImportError:
    pygame = None  # type: ignore[assignment]


class DeploymentDragDrop:
    """Manages drag-and-drop deployment interaction.

    Holds all dragging state variables and provides methods for starting,
    updating, ending, and cancelling drags. Also handles ghost sprite
    rendering during drag operations.
    """

    def __init__(self) -> None:
        """Initialize the DeploymentDragDrop."""
        # === Drag-and-drop state (Issue 3) ===
        self._dragging_unit: DeploymentUnit | None = None
        self._dragging_unit_index: int | None = None
        self._drag_start_pos: tuple[int, int] | None = None
        self._drag_current_pos: tuple[int, int] | None = None
        self._ghost_surface: pygame.Surface | None = None  # Pre-rendered ghost sprite
        self._is_dragging: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_dragging(self) -> bool:
        """Whether a drag operation is currently in progress."""
        return self._is_dragging

    @property
    def dragging_unit(self) -> DeploymentUnit | None:
        """The unit currently being dragged, or None."""
        return self._dragging_unit

    @property
    def dragging_unit_index(self) -> int | None:
        """Index of the unit currently being dragged in the available_units list."""
        return self._dragging_unit_index

    @property
    def ghost_surface(self) -> pygame.Surface | None:
        """Pre-rendered ghost sprite surface for the dragged unit."""
        return self._ghost_surface

    @property
    def drag_current_pos(self) -> tuple[int, int] | None:
        """Current screen position of the drag cursor."""
        return self._drag_current_pos

    def handle_mouse_down(
        self,
        screen_x: int,
        screen_y: int,
        ui,
    ) -> str | None:
        """Handle mouse button DOWN - start drag from roster unit.

        Parameters
        ----------
        screen_x, screen_y : int
            Screen coordinates of the mouse click.
        ui : DeploymentUI
            The parent DeploymentUI instance (for accessing state, roster, etc.).

        Returns an action string or None:
          - ``"drag_start:<index>"`` – drag started for roster unit at index
          - ``None`` – click did not start a drag

        """
        if ui._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return None

        # Only start drag from roster panel (left side)
        if screen_x >= ui._roster_width:
            return None

        # Find which roster unit was clicked
        idx = ui._roster_index_at(screen_x, screen_y)
        if idx is None or idx < 0 or idx >= len(ui._state.available_units):
            return None

        unit = ui._state.available_units[idx]

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
            self._ghost_surface = self._create_ghost_surface(unit, ui)
        except (pygame.error, ValueError, TypeError):
            self._ghost_surface = None  # Safe fallback

        # Select the unit (for placement highlights)
        ui._selected_unit_index = idx

        return f"drag_start:{idx}"

    def handle_mouse_move(
        self,
        screen_x: int,
        screen_y: int,
    ) -> None:
        """Handle mouse movement while dragging - update ghost position.

        Parameters
        ----------
        screen_x, screen_y : int
            Current screen coordinates of the mouse.

        """
        if not self._is_dragging or self._dragging_unit is None:
            return

        self._drag_current_pos = (screen_x, screen_y)

    def handle_mouse_up(
        self,
        screen_x: int,
        screen_y: int,
        ui,
    ) -> str | None:
        """Handle mouse button UP - complete drag (place or cancel).

        Parameters
        ----------
        screen_x, screen_y : int
            Screen coordinates where the mouse was released.
        ui : DeploymentUI
            The parent DeploymentUI instance.

        Returns an action string or None:
          - ``"place_unit:<index>"`` – unit placed successfully
          - ``"place_failed"`` – placement failed unexpectedly
          - ``"invalid_placement"`` – dropped on invalid tile
          - ``"drag_cancelled"`` – dropped outside map area
          - ``None`` – no drag was active

        """
        if not self._is_dragging or self._dragging_unit is None:
            return None

        result = None

        # Try to place at current position if over map
        if screen_x >= ui._roster_width:
            map_pos = ui.screen_to_map(screen_x, screen_y)

            if map_pos is not None and self._dragging_unit_index is not None:
                map_x, map_y = map_pos

                # Check if valid placement
                terrain = ui._get_terrain_at(map_x, map_y)
                can_place = (
                    ui.can_place_at(self._dragging_unit, map_x, map_y, terrain)
                    and not any(pu.position == (map_x, map_y) for pu in ui._state.placed_units)
                    and self._dragging_unit.deployment_cost <= ui.requisition_remaining
                )

                if can_place:
                    # SUCCESS: Place the unit
                    if ui.place_unit(self._dragging_unit_index, map_x, map_y):
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
        self.clear_drag_state()

        return result

    def clear_drag_state(self) -> None:
        """Clear all drag-and-drop state."""
        self._dragging_unit = None
        self._dragging_unit_index = None
        self._drag_start_pos = None
        self._drag_current_pos = None
        self._ghost_surface = None
        self._is_dragging = False
        # Don't clear selection - let user click again if needed

    # ------------------------------------------------------------------
    # Ghost sprite rendering
    # ------------------------------------------------------------------

    def _create_ghost_surface(self, unit: DeploymentUnit, ui) -> pygame.Surface | None:
        """Create a semi-transparent ghost sprite for dragged unit.

        Parameters
        ----------
        unit : DeploymentUnit
            The unit being dragged.
        ui : DeploymentUI
            The parent UI instance (for font access).

        """
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
            if ui._font_small:
                label = ui._font_small.render(unit.display_name[:4], True, (255, 255, 255, 200))
                label.set_alpha(200)
                ghost.blit(label, (cx - label.get_width() // 2, cy - radius - 12))

            return ghost
        except (pygame.error, ValueError, TypeError) as e:
            logging.debug("Ghost surface rendering failed: %s", e)
            return None
