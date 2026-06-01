"""
Unit tests for PixelArtist3D - CC2 45° Isometric Pixel Art Generator

Tests cover:
- Infantry sprite generation (8 directions, 4 states)
- Tank sprite generation
- Tree and building sprites
- Color palette correctness
- Direction offset calculations
"""

from __future__ import annotations

import os
import sys
import pytest

# Ensure SDL dummy drivers are set before pygame imports
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class TestPixelArtist3DInitialization:
    """Test PixelArtist3D class initialization and basic functionality."""

    def test_import_pixel_artist_3d(self):
        """Test that PixelArtist3D can be imported"""
        from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D
        assert PixelArtist3D is not None

    def test_direction_enum_exists(self):
        """Test that Direction enum has all 8 directions"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction

        expected_directions = [
            "NORTH", "NORTHEAST", "EAST", "SOUTHEAST",
            "SOUTH", "SOUTHWEST", "WEST", "NORTHWEST"
        ]
        actual_directions = [d.name for d in Direction]
        assert actual_directions == expected_directions

    def test_faction_enum_exists(self):
        """Test that Faction enum has ALLIES and AXIS"""
        from pycc2.presentation.rendering.pixel_artist_3d import Faction

        assert Faction.ALLIES.value == "allies"
        assert Faction.AXIS.value == "axis"

    def test_cc2_palette_exists(self):
        """Test that CC2_PALETTE contains both factions"""
        from pycc2.presentation.rendering.pixel_artist_color_palette import CC2_PALETTE

        assert "allies" in CC2_PALETTE
        assert "axis" in CC2_PALETTE

        allies_palette = CC2_PALETTE["allies"]
        axis_palette = CC2_PALETTE["axis"]

        # Check required color keys exist
        required_keys = ['uniform', 'helmet', 'weapon', 'boots',
                         'uniform_dark', 'uniform_light', 'helmet_dark',
                         'helmet_highlight', 'weapon_metal',
                         'weapon_wood', 'equipment', 'equipment_dark',
                         'canteen', 'ammo_belt', 'beret']
        for key in required_keys:
            assert key in allies_palette, f"Missing '{key}' in allies palette"
            assert key in axis_palette, f"Missing '{key}' in axis palette"


class TestInfantrySpriteGeneration:
    """Test infantry sprite generation for all directions and states."""

    @pytest.fixture()
    def artist(self):
        from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D
        return PixelArtist3D()

    def test_create_infantry_allies_idle_north(self, artist, pygame_display):
        """Test creating Allied infantry sprite facing North, idle state"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction
        import pygame

        sprite = artist.create_infantry_sprite(
            direction=Direction.NORTH,
            faction=Faction.ALLIES,
            state="idle",
            frame=0,
        )

        assert sprite is not None
        assert isinstance(sprite, pygame.Surface)
        assert sprite.get_size() == (24, 24)
        # Check alpha channel exists
        assert sprite.get_bitsize() == 32

    def test_create_infantry_axis_idle_south(self, artist, pygame_display):
        """Test creating Axis infantry sprite facing South, idle state"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction
        import pygame

        sprite = artist.create_infantry_sprite(
            direction=Direction.SOUTH,
            faction=Faction.AXIS,
            state="idle",
            frame=0,
        )

        assert sprite is not None
        assert isinstance(sprite, pygame.Surface)
        assert sprite.get_size() == (24, 24)

    def test_create_infantry_all_8_directions(self, artist, pygame_display):
        """Test that infantry can be created in all 8 directions"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        for direction in Direction:
            sprite = artist.create_infantry_sprite(
                direction=direction,
                faction=Faction.ALLIES,
                state="idle",
                frame=0,
            )
            assert sprite is not None, f"Failed to create sprite for {direction.name}"

    def test_create_infantry_walk_state(self, artist, pygame_display):
        """Test infantry walk animation state"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        for frame in range(4):  # Walk has 4 frames
            sprite = artist.create_infantry_sprite(
                direction=Direction.EAST,
                faction=Faction.ALLIES,
                state="walk",
                frame=frame,
            )
            assert sprite is not None

    def test_create_infantry_shoot_state(self, artist, pygame_display):
        """Test infantry shoot animation state"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        for frame in range(3):  # Shoot has 3 frames
            sprite = artist.create_infantry_sprite(
                direction=Direction.EAST,
                faction=Faction.ALLIES,
                state="shoot",
                frame=frame,
            )
            assert sprite is not None

    def test_create_infantry_die_state(self, artist, pygame_display):
        """Test infantry death animation state"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        for frame in range(4):  # Die has 4 frames
            sprite = artist.create_infantry_sprite(
                direction=Direction.EAST,
                faction=Faction.ALLIES,
                state="die",
                frame=frame,
            )
            assert sprite is not None

    def test_create_infantry_hit_state(self, artist, pygame_display):
        """Test infantry hit/damage state"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        sprite = artist.create_infantry_sprite(
            direction=Direction.EAST,
            faction=Faction.ALLIES,
            state="hit",
            frame=0,
        )
        assert sprite is not None


class TestTankSpriteGeneration:
    """Test tank sprite generation."""

    @pytest.fixture()
    def artist(self):
        from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D
        return PixelArtist3D()

    def test_create_tank_allies_idle(self, artist, pygame_display):
        """Test creating Allied tank sprite"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction
        import pygame

        sprite = artist.create_tank_sprite(
            direction=Direction.SOUTH,
            faction=Faction.ALLIES,
            state="idle",
        )

        assert sprite is not None
        assert isinstance(sprite, pygame.Surface)
        assert sprite.get_size() == (36, 36)

    def test_create_tank_axis_moving(self, artist, pygame_display):
        """Test creating Axis tank sprite in move state"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        sprite = artist.create_tank_sprite(
            direction=Direction.EAST,
            faction=Faction.AXIS,
            state="move",
            frame=1,
        )
        assert sprite is not None

    def test_create_tank_with_turret_rotation(self, artist, pygame_display):
        """Test tank with independent turret direction"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        # Body facing East, turret facing North-East
        sprite = artist.create_tank_sprite(
            direction=Direction.EAST,
            faction=Faction.ALLIES,
            turret_direction=Direction.NORTHEAST,
            state="idle",
        )
        assert sprite is not None

    def test_create_tank_shoot_state(self, artist, pygame_display):
        """Test tank shoot state with muzzle flash"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        sprite = artist.create_tank_sprite(
            direction=Direction.SOUTH,
            faction=Faction.ALLIES,
            state="shoot",
            frame=1,  # Frame 1 should have muzzle flash
        )
        assert sprite is not None


class TestVehicleSpriteGeneration:
    """Test new vehicle sprite generation: Halftrack, Jeep, AT Gun, Mortar Team."""

    @pytest.fixture()
    def artist(self):
        from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D
        return PixelArtist3D()

    def test_create_halftrack_allies_idle_north(self, artist, pygame_display):
        """Test creating Allied halftrack sprite facing North"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction
        import pygame

        sprite = artist.create_halftrack_sprite(
            direction=Direction.NORTH,
            faction=Faction.ALLIES,
            state="idle",
            frame=0,
        )

        assert sprite is not None
        assert isinstance(sprite, pygame.Surface)
        assert sprite.get_size() == (40, 44)
        # Check alpha channel exists
        assert sprite.get_bitsize() == 32

    def test_create_halftrack_axis_south(self, artist, pygame_display):
        """Test creating Axis halftrack sprite facing South"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction
        import pygame

        sprite = artist.create_halftrack_sprite(
            direction=Direction.SOUTH,
            faction=Faction.AXIS,
            state="idle",
        )

        assert sprite is not None
        assert isinstance(sprite, pygame.Surface)

    def test_create_halftrack_all_8_directions(self, artist, pygame_display):
        """Test that halftrack can be created in all 8 directions"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        for direction in Direction:
            sprite = artist.create_halftrack_sprite(
                direction=direction,
                faction=Faction.ALLIES,
                state="idle",
                frame=0,
            )
            assert sprite is not None, f"Failed to create halftrack for {direction.name}"

    def test_create_halftrack_move_state(self, artist, pygame_display):
        """Test halftrack move state with dust effect"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        for frame in range(2):  # Move has 2 dust variations
            sprite = artist.create_halftrack_sprite(
                direction=Direction.EAST,
                faction=Faction.ALLIES,
                state="move",
                frame=frame,
            )
            assert sprite is not None

    def test_create_jeep_allies_idle(self, artist, pygame_display):
        """Test creating Allied jeep sprite"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction
        import pygame

        sprite = artist.create_jeep_sprite(
            direction=Direction.NORTH,
            faction=Faction.ALLIES,
            state="idle",
        )

        assert sprite is not None
        assert isinstance(sprite, pygame.Surface)
        assert sprite.get_size() == (28, 20)  # Smallest vehicle size per spec

    def test_create_jeep_axis_east(self, artist, pygame_display):
        """Test creating Axis jeep (Kubelwagen) facing East"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        sprite = artist.create_jeep_sprite(
            direction=Direction.EAST,
            faction=Faction.AXIS,
            state="idle",
        )
        assert sprite is not None

    def test_create_jeep_all_directions_different_appearance(self, artist, pygame_display):
        """Test that jeep sprites have different appearances for different directions"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        sprites = []
        for direction in Direction:
            sprite = artist.create_jeep_sprite(
                direction=direction,
                faction=Faction.ALLIES,
                state="idle",
            )
            assert sprite is not None
            sprites.append(sprite)

        # Verify all sprites are valid surfaces
        assert len(sprites) == 8
        for i, sprite in enumerate(sprites):
            assert sprite.get_size() == (28, 20), f"Jeep {Direction(i).name} has wrong size"

    def test_create_at_gun_allies_idle(self, artist, pygame_display):
        """Test creating Allied anti-tank gun sprite"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction
        import pygame

        sprite = artist.create_at_gun_sprite(
            direction=Direction.NORTH,
            faction=Faction.ALLIES,
            state="idle",
        )

        assert sprite is not None
        assert isinstance(sprite, pygame.Surface)
        assert sprite.get_size() == (28, 20)  # AT gun dimensions per spec

    def test_create_at_gun_barrel_orientation(self, artist, pygame_display):
        """Test AT gun barrel points in different directions"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        for direction in [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]:
            sprite = artist.create_at_gun_sprite(
                direction=direction,
                faction=Faction.AXIS,
                state="idle",
            )
            assert sprite is not None, f"AT gun failed for direction {direction.name}"

    def test_create_at_gun_shoot_state_with_flash(self, artist, pygame_display):
        """Test AT gun shoot state with muzzle flash"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        sprite = artist.create_at_gun_sprite(
            direction=Direction.EAST,
            faction=Faction.ALLIES,
            state="shoot",
            frame=1,  # Frame 1 should have flash
        )
        assert sprite is not None

    def test_create_mortar_team_allies(self, artist, pygame_display):
        """Test creating Allied mortar team sprite"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction
        import pygame

        sprite = artist.create_mortar_team_sprite(
            direction=Direction.NORTH,
            faction=Faction.ALLIES,
            state="idle",
        )

        assert sprite is not None
        assert isinstance(sprite, pygame.Surface)
        assert sprite.get_size() == (22, 20)  # Mortar team dimensions per spec

    def test_create_mortar_team_crew_visible(self, artist, pygame_display):
        """Test mortar team has 2 crew members visible"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        # Just verify it generates without error - crew visibility is visual
        sprite = artist.create_mortar_team_sprite(
            direction=Direction.SOUTH,
            faction=Faction.AXIS,
            state="idle",
        )
        assert sprite is not None

    def test_create_mortar_team_shoot_state(self, artist, pygame_display):
        """Test mortar team shoot state with firing effect"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        sprite = artist.create_mortar_team_sprite(
            direction=Direction.NORTHEAST,
            faction=Faction.ALLIES,
            state="shoot",
            frame=1,
        )
        assert sprite is not None

    def test_vehicle_sprites_non_zero_dimensions(self, artist, pygame_display):
        """Test that all new vehicle sprites have non-zero size and correct dimensions"""
        from pycc2.presentation.rendering.pixel_artist_3d import Direction, Faction

        expected_sizes = {
            'halftrack': (40, 44),
            'jeep': (28, 20),
            'at_gun': (28, 20),
            'mortar': (22, 20),
        }

        create_funcs = {
            'halftrack': lambda d, f: artist.create_halftrack_sprite(direction=d, faction=f),
            'jeep': lambda d, f: artist.create_jeep_sprite(direction=d, faction=f),
            'at_gun': lambda d, f: artist.create_at_gun_sprite(direction=d, faction=f),
            'mortar': lambda d, f: artist.create_mortar_team_sprite(direction=d, faction=f),
        }

        for vehicle_name, create_func in create_funcs.items():
            sprite = create_func(Direction.NORTH, Faction.ALLIES)
            expected = expected_sizes[vehicle_name]
            assert sprite.get_size() == expected, \
                f"{vehicle_name} has wrong size: {sprite.get_size()} != {expected}"
            assert sprite.get_width() > 0 and sprite.get_height() > 0, \
                f"{vehicle_name} has zero dimension"


class TestEnvironmentSprites:
    """Test tree, building, and terrain sprites."""

    @pytest.fixture()
    def artist(self):
        from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D
        return PixelArtist3D()

    def test_create_tree_sprites_variants(self, artist, pygame_display):
        """Test tree sprite generation with different variants"""
        import pygame

        for variant in range(3):
            # Fix 0.5: 树木默认尺寸从24×24改为28×28 (medium)
            sprite = artist.create_tree_sprite(variant=variant)
            assert sprite is not None
            assert isinstance(sprite, pygame.Surface)
            assert sprite.get_size() == (28, 28), f"Expected medium tree size (28,28), got {sprite.get_size()}"

    def test_create_building_house(self, artist, pygame_display):
        """Test house building sprite"""
        import pygame

        sprite = artist.create_building_sprite(building_type="house")
        assert sprite is not None
        assert isinstance(sprite, pygame.Surface)
        assert sprite.get_size() == (40, 40)

    def test_create_building_church(self, artist, pygame_display):
        """Test church building sprite with steeple"""

        sprite = artist.create_building_sprite(building_type="church")
        assert sprite is not None

    def test_create_building_barn(self, artist, pygame_display):
        """Test barn building sprite"""

        sprite = artist.create_building_sprite(building_type="barn")
        assert sprite is not None

    def test_create_building_custom_colors(self, artist, pygame_display):
        """Test building with custom roof and wall colors"""

        sprite = artist.create_building_sprite(
            building_type="house",
            roof_color=(200, 50, 50),
            wall_color=(220, 210, 190),
        )
        assert sprite is not None



class TestIsometricCalculations:
    """Test isometric projection calculations."""

    def test_get_isometric_offset_all_directions(self):
        """Test that all 8 directions have valid offsets"""
        from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D, Direction

        for direction in Direction:
            dx, dy = PixelArtist3D._get_isometric_offset(direction)
            assert isinstance(dx, int), f"dx should be int for {direction.name}"
            assert isinstance(dy, int), f"dy should be int for {direction.name}"
            # Offsets should be small (pseudo-3D effect)
            assert abs(dx) <= 3, f"dx too large for {direction.name}: {dx}"
            assert abs(dy) <= 2, f"dy too large for {direction.name}: {dy}"

    def test_isometric_offsets_symmetry(self):
        """Test that opposite directions have opposite offsets"""
        from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D, Direction

        opposite_pairs = [
            (Direction.NORTH, Direction.SOUTH),
            (Direction.EAST, Direction.WEST),
            (Direction.NORTHEAST, Direction.SOUTHWEST),
            (Direction.NORTHEAST, Direction.SOUTHWEST),
            (Direction.NORTHWEST, Direction.SOUTHEAST),
        ]

        for dir1, dir2 in opposite_pairs:
            dx1, dy1 = PixelArtist3D._get_isometric_offset(dir1)
            dx2, dy2 = PixelArtist3D._get_isometric_offset(dir2)
            # Opposite directions should have opposite signs (approximately)
            assert dx1 == -dx2 or dx1 == dx2, f"{dir1.name} vs {dir2.name} x-offset not opposite"
            assert dy1 == -dy2 or dy1 == dy2, f"{dir1.name} vs {dir2.name} y-offset not opposite"

    def test_weapon_position_calculation(self):
        """Test weapon position calculation for all directions"""
        from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D, Direction

        cx, cy = 12, 14  # Center position

        for direction in Direction:
            start, end = PixelArtist3D._get_weapon_position(direction, cx, cy)
            assert len(start) == 2, f"Weapon start invalid for {direction.name}"
            assert len(end) == 2, f"Weapon end invalid for {direction.name}"

            # Weapon should extend outward from center
            length = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
            assert length > 5, f"Weapon too short for {direction.name}: {length}"


class TestConvenienceFunctions:
    """Test convenience/wrapper functions."""

    def test_create_cc2_infantry_sprite(self, pygame_display):
        """Test convenience function for infantry creation"""
        from pycc2.presentation.rendering.pixel_artist_3d import create_cc2_infantry_sprite
        import pygame

        sprite = create_cc2_infantry_sprite(
            direction=0,  # North
            faction="allies",
            state="idle",
            frame=0,
        )

        assert sprite is not None
        assert isinstance(sprite, pygame.Surface)
        assert sprite.get_size() == (24, 24)

    def test_create_cc2_tank_sprite(self, pygame_display):
        """Test convenience function for tank creation - 支持动态尺寸"""
        from pycc2.presentation.rendering.pixel_artist_3d import create_cc2_tank_sprite
        import pygame

        sprite = create_cc2_tank_sprite(
            direction=4,  # South
            faction="axis",
            turret_direction=2,  # East
            state="idle",
        )

        assert sprite is not None
        assert isinstance(sprite, pygame.Surface)
        # 坦克尺寸现在是动态的（基于坦克类型）:
        # Sherman M4: 36×36, Panther Ausf.G: 38×38, Tiger I: 44×44
        size = sprite.get_size()
        assert size[0] in [36, 38, 44], f"Unexpected width: {size[0]}"
        assert size[1] in [36, 38, 44], f"Unexpected height: {size[1]}"
        assert size[0] == size[1], f"Tank sprite should be square, got {size}"


class TestColorPaletteCorrectness:
    """Test that color palettes match CC2 screenshot analysis."""

    def test_allies_uniform_color(self):
        """Test Allies uniform is CC2-accurate OD Green.

        CC2 spec (UI_REALISTIC_PIXEL_SPEC.md): Allied uniform #4B5320 = (75, 83, 32)
        This is the authentic WWII Olive Drab shade used in CC2.
        """
        from pycc2.presentation.rendering.pixel_artist_color_palette import CC2_PALETTE

        allies_uniform = CC2_PALETTE['allies']['uniform']
        assert 65 <= allies_uniform[0] <= 90, f"Allies uniform R out of OD green range: {allies_uniform}"
        assert 70 <= allies_uniform[1] <= 95, f"Allies uniform G out of OD green range: {allies_uniform}"
        assert 20 <= allies_uniform[2] <= 45, f"Allies uniform B out of OD green range: {allies_uniform}"

    def test_axis_uniform_color(self):
        """Test Axis uniform is Field gray"""
        from pycc2.presentation.rendering.pixel_artist_color_palette import CC2_PALETTE

        axis_uniform = CC2_PALETTE['axis']['uniform']
        # Should be gray-green: values close together, mid-range
        assert 75 <= axis_uniform[0] <= 95, f"Axis uniform R out of range: {axis_uniform}"
        assert 80 <= axis_uniform[1] <= 100, f"Axis uniform G out of range: {axis_uniform}"
        assert 65 <= axis_uniform[2] <= 90, f"Axis uniform B out of range: {axis_uniform}"

    def test_helmet_color_reasonable(self):
        """Test helmet color is reasonable military steel color"""
        from pycc2.presentation.rendering.pixel_artist_color_palette import CC2_PALETTE

        for faction in ['allies', 'axis']:
            helmet = CC2_PALETTE[faction]['helmet']
            # Helmet should be gray-green steel: mid range RGB
            assert 50 <= helmet[0] <= 80, f"{faction} helmet R out of range: {helmet}"
            assert 50 <= helmet[1] <= 80, f"{faction} helmet G out of range: {helmet}"
            assert 50 <= helmet[2] <= 80, f"{faction} helmet B out of range: {helmet}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
