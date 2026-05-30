from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.display_config import DisplayConfig
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
    from pycc2.presentation.rendering.window_config import WindowManager
    from pycc2.presentation.rendering.weather_system import WeatherRenderer
    from pycc2.services.ai_service import AIService

logger = logging.getLogger(__name__)


@dataclass
class RenderPipeline:
    renderer: EnhancedRenderer
    window_manager: WindowManager
    display_config: DisplayConfig
    hud_manager: object | None = None
    command_bar: object | None = None
    unit_panel: object | None = None
    minimap: object | None = None
    ai_service: AIService | None = None
    use_full_hud: bool = True
    weather_renderer: WeatherRenderer | None = None

    _fps: float = 0.0

    def render(
        self,
        game_map: GameMap,
        units: list[Unit],
        camera: Camera,
        alpha: float,
        selected_unit_ids: set[str],
        debug_mode: bool,
        paused: bool,
        tick: int,
        show_post_battle: bool = False,
        game_result: object | None = None,
        battle_stats: object | None = None,
        weather=None,  # P0-3 Fix: WeatherCondition or None (default=CLEAR)
        time_of_day=None,  # P0-3 Fix: TimeOfDay or None (default=DAY)
    ) -> None:
        self.renderer.render(
            game_map,
            units,
            camera,
            alpha=alpha,
            selected_unit_ids=selected_unit_ids,
            debug_mode=debug_mode,
        )

        # Render weather effects (before HUD) - P0-3 Fix: Use injected values or defaults
        if self.weather_renderer is not None:
            from pycc2.domain.systems.environment import WeatherCondition, TimeOfDay
            screen = self.window_manager.get_screen()
            cam_x, cam_y = int(camera.x), int(camera.y)
            # Use provided values or fallback to defaults (backward compatible)
            actual_weather = weather if weather is not None else WeatherCondition.CLEAR
            actual_time = time_of_day if time_of_day is not None else TimeOfDay.DAY
            self.weather_renderer.render(
                screen,
                weather=actual_weather,
                time_of_day=actual_time,
                camera_offset_x=cam_x,
                camera_offset_y=cam_y,
            )

        self._render_hud(
            game_map=game_map,
            units=units,
            camera=camera,
            selected_unit_ids=selected_unit_ids,
            debug_mode=debug_mode,
            paused=paused,
            tick=tick,
            show_post_battle=show_post_battle,
            game_result=game_result,
            battle_stats=battle_stats,
        )

    def update_fps(self, fps: float) -> None:
        self._fps = fps

    def _render_hud(
        self,
        game_map: GameMap,
        units: list[Unit],
        camera: Camera,
        selected_unit_ids: set[str],
        debug_mode: bool,
        paused: bool,
        tick: int,
        show_post_battle: bool = False,
        game_result: object | None = None,
        battle_stats: object | None = None,
    ) -> None:
        screen = self.window_manager.get_screen()

        if show_post_battle:
            self._render_post_battle_screen(screen, game_result, battle_stats)
            return

        if self.use_full_hud and self.hud_manager and isinstance(screen, pygame.Surface):
            selected = [u for u in units if u.id in selected_unit_ids]
            self.hud_manager.set_selected_units(selected)
            self.hud_manager.update_fps(self._fps)

            total_secs = tick // 30
            mins, secs = divmod(total_secs, 60)
            time_str = f"{mins:02d}:{secs:02d}"
            self.hud_manager.update_game_time(time_str)
            self.hud_manager.update_turn(tick // 1800 + 1)

            self.hud_manager.render(screen)

            if self.command_bar:
                self.command_bar.set_selected_unit(selected[0] if selected else None)
                self.command_bar.render(screen)

            if self.unit_panel:
                if selected:
                    self.unit_panel.set_unit(selected[0])
                else:
                    self.unit_panel.set_unit(None)
                self.unit_panel.render(screen)

            if self.minimap:
                self.minimap.update_units(units)
                sw, sh = screen.get_size()
                dc = self.display_config
                mm_offset = int(160 * dc.ui_scale)
                mm_offset_y = int(180 * dc.ui_scale)
                self.minimap.render(screen, sw - mm_offset, sh - mm_offset_y)

            if debug_mode and self.ai_service:
                self._render_debug_ai(screen)
        else:
            font = pygame.font.Font(None, 20)
            status = f"FPS:{self._fps:.0f} Tick:{tick} {'[PAUSED]' if paused else ''}"
            text = font.render(status, True, (255, 255, 255))
            screen.blit(text, (10, 10))

            if self.ai_service is not None and self.ai_service.managed_unit_count > 0:
                ai_info = f"AI Units: {self.ai_service.managed_unit_count}"
                ai_text = font.render(ai_info, True, (100, 255, 100))
                screen.blit(ai_text, (10, 30))

    def _render_post_battle_screen(
        self, screen, game_result: object | None, battle_stats: object | None
    ) -> None:
        import pygame

        if not game_result:
            return

        dc = self.display_config
        sw, sh = screen.get_size()

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        panel_w = min(500, int(sw * 0.6))
        panel_h = min(400, int(sh * 0.7))
        panel_x = (sw - panel_w) // 2
        panel_y = (sh - panel_h) // 2

        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((30, 30, 40, 230))
        pygame.draw.rect(panel_surf, (100, 100, 120), (0, 0, panel_w, panel_h), 2, border_radius=8)
        screen.blit(panel_surf, (panel_x, panel_y))

        result = game_result
        title_font = pygame.font.Font(None, int(dc.font_size_title * 1.8))
        sub_font = pygame.font.Font(None, int(dc.font_size_large * 1.2))
        stat_font = pygame.font.Font(None, int(dc.font_size_normal * 1.2))

        if result.name == "ALLIES_VICTORY":
            title_color = (80, 200, 120)
            title_text = "VICTORY"
        elif result.name == "AXIS_VICTORY":
            title_color = (200, 80, 80)
            title_text = "DEFEAT"
        else:
            title_color = (200, 200, 100)
            title_text = f"{result.name}"

        title_surf = title_font.render(title_text, True, title_color)
        screen.blit(title_surf, (panel_x + (panel_w - title_surf.get_width()) // 2, panel_y + 25))

        if battle_stats:
            stats = battle_stats
            y_offset = panel_y + 80
            line_height = 28

            stat_lines = [
                ("-" * 28, (150, 150, 150)),
                ("  BATTLE STATISTICS", (255, 255, 255)),
                ("-" * 28, (150, 150, 150)),
                (f"  Duration: {stats.ticks_elapsed // 30}s", (200, 200, 200)),
                ("", None),
                (
                    f"  * Allies  Kills: {stats.allies_kills}  Lost: {stats.allies_units_lost}",
                    (100, 180, 255),
                ),
                (
                    f"  [] Axis    Kills: {stats.axis_kills}  Lost: {stats.axis_units_lost}",
                    (255, 150, 100),
                ),
                ("", None),
                (f"  Allies Accuracy: {stats.allies_accuracy:.1%}", (150, 200, 150)),
                (f"  Axis Accuracy:   {stats.axis_accuracy:.1%}", (200, 150, 150)),
                (f"  Kill Ratio:      {stats.kill_ratio:.2f}", (255, 220, 100)),
                ("", None),
                ("-" * 28, (150, 150, 150)),
            ]

            for text, color in stat_lines:
                if color:
                    txt_surf = stat_font.render(text, True, color)
                    screen.blit(txt_surf, (panel_x + 25, y_offset))
                y_offset += line_height

            instr_y = panel_y + panel_h - 50
            instr_text = "Press ESC or R to continue"
            instr_surf = sub_font.render(instr_text, True, (180, 180, 180))
            screen.blit(instr_surf, (panel_x + (panel_w - instr_surf.get_width()) // 2, instr_y))

    def _render_debug_ai(self, screen) -> None:
        font = pygame.font.Font(None, 18)
        y = 40
        if self.ai_service:
            text = font.render(
                f"AI: {self.ai_service.managed_unit_count} units", True, (100, 255, 100)
            )
            screen.blit(text, (10, y))
            y += 18

            for uid in self.ai_service.managed_unit_ids:
                bb = self.ai_service.get_blackboard(uid)
                if bb:
                    intent = bb.get("current_intent")
                    tactic = intent.tactic_type.name if intent else "idle"
                    info = f"  {uid[:12]}: {tactic}"
                    t_surf = font.render(info, True, (180, 220, 180))
                    screen.blit(t_surf, (10, y))
                    y += 16
