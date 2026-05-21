from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera


class TestCameraConstruction:
    def test_default_position_is_origin(self):
        cam = Camera(position=Vec2(0, 0))
        assert cam.position.x == 0.0
        assert cam.position.y == 0.0

    def test_default_zoom_is_one(self):
        cam = Camera(position=Vec2(0, 0))
        assert cam.zoom == 1.0

    def test_default_viewport_size(self):
        cam = Camera(position=Vec2(0, 0))
        assert cam.viewport_width == 1280
        assert cam.viewport_height == 720

    def test_custom_viewport_size(self):
        cam = Camera(position=Vec2(0, 0), viewport_width=1920, viewport_height=1080)
        assert cam.viewport_width == 1920
        assert cam.viewport_height == 1080

    def test_custom_position(self):
        pos = Vec2(100, 200)
        cam = Camera(position=pos)
        assert cam.position == pos


class TestWorldToScreen:
    def test_center_point_maps_to_viewport_center(self):
        cam = Camera(position=Vec2(0, 0), viewport_width=800, viewport_height=600)
        screen = cam.world_to_screen(Vec2(0, 0))
        assert screen == (400.0, 300.0)

    def test_positive_offset(self):
        cam = Camera(position=Vec2(0, 0), viewport_width=800, viewport_height=600)
        screen = cam.world_to_screen(Vec2(100, 50))
        assert screen == (500.0, 350.0)

    def test_negative_offset(self):
        cam = Camera(position=Vec2(0, 0), viewport_width=800, viewport_height=600)
        screen = cam.world_to_screen(Vec2(-100, -50))
        assert screen == (300.0, 250.0)

    def test_zoom_affects_scale(self):
        cam = Camera(position=Vec2(0, 0), zoom=2.0, viewport_width=800, viewport_height=600)
        screen = cam.world_to_screen(Vec2(100, 50))
        assert screen == (600.0, 400.0)


class TestScreenToWorld:
    def test_viewport_center_maps_to_camera_position(self):
        cam = Camera(position=Vec2(100, 200), viewport_width=800, viewport_height=600)
        world = cam.screen_to_world((400.0, 300.0))
        assert abs(world.x - 100.0) < 1e-9
        assert abs(world.y - 200.0) < 1e-9

    def test_roundtrip_conversion(self):
        cam = Camera(position=Vec2(50, 75), zoom=1.5, viewport_width=1024, viewport_height=768)
        original = Vec2(123.456, 789.012)
        screen = cam.world_to_screen(original)
        recovered = cam.screen_to_world(screen)
        assert abs(recovered.x - original.x) < 1e-6
        assert abs(recovered.y - original.y) < 1e-6


class TestViewBounds:
    def test_bounds_at_origin_zoom_one(self):
        cam = Camera(position=Vec2(0, 0), zoom=1.0, viewport_width=800, viewport_height=600)
        top_left, bottom_right = cam.view_bounds
        assert top_left.x == -400.0
        assert top_left.y == -300.0
        assert bottom_right.x == 400.0
        assert bottom_right.y == 300.0

    def test_bounds_shrink_with_zoom(self):
        cam = Camera(position=Vec2(0, 0), zoom=2.0, viewport_width=800, viewport_height=600)
        top_left, bottom_right = cam.view_bounds
        assert top_left.x == -200.0
        assert bottom_right.x == 200.0


class TestMove:
    def test_move_positive(self):
        cam = Camera(position=Vec2(0, 0))
        cam.move(10, 20)
        assert cam.position.x == 10.0
        assert cam.position.y == 20.0

    def test_move_divided_by_zoom(self):
        cam = Camera(position=Vec2(0, 0), zoom=2.0)
        cam.move(20, 40)
        assert cam.position.x == 10.0
        assert cam.position.y == 20.0


class TestSetPosition:
    def test_set_position_updates(self):
        cam = Camera(position=Vec2(0, 0))
        new_pos = Vec2(999, 888)
        cam.set_position(new_pos)
        assert cam.position == new_pos


class TestAdjustZoom:
    def test_zoom_in(self):
        cam = Camera(position=Vec2(0, 0), zoom=1.0)
        cam.adjust_zoom(2.0)
        assert cam.zoom == 2.0

    def test_zoom_out(self):
        cam = Camera(position=Vec2(0, 0), zoom=1.0)
        cam.adjust_zoom(0.5)
        assert cam.zoom == 0.5

    def test_zoom_clamps_to_max(self):
        cam = Camera(position=Vec2(0, 0), zoom=3.0)
        cam.adjust_zoom(2.0)
        assert cam.zoom == cam.MAX_ZOOM

    def test_zoom_clamps_to_min(self):
        cam = Camera(position=Vec2(0, 0), zoom=0.5)
        cam.adjust_zoom(0.1)
        assert cam.zoom == cam.MIN_ZOOM

    def test_zoom_with_anchor_preserves_mouse_position(self):
        cam = Camera(position=Vec2(0, 0), zoom=1.0, viewport_width=800, viewport_height=600)
        anchor = (400.0, 300.0)
        mouse_world_before = cam.screen_to_world(anchor)
        cam.adjust_zoom(2.0, anchor=anchor)
        mouse_world_after = cam.screen_to_world(anchor)
        assert abs(mouse_world_after.x - mouse_world_before.x) < 1e-6
        assert abs(mouse_world_after.y - mouse_world_before.y) < 1e-6


class TestConstrainToMap:
    def test_constrain_large_map(self):
        cam = Camera(
            position=Vec2(-100, -100),
            zoom=1.0,
            viewport_width=800,
            viewport_height=600,
        )
        cam.constrain_to_map(1600, 1200)
        assert cam.position.x >= 400
        assert cam.position.y >= 300

    def test_constrain_small_map_centers(self):
        cam = Camera(position=Vec2(0, 0), zoom=1.0, viewport_width=800, viewport_height=600)
        cam.constrain_to_map(400, 300)
        assert abs(cam.position.x - 200.0) < 1e-9
        assert abs(cam.position.y - 150.0) < 1e-9

    def test_constrain_extreme_zoom_allows_overflow(self):
        cam = Camera(position=Vec2(-500, -500), zoom=4.0)
        cam.constrain_to_map(512, 512)
        assert cam.zoom > 3.0


class TestFocusOn:
    def test_focus_immediate_sets_position(self):
        cam = Camera(position=Vec2(0, 0))
        target = Vec2(42, 99)
        cam.focus_on(target, immediate=True)
        assert cam.position == target

    def test_focus_not_immediate_no_change(self):
        cam = Camera(position=Vec2(0, 0))
        target = Vec2(42, 99)
        cam.focus_on(target, immediate=False)
        assert cam.position == Vec2(0, 0)


class TestReset:
    def test_reset_restores_defaults(self):
        cam = Camera(position=Vec2(100, 200), zoom=3.0)
        cam.reset()
        assert cam.position == Vec2(0, 0)
        assert cam.zoom == 1.0


class TestZoomLimits:
    def test_min_zoom_constant(self):
        cam = Camera(position=Vec2(0, 0))
        assert cam.MIN_ZOOM == 0.25

    def test_max_zoom_constant(self):
        cam = Camera(position=Vec2(0, 0))
        assert cam.MAX_ZOOM == 4.0
