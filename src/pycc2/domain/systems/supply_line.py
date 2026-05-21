"""
Supply Line System for PyCC2 Grand Campaign.
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
    LAND = auto()      # Via road/rail (XXX Corps or German)
    AIRDROP = auto()   # Via parachute/glider (requires LZ control)
    BLOCKED = auto()   # No supply possible


class SupplyLevel(Enum):
    FULL = auto()      # 100% - normal operations
    REDUCED = auto()   # 50% - limited ammo/reinforcements
    MINIMAL = auto()   # 25% - critical shortage
    NONE = auto()      # 0% - no supply at all


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
    ammo_replenishment_rate: float = 0.0   # 0.0-1.0
    reinforcement_rate: float = 0.0        # 0.0-1.0
    morale_recovery_rate: float = 0.0      # 0.0-1.0

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
    START = auto()           # Day 1 start
    VEGHEL = auto()          # Day 2
    SON = auto()             # Day 3
    GRAVE = auto()           # Day 4
    NIJMEGEN = auto()        # Day 5-6
    ELST = auto()            # Day 7-8
    ARNHEM_SOUTH = auto()    # Day 9+ (if they make it)


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
    priority_sector: str = 'arnhem'

    def advance_day(self) -> None:
        """Advance to next day, update XXX Corps position and supply."""
        self.current_day += 1

        # Update XXX Corps position
        if self.current_day in XXX_CORPS_TIMELINE:
            self.xxx_corps_position = XXX_CORPS_TIMELINE[self.current_day]

        # Update supply for each sector
        self._update_sector_supply()

    def _update_sector_supply(self) -> None:
        """Recalculate supply for all sectors."""
        for sector_id, supply in self.sector_supply.items():
            supply.day = self.current_day

            # German always has land supply
            # (handled separately - this is Allied supply)

            # Check XXX Corps connection
            if sector_id == 'eindhoven':
                supply.xxx_corps_reached = self.current_day >= 2
                supply.supply_type = SupplyType.LAND if supply.xxx_corps_reached else SupplyType.AIRDROP
            elif sector_id == 'nijmegen':
                supply.xxx_corps_reached = self.current_day >= 5
                supply.supply_type = SupplyType.LAND if supply.xxx_corps_reached else SupplyType.AIRDROP
            elif sector_id == 'arnhem':
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
    def create_default(cls) -> 'SupplyLineManager':
        """Create default Market Garden supply configuration."""
        manager = cls()
        manager.sector_supply = {
            'arnhem': SupplyState(
                sector_id='arnhem', day=1,
                supply_type=SupplyType.AIRDROP,
                lz_controlled=True, lz_name='LZ-S/DZ-X',
            ),
            'nijmegen': SupplyState(
                sector_id='nijmegen', day=1,
                supply_type=SupplyType.AIRDROP,
                lz_controlled=True, lz_name='LZ-T',
            ),
            'eindhoven': SupplyState(
                sector_id='eindhoven', day=1,
                supply_type=SupplyType.AIRDROP,
                lz_controlled=True, lz_name='LZ-W',
            ),
        }
        for supply in manager.sector_supply.values():
            supply.calculate_supply()
        return manager
