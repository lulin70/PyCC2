from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.systems.ballistic import ShotResult as BallisticShotResult


@dataclass(slots=True)
class CombatResult:
    shots_fired: int = 0
    shots_hit: int = 0
    total_damage: float = 0.0
    target_eliminated: bool = False
    shot_results: list[BallisticShotResult] = field(default_factory=list)


@dataclass(slots=True)
class ShotResult:
    hit: bool = False
    damage_dealt: float = 0.0
    distance: float = 0.0
