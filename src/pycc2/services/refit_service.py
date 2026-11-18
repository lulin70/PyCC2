"""Refit Service — MC2-06 between-battle refit economy on CampaignProgress.

Operations (1 RP = 1 hp for repair; replacements cost REINFORCE_RP_PER_MEMBER
each and also steady the squad's morale):
- ``available_rp(faction)`` / ``spend_rp(faction, amount)`` — read/write
  ``CampaignProgress.requisition_points_allies`` / ``requisition_points_axis``
  (faction strings are normalized case-insensitively).
- ``repair_cost(unit)`` / ``repair(unit, rp)`` — restore hp.
- ``reinforce_cost(unit)`` / ``reinforce(unit, rp)`` — replace fallen squad
  members (manpower) and lift morale.

The UI (campaign refit screen) is deferred; this wave ships the service and
its integration coverage only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pycc2.domain.systems.campaign_persistence import (
    DEFAULT_CAMPAIGN_ID,
    CampaignPersistenceManager,
    CampaignProgress,
)

logger = logging.getLogger(__name__)


def normalize_side(faction: str) -> str:
    """Normalize a faction string ("ALLIES"/"german"/"Axis"/...) to "allies"/"axis"."""
    name = str(faction).strip().lower()
    if name in ("axis", "german", "germany"):
        return "axis"
    return "allies"


@dataclass
class RefitService:
    """Between-battle refit: repair and reinforce units with requisition points."""

    manager: CampaignPersistenceManager
    campaign_id: str = DEFAULT_CAMPAIGN_ID
    # Class constants (not constructor fields):
    # replacement soldiers cost more than raw hp (1 RP = 1 hp);
    # fresh replacements steady the squad's morale per member reinforced.
    REINFORCE_RP_PER_MEMBER = 10
    REINFORCE_MORALE_PER_MEMBER = 10

    # ------------------------------------------------------------------
    # Requisition points
    # ------------------------------------------------------------------

    def _load_progress(self) -> CampaignProgress:
        progress = self.manager.load_campaign_progress(self.campaign_id)
        if progress is None:
            progress = CampaignProgress(
                campaign_id=self.campaign_id,
                current_operation_id="unknown",
            )
        return progress

    @staticmethod
    def _side_rp(progress: CampaignProgress, side: str) -> int:
        if side == "allies":
            return int(progress.requisition_points_allies)
        return int(progress.requisition_points_axis)

    def _set_side_rp(self, progress: CampaignProgress, side: str, value: int) -> None:
        value = max(0, int(value))
        if side == "allies":
            progress.requisition_points_allies = value
        else:
            progress.requisition_points_axis = value
        if not self.manager.save_campaign_progress(self.campaign_id, progress):
            logger.warning("Refit: campaign progress save failed for %s", self.campaign_id)

    def available_rp(self, faction: str) -> int:
        """Return the requisition points currently held by the faction side."""
        return self._side_rp(self._load_progress(), normalize_side(faction))

    def spend_rp(self, faction: str, amount: int) -> bool:
        """Deduct requisition points; False when the balance is insufficient."""
        amount = int(amount)
        if amount <= 0:
            return False
        progress = self._load_progress()
        side = normalize_side(faction)
        current = self._side_rp(progress, side)
        if amount > current:
            return False
        self._set_side_rp(progress, side, current - amount)
        return True

    # ------------------------------------------------------------------
    # Repair (1 RP = 1 hp)
    # ------------------------------------------------------------------

    @staticmethod
    def _unit_side(unit: Any) -> str:
        return normalize_side(getattr(getattr(unit, "faction", None), "name", "allies"))

    @staticmethod
    def repair_cost(unit: Any) -> int:
        """RP needed to restore the unit to full hp (1 RP = 1 hp)."""
        health = getattr(unit, "health", None)
        if health is None:
            return 0
        return max(0, int(health.max_hp) - int(health.hp))

    def repair(self, unit: Any, rp: int) -> int:
        """Spend up to rp points restoring hp; returns the hp actually repaired."""
        rp = int(rp)
        if rp <= 0:
            return 0
        missing = self.repair_cost(unit)
        if missing <= 0:
            return 0
        side = self._unit_side(unit)
        budget = min(rp, missing, self.available_rp(side))
        if budget <= 0:
            return 0
        if not self.spend_rp(side, budget):
            return 0
        repaired = int(unit.health.heal(budget))
        logger.debug("Refit: repaired %s by %d hp", getattr(unit, "id", "?"), repaired)
        return repaired

    # ------------------------------------------------------------------
    # Reinforce (manpower + morale)
    # ------------------------------------------------------------------

    def reinforce_cost(self, unit: Any) -> int:
        """RP needed to replace every fallen squad member."""
        squad = getattr(unit, "squad_ref", None)
        if squad is None:
            return 0
        missing = int(getattr(squad, "dead_count", 0))
        return missing * self.REINFORCE_RP_PER_MEMBER

    def reinforce(self, unit: Any, rp: int) -> int:
        """Replace fallen squad members; returns the number reinforced.

        Reinforced manpower costs ``REINFORCE_RP_PER_MEMBER`` per member and
        each fresh replacement lifts the unit's morale a little.
        """
        rp = int(rp)
        if rp <= 0:
            return 0
        squad = getattr(unit, "squad_ref", None)
        if squad is None:
            return 0
        missing = int(getattr(squad, "dead_count", 0))
        if missing <= 0:
            return 0
        affordable = min(missing, rp // self.REINFORCE_RP_PER_MEMBER)
        if affordable <= 0:
            return 0
        side = self._unit_side(unit)
        if not self.spend_rp(side, affordable * self.REINFORCE_RP_PER_MEMBER):
            return 0
        squad.remove_dead()
        squad.reinforce(affordable)
        morale = getattr(unit, "morale", None)
        if morale is not None:
            morale.apply_delta(self.REINFORCE_MORALE_PER_MEMBER * affordable)
        logger.debug(
            "Refit: reinforced %s with %d replacements", getattr(unit, "id", "?"), affordable
        )
        return affordable


__all__ = ["RefitService", "normalize_side"]
