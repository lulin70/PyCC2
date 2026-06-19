from __future__ import annotations

from pycc2.domain.entities.unit import UNIT_TEMPLATES, UnitType
from pycc2.domain.systems.campaign import (
    CampaignManager,
    MissionDefinition,
    MissionDifficulty,
    MissionObjective,
    create_default_campaign,
)
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


class TestCampaignSystem:
    def test_create_default_campaign_has_10_missions(self):
        mgr = create_default_campaign()
        assert mgr.total_missions == 10

    def test_mission_01_is_recruit_difficulty(self):
        mgr = create_default_campaign()
        m = mgr.get_mission("mission_01_tutorial")
        assert m is not None
        assert m.difficulty == MissionDifficulty.RECRUIT

    def test_mission_02_has_time_limit(self):
        mgr = create_default_campaign()
        m = mgr.get_mission("mission_02_bridge")
        assert m is not None
        assert m.time_limit_ticks == 5400

    def test_mission_03_has_medic_and_mortar(self):
        mgr = create_default_campaign()
        m = mgr.get_mission("mission_03_hold")
        assert m is not None
        ally_types = [u["unit_type"] for u in m.ally_unit_templates]
        assert "MEDIC_TEAM" in ally_types
        assert "MORTAR_TEAM" in ally_types

    def test_mission_04_night_is_veteran_with_sniper(self):
        mgr = create_default_campaign()
        m = mgr.get_mission("mission_04_night")
        assert m is not None
        assert m.difficulty == MissionDifficulty.VETERAN
        assert m.map_id == "night_map"
        ally_types = [u["unit_type"] for u in m.ally_unit_templates]
        assert "SNIPER_TEAM" in ally_types
        enemy_types = [u["unit_type"] for u in m.enemy_unit_templates]
        assert "MORTAR_TEAM" in enemy_types
        assert len(m.objectives) == 2

    def test_mission_05_armor_is_hero_with_tanks(self):
        mgr = create_default_campaign()
        m = mgr.get_mission("mission_05_armor")
        assert m is not None
        assert m.difficulty == MissionDifficulty.HERO
        assert m.map_id == "road_ambush"
        enemy_types = [u["unit_type"] for u in m.enemy_unit_templates]
        tank_count = enemy_types.count("TANK")
        assert tank_count == 3, f"Expected 3 enemy tanks, got {tank_count}"
        ally_types = [u["unit_type"] for u in m.ally_unit_templates]
        assert "TANK" in ally_types

    def test_register_and_retrieve_mission(self):
        mgr = CampaignManager()
        mission = MissionDefinition(
            id="test_mission",
            name="Test",
            description="Test desc",
            map_id="test_map",
            difficulty=MissionDifficulty.REGULAR,
        )
        mgr.register_mission(mission)
        retrieved = mgr.get_mission("test_mission")
        assert retrieved is mission

    def test_complete_mission_marks_completed(self):
        mgr = CampaignManager()
        mgr.register_mission(
            MissionDefinition(
                id="m1",
                name="M1",
                description="d",
                map_id="x",
                difficulty=MissionDifficulty.RECRUIT,
            )
        )
        mgr.start_mission("m1")
        mgr.complete_current_mission(victory=True)
        assert "m1" in mgr._completed_missions
        assert mgr.completed_count == 1

    def test_available_excludes_completed(self):
        mgr = CampaignManager()
        mgr.register_mission(
            MissionDefinition(
                id="m1",
                name="M1",
                description="d",
                map_id="x",
                difficulty=MissionDifficulty.RECRUIT,
            )
        )
        mgr.register_mission(
            MissionDefinition(
                id="m2",
                name="M2",
                description="d",
                map_id="y",
                difficulty=MissionDifficulty.REGULAR,
            )
        )
        mgr.start_mission("m1")
        mgr.complete_current_mission(victory=True)
        available = [m.id for m in mgr.available_missions]
        assert "m1" not in available
        assert "m2" in available

    def test_start_mission_sets_current(self):
        mgr = CampaignManager()
        mgr.register_mission(
            MissionDefinition(
                id="m1",
                name="M1",
                description="d",
                map_id="x",
                difficulty=MissionDifficulty.RECRUIT,
            )
        )
        result = mgr.start_mission("m1")
        assert result is not None
        assert mgr._current_mission is not None
        assert mgr._current_mission.id == "m1"

    def test_mission_objective_definitions(self):
        mgr = create_default_campaign()
        m = mgr.get_mission("mission_02_bridge")
        assert m is not None
        assert m.total_objectives == 2
        obj_types = [o.objective_type for o in m.objectives]
        assert MissionObjective.CAPTURE_LOCATION in obj_types
        assert MissionObjective.ELIMINATE_ENEMY_FORCE in obj_types


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
