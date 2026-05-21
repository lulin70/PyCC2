"""
Medic AI — CC2-Authentic Active Medic Treatment Behavior

Medic units actively seek and treat wounded soldiers.  In CC2,
medics are a critical support unit that moves between wounded
soldiers, stabilizing them so they can continue fighting.

Rules:
  - MedicAI follows TacticalAIBase pattern (evaluate/execute)
  - Evaluate: score based on number of wounded allies nearby
  - Wounded = unit with health_ratio < 0.7
  - Medic moves to nearest wounded within 15 tiles
  - Treatment: heal 0.5 HP per tick (up to health_ratio 0.7, not full)
  - Treatment takes 10 ticks minimum
  - Medic cannot heal while suppressed
  - Medic prioritizes: officers > MG gunners > regular soldiers
  - Medic will not enter enemy LOS to reach wounded
  - TacticType: HEAL_WOUNDED (added to tactic_intent.py)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WOUNDED_THRESHOLD: float = 0.7       # health_ratio below this = wounded
HEAL_RANGE: int = 15                 # Max tiles medic will travel to wounded
HEAL_PER_TICK: float = 0.5          # HP healed per tick
HEAL_CAP_RATIO: float = 0.7         # Heal up to this ratio, not full
MIN_TREATMENT_TICKS: int = 10       # Minimum treatment duration
HEAL_ADJACENT_RANGE: int = 1        # Must be adjacent to heal


# ---------------------------------------------------------------------------
# Treatment priority
# ---------------------------------------------------------------------------

class TreatmentPriority(Enum):
    OFFICER = auto()        # Commander units
    MG_GUNNER = auto()      # Machine gun squads
    REGULAR = auto()        # Regular infantry


def _treatment_priority(unit: Unit) -> TreatmentPriority:
    """Determine treatment priority for a wounded unit."""
    if unit.unit_type == UnitType.COMMANDER:
        return TreatmentPriority.OFFICER
    if unit.unit_type == UnitType.MACHINE_GUN_SQUAD:
        return TreatmentPriority.MG_GUNNER
    return TreatmentPriority.REGULAR


_PRIORITY_ORDER: dict[TreatmentPriority, int] = {
    TreatmentPriority.OFFICER: 0,
    TreatmentPriority.MG_GUNNER: 1,
    TreatmentPriority.REGULAR: 2,
}


# ---------------------------------------------------------------------------
# Treatment state
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TreatmentRecord:
    """Tracks an in-progress treatment by a medic."""
    medic_id: str
    patient_id: str
    ticks_remaining: int
    patient_start_hp: int


# ---------------------------------------------------------------------------
# MedicAI
# ---------------------------------------------------------------------------

class MedicAI(TacticalAIBase):
    """Tactical AI for medic units that actively seek and treat wounded.

    Evaluation heuristic:
      - Score based on number of wounded allies nearby
      - Higher score when medics are available and not suppressed
      - Zero score when no wounded allies or no medics

    Execution:
      - Find wounded allies, prioritize by type (officer > MG > regular)
      - Move medic to nearest wounded within HEAL_RANGE
      - Issue HEAL_WOUNDED intent when adjacent to patient
      - Medic will not enter enemy LOS to reach wounded
    """

    def __init__(self) -> None:
        self._active_treatments: dict[str, TreatmentRecord] = {}
        self._logger = logging.getLogger("pycc2.ai.medic")

    # ------------------------------------------------------------------
    # TacticalAIBase interface
    # ------------------------------------------------------------------

    def evaluate(self, context: TacticalContext) -> float:
        """Return a priority score in [0.0, 1.0].

        Score is driven by:
          - Number of wounded allies (more = higher score)
          - Availability of medics (no medics = 0.0)
          - Whether medics are suppressed (suppressed medics can't heal)
        """
        medics = self._find_medics(context)
        if not medics:
            return 0.0

        wounded = self._find_wounded(context)
        if not wounded:
            return 0.0

        # Score based on ratio of wounded to total friendly units
        total_friendly = sum(1 for u in context.friendly_units if u.is_alive)
        wounded_ratio = len(wounded) / max(total_friendly, 1)

        # Available (non-suppressed) medics
        available_medics = [m for m in medics if not self._is_suppressed(m)]
        medic_ratio = len(available_medics) / max(len(medics), 1)

        score = 0.6 * min(wounded_ratio * 2.0, 1.0) + 0.4 * medic_ratio
        return min(score, 1.0)

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Return HEAL_WOUNDED intents for medics to treat wounded allies.

        For each available medic:
          1. Find the highest-priority wounded ally within range
          2. Check if the path to the wounded is safe (no enemy LOS)
          3. If adjacent, issue HEAL_WOUNDED intent
          4. If not adjacent, issue MOVE_TO intent toward the wounded
        """
        medics = self._find_medics(context)
        wounded = self._find_wounded(context)
        if not medics or not wounded:
            return []

        intents: list[TacticIntent] = []
        assigned_patients: set[str] = set()

        # Sort wounded by priority (officers first, then MG, then regular)
        sorted_wounded = sorted(
            wounded,
            key=lambda u: _PRIORITY_ORDER[_treatment_priority(u)],
        )

        for medic in medics:
            if not medic.can_act:
                continue
            if self._is_suppressed(medic):
                continue
            # Skip medics already treating someone
            if medic.id in self._active_treatments:
                continue

            # Find best patient for this medic
            patient = self._find_best_patient(
                medic, sorted_wounded, assigned_patients, context
            )
            if patient is None:
                continue

            assigned_patients.add(patient.id)

            # Check distance
            dist = medic.position.tile_coord.chebyshev_distance(
                patient.position.tile_coord
            )

            if dist <= HEAL_ADJACENT_RANGE:
                # Adjacent — start healing
                intents.append(
                    TacticIntent(
                        unit_id=medic.id,
                        tactic_type=TacticType.HEAL_WOUNDED,
                        priority=8,
                        target_unit_id=patient.id,
                        target_position=patient.position.tile_coord,
                    )
                )
            else:
                # Move toward patient
                intents.append(
                    TacticIntent(
                        unit_id=medic.id,
                        tactic_type=TacticType.MOVE_TO,
                        priority=7,
                        target_unit_id=patient.id,
                        target_position=patient.position.tile_coord,
                    )
                )

        return intents

    # ------------------------------------------------------------------
    # Treatment management
    # ------------------------------------------------------------------

    def start_treatment(self, medic: Unit, patient: Unit) -> bool:
        """Start a treatment session for a medic-patient pair.

        Returns True if treatment was started successfully.
        """
        if not medic.is_alive or not patient.is_alive:
            return False
        if self._is_suppressed(medic):
            return False
        if medic.id in self._active_treatments:
            return False

        dist = medic.position.tile_coord.chebyshev_distance(
            patient.position.tile_coord
        )
        if dist > HEAL_ADJACENT_RANGE:
            return False

        self._active_treatments[medic.id] = TreatmentRecord(
            medic_id=medic.id,
            patient_id=patient.id,
            ticks_remaining=MIN_TREATMENT_TICKS,
            patient_start_hp=patient.health.hp,
        )
        self._logger.info(
            f"Medic {medic.id} started treating {patient.id} "
            f"({MIN_TREATMENT_TICKS} ticks)"
        )
        return True

    def tick(self, all_units: list[Unit]) -> list[TreatmentRecord]:
        """Advance all active treatments by one tick.

        Returns a list of TreatmentRecord entries that completed this tick.
        Heals the patient by HEAL_PER_TICK each tick (up to HEAL_CAP_RATIO).
        """
        completed: list[TreatmentRecord] = []

        for medic_id, record in list(self._active_treatments.items()):
            medic = self._find_unit(medic_id, all_units)
            patient = self._find_unit(record.patient_id, all_units)

            # Check if treatment can continue
            if medic is None or not medic.is_alive:
                del self._active_treatments[medic_id]
                continue
            if patient is None or not patient.is_alive:
                del self._active_treatments[medic_id]
                continue
            if self._is_suppressed(medic):
                # Suppressed medic pauses treatment (doesn't cancel)
                continue

            # Heal the patient
            if patient.health.hp_ratio < HEAL_CAP_RATIO:
                heal_amount = int(HEAL_PER_TICK * patient.health.max_hp)
                if heal_amount > 0:
                    # Cap healing at HEAL_CAP_RATIO
                    max_hp = int(HEAL_CAP_RATIO * patient.health.max_hp)
                    actual_heal = min(heal_amount, max_hp - patient.health.hp)
                    if actual_heal > 0:
                        patient.health.heal(actual_heal)

            record.ticks_remaining -= 1
            if record.ticks_remaining <= 0:
                # Treatment complete or patient has reached cap
                completed.append(record)
                del self._active_treatments[medic_id]
                self._logger.info(
                    f"Medic {medic_id} completed treating {record.patient_id}"
                )

        return completed

    def get_treatment_state(self, medic_id: str) -> TreatmentRecord | None:
        return self._active_treatments.get(medic_id)

    @property
    def active_treatment_count(self) -> int:
        return len(self._active_treatments)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_medics(context: TacticalContext) -> list[Unit]:
        """Find friendly medic units."""
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.unit_type == UnitType.MEDIC_TEAM
        ]

    @staticmethod
    def _find_wounded(context: TacticalContext) -> list[Unit]:
        """Find friendly wounded units (health_ratio < 0.7)."""
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.health.hp_ratio < WOUNDED_THRESHOLD
            and u.unit_type != UnitType.MEDIC_TEAM  # Medics don't heal themselves
        ]

    @staticmethod
    def _is_suppressed(unit: Unit) -> bool:
        """Check if a unit is suppressed (cannot perform healing)."""
        from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect

        effect = unit.suppression_level
        return effect in (
            SuppressionEffect.MODERATE,
            SuppressionEffect.HEAVY,
            SuppressionEffect.PINNED,
            SuppressionEffect.PANIC,
        )

    def _find_best_patient(
        self,
        medic: Unit,
        wounded: list[Unit],
        already_assigned: set[str],
        context: TacticalContext,
    ) -> Unit | None:
        """Find the best patient for a medic.

        Considers:
          1. Treatment priority (officer > MG > regular)
          2. Distance (within HEAL_RANGE)
          3. Safety (path not in enemy LOS)
        """
        medic_pos = medic.position.tile_coord
        best: Unit | None = None
        best_score = float("inf")

        for patient in wounded:
            if patient.id in already_assigned:
                continue

            dist = medic_pos.chebyshev_distance(patient.position.tile_coord)
            if dist > HEAL_RANGE:
                continue

            # Check if path to patient is safe (not in enemy LOS)
            if not self._is_path_safe(medic, patient, context):
                continue

            # Score: priority first, then distance
            priority_val = _PRIORITY_ORDER[_treatment_priority(patient)]
            score = priority_val * 100 + dist  # Priority dominates

            if score < best_score:
                best_score = score
                best = patient

        return best

    @staticmethod
    def _is_path_safe(
        medic: Unit,
        patient: Unit,
        context: TacticalContext,
    ) -> bool:
        """Check if the path from medic to patient avoids enemy LOS.

        A path is unsafe if the midpoint between medic and patient
        is visible to any enemy unit.
        """
        medic_pos = medic.position.tile_coord
        patient_pos = patient.position.tile_coord
        mid = TileCoord(
            (medic_pos.x + patient_pos.x) // 2,
            (medic_pos.y + patient_pos.y) // 2,
        )

        for enemy in context.enemy_units:
            if not enemy.is_alive:
                continue
            enemy_pos = enemy.position.tile_coord
            # Check if enemy can see the midpoint
            if hasattr(context.game_map, 'has_line_of_sight'):
                if context.game_map.has_line_of_sight(enemy_pos, mid):
                    return False
            else:
                # Fallback: simple distance check
                dist = enemy_pos.chebyshev_distance(mid)
                if dist <= 5:
                    return False

        return True

    @staticmethod
    def _find_unit(unit_id: str, all_units: list[Unit]) -> Unit | None:
        for u in all_units:
            if u.id == unit_id:
                return u
        return None
