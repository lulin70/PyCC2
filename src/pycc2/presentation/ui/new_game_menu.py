"""
New Game Menu — Full-screen menu shown at game start.

Allows the player to select faction, difficulty, and campaign/skirmish
settings before entering the battle.  Rendered entirely with pygame
(no external UI library needed).

Screens:
  MAIN      — Title + New Campaign / Skirmish / Quit
  CAMPAIGN  — Campaign settings (side, difficulty preset, side details)
  SKIRMISH  — Skirmish settings (map, battle type, side, difficulty)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

import contextlib

import pygame

from pycc2.domain.systems.game_settings import (
    GAME_PRESETS,
    ExperienceLevel,
    GamePreset,
    GameSettings,
    SideSettings,
    SupplyLevelSetting,
)
from pycc2.domain.systems.skirmish_generator import SkirmishType

if TYPE_CHECKING:
    pass


# ========================================================================
# Menu screen enum
# ========================================================================


class MenuScreen(Enum):
    MAIN = auto()
    CAMPAIGN = auto()
    SKIRMISH = auto()
    LOAD_GAME = auto()


# ========================================================================
# Colour palette — dark military theme
# ========================================================================

_BG_COLOR = (28, 32, 24)  # dark olive
_PANEL_COLOR = (38, 42, 34)  # slightly lighter olive
_BORDER_COLOR = (80, 85, 60)  # muted olive border
_TITLE_COLOR = (218, 195, 130)  # gold
_TEXT_COLOR = (220, 220, 210)  # off-white
_TEXT_DIM = (140, 140, 130)  # dim text
_HIGHLIGHT_COLOR = (160, 145, 80)  # gold highlight for selected
_BTN_NORMAL = (50, 55, 42)  # button background
_BTN_HOVER = (70, 78, 55)  # button hover
_BTN_SELECTED = (100, 95, 50)  # selected / active button
_BTN_TEXT = (220, 220, 210)  # button text
_BTN_BORDER = (90, 95, 65)  # button border
_ACCENT_ALLIES = (80, 130, 200)  # blue for allies
_ACCENT_AXIS = (180, 80, 80)  # red for axis


# ========================================================================
# Difficulty preset display helpers
# ========================================================================

_PRESET_ORDER: list[GamePreset] = [
    GamePreset.RECRUIT,
    GamePreset.EASY,
    GamePreset.NORMAL,
    GamePreset.HARD,
    GamePreset.VETERAN,
]

_PRESET_LABELS: dict[GamePreset, str] = {
    GamePreset.RECRUIT: "RECRUIT",
    GamePreset.EASY: "EASY",
    GamePreset.NORMAL: "NORMAL",
    GamePreset.HARD: "HARD",
    GamePreset.VETERAN: "VETERAN",
}

_BATTLE_TYPE_ORDER: list[SkirmishType] = [
    SkirmishType.MEETING_ENGAGEMENT,
    SkirmishType.ATTACK_DEFEND,
    SkirmishType.BREAKTHROUGH,
    SkirmishType.HOLD_GROUND,
]

_BATTLE_TYPE_LABELS: dict[SkirmishType, str] = {
    SkirmishType.MEETING_ENGAGEMENT: "Meeting Engagement",
    SkirmishType.ATTACK_DEFEND: "Attack / Defend",
    SkirmishType.BREAKTHROUGH: "Breakthrough",
    SkirmishType.HOLD_GROUND: "Hold Ground",
}

_EXP_LABELS: dict[ExperienceLevel, str] = {
    ExperienceLevel.CONSCRIPT: "CONSCRIPT",
    ExperienceLevel.REGULAR: "REGULAR",
    ExperienceLevel.VETERAN: "VETERAN",
    ExperienceLevel.ELITE: "ELITE",
}

_SUPPLY_LABELS: dict[SupplyLevelSetting, str] = {
    SupplyLevelSetting.ABUNDANT: "ABUNDANT",
    SupplyLevelSetting.ADEQUATE: "ADEQUATE",
    SupplyLevelSetting.SCARCE: "SCARCE",
    SupplyLevelSetting.CRITICAL: "CRITICAL",
}


# ========================================================================
# Available maps discovery
# ========================================================================


def _discover_maps() -> list[str]:
    """Return map stem names found in data/maps/ (excluding _schema)."""
    map_dir = Path("data/maps")
    if not map_dir.is_dir():
        return []
    return sorted(m.stem for m in map_dir.glob("*.json") if m.stem != "_schema")


# ========================================================================
# NewGameMenu dataclass
# ========================================================================


@dataclass
class NewGameMenu:
    """Full-screen new-game menu rendered with pygame."""

    screen_width: int = 1280
    screen_height: int = 720
    current_screen: MenuScreen = MenuScreen.MAIN
    selected_preset: GamePreset = GamePreset.NORMAL
    player_side: str = "allied"
    selected_map_index: int = 0
    available_maps: list[str] = field(default_factory=_discover_maps)
    battle_type: SkirmishType = SkirmishType.MEETING_ENGAGEMENT

    # Load game state
    _save_slots: list[tuple[int, object | None, object]] = field(default_factory=list, repr=False)
    _selected_save_slot: int = -1

    # Internal — button rectangles rebuilt each render
    _buttons: dict[str, pygame.Rect] = field(default_factory=dict, repr=False)
    _mouse_pos: tuple[int, int] = (0, 0)

    # Fonts — lazily initialised
    _font_title: pygame.font.Font | None = field(default=None, repr=False)
    _font_large: pygame.font.Font | None = field(default=None, repr=False)
    _font_normal: pygame.font.Font | None = field(default=None, repr=False)
    _font_small: pygame.font.Font | None = field(default=None, repr=False)

    # ------------------------------------------------------------------
    # Font helpers
    # ------------------------------------------------------------------

    def _ensure_fonts(self) -> None:
        if self._font_title is None:
            pygame.font.init()
            self._font_title = pygame.font.Font(None, 52)
            self._font_large = pygame.font.Font(None, 36)
            self._font_normal = pygame.font.Font(None, 28)
            self._font_small = pygame.font.Font(None, 22)

    # ------------------------------------------------------------------
    # Drawing primitives
    # ------------------------------------------------------------------

    def _draw_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        text: str,
        *,
        selected: bool = False,
        accent: tuple[int, int, int] | None = None,
    ) -> None:
        self._ensure_fonts()
        assert self._font_normal is not None
        hovered = rect.collidepoint(self._mouse_pos)

        if selected:
            bg = _BTN_SELECTED
        elif hovered:
            bg = _BTN_HOVER
        else:
            bg = _BTN_NORMAL

        pygame.draw.rect(surface, bg, rect, border_radius=6)
        border = accent if accent else _BTN_BORDER
        pygame.draw.rect(surface, border, rect, width=2, border_radius=6)

        txt_surf = self._font_normal.render(text, True, _BTN_TEXT)
        txt_rect = txt_surf.get_rect(center=rect.center)
        surface.blit(txt_surf, txt_rect)

    def _draw_label(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        text: str,
        *,
        color: tuple[int, int, int] | None = None,
        font: pygame.font.Font | None = None,
    ) -> int:
        self._ensure_fonts()
        c = color or _TEXT_COLOR
        f = font or self._font_normal
        assert f is not None
        surf = f.render(text, True, c)
        surface.blit(surf, (x, y))
        return surf.get_height()

    # ------------------------------------------------------------------
    # Screen renderers
    # ------------------------------------------------------------------

    def _render_main(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        self._buttons.clear()
        self._ensure_fonts()

        # Title
        title = "PyCC2 — Close Combat 2: A Bridge Too Far"
        assert self._font_title is not None
        ts = self._font_title.render(title, True, _TITLE_COLOR)
        surface.blit(ts, ((sw - ts.get_width()) // 2, sh // 5))

        # Subtitle
        sub = "Operation Market Garden, September 1944"
        assert self._font_small is not None
        ss = self._font_small.render(sub, True, _TEXT_DIM)
        surface.blit(ss, ((sw - ss.get_width()) // 2, sh // 5 + 58))

        # Buttons
        bw, bh = 320, 52
        bx = (sw - bw) // 2
        start_y = sh // 2 - 30
        gap = 68

        for i, (key, label) in enumerate(
            [
                ("new_campaign", "New Campaign"),
                ("load_game", "Load Game"),
                ("skirmish", "Skirmish"),
                ("quit", "Quit"),
            ]
        ):
            rect = pygame.Rect(bx, start_y + i * gap, bw, bh)
            self._buttons[key] = rect
            self._draw_button(surface, rect, label)

    def _render_campaign(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        self._buttons.clear()

        # Section title
        self._draw_label(
            surface,
            60,
            40,
            "Campaign Settings",
            color=_TITLE_COLOR,
            font=self._font_large,
        )

        # Campaign name
        self._draw_label(surface, 60, 90, "Campaign:  Market Garden", color=_TEXT_DIM)

        # Player side toggle
        side_label = (
            "Player Side:  Allies (British / US / Polish)"
            if self.player_side == "allied"
            else "Player Side:  Axis (German)"
        )
        side_accent = _ACCENT_ALLIES if self.player_side == "allied" else _ACCENT_AXIS
        side_rect = pygame.Rect(60, 130, 500, 40)
        self._buttons["toggle_side"] = side_rect
        self._draw_button(surface, side_rect, side_label, accent=side_accent)

        # Difficulty presets
        self._draw_label(
            surface,
            60,
            195,
            "Difficulty Preset",
            color=_TITLE_COLOR,
            font=self._font_normal,
        )

        pw, ph = 140, 42
        px_start = 60
        py = 225
        for i, preset in enumerate(_PRESET_ORDER):
            rect = pygame.Rect(px_start + i * (pw + 12), py, pw, ph)
            key = f"preset_{preset.name}"
            self._buttons[key] = rect
            is_sel = preset == self.selected_preset
            self._draw_button(
                surface,
                rect,
                _PRESET_LABELS[preset],
                selected=is_sel,
            )

        # Current side settings
        settings = GAME_PRESETS[self.selected_preset]
        detail_y = py + ph + 40

        # Allied settings
        self._draw_label(
            surface,
            60,
            detail_y,
            "Allied Forces",
            color=_ACCENT_ALLIES,
            font=self._font_large,
        )
        self._draw_label(
            surface,
            80,
            detail_y + 36,
            f"Experience:  {_EXP_LABELS[settings.allied_settings.experience_level]}",
        )
        self._draw_label(
            surface,
            80,
            detail_y + 64,
            f"Supply:  {_SUPPLY_LABELS[settings.allied_settings.supply_level]}",
        )

        # Axis settings
        axis_y = detail_y + 110
        self._draw_label(
            surface,
            60,
            axis_y,
            "Axis Forces",
            color=_ACCENT_AXIS,
            font=self._font_large,
        )
        self._draw_label(
            surface,
            80,
            axis_y + 36,
            f"Experience:  {_EXP_LABELS[settings.axis_settings.experience_level]}",
        )
        self._draw_label(
            surface,
            80,
            axis_y + 64,
            f"Supply:  {_SUPPLY_LABELS[settings.axis_settings.supply_level]}",
        )

        # Bottom buttons
        btn_y = sh - 80
        start_rect = pygame.Rect(sw // 2 - 170, btn_y, 200, 48)
        back_rect = pygame.Rect(sw // 2 + 30, btn_y, 140, 48)
        self._buttons["start_campaign"] = start_rect
        self._buttons["back"] = back_rect
        self._draw_button(surface, start_rect, "Start Campaign")
        self._draw_button(surface, back_rect, "Back")

    def _render_skirmish(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        self._buttons.clear()

        # Section title
        self._draw_label(
            surface,
            60,
            40,
            "Skirmish Settings",
            color=_TITLE_COLOR,
            font=self._font_large,
        )

        # Map selector
        self._draw_label(surface, 60, 90, "Map:", color=_TEXT_DIM)
        map_name = (
            self.available_maps[self.selected_map_index]
            if self.available_maps
            else "(no maps found)"
        )
        map_rect = pygame.Rect(160, 84, 400, 38)
        self._buttons["cycle_map"] = map_rect
        self._draw_button(surface, map_rect, f"<  {map_name}  >")

        # Battle type
        self._draw_label(surface, 60, 140, "Battle Type:", color=_TEXT_DIM)
        bt_label = _BATTLE_TYPE_LABELS[self.battle_type]
        bt_rect = pygame.Rect(220, 134, 340, 38)
        self._buttons["cycle_battle_type"] = bt_rect
        self._draw_button(surface, bt_rect, f"<  {bt_label}  >")

        # Player side
        side_label = (
            "Player Side:  Allies" if self.player_side == "allied" else "Player Side:  Axis"
        )
        side_accent = _ACCENT_ALLIES if self.player_side == "allied" else _ACCENT_AXIS
        side_rect = pygame.Rect(60, 190, 500, 40)
        self._buttons["toggle_side"] = side_rect
        self._draw_button(surface, side_rect, side_label, accent=side_accent)

        # Difficulty presets
        self._draw_label(
            surface,
            60,
            255,
            "Difficulty Preset",
            color=_TITLE_COLOR,
            font=self._font_normal,
        )

        pw, ph = 140, 42
        px_start = 60
        py = 285
        for i, preset in enumerate(_PRESET_ORDER):
            rect = pygame.Rect(px_start + i * (pw + 12), py, pw, ph)
            key = f"preset_{preset.name}"
            self._buttons[key] = rect
            is_sel = preset == self.selected_preset
            self._draw_button(
                surface,
                rect,
                _PRESET_LABELS[preset],
                selected=is_sel,
            )

        # Side settings detail
        settings = GAME_PRESETS[self.selected_preset]
        detail_y = py + ph + 30

        self._draw_label(
            surface,
            60,
            detail_y,
            "Allied Forces",
            color=_ACCENT_ALLIES,
            font=self._font_large,
        )
        self._draw_label(
            surface,
            80,
            detail_y + 36,
            f"Experience:  {_EXP_LABELS[settings.allied_settings.experience_level]}",
        )
        self._draw_label(
            surface,
            80,
            detail_y + 64,
            f"Supply:  {_SUPPLY_LABELS[settings.allied_settings.supply_level]}",
        )

        axis_y = detail_y + 110
        self._draw_label(
            surface,
            60,
            axis_y,
            "Axis Forces",
            color=_ACCENT_AXIS,
            font=self._font_large,
        )
        self._draw_label(
            surface,
            80,
            axis_y + 36,
            f"Experience:  {_EXP_LABELS[settings.axis_settings.experience_level]}",
        )
        self._draw_label(
            surface,
            80,
            axis_y + 64,
            f"Supply:  {_SUPPLY_LABELS[settings.axis_settings.supply_level]}",
        )

        # Bottom buttons
        btn_y = sh - 80
        start_rect = pygame.Rect(sw // 2 - 170, btn_y, 200, 48)
        back_rect = pygame.Rect(sw // 2 + 30, btn_y, 140, 48)
        self._buttons["start_skirmish"] = start_rect
        self._buttons["back"] = back_rect
        self._draw_button(surface, start_rect, "Start Skirmish")
        self._draw_button(surface, back_rect, "Back")

    def _render_load_game(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        self._buttons.clear()

        # Section title
        self._draw_label(
            surface,
            60,
            40,
            "Load Game",
            color=_TITLE_COLOR,
            font=self._font_large,
        )

        # Refresh save slots
        self._refresh_save_slots()

        if not self._save_slots:
            self._draw_label(
                surface,
                80,
                100,
                "No save files found.",
                color=_TEXT_DIM,
                font=self._font_normal,
            )
        else:
            # List save slots
            slot_y = 90
            for slot_idx, meta, status in self._save_slots:
                slot_key = f"save_slot_{slot_idx}"
                is_selected = slot_idx == self._selected_save_slot

                # Build slot info text
                if meta is not None:
                    from pycc2.infrastructure.save_system import SaveSlotStatus

                    if status == SaveSlotStatus.OK:
                        date_str = meta.saved_at[:19] if meta.saved_at else "unknown"
                        info = f"Slot {slot_idx}:  Tick {meta.tick}  |  {date_str}  |  Allies:{meta.allies_alive}  Axis:{meta.axis_alive}"
                    elif status == SaveSlotStatus.INCOMPATIBLE:
                        info = f"Slot {slot_idx}:  [Incompatible Version]"
                    else:
                        info = f"Slot {slot_idx}:  [Corrupted]"
                else:
                    info = f"Slot {slot_idx}:  [Empty]"

                rect = pygame.Rect(60, slot_y, sw - 120, 42)
                self._buttons[slot_key] = rect
                self._draw_button(surface, rect, info, selected=is_selected)
                slot_y += 50

        # Bottom buttons
        btn_y = sh - 80
        load_rect = pygame.Rect(sw // 2 - 250, btn_y, 200, 48)
        back_rect = pygame.Rect(sw // 2 + 50, btn_y, 140, 48)
        self._buttons["load_selected"] = load_rect
        self._buttons["back"] = back_rect
        self._draw_button(surface, load_rect, "Load Selected")
        self._draw_button(surface, back_rect, "Back")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, screen: pygame.Surface) -> None:
        """Render the current menu screen."""
        self._ensure_fonts()
        screen.fill(_BG_COLOR)

        # Decorative top/bottom bars
        sw, sh = screen.get_size()
        pygame.draw.rect(screen, _PANEL_COLOR, (0, 0, sw, 4))
        pygame.draw.rect(screen, _PANEL_COLOR, (0, sh - 4, sw, 4))

        renderer = {
            MenuScreen.MAIN: self._render_main,
            MenuScreen.CAMPAIGN: self._render_campaign,
            MenuScreen.SKIRMISH: self._render_skirmish,
            MenuScreen.LOAD_GAME: self._render_load_game,
        }
        renderer[self.current_screen](screen)

    def handle_click(self, pos: tuple[int, int]) -> str | None:
        """Process a mouse click.  Returns an action string or None."""
        for key, rect in self._buttons.items():
            if not rect.collidepoint(pos):
                continue

            # ---- Main screen ----
            if self.current_screen == MenuScreen.MAIN:
                if key == "new_campaign":
                    self.current_screen = MenuScreen.CAMPAIGN
                    return None
                if key == "load_game":
                    self.current_screen = MenuScreen.LOAD_GAME
                    return None
                if key == "skirmish":
                    self.current_screen = MenuScreen.SKIRMISH
                    return None
                if key == "quit":
                    return "quit"

            # ---- Campaign screen ----
            elif self.current_screen == MenuScreen.CAMPAIGN:
                if key == "toggle_side":
                    self.player_side = "axis" if self.player_side == "allied" else "allied"
                    return None
                if key.startswith("preset_"):
                    preset_name = key[len("preset_") :]
                    self.selected_preset = GamePreset[preset_name]
                    return None
                if key == "start_campaign":
                    return "start_campaign"
                if key == "back":
                    self.current_screen = MenuScreen.MAIN
                    return None

            # ---- Skirmish screen ----
            elif self.current_screen == MenuScreen.SKIRMISH:
                if key == "cycle_map":
                    if self.available_maps:
                        self.selected_map_index = (self.selected_map_index + 1) % len(
                            self.available_maps
                        )
                    return None
                if key == "cycle_battle_type":
                    idx = _BATTLE_TYPE_ORDER.index(self.battle_type)
                    self.battle_type = _BATTLE_TYPE_ORDER[(idx + 1) % len(_BATTLE_TYPE_ORDER)]
                    return None
                if key == "toggle_side":
                    self.player_side = "axis" if self.player_side == "allied" else "allied"
                    return None
                if key.startswith("preset_"):
                    preset_name = key[len("preset_") :]
                    self.selected_preset = GamePreset[preset_name]
                    return None
                if key == "start_skirmish":
                    return "start_skirmish"
                if key == "back":
                    self.current_screen = MenuScreen.MAIN
                    return None

            # ---- Load Game screen ----
            elif self.current_screen == MenuScreen.LOAD_GAME:
                if key.startswith("save_slot_"):
                    slot_str = key[len("save_slot_") :]
                    with contextlib.suppress(ValueError):
                        self._selected_save_slot = int(slot_str)
                    return None
                if key == "load_selected":
                    if self._selected_save_slot >= 0:
                        return f"load_game:{self._selected_save_slot}"
                    return None
                if key == "back":
                    self.current_screen = MenuScreen.MAIN
                    return None

        return None

    def handle_key(self, key: int) -> str | None:
        """Process a key press.  Returns an action string or None."""
        if key == pygame.K_ESCAPE:
            if self.current_screen != MenuScreen.MAIN:
                self.current_screen = MenuScreen.MAIN
                return None
            return "quit"

        # Arrow-key cycling on skirmish/campaign screens
        if self.current_screen in (MenuScreen.CAMPAIGN, MenuScreen.SKIRMISH):
            if key == pygame.K_LEFT:
                idx = _PRESET_ORDER.index(self.selected_preset)
                self.selected_preset = _PRESET_ORDER[(idx - 1) % len(_PRESET_ORDER)]
                return None
            if key == pygame.K_RIGHT:
                idx = _PRESET_ORDER.index(self.selected_preset)
                self.selected_preset = _PRESET_ORDER[(idx + 1) % len(_PRESET_ORDER)]
                return None
            if key == pygame.K_TAB:
                self.player_side = "axis" if self.player_side == "allied" else "allied"
                return None

        return None

    def update_mouse(self, pos: tuple[int, int]) -> None:
        """Track mouse position for hover highlighting."""
        self._mouse_pos = pos

    def get_settings(self) -> GameSettings:
        """Build a GameSettings from the current menu selections."""
        preset = GAME_PRESETS[self.selected_preset]
        return GameSettings(
            allied_settings=SideSettings(
                experience_level=preset.allied_settings.experience_level,
                supply_level=preset.allied_settings.supply_level,
            ),
            axis_settings=SideSettings(
                experience_level=preset.axis_settings.experience_level,
                supply_level=preset.axis_settings.supply_level,
            ),
            campaign_id="market_garden",
            player_side=self.player_side,
        )

    def get_selected_map(self) -> str:
        """Return the currently selected map stem name."""
        if self.available_maps:
            return self.available_maps[self.selected_map_index]
        return "arnhem"

    def get_battle_type(self) -> SkirmishType:
        """Return the currently selected skirmish battle type."""
        return self.battle_type

    def _refresh_save_slots(self) -> None:
        """Refresh the save slot list from the save manager."""
        try:
            from pycc2.infrastructure.save_system import SecureSaveManager

            manager = SecureSaveManager()
            self._save_slots = manager.list_all_slots()
        except (OSError, ValueError, RuntimeError) as e:
            logging.info("Save slot list refresh failed: %s", e)
            self._save_slots = []

    def get_selected_load_slot(self) -> int:
        """Return the currently selected save slot index, or -1 if none."""
        return self._selected_save_slot
