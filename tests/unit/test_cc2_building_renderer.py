"""Tests for CC2-style orthographic building renderer."""

import pygame
import pytest

from pycc2.presentation.rendering.cc2_building_renderer import (
    CC2BuildingType,
    CC2_ROOF_COLORS,
    DamageLevel,
    get_building_size,
    render_cc2_building,
)


@pytest.fixture(autouse=True)
def init_pygame():
    if not pygame.get_init():
        pygame.init()
    yield


class TestSmallHouseIntact:
    def test_surface_size_is_1x1(self):
        surface = render_cc2_building(CC2BuildingType.SMALL_HOUSE)
        assert surface.get_size() == (48, 48)

    def test_roof_is_red(self):
        surface = render_cc2_building(CC2BuildingType.SMALL_HOUSE)
        color_at_center = surface.get_at((24, 24))
        expected = CC2_ROOF_COLORS[CC2BuildingType.SMALL_HOUSE]
        assert color_at_center[:3] == expected

    def test_shadow_strip_on_bottom_edge(self):
        surface = render_cc2_building(CC2BuildingType.SMALL_HOUSE)
        roof_color = CC2_ROOF_COLORS[CC2BuildingType.SMALL_HOUSE]
        shadow_color = tuple(max(0, c - 50) for c in roof_color)
        bottom_pixel = surface.get_at((24, 47))
        assert bottom_pixel[:3] == shadow_color

    def test_shadow_strip_on_right_edge(self):
        surface = render_cc2_building(CC2BuildingType.SMALL_HOUSE)
        roof_color = CC2_ROOF_COLORS[CC2BuildingType.SMALL_HOUSE]
        shadow_color = tuple(max(0, c - 50) for c in roof_color)
        right_pixel = surface.get_at((47, 24))
        assert right_pixel[:3] == shadow_color


class TestMediumHouseIntact:
    def test_surface_size_is_2x2(self):
        surface = render_cc2_building(CC2BuildingType.MEDIUM_HOUSE)
        assert surface.get_size() == (96, 96)

    def test_roof_color(self):
        surface = render_cc2_building(CC2BuildingType.MEDIUM_HOUSE)
        color_at_center = surface.get_at((48, 48))
        expected = CC2_ROOF_COLORS[CC2BuildingType.MEDIUM_HOUSE]
        assert color_at_center[:3] == expected

    def test_has_shadow_strips(self):
        surface = render_cc2_building(CC2BuildingType.MEDIUM_HOUSE)
        roof_color = CC2_ROOF_COLORS[CC2BuildingType.MEDIUM_HOUSE]
        shadow_color = tuple(max(0, c - 50) for c in roof_color)
        assert surface.get_at((48, 95))[:3] == shadow_color
        assert surface.get_at((95, 48))[:3] == shadow_color


class TestLargeBuildingWithNumber:
    def test_surface_size_is_3x3(self):
        surface = render_cc2_building(CC2BuildingType.LARGE_BUILDING)
        assert surface.get_size() == (144, 144)

    def test_gray_roof(self):
        surface = render_cc2_building(CC2BuildingType.LARGE_BUILDING)
        color_at_center = surface.get_at((72, 72))
        expected = CC2_ROOF_COLORS[CC2BuildingType.LARGE_BUILDING]
        assert color_at_center[:3] == expected

    def test_shows_yellow_number(self):
        surface = render_cc2_building(
            CC2BuildingType.LARGE_BUILDING,
            show_number=True,
            number="2",
        )
        center_pixel = surface.get_at((72, 72))
        assert center_pixel[0] > 180
        assert center_pixel[1] > 140
        assert center_pixel[2] < 80


class TestBarn:
    def test_surface_size_is_2x2(self):
        surface = render_cc2_building(CC2BuildingType.BARN)
        assert surface.get_size() == (96, 96)

    def test_brown_roof(self):
        surface = render_cc2_building(CC2BuildingType.BARN)
        color_at_center = surface.get_at((48, 48))
        expected = CC2_ROOF_COLORS[CC2BuildingType.BARN]
        assert color_at_center[:3] == expected


class TestWall:
    def test_surface_size_is_1x1(self):
        surface = render_cc2_building(CC2BuildingType.WALL)
        assert surface.get_size() == (48, 48)

    def test_stone_gray_color(self):
        surface = render_cc2_building(CC2BuildingType.WALL)
        color_at_center = surface.get_at((24, 24))
        expected = CC2_ROOF_COLORS[CC2BuildingType.WALL]
        assert color_at_center[:3] == expected


class TestLightDamage:
    def test_darker_roof_color(self):
        intact = render_cc2_building(
            CC2BuildingType.SMALL_HOUSE,
            damage=DamageLevel.INTACT,
        )
        damaged = render_cc2_building(
            CC2BuildingType.SMALL_HOUSE,
            damage=DamageLevel.LIGHT_DAMAGE,
        )
        intact_color = intact.get_at((24, 24))[:3]
        damaged_color = damaged.get_at((24, 24))[:3]
        for i in range(3):
            assert damaged_color[i] <= intact_color[i]

    def test_has_cracks(self):
        surface = render_cc2_building(
            CC2BuildingType.SMALL_HOUSE,
            damage=DamageLevel.LIGHT_DAMAGE,
        )
        crack_color = (40, 36, 32)
        found_crack = False
        for x in range(10, 38):
            for y in range(10, 38):
                if surface.get_at((x, y))[:3] == crack_color:
                    found_crack = True
                    break
            if found_crack:
                break
        assert found_crack, "Expected to find crack pixels on light-damaged building"


class TestHeavyDamage:
    def test_much_darker_than_intact(self):
        intact = render_cc2_building(
            CC2BuildingType.SMALL_HOUSE,
            damage=DamageLevel.INTACT,
        )
        heavy = render_cc2_building(
            CC2BuildingType.SMALL_HOUSE,
            damage=DamageLevel.HEAVY_DAMAGE,
        )
        intact_color = intact.get_at((24, 24))[:3]
        heavy_color = heavy.get_at((24, 24))[:3]
        for i in range(3):
            assert heavy_color[i] <= intact_color[i] - 25

    def test_more_cracks_than_light_damage(self):
        light = render_cc2_building(
            CC2BuildingType.SMALL_HOUSE,
            damage=DamageLevel.LIGHT_DAMAGE,
        )
        heavy = render_cc2_building(
            CC2BuildingType.SMALL_HOUSE,
            damage=DamageLevel.HEAVY_DAMAGE,
        )
        crack_color = (40, 36, 32)
        light_cracks = sum(
            1
            for x in range(light.get_width())
            for y in range(light.get_height())
            if light.get_at((x, y))[:3] == crack_color
        )
        heavy_cracks = sum(
            1
            for x in range(heavy.get_width())
            for y in range(heavy.get_height())
            if heavy.get_at((x, y))[:3] == crack_color
        )
        assert heavy_cracks > light_cracks


class TestDestroyed:
    def test_very_dark_color(self):
        destroyed = render_cc2_building(
            CC2BuildingType.SMALL_HOUSE,
            damage=DamageLevel.DESTROYED,
        )
        color = destroyed.get_at((24, 24))[:3]
        for c in color:
            assert c <= 120

    def test_heavy_cracks_present(self):
        surface = render_cc2_building(
            CC2BuildingType.SMALL_HOUSE,
            damage=DamageLevel.DESTROYED,
        )
        crack_color = (40, 36, 32)
        found_cracks = sum(
            1
            for x in range(surface.get_width())
            for y in range(surface.get_height())
            if surface.get_at((x, y))[:3] == crack_color
        )
        assert found_cracks >= 4


class TestAllBuildingTypesHaveDifferentColors:
    def test_all_unique_colors(self):
        colors = set()
        for btype in CC2BuildingType:
            surface = render_cc2_building(btype)
            center_color = surface.get_at(
                (surface.get_width() // 2, surface.get_height() // 2)
            )[:3]
            colors.add(center_color)
        assert len(colors) == len(list(CC2BuildingType))


class TestShadowStripVisibleOnAllTypes:
    def test_bottom_and_right_shadow_exist(self):
        for btype in CC2BuildingType:
            surface = render_cc2_building(btype)
            w, h = surface.get_size()
            roof_color = CC2_ROOF_COLORS[btype]
            shadow_color = tuple(max(0, c - 50) for c in roof_color)
            bottom_pixel = surface.get_at((w // 2, h - 1))[:3]
            right_pixel = surface.get_at((w - 1, h // 2))[:3]
            assert (
                bottom_pixel == shadow_color
            ), f"{btype} missing bottom shadow"
            assert (
                right_pixel == shadow_color
            ), f"{btype} missing right shadow"


class TestGetBuildingSize:
    def test_small_house_is_1x1(self):
        assert get_building_size(CC2BuildingType.SMALL_HOUSE) == (1, 1)

    def test_medium_house_is_2x2(self):
        assert get_building_size(CC2BuildingType.MEDIUM_HOUSE) == (2, 2)

    def test_large_building_is_3x3(self):
        assert get_building_size(CC2BuildingType.LARGE_BUILDING) == (3, 3)

    def test_barn_is_2x2(self):
        assert get_building_size(CC2BuildingType.BARN) == (2, 2)

    def test_church_is_2x2(self):
        assert get_building_size(CC2BuildingType.CHURCH) == (2, 2)

    def test_wall_is_1x1(self):
        assert get_building_size(CC2BuildingType.WALL) == (1, 1)


class TestCustomTileSize:
    def test_custom_tile_size_affects_output(self):
        surface_default = render_cc2_building(
            CC2BuildingType.SMALL_HOUSE, tile_size=48
        )
        surface_custom = render_cc2_building(
            CC2BuildingType.SMALL_HOUSE, tile_size=64
        )
        assert surface_default.get_size() == (48, 48)
        assert surface_custom.get_size() == (64, 64)
