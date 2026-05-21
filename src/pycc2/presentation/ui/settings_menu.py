from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class SettingsTab(Enum):
    GENERAL = auto()
    AUDIO = auto()
    CONTROLS = auto()
    GAMEPLAY = auto()


@dataclass(slots=True)
class SettingsState:
    master_volume: float = 0.8
    music_volume: float = 0.6
    sfx_volume: float = 1.0
    quality_preset: str = "HIGH"
    show_fps: bool = True
    show_debug: bool = False
    screen_shake: bool = True
    particles: bool = True
    damage_numbers: bool = True
    difficulty: str = "REGULAR"
    autosave_interval: int = 300


class SettingsMenu:
    def __init__(self, display_config):
        self.state = SettingsState()
        self._display_config = display_config
        self._visible = False
        self._active_tab = SettingsTab.GENERAL
        self._tab_names = ["General", "Audio", "Controls", "Gameplay"]
        self._option_rects: list[tuple[object, str]] = []
        self._selected_option_idx: int = 0

    @property
    def visible(self) -> bool:
        return self._visible

    def toggle(self) -> None:
        self._visible = not self._visible

    def show(self) -> None:
        self._visible = True

    def hide(self) -> None:
        self._visible = False

    def handle_input(self, event, mouse_pos) -> str | None:
        import pygame

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.hide()
                return "closed"
            if event.key == pygame.K_TAB:
                tabs = list(SettingsTab)
                idx = (tabs.index(self._active_tab) + 1) % len(tabs)
                self._active_tab = tabs[idx]
                self._selected_option_idx = 0
                return None
            if event.key in (pygame.K_UP, pygame.K_w):
                self._adjust_selection(-1)
                return None
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self._adjust_selection(1)
                return None
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self._cycle_option_value(-1)
                return "applied"
            if event.key == pygame.K_RIGHT:
                self._cycle_option_value(1)
                return "applied"
            if event.key == pygame.K_RETURN:
                self._toggle_option_at_index(self._selected_option_idx)
                return "applied"
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_click(mouse_pos)
        return None

    def render(self, screen) -> None:
        import pygame

        dc = self._display_config
        sw, sh = screen.get_size()

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        pw, ph = min(600, int(sw * 0.65)), min(500, int(sh * 0.75))
        px, py = (sw - pw) // 2, (sh - ph) // 2

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((25, 28, 38, 245))
        pygame.draw.rect(panel, (100, 110, 140), (0, 0, pw, ph), 2, border_radius=10)
        screen.blit(panel, (px, py))

        font_lg = pygame.font.Font(None, int(dc.font_size_title * 1.2))
        title_surf = font_lg.render("⚙ Settings", True, (220, 220, 230))
        screen.blit(title_surf, (px + (pw - title_surf.get_width()) // 2, py + 15))

        font_md = pygame.font.Font(None, int(dc.font_size_large))
        tab_y = py + 50
        tab_w = pw // len(self._tab_names)
        for i, name in enumerate(self._tab_names):
            tx = px + i * tab_w
            is_active = i == self._active_tab.value
            color = (80, 140, 200) if is_active else (80, 85, 95)
            bg_color = (40, 45, 60) if is_active else (30, 33, 42)
            tab_surf = pygame.Surface((tab_w - 4, 28), pygame.SRCALPHA)
            tab_surf.fill(bg_color)
            screen.blit(tab_surf, (tx + 2, tab_y))
            txt = font_md.render(name, True, color)
            screen.blit(txt, (tx + (tab_w - 4 - txt.get_width()) // 2, tab_y + 5))

        opt_y = tab_y + 40
        options = self._get_options_for_tab()
        font_sm = pygame.font.Font(None, int(dc.font_size_normal))
        self._option_rects = []

        for i, (opt_name, opt_value, opt_type) in enumerate(options):
            oy = opt_y + i * 32
            if oy > py + ph - 50:
                break

            name_surf = font_sm.render(opt_name, True, (200, 200, 210))
            screen.blit(name_surf, (px + 20, oy))

            val_str = self._format_value(opt_value, opt_type)
            val_color = (80, 180, 255) if i == self._selected_option_idx else (140, 200, 140)
            val_surf = font_sm.render(val_str, True, val_color)
            screen.blit(val_surf, (px + pw - 20 - val_surf.get_width(), oy))

            self._option_rects.append((pygame.Rect(px + 15, oy, pw - 30, 28), opt_name))

            if i == 0:
                hint = font_sm.render(
                    "← → to change | Enter to toggle | ↑↓ to select", True, (120, 120, 130)
                )
                screen.blit(hint, (px + 20, oy + 18))

        footer_y = py + ph - 35
        footer = font_sm.render(
            "TAB: switch category | ESC: close | arrows/Enter: change value", True, (140, 140, 150)
        )
        screen.blit(footer, (px + (pw - footer.get_width()) // 2, footer_y))

    def _get_options_for_tab(self) -> list[tuple[str, object, str]]:
        match self._active_tab:
            case SettingsTab.GENERAL:
                return [
                    ("Quality Preset", self.state.quality_preset, "enum"),
                    ("Show FPS Counter", self.state.show_fps, "bool"),
                    ("Screen Shake", self.state.screen_shake, "bool"),
                    ("Particle Effects", self.state.particles, "bool"),
                    ("Damage Numbers", self.state.damage_numbers, "bool"),
                ]
            case SettingsTab.AUDIO:
                return [
                    ("Master Volume", f"{self.state.master_volume:.0%}", "slider"),
                    ("Music Volume", f"{self.state.music_volume:.0%}", "slider"),
                    ("SFX Volume", f"{self.state.sfx_volume:.0%}", "slider"),
                ]
            case SettingsTab.CONTROLS:
                return [
                    ("(Controls are hardcoded)", "See USER_MANUAL.md", "info"),
                    ("Move key", "WASD / Arrow keys", "info"),
                    ("Attack mode", "A key", "info"),
                    ("Quick save", "F5", "info"),
                    ("Quick load", "F9", "info"),
                ]
            case SettingsTab.GAMEPLAY:
                return [
                    ("Difficulty", self.state.difficulty, "enum"),
                    (
                        "Autosave interval",
                        f"{self.state.autosave_interval // 30}s"
                        if self.state.autosave_interval > 0
                        else "Off",
                        "toggle",
                    ),
                ]

    def _format_value(self, value, opt_type: str) -> str:
        if opt_type == "bool":
            return "✓ ON" if value else "✗ OFF"
        return str(value)

    def _adjust_selection(self, direction: int) -> None:
        options = self._get_options_for_tab()
        if not options:
            return
        max_idx = len(options) - 1
        self._selected_option_idx = (self._selected_option_idx + direction) % (max_idx + 1)

    def _toggle_option_at_index(self, idx: int) -> None:
        options = self._get_options_for_tab()
        if idx < 0 or idx >= len(options):
            return
        name, value, typ = options[idx]
        if typ == "bool":
            if name == "Show FPS Counter":
                self.state.show_fps = not self.state.show_fps
            elif name == "Screen Shake":
                self.state.screen_shake = not self.state.screen_shake
            elif name == "Particle Effects":
                self.state.particles = not self.state.particles
            elif name == "Damage Numbers":
                self.state.damage_numbers = not self.state.damage_numbers

    def _toggle_option(self) -> None:
        self._toggle_option_at_index(self._selected_option_idx)

    def _cycle_option_value(self, direction: int) -> None:
        options = self._get_options_for_tab()
        if self._selected_option_idx >= len(options):
            return
        name, value, typ = options[self._selected_option_idx]
        if typ == "enum":
            if name == "Quality Preset":
                presets = ["LOW", "MEDIUM", "HIGH", "ULTRA"]
                idx = (presets.index(value) + direction) % len(presets)
                self.state.quality_preset = presets[idx]
            elif name == "Difficulty":
                difficulties = ["EASY", "MEDIUM", "HARD", "VETERAN"]
                idx = (difficulties.index(value) + direction) % len(difficulties)
                self.state.difficulty = difficulties[idx]
        elif typ == "slider":
            if name == "Master Volume":
                self.state.master_volume = max(
                    0.0, min(1.0, self.state.master_volume + direction * 0.1)
                )
            elif name == "Music Volume":
                self.state.music_volume = max(
                    0.0, min(1.0, self.state.music_volume + direction * 0.1)
                )
            elif name == "SFX Volume":
                self.state.sfx_volume = max(0.0, min(1.0, self.state.sfx_volume + direction * 0.1))
        elif typ == "toggle":
            if name == "Autosave interval":
                if self.state.autosave_interval > 0:
                    self.state.autosave_interval = 0
                else:
                    self.state.autosave_interval = 300

    def _handle_click(self, mouse_pos) -> str | None:
        for rect, name in getattr(self, "_option_rects", []):
            if rect.collidepoint(mouse_pos):
                for i, (_, n, _) in enumerate(self._get_options_for_tab()):
                    if n == name:
                        self._selected_option_idx = i
                        break
                self._toggle_option()
                return "applied"
        return None

    def apply_to_systems(self, sound_system=None, display_config=None) -> dict:
        changes = {}
        if sound_system and hasattr(sound_system, "set_master_volume"):
            sound_system.set_master_volume(self.state.master_volume)
            changes["volume"] = self.state.master_volume
        return changes
