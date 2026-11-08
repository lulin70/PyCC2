"""Life Bar UI Component - Sprint 3 Day 13 FUNC-06.

Displays unit health bars above units.
Shows HP percentage with color gradients (green → yellow → red).
"""

from __future__ import annotations

import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pygame import Surface


# Color constants
COLOR_HP_HIGH = (0, 255, 0)  # Green (>66% HP)
COLOR_HP_MEDIUM = (255, 255, 0)  # Yellow (33-66% HP)
COLOR_HP_LOW = (255, 0, 0)  # Red (<33% HP)
COLOR_HP_BG = (60, 60, 60)  # Dark gray background
COLOR_HP_BORDER = (0, 0, 0)  # Black border


class LifeBarUI:
    """UI component for rendering unit health bars.
    
    Renders a horizontal bar above each unit showing HP percentage.
    Color changes based on health: green (high) → yellow (medium) → red (low).
    
    Attributes:
        bar_width: Width of health bar (pixels)
        bar_height: Height of health bar (pixels)
        offset_y: Vertical offset above unit center (pixels)
        show_border: Whether to show border around bar
    """
    
    def __init__(
        self,
        bar_width: int = 40,
        bar_height: int = 4,
        offset_y: int = -20,
        show_border: bool = True,
    ):
        """Initialize life bar UI.
        
        Args:
            bar_width: Width of health bar (pixels)
            bar_height: Height of health bar (pixels)
            offset_y: Vertical offset above unit center (pixels, negative = above)
            show_border: Whether to show border
        """
        self.bar_width = bar_width
        self.bar_height = bar_height
        self.offset_y = offset_y
        self.show_border = show_border
    
    def get_hp_color(self, hp_percent: float) -> tuple[int, int, int]:
        """Get color based on HP percentage.
        
        Args:
            hp_percent: HP percentage (0.0 to 1.0)
        
        Returns:
            RGB color tuple
        """
        if hp_percent > 0.66:
            return COLOR_HP_HIGH
        elif hp_percent > 0.33:
            return COLOR_HP_MEDIUM
        else:
            return COLOR_HP_LOW
    
    def render_life_bar(
        self,
        surface: Surface,
        unit_screen_x: int,
        unit_screen_y: int,
        hp: int,
        max_hp: int,
    ) -> None:
        """Render life bar for a single unit.
        
        Args:
            surface: Pygame surface to render onto
            unit_screen_x: Unit center X in screen coordinates
            unit_screen_y: Unit center Y in screen coordinates
            hp: Current hit points
            max_hp: Maximum hit points
        """
        if max_hp <= 0:
            return
        
        # Calculate HP percentage
        hp_percent = max(0.0, min(1.0, hp / max_hp))
        
        # Don't render if at full health (optional optimization)
        if hp_percent >= 1.0:
            return
        
        # Calculate bar position (centered above unit)
        bar_x = unit_screen_x - self.bar_width // 2
        bar_y = unit_screen_y + self.offset_y
        
        # Render background
        bg_rect = pygame.Rect(bar_x, bar_y, self.bar_width, self.bar_height)
        pygame.draw.rect(surface, COLOR_HP_BG, bg_rect)
        
        # Render HP fill
        if hp_percent > 0.0:
            fill_width = int(self.bar_width * hp_percent)
            hp_rect = pygame.Rect(bar_x, bar_y, fill_width, self.bar_height)
            hp_color = self.get_hp_color(hp_percent)
            pygame.draw.rect(surface, hp_color, hp_rect)
        
        # Render border
        if self.show_border:
            pygame.draw.rect(surface, COLOR_HP_BORDER, bg_rect, 1)
    
    def render_batch(
        self,
        surface: Surface,
        units: list[tuple[int, int, int, int]],
    ) -> None:
        """Render life bars for multiple units (batch).
        
        Args:
            surface: Pygame surface to render onto
            units: List of (screen_x, screen_y, hp, max_hp) tuples
        """
        for screen_x, screen_y, hp, max_hp in units:
            self.render_life_bar(surface, screen_x, screen_y, hp, max_hp)


class LifeBarUIExtended(LifeBarUI):
    """Extended life bar with optional HP text display."""
    
    def __init__(
        self,
        bar_width: int = 40,
        bar_height: int = 4,
        offset_y: int = -20,
        show_border: bool = True,
        show_text: bool = False,
        font_size: int = 12,
    ):
        """Initialize extended life bar UI.
        
        Args:
            bar_width: Width of health bar (pixels)
            bar_height: Height of health bar (pixels)
            offset_y: Vertical offset above unit center (pixels)
            show_border: Whether to show border
            show_text: Whether to show HP text (e.g., "50/100")
            font_size: Font size for HP text
        """
        super().__init__(bar_width, bar_height, offset_y, show_border)
        self.show_text = show_text
        self.font = pygame.font.Font(None, font_size) if show_text else None
    
    def render_life_bar(
        self,
        surface: Surface,
        unit_screen_x: int,
        unit_screen_y: int,
        hp: int,
        max_hp: int,
    ) -> None:
        """Render life bar with optional HP text.
        
        Args:
            surface: Pygame surface to render onto
            unit_screen_x: Unit center X in screen coordinates
            unit_screen_y: Unit center Y in screen coordinates
            hp: Current hit points
            max_hp: Maximum hit points
        """
        # Render base life bar
        super().render_life_bar(surface, unit_screen_x, unit_screen_y, hp, max_hp)
        
        # Render HP text if enabled
        if self.show_text and self.font and max_hp > 0:
            hp_text = f"{hp}/{max_hp}"
            text_surf = self.font.render(hp_text, True, (255, 255, 255))
            text_x = unit_screen_x - text_surf.get_width() // 2
            text_y = unit_screen_y + self.offset_y - 12  # Above bar
            surface.blit(text_surf, (text_x, text_y))
