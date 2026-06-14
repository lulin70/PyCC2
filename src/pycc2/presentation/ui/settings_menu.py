from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.presentation.ui.keybind_manager import KeybindManager


class SettingsTab(Enum):
    GENERAL = auto()
    AUDIO = auto()
    CONTROLS = auto()
    GAMEPLAY = auto()


@dataclass(slots=True)
class SettingsState:
    _SAVE_PATH = os.path.join(
        os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
        'pycc2',
        'settings.json',
    )

    master_volume: float = 0.8
    music_volume: float = 0.6
    sfx_volume: float = 1.0
    quality_preset: str = "HIGH"
    show_fps: bool = True
    show_debug: bool = False
    screen_shake: bool = True
    particles: bool = True
    damage_numbers: bool = True
    difficulty: str = "MEDIUM"
    autosave_interval: int = 300

    def save(self) -> None:
        """Persist settings to disk."""
        path = Path(self._SAVE_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'master_volume': self.master_volume,
            'music_volume': self.music_volume,
            'sfx_volume': self.sfx_volume,
            'quality_preset': self.quality_preset,
            'show_fps': self.show_fps,
            'show_debug': self.show_debug,
            'screen_shake': self.screen_shake,
            'particles': self.particles,
            'damage_numbers': self.damage_numbers,
            'difficulty': self.difficulty,
            'autosave_interval': self.autosave_interval,
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> SettingsState:
        """Load settings from disk, falling back to defaults."""
        path = Path(cls._SAVE_PATH)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()


class SettingsMenu:
    def __init__(self, display_config, keybind_manager: KeybindManager | None = None):
        self.state = SettingsState()
        self._display_config = display_config
        self._keybind_manager = keybind_manager
        self._visible = False
        self._active_tab = SettingsTab.GENERAL
        self._tab_names = ["General", "Audio", "Controls", "Gameplay"]
        self._option_rects: list[tuple[object, str]] = []
        self._selected_option_idx: int = 0

        # Pre-create fonts to avoid per-frame allocation (lazy init)
        self._font_lg = None
        self._font_md = None
        self._font_sm = None

        # Cached surfaces (rebuilt on resize)
        self._overlay: object | None = None
        self._panel: object | None = None
        self._cached_size: tuple[int, int] = (0, 0)

    def _init_fonts(self) -> None:
        import pygame
        dc = self._display_config
        self._font_lg = pygame.font.Font(None, int(dc.font_size_title * 1.2))
        self._font_md = pygame.font.Font(None, int(dc.font_size_large))
        self._font_sm = pygame.font.Font(None, int(dc.font_size_normal))

    def _rebuild_surfaces(self, sw: int, sh: int) -> None:
        import pygame
        self._overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pw, ph = min(600, int(sw * 0.65)), min(500, int(sh * 0.75))
        self._panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        self._cached_size = (sw, sh)

    @property
    def visible(self) -> bool:
        return self._visible

    def toggle(self) -> None:
        self._visible = not self._visible

    def show(self) -> None:
        self.state = SettingsState.load()
        self._visible = True

    def hide(self) -> None:
        self.state.save()
        self._visible = False

    def handle_input(self, event, mouse_pos) -> str | None:
        import pygame

        if event.type == pygame.KEYDOWN:
            # If keybind manager is listening for a key, capture it
            if (self._keybind_manager and self._keybind_manager.is_listening
                    and self._active_tab == SettingsTab.CONTROLS):
                if self._keybind_manager.handle_key(event.key):
                    return "applied"
                # ESC cancels listening (handled by handle_key returning False)
                return None

            if event.key == pygame.K_ESCAPE:
                # Cancel listening if active, otherwise close
                if self._keybind_manager and self._keybind_manager.is_listening:
                    self._keybind_manager.cancel_listening()
                    return None
                self.hide()
                return "closed"
            if event.key == pygame.K_TAB:
                tabs = list(SettingsTab)
                idx = (tabs.index(self._active_tab) + 1) % len(tabs)
                self._active_tab = tabs[idx]
                self._selected_option_idx = 0
                # Cancel listening when switching tabs
                if self._keybind_manager and self._keybind_manager.is_listening:
                    self._keybind_manager.cancel_listening()
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

        # Lazy-init fonts on first render
        if self._font_lg is None:
            self._init_fonts()

        # Rebuild cached surfaces if screen size changed
        if self._cached_size != (sw, sh):
            self._rebuild_surfaces(sw, sh)

        self._overlay.fill((0, 0, 0, 180))
        screen.blit(self._overlay, (0, 0))

        pw, ph = min(600, int(sw * 0.65)), min(500, int(sh * 0.75))
        px, py = (sw - pw) // 2, (sh - ph) // 2

        self._panel.fill((25, 28, 38, 245))
        pygame.draw.rect(self._panel, (100, 110, 140), (0, 0, pw, ph), 2, border_radius=10)
        screen.blit(self._panel, (px, py))

        title_surf = self._font_lg.render("⚙ Settings", True, (220, 220, 230))
        screen.blit(title_surf, (px + (pw - title_surf.get_width()) // 2, py + 15))

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
            txt = self._font_md.render(name, True, color)
            screen.blit(txt, (tx + (tab_w - 4 - txt.get_width()) // 2, tab_y + 5))

        opt_y = tab_y + 40
        options = self._get_options_for_tab()
        self._option_rects = []

        for i, (opt_name, opt_value, opt_type) in enumerate(options):
            oy = opt_y + i * 32
            if oy > py + ph - 50:
                break

            name_surf = self._font_sm.render(opt_name, True, (200, 200, 210))
            screen.blit(name_surf, (px + 20, oy))

            val_str = self._format_value(opt_value, opt_type)
            # Highlight the listening keybind
            is_listening = (self._keybind_manager and self._keybind_manager.is_listening
                            and opt_type == "keybind"
                            and self._keybind_manager.listening_action)
            if is_listening and val_str == "Press any key...":
                val_color = (255, 200, 80)
            elif opt_type == "keybind":
                val_color = (80, 180, 255) if i == self._selected_option_idx else (140, 200, 140)
            elif opt_type == "reset_keybinds":
                val_color = (200, 120, 120)
            else:
                val_color = (80, 180, 255) if i == self._selected_option_idx else (140, 200, 140)
            val_surf = self._font_sm.render(val_str, True, val_color)
            screen.blit(val_surf, (px + pw - 20 - val_surf.get_width(), oy))

            self._option_rects.append((pygame.Rect(px + 15, oy, pw - 30, 28), opt_name))

            if i == 0:
                if self._active_tab == SettingsTab.CONTROLS and self._keybind_manager:
                    hint = self._font_sm.render(
                        "Enter/Click to rebind | ESC to cancel", True, (120, 120, 130)
                    )
                else:
                    hint = self._font_sm.render(
                        "← → to change | Enter to toggle | ↑↓ to select", True, (120, 120, 130)
                    )
                screen.blit(hint, (px + 20, oy + 18))

        footer_y = py + ph - 35
        footer = self._font_sm.render(
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
                if self._keybind_manager:
                    from pycc2.presentation.ui.keybind_manager import ACTION_LABELS
                    bindings = self._keybind_manager.get_all_bindings()
                    rows = []
                    for action in ACTION_LABELS:
                        label = ACTION_LABELS[action]
                        key_combo = bindings.get(action, (0,))
                        key_name = self._keybind_manager.key_name(key_combo) if key_combo else "???"
                        if self._keybind_manager.is_listening and self._keybind_manager.listening_action == action:
                            key_name = "Press any key..."
                        rows.append((label, key_name, "keybind"))
                    rows.append(("Reset to Default", "", "reset_keybinds"))
                    return rows
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
        elif typ == "keybind":
            # Start listening for a new key for this action
            if self._keybind_manager:
                from pycc2.presentation.ui.keybind_manager import ACTION_LABELS
                # Find the action name from the label
                for action, label in ACTION_LABELS.items():
                    if label == name:
                        self._keybind_manager.start_listening(action)
                        break
        elif typ == "reset_keybinds":
            if self._keybind_manager:
                self._keybind_manager.reset_to_default()

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
