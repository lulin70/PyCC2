"""E2E Test: Infantry Sprite Rendering Verification

Tests all infantry sprite variations render correctly:
1. For each of 8 directions: render idle sprite, verify size, verify non-transparent pixels
2. For each of 8 animation states: render sprite, verify non-empty surface
3. Generate full animation sheet, verify dimensions
4. Test InfantryAnimator state transitions
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_non_transparent_pixels(surface: pygame.Surface) -> bool:
    """Check if a surface has at least one non-transparent pixel."""
    w, h = surface.get_size()
    if w == 0 or h == 0:
        return False
    try:
        # Sample a grid of pixels for efficiency
        step = max(1, min(w, h) // 8)
        for x in range(0, w, step):
            for y in range(0, h, step):
                pixel = surface.get_at((x, y))
                if pixel.a > 0:
                    return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInfantryRenderingE2E:
    """Full E2E test for infantry sprite rendering."""

    def test_01_idle_sprite_8_directions(self):
        """Step 1: For each of 8 directions, render idle sprite and verify."""
        from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D, Direction, Faction

        directions = [
            Direction.NORTH, Direction.NORTHEAST, Direction.EAST, Direction.SOUTHEAST,
            Direction.SOUTH, Direction.SOUTHWEST, Direction.WEST, Direction.NORTHWEST,
        ]

        for direction in directions:
            sprite = PixelArtist3D.create_infantry_sprite(
                direction=direction,
                faction=Faction.ALLIES,
                state="idle",
                frame=0,
            )
            assert sprite is not None, f"Sprite should not be None for {direction}"
            w, h = sprite.get_size()
            assert w > 0 and h > 0, f"Sprite size should be > 0 for {direction}, got {w}x{h}"
            assert _has_non_transparent_pixels(sprite), f"Sprite should have visible pixels for {direction}"

    def test_02_all_animation_states_render(self):
        """Step 2: For each of 8 animation states, render sprite and verify non-empty."""
        from pycc2.presentation.rendering.pixel_artist_3d import (
            PixelArtist3D, InfantryAnimState, Direction, Faction,
        )

        anim_states = [
            InfantryAnimState.IDLE,
            InfantryAnimState.WALK_1,
            InfantryAnimState.WALK_2,
            InfantryAnimState.SHOOT,
            InfantryAnimState.PRONE,
            InfantryAnimState.DIE_1,
            InfantryAnimState.DIE_2,
            InfantryAnimState.DEAD,
        ]

        for anim_state in anim_states:
            state, frame = PixelArtist3D._anim_state_to_params(anim_state)
            sprite = PixelArtist3D.create_infantry_sprite(
                direction=Direction.SOUTH,
                faction=Faction.ALLIES,
                state=state,
                frame=frame,
            )
            assert sprite is not None, f"Sprite should not be None for {anim_state}"
            w, h = sprite.get_size()
            assert w > 0 and h > 0, f"Sprite size should be > 0 for {anim_state}, got {w}x{h}"

    def test_03_full_animation_sheet_dimensions(self):
        """Step 3: Generate full animation sheet and verify dimensions (8x8)."""
        from pycc2.presentation.rendering.pixel_artist_3d import (
            PixelArtist3D, Faction,
        )

        sheet, direction_order, anim_state_order = PixelArtist3D.create_infantry_animation_sheet(
            faction=Faction.ALLIES,
        )

        assert sheet is not None, "Animation sheet should not be None"
        w, h = sheet.get_size()
        # 8 directions x 24px = 192, 8 states x 24px = 192
        assert w == 192, f"Sheet width should be 192 (8*24), got {w}"
        assert h == 192, f"Sheet height should be 192 (8*24), got {h}"
        assert len(direction_order) == 8, "Should have 8 directions"
        assert len(anim_state_order) == 8, "Should have 8 animation states"

    def test_04_walk_cycle_transition(self):
        """Step 4a: IDLE -> WALK_1 -> WALK_2 -> IDLE (walk cycle)."""
        from pycc2.presentation.rendering.pixel_artist_3d import InfantryAnimator, InfantryAnimState

        animator = InfantryAnimator()
        assert animator.state == InfantryAnimState.IDLE

        # Start walking
        dt = 0.2  # Walk cycle interval
        animator.update(dt, is_moving=True)
        # After first tick, should be in walk cycle
        assert animator.state in (
            InfantryAnimState.WALK_1,
            InfantryAnimState.WALK_2,
            InfantryAnimState.IDLE,  # Could still be IDLE at cycle boundary
        ), f"Expected walk state, got {animator.state}"

        # Continue walking for several ticks
        states_seen = set()
        for _ in range(20):
            animator.update(dt, is_moving=True)
            states_seen.add(animator.state)

        # Should have seen walk states
        assert InfantryAnimState.WALK_1 in states_seen or InfantryAnimState.WALK_2 in states_seen, \
            f"Should have seen walk states, got {states_seen}"

        # Stop walking -> should return to IDLE
        animator.update(dt, is_moving=False)
        assert animator.state == InfantryAnimState.IDLE, \
            f"After stopping, should be IDLE, got {animator.state}"

    def test_04_fire_cycle_transition(self):
        """Step 4b: IDLE -> SHOOT -> IDLE (fire cycle)."""
        from pycc2.presentation.rendering.pixel_artist_3d import InfantryAnimator, InfantryAnimState

        animator = InfantryAnimator()
        assert animator.state == InfantryAnimState.IDLE

        # Start firing
        animator.update(0.01, is_firing=True)
        assert animator.state == InfantryAnimState.SHOOT, \
            f"While firing, should be SHOOT, got {animator.state}"

        # Stop firing -> should return to IDLE
        animator.update(0.01, is_firing=False)
        assert animator.state == InfantryAnimState.IDLE, \
            f"After firing, should be IDLE, got {animator.state}"

    def test_04_death_sequence_irreversible(self):
        """Step 4c: IDLE -> DIE_1 -> DIE_2 -> DEAD (death sequence, irreversible)."""
        from pycc2.presentation.rendering.pixel_artist_3d import InfantryAnimator, InfantryAnimState

        animator = InfantryAnimator()
        assert animator.state == InfantryAnimState.IDLE

        # Trigger death
        animator.update(0.01, is_dead=True)
        assert animator.state == InfantryAnimState.DIE_1, \
            f"First death frame should be DIE_1, got {animator.state}"

        # Continue death sequence
        animator.update(0.3, is_dead=True)
        assert animator.state in (InfantryAnimState.DIE_1, InfantryAnimState.DIE_2, InfantryAnimState.DEAD), \
            f"Should progress through death, got {animator.state}"

        # Advance to DEAD
        animator.update(0.3, is_dead=True)
        animator.update(0.3, is_dead=True)

        # Once DEAD, should stay DEAD regardless of input
        assert animator.state == InfantryAnimState.DEAD, \
            f"Should reach DEAD state, got {animator.state}"

        # Try to revive (should not work)
        animator.update(0.01, is_moving=True, is_firing=True)
        assert animator.state == InfantryAnimState.DEAD, \
            f"DEAD state should be irreversible, got {animator.state}"

    def test_04_prone_transition(self):
        """Step 4d: IDLE -> PRONE (prone transition)."""
        from pycc2.presentation.rendering.pixel_artist_3d import InfantryAnimator, InfantryAnimState

        animator = InfantryAnimator()
        assert animator.state == InfantryAnimState.IDLE

        # Go prone
        animator.update(0.01, is_prone=True)
        assert animator.state == InfantryAnimState.PRONE, \
            f"While prone, should be PRONE, got {animator.state}"

        # Stand up
        animator.update(0.01, is_prone=False)
        assert animator.state == InfantryAnimState.IDLE, \
            f"After standing up, should be IDLE, got {animator.state}"

    def test_05_axis_faction_sprites(self):
        """Step 5: Verify axis faction sprites also render correctly."""
        from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D, Direction, Faction

        sprite = PixelArtist3D.create_infantry_sprite(
            direction=Direction.SOUTH,
            faction=Faction.AXIS,
            state="idle",
            frame=0,
        )
        assert sprite is not None
        assert _has_non_transparent_pixels(sprite), "Axis sprite should have visible pixels"
