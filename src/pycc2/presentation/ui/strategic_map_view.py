"""Strategic Map View - Market Garden campaign overview."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import pygame

    from pycc2.domain.systems.campaign_state import CampaignState


class SectorStatus(Enum):
    """Control status of a sector."""

    ALLIED_CONTROL = auto()
    AXIS_CONTROL = auto()
    CONTESTED = auto()
    LOCKED = auto()


@dataclass
class Sector:
    """A strategic sector in Market Garden."""

    name: str
    position: tuple[float, float]  # Screen position on strategic map
    status: SectorStatus = SectorStatus.CONTESTED
    operations: list[str] = field(default_factory=list)
    color: tuple[int, int, int] = (100, 100, 100)

    def update_color(self) -> None:
        """Update color based on status."""
        color_map = {
            SectorStatus.ALLIED_CONTROL: (0, 150, 0),
            SectorStatus.AXIS_CONTROL: (150, 0, 0),
            SectorStatus.CONTESTED: (150, 150, 0),
            SectorStatus.LOCKED: (100, 100, 100),
        }
        self.color = color_map.get(self.status, (100, 100, 100))


@dataclass
class StrategicMapView:
    """Strategic-level map showing entire Market Garden corridor.

    Features:
    - Overview of all sectors (Arnhem/Nijmegen/Eindhoven)
    - Operation and battle markers
    - Click to navigate to specific battle
    - Timeline indicator

    Simplified Implementation:
    - Static background image with hot zones
    - Sector click detection
    - Status color coding
    """

    sectors: dict[str, Sector] = field(init=False)
    _background_image = None
    _campaign_state: CampaignState | None = None
    _bg_surface: pygame.Surface | None = field(default=None, init=False, repr=False)
    _bg_size: tuple[int, int] = field(default=(0, 0), init=False, repr=False)

    def __init__(self):
        """Initialize the StrategicMapView."""
        self.sectors = {}
        self._load_default_sectors()

    def _load_default_sectors(self) -> None:
        """Load default Market Garden sector data."""
        sector_data = [
            ("arnhem", "Arnhem", (700, 100), SectorStatus.CONTESTED),
            ("nijmegen", "Nijmegen", (500, 300), SectorStatus.CONTESTED),
            ("eindhoven", "Eindhoven", (300, 450), SectorStatus.ALLIED_CONTROL),
            ("veghel", "Veghel", (250, 520), SectorStatus.ALLIED_CONTROL),
            ("son", "Son", (350, 480), SectorStatus.ALLIED_CONTROL),
            ("grave", "Grave", (420, 400), SectorStatus.CONTESTED),
        ]

        for sid, name, pos, status in sector_data:
            sector = Sector(name=name, position=pos, status=status)
            sector.update_color()
            self.sectors[sid] = sector

    def set_campaign_state(self, state: CampaignState) -> None:
        """Link to campaign state for live updates."""
        self._campaign_state = state
        self._update_sectors_from_campaign()

    def _update_sectors_from_campaign(self) -> None:
        """Update sector statuses from campaign progress."""
        if not self._campaign_state:
            return

        for sector_id, sector in self.sectors.items():
            if hasattr(self._campaign_state, "sectors_controlled"):
                control = self._campaign_state.sectors_controlled.get(sector_id)
                if control == "allied":
                    sector.status = SectorStatus.ALLIED_CONTROL
                elif control == "axis":
                    sector.status = SectorStatus.AXIS_CONTROL
                else:
                    sector.status = SectorStatus.CONTESTED
                sector.update_color()

    def handle_click(
        self,
        click_pos: tuple[int, int],
    ) -> str | None:
        """Handle click on strategic map.

        Args:
            click_pos: Screen coordinates of click

        Returns:
            Sector ID if clicked on sector, None otherwise

        """
        for sector_id, sector in self.sectors.items():
            sx, sy = sector.position
            dx = click_pos[0] - sx
            dy = click_pos[1] - sy

            if (dx * dx + dy * dy) ** 0.5 < 40:  # 40 pixel radius
                return sector_id

        return None

    def render(self, surface, screen_size: tuple[int, int]) -> None:
        """Render strategic map view.

        Args:
            surface: Pygame surface to draw on
            screen_size: Current screen dimensions

        """
        try:
            import pygame

            width, height = screen_size

            # Lazy-init or resize bg surface
            if self._bg_surface is None or self._bg_size != (width, height):
                self._bg_surface = pygame.Surface((width, height))
                self._bg_size = (width, height)
            self._bg_surface.fill((30, 35, 45))

            font_large = pygame.font.SysFont("arial", 24, bold=True)
            font_small = pygame.font.SysFont("arial", 14)

            title = font_large.render("MARKET GARDEN - STRATEGIC MAP", True, (255, 215, 0))
            self._bg_surface.blit(title, (width // 2 - title.get_width() // 2, 20))

            corridor_color = (60, 70, 80)
            points = [
                self.sectors["eindhoven"].position,
                self.sectors["veghel"].position,
                self.sectors["son"].position,
                self.sectors["grave"].position,
                self.sectors["nijmegen"].position,
                self.sectors["arnhem"].position,
            ]

            if len(points) >= 2:
                pygame.draw.lines(self._bg_surface, corridor_color, False, points, 3)

            for _sector_id, sector in self.sectors.items():
                x, y = int(sector.position[0]), int(sector.position[1])

                pygame.draw.circle(self._bg_surface, sector.color, (x, y), 30)
                pygame.draw.circle(self._bg_surface, (255, 255, 255), (x, y), 30, 2)

                name_surf = font_small.render(sector.name, True, (255, 255, 255))
                self._bg_surface.blit(name_surf, (x - name_surf.get_width() // 2, y + 35))

                status_text = sector.status.name.replace("_", " ")
                status_surf = font_small.render(status_text, True, sector.color)
                self._bg_surface.blit(status_surf, (x - status_surf.get_width() // 2, y + 50))

            surface.blit(self._bg_surface, (0, 0))

        except (pygame.error, ValueError, TypeError) as e:
            logging.debug("Strategic map rendering failed: %s", e)

    def get_sector(self, sector_id: str) -> Sector | None:
        """Get sector by ID."""
        return self.sectors.get(sector_id)

    @property
    def sector_count(self) -> int:
        """Get the sector count."""
        return len(self.sectors)

    @property
    def allied_sectors(self) -> list[str]:
        """Get the allied sectors."""
        return [
            sid
            for sid, sector in self.sectors.items()
            if sector.status == SectorStatus.ALLIED_CONTROL
        ]

    @property
    def axis_sectors(self) -> list[str]:
        """Get the axis sectors."""
        return [
            sid
            for sid, sector in self.sectors.items()
            if sector.status == SectorStatus.AXIS_CONTROL
        ]
