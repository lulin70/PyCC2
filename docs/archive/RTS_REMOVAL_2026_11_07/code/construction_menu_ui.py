"""Construction Menu UI Component - Sprint 3 Day 11 FUNC-05.

Displays building options (Barracks/Power Plant/Defense Tower) in bottom-right corner.
Shows building icons, costs, and handles click events for building selection.
"""

from __future__ import annotations

import pygame
from enum import Enum
from typing import Optional, TYPE_CHECKING

from pycc2.domain.entities.building import BuildingType, BUILDING_PRESETS
from pycc2.domain.systems.resource_manager import ResourceManager

if TYPE_CHECKING:
    from pygame import Surface


# Color constants
COLOR_PANEL_BG = (40, 40, 50, 220)  # Dark semi-transparent
COLOR_BUTTON_BG = (60, 60, 70)
COLOR_BUTTON_HOVER = (80, 80, 100)
COLOR_BUTTON_SELECTED = (100, 150, 255)
COLOR_TEXT = (255, 255, 255)
COLOR_COST_GOLD = (255, 215, 0)
COLOR_COST_WOOD = (139, 69, 19)
COLOR_COST_POWER = (30, 144, 255)
COLOR_INSUFFICIENT = (255, 100, 100)  # Red for insufficient resources


class ConstructionMenuUI:
    """UI component for building construction menu (bottom-right).
    
    Displays available building types with costs and affordability indicators.
    Handles mouse hover and click interactions.
    
    Attributes:
        position: Bottom-right position (x, y) in pixels
        button_width: Width of each building button
        button_height: Height of each building button
        spacing: Spacing between buttons
        selected_building: Currently selected building type (or None)
        hovered_index: Index of hovered button (or None)
        resource_manager: Reference to ResourceManager singleton
        font: Pygame font for rendering text
        small_font: Smaller font for cost text
    """
    
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        button_width: int = 120,
        button_height: int = 100,
        spacing: int = 10,
        font_size: int = 18,
    ):
        """Initialize construction menu UI.
        
        Args:
            screen_width: Screen width (to anchor to bottom-right)
            screen_height: Screen height (to anchor to bottom-right)
            button_width: Width of each building button
            button_height: Height of each building button
            spacing: Spacing between UI elements
            font_size: Font size for button text
        """
        self.button_width = button_width
        self.button_height = button_height
        self.spacing = spacing
        
        # Calculate panel position (bottom-right)
        panel_width = button_width * 3 + spacing * 4  # 3 buttons + margins
        panel_height = button_height + spacing * 2
        self.position = (
            screen_width - panel_width - spacing,
            screen_height - panel_height - spacing,
        )
        self.panel_width = panel_width
        self.panel_height = panel_height
        
        self.selected_building: Optional[BuildingType] = None
        self.hovered_index: Optional[int] = None
        self.resource_manager = ResourceManager()
        
        self.font = pygame.font.Font(None, font_size)
        self.small_font = pygame.font.Font(None, 14)
        
        # Building types to display (3 basic buildings)
        self.building_types = [
            BuildingType.BARRACKS,
            BuildingType.POWER_PLANT,
            BuildingType.DEFENSE_TOWER,
        ]
    
    def handle_mouse_motion(self, mouse_pos: tuple[int, int]) -> None:
        """Update hover state based on mouse position.
        
        Args:
            mouse_pos: (x, y) mouse position in screen coordinates
        """
        self.hovered_index = None
        
        for i in range(len(self.building_types)):
            button_rect = self._get_button_rect(i)
            if button_rect.collidepoint(mouse_pos):
                self.hovered_index = i
                break
    
    def handle_mouse_click(self, mouse_pos: tuple[int, int]) -> Optional[BuildingType]:
        """Handle mouse click on building button.
        
        Args:
            mouse_pos: (x, y) mouse position in screen coordinates
        
        Returns:
            BuildingType if a button was clicked, None otherwise
        """
        for i, building_type in enumerate(self.building_types):
            button_rect = self._get_button_rect(i)
            if button_rect.collidepoint(mouse_pos):
                # Toggle selection
                if self.selected_building == building_type:
                    self.selected_building = None
                else:
                    self.selected_building = building_type
                return self.selected_building
        
        return None
    
    def get_selected_building(self) -> Optional[BuildingType]:
        """Get currently selected building type.
        
        Returns:
            BuildingType or None if no selection
        """
        return self.selected_building
    
    def clear_selection(self) -> None:
        """Clear building selection (e.g., after placement)."""
        self.selected_building = None
    
    def render(self, surface: Surface) -> None:
        """Render construction menu to screen surface.
        
        Args:
            surface: Pygame surface to render onto
        """
        # Render panel background
        panel_surface = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        panel_surface.fill(COLOR_PANEL_BG)
        surface.blit(panel_surface, self.position)
        
        # Render building buttons
        for i, building_type in enumerate(self.building_types):
            self._render_building_button(surface, i, building_type)
    
    def _get_button_rect(self, index: int) -> pygame.Rect:
        """Get button rectangle for given index.
        
        Args:
            index: Button index (0-2)
        
        Returns:
            Pygame Rect for button
        """
        x = self.position[0] + self.spacing + index * (self.button_width + self.spacing)
        y = self.position[1] + self.spacing
        return pygame.Rect(x, y, self.button_width, self.button_height)
    
    def _render_building_button(self, surface: Surface, index: int, building_type: BuildingType) -> None:
        """Render individual building button with icon, name, and cost.
        
        Args:
            surface: Pygame surface to render onto
            index: Button index
            building_type: Building type to render
        """
        button_rect = self._get_button_rect(index)
        
        # Determine button color
        preset = BUILDING_PRESETS[building_type]
        cost = preset["cost"]
        can_afford = self.resource_manager.can_afford(cost.gold, cost.wood, cost.power)
        
        if self.selected_building == building_type:
            button_color = COLOR_BUTTON_SELECTED
        elif self.hovered_index == index:
            button_color = COLOR_BUTTON_HOVER
        else:
            button_color = COLOR_BUTTON_BG
        
        # Render button background
        pygame.draw.rect(surface, button_color, button_rect)
        pygame.draw.rect(surface, COLOR_TEXT, button_rect, 2)  # Border
        
        # Render building icon (simplified: first letter)
        icon_text = building_type.name[0]  # B/P/D
        icon_surf = self.font.render(icon_text, True, COLOR_TEXT)
        icon_x = button_rect.centerx - icon_surf.get_width() // 2
        icon_y = button_rect.y + 10
        surface.blit(icon_surf, (icon_x, icon_y))
        
        # Render building name
        name_text = building_type.name.replace("_", " ")
        name_surf = self.small_font.render(name_text, True, COLOR_TEXT)
        name_x = button_rect.centerx - name_surf.get_width() // 2
        name_y = button_rect.y + 35
        surface.blit(name_surf, (name_x, name_y))
        
        # Render cost (3 lines: gold/wood/power)
        cost_y = button_rect.y + 55
        cost_color = COLOR_TEXT if can_afford else COLOR_INSUFFICIENT
        
        gold_text = f"{int(cost.gold)}g"
        gold_surf = self.small_font.render(gold_text, True, cost_color if self.resource_manager.gold >= cost.gold else COLOR_INSUFFICIENT)
        gold_x = button_rect.centerx - gold_surf.get_width() // 2
        surface.blit(gold_surf, (gold_x, cost_y))
        
        wood_text = f"{int(cost.wood)}w"
        wood_surf = self.small_font.render(wood_text, True, cost_color if self.resource_manager.wood >= cost.wood else COLOR_INSUFFICIENT)
        wood_x = button_rect.centerx - wood_surf.get_width() // 2
        surface.blit(wood_surf, (wood_x, cost_y + 12))
        
        power_text = f"{cost.power}p"
        power_surf = self.small_font.render(power_text, True, cost_color if self.resource_manager.power + cost.power <= self.resource_manager.max_power else COLOR_INSUFFICIENT)
        power_x = button_rect.centerx - power_surf.get_width() // 2
        surface.blit(power_surf, (power_x, cost_y + 24))
    
    def is_mouse_over_menu(self, mouse_pos: tuple[int, int]) -> bool:
        """Check if mouse is over the construction menu panel.
        
        Args:
            mouse_pos: (x, y) mouse position in screen coordinates
        
        Returns:
            True if mouse is over menu panel
        """
        panel_rect = pygame.Rect(self.position[0], self.position[1], self.panel_width, self.panel_height)
        return panel_rect.collidepoint(mouse_pos)
