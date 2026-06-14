"""Smoke tests for zero-coverage core modules.

Each test verifies: import succeeds -> class can be instantiated ->
basic API doesn't crash.  These are NOT thorough unit tests -- they are
regression guards to catch import errors, constructor mismatches, and
obvious runtime failures in modules that had no test coverage at all.
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"



class TestSaveSystemSmoke:
    """SecureSaveManager: the persistence layer behind F5/F9."""

    def test_import_and_create(self):
        from pycc2.infrastructure.save_system import SecureSaveManager
        sm = SecureSaveManager()
        assert sm._save_dir.exists()
        assert sm.MAX_SLOTS == 8

    def test_get_slot_info_empty(self):
        from pycc2.infrastructure.save_system import SecureSaveManager
        sm = SecureSaveManager()
        meta, status = sm.get_slot_info(0)
        # Empty slot should return EMPTY status
        assert meta is None or status.name in ("EMPTY", "OK")

    def test_delete_nonexistent_slot(self):
        from pycc2.infrastructure.save_system import SecureSaveManager
        sm = SecureSaveManager()
        result = sm.delete_save(0)
        # May return True (delete succeeded) or False (nothing to delete)
        assert isinstance(result, bool)


class TestConfigSmoke:
    """Infrastructure config module."""

    def test_import(self):
        from pycc2.infrastructure.config import Settings
        s = Settings()
        assert s is not None


class TestAttackLineSystemSmoke:
    """Attack line system — drawn when player selects attack command."""

    def test_import_and_create(self):
        from pycc2.presentation.input.attack_line_system import AttackLineSystem
        sys = AttackLineSystem()
        assert sys is not None

    def test_clear_all(self):
        from pycc2.presentation.input.attack_line_system import AttackLineSystem
        sys = AttackLineSystem()
        sys.clear_all()  # Should not crash on empty state


class TestFeedbackSmoke:
    """UI feedback system — floating text, screen shake, etc."""

    def test_import(self):
        from pycc2.presentation.input.feedback import FeedbackManager
        fb = FeedbackManager()
        assert fb is not None


class TestCommandSmoke:
    """Player command TypedDict — the data structure for all user actions."""

    def test_import(self):
        from pycc2.domain.interfaces.event_types import PlayerCommand
        cmd: PlayerCommand = {
            "command_type": "move",
            "target_id": None,
            "target_position": (5, 10),
            "context": {},
        }
        assert cmd["command_type"] == "move"


class TestDirectionSpriteSmoke:
    """Direction sprite cache — generates directional indicator sprites."""

    def test_import(self):
        from pycc2.presentation.rendering.direction_sprite import DirectionSpriteManager
        cache = DirectionSpriteManager()
        assert cache is not None


class TestWeatherRendererSmoke:
    """Weather rendering overlay system."""

    def test_import(self):
        from pycc2.presentation.rendering.weather_renderer import WeatherRenderer
        wr = WeatherRenderer(screen_width=1024, screen_height=768)
        assert wr is not None


class TestShadowRendererSmoke:
    """Dynamic shadow rendering system."""

    def test_import(self):
        from pycc2.presentation.rendering.shadow_system import ShadowRenderer
        sr = ShadowRenderer()
        assert sr is not None


class TestParticlePoolSmoke:
    """Particle pool — recycles particle objects to avoid GC pressure."""

    def test_import(self):
        from pycc2.presentation.rendering.particle_pool import ParticlePool
        pool = ParticlePool(preallocate=10)
        assert pool is not None

    def test_acquire_release(self):
        from pycc2.presentation.rendering.particle_pool import ParticlePool
        pool = ParticlePool(preallocate=10)
        p = pool.acquire()
        if p is not None:
            pool.release(p)


class TestCameraEffectsSmoke:
    """Cinematic camera effects stack (shake, zoom, etc.)."""

    def test_import(self):
        from pycc2.presentation.rendering.camera_effects import EffectStack
        stack = EffectStack()
        assert stack is not None


class TestPostProcessingSmoke:
    """Post-processing effects (color grading, vignette, etc.)."""

    def test_import(self):
        from pycc2.presentation.rendering.post_processing import PostProcessingEffects
        ppe = PostProcessingEffects(screen_width=1024, screen_height=768)
        assert ppe is not None


class TestTimeControlUISmoke:
    """Time control UI widget (play/pause/speed buttons)."""

    def test_import(self):
        from pycc2.presentation.ui.time_control import TimeControlUI
        tc = TimeControlUI()
        assert tc is not None


class TestCombatPopupSmoke:
    """Combat popup manager — floating damage/kill text."""

    def test_import(self):
        from pycc2.presentation.ui.combat_popup import CombatPopupManager
        mgr = CombatPopupManager()
        assert mgr is not None


class TestKeybindManagerSmoke:
    """Keybinding configuration manager."""

    def test_import(self):
        from pycc2.presentation.ui.keybind_manager import KeybindManager
        km = KeybindManager()
        assert km is not None


class TestThemeSmoke:
    """UI theme definitions (colors, fonts, sizes)."""

    def test_import(self):
        from pycc2.presentation.ui.theme import Theme
        t = Theme()
        assert t is not None


class TestTooltipSmoke:
    """Tooltip rendering system."""

    def test_import(self):
        from pycc2.presentation.ui.tooltip import Tooltip
        tt = Tooltip()
        assert tt is not None


class TestWindowConfigSmoke:
    """Window manager / display configuration."""

    def test_import(self):
        from pycc2.presentation.rendering.window_config import WindowManager
        wm = WindowManager()
        assert wm is not None


class TestRenderContextSmoke:
    """RenderContext DI container — holds all shared render dependencies."""

    def test_import(self):
        from pycc2.presentation.rendering.render_context import RenderContext
        rc = RenderContext(tile_size=48)
        assert rc.tile_size == 48


class TestGameStateViewProtocolSmoke:
    """GameStateView Protocol — structural interface for presentation layer."""

    def test_protocol_exists(self):
        from pycc2.domain.interfaces.game_state_view import GameStateView
        assert hasattr(GameStateView, '__protocol_attrs__') or hasattr(GameStateView, '_is_protocol')

    def test_gameloop_state_satisfies_protocol(self):
        from pycc2.domain.interfaces.game_state_view import GameStateView
        from pycc2.services.game_loop import GameState
        import numpy as np
        from pycc2.domain.entities.game_map import GameMap
        from pycc2.domain.value_objects.vec2 import Vec2
        from pycc2.presentation.rendering.camera import Camera

        gm = GameMap(id="t", name="T", width=10, height=10,
                     tile_grid=np.zeros((10, 10), dtype=np.int8))
        cam = Camera(position=Vec2(0, 0))
        state = GameState(game_map=gm, units=[], camera=cam)
        assert isinstance(state, GameStateView)


class TestGameLoopAssemblerSmoke:
    """GameLoopAssembler — extracted subsystem wiring."""

    def test_import(self):
        from pycc2.services.game_loop_assembler import GameLoopAssembler
        assert hasattr(GameLoopAssembler, 'assemble')


class TestBGMGeneratorSmoke:
    """Background music generator."""

    def test_import(self):
        from pycc2.infrastructure.audio.bgm_system import BGMGenerator
        bgm = BGMGenerator()
        assert bgm is not None


class TestEnhancedSoundBridgeSmoke:
    """Sound bridge layer between domain audio requests and pygame mixer."""

    def test_import(self):
        from pycc2.presentation.audio.enhanced_sound_bridge import EnhancedSoundSystem
        bridge = EnhancedSoundSystem()
        assert bridge is not None
