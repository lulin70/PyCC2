"""Tests for the supply procurement system (P4-4).

Covers:
  - :meth:`SupplyLineManager.procure_supply` — allocating supply points
    boosts sector supply levels and respects the daily pool.
  - :class:`SupplyProcurementUI` initial state after binding a manager.
  - :class:`SupplyProcurementUI` allocation interaction — clicking the
    ``[+]`` / ``[-]`` buttons updates the displayed numbers and mutates
    the real :class:`SupplyLineManager`.

All tests use real components (no mocks) per the P4-4 task requirements.
Pygame runs headless via the ``SDL_VIDEODRIVER=dummy`` driver configured
in ``tests/conftest.py``.
"""

from __future__ import annotations

import pytest

from pycc2.domain.systems.supply_line import (
    SupplyLevel,
    SupplyLineManager,
    SupplyType,
)
from pycc2.presentation.ui.supply_procurement_ui import (
    ALLOCATE_STEP,
    SupplyProcurementUI,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def supply_manager() -> SupplyLineManager:
    """Return a fresh default Market Garden SupplyLineManager (day 1)."""
    return SupplyLineManager.create_default()


@pytest.fixture()
def procurement_ui(pygame_display) -> SupplyProcurementUI:
    """Return a SupplyProcurementUI bound to a fresh manager.

    ``pygame_display`` is requested so pygame is initialised and the UI's
    ``render`` call can populate click rectangles for interaction tests.
    """
    import pygame

    manager = SupplyLineManager.create_default()
    ui = SupplyProcurementUI(width=800, height=600)
    ui.start_procurement(manager, day=1)
    # Render once to populate the [+]/[-] button rects.
    screen = pygame.display.get_surface() or pygame.display.set_mode((800, 600))
    ui.render(screen)
    return ui


# ---------------------------------------------------------------------------
# SupplyLineManager.procure_supply
# ---------------------------------------------------------------------------


class TestSupplyLineManagerProcure:
    """Verify procure_supply boosts supply and respects the pool."""

    def test_supply_line_manager_procure(self, supply_manager: SupplyLineManager) -> None:
        """Allocating supply points to a sector raises its supply level.

        This is the headline P4-4 test: after procurement, the sector's
        ammunition replenishment rate must be strictly higher than the
        base airdrop rate (0.6), and the available pool must shrink by
        the allocated amount.

        """
        manager = supply_manager
        sector = "arnhem"
        base_ammo = manager.sector_supply[sector].ammo_replenishment_rate
        assert base_ammo == pytest.approx(0.6), "Day-1 Arnhem base ammo should be 0.6"

        allocated = 20
        ok = manager.procure_supply(sector, allocated)
        assert ok is True, "procure_supply should succeed for a known sector"

        new_ammo = manager.sector_supply[sector].ammo_replenishment_rate
        assert new_ammo > base_ammo, "Ammo rate must improve after procurement"
        # 20 points * 0.006 = 0.12 bonus → 0.72
        assert new_ammo == pytest.approx(0.72)
        assert manager.available_supply_points == 100 - allocated
        assert manager.procured_points[sector] == allocated

    def test_procure_returns_false_for_unknown_sector(
        self, supply_manager: SupplyLineManager
    ) -> None:
        assert supply_manager.procure_supply("unknown_sector", 10) is False
        assert supply_manager.available_supply_points == 100

    def test_procure_respects_daily_pool(self, supply_manager: SupplyLineManager) -> None:
        """Allocating more than the available pool must fail."""
        manager = supply_manager
        # Spend 90 of 100 points.
        assert manager.procure_supply("arnhem", 90) is True
        assert manager.available_supply_points == 10
        # 20 more would exceed the remaining 10.
        assert manager.procure_supply("nijmegen", 20) is False
        # 10 exactly should succeed.
        assert manager.procure_supply("nijmegen", 10) is True
        assert manager.available_supply_points == 0

    def test_procure_revokes_points_with_negative_allocation(
        self, supply_manager: SupplyLineManager
    ) -> None:
        manager = supply_manager
        assert manager.procure_supply("arnhem", 30) is True
        assert manager.available_supply_points == 70
        assert manager.procured_points["arnhem"] == 30

        # Revoke 10.
        assert manager.procure_supply("arnhem", -10) is True
        assert manager.procured_points["arnhem"] == 20
        assert manager.available_supply_points == 80

    def test_procure_cannot_revoke_below_zero(self, supply_manager: SupplyLineManager) -> None:
        manager = supply_manager
        assert manager.procure_supply("arnhem", 10) is True
        # Try to revoke 20 when only 10 allocated.
        assert manager.procure_supply("arnhem", -20) is False
        assert manager.procured_points["arnhem"] == 10

    def test_procure_promotes_supply_level_to_full(self, supply_manager: SupplyLineManager) -> None:
        """Allocating >=60 points promotes the sector to FULL supply level."""
        manager = supply_manager
        assert manager.sector_supply["arnhem"].supply_level == SupplyLevel.REDUCED
        assert manager.procure_supply("arnhem", 60) is True
        assert manager.sector_supply["arnhem"].supply_level == SupplyLevel.FULL

    def test_procure_promotes_none_to_minimal(self) -> None:
        """A BLOCKED sector reaches MINIMAL with >=10 procured points."""
        manager = SupplyLineManager.create_default()
        # Force arnhem into a no-supply state by losing the LZ.
        manager.sector_supply["arnhem"].lz_controlled = False
        manager.sector_supply["arnhem"].calculate_supply()
        assert manager.sector_supply["arnhem"].supply_level == SupplyLevel.NONE

        assert manager.procure_supply("arnhem", 10) is True
        assert manager.sector_supply["arnhem"].supply_level == SupplyLevel.MINIMAL

    def test_procure_zero_allocation_is_noop(self, supply_manager: SupplyLineManager) -> None:
        manager = supply_manager
        base_ammo = manager.sector_supply["arnhem"].ammo_replenishment_rate
        assert manager.procure_supply("arnhem", 0) is True
        assert manager.sector_supply["arnhem"].ammo_replenishment_rate == base_ammo
        assert manager.available_supply_points == 100

    def test_advance_day_resets_procured_points(self, supply_manager: SupplyLineManager) -> None:
        manager = supply_manager
        assert manager.procure_supply("arnhem", 40) is True
        assert manager.procured_points == {"arnhem": 40}
        manager.advance_day()
        assert manager.procured_points == {}
        assert manager._total_procured == 0
        assert manager.available_supply_points == 100


# ---------------------------------------------------------------------------
# SupplyProcurementUI — initial state
# ---------------------------------------------------------------------------


class TestSupplyProcurementUIInitialState:
    """Verify the UI's initial display after start_procurement."""

    def test_supply_procurement_ui_initial_state(self, procurement_ui: SupplyProcurementUI) -> None:
        """The UI shows the full pool and zero allocations on entry.

        Headline P4-4 UI test: after binding a fresh manager the UI must
        report all 100 supply points available, every sector at zero
        allocation, the correct day, and an un-confirmed state.

        """
        ui = procurement_ui
        assert ui.state.day == 1
        assert ui.is_confirmed is False
        assert ui.get_available_points() == 100
        # All three Market Garden sectors present.
        assert set(ui.state.allocations.keys()) == {"arnhem", "nijmegen", "eindhoven"}
        # All allocations start at zero.
        assert all(v == 0 for v in ui.state.allocations.values())

    def test_initial_state_shows_three_sector_rows(
        self, procurement_ui: SupplyProcurementUI
    ) -> None:
        """The rendered UI exposes one [+] button per sector."""
        ui = procurement_ui
        assert set(ui._inc_button_rects.keys()) == {"arnhem", "nijmegen", "eindhoven"}
        assert set(ui._dec_button_rects.keys()) == {"arnhem", "nijmegen", "eindhoven"}

    def test_initial_state_confirm_button_present(
        self, procurement_ui: SupplyProcurementUI
    ) -> None:
        ui = procurement_ui
        assert ui._confirm_button_rect is not None
        assert ui._back_button_rect is not None

    def test_initial_state_manager_bound(self, procurement_ui: SupplyProcurementUI) -> None:
        """The UI holds a live reference to the real SupplyLineManager."""
        ui = procurement_ui
        assert ui.manager is not None
        assert isinstance(ui.manager, SupplyLineManager)
        assert ui.manager.current_day == 1

    def test_initial_sector_supply_levels(self, procurement_ui: SupplyProcurementUI) -> None:
        """Day-1 sectors all show AIRDROP / REDUCED supply (historical)."""
        ui = procurement_ui
        manager = ui.manager
        assert manager is not None
        for sector_id in ("arnhem", "nijmegen", "eindhoven"):
            supply = manager.sector_supply[sector_id]
            assert supply.supply_type == SupplyType.AIRDROP
            assert supply.supply_level == SupplyLevel.REDUCED


# ---------------------------------------------------------------------------
# SupplyProcurementUI — allocation interaction
# ---------------------------------------------------------------------------


class TestSupplyProcurementUIAllocate:
    """Verify clicking [+] / [-] updates numbers and the bound manager."""

    def test_supply_procurement_ui_allocate(self, procurement_ui: SupplyProcurementUI) -> None:
        """Clicking [+] on a sector increases its allocation by ALLOCATE_STEP.

        Headline P4-4 UI test: the click must both (a) update the UI's
        displayed allocation and (b) mutate the real SupplyLineManager's
        ``procured_points`` so the domain state stays authoritative.

        """
        ui = procurement_ui
        sector = "arnhem"
        before = ui.get_allocation(sector)
        assert before == 0

        inc_rect = ui._inc_button_rects[sector]
        action = ui.handle_click(inc_rect.centerx, inc_rect.centery)

        assert action == f"allocate:{sector},{ALLOCATE_STEP}"
        assert ui.get_allocation(sector) == ALLOCATE_STEP
        assert ui.get_available_points() == 100 - ALLOCATE_STEP
        # Domain state updated too.
        manager = ui.manager
        assert manager is not None
        assert manager.procured_points[sector] == ALLOCATE_STEP
        # Supply effect applied.
        assert manager.sector_supply[sector].ammo_replenishment_rate > 0.6

    def test_allocate_multiple_clicks_accumulate(self, procurement_ui: SupplyProcurementUI) -> None:
        ui = procurement_ui
        sector = "nijmegen"
        inc_rect = ui._inc_button_rects[sector]

        for _ in range(3):
            ui.handle_click(inc_rect.centerx, inc_rect.centery)

        assert ui.get_allocation(sector) == 30
        assert ui.get_available_points() == 70

    def test_deallocate_reduces_numbers(self, procurement_ui: SupplyProcurementUI) -> None:
        ui = procurement_ui
        sector = "eindhoven"

        # Allocate 20 first.
        inc_rect = ui._inc_button_rects[sector]
        ui.handle_click(inc_rect.centerx, inc_rect.centery)
        ui.handle_click(inc_rect.centerx, inc_rect.centery)
        assert ui.get_allocation(sector) == 20

        # Revoke 10.
        dec_rect = ui._dec_button_rects[sector]
        action = ui.handle_click(dec_rect.centerx, dec_rect.centery)
        assert action == f"allocate:{sector},{-ALLOCATE_STEP}"
        assert ui.get_allocation(sector) == 10
        assert ui.get_available_points() == 90

    def test_deallocate_below_zero_blocked(self, procurement_ui: SupplyProcurementUI) -> None:
        ui = procurement_ui
        sector = "arnhem"
        dec_rect = ui._dec_button_rects[sector]
        # No points allocated yet — clicking [-] should do nothing.
        action = ui.handle_click(dec_rect.centerx, dec_rect.centery)
        assert action is None
        assert ui.get_allocation(sector) == 0
        assert ui.get_available_points() == 100

    def test_confirm_freezes_allocation(self, procurement_ui: SupplyProcurementUI) -> None:
        ui = procurement_ui
        sector = "arnhem"
        inc_rect = ui._inc_button_rects[sector]
        ui.handle_click(inc_rect.centerx, inc_rect.centery)
        assert ui.get_allocation(sector) == ALLOCATE_STEP

        # Confirm.
        confirm_rect = ui._confirm_button_rect
        assert confirm_rect is not None
        action = ui.handle_click(confirm_rect.centerx, confirm_rect.centery)
        assert action == "confirm"
        assert ui.is_confirmed is True

        # Further [+] clicks are refused.
        action = ui.handle_click(inc_rect.centerx, inc_rect.centery)
        assert action is None
        assert ui.get_allocation(sector) == ALLOCATE_STEP

    def test_confirm_returns_final_allocation(self, procurement_ui: SupplyProcurementUI) -> None:
        ui = procurement_ui
        ui.handle_click(
            ui._inc_button_rects["arnhem"].centerx,
            ui._inc_button_rects["arnhem"].centery,
        )
        ui.handle_click(
            ui._inc_button_rects["nijmegen"].centerx,
            ui._inc_button_rects["nijmegen"].centery,
        )
        final = ui.confirm()
        assert final["arnhem"] == ALLOCATE_STEP
        assert final["nijmegen"] == ALLOCATE_STEP
        assert final["eindhoven"] == 0

    def test_allocate_unknown_position_returns_none(
        self, procurement_ui: SupplyProcurementUI
    ) -> None:
        """A click outside any button does nothing."""
        ui = procurement_ui
        # Click in the top-left corner (header area).
        assert ui.handle_click(5, 5) is None

    def test_allocate_step_is_ten(self) -> None:
        """The procurement step constant is 10 points per click."""
        assert ALLOCATE_STEP == 10


# ---------------------------------------------------------------------------
# CampaignUI integration (state machine)
# ---------------------------------------------------------------------------


class TestCampaignUISupplyProcurementIntegration:
    """Verify CampaignUI wires the supply procurement state correctly."""

    def test_campaign_ui_enters_supply_procurement_state(self, pygame_display) -> None:
        from pycc2.presentation.ui.campaign_ui import CampaignUI

        ui = CampaignUI()
        ui.initialize()
        manager = SupplyLineManager.create_default()
        ui.show_supply_procurement(manager, day=2, return_state="operation_select")

        assert ui.state == "supply_procurement"
        assert ui.supply_procurement_ui.manager is manager
        assert ui.supply_procurement_ui.state.day == 2

    def test_campaign_ui_confirm_returns_to_return_state(self, pygame_display) -> None:
        from pycc2.presentation.ui.campaign_ui import CampaignUI

        ui = CampaignUI()
        ui.initialize()
        ui.show()
        manager = SupplyLineManager.create_default()
        ui.show_supply_procurement(manager, day=1, return_state="operation_select")

        # Render so the supply UI's confirm rect is populated.
        import pygame

        screen = pygame.display.get_surface() or pygame.display.set_mode((800, 600))
        ui.render(screen)

        confirm_rect = ui.supply_procurement_ui._confirm_button_rect
        assert confirm_rect is not None
        action = ui.handle_click((confirm_rect.centerx, confirm_rect.centery))
        assert action is not None
        assert action.startswith("supply_confirmed")
        assert ui.state == "operation_select"

    def test_campaign_ui_back_returns_to_return_state(self, pygame_display) -> None:
        from pycc2.presentation.ui.campaign_ui import CampaignUI

        ui = CampaignUI()
        ui.initialize()
        ui.show()
        manager = SupplyLineManager.create_default()
        ui.show_supply_procurement(manager, day=1, return_state="briefing")

        import pygame

        screen = pygame.display.get_surface() or pygame.display.set_mode((800, 600))
        ui.render(screen)

        back_rect = ui.supply_procurement_ui._back_button_rect
        assert back_rect is not None
        action = ui.handle_click((back_rect.centerx, back_rect.centery))
        assert action == "back"
        assert ui.state == "briefing"

    def test_campaign_ui_allocate_click_pass_through(self, pygame_display) -> None:
        """Allocation clicks in CampaignUI reach the embedded SupplyProcurementUI."""
        from pycc2.presentation.ui.campaign_ui import CampaignUI

        ui = CampaignUI()
        ui.initialize()
        ui.show()
        manager = SupplyLineManager.create_default()
        ui.show_supply_procurement(manager, day=1)

        import pygame

        screen = pygame.display.get_surface() or pygame.display.set_mode((800, 600))
        ui.render(screen)

        inc_rect = ui.supply_procurement_ui._inc_button_rects["arnhem"]
        action = ui.handle_click((inc_rect.centerx, inc_rect.centery))
        assert action == f"allocate:arnhem,{ALLOCATE_STEP}"
        assert manager.procured_points["arnhem"] == ALLOCATE_STEP


# ---------------------------------------------------------------------------
# FourLayerCampaignManager delegation
# ---------------------------------------------------------------------------


class TestFourLayerManagerSupplyDelegation:
    """Verify FourLayerCampaignManager delegates _get_supply_type to the manager."""

    def test_german_supply_is_axis_land(self) -> None:
        from pycc2.domain.systems.campaign_four_layer import FourLayerCampaignManager

        mgr = FourLayerCampaignManager()
        assert mgr._get_supply_type("german", "arnhem") == "axis_land"
        assert mgr._get_supply_type("axis", "nijmegen") == "axis_land"

    def test_allies_eindhoven_land_after_day2(self) -> None:
        from pycc2.domain.systems.campaign_four_layer import FourLayerCampaignManager

        mgr = FourLayerCampaignManager()
        # Day 1: airdrop.
        assert mgr._get_supply_type("allies", "eindhoven") == "allies_airdrop"
        # Advance to day 2.
        mgr.campaign_state.current_day = 2
        assert mgr._get_supply_type("allies", "eindhoven") == "allies_land"

    def test_allies_arnhem_airdrop_with_lz(self) -> None:
        from pycc2.domain.systems.campaign_four_layer import FourLayerCampaignManager

        mgr = FourLayerCampaignManager()
        assert mgr._get_supply_type("allies", "arnhem") == "allies_airdrop"

    def test_allies_arnhem_no_supply_when_lz_lost(self) -> None:
        from pycc2.domain.systems.campaign_four_layer import (
            FourLayerCampaignManager,
            SectorState,
        )

        mgr = FourLayerCampaignManager()
        # Simulate losing the Arnhem LZ.
        mgr.campaign_state.sectors["arnhem"] = SectorState(
            sector_id="arnhem", status="active", lz_controlled=False
        )
        assert mgr._get_supply_type("allies", "arnhem") == "allies_no_supply"

    def test_supply_manager_property_exposed(self) -> None:
        from pycc2.domain.systems.campaign_four_layer import FourLayerCampaignManager

        mgr = FourLayerCampaignManager()
        assert isinstance(mgr.supply_manager, SupplyLineManager)
        assert "arnhem" in mgr.supply_manager.sector_supply
