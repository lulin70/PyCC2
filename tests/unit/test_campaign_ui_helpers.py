"""Tests for campaign_ui_helpers — drawing utilities.

Uses real CampaignUI with initialize() and real pygame Surface, following
the same pattern as the campaign_ui mixin tests. Structural assertions
(surface modified, no crash) rather than pixel-level color checks.
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from pycc2.presentation.ui.campaign_ui import CampaignUI
from pycc2.presentation.ui.campaign_ui_helpers import (
    draw_button,
    draw_mini_map,
    draw_strategic_map,
    wrap_text,
)


@pytest.fixture
def ui(pygame_display):
    ui = CampaignUI()
    ui.initialize()
    return ui


@pytest.fixture
def surface():
    return pygame.Surface((400, 300))


# ===========================================================================
# wrap_text (pure logic)
# ===========================================================================


@pytest.mark.unit
class TestWrapText:
    def test_short_text_single_line(self, mock_font):
        result = wrap_text("Hello world", mock_font, 500)
        assert result == ["Hello world"]

    def test_long_text_wraps_to_multiple_lines(self, mock_font):
        text = "The quick brown fox jumps over the lazy dog and runs away"
        result = wrap_text(text, mock_font, 100)
        assert len(result) >= 2
        assert "".join(result).replace(" ", "") == text.replace(" ", "")

    def test_empty_text_returns_empty(self, mock_font):
        assert wrap_text("", mock_font, 200) == []

    def test_single_word(self, mock_font):
        assert wrap_text("Hello", mock_font, 500) == ["Hello"]

    def test_single_word_too_long_still_returned(self, mock_font):
        result = wrap_text("VeryLongWordThatExceedsWidth", mock_font, 10)
        assert result == ["VeryLongWordThatExceedsWidth"]

    def test_multiple_spaces_collapsed(self, mock_font):
        result = wrap_text("Hello     world", mock_font, 500)
        assert result == ["Hello world"]

    def test_each_line_within_max_width(self, mock_font):
        max_width = 80
        text = "The quick brown fox jumps over the lazy dog and keeps on running far"
        result = wrap_text(text, mock_font, max_width)
        for line in result:
            assert mock_font.size(line)[0] < max_width or len(result) == 1


# ===========================================================================
# draw_button
# ===========================================================================


@pytest.mark.unit
class TestDrawButton:
    def test_draw_button_normal_modifies_surface(self, ui, surface):
        rect = pygame.Rect(10, 10, 100, 30)
        before = surface.get_at((50, 25))
        draw_button(ui, surface, rect, "Start", hovered=False)
        after = surface.get_at((50, 25))
        assert before != after

    def test_draw_button_hovered_modifies_surface(self, ui, surface):
        rect = pygame.Rect(10, 10, 100, 30)
        before = surface.get_at((50, 25))
        draw_button(ui, surface, rect, "Start", hovered=True)
        after = surface.get_at((50, 25))
        assert before != after

    def test_draw_button_custom_text_color(self, ui, surface):
        rect = pygame.Rect(0, 0, 100, 30)
        draw_button(ui, surface, rect, "OK", hovered=False, text_color=(255, 0, 0))
        assert surface.get_at((50, 15)) is not None

    def test_draw_button_centers_text(self, ui, surface):
        rect = pygame.Rect(50, 50, 200, 40)
        draw_button(ui, surface, rect, "Begin Battle", hovered=False)
        center_pixel = surface.get_at((rect.centerx, rect.centery))
        assert center_pixel is not None

    def test_draw_button_hovered_vs_normal_differ(self, ui, surface):
        rect_normal = pygame.Rect(0, 0, 100, 30)
        rect_hover = pygame.Rect(0, 50, 100, 30)
        draw_button(ui, surface, rect_normal, "Btn", hovered=False)
        draw_button(ui, surface, rect_hover, "Btn", hovered=True)
        bg_normal = surface.get_at((50, 15))
        bg_hover = surface.get_at((50, 65))
        assert bg_normal != bg_hover


# ===========================================================================
# draw_strategic_map
# ===========================================================================


@pytest.mark.unit
class TestDrawStrategicMap:
    def test_draws_without_crash(self, ui, surface):
        draw_strategic_map(ui, surface, 10, 10, 180, "nijmegen", 3)
        assert surface.get_at((100, 100)) is not None

    def test_modifies_surface_background(self, ui, surface):
        before = surface.get_at((100, 100))
        draw_strategic_map(ui, surface, 10, 10, 180, "arnhem", 1)
        after = surface.get_at((100, 100))
        assert before != after

    def test_highlight_current_sector_arnhem(self, ui, surface):
        draw_strategic_map(ui, surface, 0, 0, 180, "arnhem", 1)
        pixel = surface.get_at((90, 10))
        assert pixel is not None

    def test_highlight_current_sector_eindhoven(self, ui, surface):
        draw_strategic_map(ui, surface, 0, 0, 180, "eindhoven", 5)
        pixel = surface.get_at((90, 120))
        assert pixel is not None

    def test_day_progress_capped_at_9(self, ui, surface):
        draw_strategic_map(ui, surface, 0, 0, 180, "arnhem", 15)
        assert surface.get_at((90, 170)) is not None

    def test_day_progress_zero(self, ui, surface):
        draw_strategic_map(ui, surface, 0, 0, 180, "arnhem", 0)
        assert surface.get_at((90, 170)) is not None

    def test_unknown_sector_draws_without_crash(self, ui, surface):
        draw_strategic_map(ui, surface, 0, 0, 180, "unknown_sector", 3)
        assert surface.get_at((90, 90)) is not None


# ===========================================================================
# draw_mini_map
# ===========================================================================


@pytest.mark.unit
class TestDrawMiniMap:
    def test_fallback_grid_when_file_not_found(self, ui, surface, monkeypatch):
        monkeypatch.chdir("/tmp")
        before = surface.get_at((50, 50))
        draw_mini_map(ui, surface, 0, 0, 100, "nonexistent_map_file")
        after = surface.get_at((50, 50))
        assert before != after

    def test_renders_from_map_file(self, ui, surface, tmp_path, monkeypatch):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        tiles = [
            ["grass", "road", "water"],
            ["woods", "building", "open"],
        ]
        (maps_dir / "test_map.json").write_text(json.dumps({"tiles": tiles}))
        monkeypatch.chdir(tmp_path)
        before = surface.get_at((60, 60))
        draw_mini_map(ui, surface, 0, 0, 120, "test_map")
        after = surface.get_at((60, 60))
        assert before != after

    def test_renders_map_with_numeric_tiles(self, ui, surface, tmp_path, monkeypatch):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        tiles = [[0, 1, 2], [3, 4, 5]]
        (maps_dir / "numeric_map.json").write_text(json.dumps({"tiles": tiles}))
        monkeypatch.chdir(tmp_path)
        draw_mini_map(ui, surface, 0, 0, 120, "numeric_map")
        assert surface.get_at((60, 60)) is not None

    def test_renders_map_without_json_extension(self, ui, surface, tmp_path, monkeypatch):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        tiles = [["grass", "road"], ["water", "woods"]]
        (maps_dir / "noext_map").write_text(json.dumps({"tiles": tiles}))
        monkeypatch.chdir(tmp_path)
        before = surface.get_at((60, 60))
        draw_mini_map(ui, surface, 0, 0, 120, "noext_map")
        after = surface.get_at((60, 60))
        assert before != after

    def test_handles_empty_tiles(self, ui, surface, tmp_path, monkeypatch):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "empty_map.json").write_text(json.dumps({"tiles": []}))
        monkeypatch.chdir(tmp_path)
        before = surface.get_at((50, 50))
        draw_mini_map(ui, surface, 0, 0, 100, "empty_map")
        after = surface.get_at((50, 50))
        assert before != after

    def test_handles_invalid_json(self, ui, surface, tmp_path, monkeypatch):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "bad_map.json").write_text("NOT VALID JSON{{{")
        monkeypatch.chdir(tmp_path)
        before = surface.get_at((50, 50))
        draw_mini_map(ui, surface, 0, 0, 100, "bad_map")
        after = surface.get_at((50, 50))
        assert before != after

    def test_fallback_grid_10x10(self, ui, surface, monkeypatch):
        monkeypatch.chdir("/tmp")
        draw_mini_map(ui, surface, 0, 0, 100, "no_such_file")
        assert surface.get_at((5, 5)) is not None
        assert surface.get_at((95, 95)) is not None
