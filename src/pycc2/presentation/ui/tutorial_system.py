from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame


class TutorialStep(Enum):
    WELCOME = auto()
    SELECT_UNIT = auto()
    MOVE_UNIT = auto()
    ATTACK_ENEMY = auto()
    VICTORY_CONDITIONS = auto()
    COMPLETE = auto()


@dataclass(slots=True)
class TutorialState:
    step: TutorialStep = TutorialStep.WELCOME
    completed: set[TutorialStep] = field(default_factory=set)
    dismissed: bool = False
    show_hints: bool = True
    hint_cooldown: int = 0


class TutorialOverlay:
    STEPS = {
        TutorialStep.WELCOME: {
            "title": "Welcome to PyCC2",
            "lines": [
                "Close Combat 2 Remake — A WWII Tactical Simulator",
                "",
                "Your objective: Command Allied forces to defeat the Axis.",
                "",
                "CONTROLS:",
                "  Left Click  → Select unit",
                "  Right Click → Move or Attack",
                "  ESC        → Pause / Menu",
                "  F10        → Settings",
                "",
                "Press SPACE or click to begin...",
            ],
            "highlight_keys": ["SPACE"],
            "highlight_ui": ["command_bar"],
        },
        TutorialStep.SELECT_UNIT: {
            "title": "Select Your Units",
            "lines": [
                "Click on any GREEN (Allied) unit to select it.",
                "Selected units show a yellow ring.",
                "Hold SHIFT + Click to select multiple units.",
                "",
                "TIP: Your Commander (★) is your most valuable unit!",
            ],
            "highlight_ui": ["unit_panel"],
        },
        TutorialStep.MOVE_UNIT: {
            "title": "Move Your Units",
            "lines": [
                "After selecting a unit, RIGHT-CLICK on open ground to move.",
                "Units will pathfind around obstacles.",
                "",
                "TIP: Woods and buildings provide cover but slow movement.",
            ],
            "highlight_ui": ["minimap"],
        },
        TutorialStep.ATTACK_ENEMY: {
            "title": "Engage the Enemy",
            "lines": [
                "RIGHT-CLICK directly on a GRAY (Axis) unit to attack!",
                "Watch for damage numbers floating up when you hit.",
                "",
                "Press A then right-click for Attack mode (auto-fires).",
                "",
                "⚔ Eliminate the enemy commander (Oberst Krebs)",
                "   or destroy all enemy forces to win!",
            ],
            "highlight_ui": ["health"],
        },
        TutorialStep.VICTORY_CONDITIONS: {
            "title": "Victory Conditions",
            "lines": [
                "You win by doing ONE of these:",
                "  1. Kill the enemy Commander (★ symbol)",
                "  2. Destroy ALL enemy units",
                "  3. Cause enemy morale collapse",
                "",
                "Good luck, Commander! ⭐",
            ],
            "highlight_keys": [],
        },
    }

    def __init__(self, display_config):
        self.state = TutorialState()
        self._display_config = display_config
        self._visible = False
        self._alpha: float = 0.0
        self._target_alpha: float = 0.9
        self._current_hint: str = ""
        self._hint_timer: int = 0
        self._hint_position: tuple[float, float] = (0.0, 0.0)

        # Pre-create fonts to avoid per-frame allocation (lazy init)
        self._font_lg = None
        self._font_md = None
        self._font_sm = None
        self._font_hint = None

        # Cached surfaces (rebuilt on resize)
        self._overlay: pygame.Surface | None = None
        self._panel_surf: pygame.Surface | None = None
        self._cached_size: tuple[int, int] = (0, 0)

    def _init_fonts(self) -> None:
        import pygame

        dc = self._display_config
        self._font_lg = pygame.font.Font(None, int(dc.font_size_title * 1.3))
        self._font_md = pygame.font.Font(None, int(dc.font_size_normal))
        self._font_sm = pygame.font.Font(None, int(dc.font_size_small))
        self._font_hint = pygame.font.Font(None, 18)

    def _rebuild_surfaces(self, sw: int, sh: int) -> None:
        import pygame

        self._overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pw, ph = min(550, int(sw * 0.6)), min(380, int(sh * 0.65))
        self._panel_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        self._cached_size = (sw, sh)

    @property
    def visible(self) -> bool:
        return self._visible

    def show(self, step: TutorialStep | None = None) -> None:
        self._visible = True
        if step:
            self.state.step = step
        self._target_alpha = 0.9
        self._alpha = 0.0

    def hide(self) -> None:
        self._target_alpha = 0.0

    def toggle(self) -> None:
        if self._visible:
            self.hide()
        else:
            self.show()

    def advance_step(self) -> bool:
        steps = list(TutorialStep)
        current_idx = steps.index(self.state.step)
        if current_idx < len(steps) - 1:
            self.state.completed.add(self.state.step)
            self.state.step = steps[current_idx + 1]
            return True
        self.state.completed.add(self.state.step)
        self.state.step = TutorialStep.COMPLETE
        self.hide()
        return False

    def handle_input(self, event) -> str | None:
        import pygame

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if self.state.step != TutorialStep.COMPLETE:
                    self.advance_step()
                    return "advanced"
            elif event.key == pygame.K_ESCAPE:
                self.hide()
                return "closed"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state.step != TutorialStep.COMPLETE:
                self.advance_step()
                return "advanced"
        return None

    def update(self) -> None:
        if abs(self._alpha - self._target_alpha) > 0.01:
            speed = 0.08 if self._target_alpha > self._alpha else 0.12
            self._alpha += (self._target_alpha - self._alpha) * speed
        else:
            self._alpha = self._target_alpha

        if self.state.step == TutorialStep.COMPLETE and self._target_alpha > 0.5:
            if self._hint_timer > 180:
                self.hide()
                self._hint_timer = 0
        self._hint_timer += 1

        if self.state.hint_cooldown > 0:
            self.state.hint_cooldown -= 1

    def render(self, screen) -> None:
        if self._alpha < 0.01:
            return

        import pygame

        sw, sh = screen.get_size()

        content = self.STEPS.get(self.state.step)
        if not content:
            return

        # Lazy-init fonts on first render
        if self._font_lg is None:
            self._init_fonts()

        # Rebuild cached surfaces if screen size changed
        if self._cached_size != (sw, sh):
            self._rebuild_surfaces(sw, sh)

        if self._overlay is None or self._panel_surf is None or self._font_lg is None:
            return

        if self._alpha < 0.99:
            self._overlay.fill((0, 0, 0, int(self._alpha * 180)))
            screen.blit(self._overlay, (0, 0))

        pw, ph = min(550, int(sw * 0.6)), min(380, int(sh * 0.65))
        px, py = (sw - pw) // 2, (sh - ph) // 2 - 30

        self._panel_surf.fill((20, 24, 36, int(self._alpha * 240)))
        pygame.draw.rect(
            self._panel_surf,
            (80, 100, 140, int(self._alpha * 200)),
            (0, 0, pw, ph),
            2,
            border_radius=12,
        )
        screen.blit(self._panel_surf, (px, py))

        title_surf = self._font_lg.render(content["title"], True, (220, 230, 255))
        screen.blit(title_surf, (px + (pw - title_surf.get_width()) // 2, py + 18))

        steps = list(TutorialStep)
        current_idx = steps.index(self.state.step)
        dot_y = py + 52
        dot_spacing = min(20, (pw - 40) // len(steps))
        dot_start_x = px + (pw - dot_spacing * (len(steps) - 1)) // 2
        for i, _step in enumerate(steps):
            color = (100, 180, 255) if i <= current_idx else (60, 70, 80)
            if i < current_idx:
                pygame.draw.circle(screen, color, (dot_start_x + i * dot_spacing, dot_y), 5)
            elif i == current_idx:
                pygame.draw.circle(
                    screen, (150, 210, 255), (dot_start_x + i * dot_spacing, dot_y), 7, 2
                )
            else:
                pygame.draw.circle(screen, color, (dot_start_x + i * dot_spacing, dot_y), 4)

        text_y = py + 72
        for line in content["lines"]:
            if line.startswith("  "):
                color = (160, 200, 160)
            elif line.startswith("⚔") or line.startswith("★"):
                color = (255, 220, 120)
            else:
                color = (210, 215, 225)

            text_surf = self._font_md.render(line, True, color)
            screen.blit(text_surf, (px + 25, text_y))
            text_y += 22

        footer_y = py + ph - 35
        if self.state.step != TutorialStep.COMPLETE:
            footer = self._font_sm.render(
                "[ SPACE / Click to continue ]  [ ESC to close ]", True, (140, 150, 170)
            )
        else:
            footer = self._font_sm.render(
                "Tutorial complete! Press F1 to review anytime.", True, (140, 200, 140)
            )
        screen.blit(footer, (px + (pw - footer.get_width()) // 2, footer_y))

    def show_contextual_hint(
        self, text: str, position: tuple[float, float], lifetime: int = 120
    ) -> None:
        self._current_hint = text
        self._hint_position = position
        self.state.hint_cooldown = lifetime

    def render_hint(self, screen) -> None:
        if self.state.hint_cooldown <= 0 or not self._current_hint:
            return
        # Lazy-init fonts on first use
        if self._font_hint is None:
            self._init_fonts()
        alpha = min(255, int(self.state.hint_cooldown * 2))
        surf = self._font_hint.render(
            f"💡 {self._current_hint}",
            True,
            (255, 255, 200),
        )
        surf.set_alpha(alpha)
        x, y = int(self._hint_position[0]), int(self._hint_position[1])
        screen.blit(surf, (x - surf.get_width() // 2, y - 25))
