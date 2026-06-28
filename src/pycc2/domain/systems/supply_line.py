"""Supply Line System for PyCC2 Grand Campaign.
Models the critical supply mechanics from CC2's Market Garden campaign.

Key rules (from CC2 strategy guide):
- Germans always have land supply (road/rail connections)
- Allied XXX Corps areas have land supply once XXX Corps arrives
- Other Allied areas (airborne) depend on airdrops
- Airdrops require controlled Landing Zones (LZ)
- If Germans capture an LZ, airdrops are blocked
- Each day, player chooses priority sector for supply
- Supply affects: ammunition replenishment, reinforcement arrival, morale recovery
"""

from dataclasses import dataclass, field
from enum import Enum, auto


class SupplyType(Enum):
    """Mechanisms by which a sector can receive supplies."""

    LAND = auto()  # Via road/rail (XXX Corps or German)
    AIRDROP = auto()  # Via parachute/glider (requires LZ control)
    BLOCKED = auto()  # No supply possible


class SupplyLevel(Enum):
    """Throughput tiers governing ammo, reinforcements, and morale recovery."""

    FULL = auto()  # 100% - normal operations
    REDUCED = auto()  # 50% - limited ammo/reinforcements
    MINIMAL = auto()  # 25% - critical shortage
    NONE = auto()  # 0% - no supply at all


@dataclass
class SupplyState:
    """Supply state for one sector on one day."""

    sector_id: str
    day: int
    supply_type: SupplyType = SupplyType.BLOCKED
    supply_level: SupplyLevel = SupplyLevel.NONE

    # LZ control (for airborne sectors)
    lz_controlled: bool = True
    lz_name: str = ""

    # XXX Corps position (for land supply)
    xxx_corps_reached: bool = False

    # Supply effects
    ammo_replenishment_rate: float = 0.0  # 0.0-1.0
    reinforcement_rate: float = 0.0  # 0.0-1.0
    morale_recovery_rate: float = 0.0  # 0.0-1.0

    def calculate_supply(self) -> SupplyLevel:
        """Calculate supply level based on conditions."""
        if self.supply_type == SupplyType.LAND:
            self.supply_level = SupplyLevel.FULL
            self.ammo_replenishment_rate = 1.0
            self.reinforcement_rate = 1.0
            self.morale_recovery_rate = 0.8
        elif self.supply_type == SupplyType.AIRDROP:
            if not self.lz_controlled:
                self.supply_level = SupplyLevel.NONE
                self.ammo_replenishment_rate = 0.0
                self.reinforcement_rate = 0.0
                self.morale_recovery_rate = 0.1
            else:
                self.supply_level = SupplyLevel.REDUCED
                self.ammo_replenishment_rate = 0.6
                self.reinforcement_rate = 0.4
                self.morale_recovery_rate = 0.5
        elif self.supply_type == SupplyType.BLOCKED:
            self.supply_level = SupplyLevel.NONE
            self.ammo_replenishment_rate = 0.0
            self.reinforcement_rate = 0.0
            self.morale_recovery_rate = 0.1
        return self.supply_level


class XXXCorpsPosition(Enum):
    """XXX Corps advance positions along Hell's Highway."""

    START = auto()  # Day 1 start
    VEGHEL = auto()  # Day 2
    SON = auto()  # Day 3
    GRAVE = auto()  # Day 4
    NIJMEGEN = auto()  # Day 5-6
    ELST = auto()  # Day 7-8
    ARNHEM_SOUTH = auto()  # Day 9+ (if they make it)


# XXX Corps advance timeline (historical)
XXX_CORPS_TIMELINE = {
    1: XXXCorpsPosition.START,
    2: XXXCorpsPosition.VEGHEL,
    3: XXXCorpsPosition.SON,
    4: XXXCorpsPosition.GRAVE,
    5: XXXCorpsPosition.NIJMEGEN,
    6: XXXCorpsPosition.NIJMEGEN,
    7: XXXCorpsPosition.ELST,
    8: XXXCorpsPosition.ELST,
    9: XXXCorpsPosition.ARNHEM_SOUTH,
}


@dataclass
class SupplyLineManager:
    """Manages supply lines for the entire Grand Campaign."""

    # Daily supply points to allocate
    daily_supply_points: int = 100

    # Priority sector gets 60%, others split 40%
    priority_allocation: float = 0.6

    # Current day
    current_day: int = 1

    # Supply state per sector
    sector_supply: dict[str, SupplyState] = field(default_factory=dict)

    # XXX Corps position
    xxx_corps_position: XXXCorpsPosition = XXXCorpsPosition.START

    # Priority sector chosen by player
    priority_sector: str = "arnhem"

    # Supply points procured (allocated) per sector during the daily phase.
    # Populated by ``procure_supply``; reset to empty when a new day begins.
    procured_points: dict[str, int] = field(default_factory=dict)

    # Total points procured so far this day (cached for fast availability checks).
    _total_procured: int = 0

    def advance_day(self) -> None:
        """Advance to next day, update XXX Corps position and supply."""
        self.current_day += 1

        # Update XXX Corps position
        if self.current_day in XXX_CORPS_TIMELINE:
            self.xxx_corps_position = XXX_CORPS_TIMELINE[self.current_day]

        # Reset daily procurement — new day, fresh pool of supply points
        self.procured_points = {}
        self._total_procured = 0

        # Update supply for each sector
        self._update_sector_supply()

    # ------------------------------------------------------------------
    # Supply procurement (player-driven allocation, P4-4)
    # ------------------------------------------------------------------

    @property
    def available_supply_points(self) -> int:
        """Supply points still available for procurement today."""
        return max(0, self.daily_supply_points - self._total_procured)

    def procure_supply(self, sector_id: str, allocation: int) -> bool:
        """Allocate supply points to a sector, boosting its supply level.

        Called by the supply procurement UI (P4-4) when the player assigns
        supply points to a sector.  Each procured point increases the
        sector's ammunition, reinforcement, and morale recovery rates.

        Args:
            sector_id: Target sector (must exist in ``sector_supply``).
            allocation: Number of supply points to assign.  A negative
                value revokes points (e.g. when the player clicks the
                decrement button in the UI).

        Returns:
            True if the procurement was applied; False if the sector is
            unknown or the allocation would exceed the available pool.

        """
        if sector_id not in self.sector_supply:
            return False
        if allocation == 0:
            return True

        current = self.procured_points.get(sector_id, 0)
        new_total = current + allocation

        # Revoking points: cannot go below zero for the sector
        if new_total < 0:
            return False

        # Adding points: cannot exceed the daily pool
        if allocation > 0 and allocation > self.available_supply_points:
            return False

        self.procured_points[sector_id] = new_total
        self._total_procured += allocation

        # Apply the boost to the sector's supply effects.
        # Recalculate the base supply first, then add the procurement bonus.
        supply = self.sector_supply[sector_id]
        supply.calculate_supply()
        self._apply_procurement_boost(supply, new_total)
        return True

    def _apply_procurement_boost(self, supply: SupplyState, points: int) -> None:
        """Boost a sector's supply rates based on procured points.

        Each procured point adds a small increment to ammo, reinforcement,
        and morale recovery rates (capped at 1.0).  The boost is relative
        to the sector's base ``calculate_supply()`` output, so a sector
        with a working supply line still benefits from priority allocation.

        """
        # 0.6% per point → ~60 points yields a full +0.36 bonus
        ammo_bonus = points * 0.006
        reinforce_bonus = points * 0.004
        morale_bonus = points * 0.003

        supply.ammo_replenishment_rate = min(
            1.0, supply.ammo_replenishment_rate + ammo_bonus
        )
        supply.reinforcement_rate = min(
            1.0, supply.reinforcement_rate + reinforce_bonus
        )
        supply.morale_recovery_rate = min(
            1.0, supply.morale_recovery_rate + morale_bonus
        )

        # Promote the supply level tier if enough points are allocated.
        # This lets a BLOCKED sector reach MINIMAL, or an AIRDROP sector
        # reach FULL, when the player invests enough points.
        if points >= 60:
            supply.supply_level = SupplyLevel.FULL
        elif points >= 30:
            if supply.supply_level != SupplyLevel.FULL:
                supply.supply_level = SupplyLevel.REDUCED
        elif points >= 10:
            if supply.supply_level == SupplyLevel.NONE:
                supply.supply_level = SupplyLevel.MINIMAL

    def _update_sector_supply(self) -> None:
        """Recalculate supply for all sectors."""
        for sector_id, supply in self.sector_supply.items():
            supply.day = self.current_day

            # German always has land supply
            # (handled separately - this is Allied supply)

            # Check XXX Corps connection
            if sector_id == "eindhoven":
                supply.xxx_corps_reached = self.current_day >= 2
                supply.supply_type = (
                    SupplyType.LAND if supply.xxx_corps_reached else SupplyType.AIRDROP
                )
            elif sector_id == "nijmegen":
                supply.xxx_corps_reached = self.current_day >= 5
                supply.supply_type = (
                    SupplyType.LAND if supply.xxx_corps_reached else SupplyType.AIRDROP
                )
            elif sector_id == "arnhem":
                supply.xxx_corps_reached = self.current_day >= 9
                supply.supply_type = SupplyType.AIRDROP  # Never gets land supply historically

            supply.calculate_supply()

    def allocate_supply(self) -> dict[str, float]:
        """Allocate supply points across sectors based on priority."""
        sectors = list(self.sector_supply.keys())
        if not sectors:
            return {}

        allocation = {}
        priority_points = self.daily_supply_points * self.priority_allocation
        remaining_points = self.daily_supply_points - priority_points
        other_share = remaining_points / max(len(sectors) - 1, 1)

        for sector_id in sectors:
            if sector_id == self.priority_sector:
                allocation[sector_id] = priority_points
            else:
                allocation[sector_id] = other_share

        return allocation

    def get_german_supply(self, sector_id: str) -> SupplyState:
        """German supply is always via land routes."""
        return SupplyState(
            sector_id=sector_id,
            day=self.current_day,
            supply_type=SupplyType.LAND,
            supply_level=SupplyLevel.FULL,
            ammo_replenishment_rate=1.0,
            reinforcement_rate=0.8,  # Slightly less than full
            morale_recovery_rate=0.7,
        )

    @classmethod
    def create_default(cls) -> "SupplyLineManager":
        """Create default Market Garden supply configuration."""
        manager = cls()
        manager.sector_supply = {
            "arnhem": SupplyState(
                sector_id="arnhem",
                day=1,
                supply_type=SupplyType.AIRDROP,
                lz_controlled=True,
                lz_name="LZ-S/DZ-X",
            ),
            "nijmegen": SupplyState(
                sector_id="nijmegen",
                day=1,
                supply_type=SupplyType.AIRDROP,
                lz_controlled=True,
                lz_name="LZ-T",
            ),
            "eindhoven": SupplyState(
                sector_id="eindhoven",
                day=1,
                supply_type=SupplyType.AIRDROP,
                lz_controlled=True,
                lz_name="LZ-W",
            ),
        }
        for supply in manager.sector_supply.values():
            supply.calculate_supply()
        return manager
