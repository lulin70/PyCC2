"""Campaign data type definitions for the four-layer CC2 campaign system.

This module contains all frozen dataclass definitions that define the
campaign hierarchy: GrandCampaign → SectorCampaign → Operation → Battle,
plus runtime state dataclasses.

See campaign_data.py for the Market Garden factory function.
See campaign_four_layer.py for FourLayerCampaignManager engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pycc2.domain.entities.unit import Faction

# ========================================================================
# Layer 1 — Battle: Single engagement on one map
# ========================================================================


@dataclass(frozen=True)
class VictoryLocationDef:
    """A victory location on a battle map with point value and type."""

    vl_id: str
    name: str
    position: tuple[int, int]
    value: int  # 10 / 20 / 30 / 40
    vl_type: str  # 'regular', 'landing_zone', 'road', 'bridge'


@dataclass(frozen=True)
class BattleDefinition:
    """Single engagement on one map — the atomic unit of the campaign."""

    battle_id: str
    map_id: str
    name: str
    day: int  # Day 1-9
    sector: str  # 'arnhem', 'nijmegen', 'eindhoven'
    operation_id: str
    attacker: Faction
    defender: Faction
    victory_locations: list[VictoryLocationDef]
    time_of_day: str  # 'dawn', 'day', 'dusk', 'night'
    weather: str  # 'clear', 'overcast', 'rain', 'fog'
    reinforcement_turns: dict[str, list[tuple[int, str]]]  # faction -> [(turn, unit_template_id)]
    map_value: int  # 10-40 points


# ========================================================================
# Layer 2 — Operation: Series of 2-5 battles over days in one area
# ========================================================================


@dataclass(frozen=True)
class OperationDefinition:
    """Series of 2-5 battles over days in one area.

    CC2 mechanics:
      - Requisition points to buy units (max 9 infantry + 6 support)
      - Ceasefire option (1-7 hours rest) between battles
      - Retreat option (risk of capture)
      - Damaged units slowly replenish between battles
    """

    operation_id: str
    name: str
    sector: str
    battles: list[BattleDefinition]
    requisition_points_allies: int
    requisition_points_axis: int
    max_infantry: int = 9
    max_support: int = 6


# ========================================================================
# Layer 3 — SectorCampaign: One of three sectors
# ========================================================================


@dataclass(frozen=True)
class SectorCampaignDefinition:
    """One of three sectors (Arnhem / Nijmegen / Eindhoven).

    CC2 mechanics:
      - Multiple operations running in parallel
      - Arnhem: scored by British/Polish holding
      - Nijmegen/Eindhoven: scored by XXX Corps advance speed
      - Germans capturing LZ blocks Allied supply drops
      - Germans can attack highway after XXX Corps passes
    """

    sector_id: str  # 'arnhem', 'nijmegen', 'eindhoven'
    name: str
    operations: list[OperationDefinition]
    scoring_type: str  # 'holding', 'advance_speed'
    historical_days: tuple[int, int]  # (start_day, end_day)


# ========================================================================
# Layer 4 — GrandCampaign: Full Market Garden
# ========================================================================


@dataclass(frozen=True)
class GrandCampaignDefinition:
    """Full Market Garden, Sept 17-26, 1944.

    CC2 mechanics:
      - Three sectors running simultaneously
      - Daily supply allocation (choose priority sector)
      - German always has land supply
      - Allied: only XXX Corps areas have land supply;
        others need airdrops (blocked if LZ lost)
      - Victory: XXX Corps speed to Arnhem + 1st Airborne holding
    """

    campaign_id: str = "market_garden"
    name: str = "Operation Market Garden"
    start_date: str = "1944-09-17"
    end_date: str = "1944-09-26"
    sectors: list[SectorCampaignDefinition] = field(default_factory=list)
    daily_supply_points: int = 100


# ========================================================================
# Runtime State Classes
# ========================================================================


@dataclass
class BattleState:
    """Runtime state of a single battle."""

    battle_id: str
    status: str  # 'pending', 'active', 'allied_victory', 'axis_victory', 'draw'
    vl_control: dict[str, Faction]  # vl_id -> controlling faction
    casualties: dict[str, dict[str, int]]  # faction_name -> {kia, wounded}
    turns_elapsed: int = 0


@dataclass
class OperationState:
    """Runtime state of an operation (series of battles)."""

    operation_id: str
    status: str  # 'pending', 'active', 'complete'
    current_battle_index: int = 0
    battle_results: list[BattleState] = field(default_factory=list)
    total_victory_points: dict[str, int] = field(default_factory=dict)  # faction_name -> points
    requisition_remaining: dict[str, int] = field(default_factory=dict)
    damaged_units: list[Any] = field(default_factory=list)


@dataclass
class SectorState:
    """Runtime state of a sector campaign."""

    sector_id: str
    status: str  # 'pending', 'active', 'complete'
    operations: list[OperationState] = field(default_factory=list)
    supply_available: bool = True
    lz_controlled: bool = True  # For Arnhem sector


@dataclass
class GrandCampaignState:
    """Runtime state of the full grand campaign."""

    current_day: int = 1
    sectors: dict[str, SectorState] = field(default_factory=dict)
    supply_priority_sector: str = "arnhem"
    xxx_corps_position: str = "start"  # How far XXX Corps has advanced
    victory_determined: bool = False


@dataclass
class UnitCarryoverState:
    """Persistent state of a unit that carries over between battles."""

    unit_id: str
    faction: str
    is_alive: bool = True
    current_hp: float = 100.0
    max_hp: float = 100.0
    morale: float = 100.0
    experience: int = 0
    ammo_remaining: int = 0
    max_ammo: int = 0
    kills: int = 0
    status: str = "active"  # 'active', 'wounded', 'kia', 'mia'

    # Squad-level carryover
    squad_members_alive: int = 0
    squad_members_wounded: int = 0
    squad_members_dead: int = 0
    squad_total_size: int = 0
