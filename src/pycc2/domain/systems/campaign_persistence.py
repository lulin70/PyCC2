"""Campaign Persistence - Cross-battle state inheritance for continuous campaigns."""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field, asdict
from datetime import UTC, datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BattleOutcome(Enum):
    """Possible outcomes of a battle."""
    ALLIED_VICTORY = auto()
    AXIS_VICTORY = auto()
    DRAW = auto()
    CEASEFIRE = auto()
    ALLIED_RETREAT = auto()
    AXIS_RETREAT = auto()


@dataclass(slots=True)
class UnitBattleState:
    """Persistent state of a unit across battles."""
    unit_id: str
    unit_template_id: str
    faction: str
    is_alive: bool = True
    current_hp: float = 100.0
    max_hp: float = 100.0
    morale: float = 100.0
    experience: int = 0
    ammo_remaining: dict[str, int] = field(default_factory=dict)
    kills: int = 0
    status: str = "active"  # active, wounded, dead, captured


@dataclass
class BattleResult:
    """Result of a single battle for persistence."""
    battle_id: str
    operation_id: str
    sector: str
    day: int
    outcome: BattleOutcome
    timestamp: str = ""
    duration_ticks: int = 0
    allied_units_start: int = 0
    allied_units_end: int = 0
    axis_units_start: int = 0
    axis_units_end: int = 0
    allied_casualties: int = 0
    axis_casualties: int = 0
    allied_vp_earned: int = 0
    axis_vp_earned: int = 0
    unit_states: list[UnitBattleState] = field(default_factory=list)
    reinforcements_available: dict[str, list[str]] = field(default_factory=dict)
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()


@dataclass
class CampaignProgress:
    """
    Overall campaign progress across multiple battles.

    This is what gets saved/loaded between battles.
    """
    campaign_id: str
    current_operation_id: str
    current_battle_index: int = 0
    total_battles_completed: int = 0
    battle_results: list[BattleResult] = field(default_factory=list)
    current_unit_states: list[UnitBattleState] = field(default_factory=list)
    requisition_points_allies: int = 500
    requisition_points_axis: int = 500
    total_allied_casualties: int = 0
    total_axis_casualties: int = 0
    sectors_controlled: dict[str, str] = field(default_factory=dict)
    last_updated: str = ""

    def __post_init__(self) -> None:
        if not self.last_updated:
            self.last_updated = datetime.now(UTC).isoformat()

    def add_battle_result(self, result: BattleResult) -> None:
        """Add a battle result and update aggregate stats."""
        self.battle_results.append(result)
        self.total_battles_completed += 1
        self.current_battle_index += 1
        self.total_allied_casualties += result.allied_casualties
        self.total_axis_casualties += result.axis_casualties
        self.current_unit_states = result.unit_states.copy()
        self.last_updated = datetime.now(UTC).isoformat()

    def get_surviving_units(self, faction: str) -> list[UnitBattleState]:
        """Get all surviving units for a faction."""
        return [
            u for u in self.current_unit_states
            if u.faction == faction.lower() and u.is_alive
        ]

    def get_unit_state(self, unit_id: str) -> UnitBattleState | None:
        """Get state of a specific unit."""
        for u in self.current_unit_states:
            if u.unit_id == unit_id:
                return u
        return None

    def calculate_reinforcement_bonus(self) -> dict[str, int]:
        """
        Calculate reinforcement points based on performance.

        Better performance = more requisition points for next battle.
        """
        bonus: dict[str, int] = {"allies": 0, "axis": 0}

        if not self.battle_results:
            return bonus

        last_result = self.battle_results[-1]

        if last_result.outcome == BattleOutcome.ALLIED_VICTORY:
            bonus["allies"] += 100
            bonus["axis"] += 25
        elif last_result.outcome == BattleOutcome.AXIS_VICTORY:
            bonus["axis"] += 100
            bonus["allies"] += 25
        else:
            bonus["allies"] += 50
            bonus["axis"] += 50

        survival_rate_allies = (
            (last_result.allied_units_end / max(last_result.allied_units_start, 1)) * 50
        )
        survival_rate_axis = (
            (last_result.axis_units_end / max(last_result.axis_units_start, 1)) * 50
        )

        bonus["allies"] += int(survival_rate_allies)
        bonus["axis"] += int(survival_rate_axis)

        return bonus


class CampaignPersistenceManager:
    """
    Manages saving/loading campaign progress between battles.

    Integration with existing SecureSaveManager for actual file I/O.
    """

    CAMPAIGN_DIR_NAME = "campaign_saves"
    VERSION = "1.0"

    def __init__(self, base_dir: Path | str | None = None):
        if isinstance(base_dir, str):
            base_dir = Path(base_dir)
        self._base_dir = (
            base_dir
            if base_dir
            else Path(__file__).resolve().parent.parent.parent / "saves"
        )
        self._campaign_dir = self._base_dir / self.CAMPAIGN_DIR_NAME
        self._campaign_dir.mkdir(parents=True, exist_ok=True)

    def save_campaign_progress(
        self,
        campaign_id: str,
        progress: CampaignProgress,
    ) -> bool:
        """
        Save campaign progress to JSON file.

        Args:
            campaign_id: Unique campaign identifier
            progress: CampaignProgress object to save

        Returns:
            True if save successful
        """
        try:
            filepath = self._campaign_dir / f"campaign_{campaign_id}.json"
            data = {
                "version": self.VERSION,
                "campaign_id": campaign_id,
                "saved_at": datetime.now(UTC).isoformat(),
                "progress": asdict(progress),
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str, indent=2, ensure_ascii=False)

            logger.info("[Campaign] Saved progress for %s", campaign_id)
            return True

        except Exception as e:
            logger.error("[Campaign] Error saving campaign: %s", e)
            return False

    def load_campaign_progress(
        self,
        campaign_id: str,
    ) -> CampaignProgress | None:
        """
        Load campaign progress from JSON file.

        Args:
            campaign_id: Unique campaign identifier

        Returns:
            CampaignProgress object or None if not found
        """
        filepath = self._campaign_dir / f"campaign_{campaign_id}.json"

        if not filepath.exists():
            logger.info("[Campaign] No saved progress for %s", campaign_id)
            return None

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            version = data.get("version", "0.0")
            if version != self.VERSION:
                logger.warning("[Campaign] Version mismatch: %s != %s", version, self.VERSION)

            progress_dict = data.get("progress", {})
            progress = CampaignProgress(**{
                k: v for k, v in progress_dict.items()
                if k in CampaignProgress.__dataclass_fields__
            })

            unit_states = []
            for us in progress_dict.get("current_unit_states", []):
                unit_states.append(UnitBattleState(**us))
            progress.current_unit_states = unit_states

            results = []
            for br in progress_dict.get("battle_results", []):
                br_units = [UnitBattleState(**u) for u in br.get("unit_states", [])]
                br_copy = {k: v for k, v in br.items() if k != "unit_states"}
                br_copy["unit_states"] = br_units
                results.append(BattleResult(**br_copy))
            progress.battle_results = results

            logger.info("[Campaign] Loaded progress for %s (%d battles)",
                        campaign_id, progress.total_battles_completed)
            return progress

        except Exception as e:
            logger.error("[Campaign] Error loading campaign: %s", e)
            return None

    def apply_inheritance_to_units(
        self,
        progress: CampaignProgress,
        current_units: list,
    ) -> list:
        """
        Apply inherited states from previous battle to current units.

        Units with matching template_ids get their HP, morale, ammo, etc.
        from the previous battle's end state.

        Args:
            progress: CampaignProgress with previous battle data
            current_units: List of Unit objects for new battle

        Returns:
            Updated units with inherited stats
        """
        inherited_count = 0

        for unit in current_units:
            unit_template = getattr(unit, 'unit_template_id', None) or getattr(unit, 'id', None)

            if not unit_template:
                continue

            prev_state = progress.get_unit_state(unit_template)
            if prev_state and prev_state.is_alive:

                if hasattr(unit, 'health_component'):
                    hp_ratio = prev_state.current_hp / max(prev_state.max_hp, 1)
                    unit.health_component.current_hp = (
                        unit.health_component.max_hp * hp_ratio
                    )

                if hasattr(unit, 'morale_component'):
                    recovery = min(20, 10 + progress.total_battles_completed * 2)
                    unit.morale_component.current_morale = min(
                        100.0,
                        prev_state.morale + recovery,
                    )

                if hasattr(unit, 'weapon_component') and prev_state.ammo_remaining:
                    for slot, ammo in prev_state.ammo_remaining.items():
                        if hasattr(unit.weapon_component, slot):
                            setattr(unit.weapon_component, slot, ammo)

                if hasattr(unit, 'veterancy_component'):
                    unit.veterancy_component.add_xp(prev_state.experience)

                inherited_count += 1
            elif prev_state and not prev_state.is_alive:
                if hasattr(unit, 'health_component'):
                    unit.health_component.current_hp = 0

                if hasattr(unit, 'state_machine'):
                    from pycc2.domain.entities.unit import UnitState
                    unit.state_machine.force_state(UnitState.DEAD)

        logger.info("[Campaign] Applied inheritance to %d/%d units", inherited_count, len(current_units))
        return current_units

    def list_saved_campaigns(self) -> list[dict]:
        """List all saved campaign files with metadata."""
        campaigns = []

        for filepath in sorted(self._campaign_dir.glob("campaign_*.json")):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)

                progress = data.get("progress", {})
                campaigns.append({
                    "campaign_id": data.get("campaign_id", filepath.stem),
                    "saved_at": data.get("saved_at", ""),
                    "battles_completed": progress.get("total_battles_completed", 0),
                    "current_operation": progress.get("current_operation_id", ""),
                    "file_path": str(filepath),
                })

            except Exception as e:
                logging.info(f"Campaign save parse failed for {filepath.stem}: {e}")
                campaigns.append({
                    "campaign_id": filepath.stem,
                    "saved_at": "Unknown",
                    "battles_completed": 0,
                    "current_operation": "",
                    "file_path": str(filepath),
                    "error": True,
                })

        return campaigns

    def delete_campaign_save(self, campaign_id: str) -> bool:
        """Delete a campaign save file."""
        filepath = self._campaign_dir / f"campaign_{campaign_id}.json"

        if filepath.exists():
            filepath.unlink()
            logger.info("[Campaign] Deleted save for %s", campaign_id)
            return True

        return False
