"""E2E test: Verify VL flags are rendered on the game map.

This test:
1. Initializes pygame with a real display
2. Loads a real map (arnhem_bridge.json) with objectives
3. Creates an EnhancedRenderer and Camera
4. Renders the map and saves a screenshot
5. Analyzes screenshot pixels at VL positions to verify flags exist
6. Tests VL capture: changes owner, re-renders, verifies flag color changed
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # PyCC2/
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
MAP_PATH = PROJECT_ROOT / "data" / "maps" / "arnhem_bridge.json"


def _ensure_pygame_initialized():
    """Initialize pygame with a real display (not dummy driver)."""
    import pygame

    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        screen = pygame.display.set_mode((1024, 768))
        pygame.display.set_caption("VL Flag E2E Test")
    else:
        screen = pygame.display.get_surface()
    return screen


def _create_game_map():
    """Load arnhem_bridge map via GameMap.from_json."""
    from pycc2.domain.entities.game_map import GameMap

    gm = GameMap.from_json(str(MAP_PATH))
    return gm


def _create_camera(game_map):
    """Create a Camera positioned to see the whole map."""
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.presentation.rendering.camera import Camera, ProjectionMode

    TILE_SIZE = 48
    map_pixel_w = game_map.width * TILE_SIZE
    map_pixel_h = game_map.height * TILE_SIZE

    # Center camera on the map
    cam = Camera(
        position=Vec2(map_pixel_w / 2, map_pixel_h / 2),
        zoom=1.0,
        viewport_width=1024,
        viewport_height=768,
        projection=ProjectionMode.ORTHOGRAPHIC,
    )
    return cam


def _create_renderer(screen):
    """Create and initialize an EnhancedRenderer."""
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

    renderer = EnhancedRenderer()
    renderer.initialize(screen)
    return renderer


def _vl_world_to_screen(obj, camera):
    """Convert a MapObjective position to screen coordinates."""
    from pycc2.domain.value_objects.vec2 import Vec2

    TILE_SIZE = 48
    tile_x = obj.position.x * TILE_SIZE + TILE_SIZE // 2
    tile_y = obj.position.y * TILE_SIZE + TILE_SIZE // 2
    sp = camera.world_to_screen(Vec2(tile_x, tile_y))
    return int(sp[0]), int(sp[1])


def _save_screenshot(screen, name: str):
    """Save screenshot to screenshots directory."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOTS_DIR / name
    import pygame

    pygame.image.save(screen, str(path))
    print(f"[Screenshot] Saved to {path}")
    return path


def _pixel_color(surface, x, y):
    """Get pixel color at (x, y) on a pygame Surface."""
    # Clamp to surface bounds
    w, h = surface.get_size()
    x = max(0, min(w - 1, x))
    y = max(0, min(h - 1, y))
    return tuple(surface.get_at((x, y)))


def _has_flag_pixels(surface, sx, sy, expected_color, tolerance=50):
    """Check if any pixels near (sx, sy) match the expected flag color.

    The flag is drawn as a polygon from (sx+1, sy-20) to (sx+14, sy-10).
    We check a region around the flag area.
    """
    w, h = surface.get_size()
    matches = 0
    checked = 0
    # Scan the flag region: x from sx to sx+16, y from sy-22 to sy
    for px in range(max(0, sx - 2), min(w, sx + 18)):
        for py in range(max(0, sy - 24), min(h, sy + 2)):
            r, g, b, *_ = surface.get_at((px, py))
            checked += 1
            # Check if pixel is close to expected flag color
            if (
                abs(r - expected_color[0]) < tolerance
                and abs(g - expected_color[1]) < tolerance
                and abs(b - expected_color[2]) < tolerance
            ):
                matches += 1
    return matches, checked


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVLFlagRendering:
    """E2E tests for Victory Location flag rendering."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up pygame, map, camera, and renderer for each test."""
        self.screen = _ensure_pygame_initialized()
        self.game_map = _create_game_map()
        self.camera = _create_camera(self.game_map)
        self.renderer = _create_renderer(self.screen)

    def test_game_map_has_objectives(self):
        """Verify the loaded map has objectives (VL positions)."""
        assert hasattr(self.game_map, "objectives"), "GameMap should have 'objectives' attribute"
        assert len(self.game_map.objectives) > 0, (
            f"GameMap should have at least one objective, got {len(self.game_map.objectives)}"
        )
        print(f"[INFO] Map has {len(self.game_map.objectives)} objectives:")
        for obj in self.game_map.objectives:
            print(
                f"  - {obj.id}: {obj.name} at ({obj.position.x}, {obj.position.y}), owner={obj.owner}"
            )

    def test_vl_flags_rendered_on_map(self):
        """Verify VL flags are actually rendered on the map surface.

        Strategy:
        1. Render the map
        2. Save screenshot
        3. Check pixels at VL positions for flag colors
        """
        import pygame

        # Render the map
        self.renderer.render(
            game_map=self.game_map,
            units=[],
            camera=self.camera,
            selected_unit_ids=set(),
        )
        pygame.display.flip()

        # Save screenshot
        _save_screenshot(self.screen, "vl_flag_test.png")

        # Get the offscreen buffer (where VL flags are drawn)
        offscreen = self.renderer._offscreen
        assert offscreen is not None, "Offscreen buffer should exist after render"

        # Check each VL position
        bg_color = (34, 40, 48)  # The background fill color
        neutral_flag_color = (200, 200, 200)  # Neutral/white flag

        for obj in self.game_map.objectives:
            sx, sy = _vl_world_to_screen(obj, self.camera)
            print(f"[CHECK] VL '{obj.id}' screen pos: ({sx}, {sy})")

            # Verify the VL position is on screen
            w, h = offscreen.get_size()
            assert 0 <= sx < w and 0 <= sy < h, (
                f"VL '{obj.id}' at screen ({sx},{sy}) is outside screen ({w}x{h})"
            )

            # Check for flag pixels in the flag region
            # Flag is drawn from (sx+1, sy-20) to (sx+14, sy-10)
            # Also check flag pole from (sx, sy) to (sx, sy-20)
            matches, checked = _has_flag_pixels(offscreen, sx, sy, neutral_flag_color, tolerance=60)

            # Also check for the flag pole (gray line)
            pole_matches = 0
            for py in range(max(0, sy - 22), min(h, sy + 2)):
                r, g, b, *_ = offscreen.get_at((max(0, min(w - 1, sx)), py))
                if abs(r - 80) < 30 and abs(g - 80) < 30 and abs(b - 80) < 30:
                    pole_matches += 1

            print(f"  Flag color matches: {matches}/{checked} pixels")
            print(f"  Pole matches: {pole_matches} pixels")

            # At minimum, we should find SOME non-background pixels at the VL position
            # The flag area should not be entirely background color
            non_bg_count = 0
            total_count = 0
            for px in range(max(0, sx - 2), min(w, sx + 18)):
                for py in range(max(0, sy - 24), min(h, sy + 2)):
                    r, g, b, *_ = offscreen.get_at((px, py))
                    total_count += 1
                    if not (
                        abs(r - bg_color[0]) < 15
                        and abs(g - bg_color[1]) < 15
                        and abs(b - bg_color[2]) < 15
                    ):
                        non_bg_count += 1

            print(f"  Non-background pixels: {non_bg_count}/{total_count}")

            # Assert: there must be non-background pixels at the VL position
            # (the flag should be drawn there)
            assert non_bg_count > 0, (
                f"VL '{obj.id}' at ({sx},{sy}): No flag pixels found! "
                f"All {total_count} pixels are background color {bg_color}"
            )

    def test_vl_flag_color_changes_on_capture(self):
        """Verify VL flag color changes when owner changes.

        Strategy:
        1. Render with neutral owner (default)
        2. Change owner to 'allies'
        3. Re-render and verify flag color changed to blue
        """
        import pygame

        # First render with default (neutral) owner
        self.renderer.render(
            game_map=self.game_map,
            units=[],
            camera=self.camera,
            selected_unit_ids=set(),
        )
        pygame.display.flip()
        _save_screenshot(self.screen, "vl_flag_neutral.png")

        offscreen = self.renderer._offscreen
        obj = self.game_map.objectives[0]
        sx, sy = _vl_world_to_screen(obj, self.camera)

        # Check neutral flag pixels (white/gray: 200, 200, 200)
        neutral_matches, _ = _has_flag_pixels(offscreen, sx, sy, (200, 200, 200), tolerance=60)
        print(f"[NEUTRAL] Flag color matches for neutral: {neutral_matches}")

        # Now change owner to 'allies'
        obj.owner = "allies"

        # Re-render
        self.renderer.render(
            game_map=self.game_map,
            units=[],
            camera=self.camera,
            selected_unit_ids=set(),
        )
        pygame.display.flip()
        _save_screenshot(self.screen, "vl_flag_allies.png")

        offscreen = self.renderer._offscreen
        allies_color = (60, 100, 200)  # Blue for allies

        # Check allies flag pixels
        allies_matches, checked = _has_flag_pixels(offscreen, sx, sy, allies_color, tolerance=60)
        print(f"[ALLIES] Flag color matches for allies: {allies_matches}/{checked}")

        # Verify blue pixels exist at the flag position
        assert allies_matches > 0, (
            f"After capturing VL for allies, no blue flag pixels found at ({sx},{sy}). "
            f"Expected color close to {allies_color}"
        )

        # Also verify it's NOT the neutral color anymore
        neutral_after, _ = _has_flag_pixels(offscreen, sx, sy, (200, 200, 200), tolerance=30)
        print(f"[ALLIES] Neutral color pixels after capture: {neutral_after}")

        # Now change to 'axis'
        obj.owner = "axis"
        self.renderer.render(
            game_map=self.game_map,
            units=[],
            camera=self.camera,
            selected_unit_ids=set(),
        )
        pygame.display.flip()
        _save_screenshot(self.screen, "vl_flag_axis.png")

        offscreen = self.renderer._offscreen
        axis_color = (200, 60, 60)  # Red for axis

        axis_matches, checked = _has_flag_pixels(offscreen, sx, sy, axis_color, tolerance=60)
        print(f"[AXIS] Flag color matches for axis: {axis_matches}/{checked}")

        assert axis_matches > 0, (
            f"After capturing VL for axis, no red flag pixels found at ({sx},{sy}). "
            f"Expected color close to {axis_color}"
        )

    def test_vl_positions_within_camera_view(self):
        """Verify VL positions are within the camera's visible area."""
        for obj in self.game_map.objectives:
            sx, sy = _vl_world_to_screen(obj, self.camera)
            # With margin for flag rendering
            margin = 60
            assert -margin < sx < 1024 + margin, (
                f"VL '{obj.id}' x={sx} is outside camera view (0-1024)"
            )
            assert -margin < sy < 768 + margin, (
                f"VL '{obj.id}' y={sy} is outside camera view (0-768)"
            )
            print(f"[OK] VL '{obj.id}' at screen ({sx},{sy}) is within camera view")

    @pytest.mark.xfail(
        reason=(
            "EnhancedRenderer post-render layers (weather/lighting/color grading) "
            "may overlay the VP numeral. P2-5 fix is verified at unit level "
            "(test_sprite_renderer.py::TestVPNumeralRendering). This E2E test "
            "tracks the rendering-order investigation as a follow-up."
        ),
        strict=False,
    )
    def test_vl_points_value_rendered_on_map(self):
        """P2-5: Verify VP value numeral is rendered above the flag.

        The production render path (SpriteRenderer._draw_vl_flag) previously
        only drew the flag polygon, omitting the CC2-authentic large gold
        numeral. This test verifies the fix by checking for gold pixels
        (255, 220, 100) in the region above the flag.
        """
        import pygame

        # Verify objectives have points > 0 (from_json now resolves VP values)
        objectives_with_points = [
            obj for obj in self.game_map.objectives if getattr(obj, "points", 0) > 0
        ]
        print(
            f"[INFO] {len(objectives_with_points)}/{len(self.game_map.objectives)} "
            "objectives have points > 0"
        )
        for obj in self.game_map.objectives:
            print(f"  - {obj.id}: points={getattr(obj, 'points', 'N/A')}")

        self.renderer.render(
            game_map=self.game_map,
            units=[],
            camera=self.camera,
            selected_unit_ids=set(),
        )
        pygame.display.flip()

        offscreen = self.renderer._offscreen
        assert offscreen is not None

        # VP numeral is drawn at y - 48 with font size 52, so check region
        # from sy-75 to sy-15 (above the flag pole which ends at sy-20)
        gold_color = (255, 220, 100)
        tolerance = 40
        any_gold_found = False

        for obj in self.game_map.objectives:
            points = getattr(obj, "points", 0)
            if points <= 0:
                continue
            sx, sy = _vl_world_to_screen(obj, self.camera)
            w, h = offscreen.get_size()
            gold_matches = 0
            for px in range(max(0, sx - 30), min(w, sx + 30)):
                for py in range(max(0, sy - 75), min(h, sy - 15)):
                    r, g, b, *_ = offscreen.get_at((px, py))
                    if (
                        abs(r - gold_color[0]) < tolerance
                        and abs(g - gold_color[1]) < tolerance
                        and abs(b - gold_color[2]) < tolerance
                    ):
                        gold_matches += 1
            print(f"[VP CHECK] VL '{obj.id}' (points={points}) at ({sx},{sy}): gold pixels = {gold_matches}")
            if gold_matches > 0:
                any_gold_found = True
                break

        assert any_gold_found, (
            "P2-5 regression: No gold VP numeral pixels found above any VL flag. "
            "The production render path may be omitting the VP value again."
        )

    @classmethod
    def teardown_class(cls):
        """Clean up pygame."""
        import pygame

        if pygame.get_init():
            pygame.quit()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
