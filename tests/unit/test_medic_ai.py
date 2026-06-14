"""
Unit Tests for MedicAI

Tests medic behavior, healing target selection, treatment priority,
and treatment lifecycle.
"""

import pytest
from unittest.mock import Mock

from pycc2.domain.ai.medic_ai import (
    MedicAI,
    TreatmentPriority,
    _treatment_priority,
    MIN_TREATMENT_TICKS,
)
from pycc2.domain.entities.unit import Faction, UnitType
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.value_objects.tile_coord import TileCoord


# ===========================================================================
# Stub helpers
# ===========================================================================

def _make_unit(unit_id, faction=Faction.ALLIES, unit_type=UnitType.INFANTRY_SQUAD,
               tile_x=10, tile_y=10, alive=True, can_act=True,
               hp=100, max_hp=100, suppressed=False):
    """Create a mock unit for medic testing."""
    unit = Mock()
    unit.id = unit_id
    unit.name = unit_id
    unit.faction = faction
    unit.unit_type = unit_type
    unit.is_alive = alive
    unit.can_act = can_act

    # Position
    pos = Mock()
    pos.tile_coord = TileCoord(tile_x, tile_y)
    unit.position = pos

    # Health
    health = Mock()
    health.hp = hp
    health.max_hp = max_hp
    health.hp_ratio = hp / max_hp if max_hp > 0 else 0.0
    health.heal = Mock()
    unit.health = health

    # Suppression
    unit.suppression_level = Mock()
    if suppressed:
        from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect
        unit.suppression_level = SuppressionEffect.HEAVY
    else:
        from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect
        unit.suppression_level = SuppressionEffect.NONE

    return unit


def _make_medic(unit_id="medic1", tile_x=10, tile_y=10, suppressed=False,
                hp=100, max_hp=100):
    """Create a mock medic unit."""
    return _make_unit(
        unit_id, unit_type=UnitType.MEDIC_TEAM,
        tile_x=tile_x, tile_y=tile_y,
        hp=hp, max_hp=max_hp, suppressed=suppressed,
    )


def _make_wounded(unit_id="wounded1", tile_x=11, tile_y=10, hp=50,
                  unit_type=UnitType.INFANTRY_SQUAD):
    """Create a mock wounded unit."""
    return _make_unit(
        unit_id, unit_type=unit_type,
        tile_x=tile_x, tile_y=tile_y,
        hp=hp, max_hp=100,
    )


# ===========================================================================
# Tests — Treatment Priority
# ===========================================================================

@pytest.mark.unit
class TestTreatmentPriority:
    """Test treatment priority assignment."""

    def test_commander_highest_priority(self):
        unit = _make_unit("cmd", unit_type=UnitType.COMMANDER)
        assert _treatment_priority(unit) == TreatmentPriority.OFFICER

    def test_mg_gunner_medium_priority(self):
        unit = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD)
        assert _treatment_priority(unit) == TreatmentPriority.MG_GUNNER

    def test_infantry_lowest_priority(self):
        unit = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD)
        assert _treatment_priority(unit) == TreatmentPriority.REGULAR

    def test_sniper_regular_priority(self):
        unit = _make_unit("sniper", unit_type=UnitType.SNIPER_TEAM)
        assert _treatment_priority(unit) == TreatmentPriority.REGULAR


# ===========================================================================
# Tests — Find Medics and Wounded
# ===========================================================================

@pytest.mark.unit
class TestFindMedicsAndWounded:
    """Test medic and wounded unit discovery."""

    def test_find_medics(self):
        ai = MedicAI()
        medic = _make_medic()
        infantry = _make_unit("inf")
        context = TacticalContext(
            friendly_units=[medic, infantry],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        medics = ai._find_medics(context)
        assert len(medics) == 1
        assert medics[0].id == "medic1"

    def test_find_no_medics(self):
        ai = MedicAI()
        infantry = _make_unit("inf")
        context = TacticalContext(
            friendly_units=[infantry],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        medics = ai._find_medics(context)
        assert len(medics) == 0

    def test_find_wounded(self):
        ai = MedicAI()
        wounded = _make_wounded(hp=50)
        healthy = _make_unit("healthy", hp=100, max_hp=100)
        context = TacticalContext(
            friendly_units=[wounded, healthy],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        wounded_list = ai._find_wounded(context)
        assert len(wounded_list) == 1
        assert wounded_list[0].id == "wounded1"

    def test_no_wounded_when_all_healthy(self):
        ai = MedicAI()
        healthy = _make_unit("h1", hp=90, max_hp=100)
        context = TacticalContext(
            friendly_units=[healthy],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        wounded_list = ai._find_wounded(context)
        assert len(wounded_list) == 0

    def test_medic_not_in_wounded_list(self):
        ai = MedicAI()
        wounded_medic = _make_medic(hp=50, max_hp=100)
        context = TacticalContext(
            friendly_units=[wounded_medic],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        wounded_list = ai._find_wounded(context)
        assert len(wounded_list) == 0


# ===========================================================================
# Tests — Evaluate
# ===========================================================================

@pytest.mark.unit
class TestMedicEvaluate:
    """Test MedicAI evaluate scoring."""

    def test_zero_when_no_medics(self):
        ai = MedicAI()
        context = TacticalContext(
            friendly_units=[_make_wounded()],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        assert ai.evaluate(context) == 0.0

    def test_zero_when_no_wounded(self):
        ai = MedicAI()
        context = TacticalContext(
            friendly_units=[_make_medic(), _make_unit("h1", hp=100, max_hp=100)],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        assert ai.evaluate(context) == 0.0

    def test_nonzero_with_medics_and_wounded(self):
        ai = MedicAI()
        medic = _make_medic()
        wounded = _make_wounded()
        context = TacticalContext(
            friendly_units=[medic, wounded],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        score = ai.evaluate(context)
        assert score > 0.0


# ===========================================================================
# Tests — Execute
# ===========================================================================

@pytest.mark.unit
class TestMedicExecute:
    """Test MedicAI execute intent generation."""

    def test_heal_intent_when_adjacent(self):
        ai = MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        wounded = _make_wounded(tile_x=11, tile_y=10)
        context = TacticalContext(
            friendly_units=[medic, wounded],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        intents = ai.execute(context)
        assert len(intents) >= 1
        heal_intents = [i for i in intents if i.tactic_type == TacticType.HEAL_WOUNDED]
        assert len(heal_intents) >= 1

    def test_move_intent_when_not_adjacent(self):
        ai = MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        wounded = _make_wounded(tile_x=15, tile_y=10)
        context = TacticalContext(
            friendly_units=[medic, wounded],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        intents = ai.execute(context)
        assert len(intents) >= 1
        move_intents = [i for i in intents if i.tactic_type == TacticType.MOVE_TO]
        assert len(move_intents) >= 1

    def test_suppressed_medic_skipped(self):
        ai = MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10, suppressed=True)
        wounded = _make_wounded(tile_x=11, tile_y=10)
        context = TacticalContext(
            friendly_units=[medic, wounded],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        intents = ai.execute(context)
        assert len(intents) == 0

    def test_no_intents_when_no_medics(self):
        ai = MedicAI()
        context = TacticalContext(
            friendly_units=[_make_wounded()],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        intents = ai.execute(context)
        assert intents == []


# ===========================================================================
# Tests — Treatment Lifecycle
# ===========================================================================

@pytest.mark.unit
class TestTreatmentLifecycle:
    """Test start_treatment and tick methods."""

    def test_start_treatment_success(self):
        ai = MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        patient = _make_wounded(tile_x=11, tile_y=10)
        result = ai.start_treatment(medic, patient)
        assert result is True
        assert ai.active_treatment_count == 1

    def test_start_treatment_too_far(self):
        ai = MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        patient = _make_wounded(tile_x=20, tile_y=20)
        result = ai.start_treatment(medic, patient)
        assert result is False
        assert ai.active_treatment_count == 0

    def test_start_treatment_dead_patient(self):
        ai = MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        patient = _make_wounded(tile_x=11, tile_y=10)
        patient.is_alive = False
        result = ai.start_treatment(medic, patient)
        assert result is False

    def test_start_treatment_already_treating(self):
        ai = MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        patient1 = _make_wounded("w1", tile_x=11, tile_y=10)
        patient2 = _make_wounded("w2", tile_x=10, tile_y=11)
        ai.start_treatment(medic, patient1)
        result = ai.start_treatment(medic, patient2)
        assert result is False

    def test_tick_heals_patient(self):
        ai = MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        patient = _make_wounded(tile_x=11, tile_y=10, hp=50)
        ai.start_treatment(medic, patient)

        ai.tick([medic, patient])
        # Patient should have been healed
        patient.health.heal.assert_called()

    def test_tick_completes_treatment(self):
        ai = MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        patient = _make_wounded(tile_x=11, tile_y=10, hp=50)
        ai.start_treatment(medic, patient)

        # Run enough ticks to complete
        completed = []
        for _ in range(MIN_TREATMENT_TICKS + 1):
            completed.extend(ai.tick([medic, patient]))

        assert len(completed) >= 1
        assert ai.active_treatment_count == 0

    def test_tick_dead_medic_cancels_treatment(self):
        ai = MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        patient = _make_wounded(tile_x=11, tile_y=10, hp=50)
        ai.start_treatment(medic, patient)

        medic.is_alive = False
        ai.tick([medic, patient])
        assert ai.active_treatment_count == 0

    def test_get_treatment_state(self):
        ai = MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        patient = _make_wounded(tile_x=11, tile_y=10, hp=50)
        ai.start_treatment(medic, patient)

        state = ai.get_treatment_state("medic1")
        assert state is not None
        assert state.patient_id == "wounded1"
        assert state.ticks_remaining == MIN_TREATMENT_TICKS

    def test_get_treatment_state_none(self):
        ai = MedicAI()
        assert ai.get_treatment_state("nonexistent") is None


# ===========================================================================
# Tests — Path Safety
# ===========================================================================

@pytest.mark.unit
class TestPathSafety:
    """Test path safety checking for medic movement."""

    def test_safe_path_no_enemies(self):
        MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        patient = _make_wounded(tile_x=12, tile_y=10)
        context = TacticalContext(
            friendly_units=[medic, patient],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )
        assert MedicAI._is_path_safe(medic, patient, context) is True

    def test_unsafe_path_enemy_near_midpoint(self):
        MedicAI()
        medic = _make_medic(tile_x=10, tile_y=10)
        patient = _make_wounded(tile_x=14, tile_y=10)
        # Enemy near midpoint (12, 10)
        enemy = _make_unit("e1", faction=Faction.AXIS, tile_x=12, tile_y=10)
        game_map = Mock()
        game_map.has_line_of_sight = None  # Force distance-based check
        context = TacticalContext(
            friendly_units=[medic, patient],
            enemy_units=[enemy],
            game_map=game_map,
            current_tick=100,
        )
        result = MedicAI._is_path_safe(medic, patient, context)
        assert result is False
