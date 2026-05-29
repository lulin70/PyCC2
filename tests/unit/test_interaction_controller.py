from __future__ import annotations

from unittest.mock import Mock

import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.input.interaction_controller import (
    ClickResult,
    InteractionController,
    InteractionMode,
)
from pycc2.presentation.rendering.camera import Camera
from pycc2.services.event_bus import EventBus


@pytest.fixture
def camera():
    return Camera(position=Vec2(256.0, 256.0), viewport_width=1280, viewport_height=720)


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def game_map():
    gm = Mock()
    gm.width = 50
    gm.height = 50
    return gm


@pytest.fixture
def interaction_controller(camera, game_map, event_bus):
    return InteractionController(camera=camera, game_map=game_map, event_bus=event_bus)


@pytest.fixture
def sample_units():
    def make_unit(
        uid: str,
        unit_type: UnitType,
        faction: Faction = Faction.ALLIES,
        tile_x: int = 5,
        tile_y: int = 5,
        alive: bool = True,
    ) -> Unit:
        health = HealthComponent(hp=100, max_hp=100)
        if not alive:
            health.take_damage(100)
        return Unit(
            id=uid,
            name=f"Unit-{uid}",
            faction=faction,
            unit_type=unit_type,
            health=health,
            morale=MoraleComponent(value=100),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
            position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
            vision=VisionComponent(range_tiles=5),
        )

    return [
        make_unit("u1", UnitType.INFANTRY_SQUAD, Faction.ALLIES, 5, 5),
        make_unit("u2", UnitType.MACHINE_GUN_SQUAD, Faction.ALLIES, 7, 7),
        make_unit("u3", UnitType.INFANTRY_SQUAD, Faction.AXIS, 10, 10),
        make_unit("u4", UnitType.COMMANDER, Faction.ALLIES, 5, 5, alive=False),
    ]


class TestScreenToTile:
    def test_center_screen_maps_to_center_tile(self, interaction_controller):
        screen_pos = (640.0, 360.0)
        tile = interaction_controller.screen_to_tile(screen_pos)
        assert tile.x == 8
        assert tile.y == 8

    def test_offset_screen_maps_correctly(self, interaction_controller):
        screen_pos = (672.0, 392.0)
        tile = interaction_controller.screen_to_tile(screen_pos)
        assert tile.x == 9
        assert tile.y == 9

    def test_negative_screen_clamps_to_zero(self, interaction_controller):
        screen_pos = (-100.0, -100.0)
        tile = interaction_controller.screen_to_tile(screen_pos)
        assert tile.x == 0
        assert tile.y == 0


class TestHitTest:
    def test_hit_living_unit(self, interaction_controller, sample_units):
        unit_pos = sample_units[0].position.pixel_position
        screen_pos = interaction_controller.camera.world_to_screen(unit_pos)
        result = interaction_controller.hit_test(screen_pos, sample_units)
        assert result.is_unit_click is True
        assert result.hit_unit is not None
        assert result.hit_unit.id == "u1"

    def test_miss_returns_terrain_click(self, interaction_controller, sample_units):
        far_pos = Vec2(99999.0, 99999.0)
        screen_pos = interaction_controller.camera.world_to_screen(far_pos)
        result = interaction_controller.hit_test(screen_pos, sample_units)
        assert result.is_terrain_click is True
        assert result.hit_unit is None
        assert result.world_position is not None

    def test_dead_unit_not_hittable(self, interaction_controller, sample_units):
        dead_unit = sample_units[3]
        dead_unit_pos = dead_unit.position.pixel_position
        screen_pos = interaction_controller.camera.world_to_screen(dead_unit_pos)
        result = interaction_controller.hit_test(screen_pos, sample_units)
        assert result.hit_unit is None or result.hit_unit.is_alive

    def test_different_unit_types_have_different_radii(self, interaction_controller):
        def make_unit_at(uid: str, utype: UnitType, tx: int, ty: int) -> Unit:
            return Unit(
                id=uid,
                name=uid,
                faction=Faction.ALLIES,
                unit_type=utype,
                health=HealthComponent(hp=100, max_hp=100),
                morale=MoraleComponent(value=100),
                weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
                position=PositionComponent(tile_coord=TileCoord(tx, ty)),
                vision=VisionComponent(range_tiles=5),
            )

        units = [
            make_unit_at("mg", UnitType.MACHINE_GUN_SQUAD, 8, 8),
            make_unit_at("cmd", UnitType.COMMANDER, 8, 8),
        ]
        unit_screen = interaction_controller.camera.world_to_screen(
            units[0].position.pixel_position
        )
        result = interaction_controller.hit_test(unit_screen, units)
        assert result.hit_unit is not None

    def test_overlapping_units_selects_closest(self, interaction_controller):
        def make_unit_at(uid: str, tx: int, ty: int) -> Unit:
            return Unit(
                id=uid,
                name=uid,
                faction=Faction.ALLIES,
                unit_type=UnitType.INFANTRY_SQUAD,
                health=HealthComponent(hp=100, max_hp=100),
                morale=MoraleComponent(value=100),
                weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
                position=PositionComponent(tile_coord=TileCoord(tx, ty)),
                vision=VisionComponent(range_tiles=5),
            )

        units = [make_unit_at("a", 5, 5), make_unit_at("b", 5, 5)]
        screen = interaction_controller.camera.world_to_screen(units[0].position.pixel_position)
        result = interaction_controller.hit_test(screen, units)
        assert result.hit_unit is not None
        assert result.hit_unit.id in ("a", "b")


class TestHandleLeftClick:
    def test_click_unit_selects_it(self, interaction_controller, sample_units):
        target_screen = interaction_controller.camera.world_to_screen(
            sample_units[0].position.pixel_position
        )
        selected = interaction_controller.handle_left_click(target_screen, sample_units)
        assert "u1" in selected

    def test_click_empty_deselects(self, interaction_controller, sample_units):
        target_screen = interaction_controller.camera.world_to_screen(
            sample_units[0].position.pixel_position
        )
        interaction_controller.handle_left_click(target_screen, sample_units)
        far_screen = interaction_controller.camera.world_to_screen(Vec2(99999, 99999))
        selected = interaction_controller.handle_left_click(far_screen, sample_units)
        assert len(selected) == 0

    def test_shift_click_adds_to_selection(self, interaction_controller, sample_units):
        screen_u1 = interaction_controller.camera.world_to_screen(
            sample_units[0].position.pixel_position
        )
        interaction_controller.handle_left_click(screen_u1, sample_units)
        screen_u2 = interaction_controller.camera.world_to_screen(
            sample_units[1].position.pixel_position
        )
        selected = interaction_controller.handle_left_click(
            screen_u2, sample_units, (False, True, False, False)
        )
        assert "u1" in selected
        assert "u2" in selected

    def test_shift_click_removes_already_selected(self, interaction_controller, sample_units):
        screen_u1 = interaction_controller.camera.world_to_screen(
            sample_units[0].position.pixel_position
        )
        interaction_controller.handle_left_click(screen_u1, sample_units)
        selected = interaction_controller.handle_left_click(
            screen_u1, sample_units, (False, True, False, False)
        )
        assert "u1" not in selected

    def test_move_mode_resets_to_select_on_click(self, interaction_controller, sample_units):
        interaction_controller.set_mode(InteractionMode.MOVE)
        screen = interaction_controller.camera.world_to_screen(
            sample_units[0].position.pixel_position
        )
        interaction_controller.handle_left_click(screen, sample_units)
        assert interaction_controller.mode == InteractionMode.SELECT


class TestHandleRightClick:
    def test_no_selection_does_nothing(self, interaction_controller, sample_units):
        screen = interaction_controller.camera.world_to_screen(Vec2(10 * 32, 10 * 32))
        interaction_controller.handle_right_click(screen, sample_units)

    def test_right_click_ground_issues_move(self, interaction_controller, sample_units):
        screen_u1 = interaction_controller.camera.world_to_screen(
            sample_units[0].position.pixel_position
        )
        interaction_controller.handle_left_click(screen_u1, sample_units)
        move_called = []
        interaction_controller.register_on_move(lambda ids, tile: move_called.append((ids, tile)))
        ground_screen = interaction_controller.camera.world_to_screen(Vec2(12 * 32, 12 * 32))
        interaction_controller.handle_right_click(ground_screen, sample_units)
        assert len(move_called) == 1

    def test_right_click_enemy_issues_attack(self, interaction_controller, sample_units):
        screen_u1 = interaction_controller.camera.world_to_screen(
            sample_units[0].position.pixel_position
        )
        interaction_controller.handle_left_click(screen_u1, sample_units)
        attack_called = []
        interaction_controller.register_on_attack(lambda ids, tid: attack_called.append((ids, tid)))
        enemy_screen = interaction_controller.camera.world_to_screen(
            sample_units[2].position.pixel_position
        )
        interaction_controller.handle_right_click(enemy_screen, sample_units)
        assert len(attack_called) == 1
        assert attack_called[0][1] == "u3"


class TestShortcutKeys:
    def test_key_z_sets_move_mode(self, interaction_controller):
        import pygame

        interaction_controller.handle_shortcut_key(pygame.K_z)
        assert interaction_controller.mode == InteractionMode.MOVE

    def test_key_c_sets_attack_mode(self, interaction_controller):
        import pygame

        interaction_controller.handle_shortcut_key(pygame.K_c)
        assert interaction_controller.mode == InteractionMode.ATTACK

    def test_key_esc_clears_selection(self, interaction_controller, sample_units):
        import pygame

        screen = interaction_controller.camera.world_to_screen(
            sample_units[0].position.pixel_position
        )
        interaction_controller.handle_left_click(screen, sample_units)
        assert len(interaction_controller.selected_unit_ids) > 0
        interaction_controller.handle_shortcut_key(pygame.K_ESCAPE)
        assert len(interaction_controller.selected_unit_ids) == 0
        assert interaction_controller.mode == InteractionMode.SELECT

    def test_mode_change_preserves_selection(self, interaction_controller, sample_units):
        import pygame

        screen = interaction_controller.camera.world_to_screen(
            sample_units[0].position.pixel_position
        )
        interaction_controller.handle_left_click(screen, sample_units)
        interaction_controller.handle_shortcut_key(pygame.K_z)
        assert len(interaction_controller.selected_unit_ids) > 0


class TestCallbacks:
    def test_on_selected_callback_fires(self, interaction_controller, sample_units):
        received: list[set[str]] = []
        interaction_controller.register_on_selected(lambda ids: received.append(ids))
        screen = interaction_controller.camera.world_to_screen(
            sample_units[0].position.pixel_position
        )
        interaction_controller.handle_left_click(screen, sample_units)
        assert len(received) >= 1

    def test_on_deselect_callback_fires_on_esc(self, interaction_controller):
        import pygame

        called = []
        interaction_controller.register_on_deselect(lambda: called.append(1))
        interaction_controller.handle_shortcut_key(pygame.K_ESCAPE)
        assert len(called) == 1


class TestEdgeCases:
    def test_out_of_bounds_click_does_not_crash(self, interaction_controller, sample_units):
        result = interaction_controller.hit_test((-1000.0, -1000.0), sample_units)
        assert isinstance(result, ClickResult)

    def test_empty_unit_list_does_not_crash(self, interaction_controller):
        result = interaction_controller.hit_test((100.0, 100.0), [])
        assert result.is_terrain_click is True
        assert result.hit_unit is None

    def test_clear_selection_works(self, interaction_controller, sample_units):
        screen = interaction_controller.camera.world_to_screen(
            sample_units[0].position.pixel_position
        )
        interaction_controller.handle_left_click(screen, sample_units)
        assert len(interaction_controller.selected_unit_ids) > 0
        interaction_controller.clear_selection()
        assert len(interaction_controller.selected_unit_ids) == 0
        assert interaction_controller.mode == InteractionMode.SELECT
