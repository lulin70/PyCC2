"""Tooltip System - Hover information display for units."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


@dataclass
class TooltipData:
    """Data to display in tooltip."""
    name: str = ""
    unit_type: str = ""
    hp: int = 0
    max_hp: int = 100
    morale: float = 100.0
    ammo: int = 0
    max_ammo: int = 10
    status: str = "Normal"
    position: tuple[float, float] = (0.0, 0.0)


class Tooltip:
    """
    Mouse hover tooltip display system.
    
    Features:
    - Show unit info after 0.5s hover delay
    - Display: Name, Type, HP, Morale, Ammo, Status
    - Follow mouse cursor intelligently (avoid screen edges)
    - Auto-hide when mouse leaves unit
    
    CC2 Behavior:
    - Appears after brief delay (prevents flickering)
    - Shows relevant combat information
    - Positioned to not obscure the unit or action
    - Clean, readable font with semi-transparent background
    """
    
    SHOW_DELAY: float = 0.5  # seconds before showing
    HIDE_DELAY: float = 0.1  # seconds before hiding
    MAX_WIDTH: int = 220
    PADDING: int = 8
    FONT_SIZE: int = 12
    LINE_HEIGHT: int = 18
    
    def __init__(self):
        self.target_unit: Unit | None = None
        self._show_timer: float = 0.0
        self._hide_timer: float = 0.0
        self._visible: bool = False
        self._data: TooltipData = TooltipData()
        self._was_hovering: bool = False
        self._mouse_pos: tuple[int, int] = (0, 0)
        # Surface cache – lazy init
        self._tooltip_surface_cache = None
        self._tooltip_surface_cache_size: tuple[int, int] | None = None

    def on_hover(self, unit: Unit | None, dt: float) -> None:
        """
        Process hover event.
        
        Args:
            unit: Unit under cursor (None if no unit)
            dt: Delta time since last frame
        """
        if unit != self.target_unit:
            self.target_unit = unit
            self._show_timer = 0.0
            self._visible = False
            self._was_hovering = False
            if unit:
                self._update_data(unit)
        else:
            if unit is not None:
                self._show_timer += dt
                self._was_hovering = True
                
                if self._show_timer >= self.SHOW_DELAY and not self._visible:
                    self._visible = True
                    self._update_data(unit)
            else:
                if self._was_hovering:
                    self._hide_timer += dt
                    if self._hide_timer >= self.HIDE_DELAY:
                        self._visible = False
                        self._was_hovering = False

    def _update_data(self, unit: Unit) -> None:
        """Extract display data from unit."""
        self._data.name = getattr(unit, 'name', 'Unknown')
        self._data.unit_type = getattr(unit, 'unit_type', 'Infantry')
        
        health = getattr(unit, 'health_component', None)
        if health:
            self._data.hp = getattr(health, 'current_hp', 0)
            self._data.max_hp = getattr(health, 'max_hp', 100)
        
        morale = getattr(unit, 'morale_component', None)
        if morale:
            self._data.morale = getattr(morale, 'current_morale', 100.0)
        
        weapon = getattr(unit, 'weapon_component', None)
        if weapon:
            self._data.ammo = getattr(weapon, 'current_ammo', 0)
            self._data.max_ammo = getattr(weapon, 'max_ammo', 10)
        
        self._data.status = getattr(unit, 'status', 'Normal')
        
        pos_comp = getattr(unit, 'position_component', None)
        if pos_comp:
            self._data.position = (pos_comp.x, pos_comp.y)

    def render(
        self,
        surface,
        mouse_pos: tuple[int, int],
        screen_size: tuple[int, int] = (1280, 720),
    ) -> None:
        """
        Render tooltip at mouse position.
        
        Args:
            surface: Pygame surface to draw on
            mouse_pos: Current mouse cursor position
            screen_size: Screen dimensions for edge detection
        """
        if not self._visible or not self.target_unit:
            return
        
        try:
            import pygame
            
            self._mouse_pos = mouse_pos
            lines = self._get_display_lines()
            
            if not lines:
                return
            
            font = pygame.font.SysFont('arial', self.FONT_SIZE)
            
            padding = self.PADDING
            line_h = self.LINE_HEIGHT
            width = self.MAX_WIDTH
            height = len(lines) * line_h + padding * 2
            
            x = mouse_pos[0] + 15
            y = mouse_pos[1] + 15
            
            if x + width > screen_size[0]:
                x = mouse_pos[0] - width - 15
            if y + height > screen_size[1]:
                y = mouse_pos[1] - height - 15
            
            x = max(0, min(x, screen_size[0] - width))
            y = max(0, min(y, screen_size[1] - height))
            
            tooltip_size = (width, height)
            if self._tooltip_surface_cache is None or self._tooltip_surface_cache_size != tooltip_size:
                self._tooltip_surface_cache = pygame.Surface(tooltip_size, pygame.SRCALPHA)
                self._tooltip_surface_cache_size = tooltip_size
            tooltip_surface = self._tooltip_surface_cache
            tooltip_surface.fill((0, 0, 0, 0))
            pygame.draw.rect(
                tooltip_surface,
                (20, 20, 30, 230),
                (0, 0, width, height),
                border_radius=5,
            )
            pygame.draw.rect(
                tooltip_surface,
                (100, 100, 120, 255),
                (0, 0, width, height),
                width=1,
                border_radius=5,
            )
            
            for i, (text, color) in enumerate(lines):
                text_surf = font.render(text, True, color)
                tooltip_surface.blit(
                    text_surf,
                    (padding, padding + i * line_h),
                )
            
            surface.blit(tooltip_surface, (x, y))
            
        except Exception as e:
            logging.debug(f"Tooltip rendering failed: {e}")

    def _get_display_lines(self) -> list[tuple[str, tuple[int, int, int]]]:
        """Generate formatted text lines for display."""
        lines: list[tuple[str, tuple[int, int, int]]] = []
        
        d = self._data
        
        lines.append((f"【 {d.name} 】", (255, 215, 0)))
        lines.append((f"Type: {d.unit_type}", (200, 200, 200)))
        
        hp_pct = (d.hp / d.max_hp * 100) if d.max_hp > 0 else 0
        hp_color = self._get_hp_color(hp_pct)
        lines.append((f"HP: {d.hp}/{d.max_hp} ({hp_pct:.0f}%)", hp_color))
        
        morale_color = self._get_morale_color(d.morale)
        lines.append((f"Morale: {d.morale:.0f}%", morale_color))
        
        lines.append((f"Ammo: {d.ammo}/{d.max_ammo}", (150, 200, 255)))
        
        status_color = self._get_status_color(d.status)
        lines.append((f"Status: {d.status}", status_color))
        
        return lines

    @staticmethod
    def _get_hp_color(percent: float) -> tuple[int, int, int]:
        """Get color based on HP percentage."""
        if percent > 70:
            return (0, 255, 0)
        elif percent > 30:
            return (255, 255, 0)
        else:
            return (255, 80, 80)

    @staticmethod
    def _get_morale_color(morale: float) -> tuple[int, int, int]:
        """Get color based on morale level."""
        if morale > 70:
            return (100, 255, 100)
        elif morale > 30:
            return (255, 255, 100)
        else:
            return (255, 120, 120)

    @staticmethod
    def _get_status_color(status: str) -> tuple[int, int, int]:
        """Get color based on unit status."""
        status_lower = status.lower()
        if 'suppressed' in status_lower or 'pinned' in status_lower:
            return (255, 100, 100)
        elif 'moving' in status_lower:
            return (100, 200, 255)
        elif 'combat' in status_lower or 'attacking' in status_lower:
            return (255, 180, 50)
        elif 'hidden' in status_lower or 'sneaking' in status_lower:
            return (100, 255, 150)
        else:
            return (200, 200, 200)

    @property
    def is_visible(self) -> bool:
        return self._visible

    @property
    def data(self) -> TooltipData:
        return self._data

    def force_hide(self) -> None:
        """Immediately hide tooltip."""
        self._visible = False
        self._show_timer = 0.0
        self._hide_timer = 0.0
        self.target_unit = None
        self._was_hovering = False
