from __future__ import annotations

import ctypes
import logging
import platform
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger(__name__)

import pygame


class WindowMode(Enum):
    WINDOWED = auto()
    FULLSCREEN = auto()
    BORDERLESS = auto()


@dataclass(slots=True)
class DisplayInfo:
    base_width: int = 1280
    base_height: int = 720
    dpi_scale: float = 1.0
    is_retina: bool = False
    screen_width: int = 0
    screen_height: int = 0


@dataclass
class WindowManager:
    display_info: DisplayInfo = field(default_factory=DisplayInfo)
    mode: WindowMode = WindowMode.WINDOWED
    _screen: pygame.Surface | None = None
    _clock: pygame.time.Clock | None = None
    _shutdown_called: bool = False

    def initialize(self) -> pygame.Surface:
        self.display_info.dpi_scale = self.detect_dpi()
        self.display_info.is_retina = self.display_info.dpi_scale >= 2.0
        info = pygame.display.Info()
        self.display_info.screen_width = info.current_w
        self.display_info.screen_height = info.current_h
        # SCALED + DOUBLEBUF with native vsync (pygame 2.2+).
        # HWSURFACE is deprecated in SDL2 and causes flickering on macOS — removed.
        flags = pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF
        self._screen = pygame.display.set_mode(
            (self.display_info.base_width, self.display_info.base_height),
            flags,
            vsync=1,
        )
        pygame.display.set_caption("PyCC2 - Close Combat 2 Remake")
        return self._screen

    def initialize_with_config(self, display_config) -> pygame.Surface:
        from pycc2.domain.interfaces.display_config import DisplayConfig as DC

        if not isinstance(display_config, DC):
            return self.initialize()

        self.display_info.dpi_scale = display_config.dpi_scale or self.detect_dpi()
        self.display_info.is_retina = display_config.is_retina or self.display_info.dpi_scale >= 2.0
        info = pygame.display.Info()
        self.display_info.screen_width = info.current_w
        self.display_info.screen_height = info.current_h
        self.display_info.base_width = display_config.window_width
        self.display_info.base_height = display_config.window_height
        flags = pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF
        self._screen = pygame.display.set_mode(
            (display_config.window_width, display_config.window_height),
            flags,
            vsync=1,
        )
        pygame.display.set_caption("PyCC2 - Close Combat 2 Remake")
        return self._screen

    def get_screen(self) -> pygame.Surface:
        if self._screen is None:
            self._screen = self.initialize()
        return self._screen

    def toggle_fullscreen(self) -> None:
        if self.mode == WindowMode.WINDOWED:
            self.mode = WindowMode.FULLSCREEN
            flags = pygame.FULLSCREEN | pygame.DOUBLEBUF
            self._screen = pygame.display.set_mode(
                (self.display_info.base_width, self.display_info.base_height),
                flags,
                vsync=1,
            )
        else:
            self.mode = WindowMode.WINDOWED
            flags = pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF
            self._screen = pygame.display.set_mode(
                (self.display_info.base_width, self.display_info.base_height),
                flags,
                vsync=1,
            )

    def toggle_maximize(self) -> None:
        flags = pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF
        if self.mode == WindowMode.WINDOWED:
            self._screen = pygame.display.set_mode(
                (self.display_info.screen_width, self.display_info.screen_height),
                flags,
                vsync=1,
            )
        else:
            self._screen = pygame.display.set_mode(
                (self.display_info.base_width, self.display_info.base_height),
                flags,
                vsync=1,
            )
            self.mode = WindowMode.WINDOWED

    def resize(self, width: int, height: int) -> None:
        self.display_info.base_width = width
        self.display_info.base_height = height
        if self._screen is not None:
            flags = pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF
            if self.mode == WindowMode.FULLSCREEN:
                flags |= pygame.FULLSCREEN
            self._screen = pygame.display.set_mode((width, height), flags, vsync=1)

    def handle_event(self, event: pygame.event.EventType) -> bool:
        if event.type == pygame.QUIT:
            return True
        if event.type == pygame.VIDEORESIZE:
            self.resize(event.w, event.h)
        return False

    def get_actual_size(self) -> tuple[int, int]:
        if self._screen is not None:
            return self._screen.get_size()
        return (self.display_info.base_width, self.display_info.base_height)

    def detect_dpi(self) -> float:
        system = platform.system()
        if system == "Darwin":
            try:
                from AppKit import NSScreen

                main_screen = NSScreen.mainScreen()
                if main_screen is not None:
                    return main_screen.backingScaleFactor() or 1.0
            except (OSError, AttributeError, ImportError) as e:
                logging.debug("macOS NSScreen backing scale factor failed: %s", e)
            try:
                objc = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/AppKit.framework/AppKit")
                objc.NSScreen_mainScreen.restype = ctypes.c_void_p
                objc.NSScreen_backingScaleFactor.restype = ctypes.c_double
                screen = objc.NSScreen_mainScreen()
                if screen:
                    scale = objc.NSScreen_backingScaleFactor(screen)
                    return scale if scale > 0 else 1.0
            except (OSError, AttributeError, ImportError) as e:
                logging.debug("macOS ctypes DPI detection failed: %s", e)
        elif system == "Linux":
            try:
                import subprocess

                result = subprocess.run(
                    ["xdpyinfo"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in result.stdout.splitlines():
                    if "resolution" in line.lower():
                        parts = line.split(":")[-1].strip().split("x")
                        if len(parts) == 2:
                            dpi_x = float(parts[0].split()[0])
                            return dpi_x / 96.0
            except (OSError, ValueError, RuntimeError) as e:
                logging.debug("Linux DPI detection failed: %s", e)
        elif system == "Windows":
            try:
                user32 = ctypes.windll.user32  # type: ignore[attr-defined]
                user32.SetProcessDPIAware()
                dc = user32.GetDC(0)
                dpi_x = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  # type: ignore[attr-defined]
                return float(dpi_x) / 96.0
            except (OSError, AttributeError, ImportError) as e:
                logging.debug("Windows DPI detection failed: %s", e)
        return 1.0

    @property
    def fps(self) -> float:
        if self._clock is not None:
            return self._clock.get_fps()
        return 0.0

    def tick(self, target_fps: int = 60) -> int:
        if self._clock is None:
            self._clock = pygame.time.Clock()
        return self._clock.tick(target_fps)

    def shutdown(self) -> None:
        if self._shutdown_called:
            return
        self._shutdown_called = True
        if pygame.get_init():
            pygame.quit()
