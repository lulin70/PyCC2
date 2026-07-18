"""Integration tests for psychology_system INTEGRATE v0.7.5.

Verifies that TacticalOrchestrator.tick() Phase 5 correctly filters
orders based on unit psychological state via PsychologySystem.evaluate_order().

Note: Phase 3 conflict resolution assigns at most one intent per unit.
Tests use distinct unit_ids per tactic to verify psychology filtering.

Covers:
  - Healthy units' orders are preserved
  - BROKEN/ROUTING units' non-survival orders are filtered
  - Survival commands (RETREAT/TAKE_COVER/SURRENDER/RALLY_NCO) always accepted
  - Dead units' orders are filtered
  - Units not in context are preserved (defensive)
  - Mixed units: partial filtering
  - Suppression-based rejection (HEAVY/PANIC)
"""

from __future__ import annotations

from unittest.mock import MagicMock

from pycc2.domain.ai.difficulty_system import DifficultyConfig, DifficultyLevel
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext, TacticalOrchestrator
from pycc2.domain.ai.tactical_ai_types import TacticalAIBase
from pycc2.domain.components.fatigue_component import FatigueLevel
from pycc2.domain.components.morale_component import MoraleState
from pycc2.domain.entities.unit import Faction, UnitType
from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect
from pycc2.domain.value_objects.tile_coord import TileCoord

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
    suppression: SuppressionEffect = SuppressionEffect.NONE,
    fatigue: FatigueLevel = FatigueLevel.FRESH,
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    x: int = 10,
    y: int = 10,
) -> MagicMock:
    """Create a mock Unit with psychology-relevant attributes."""
    unit = MagicMock(spec=[])
    unit.id = uid
    unit.faction = faction
    unit.unit_type = unit_type
    unit.is_alive = alive

    # position (not used by psychology but needed for some AI stubs)
    pos = MagicMock()
    pos.tile_coord = TileCoord(x, y)
    unit.position = pos

    # morale component
    morale = MagicMock()
    morale.state = morale_state
    unit.morale = morale

    # suppression_state with get_current_effect()
    supp_state = MagicMock()
    supp_state.get_current_effect = MagicMock(return_value=suppression)
    unit.suppression_state = supp_state

    # fatigue component
    fat = MagicMock()
    fat.level = fatigue
    unit.fatigue = fat

    return unit


def _make_context(friendlies: list, enemies: list | None = None) -> TacticalContext:
    """Create a TacticalContext with the given friendly units."""
    gmap = MagicMock()
    gmap.width = 50
    gmap.height = 50
    gmap.is_within_bounds = MagicMock(return_value=True)
    gmap.is_passable = MagicMock(return_value=True)
    gmap.has_line_of_sight = MagicMock(return_value=False)
    terrain = MagicMock()
    terrain.cover_modifier = 0.3
    gmap.get_terrain = MagicMock(return_value=terrain)
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


def _make_units_with_tactics(
    morale_state: MoraleState = MoraleState.RALLIED,
    suppression: SuppressionEffect = SuppressionEffect.NONE,
    fatigue: FatigueLevel = FatigueLevel.FRESH,
    alive: bool = True,
    tactics: list[TacticType] | None = None,
) -> tuple[list[MagicMock], list[TacticIntent]]:
    """Create one unit per tactic (distinct unit_ids) + matching intents.

    Each unit gets a distinct id (u0, u1, ...) so Phase 3 conflict resolution
    keeps all intents (one per unit).
    """
    tactics = tactics or [TacticType.ATTACK]
    units: list[MagicMock] = []
    intents: list[TacticIntent] = []
    for i, tactic in enumerate(tactics):
        uid = f"u{i}"
        units.append(
            _make_unit(
                uid=uid,
                alive=alive,
                morale_state=morale_state,
                suppression=suppression,
                fatigue=fatigue,
                x=10 + i,
                y=10,
            )
        )
        intents.append(_make_intent(uid, tactic))
    return units, intents


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestPsychologyIntegration:
    """Verify TacticalOrchestrator.tick() Phase 5 psychology filtering."""

    def test_healthy_unit_orders_accepted(self):
        """Healthy units (RALLIED/NONE/FRESH) — all orders preserved."""
        units, intents = _make_units_with_tactics(
            morale_state=MoraleState.RALLIED,
            tactics=[TacticType.ATTACK, TacticType.MOVE_TO, TacticType.DEFEND],
        )
        ctx = _make_context(friendlies=units)
        ai = _StubAI("TestAI", score=0.8, intents=intents)
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        assert len(orders) == 3, f"Expected 3 orders preserved, got {len(orders)}"

    def test_broken_unit_non_survival_orders_rejected(self):
        """BROKEN morale — non-survival orders filtered, survival preserved."""
        units, intents = _make_units_with_tactics(
            morale_state=MoraleState.BROKEN,
            tactics=[
                TacticType.ATTACK,  # non-survival — rejected
                TacticType.RETREAT,  # survival — accepted
                TacticType.MOVE_TO,  # non-survival — rejected
                TacticType.TAKE_COVER,  # survival — accepted
            ],
        )
        ctx = _make_context(friendlies=units)
        ai = _StubAI("TestAI", score=0.8, intents=intents)
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        tactics = {o.tactic_type for o in orders}
        assert TacticType.RETREAT in tactics, "Survival RETREAT must be accepted for BROKEN unit"
        assert TacticType.TAKE_COVER in tactics, "Survival TAKE_COVER must be accepted"
        assert TacticType.ATTACK not in tactics, "ATTACK must be rejected for BROKEN unit"
        assert TacticType.MOVE_TO not in tactics, "MOVE_TO must be rejected for BROKEN unit"
        assert len(orders) == 2, f"Expected 2 survival orders, got {len(orders)}"

    def test_routing_unit_non_survival_orders_rejected(self):
        """ROUTING morale — non-survival orders filtered."""
        units, intents = _make_units_with_tactics(
            morale_state=MoraleState.ROUTING,
            tactics=[
                TacticType.FLANKING,  # non-survival — rejected
                TacticType.SURRENDER,  # survival — accepted
            ],
        )
        ctx = _make_context(friendlies=units)
        ai = _StubAI("TestAI", score=0.8, intents=intents)
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        tactics = {o.tactic_type for o in orders}
        assert TacticType.SURRENDER in tactics, (
            "Survival SURRENDER must be accepted for ROUTING unit"
        )
        assert TacticType.FLANKING not in tactics, "FLANKING must be rejected for ROUTING unit"
        assert len(orders) == 1

    def test_survival_orders_always_accepted(self):
        """All 4 survival commands accepted even for ROUTING unit."""
        units, intents = _make_units_with_tactics(
            morale_state=MoraleState.ROUTING,
            tactics=[
                TacticType.RETREAT,
                TacticType.TAKE_COVER,
                TacticType.SURRENDER,
                TacticType.RALLY_NCO,
            ],
        )
        ctx = _make_context(friendlies=units)
        ai = _StubAI("TestAI", score=0.8, intents=intents)
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        assert len(orders) == 4, f"All 4 survival commands must be accepted, got {len(orders)}"

    def test_dead_unit_orders_rejected(self):
        """Dead unit (is_alive=False) — all orders filtered (Step 1 alive check)."""
        units, intents = _make_units_with_tactics(
            alive=False,
            tactics=[TacticType.ATTACK, TacticType.RETREAT],
        )
        ctx = _make_context(friendlies=units)
        ai = _StubAI("TestAI", score=0.8, intents=intents)
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        assert len(orders) == 0, f"Dead unit must have all orders rejected, got {len(orders)}"

    def test_unit_not_in_context_preserved(self):
        """Unit ID not in context.friendly_units — order preserved (defensive)."""
        unit = _make_unit(uid="u_real")
        ctx = _make_context(friendlies=[unit])
        ai = _StubAI(
            "TestAI",
            score=0.8,
            intents=[
                _make_intent("u_unknown", TacticType.ATTACK),  # unit not in context
            ],
        )
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        assert len(orders) == 1, "Orders for units not in context must be preserved (defensive)"

    def test_mixed_units_partial_filtering(self):
        """Mixed units: healthy preserved, BROKEN filtered (non-survival)."""
        healthy = _make_unit(uid="u_healthy", morale_state=MoraleState.RALLIED)
        broken = _make_unit(uid="u_broken", morale_state=MoraleState.BROKEN)
        ctx = _make_context(friendlies=[healthy, broken])
        ai = _StubAI(
            "TestAI",
            score=0.8,
            intents=[
                _make_intent("u_healthy", TacticType.ATTACK),  # healthy — accepted
                _make_intent("u_broken", TacticType.ATTACK),  # broken — rejected
                _make_intent("u_broken", TacticType.RETREAT),  # broken survival — accepted
            ],
        )
        # Note: u_broken has 2 intents; Phase 3 keeps only the higher-priority one.
        # Both have priority=5, so the first (ATTACK) wins — then psychology rejects it.
        # To test both, we need distinct units. Let's use a third unit for RETREAT.
        broken_retreat = _make_unit(uid="u_broken_retreat", morale_state=MoraleState.BROKEN)
        ctx = _make_context(friendlies=[healthy, broken, broken_retreat])
        ai = _StubAI(
            "TestAI",
            score=0.8,
            intents=[
                _make_intent("u_healthy", TacticType.ATTACK),
                _make_intent("u_broken", TacticType.ATTACK),
                _make_intent("u_broken_retreat", TacticType.RETREAT),
            ],
        )
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        assert len(orders) == 2, f"Expected 2 orders (1 healthy + 1 survival), got {len(orders)}"
        uids = {o.unit_id for o in orders}
        assert "u_healthy" in uids, "Healthy unit's order must be preserved"
        assert "u_broken_retreat" in uids, "Broken unit's survival order must be preserved"

    def test_heavy_suppression_rejects_offensive(self):
        """HEAVY suppression rejects offensive orders (but not defensive)."""
        units, intents = _make_units_with_tactics(
            morale_state=MoraleState.RALLIED,
            suppression=SuppressionEffect.HEAVY,
            tactics=[
                TacticType.ATTACK,  # offensive — rejected by HEAVY supp
                TacticType.DEFEND,  # defensive — accepted (only PANIC rejects)
            ],
        )
        ctx = _make_context(friendlies=units)
        ai = _StubAI("TestAI", score=0.8, intents=intents)
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        tactics = {o.tactic_type for o in orders}
        assert TacticType.DEFEND in tactics, (
            "Defensive order should be accepted under HEAVY suppression"
        )
        assert TacticType.ATTACK not in tactics, (
            "Offensive order must be rejected under HEAVY suppression"
        )

    def test_panic_suppression_rejects_defensive(self):
        """PANIC suppression rejects even defensive orders."""
        units, intents = _make_units_with_tactics(
            morale_state=MoraleState.RALLIED,
            suppression=SuppressionEffect.PANIC,
            tactics=[
                TacticType.DEFEND,  # defensive — rejected by PANIC
                TacticType.TAKE_COVER,  # survival — accepted
            ],
        )
        ctx = _make_context(friendlies=units)
        ai = _StubAI("TestAI", score=0.8, intents=intents)
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        tactics = {o.tactic_type for o in orders}
        assert TacticType.TAKE_COVER in tactics, "Survival order must be accepted under PANIC"
        assert TacticType.DEFEND not in tactics, (
            "Defensive order must be rejected under PANIC suppression"
        )

    def test_empty_intents_returns_empty(self):
        """No intents — tick() returns empty list."""
        unit = _make_unit(uid="u1")
        ctx = _make_context(friendlies=[unit])
        ai = _StubAI("TestAI", score=0.8, intents=[])
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        assert len(orders) == 0

    def test_low_score_ai_skipped(self):
        """AI with score < 0.1 is skipped (Phase 2 threshold)."""
        unit = _make_unit(uid="u1")
        ctx = _make_context(friendlies=[unit])
        ai = _StubAI(
            "LowScoreAI",
            score=0.05,
            intents=[
                _make_intent("u1", TacticType.ATTACK),
            ],
        )
        orch = TacticalOrchestrator()
        orch.register(ai)
        orders = orch.tick(ctx)
        assert len(orders) == 0, "Low-score AI intents must be skipped"
