"""
Campaign State — persistent state across multiple battles.
This is the heart of the CC2 campaign system: units carry over between battles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from pycc2.domain.components.veterancy_component import VeterancyComponent, VeteranRank
from pycc2.domain.systems.battle_result import BattleResult


class OperationPhase(Enum):
    PLANNING = auto()
    DAY_1_SEPT17 = auto()
    DAY_2_SEPT18 = auto()
    DAY_3_SEPT19 = auto()
    DAY_4_SEPT20 = auto()
    DAY_5_SEPT21 = auto()
    DAY_6_SEPT22 = auto()


BRIDGE_NAMES = {
    "son": "Son Bridge",
    "veghel": "Veghel Bridge",
    "grave": "Grave Bridge",
    "nijmegen": "Nijmegen Bridge",
    "arnhem": "Arnhem (The Bridge Too Far)",
}

MAX_ALLIED_UNITS = 24
MAX_AXIS_UNITS = 30


@dataclass
class PersistentUnit:
    unit_id: str
    name: str
    unit_type: str
    is_alive: bool = True
    current_hp: int = 100
    max_hp: int = 100
    current_ammo: int = 100
    max_ammo: int = 100
    veterancy: VeterancyComponent = field(default_factory=VeterancyComponent)
    battles_participated: int = 0

    @property
    def hp_ratio(self) -> float:
        if self.max_hp <= 0:
            return 0.0
        return self.current_hp / self.max_hp

    @property
    def ammo_ratio(self) -> float:
        if self.max_ammo <= 0:
            return 1.0
        return self.current_ammo / self.max_ammo

    def apply_battle_result(self, record: dict) -> None:
        self.battles_participated += 1
        self.current_hp = record.get("hp_end", self.current_hp)
        self.current_ammo = max(0, self.current_ammo - record.get("ammo_used", 0))
        self.is_alive = record.get("survived", self.is_alive)

        if record.get("xp_gained", 0) > 0:
            self.veterancy.add_xp(record["xp_gained"])
        if record.get("kills", 0) > 0:
            self.veterancy.kills += record["kills"]

    def replenish(self, hp_pct: float = 0.3, ammo_pct: float = 0.5) -> None:
        if self.is_alive:
            hp_gain = int(self.max_hp * hp_pct)
            self.current_hp = min(self.max_hp, self.current_hp + hp_gain)
            ammo_gain = int(self.max_ammo * ammo_pct)
            self.current_ammo = min(self.max_ammo, self.current_ammo + ammo_gain)

    def to_dict(self) -> dict:
        return {
            "unit_id": self.unit_id,
            "name": self.name,
            "unit_type": self.unit_type,
            "is_alive": self.is_alive,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "current_ammo": self.current_ammo,
            "max_ammo": self.max_ammo,
            "veterancy": self.veterancy.to_dict(),
            "battles_participated": self.battles_participated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PersistentUnit:
        vet_data = data.get("veterancy", {})
        return cls(
            unit_id=data["unit_id"],
            name=data["name"],
            unit_type=data["unit_type"],
            is_alive=data.get("is_alive", True),
            current_hp=data.get("current_hp", data.get("max_hp", 100)),
            max_hp=data.get("max_hp", 100),
            current_ammo=data.get("current_ammo", data.get("max_ammo", 100)),
            max_ammo=data.get("max_ammo", 100),
            veterancy=VeterancyComponent.from_dict(vet_data) if vet_data else VeterancyComponent(),
            battles_participated=data.get("battles_participated", 0),
        )


@dataclass
class CampaignState:
    campaign_id: str = "market_garden"
    name: str = "Operation Market Garden"

    current_day: OperationPhase = OperationPhase.DAY_1_SEPT17
    current_battle_number: int = 0
    total_battles_played: int = 0

    bridges_captured: dict[str, bool] = field(default_factory=lambda: {
        k: False for k in BRIDGE_NAMES
    })
    total_vp: int = 0

    allied_units: list[PersistentUnit] = field(default_factory=list)
    axis_units: list[PersistentUnit] = field(default_factory=list)

    battle_history: list[BattleResult] = field(default_factory=list)

    available_reinforcements: int = 3

    enemy_strength_modifier: float = 1.0
    morale_modifier: float = 1.0

    @property
    def alive_allied_count(self) -> int:
        return sum(1 for u in self.allied_units if u.is_alive)

    @property
    def alive_axis_count(self) -> int:
        return sum(1 for u in self.axis_units if u.is_alive)

    @property
    def bridges_held(self) -> int:
        return sum(1 for v in self.bridges_captured.values() if v)

    @property
    def campaign_progress_pct(self) -> float:
        total_bridges = len(self.bridges_captured)
        if total_bridges == 0:
            return 0.0
        return self.bridges_held / total_bridges

    @property
    def average_allied_veterancy(self) -> float:
        alive = [u for u in self.allied_units if u.is_alive]
        if not alive:
            return 0.0
        ranks = {VeteranRank.RECRUIT: 0, VeteranRank.REGULAR: 1,
                 VeteranRank.VETERAN: 2, VeteranRank.ELITE: 3}
        avg = sum(ranks.get(u.veterancy.rank, 0) for u in alive) / len(alive)
        return avg

    def advance_day(self) -> None:
        days = list(OperationPhase)
        current_idx = days.index(self.current_day)
        if current_idx < len(days) - 1:
            self.current_day = days[current_idx + 1]
        self.enemy_strength_modifier = 1.0 + (current_idx + 1) * 0.15

    def record_battle(self, result: BattleResult) -> None:
        self.battle_history.append(result)
        self.total_battles_played += 1
        self.current_battle_number += 1
        self.total_vp += result.victory_points

        recent = self.battle_history[-3:] if len(self.battle_history) >= 3 else self.battle_history
        wins = sum(1 for b in recent if b.is_victory)
        losses = len(recent) - wins
        self.morale_modifier = 1.0 + (wins - losses) * 0.1
        self.morale_modifier = max(0.7, min(1.3, self.morale_modifier))

        for record in result.unit_records:
            self._apply_unit_record(record)

    def _apply_unit_record(self, record) -> None:
        target_pool = (
            self.allied_units if record.faction == "allies"
            else self.axis_units
        )
        for pu in target_pool:
            if pu.unit_id == record.unit_id:
                pu.apply_battle_result({
                    "hp_end": record.hp_end,
                    "survived": record.survived,
                    "xp_gained": record.xp_gained,
                    "kills": record.kills,
                    "ammo_used": record.shots_fired // 3,
                })
                break

    def replenish_all_units(self) -> None:
        for unit in self.allied_units:
            if unit.is_alive:
                unit.replenish(hp_pct=0.25, ammo_pct=0.4)
        for unit in self.axis_units:
            if unit.is_alive:
                unit.replenish(hp_pct=0.2, ammo_pct=0.3)

    def capture_bridge(self, bridge_key: str) -> bool:
        if bridge_key in self.bridges_captured:
            self.bridges_captured[bridge_key] = True
            return True
        return False

    @property
    def is_campaign_over(self) -> bool:
        if all(self.bridges_captured.values()):
            return True
        if self.alive_allied_count == 0:
            return True
        if self.current_day == OperationPhase.DAY_6_SEPT22 and self.bridges_held == 0:
            return True
        return False

    @property
    def campaign_outcome(self) -> str:
        if not self.is_campaign_over:
            return "ongoing"
        if all(self.bridges_captured.values()):
            return "decisive_victory"
        if self.bridges_held >= 3:
            return "tactical_victory"
        if self.alive_allied_count == 0:
            return "defeat"
        return "marginal_result"

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "current_day": self.current_day.name,
            "current_battle_number": self.current_battle_number,
            "total_battles_played": self.total_battles_played,
            "bridges_captured": self.bridges_captured,
            "total_vp": self.total_vp,
            "enemy_strength_modifier": self.enemy_strength_modifier,
            "morale_modifier": self.morale_modifier,
            "available_reinforcements": self.available_reinforcements,
            "allied_units": [u.to_dict() for u in self.allied_units],
            "axis_units": [u.to_dict() for u in self.axis_units],
            "battle_history": [b.to_dict() for b in self.battle_history],
        }

    @classmethod
    def from_dict(cls, data: dict) -> CampaignState:
        allied = [PersistentUnit.from_dict(u) for u in data.get("allied_units", [])]
        axis = [PersistentUnit.from_dict(u) for u in data.get("axis_units", [])]
        history = [BattleResult.from_dict(b) for b in data.get("battle_history", [])]

        bridges = data.get("bridges_captured", {})
        day_name = data.get("current_day", "DAY_1_SEPT17")

        try:
            day_phase = OperationPhase[day_name]
        except KeyError:
            day_phase = OperationPhase.DAY_1_SEPT17

        return cls(
            campaign_id=data.get("campaign_id", "market_garden"),
            current_day=day_phase,
            current_battle_number=data.get("current_battle_number", 0),
            total_battles_played=data.get("total_battles_played", 0),
            bridges_captured=bridges,
            total_vp=data.get("total_vp", 0),
            enemy_strength_modifier=data.get("enemy_strength_modifier", 1.0),
            morale_modifier=data.get("morale_modifier", 1.0),
            available_reinforcements=data.get("available_reinforcements", 3),
            allied_units=allied,
            axis_units=axis,
            battle_history=history,
        )

    @classmethod
    def create_default(cls) -> CampaignState:
        state = cls()
        starting_allies = [
            ("A-101", "Alpha Co", "INFANTRY_SQUAD"),
            ("A-102", "Bravo Co", "INFANTRY_SQUAD"),
            ("A-103", "Cmd Group", "COMMANDER"),
        ]
        for uid, uname, utype in starting_allies:
            state.allied_units.append(PersistentUnit(
                unit_id=uid, name=uname, unit_type=utype,
            ))
        return state
