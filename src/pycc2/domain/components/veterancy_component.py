"""Veterancy Component — tracks unit experience across campaign battles.
Veteran units gain accuracy, morale stability, and panic resistance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class VeteranRank(Enum):
    """Experience-based rank tiers from recruit to elite."""

    RECRUIT = auto()
    REGULAR = auto()
    VETERAN = auto()
    ELITE = auto()


RANK_THRESHOLDS = {
    VeteranRank.RECRUIT: 0,
    VeteranRank.REGULAR: 100,
    VeteranRank.VETERAN: 300,
    VeteranRank.ELITE: 600,
}

RANK_BONUSES = {
    VeteranRank.RECRUIT: {"accuracy": 1.0, "morale_resist": 1.0, "panic_chance": 1.0},
    VeteranRank.REGULAR: {"accuracy": 1.08, "morale_resist": 1.1, "panic_chance": 0.92},
    VeteranRank.VETERAN: {"accuracy": 1.15, "morale_resist": 1.2, "panic_chance": 0.80},
    VeteranRank.ELITE: {"accuracy": 1.22, "morale_resist": 1.35, "panic_chance": 0.65},
}


@dataclass(slots=True)
class VeterancyComponent:
    """Tracks unit experience, kills, and derived rank-based combat bonuses."""

    xp: int = 0
    kills: int = 0
    battles_survived: int = 0
    shots_fired: int = 0
    shots_hit: int = 0
    total_damage_dealt: float = 0.0

    _rank: VeteranRank = field(init=False)

    def __post_init__(self) -> None:
        self._update_rank()

    @property
    def rank(self) -> VeteranRank:
        """Return the current veterancy rank tier."""
        return self._rank

    @property
    def rank_name(self) -> str:
        """Return the name of the current veterancy rank tier."""
        return self._rank.name

    def add_xp(self, amount: int) -> bool:
        """Add XP and return whether the rank changed."""
        old_rank = self._rank
        self.xp += amount
        self._update_rank()
        return self._rank != old_rank

    def record_kill(self, xp_reward: int = 15) -> bool:
        """Record a kill, grant XP, and return whether the rank changed."""
        self.kills += 1
        return self.add_xp(xp_reward)

    def record_battle_survived(self, xp_bonus: int = 25) -> bool:
        """Record a survived battle, grant XP, and return whether rank changed."""
        self.battles_survived += 1
        return self.add_xp(xp_bonus)

    def record_shot(self, hit: bool, damage: float = 0.0) -> None:
        """Record a fired shot, optionally marking a hit and damage dealt."""
        self.shots_fired += 1
        if hit:
            self.shots_hit += 1
            self.total_damage_dealt += damage

    @property
    def accuracy(self) -> float:
        """Return the hit accuracy ratio (shots_hit / shots_fired)."""
        if self.shots_fired == 0:
            return 0.0
        return self.shots_hit / self.shots_fired

    @property
    def accuracy_bonus(self) -> float:
        """Return the accuracy bonus multiplier granted by current rank."""
        return RANK_BONUSES[self._rank]["accuracy"]

    @property
    def morale_resistance(self) -> float:
        """Return the morale resistance multiplier granted by current rank."""
        return RANK_BONUSES[self._rank]["morale_resist"]

    @property
    def panic_probability_mod(self) -> float:
        """Return the panic probability multiplier granted by current rank."""
        return RANK_BONUSES[self._rank]["panic_chance"]

    def xp_to_next_rank(self) -> int:
        """Return XP remaining to reach the next rank (0 if maxed)."""
        ranks_ordered = list(VeteranRank)
        current_idx = ranks_ordered.index(self._rank)
        if current_idx >= len(ranks_ordered) - 1:
            return 0
        next_rank = ranks_ordered[current_idx + 1]
        return RANK_THRESHOLDS[next_rank] - self.xp

    def progress_to_next_rank(self) -> float:
        """Return 0-1 progress toward the next rank based on XP thresholds."""
        needed = self.xp_to_next_rank()
        if needed <= 0:
            return 1.0
        ranks_ordered = list(VeteranRank)
        current_idx = ranks_ordered.index(self._rank)
        if current_idx == 0:
            prev_threshold = 0
        else:
            prev_rank = ranks_ordered[current_idx - 1]
            prev_threshold = RANK_THRESHOLDS[prev_rank]
        current_progress = self.xp - prev_threshold
        total_needed = RANK_THRESHOLDS[ranks_ordered[current_idx + 1]] - prev_threshold
        return min(1.0, current_progress / total_needed) if total_needed > 0 else 1.0

    def _update_rank(self) -> None:
        new_rank = VeteranRank.RECRUIT
        for rank, threshold in sorted(RANK_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if self.xp >= threshold:
                new_rank = rank
                break
        self._rank = new_rank

    def to_dict(self) -> dict:
        """Serialize the component to a plain dict for saving."""
        return {
            "xp": self.xp,
            "kills": self.kills,
            "battles_survived": self.battles_survived,
            "shots_fired": self.shots_fired,
            "shots_hit": self.shots_hit,
            "total_damage_dealt": round(self.total_damage_dealt, 2),
            "rank": self._rank.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> VeterancyComponent:
        """Reconstruct a VeterancyComponent from a saved dict."""
        comp = cls(
            xp=data.get("xp", 0),
            kills=data.get("kills", 0),
            battles_survived=data.get("battles_survived", 0),
            shots_fired=data.get("shots_fired", 0),
            shots_hit=data.get("shots_hit", 0),
            total_damage_dealt=data.get("total_damage_dealt", 0.0),
        )
        return comp
