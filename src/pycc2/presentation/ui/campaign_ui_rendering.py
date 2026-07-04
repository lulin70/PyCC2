"""Campaign UI rendering facade — composes the SRP-split rendering mixins.

This module is the public entry point for campaign screen rendering. The
original monolithic ``CampaignUIRenderer`` class (1118 lines) was split during
Phase 2 P0-1 (2026-07-04) into a facade plus four screen-specific mixins:

  - ``campaign_ui_select_mixin.CampaignUISelectMixin``
      ``_render_operation_select``, ``_render_battle_select``.
  - ``campaign_ui_briefing_mixin.CampaignUIBriefingMixin``
      ``_render_briefing``, ``_render_preview``.
  - ``campaign_ui_report_mixin.CampaignUIReportMixin``
      ``_render_report``, ``_generate_narrative_report`` (staticmethod),
      ``_render_campaign_end``.
  - ``campaign_ui_supply_mixin.CampaignUISupplyMixin``
      ``_render_supply_procurement``.

The facade ``CampaignUIRenderer`` inherits all of the above and keeps the
``__init__`` + ``render`` dispatch. Public API is 100% backward-compatible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Surface

from .campaign_ui_briefing_mixin import CampaignUIBriefingMixin
from .campaign_ui_report_mixin import CampaignUIReportMixin
from .campaign_ui_select_mixin import CampaignUISelectMixin
from .campaign_ui_supply_mixin import CampaignUISupplyMixin

if TYPE_CHECKING:
    from .campaign_ui import CampaignUI


class CampaignUIRenderer(
    CampaignUISelectMixin,
    CampaignUIBriefingMixin,
    CampaignUIReportMixin,
    CampaignUISupplyMixin,
):
    """Renders every screen state for CampaignUI.

    Composes 4 screen-specific mixins (select/briefing/report/supply) split
    out during Phase 2 P0-1 (2026-07-04). Each mixin holds the ``_render_*``
    methods for its screen group; the facade provides ``__init__`` and the
    ``render`` dispatch. Public API 100% backward-compatible.
    """

    def __init__(self, ui: CampaignUI) -> None:
        """Initialize the CampaignUIRenderer."""
        self._ui = ui

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def render(self, surface: Surface) -> None:
        """Render the campaign screen based on current state."""
        ui = self._ui
        if not ui._visible or not ui._font_title:
            return

        if ui._state == "operation_select":
            self._render_operation_select(surface)
        elif ui._state == "briefing":
            self._render_briefing(surface)
        elif ui._state == "battle_select":
            self._render_battle_select(surface)
        elif ui._state == "preview":
            self._render_preview(surface)
        elif ui._state == "report":
            self._render_report(surface)
        elif ui._state == "campaign_end":
            self._render_campaign_end(surface)
        elif ui._state == "supply_procurement":
            self._render_supply_procurement(surface)
