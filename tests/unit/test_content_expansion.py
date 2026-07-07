from __future__ import annotations

import pytest

from pycc2.domain.entities.unit import UNIT_TEMPLATES, UnitType
from pycc2.domain.value_objects.terrain_type import TerrainType


class TestUnitTemplates:
    def test_all_8_unit_types_have_templates(self):
        assert len(UNIT_TEMPLATES) == 8
        for ut in UnitType:
            assert ut in UNIT_TEMPLATES, f"Missing template for {ut.name}"

    def test_template_values_sensible(self):
        for ut, tmpl in UNIT_TEMPLATES.items():
            assert tmpl.max_hp > 0, f"{ut.name}: max_hp must be > 0"
            assert tmpl.max_ammo > 0, f"{ut.name}: max_ammo must be > 0"
            assert tmpl.base_morale > 0, f"{ut.name}: base_morale must be > 0"
            assert tmpl.vision_range > 0, f"{ut.name}: vision_range must be > 0"
            assert tmpl.movement_speed > 0, f"{ut.name}: movement_speed must be > 0"
            assert tmpl.size_radius > 0, f"{ut.name}: size_radius must be > 0"
            assert len(tmpl.weapon_damage_range) == 2
            assert tmpl.weapon_damage_range[0] <= tmpl.weapon_damage_range[1]

    def test_tank_is_vehicle_with_high_hp(self):
        tank = UNIT_TEMPLATES[UnitType.TANK]
        assert tank.is_vehicle is True
        assert tank.max_hp == 200
        assert tank.max_hp > UNIT_TEMPLATES[UnitType.INFANTRY_SQUAD].max_hp

    def test_sniper_has_long_vision_and_stealth(self):
        sniper = UNIT_TEMPLATES[UnitType.SNIPER_TEAM]
        assert sniper.vision_range == 10
        assert sniper.stealth_bonus == 0.40
        assert sniper.vision_range > UNIT_TEMPLATES[UnitType.INFANTRY_SQUAD].vision_range

    def test_medic_can_heal_with_low_damage(self):
        medic = UNIT_TEMPLATES[UnitType.MEDIC_TEAM]
        assert medic.can_heal is True
        assert medic.heal_per_tick == 0.5
        assert medic.heal_range == 3
        assert (
            medic.weapon_damage_range[1]
            < UNIT_TEMPLATES[UnitType.INFANTRY_SQUAD].weapon_damage_range[1]
        )

    def test_at_gun_has_high_damage_vs_armor(self):
        at_gun = UNIT_TEMPLATES[UnitType.AT_GUN_TEAM]
        assert at_gun.weapon_damage_range[0] >= 30
        assert at_gun.movement_speed < UNIT_TEMPLATES[UnitType.INFANTRY_SQUAD].movement_speed

    def test_mortar_has_indirect_fire_profile(self):
        mortar = UNIT_TEMPLATES[UnitType.MORTAR_TEAM]
        assert mortar.max_ammo == 6
        assert mortar.movement_speed < UNIT_TEMPLATES[UnitType.INFANTRY_SQUAD].movement_speed
        assert mortar.weapon_damage_range[0] >= 20

    def test_movement_speeds_reasonable(self):
        speeds = {ut: tmpl.movement_speed for ut, tmpl in UNIT_TEMPLATES.items()}
        assert speeds[UnitType.TANK] > speeds[UnitType.AT_GUN_TEAM]
        assert speeds[UnitType.INFANTRY_SQUAD] >= speeds[UnitType.MACHINE_GUN_SQUAD]


class TestNewTerrainTypes:
    def test_crater_exists_in_enum(self):
        assert TerrainType.CRATER.value == 12

    def test_swamp_exists_in_enum(self):
        assert TerrainType.SWAMP.value == 13

    def test_crater_slow_movement_high_cover(self):
        assert TerrainType.CRATER.movement_cost == 2.5
        assert TerrainType.CRATER.cover_bonus == 0.25

    def test_swamp_very_slow_no_cover(self):
        assert TerrainType.SWAMP.movement_cost == 4.0
        assert TerrainType.SWAMP.cover_bonus == 0.0

    def test_crater_is_passable(self):
        assert TerrainType.CRATER.is_passable is True

    def test_swamp_is_passable(self):
        assert TerrainType.SWAMP.is_passable is True

    def test_crater_height_is_ground_level(self):
        """Crater height=0: LOS sees prone unit at ground level; cover via cover_bonus."""
        assert TerrainType.CRATER.height == 0

    def test_total_terrain_types_is_15(self):
        assert len(TerrainType) == 22


@pytest.mark.slow
class TestNewUnitSprites:
    def test_tank_sprite_generates_without_error(self):
        from pycc2.presentation.rendering.pixel_artist import UnitSpriteGenerator, UnitSpriteSpec

        spec = UnitSpriteSpec(faction="allies", unit_type="TANK", direction=0, size=16)
        canvas = UnitSpriteGenerator.generate(spec)
        assert canvas is not None
        assert canvas.width == 16
        assert canvas.height == 16

    def test_sniper_sprite_generates_without_error(self):
        from pycc2.presentation.rendering.pixel_artist import UnitSpriteGenerator, UnitSpriteSpec

        spec = UnitSpriteSpec(faction="axis", unit_type="SNIPER_TEAM", direction=2, size=16)
        canvas = UnitSpriteGenerator.generate(spec)
        assert canvas is not None
        assert canvas.width == 16

    def test_medic_sprite_generates_without_error(self):
        from pycc2.presentation.rendering.pixel_artist import UnitSpriteGenerator, UnitSpriteSpec

        spec = UnitSpriteSpec(faction="allies", unit_type="MEDIC_TEAM", direction=4, size=16)
        canvas = UnitSpriteGenerator.generate(spec)
        assert canvas is not None
        assert canvas.height == 16

    def test_crater_tile_generates_without_error(self):
        from pycc2.presentation.rendering.pixel_artist import TerrainTileGenerator

        canvas = TerrainTileGenerator.generate_crater(16)
        assert canvas is not None
        assert canvas.width == 16
        assert canvas.height == 16

    def test_swamp_tile_generates_without_error(self):
        from pycc2.presentation.rendering.pixel_artist import TerrainTileGenerator

        canvas = TerrainTileGenerator.generate_swamp(16)
        assert canvas is not None
        assert canvas.width == 16
        assert canvas.height == 16

    def test_new_sprites_are_cached_by_renderer(self):
        import os

        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        import pygame

        pygame.init()
        from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer

        renderer = SpriteRenderer()
        assert "allies_TANK_d0" in renderer._sprite_cache
        assert "axis_SNIPER_TEAM_d0" in renderer._sprite_cache
        assert "allies_MEDIC_TEAM_d0" in renderer._sprite_cache
        assert 12 in renderer._terrain_cache
        assert 13 in renderer._terrain_cache
        pygame.quit()
