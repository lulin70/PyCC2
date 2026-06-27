"""Operation Timeline UI — displays campaign progress and day selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame

    from pycc2.domain.systems.campaign_state import CampaignState


DAY_INFO = {
    "DAY_1_SEPT17": {
        "display": "Day 1 — Sept 17",
        "short": "D1:17 Sep",
        "desc": "Initial Airborne Drops — Eindhoven & Son",
        "historical": "101st and 82nd Airborne divisions drop behind enemy lines.",
    },
    "DAY_2_SEPT18": {
        "display": "Day 2 — Sept 18",
        "short": "D2:18 Sep",
        "desc": "Consolidation — Son & Veghel Bridges",
        "historical": "Secure supply route; XXX Corps advances from south.",
    },
    "DAY_3_SEPT19": {
        "display": "Day 3 — Sept 19",
        "short": "D3:19 Sep",
        "desc": "Push North — Grave & Nijmegen",
        "historical": "Critical push toward Waal river crossings.",
    },
    "DAY_4_SEPT20": {
        "display": "Day 4 — Sept 20",
        "short": "D4:20 Sep",
        "desc": "Hold & Resupply",
        "historical": "German counterattacks intensify. Resupply by air.",
    },
    "DAY_5_SEPT21": {
        "display": "Day 5 — Sept 21",
        "short": "D5:21 Sep",
        "desc": "Final Push or Desperate Defense",
        "historical": "Last chance to reach Arnhem or evacuate.",
    },
    "DAY_6_SEPT22": {
        "display": "Day 6 — Sept 22",
        "short": "D6:22 Sep",
        "desc": "Arnhem — The Bridge Too Far",
        "historical": "Relief or evacuation of British 1st Airborne.",
    },
}


@dataclass
class TimelineConfig:
    x: int = 10
    y: int = 10
    width: int = 780
    day_height: int = 36
    active_color: tuple = (60, 130, 200)
    completed_color: tuple = (60, 150, 80)
    locked_color: tuple = (80, 80, 90)
    current_color: tuple = (200, 160, 50)
    text_color: tuple = (220, 220, 220)


class OperationTimelineUI:
    def __init__(self, config: TimelineConfig | None = None):
        self.config = config or TimelineConfig()
        self._days_order = list(DAY_INFO.keys())

    def render(
        self,
        screen: pygame.Surface,
        campaign_state: CampaignState | None = None,
        font=None,
        small_font=None,
    ) -> list[dict]:
        import pygame

        cfg = self.config
        clickable_areas = []

        current_day_name = campaign_state.current_day.name if campaign_state else "DAY_1_SEPT17"

        for i, day_key in enumerate(self._days_order):
            info = DAY_INFO[day_key]
            y_pos = cfg.y + i * cfg.day_height

            is_current = day_key == current_day_name
            is_past = (
                i < self._days_order.index(current_day_name)
                if current_day_name in self._days_order
                else False
            )

            if is_current:
                color = cfg.current_color
            elif is_past:
                color = cfg.completed_color
            else:
                color = cfg.locked_color

            day_rect = pygame.Rect(cfg.x, y_pos, cfg.width, cfg.day_height - 4)
            pygame.draw.rect(screen, color, day_rect, border_radius=6)
            pygame.draw.rect(screen, (255, 255, 255), day_rect, 1, border_radius=6)

            if font:
                display_text = info["display"]
                if is_current:
                    display_text = "▶ " + display_text + " (CURRENT)"
                surf = font.render(display_text, True, cfg.text_color)
                screen.blit(surf, (cfg.x + 10, y_pos + 8))

            if small_font and is_current:
                desc_surf = small_font.render(info["desc"], True, (180, 180, 180))
                screen.blit(desc_surf, (cfg.x + 10, y_pos + 24))

            clickable_areas.append(
                {
                    "day_key": day_key,
                    "rect": day_rect,
                    "is_current": is_current,
                    "clickable": is_past or is_current,
                }
            )

        return clickable_areas

    def handle_click(self, x: int, y: int, clickable_areas: list[dict]) -> str | None:
        for area in clickable_areas:
            if area["rect"].collidepoint(x, y) and area["clickable"]:
                return area["day_key"]
        return None

    def get_day_info(self, day_key: str) -> dict | None:
        return DAY_INFO.get(day_key)

    @property
    def total_days(self) -> int:
        return len(self._days_order)

    @property
    def days_order(self) -> list[str]:
        return list(self._days_order)
