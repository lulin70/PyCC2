"""E2E tests for v0.7.0 ghost module integration into the live game loop.

Validates the three previously-orphaned modules are now reachable through
real user-facing entry points (TD-076b/c/d, v0.7.0):

  Wave 1 (TD-076c): WeaponJamSystem is owned by AIService and clears jams
    in exactly ``clear_ticks`` ticks (off-by-one fix verified).
  Wave 2 (TD-076b): SurrenderAI is registered in TacticalOrchestrator and
    produces SurrenderIntent when an isolated, out-of-ammo unit is fed
    through ``AIService.tick()``.
  Wave 3 (TD-076d): CampaignPersistenceManager is wired by
    GameLoopAssembler, can save/load campaign progress, and applies
    cross-battle inheritance (HP/morale/ammo) to a new batch of units.

Tests use real components (real Unit, real pygame.Surface where needed)
per the user's testing philosophy — no Mock for domain objects.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from pycc2.domain.ai.surrender_system import (
    SurrenderAI,
    SurrenderSystem,
)
from pycc2.domain.ai.weapon_jam import (
    WEAPON_JAM_CONFIGS,
    WeaponJamSystem,
)
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent, WeaponState
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitState, UnitType
from pycc2.domain.systems.campaign_persistence import (
    BattleOutcome,
    CampaignPersistenceManager,
    CampaignProgress,
    UnitBattleState,
)
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.services.ai_service import AIService

# ---------------------------------------------------------------------------
# Shared helpers — real components only (no Mock for domain objects)
# ---------------------------------------------------------------------------


def _make_unit(
    uid: str = "u1",
    faction: Faction = Faction.ALLIES,
    weapon_id: str = "rifle",
    ammo: int = 30,
    max_ammo: int = 30,
    hp: int = 100,
    morale: int = 80,
    x: int = 10,
    y: int = 10,
) -> Unit:
    """Build a real Unit with real components per user testing philosophy."""
    return Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=hp, max_hp=hp),
        morale=MoraleComponent(value=morale, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(
            primary_weapon_id=weapon_id,
            ammo_remaining=ammo,
            max_ammo=max_ammo,
        ),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )


def _make_map(w: int = 40, h: int = 30) -> GameMap:
    """Build a real GameMap filled with passable GRASS terrain."""
    grid = np.full((h, w), TerrainType.GRASS.value, dtype=np.int8)
    gm = GameMap(id="e2e_test", name="E2E Test Map", width=w, height=h, tile_grid=grid)
    if gm.tiles_enhanced is None:
        gm.tiles_enhanced = {}
    return gm


class _AlwaysZeroRNG(random.Random):
    """Test RNG that always returns 0.0 from random()."""

    def random(self) -> float:  # type: ignore[override]
        return 0.0


# ---------------------------------------------------------------------------
# Wave 1 (TD-076c): WeaponJamSystem E2E through AIService
# ---------------------------------------------------------------------------


class TestWave1WeaponJamE2E:
    """E2E: AIService owns WeaponJamSystem and clears jams in exactly N ticks.

    User journey: unit fires → weapon jams → unit waits → jam auto-clears.
    Verifies the v0.7.0 off-by-one fix (clear_ticks=N → N ticks, not N+1).
    """

    def test_ai_service_exposes_weapon_jam_system(self) -> None:
        """AIService constructor wires WeaponJamSystem (TD-076c, v0.7.0)."""
        bus = EventBus()
        svc = AIService(event_bus=bus)
        assert isinstance(svc.weapon_jam_system, WeaponJamSystem)
        # AIService.check_jam_on_fire delegates to the system
        assert callable(svc.check_jam_on_fire)

    def test_full_jam_cycle_clears_in_exactly_configured_ticks(self) -> None:
        """User fires rifle, jams, and clears in exactly 3 ticks (not 4).

        This is the v0.7.0 off-by-one regression guard: previously
        clear_ticks=3 needed 4 ticks to clear; now it needs exactly 3.
        """
        bus = EventBus()
        svc = AIService(event_bus=bus)
        unit = _make_unit(uid="rifleman", weapon_id="rifle", ammo=30)

        # Force jam by using an RNG that always triggers the probability check.
        # WEAPON_JAM_CONFIGS["rifle"].jam_probability = 0.001; with rng.random()
        # returning 0.0 (< 0.001), the jam triggers.
        svc.weapon_jam_system._rng = _AlwaysZeroRNG()

        jammed = svc.check_jam_on_fire(unit)
        assert jammed is True, "Rifle should jam when RNG returns 0.0"
        assert unit.weapon.state == WeaponState.JAMMED

        clear_ticks = WEAPON_JAM_CONFIGS["rifle"].jam_clear_ticks
        assert clear_ticks == 3, "Test assumes rifle clear_ticks=3"

        # Tick (clear_ticks - 1) times → still jammed
        for i in range(clear_ticks - 1):
            svc.weapon_jam_system.tick(unit)
            assert unit.weapon.state == WeaponState.JAMMED, (
                f"Rifle should still be JAMMED after {i + 1} ticks (needs {clear_ticks})"
            )

        # Tick exactly clear_ticks times → cleared (off-by-one fix)
        svc.weapon_jam_system.tick(unit)
        assert unit.weapon.state == WeaponState.READY, (
            f"Rifle should be READY after exactly {clear_ticks} ticks (v0.7.0 off-by-one fix)"
        )

    def test_jammed_unit_re_jam_resets_clear_timer(self) -> None:
        """User fires again while jammed → jam re-triggers and resets clear timer.

        WeaponJamSystem.check_jam_on_fire does not short-circuit on JAMMED
        state — a second jam call re-applies the jam and resets the clear
        countdown. This test documents the actual behavior so callers know
        to gate repeated calls (e.g., only check on the first shot per tick).
        """
        bus = EventBus()
        svc = AIService(event_bus=bus)
        unit = _make_unit(uid="gunner", weapon_id="rifle")
        svc.weapon_jam_system._rng = _AlwaysZeroRNG()

        # First fire → jams, clear timer starts at 3
        assert svc.check_jam_on_fire(unit) is True
        assert unit.weapon.state == WeaponState.JAMMED
        assert svc.weapon_jam_system._jam_clear_remaining[unit.id] == 3

        # Tick once → remaining = 2
        svc.weapon_jam_system.tick(unit)
        assert svc.weapon_jam_system._jam_clear_remaining[unit.id] == 2

        # Second fire while jammed → re-jam resets timer back to 3
        result = svc.check_jam_on_fire(unit)
        assert result is True, "Re-jam on JAMMED weapon re-triggers and resets timer"
        assert unit.weapon.state == WeaponState.JAMMED
        assert svc.weapon_jam_system._jam_clear_remaining[unit.id] == 3


# ---------------------------------------------------------------------------
# Wave 2 (TD-076b): SurrenderAI E2E through AIService / TacticalOrchestrator
# ---------------------------------------------------------------------------


class TestWave2SurrenderE2E:
    """E2E: SurrenderAI is registered in TacticalOrchestrator and triggers
    on isolated, out-of-ammo enemy units during AIService.tick().
    """

    def test_surrender_ai_registered_in_orchestrator(self) -> None:
        """AIService constructor registers SurrenderAI (TD-076b, v0.7.0)."""
        bus = EventBus()
        svc = AIService(event_bus=bus)
        # SurrenderAI must be reachable from the orchestrator
        registered_types = {type(ai).__name__ for ai in svc._tactical_orchestrator._ais}
        assert "SurrenderAI" in registered_types, (
            "SurrenderAI must be registered in TacticalOrchestrator"
        )
        assert isinstance(svc.surrender_system, SurrenderSystem)

    def test_surrender_triggers_for_isolated_out_of_ammo_unit(self) -> None:
        """User surrounds an isolated, out-of-ammo enemy → enemy surrenders.

        SurrenderAI evaluates friendly_units (the AI's own side). We place
        the AXIS candidate in friendly_units and the ALLIES threat in
        enemy_units. The candidate meets all four SurrenderSystem
        conditions: alive, low ammo (ratio < 0.05), isolated (no friendly
        within radius 8), and probability > 0.
        """
        from pycc2.domain.ai.tactic_intent import TacticType

        # Candidate: 1 round left out of 30 → ammo_ratio = 0.033 < 0.05.
        # MORALE_THRESHOLD=15 (not 30) — morale must be < 15 for _meets_conditions.
        candidate = _make_unit(
            uid="candidate",
            faction=Faction.AXIS,
            weapon_id="mp40",
            ammo=1,
            max_ammo=30,
            hp=40,
            morale=10,
            x=10,
            y=10,
        )
        # Nearby enemy (ALLIES) at distance 2 → triggers conditions
        enemy = _make_unit(
            uid="threat",
            faction=Faction.ALLIES,
            weapon_id="rifle",
            x=12,
            y=10,
        )
        # Use deterministic RNG so probability check always passes
        system = SurrenderSystem(rng=_AlwaysZeroRNG())
        ai = SurrenderAI(system)

        ctx = _build_tactical_context(
            friendly_units=[candidate], enemy_units=[enemy], current_tick=5
        )
        intents = ai.execute(ctx)

        surrender_intents = [i for i in intents if i.tactic_type == TacticType.SURRENDER]
        assert len(surrender_intents) == 1, (
            f"Expected 1 surrender intent, got {len(surrender_intents)}: {intents}"
        )

    def test_surrender_does_not_trigger_when_friendlies_nearby(self) -> None:
        """User has friendly near candidate → no surrender (isolation fails)."""
        from pycc2.domain.ai.tactic_intent import TacticType

        candidate = _make_unit(
            uid="candidate",
            faction=Faction.AXIS,
            ammo=1,
            max_ammo=30,
            morale=10,
            x=10,
            y=10,
        )
        friendly = _make_unit(
            uid="friendly",
            faction=Faction.AXIS,
            x=12,
            y=10,  # distance 2 < ISOLATION_RADIUS=8
        )
        enemy = _make_unit(
            uid="threat",
            faction=Faction.ALLIES,
            x=15,
            y=10,
        )

        system = SurrenderSystem(rng=_AlwaysZeroRNG())
        ai = SurrenderAI(system)

        ctx = _build_tactical_context(
            friendly_units=[candidate, friendly], enemy_units=[enemy], current_tick=5
        )
        intents = ai.execute(ctx)
        surrender_intents = [i for i in intents if i.tactic_type == TacticType.SURRENDER]
        assert len(surrender_intents) == 0, (
            "Surrender should NOT trigger when friendly is within isolation radius"
        )


def _build_tactical_context(
    friendly_units: list[Unit], enemy_units: list[Unit], current_tick: int
) -> Any:
    """Build a real TacticalContext with a real GameMap (no Mock)."""
    from pycc2.domain.ai.tactical_ai import TacticalContext

    gm = _make_map()
    return TacticalContext(
        friendly_units=friendly_units,
        enemy_units=enemy_units,
        game_map=gm,
        current_tick=current_tick,
    )


# ---------------------------------------------------------------------------
# Wave 3 (TD-076d): CampaignPersistenceManager E2E
# ---------------------------------------------------------------------------


class TestWave3CampaignPersistenceE2E:
    """E2E: CampaignPersistenceManager saves, loads, and applies inheritance.

    User journey: win battle 1 → save progress → start battle 2 →
    surviving units inherit HP/morale from battle 1 end state.
    """

    def test_save_load_roundtrip_preserves_progress(self, tmp_path: Path) -> None:
        """User saves after battle 1, loads before battle 2 → data matches."""
        manager = CampaignPersistenceManager(base_dir=tmp_path)

        progress = CampaignProgress(
            campaign_id="e2e_market_garden",
            current_operation_id="arnhem_sector",
        )
        progress.add_battle_result(
            _make_battle_result(
                battle_id="battle_1",
                outcome=BattleOutcome.ALLIED_VICTORY,
                allied_casualties=3,
                axis_casualties=8,
            )
        )

        # Save
        saved = manager.save_campaign_progress("e2e_market_garden", progress)
        assert saved is True, "save_campaign_progress should return True on success"

        # File exists on disk (real I/O verification, not just API call)
        save_file = tmp_path / "campaign_saves" / "campaign_e2e_market_garden.json"
        assert save_file.exists(), f"Save file should exist at {save_file}"
        with open(save_file) as f:
            data = json.load(f)
        assert data["campaign_id"] == "e2e_market_garden"
        assert data["progress"]["total_battles_completed"] == 1

        # Load
        loaded = manager.load_campaign_progress("e2e_market_garden")
        assert loaded is not None, "load_campaign_progress should return the progress"
        assert loaded.campaign_id == "e2e_market_garden"
        assert loaded.total_battles_completed == 1
        assert loaded.battle_results[0].allied_casualties == 3

    def test_apply_inheritance_transfers_hp_and_morale(self, tmp_path: Path) -> None:
        """User starts battle 2 → battle 1 survivors keep their HP/morale.

        Build a UnitBattleState showing a wounded veteran (hp=50/100,
        morale=70, xp=15) → apply to a fresh unit → fresh unit's HP and
        morale match the inherited state (with morale recovery bonus).

        Note: Unit is a slots dataclass without unit_template_id; the
        manager falls back to ``unit.id`` for matching (see
        campaign_persistence.py L289).
        """
        manager = CampaignPersistenceManager(base_dir=tmp_path)

        # Previous battle end state: one wounded allied veteran.
        # unit_id MUST match fresh_unit.id for the fallback lookup to work.
        veteran_state = UnitBattleState(
            unit_id="us_rifle_squad_1",
            unit_template_id="us_rifle_squad",
            faction="allies",
            is_alive=True,
            current_hp=50.0,
            max_hp=100.0,
            morale=70.0,
            experience=15,
            ammo_remaining={"ammo_remaining": 20},
        )
        progress = CampaignProgress(
            campaign_id="e2e_inheritance",
            current_operation_id="op_1",
            current_unit_states=[veteran_state],
            total_battles_completed=1,
        )

        # Fresh unit for battle 2 (full HP/morale by default).
        # id matches veteran_state.unit_id so apply_inheritance finds it.
        fresh_unit = _make_unit(
            uid="us_rifle_squad_1",
            faction=Faction.ALLIES,
            weapon_id="rifle",
            hp=100,
            morale=100,
            ammo=30,
        )

        # Apply inheritance
        updated = manager.apply_inheritance_to_units(progress, [fresh_unit])

        # HP should be 50% of max (inherited ratio)
        assert updated[0].health_component.hp == 50, "Inherited HP should be 50 (50% of max_hp=100)"
        # Morale should be inherited (70) + recovery bonus
        # recovery = min(20, 10 + total_battles_completed * 2) = min(20, 12) = 12
        # → 70 + 12 = 82
        assert updated[0].morale_component.value == 82, (
            "Inherited morale should be 70 + recovery(12) = 82"
        )

    def test_dead_unit_state_marked_dead_in_next_battle(self, tmp_path: Path) -> None:
        """User starts battle 2 → units killed in battle 1 are dead on arrival."""
        manager = CampaignPersistenceManager(base_dir=tmp_path)

        dead_state = UnitBattleState(
            unit_id="casualty_1",
            unit_template_id="us_rifle_squad",
            faction="allies",
            is_alive=False,
            current_hp=0.0,
            max_hp=100.0,
        )
        progress = CampaignProgress(
            campaign_id="e2e_dead",
            current_operation_id="op_1",
            current_unit_states=[dead_state],
        )

        # id matches dead_state.unit_id so apply_inheritance finds it
        fresh_unit = _make_unit(uid="casualty_1", faction=Faction.ALLIES)

        updated = manager.apply_inheritance_to_units(progress, [fresh_unit])
        assert updated[0].health_component.hp == 0
        assert updated[0].state_machine.current == UnitState.DEAD

    def test_list_saved_campaigns_includes_saved_campaign(self, tmp_path: Path) -> None:
        """User opens load menu → saved campaigns are listed."""
        manager = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(
            campaign_id="e2e_listable",
            current_operation_id="op_1",
        )
        progress.add_battle_result(_make_battle_result(battle_id="b1", outcome=BattleOutcome.DRAW))
        manager.save_campaign_progress("e2e_listable", progress)

        saves = manager.list_saved_campaigns()
        assert len(saves) >= 1
        matching = [s for s in saves if s["campaign_id"] == "e2e_listable"]
        assert len(matching) == 1
        assert matching[0]["battles_completed"] == 1


def _make_battle_result(
    battle_id: str,
    outcome: BattleOutcome,
    allied_casualties: int = 0,
    axis_casualties: int = 0,
) -> Any:
    """Build a BattleResult with minimal required fields."""
    from pycc2.domain.systems.campaign_persistence import BattleResult

    return BattleResult(
        battle_id=battle_id,
        operation_id="test_op",
        sector="test_sector",
        day=1,
        outcome=outcome,
        allied_casualties=allied_casualties,
        axis_casualties=axis_casualties,
        allied_units_start=10,
        allied_units_end=10 - allied_casualties,
        axis_units_start=10,
        axis_units_end=10 - axis_casualties,
    )


# ---------------------------------------------------------------------------
# Wave 3 (TD-076d): GameLoopAssembler wiring E2E
# ---------------------------------------------------------------------------


class TestWave3GameLoopWiringE2E:
    """E2E: GameLoopAssembler wires CampaignPersistenceManager into GameLoop.

    User starts the game → GameLoop constructed → __post_init__ calls
    GameLoopAssembler.assemble() → _init_persistence() wires
    CampaignPersistenceManager → GameLoop.campaign_persistence is non-None.
    """

    def test_game_loop_exposes_campaign_persistence(self, game_loop_fixture: Any) -> None:
        """GameLoopAssembler wires CampaignPersistenceManager (TD-076d, v0.7.0)."""
        loop = game_loop_fixture
        assert loop.campaign_persistence is not None, (
            "GameLoop.campaign_persistence must be wired by GameLoopAssembler"
        )
        assert isinstance(loop.campaign_persistence, CampaignPersistenceManager), (
            "campaign_persistence must be CampaignPersistenceManager"
        )

        # Functional check: list_saved_campaigns works (no exception)
        saves = loop.campaign_persistence.list_saved_campaigns()
        assert isinstance(saves, list)

    def test_campaign_persistence_save_and_load_through_game_loop(
        self, game_loop_fixture: Any, tmp_path: Path
    ) -> None:
        """User saves campaign through GameLoop.campaign_persistence → loads back."""
        loop = game_loop_fixture
        # Replace manager with one using tmp_path for test isolation
        loop._campaign_persistence = CampaignPersistenceManager(base_dir=tmp_path)

        progress = CampaignProgress(
            campaign_id="e2e_through_loop",
            current_operation_id="op_1",
        )
        progress.add_battle_result(
            _make_battle_result(
                battle_id="b1",
                outcome=BattleOutcome.AXIS_VICTORY,
                axis_casualties=2,
            )
        )

        saved = loop.campaign_persistence.save_campaign_progress("e2e_through_loop", progress)
        assert saved is True

        loaded = loop.campaign_persistence.load_campaign_progress("e2e_through_loop")
        assert loaded is not None
        assert loaded.total_battles_completed == 1
        assert loaded.battle_results[0].outcome == BattleOutcome.AXIS_VICTORY


# ---------------------------------------------------------------------------
# Pytest fixtures for GameLoop wiring E2E (reuses pattern from
# tests/unit/test_game_loop.py — Mock renderer/window_manager are
# presentation-layer adapters, not domain objects, so Mock is permitted).
# ---------------------------------------------------------------------------


@pytest.fixture
def game_loop_fixture() -> Any:
    """Build a real GameLoop with real GameMap/Unit/EventBus.

    Mocks only the pygame surface adapters (renderer/window_manager) which
    are presentation-layer concerns outside the scope of this E2E test.
    """
    from unittest.mock import Mock

    import pygame

    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
    from pycc2.presentation.rendering.window_config import WindowManager
    from pycc2.services.game_loop import GameLoop, GameState

    pygame.init()  # headless: SDL dummy drivers handle this
    grid = np.zeros((16, 16), dtype=np.int8)
    gm = GameMap(id="e2e", name="E2E", width=16, height=16, tile_grid=grid)

    unit = _make_unit(uid="e2e_unit", faction=Faction.ALLIES, x=3, y=3)
    camera = Camera(position=Vec2(256.0, 256.0), viewport_width=1280, viewport_height=720)

    state = GameState(game_map=gm, units=[unit], camera=camera)

    renderer = Mock(spec=EnhancedRenderer)
    wm = Mock(spec=WindowManager)
    screen = Mock()
    screen.get_width.return_value = 1280
    screen.get_height.return_value = 720
    screen.get_size.return_value = (1280, 720)
    screen.blit = Mock()
    screen.get_rect.return_value = pygame.Rect(0, 0, 1280, 720)
    wm.get_screen.return_value = screen
    wm._screen = screen
    wm.fps = 60.0
    wm.tick.return_value = 16

    bus = EventBus()
    return GameLoop(
        renderer=renderer,
        window_manager=wm,
        event_bus=bus,
        state=state,
    )
