"""Supply procurement screen rendering mixin — extracted from CampaignUIRenderer.

Extracted during Phase 2 P0-1 (2026-07-04). See ``campaign_ui_rendering.py``
facade for the public API entry point.

Provides:
  - ``_render_supply_procurement``: delegates to ``SupplyProcurementUI``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Surface

if TYPE_CHECKING:
    from .campaign_ui import CampaignUI


class CampaignUISupplyMixin:
    """Mixin: supply procurement screen rendering for CampaignUIRenderer.

    Relies on the facade's ``__init__`` to set ``self._ui``.
    """

    # -- Facade attribute set by CampaignUIRenderer.__init__ (typing only) --
    _ui: CampaignUI

    def _render_supply_procurement(self, surface: Surface) -> None:
        """Render the supply procurement phase by delegating to SupplyProcurementUI.

        The :class:`SupplyProcurementUI` owns its full rendering pipeline
        (header, supply pool bar, per-sector rows, allocate buttons).
        We seed it with the campaign UI's normal font so the typography
        stays consistent with the rest of the campaign screens.

        """
        ui = self._ui
        supply_ui = ui._supply_procurement_ui
        # The supply UI is a no-op when its manager is unbound; this guard
        # keeps the screen from going blank if the state is entered without
        # a prior show_supply_procurement() call.
        if supply_ui.manager is None:
            surface.fill(ui.BG_COLOR)
            assert ui._font_normal is not None
            msg = ui._font_normal.render("Supply procurement unavailable", True, ui.TEXT_COLOR)
            surface.blit(msg, (ui.MARGIN, ui.MARGIN))
            return

        supply_ui.render(surface, ui._font_normal)
