from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.window_config import WindowManager


@dataclass(slots=True)
class InputEvent:
    event_type: str
    position: tuple[float, float] | None = None
    key: int | None = None
    button: int | None = None
    modifiers: tuple[bool, bool, bool, bool] = (False, False, False, False)


@dataclass
class PygameInputHandler:
    camera: Camera
    window_manager: WindowManager
    move_speed: float = 8.0
    edge_scroll_zone: int = 12

    def process_event(self, event: pygame.event.EventType) -> InputEvent | None:
        if event.type == pygame.MOUSEMOTION:
            return InputEvent(
                event_type="mouse_move",
                position=(float(event.pos[0]), float(event.pos[1])),
            )
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return InputEvent(
                    event_type="mouse_click_left",
                    position=(float(event.pos[0]), float(event.pos[1])),
                    button=event.button,
                    modifiers=self._get_modifiers(),
                )
            elif event.button == 3:
                return InputEvent(
                    event_type="mouse_click_right",
                    position=(float(event.pos[0]), float(event.pos[1])),
                    button=event.button,
                    modifiers=self._get_modifiers(),
                )
            elif event.button == 4:
                self.camera.adjust_zoom(1.2, anchor=event.pos)
                return None
            elif event.button == 5:
                self.camera.adjust_zoom(0.8, anchor=event.pos)
                return None
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                return InputEvent(
                    event_type="mouse_up_left",
                    position=(float(event.pos[0]), float(event.pos[1])),
                    button=event.button,
                    modifiers=self._get_modifiers(),
                )
            elif event.button == 3:
                return InputEvent(
                    event_type="mouse_up_right",
                    position=(float(event.pos[0]), float(event.pos[1])),
                    button=event.button,
                    modifiers=self._get_modifiers(),
                )
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.window_manager.toggle_fullscreen()
                return None
            elif event.key == pygame.K_ESCAPE:
                return InputEvent(
                    event_type="key_down",
                    key=event.key,
                    modifiers=self._get_modifiers(),
                )
            else:
                return InputEvent(
                    event_type="key_down",
                    key=event.key,
                    modifiers=self._get_modifiers(),
                )
        elif event.type == pygame.KEYUP:
            return InputEvent(
                event_type="key_up",
                key=event.key,
                modifiers=self._get_modifiers(),
            )
        elif event.type == pygame.QUIT:
            return InputEvent(event_type="quit")
        elif event.type == pygame.VIDEORESIZE:
            self.window_manager.resize(event.w, event.h)
            return None
        return None

    def get_camera_movement(self) -> tuple[float, float]:
        keys = pygame.key.get_pressed()
        dx, dy = 0.0, 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= self.move_speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += self.move_speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= self.move_speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += self.move_speed
        mx, my = pygame.mouse.get_pos()
        vw, vh = self.window_manager.get_actual_size()
        if mx < self.edge_scroll_zone:
            dx -= self.move_speed * 0.7
        elif mx > vw - self.edge_scroll_zone:
            dx += self.move_speed * 0.7
        if my < self.edge_scroll_zone:
            dy -= self.move_speed * 0.7
        elif my > vh - self.edge_scroll_zone:
            dy += self.move_speed * 0.7
        return (dx, dy)

    def _get_modifiers(self) -> tuple[bool, bool, bool, bool]:
        mods = pygame.key.get_mods()
        return (
            bool(mods & pygame.KMOD_CTRL),
            bool(mods & pygame.KMOD_SHIFT),
            bool(mods & pygame.KMOD_ALT),
            bool(mods & pygame.KMOD_META),
        )
