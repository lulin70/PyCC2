"""Integration tests for cover_seek_ai INTEGRATE v0.7.6.

Verifies that TacticalOrchestrator.tick() Phase 6 correctly generates
cover-seeking MOVE_TO orders for suppressed units that don't already
have an order, via CoverSeekAI.execute(context).

Phase 6 design (v0.7.6):
  - Runs after Phase 5 (psychology filtering)
  - Calls CoverSeekAI.execute(context) to generate MOVE_TO intents for
    units under heavy suppression (current_suppression >= 65)
  - Only adds cover intents for units NOT already present in ``final``
    (avoids overriding Phase 1-5 decisions)
  - CoverScoringSystem is configured with context.game_map

Covers:
  - Happy Path: suppressed unit generates cover order
  - Happy Path: unsuppressed unit does NOT generate cover order
  - Boundary: suppression=0 / suppression=100 (MAX)
  - Boundary: no available cover (all tiles impassable) -> no order
  - Integration: TacticalOrchestrator.tick() Phase 6 end-to-end
  - Phase 5 + Phase 6 synergy: psychology rejects offensive, cover seeks
  - Filter Behavior: existing order not duplicated by Phase 6
  - Filter Behavior: cover intent logs info message
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

from pycc2.domain.ai.difficulty_system import DifficultyConfig, DifficultyLevel
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext, TacticalOrchestrator
from pycc2.domain.ai.tactical_ai_types import TacticalAIBase
from pycc2.domain.components.fatigue_component import FatigueLevel
from pycc2.domain.components.morale_component import MoraleState
from pycc2.domain.entities.unit import Faction, UnitType
from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubAI(TacticalAIBase):
    """Minimal AI stub that returns a fixed score and list of intents."""

    def __init__(self, name: str, score: float, intents: list[TacticIntent]) -> None:
        self._name = name
        self._score = score
        self._intents = intents

    def evaluate(self, context: TacticalContext) -> float:  # noqa: ARG002
        return self._score

    def execute(self, context: TacticalContext) -> list[TacticIntent]:  # noqa: ARG002
        return list(self._intents)

    @property
    def name(self) -> str:
        return self._name


def _make_unit(
    uid: str = "u1",
    alive: bool = True,
    morale_state: MoraleState = MoraleState.RALLIED,
    suppression_effect: SuppressionEffect = SuppressionEffect.NONE,
    suppression_value: float = 0.0,
    fatigue: FatigueLevel = FatigueLevel.FRESH,
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    x: int = 10,
    y: int = 10,
    hp_ratio: float = 1.0,
    moving: bool = False,
) -> MagicMock:
    """Create a mock Unit with both psychology and cover-seek attributes.

    - ``suppression_state.current_suppression`` (float) is read by CoverSeekAI
    - ``suppression_state.get_current_effect()`` (SuppressionEffect) is read by
      PsychologySystem
    """
    unit = MagicMock(spec=[])
    unit.id = uid
    unit.faction = faction
    unit.unit_type = unit_type
    unit.is_alive = alive

    # position_component (read by CoverSeekAI._get_candidates)
    pos_comp = MagicMock()
    pos_comp.x = x
    pos_comp.y = y
    unit.position_component = pos_comp

    # position (read by some AI stubs / threat_score helpers)
    pos = MagicMock()
    from pycc2.domain.value_objects.tile_coord import TileCoord

    pos.tile_coord = TileCoord(x, y)
    unit.position = pos

    # morale (read by PsychologySystem)
    morale = MagicMock()
    morale.state = morale_state
    unit.morale = morale

    # suppression_state — serves both CoverSeekAI (current_suppression float)
    # and PsychologySystem (get_current_effect() -> SuppressionEffect)
    supp_state = MagicMock()
    supp_state.current_suppression = suppression_value
    supp_state.turns_since_last_hit = 0
    supp_state.get_current_effect = MagicMock(return_value=suppression_effect)
    unit.suppression_state = supp_state

    # fatigue (read by PsychologySystem)
    fat = MagicMock()
    fat.level = fatigue
    unit.fatigue = fat

    # health_component (read by CoverSeekAI._get_hp_ratio)
    hc = MagicMock()
    hc.max_hp = 100
    hc.current_hp = int(100 * hp_ratio)
    unit.health_component = hc

    # state (read by CoverSeekAI._is_moving)
    unit.state = "MOVING" if moving else None

    return unit


def _make_map(
    cover_bonus: int = 3,
    concealment: float = 0.5,
    movement_cost: float = 1.0,
    impassable: bool = False,
) -> MagicMock:
    """Create a mock GameMap where every valid tile has the given properties.

    When ``impassable=True``, all tiles have movement_cost >= 5.0 so the
    CoverScoringSystem skips them (no candidates -> no cover found).
    """
    gmap = MagicMock()
    gmap.is_valid_coord = MagicMock(return_value=True)

    tile = MagicMock()
    tile.total_cover_bonus = 0 if impassable else cover_bonus
    tile.total_concealment = 0.0 if impassable else concealment
    tile.effective_movement_cost = 5.0 if impassable else movement_cost
    gmap.get_tile = MagicMock(return_value=tile)
    return gmap


def _make_context(
    friendlies: list,
    enemies: list | None = None,
    gmap: MagicMock | None = None,
) -> TacticalContext:
    """Create a TacticalContext with the given friendly units and optional map."""
    if gmap is None:
        gmap = _make_map()
    return TacticalContext(
        friendly_units=friendlies,
        enemy_units=enemies or [],
        game_map=gmap,
        current_tick=1,
        blackboards={},
        difficulty_config=DifficultyConfig(level=DifficultyLevel.EASY),
        vl_positions=[],
    )


def _make_intent(uid: str, tactic: TacticType, priority: int = 5) -> TacticIntent:
    return TacticIntent(unit_id=uid, tactic_type=tactic, priority=priority)


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestCoverSeekIntegration:
    """Verify TacticalOrchestrator.tick() Phase 6 cover-seeking integration."""

    def test_suppressed_unit_generates_cover_order(self):
        """Happy Path: suppressed unit (no existing order) -> cover MOVE_TO added."""
        unit = _make_unit(
            uid="u1",
            suppression_effect=SuppressionEffect.HEAVY,
            suppression_value=80.0,
            x=10,
            y=10,
        )
        ctx = _make_context(friendlies=[unit])
        orch = TacticalOrchestrator()  # no AIs registered -> final empty before Phase 6
        orders = orch.tick(ctx)
        assert len(orders) == 1, f"Expected 1 cover order, got {len(orders)}"
        assert orders[0].unit_id == "u1"
        assert orders[0].tactic_type == TacticType.MOVE_TO
        assert orders[0].target_position is not None, "Cover order must have a target position"

    def test_unsuppressed_unit_no_cover_order(self):
        """Happy Path: unsuppressed unit (suppression < 65) -> no cover order."""
        unit = _make_unit(
            uid="u1",
            suppression_effect=SuppressionEffect.NONE,
            suppression_value=10.0,
        )
        ctx = _make_context(friendlies=[unit])
        orch = TacticalOrchestrator()
        orders = orch.tick(ctx)
        assert len(orders) == 0, f"Unsuppressed unit should not seek cover, got {len(orders)}"

    def test_boundary_suppression_zero(self):
        """Boundary: suppression=0 -> no cover order generated."""
        unit = _make_unit(
            uid="u1",
            suppression_effect=SuppressionEffect.NONE,
            suppression_value=0.0,
        )
        ctx = _make_context(friendlies=[unit])
        orch = TacticalOrchestrator()
        orders = orch.tick(ctx)
        assert len(orders) == 0, "suppression=0 must not trigger cover seeking"

    def test_boundary_suppression_max(self):
        """Boundary: suppression=100 (MAX) -> cover order generated."""
        unit = _make_unit(
            uid="u1",
            suppression_effect=SuppressionEffect.PANIC,
            suppression_value=100.0,
            hp_ratio=0.3,  # low HP boosts priority
        )
        ctx = _make_context(friendlies=[unit])
        orch = TacticalOrchestrator()
        orders = orch.tick(ctx)
        assert len(orders) == 1, "suppression=100 must trigger cover seeking"
        assert orders[0].tactic_type == TacticType.MOVE_TO

    def test_no_available_cover_returns_none(self):
        """Boundary: all tiles impassable -> no cover candidate -> no order."""
        unit = _make_unit(
            uid="u1",
            suppression_effect=SuppressionEffect.HEAVY,
            suppression_value=80.0,
        )
        gmap = _make_map(impassable=True)
        ctx = _make_context(friendlies=[unit], gmap=gmap)
        orch = TacticalOrchestrator()
        orders = orch.tick(ctx)
        assert len(orders) == 0, (
            "No available cover (all tiles impassable) must produce no cover order"
        )

    def test_phase5_rejects_offensive_then_phase6_adds_cover(self):
        """Integration: Phase 5 rejects ATTACK (HEAVY supp), Phase 6 adds cover MOVE_TO.

        Synergy: psychology filters out the offensive order, then cover-seek
        generates a defensive move-to-cover order for the same suppressed unit.
        """
        unit = _make_unit(
            uid="u1",
            morale_state=MoraleState.RALLIED,
            suppression_effect=SuppressionEffect.HEAVY,
            suppression_value=80.0,
        )
        ctx = _make_context(friendlies=[unit])
        ai = _StubAI("TestAI", score=0.8, intents=[_make_intent("u1", TacticType.ATTACK)])
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        # Phase 5 rejects ATTACK (offensive under HEAVY suppression)
        # Phase 6 adds MOVE_TO cover order for the suppressed unit
        assert len(orders) == 1, (
            f"Expected 1 cover order after psychology filter + cover seek, got {len(orders)}"
        )
        assert orders[0].unit_id == "u1"
        assert orders[0].tactic_type == TacticType.MOVE_TO, (
            "Phase 6 must generate MOVE_TO cover order for suppressed unit"
        )

    def test_existing_defend_order_not_duplicated_by_phase6(self):
        """Filter Behavior: DEFEND survives Phase 5, Phase 6 does NOT duplicate.

        Unit has a DEFEND order (defensive, accepted under HEAVY suppression).
        Phase 6 generates a MOVE_TO cover intent but skips the unit because it
        already has an order in ``final``. Final length stays at 1.
        """
        unit = _make_unit(
            uid="u1",
            morale_state=MoraleState.RALLIED,
            suppression_effect=SuppressionEffect.HEAVY,
            suppression_value=80.0,
        )
        ctx = _make_context(friendlies=[unit])
        ai = _StubAI("TestAI", score=0.8, intents=[_make_intent("u1", TacticType.DEFEND)])
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        # Phase 5 accepts DEFEND (defensive under HEAVY suppression)
        # Phase 6 would generate MOVE_TO but u1 already in final -> skipped
        assert len(orders) == 1, (
            f"Existing order must not be duplicated by Phase 6, got {len(orders)}"
        )
        assert orders[0].tactic_type == TacticType.DEFEND, (
            "DEFEND order must be preserved, not replaced by cover MOVE_TO"
        )

    def test_cover_intent_logs_info(self, caplog):
        """Filter Behavior: cover intent generation logs an INFO message."""
        unit = _make_unit(
            uid="u1",
            suppression_effect=SuppressionEffect.HEAVY,
            suppression_value=80.0,
        )
        ctx = _make_context(friendlies=[unit])
        orch = TacticalOrchestrator()
        with caplog.at_level(logging.INFO, logger="pycc2.domain.ai.cover_seek_ai"):
            orch.tick(ctx)
        assert any("CoverSeek" in rec.message for rec in caplog.records), (
            "CoverSeekAI must log an INFO message when generating a cover intent"
        )

    def test_mixed_suppression_only_suppressed_seeks_cover(self):
        """Integration: mixed units -> only suppressed unit gets cover order."""
        suppressed = _make_unit(
            uid="u_supp",
            suppression_effect=SuppressionEffect.HEAVY,
            suppression_value=80.0,
            x=10,
            y=10,
        )
        calm = _make_unit(
            uid="u_calm",
            suppression_effect=SuppressionEffect.NONE,
            suppression_value=10.0,
            x=20,
            y=20,
        )
        ctx = _make_context(friendlies=[suppressed, calm])
        orch = TacticalOrchestrator()
        orders = orch.tick(ctx)
        assert len(orders) == 1, (
            f"Only the suppressed unit should seek cover, got {len(orders)} orders"
        )
        assert orders[0].unit_id == "u_supp", "Cover order must target the suppressed unit"
