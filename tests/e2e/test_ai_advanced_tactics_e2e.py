"""E2E tests for AI advanced tactics (TC-070~078).

Validates FlankingAI, SuppressionAI, VictoryPointAI, RetreatDecisionAI,
PerceptionSystem, and DifficultySystem at the tactical-intent level.
Complements test_ai_integration_e2e.py (which verifies registration) by
exercising each AI's evaluate()/execute() with real units and a real
GameMap loaded from data/maps/.

Coverage (场景七 AI 高级战术):
  - TC-070: AI flanking behavior (FlankingAI)
  - TC-071: AI suppression fire (SuppressionAI)
  - TC-072: AI VP capture (VictoryPointAI)
  - TC-073/TC-074: AI difficulty Green vs Veteran (DifficultySystem)
  - TC-075: AI retreat logic (RetreatDecisionAI)
  - TC-077: AI perception system (PerceptionSystem + fog_of_war)
  - TC-078: AI unit diversity (type-specific tactic selection)
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import pytest
from conftest import GameLoopFactory

from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.difficulty_system import DifficultyLevel, DifficultySystem
from pycc2.domain.ai.perception_system import PerceptionSystem
from pycc2.domain.ai.retreat_ai import RetreatDecisionAI
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.tactical_ai_types import TacticalContext
from pycc2.domain.ai.tactical_coordination import VictoryPointAI
from pycc2.domain.ai.tactical_flanking import FlankingAI
from pycc2.domain.ai.tactical_suppression import SuppressionAI
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord

# ---------------------------------------------------------------------------
# Unit factory — mirrors test_ai_behaviors_e2e._make_unit
# ---------------------------------------------------------------------------


def _make_unit(
    unit_id: str = "u",
    name: str = "Unit",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 80,
    ammo: int = 10,
    max_ammo: int = 10,
    weapon_id: str = "rifle",
    x: int = 5,
    y: int = 5,
) -> Unit:
    """Create a fully-wired Unit for tactical AI tests."""
    return Unit(
        id=unit_id,
        name=name,
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale),
        weapon=WeaponComponent(
            primary_weapon_id=weapon_id,
            ammo_remaining=ammo,
            max_ammo=max_ammo,
        ),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=5),
    )


# ===========================================================================
# TEST SUITE
# ===========================================================================


class TestAIAdvancedTacticsE2E:
    """E2E tests for AI advanced tactical behaviors (TC-070~078)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize headless pygame for each test."""
        import pygame

        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        yield
        pygame.quit()

    def _factory(self):
        return GameLoopFactory(self.screen)

    # ---------- TC-070: AI flanking behavior ----------

    def test_ai_flanking_behavior(self):
        """FlankingAI produces pinning (SUPPRESS_FIRE) and flanking intents.

        With >=2 mobile infantry units and >=1 enemy, execute() must return
        a non-empty intent list.  The pinning force always emits
        SUPPRESS_FIRE; the flanking force emits FLANKING when the
        destination passes validation (passable + concealment + cover).
        """
        f = self._factory()
        try:
            # Verify FlankingAI is registered in the live orchestrator
            registered = f.ai_service._tactical_orchestrator.registered_ais
            assert "FlankingAI" in registered

            friendly = [
                _make_unit("f1", faction=Faction.AXIS, x=3, y=5),
                _make_unit("f2", faction=Faction.AXIS, x=4, y=5),
                _make_unit("f3", faction=Faction.AXIS, x=5, y=5),
            ]
            enemy = [_make_unit("e1", faction=Faction.ALLIES, x=10, y=5)]
            context = TacticalContext(
                friendly_units=friendly,
                enemy_units=enemy,
                game_map=f.game_map,
                current_tick=0,
            )
            ai = FlankingAI()
            score = ai.evaluate(context)
            assert score > 0.0, "FlankingAI should score >0 with 3 infantry vs 1 enemy"

            intents = ai.execute(context)
            assert len(intents) > 0, "FlankingAI must emit intents"
            # Pinning force emits SUPPRESS_FIRE; flanking force emits FLANKING
            for intent in intents:
                assert intent.tactic_type in (
                    TacticType.FLANKING,
                    TacticType.SUPPRESS_FIRE,
                )
        finally:
            f.shutdown()

    # ---------- TC-071: AI suppression fire ----------

    def test_ai_suppression_fire(self):
        """SuppressionAI assigns MG units to suppress high-threat enemies.

        With an MG unit and visible enemies, execute() must return
        SUPPRESS_FIRE intents targeting enemy unit IDs.
        """
        f = self._factory()
        try:
            assert "SuppressionAI" in f.ai_service._tactical_orchestrator.registered_ais

            mg = _make_unit(
                "mg1",
                faction=Faction.AXIS,
                unit_type=UnitType.MACHINE_GUN_SQUAD,
                weapon_id="mg42",
                x=3,
                y=5,
            )
            enemy = [
                _make_unit("e1", faction=Faction.ALLIES, x=8, y=5),
                _make_unit("e2", faction=Faction.ALLIES, x=9, y=7),
            ]
            context = TacticalContext(
                friendly_units=[mg],
                enemy_units=enemy,
                game_map=f.game_map,
                current_tick=0,
            )
            ai = SuppressionAI()
            score = ai.evaluate(context)
            assert score > 0.0, "SuppressionAI should score >0 with MG + enemies"

            intents = ai.execute(context)
            assert len(intents) > 0
            assert all(i.tactic_type == TacticType.SUPPRESS_FIRE for i in intents)
            assert all(i.target_unit_id is not None for i in intents)
        finally:
            f.shutdown()

    # ---------- TC-072: AI VP capture ----------

    def test_ai_vp_capture(self):
        """VictoryPointAI issues CAPTURE_VL intents for uncontrolled VLs.

        With an uncontrolled VL and a friendly unit > CAPTURE_RADIUS (3)
        tiles away, execute() must return at least one CAPTURE_VL intent
        targeting the VL position.
        """
        f = self._factory()
        try:
            assert "VictoryPointAI" in f.ai_service._tactical_orchestrator.registered_ais

            friendly = [_make_unit("f1", faction=Faction.AXIS, x=3, y=3)]
            # vl_positions: (position, owner_faction_name_or_None, point_value)
            vl_pos = TileCoord(15, 15)
            vls = [(vl_pos, None, 50)]
            context = TacticalContext(
                friendly_units=friendly,
                enemy_units=[],
                game_map=f.game_map,
                current_tick=0,
                vl_positions=vls,
            )
            ai = VictoryPointAI()
            score = ai.evaluate(context)
            assert score > 0.0, "VictoryPointAI should score >0 with uncontrolled VL"

            intents = ai.execute(context)
            assert len(intents) > 0, "Must emit capture intent for uncontrolled VL"
            capture_intents = [i for i in intents if i.tactic_type == TacticType.CAPTURE_VL]
            assert len(capture_intents) >= 1
            assert capture_intents[0].target_position == vl_pos
        finally:
            f.shutdown()

    # ---------- TC-073 / TC-074: AI difficulty Green vs Veteran ----------

    def test_ai_difficulty_green_vs_veteran(self):
        """DifficultySystem PRESETS differentiate Green (EASY) vs Veteran.

        EASY (Green/Conscript): no flanking, no suppression tactics, low
        aggressiveness (0.2), low base_hit_chance (0.25).
        VETERAN: flanking + suppression enabled, high aggressiveness (0.9),
        high base_hit_chance (0.75).

        Also verifies FlankingAI.evaluate returns 0.0 when difficulty
        disables flanking (EASY), and >0 when enabled (VETERAN).
        v0.8.0 completed AI difficulty scaling 9/9.
        """
        easy = DifficultySystem.PRESETS[DifficultyLevel.EASY]
        veteran = DifficultySystem.PRESETS[DifficultyLevel.VETERAN]

        # Green (EASY) — limited tactics
        assert easy.use_flanking is False
        assert easy.use_suppression_tactics is False
        assert easy.aggressiveness == pytest.approx(0.2)
        assert easy.base_hit_chance == pytest.approx(0.25)

        # Veteran — full tactics
        assert veteran.use_flanking is True
        assert veteran.use_suppression_tactics is True
        assert veteran.aggressiveness == pytest.approx(0.9)
        assert veteran.base_hit_chance == pytest.approx(0.75)

        # Veteran is strictly more aggressive
        assert veteran.aggressiveness > easy.aggressiveness
        assert veteran.base_hit_chance > easy.base_hit_chance

        # Behavioural difference: FlankingAI returns 0 when flanking disabled
        f = self._factory()
        try:
            friendly = [
                _make_unit("f1", faction=Faction.AXIS, x=3, y=5),
                _make_unit("f2", faction=Faction.AXIS, x=4, y=5),
            ]
            enemy = [_make_unit("e1", faction=Faction.ALLIES, x=10, y=5)]

            ctx_easy = TacticalContext(
                friendly_units=friendly,
                enemy_units=enemy,
                game_map=f.game_map,
                current_tick=0,
                difficulty_config=easy,
            )
            ctx_veteran = TacticalContext(
                friendly_units=friendly,
                enemy_units=enemy,
                game_map=f.game_map,
                current_tick=0,
                difficulty_config=veteran,
            )
            ai = FlankingAI()
            assert ai.evaluate(ctx_easy) == 0.0, "EASY difficulty must disable flanking"
            assert ai.evaluate(ctx_veteran) > 0.0, "VETERAN difficulty enables flanking"
        finally:
            f.shutdown()

    # ---------- TC-075: AI retreat behavior ----------

    def test_ai_retreat_behavior(self):
        """RetreatDecisionAI retreats low-HP units when outnumbered.

        With an unfavorable force ratio (1 friendly vs 3 enemies) and a
        low-HP unit (hp_ratio < 0.5), execute() must return RETREAT
        intents.  evaluate() must return a high priority score (>=0.7).
        """
        f = self._factory()
        try:
            assert "RetreatDecisionAI" in f.ai_service._tactical_orchestrator.registered_ais

            weak = _make_unit(
                "weak1",
                faction=Faction.AXIS,
                hp=20,
                max_hp=100,  # hp_ratio = 0.2 < LOW_HP_RATIO (0.5)
                morale=50,
                x=3,
                y=5,
            )
            enemies = [
                _make_unit("e1", faction=Faction.ALLIES, x=8, y=5),
                _make_unit("e2", faction=Faction.ALLIES, x=9, y=5),
                _make_unit("e3", faction=Faction.ALLIES, x=10, y=5),
            ]
            context = TacticalContext(
                friendly_units=[weak],
                enemy_units=enemies,
                game_map=f.game_map,
                current_tick=0,
            )
            ai = RetreatDecisionAI()
            score = ai.evaluate(context)
            # Force ratio = 1/3 ≈ 0.33 < 0.5 → base >= 0.7
            assert score >= 0.7, f"Retreat priority should be high when outnumbered: {score}"

            intents = ai.execute(context)
            retreat_intents = [i for i in intents if i.tactic_type == TacticType.RETREAT]
            assert len(retreat_intents) >= 1, "Weak unit must get RETREAT intent"
            assert retreat_intents[0].unit_id == "weak1"
            assert retreat_intents[0].target_position is not None
        finally:
            f.shutdown()

    # ---------- TC-077: AI perception system ----------

    def test_ai_perception_system(self):
        """PerceptionSystem populates blackboard with sensed combat data.

        With fog_of_war hiding one enemy, the blackboard's visible_enemies
        must only include the visible enemy.  Also verifies allies_nearby
        counting and health_ratio population.
        """
        f = self._factory()
        try:
            observer = _make_unit("obs", faction=Faction.AXIS, x=5, y=5)
            visible_enemy = _make_unit("ve", faction=Faction.ALLIES, x=7, y=5)
            hidden_enemy = _make_unit("he", faction=Faction.ALLIES, x=9, y=5)
            ally = _make_unit("ally1", faction=Faction.AXIS, x=6, y=5)

            bb = Blackboard()
            ps = PerceptionSystem()

            # fog_of_war: reveal visible_enemy, hide hidden_enemy
            fog = {
                (
                    visible_enemy.position.tile_coord.x,
                    visible_enemy.position.tile_coord.y,
                ): True,
                (
                    hidden_enemy.position.tile_coord.x,
                    hidden_enemy.position.tile_coord.y,
                ): False,
            }
            # game_map=None skips LOS check — pure fog_of_war test
            ps.update_blackboard(
                blackboard=bb,
                unit=observer,
                game_map=None,
                all_units=[observer, visible_enemy, hidden_enemy, ally],
                fog_of_war=fog,
            )
            visible = bb.get("visible_enemies", [])
            assert "ve" in visible, "Visible enemy should be sensed"
            assert "he" not in visible, "Hidden enemy should NOT be sensed"

            # allies_nearby counts friendlies within 5 tiles
            assert bb.get("allies_nearby") == 1

            # health_ratio is populated from observer
            assert bb.get("health_ratio") == observer.health.hp_ratio
        finally:
            f.shutdown()

    # ---------- TC-078: AI unit diversity ----------

    def test_ai_unit_diversity(self):
        """Different unit types receive different tactic assignments.

        FlankingAI._mobile_units only selects infantry types
        (INFANTRY_SQUAD, COMMANDER, SNIPER_TEAM, MEDIC_TEAM).
        SuppressionAI._mg_units only selects MACHINE_GUN_SQUAD.
        This verifies the AI treats unit types differently — a core CC2
        tactical distinction.
        """
        f = self._factory()
        try:
            infantry = _make_unit(
                "inf1",
                faction=Faction.AXIS,
                unit_type=UnitType.INFANTRY_SQUAD,
                x=3,
                y=5,
            )
            mg = _make_unit(
                "mg1",
                faction=Faction.AXIS,
                unit_type=UnitType.MACHINE_GUN_SQUAD,
                weapon_id="mg42",
                x=4,
                y=5,
            )
            sniper = _make_unit(
                "snp1",
                faction=Faction.AXIS,
                unit_type=UnitType.SNIPER_TEAM,
                x=5,
                y=5,
            )
            enemy = [_make_unit("e1", faction=Faction.ALLIES, x=10, y=5)]
            context = TacticalContext(
                friendly_units=[infantry, mg, sniper],
                enemy_units=enemy,
                game_map=f.game_map,
                current_tick=0,
            )

            # FlankingAI selects infantry + sniper (NOT MG)
            mobile = FlankingAI._mobile_units(context)
            mobile_ids = {u.id for u in mobile}
            assert "inf1" in mobile_ids
            assert "snp1" in mobile_ids
            assert "mg1" not in mobile_ids, "MG should not be a flanking unit"

            # SuppressionAI selects only MG
            mg_units = SuppressionAI._mg_units(context)
            mg_ids = {u.id for u in mg_units}
            assert mg_ids == {"mg1"}, f"Only MG should suppress: {mg_ids}"
        finally:
            f.shutdown()
