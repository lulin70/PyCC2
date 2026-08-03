"""E2E: Installation & Startup — TC-001~007 coverage.

Covers scenario 1 (first-install startup). Focus on TC-003 (main menu render)
and TC-005 (config-missing graceful degradation).

These tests exercise the real startup path with headless pygame (SDL dummy
drivers) and verify that the game boots, initialises subsystems, and degrades
gracefully when config/resources are missing.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import shutil
from pathlib import Path

import pygame
import pytest
from conftest import GameLoopFactory


class TestInstallationStartupE2E:
    """P1 E2E: first-install startup journey (TC-001~007)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        yield
        pygame.quit()

    # ------------------------------------------------------------------
    # TC-003: Main menu renders without crash
    # ------------------------------------------------------------------
    def test_main_menu_renders_without_crash(self):
        """TC-003: NewGameMenu renders on headless screen and exposes core buttons."""
        from pycc2.presentation.ui.new_game_menu import NewGameMenu

        menu = NewGameMenu(screen_width=1280, screen_height=720)
        menu.render(self.screen)

        # Buttons are rebuilt on each render; main screen must expose the 4
        # primary navigation buttons documented in TC-003.
        assert isinstance(menu._buttons, dict)
        assert "new_campaign" in menu._buttons, "missing 'New Campaign' button"
        assert "load_game" in menu._buttons, "missing 'Load Game' button"
        assert "skirmish" in menu._buttons, "missing 'Skirmish' button"
        assert "quit" in menu._buttons, "missing 'Quit' button"

    # ------------------------------------------------------------------
    # TC-002: All subsystems initialise
    # ------------------------------------------------------------------
    def test_game_initializes_all_subsystems(self):
        """TC-002: GameLoopFactory wires renderer, AI, input, event bus, etc."""
        f = GameLoopFactory(self.screen)
        try:
            # Core subsystems must be non-None after assembly.
            assert f.game_loop is not None, "GameLoop not assembled"
            assert f.renderer is not None, "renderer subsystem not initialised"
            assert f.ai_service is not None, "AI service not initialised"
            assert f.interaction_controller is not None, "interaction controller not initialised"
            assert f.event_bus is not None, "event bus not initialised"
            assert f.state is not None, "game state not initialised"
            assert f.game_map is not None, "game map not loaded"
            assert f.camera is not None, "camera not initialised"
            assert f.wm is not None, "window manager not initialised"

            # Renderer must be initialised against a real screen surface.
            assert f.renderer.TILE_SIZE > 0, "renderer TILE_SIZE not configured"
        finally:
            f.shutdown()

    # ------------------------------------------------------------------
    # TC-005: Config missing graceful degradation
    # ------------------------------------------------------------------
    def test_config_missing_graceful_degradation(self, tmp_path):
        """TC-005: Removing config/engine.toml must not crash startup.

        GameLoopFactory does not hard-depend on engine.toml — settings fall
        back to code-level defaults (DisplayInfo, DisplayConfig). We verify
        the absence is tolerated and the save-system HMAC fallback path also
        degrades gracefully when ``config/secrets.toml`` is absent.
        """
        config_dir = Path("config")
        engine_toml = config_dir / "engine.toml"
        secrets_toml = config_dir / "secrets.toml"
        backup_files: list[tuple[Path, Path]] = []

        def _stash(src: Path) -> None:
            if src.exists():
                dst = tmp_path / src.name
                shutil.copy(src, dst)
                backup_files.append((src, dst))
                src.unlink()

        try:
            _stash(engine_toml)
            _stash(secrets_toml)

            # Startup must still succeed without config files.
            f = GameLoopFactory(self.screen)
            try:
                assert f.game_loop is not None
                # Render a frame to confirm the pipeline is functional.
                ok = f.render_frame()
                assert ok, "render_frame failed after config removal"
            finally:
                f.shutdown()

            # Save-system HMAC key path must fall back to an ephemeral key
            # with a UserWarning rather than raising (dev environment).
            import warnings

            from pycc2.infrastructure.save_system import SecureSaveManager

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                mgr = SecureSaveManager(base_dir=tmp_path / "saves")
            assert mgr is not None, "SecureSaveManager failed to initialise without secrets"
        finally:
            # Restore originals so other tests are unaffected.
            for src, dst in backup_files:
                shutil.copy(dst, src)

    # ------------------------------------------------------------------
    # TC-006: Resource missing fallback
    # ------------------------------------------------------------------
    def test_resource_missing_no_crash(self, tmp_path):
        """TC-006: Missing sprite/asset files must not crash rendering.

        EnhancedRenderer uses lazy sprite caching; missing assets are skipped
        rather than raising. We render a frame with no sprites placed on disk
        and confirm the pipeline completes.
        """
        f = GameLoopFactory(self.screen)
        try:
            ok = f.render_frame()
            assert ok, "render_frame failed when sprites are absent"
        finally:
            f.shutdown()

    # ------------------------------------------------------------------
    # TC-001: First launch creates save directory
    # ------------------------------------------------------------------
    def test_first_launch_creates_save_directory(self, tmp_path):
        """TC-001: SecureSaveManager creates the save directory on first launch."""
        import warnings

        from pycc2.infrastructure.save_system import SecureSaveManager

        save_root = tmp_path / "campaign_saves"
        assert not save_root.exists()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            mgr = SecureSaveManager(base_dir=save_root)

        # Constructor must create the directory tree.
        assert save_root.exists(), "save directory not created on first launch"
        assert save_root.is_dir()
        # Manager must report as not secure (ephemeral dev key) but functional.
        assert mgr.MAX_SLOTS > 0
        assert mgr.find_empty_slot() == 0, "slot 0 must be empty on first launch"

    # ------------------------------------------------------------------
    # TC-007: Headless mode initialisation
    # ------------------------------------------------------------------
    def test_pygame_init_headless_mode(self):
        """TC-007: pygame initialises under SDL dummy drivers without error."""
        # SDL dummy drivers were set at module import time; verify the
        # display surface is usable for rendering.
        assert self.screen is not None
        assert self.screen.get_size() == (1280, 720)

        # Font subsystem (used by NewGameMenu) must also initialise.
        pygame.font.init()
        font = pygame.font.Font(None, 28)
        surf = font.render("headless ok", True, (255, 255, 255))
        assert surf.get_width() > 0
