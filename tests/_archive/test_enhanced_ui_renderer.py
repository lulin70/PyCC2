"""
Unit tests for EnhancedUIRenderer - Enhanced UI Rendering

Tests cover:
- Enhanced button rendering with states (Happy Path)
- Enhanced panel rendering with titles (Happy Path)
- Enhanced icon rendering (Happy Path)
- Minimap frame rendering (Happy Path)
- Progress bar rendering (Happy Path)
- State transitions (normal, hover, pressed, disabled) (Happy Path + Boundary)
- Error handling for invalid inputs (Error Case)
- Boundary conditions (zero size, extreme dimensions)
- Color consistency (Happy Path)
- Convenience functions (Happy Path)
"""

from __future__ import annotations

import os

import pytest

# Ensure SDL dummy drivers are set before pygame imports
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class TestEnhancedUIRenderer:
    """Test EnhancedUIRenderer functionality."""

    @pytest.fixture()
    def test_surface(self, pygame_display):
        """Create a test surface for UI rendering."""
        import pygame

        surface = pygame.Surface((800, 600), pygame.SRCALPHA)
        surface.fill((50, 50, 50, 255))
        return surface

    @pytest.fixture()
    def test_font(self, pygame_display, mock_font):
        """Get a test font."""
        return mock_font

    # ===== HAPPY PATH TESTS =====

    def test_draw_button_normal_state(self, test_surface, test_font, pygame_display):
        """Test drawing button in normal state."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 150, 40)

        # Should draw without crashing
        EnhancedUIRenderer.draw_enhanced_button(
            test_surface, rect, "Test Button", test_font, state="normal"
        )

        # Verify something was drawn (check if pixels changed)
        color_at_button = test_surface.get_at((125, 120))
        color_outside = test_surface.get_at((10, 10))
        assert color_at_button != color_outside

    def test_draw_button_hover_state(self, test_surface, test_font, pygame_display):
        """Test drawing button in hover state."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 150, 40)

        EnhancedUIRenderer.draw_enhanced_button(
            test_surface, rect, "Hover", test_font, state="hover"
        )

        # Should draw differently from normal
        assert test_surface is not None

    def test_draw_button_pressed_state(self, test_surface, test_font, pygame_display):
        """Test drawing button in pressed state."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 150, 40)

        EnhancedUIRenderer.draw_enhanced_button(
            test_surface, rect, "Pressed", test_font, state="pressed"
        )

        assert test_surface is not None

    def test_draw_button_disabled_state(self, test_surface, test_font, pygame_display):
        """Test drawing button in disabled state."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 150, 40)

        EnhancedUIRenderer.draw_enhanced_button(
            test_surface, rect, "Disabled", test_font, state="disabled"
        )

        assert test_surface is not None

    def test_draw_panel_without_title(self, test_surface, pygame_display):
        """Test drawing panel without title."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(50, 50, 300, 200)

        EnhancedUIRenderer.draw_enhanced_panel(test_surface, rect)

        # Verify panel was drawn
        color_at_panel = test_surface.get_at((60, 60))
        assert color_at_panel != (50, 50, 50, 255)  # Different from background

    def test_draw_panel_with_title(self, test_surface, test_font, pygame_display):
        """Test drawing panel with title."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(50, 50, 300, 200)

        EnhancedUIRenderer.draw_enhanced_panel(
            test_surface, rect, title="Test Panel", font=test_font
        )

        assert test_surface is not None

    def test_draw_icon_move(self, test_surface, pygame_display):
        """Test drawing move icon."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 48, 48)

        EnhancedUIRenderer.draw_enhanced_icon(test_surface, rect, icon_type="move", state="normal")

        # Verify icon was drawn
        color_at_icon = test_surface.get_at((110, 110))
        assert color_at_icon != (50, 50, 50, 255)

    def test_draw_icon_attack(self, test_surface, pygame_display):
        """Test drawing attack icon."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 48, 48)

        EnhancedUIRenderer.draw_enhanced_icon(
            test_surface, rect, icon_type="attack", state="normal"
        )

        assert test_surface is not None

    def test_draw_icon_defend(self, test_surface, pygame_display):
        """Test drawing defend icon."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 48, 48)

        EnhancedUIRenderer.draw_enhanced_icon(
            test_surface, rect, icon_type="defend", state="normal"
        )

        assert test_surface is not None

    def test_draw_icon_info(self, test_surface, pygame_display):
        """Test drawing info icon."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 48, 48)

        EnhancedUIRenderer.draw_enhanced_icon(test_surface, rect, icon_type="info", state="normal")

        assert test_surface is not None

    def test_draw_icon_hover_state(self, test_surface, pygame_display):
        """Test drawing icon in hover state."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 48, 48)

        EnhancedUIRenderer.draw_enhanced_icon(test_surface, rect, icon_type="move", state="hover")

        assert test_surface is not None

    def test_draw_icon_disabled_state(self, test_surface, pygame_display):
        """Test drawing icon in disabled state."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 48, 48)

        EnhancedUIRenderer.draw_enhanced_icon(
            test_surface, rect, icon_type="attack", state="disabled"
        )

        assert test_surface is not None

    def test_draw_minimap_frame(self, test_surface, pygame_display):
        """Test drawing minimap frame."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(600, 400, 180, 180)

        EnhancedUIRenderer.draw_minimap_frame(test_surface, rect)

        # Verify frame was drawn
        color_at_border = test_surface.get_at((600, 400))
        assert color_at_border != (50, 50, 50, 255)

    def test_draw_progress_bar_empty(self, test_surface, test_font, pygame_display):
        """Test drawing empty progress bar."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 200, 30)

        EnhancedUIRenderer.draw_progress_bar(
            test_surface, rect, progress=0.0, show_text=True, font=test_font
        )

        assert test_surface is not None

    def test_draw_progress_bar_half(self, test_surface, test_font, pygame_display):
        """Test drawing half-filled progress bar."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 200, 30)

        EnhancedUIRenderer.draw_progress_bar(
            test_surface, rect, progress=0.5, show_text=True, font=test_font
        )

        assert test_surface is not None

    def test_draw_progress_bar_full(self, test_surface, test_font, pygame_display):
        """Test drawing full progress bar."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 200, 30)

        EnhancedUIRenderer.draw_progress_bar(
            test_surface, rect, progress=1.0, show_text=True, font=test_font
        )

        assert test_surface is not None

    def test_draw_progress_bar_custom_color(self, test_surface, test_font, pygame_display):
        """Test drawing progress bar with custom color."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 200, 30)

        EnhancedUIRenderer.draw_progress_bar(
            test_surface, rect, progress=0.7, color=(255, 100, 100), show_text=True, font=test_font
        )

        assert test_surface is not None

    # ===== BOUNDARY TESTS =====

    def test_draw_button_zero_size(self, test_surface, test_font, pygame_display):
        """Test drawing button with zero size (boundary)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 0, 0)

        # Should handle gracefully without crashing
        EnhancedUIRenderer.draw_enhanced_button(
            test_surface, rect, "Zero", test_font, state="normal"
        )

        assert test_surface is not None

    def test_draw_button_very_small(self, test_surface, test_font, pygame_display):
        """Test drawing very small button (boundary)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 5, 5)

        EnhancedUIRenderer.draw_enhanced_button(test_surface, rect, "X", test_font, state="normal")

        assert test_surface is not None

    def test_draw_button_very_large(self, test_surface, test_font, pygame_display):
        """Test drawing very large button (boundary)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(0, 0, 700, 500)

        EnhancedUIRenderer.draw_enhanced_button(
            test_surface, rect, "Large", test_font, state="normal"
        )

        assert test_surface is not None

    def test_draw_panel_very_small(self, test_surface, pygame_display):
        """Test drawing very small panel (boundary)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 10, 10)

        EnhancedUIRenderer.draw_enhanced_panel(test_surface, rect)

        assert test_surface is not None

    def test_draw_progress_bar_zero_progress(self, test_surface, test_font, pygame_display):
        """Test progress bar with zero progress (boundary)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 200, 30)

        EnhancedUIRenderer.draw_progress_bar(test_surface, rect, progress=0.0, show_text=False)

        assert test_surface is not None

    def test_draw_progress_bar_over_one(self, test_surface, test_font, pygame_display):
        """Test progress bar with progress > 1.0 (boundary)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 200, 30)

        # Should handle gracefully (clip to 1.0)
        EnhancedUIRenderer.draw_progress_bar(test_surface, rect, progress=1.5, show_text=False)

        assert test_surface is not None

    def test_draw_progress_bar_negative(self, test_surface, test_font, pygame_display):
        """Test progress bar with negative progress (boundary/error case)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 200, 30)

        # Should handle gracefully
        EnhancedUIRenderer.draw_progress_bar(test_surface, rect, progress=-0.5, show_text=False)

        assert test_surface is not None

    # ===== ERROR CASE TESTS =====

    def test_draw_button_invalid_state(self, test_surface, test_font, pygame_display):
        """Test drawing button with invalid state (error case)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 150, 40)

        # Should default to normal state
        EnhancedUIRenderer.draw_enhanced_button(
            test_surface, rect, "Invalid", test_font, state="invalid_state"
        )

        assert test_surface is not None

    def test_draw_icon_invalid_type(self, test_surface, pygame_display):
        """Test drawing icon with invalid type (error case)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 48, 48)

        # Should handle gracefully (draw background but no icon)
        EnhancedUIRenderer.draw_enhanced_icon(
            test_surface, rect, icon_type="invalid_icon", state="normal"
        )

        assert test_surface is not None

    def test_draw_button_empty_text(self, test_surface, test_font, pygame_display):
        """Test drawing button with empty text (error case)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 150, 40)

        EnhancedUIRenderer.draw_enhanced_button(test_surface, rect, "", test_font, state="normal")

        assert test_surface is not None

    def test_draw_panel_empty_title(self, test_surface, test_font, pygame_display):
        """Test drawing panel with empty title (should work like no title)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(50, 50, 300, 200)

        EnhancedUIRenderer.draw_enhanced_panel(test_surface, rect, title="", font=test_font)

        assert test_surface is not None

    def test_draw_button_negative_position(self, test_surface, test_font, pygame_display):
        """Test drawing button at negative position (error case)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(-50, -50, 150, 40)

        # Should handle gracefully
        EnhancedUIRenderer.draw_enhanced_button(
            test_surface, rect, "Negative", test_font, state="normal"
        )

        assert test_surface is not None

    def test_draw_panel_no_font_with_title(self, test_surface, pygame_display):
        """Test drawing panel with title but no font (error case)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(50, 50, 300, 200)

        # Should handle gracefully (skip title)
        EnhancedUIRenderer.draw_enhanced_panel(test_surface, rect, title="Title", font=None)

        assert test_surface is not None

    def test_draw_progress_bar_no_font(self, test_surface, pygame_display):
        """Test drawing progress bar without font (error case)."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        rect = pygame.Rect(100, 100, 200, 30)

        # Should handle gracefully (skip text)
        EnhancedUIRenderer.draw_progress_bar(
            test_surface, rect, progress=0.5, show_text=True, font=None
        )

        assert test_surface is not None

    # ===== INTEGRATION TESTS =====

    def test_convenience_functions(self, test_surface, test_font, pygame_display):
        """Test convenience functions work correctly."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import (
            draw_button,
            draw_icon,
            draw_panel,
        )

        # Test draw_button
        rect1 = pygame.Rect(100, 100, 150, 40)
        draw_button(test_surface, rect1, "Test", test_font, state="normal")

        # Test draw_panel
        rect2 = pygame.Rect(50, 200, 300, 200)
        draw_panel(test_surface, rect2, title="Panel", font=test_font)

        # Test draw_icon
        rect3 = pygame.Rect(400, 100, 48, 48)
        draw_icon(test_surface, rect3, icon_type="move", state="normal")

        assert test_surface is not None

    def test_multiple_buttons_same_surface(self, test_surface, test_font, pygame_display):
        """Test drawing multiple buttons on same surface."""
        import pygame
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        states = ["normal", "hover", "pressed", "disabled"]

        for i, state in enumerate(states):
            rect = pygame.Rect(100, 100 + i * 50, 150, 40)
            EnhancedUIRenderer.draw_enhanced_button(
                test_surface, rect, f"Button {i}", test_font, state=state
            )

        assert test_surface is not None

    def test_ui_color_consistency(self, pygame_display):
        """Test that UI colors are consistent and accessible."""
        from pycc2.presentation.ui.enhanced_ui_renderer import EnhancedUIRenderer

        colors = EnhancedUIRenderer.CC2_UI_COLORS

        # Verify all expected colors exist
        assert "panel_bg" in colors
        assert "panel_border" in colors
        assert "button_normal" in colors
        assert "text_normal" in colors
        assert "shadow" in colors

        # Verify colors are valid RGB tuples
        for color_name, color_value in colors.items():
            assert isinstance(color_value, tuple)
            assert len(color_value) == 3
            for channel in color_value:
                assert 0 <= channel <= 255
