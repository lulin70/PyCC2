"""Market Garden campaign data — facade composing sector builders (P5-1 batch 1).

This module is a thin facade. Sector-specific battle/operation definitions live in:
  - arnhem_campaign_data.py (3 operations: Landing/Perimeter Defense/Evacuation)
  - nijmegen_campaign_data.py (2 operations: Waal Crossing/Bridge Defense)
  - eindhoven_campaign_data.py (2 operations: Hell's Highway/Corridor Defense)

See campaign_types.py for type definitions.
See campaign_four_layer.py for FourLayerCampaignManager engine.
"""

from __future__ import annotations

import logging

from pycc2.domain.systems.arnhem_campaign_data import build_arnhem_sector
from pycc2.domain.systems.campaign_types import GrandCampaignDefinition
from pycc2.domain.systems.eindhoven_campaign_data import build_eindhoven_sector
from pycc2.domain.systems.nijmegen_campaign_data import build_nijmegen_sector

logger = logging.getLogger(__name__)


def create_market_garden_campaign() -> GrandCampaignDefinition:
    """Build the full Market Garden campaign with all three sectors (Day 1-9).

    Delegates to per-sector builders:
      - Arnhem: Landing / Perimeter Defense / Evacuation
      - Nijmegen: Waal Crossing / Bridge Defense
      - Eindhoven: Hell's Highway / Corridor Defense
    """
    arnhem_sector = build_arnhem_sector()
    nijmegen_sector = build_nijmegen_sector()
    eindhoven_sector = build_eindhoven_sector()
    return GrandCampaignDefinition(
        campaign_id="market_garden",
        name="Operation Market Garden",
        start_date="1944-09-17",
        end_date="1944-09-26",
        sectors=[arnhem_sector, nijmegen_sector, eindhoven_sector],
        daily_supply_points=100,
    )


# Pre-built default instance
DEFAULT_MARKET_GARDEN_CAMPAIGN = create_market_garden_campaign()


# ========================================================================
# Supply / recovery constants used by FourLayerCampaignManager
# ========================================================================

# Supply line resupply rates (ammo is NOT fully resupplied)
_SUPPLY_LINE_AMMO_RESUPPLY = {
    "allies_land": 0.60,  # XXX Corps land supply: 60% ammo resupply
    "allies_airdrop": 0.40,  # Airdrop supply: 40% ammo resupply
    "allies_no_supply": 0.15,  # No supply line: 15% ammo resupply (scrounging)
    "axis_land": 0.50,  # German land supply: 50% ammo resupply
}

_HP_RECOVERY_PER_DAY = 0.20  # 20% HP recovery between days for wounded
