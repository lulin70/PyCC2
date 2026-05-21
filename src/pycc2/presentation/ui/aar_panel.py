"""
After Action Report (AAR) Panel — displays detailed post-battle statistics.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame
    from pycc2.domain.systems.battle_result import BattleResult


@dataclass
class AARConfig:
    width: int = 600
    height: int = 420
    x: int = 110
    y: int = 90
    bg_color: tuple = (20, 24, 34)
    border_color: tuple = (80, 90, 110)
    title_color: tuple = (255, 220, 100)
    text_color: tuple = (210, 210, 210)
    victory_color: tuple = (100, 200, 100)
    defeat_color: tuple = (200, 80, 80)
    stat_label_color: tuple = (160, 160, 170)
    stat_value_color: tuple = (240, 240, 250)
    section_divider: tuple = (50, 55, 70)


class AARPanel:
    def __init__(self, config: AARConfig | None = None):
        self.config = config or AARConfig()
        self._visible: bool = False
        self._result: BattleResult | None = None
        self._scroll_offset: int = 0

    @property
    def visible(self) -> bool:
        return self._visible

    def show(self, result: BattleResult) -> None:
        self._result = result
        self._visible = True
        self._scroll_offset = 0

    def hide(self) -> None:
        self._visible = False
        self._result = None

    def toggle(self, result: BattleResult | None = None) -> None:
        if self._visible:
            self.hide()
        elif result is not None:
            self.show(result)

    @property
    def result(self) -> BattleResult | None:
        return self._result

    def render(self, screen: "pygame.Surface", font=None, small_font=None) -> None:
        if not self._visible or self._result is None:
            return

        import pygame

        cfg = self.config
        result = self._result

        panel = pygame.Surface((cfg.width, cfg.height), pygame.SRCALPHA)
        panel.fill((*cfg.bg_color, 245))
        pygame.draw.rect(panel, cfg.border_color, (0, 0, cfg.width, cfg.height), 2, border_radius=8)

        y = 12

        title_color = cfg.victory_color if result.is_victory else cfg.defeat_color
        outcome_text = "VICTORY" if result.is_victory else "DEFEAT"
        if font:
            title_surf = font.render(
                f"AFTER ACTION REPORT — {outcome_text}", True, title_color
            )
            panel.blit(title_surf, (cfg.width // 2 - title_surf.get_width() // 2, y))
        y += 32

        if small_font:
            info = f"Mission: {result.mission_name} | Duration: {result.ticks_elapsed // 30}s | VP: {result.victory_points}"
            info_surf = small_font.render(info, True, cfg.text_color)
            panel.blit(info_surf, (16, y))
        y += 28

        pygame.draw.line(panel, cfg.section_divider, (16, y), (cfg.width - 16, y), 1)
        y += 12

        stats = [
            ("Allies Killed", str(result.allies_killed), cfg.defeat_color),
            ("Axis Killed", str(result.axis_killed), cfg.victory_color),
            ("Allies Routed", str(result.allies_routed), cfg.defeat_color),
            ("Axis Routed", str(result.axis_routed), cfg.victory_color),
            ("", "", (0, 0, 0)),
            ("Allies Accuracy", f"{result.allies_accuracy:.1%}", cfg.stat_value_color),
            ("Axis Accuracy", f"{result.axis_accuracy:.1%}", cfg.stat_value_color),
            ("Survival Rate", f"{result.survival_rate_allies:.1%}", cfg.stat_value_color),
            ("Objectives", f"{result.objectives_completed}/{result.objectives_total}", cfg.stat_value_color),
        ]

        for label, value, color in stats:
            if label == "":
                y += 8
                continue
            if small_font:
                lbl = small_font.render(label, True, cfg.stat_label_color)
                val = small_font.render(value, True, color)
                panel.blit(lbl, (20, y))
                panel.blit(val, (cfg.width - 20 - val.get_width(), y))
            y += 22

        y += 8
        pygame.draw.line(panel, cfg.section_divider, (16, y), (cfg.width - 16, y), 1)
        y += 12

        if small_font:
            header = small_font.render("Unit Performance:", True, cfg.title_color)
            panel.blit(header, (20, y))
        y += 22

        ally_records = [r for r in result.unit_records if r.faction == "allies"][:6]
        for record in ally_records:
            if small_font:
                status = "✓" if record.survived else "✗"
                eff = f"{record.efficiency:.0%}" if record.shots_fired > 0 else "N/A"
                line = f"  {status} {record.unit_type} | DMG:{record.damage_dealt:.0f} K:{record.kills} ACC:{eff}"
                color = cfg.victory_color if record.survived else cfg.defeat_color
                surf = small_font.render(line, True, color)
                panel.blit(surf, (24, y))
            y += 18

        y = cfg.height - 36
        if small_font:
            prompt = small_font.render("Press SPACE or CLICK to continue...", True, (140, 140, 150))
            panel.blit(prompt, (cfg.width // 2 - prompt.get_width() // 2, y))

        screen.blit(panel, (cfg.x, cfg.y))

    def handle_click(self, x: int, y: int) -> bool:
        if not self._visible:
            return False
        cfg = self.config
        if (cfg.x <= x < cfg.x + cfg.width and cfg.y <= y < cfg.y + cfg.height):
            self.hide()
            return True
        return False
