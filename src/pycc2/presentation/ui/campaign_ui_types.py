"""Campaign UI data classes and layout/color constants."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CampaignBattle:
    """A single battle entry in the campaign."""

    battle_id: str
    name: str
    map_file: str
    description: str = ""
    completed: bool = False
    locked: bool = False
    objectives: list[str] = field(default_factory=list)
    allied_forces: list[str] = field(default_factory=list)
    axis_forces: list[str] = field(default_factory=list)


@dataclass
class CampaignOperation:
    """Top-level campaign operation data."""

    operation_id: str
    name: str
    day: int
    total_days: int = 9  # Market Garden was a 9-day operation (Sept 17-26, 1944)
    description: str = ""
    historical_briefing: str = ""
    sector: str = ""  # 'arnhem', 'nijmegen', 'eindhoven'
    battles: list[CampaignBattle] = field(default_factory=list)


# Layout constants
MARGIN = 20
BATTLE_ITEM_HEIGHT = 36
BATTLE_LIST_WIDTH = 400
OP_LIST_WIDTH = 500
BUTTON_WIDTH = 140
BUTTON_HEIGHT = 36

# Colors (CC2 military palette)
BG_COLOR = (40, 44, 52)
PANEL_COLOR = (50, 55, 45)
BORDER_COLOR = (90, 96, 80)
TEXT_COLOR = (220, 220, 220)
HIGHLIGHT_COLOR = (255, 255, 100)
SELECTED_BG = (60, 70, 55)
LOCKED_COLOR = (100, 100, 100)
COMPLETED_COLOR = (80, 180, 80)
BUTTON_COLOR = (65, 75, 58)
BUTTON_HOVER = (85, 95, 72)
BUTTON_BORDER = (110, 120, 95)
VICTORY_COLOR = (80, 200, 80)
DEFEAT_COLOR = (200, 80, 80)
MINIMAP_BG = (30, 35, 25)
