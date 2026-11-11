"""Resource Bar UI Component - Sprint 2 Day 8 FUNC-04.

Renders gold, wood, and power resources in the top-left corner of the screen.
Displays current values with color-coded text (gold=yellow, wood=brown, power=blue).
"""

from __future__ import annotations

import pygame
from typing import TYPE_CHECKING

from pycc2.domain.systems.resource_manager import ResourceManager

if TYPE_CHECKING:
    from pygame import Surface


# Color constants
COLOR_GOLD = (255, 215, 0)  # Gold yellow
COLOR_WOOD = (139, 69, 19)  # Brown
COLOR_POWER = (30, 144, 255)  # Dodger blue
COLOR_TEXT_BG = (0, 0, 0, 180)  # Semi-transparent black


class ResourceBarUI:
    """UI component displaying player resources (gold/wood/power).
    
    Renders in top-left corner with format:
      Gold: 1500  Wood: 800  Power: 45/100
    
    Attributes:
        font: Pygame font for rendering text
        padding: Padding from screen edge (pixels)
        resource_manager: Reference to ResourceManager singleton
    """
    
    def __init__(self, font_size: int = 24, padding: int = 10):
        """Initialize resource bar UI.
        
        Args:
            font_size: Font size for text rendering
            padding: Padding from top-left corner (pixels)
        """
        self.font = pygame.font.Font(None, font_size)
        self.padding = padding
        self.resource_manager = ResourceManager()
    
    def render(self, surface: Surface) -> None:
        """Render resource bar to screen surface.
        
        Args:
            surface: Pygame surface to render onto
        """
        resources = self.resource_manager.get_resources()
        
        # Prepare text
        gold_text = f"Gold: {int(resources['gold'])}"
        wood_text = f"Wood: {int(resources['wood'])}"
        power_text = f"Power: {resources['power']}/{resources['max_power']}"
        
        # Render text surfaces
        gold_surf = self.font.render(gold_text, True, COLOR_GOLD)
        wood_surf = self.font.render(wood_text, True, COLOR_WOOD)
        power_surf = self.font.render(power_text, True, COLOR_POWER)
        
        # Calculate positions
        x = self.padding
        y = self.padding
        spacing = 150  # Horizontal spacing between resources
        
        # Render background panel (optional, semi-transparent)
        panel_width = gold_surf.get_width() + wood_surf.get_width() + power_surf.get_width() + spacing * 2 + self.padding * 2
        panel_height = max(gold_surf.get_height(), wood_surf.get_height(), power_surf.get_height()) + self.padding * 2
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill(COLOR_TEXT_BG)
        surface.blit(panel_surface, (0, 0))
        
        # Render resource text
        surface.blit(gold_surf, (x, y + self.padding))
        x += gold_surf.get_width() + spacing
        
        surface.blit(wood_surf, (x, y + self.padding))
        x += wood_surf.get_width() + spacing
        
        surface.blit(power_surf, (x, y + self.padding))
