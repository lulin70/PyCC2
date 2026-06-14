"""
Swiss Cheese Damage Model — probabilistic squad-level casualty system.
Instead of simple HP subtraction, each hit resolves into individual
casualty outcomes per squad member.

CC2 Original: A hit "punches holes in Swiss cheese" — some soldiers get hit, others don't.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class CasualtyStatus(Enum):
    OK = auto()
    WIA = auto()
    PINNED = auto()
    KIA = auto()


class SquadSize(Enum):
    TINY = 2
    SMALL = 4
    MEDIUM = 8
    LARGE = 12
    VEHICLE = 1


UNIT_SQUAD_SIZES = {
    "INFANTRY_SQUAD": SquadSize.MEDIUM,
    "MACHINE_GUN_SQUAD": SquadSize.SMALL,
    "AT_GUN_TEAM": SquadSize.SMALL,
    "COMMANDER": SquadSize.SMALL,
    "MORTAR_TEAM": SquadSize.TINY,
    "TANK": SquadSize.VEHICLE,
    "SNIPER_TEAM": SquadSize.TINY,
    "MEDIC_TEAM": SquadSize.SMALL,
}


@dataclass(slots=True)
class SquadMember:
    index: int
    status: CasualtyStatus = CasualtyStatus.OK
    wia_effectiveness: float = 1.0

    @property
    def is_combat_effective(self) -> bool:
        return self.status in (CasualtyStatus.OK, CasualtyStatus.WIA)

    @property
    def is_alive(self) -> bool:
        return self.status != CasualtyStatus.KIA


@dataclass
class SwissCheeseResult:
    total_hp_loss: int
    kia_count: int
    wia_count: int
    pinned_count: int
    ok_count: int
    raw_damage: float
    member_outcomes: list[CasualtyStatus] = field(default_factory=list)

    @property
    def total_casualties(self) -> int:
        return self.kia_count + self.wia_count

    @property
    def effectiveness_ratio(self) -> float:
        total = self.kia_count + self.wia_count + self.pinned_count + self.ok_count
        if total == 0:
            return 0.0
        effective = sum(
            1 for s in self.member_outcomes if s in (CasualtyStatus.OK, CasualtyStatus.WIA)
        )
        return effective / total


@dataclass
class SwissCheeseEngine:
    _KIA_BASE_PROB: float = 0.08
    _WIA_BASE_PROB: float = 0.15
    _PINNED_BASE_PROB: float = 0.20
    _KIA_DAMAGE_SCALE: float = 0.003
    _WIA_DAMAGE_SCALE: float = 0.005
    _PINNED_DAMAGE_SCALE: float = 0.008
    _COVER_REDUCTION: float = 0.5
    _MORALE_PINNED_SCALE: float = 0.008

    def resolve(
        self,
        target: Unit,
        raw_damage: float,
        is_armor_piercing: bool = False,
        cover_bonus: float = 0.0,
        target_morale: float = 100.0,
    ) -> SwissCheeseResult:
        unit_type_str = (
            target.unit_type.name if hasattr(target.unit_type, "name") else str(target.unit_type)
        )
        squad_size = UNIT_SQUAD_SIZES.get(unit_type_str, SquadSize.MEDIUM).value

        if squad_size == 1:
            return self._resolve_vehicle(target, raw_damage)

        kia_prob, wia_prob, pinned_prob = self._calculate_probabilities(
            raw_damage, cover_bonus, target_morale, is_armor_piercing
        )
        outcomes = self._resolve_members(squad_size, kia_prob, wia_prob, pinned_prob)

        return self._build_result(target, raw_damage, squad_size, outcomes)

    def _resolve_vehicle(self, target: Unit, raw_damage: float) -> SwissCheeseResult:
        hp_loss = min(int(raw_damage), target.health.hp)
        return SwissCheeseResult(
            total_hp_loss=hp_loss,
            kia_count=int(target.health.hp - hp_loss <= 0),
            wia_count=0,
            pinned_count=0,
            ok_count=0 if hp_loss >= target.health.hp else 1,
            raw_damage=raw_damage,
            member_outcomes=[
                CasualtyStatus.KIA if hp_loss >= target.health.hp else CasualtyStatus.OK
            ],
        )

    def _calculate_probabilities(
        self, raw_damage: float, cover_bonus: float, target_morale: float, is_ap: bool
    ) -> tuple[float, float, float]:
        """Calculate KIA/WIA/PINNED probabilities based on damage and conditions."""
        kia_prob = self._KIA_BASE_PROB + raw_damage * self._KIA_DAMAGE_SCALE
        wia_prob = self._WIA_BASE_PROB + raw_damage * self._WIA_DAMAGE_SCALE
        pinned_prob = self._PINNED_BASE_PROB + raw_damage * self._PINNED_DAMAGE_SCALE

        if cover_bonus > 0:
            reduction = cover_bonus * self._COVER_REDUCTION
            kia_prob = max(0.01, kia_prob - reduction)
            wia_prob = max(0.02, wia_prob - reduction)
            pinned_prob = max(0.03, pinned_prob - reduction * 0.5)

        if target_morale < 70:
            morale_penalty = (70 - target_morale) * self._MORALE_PINNED_SCALE
            pinned_prob = min(0.60, pinned_prob + morale_penalty)

        if is_ap:
            kia_prob *= 1.5
            wia_prob *= 1.3
            pinned_prob *= 0.7

        kia_prob = min(0.35, max(0.01, kia_prob))
        wia_prob = min(0.40, max(0.02, wia_prob))
        pinned_prob = min(0.55, max(0.03, pinned_prob))

        return kia_prob, wia_prob, pinned_prob

    def _resolve_members(
        self, squad_size: int, kia_prob: float, wia_prob: float, pinned_prob: float
    ) -> list[CasualtyStatus]:
        """Resolve each squad member's status using probability rolls."""
        rng = random.Random(
            hash(id(object())) + int(kia_prob * 1000 + wia_prob * 100 + pinned_prob * 10)
        )

        outcomes = []
        for _i in range(squad_size):
            roll = rng.random()
            cumulative = kia_prob
            if roll < cumulative:
                outcomes.append(CasualtyStatus.KIA)
            elif roll < cumulative + wia_prob:
                outcomes.append(CasualtyStatus.WIA)
            elif roll < cumulative + wia_prob + pinned_prob:
                outcomes.append(CasualtyStatus.PINNED)
            else:
                outcomes.append(CasualtyStatus.OK)
        return outcomes

    def _build_result(
        self, target: Unit, raw_damage: float, squad_size: int, outcomes: list[CasualtyStatus]
    ) -> SwissCheeseResult:
        """Build SwissCheeseResult from resolved member outcomes."""
        kia = sum(1 for s in outcomes if s == CasualtyStatus.KIA)
        wia = sum(1 for s in outcomes if s == CasualtyStatus.WIA)
        pinned = sum(1 for s in outcomes if s == CasualtyStatus.PINNED)
        ok = sum(1 for s in outcomes if s == CasualtyStatus.OK)

        hp_per_member = target.health.max_hp // squad_size
        hp_loss = (
            kia * hp_per_member
            + int(wia * hp_per_member * 0.5)
            + int(pinned * hp_per_member * 0.25)
        )
        hp_loss = min(hp_loss, target.health.hp)

        return SwissCheeseResult(
            total_hp_loss=hp_loss,
            kia_count=kia,
            wia_count=wia,
            pinned_count=pinned,
            ok_count=ok,
            raw_damage=raw_damage,
            member_outcomes=outcomes,
        )

    def calculate_squad_effectiveness(self, result: SwissCheeseResult) -> float:
        if not result.member_outcomes:
            return 1.0
        effective = 0
        for status in result.member_outcomes:
            if status == CasualtyStatus.OK:
                effective += 1.0
            elif status == CasualtyStatus.WIA:
                effective += 0.5
            elif status == CasualtyStatus.PINNED:
                effective += 0.25
        total = len(result.member_outcomes)
        return effective / total if total > 0 else 0.0
