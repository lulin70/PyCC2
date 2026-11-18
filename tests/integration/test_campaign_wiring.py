"""MC2-06 integration tests: campaign persistence wiring in the game loop.

Covers the three wiring points of design §3 with a real
CampaignPersistenceManager (tmp_path base_dir):
1. victory → BattleResult built from state.units → save_campaign_progress;
2. next-task deployment → replay of hp/morale/xp/kills/ammo + fallen removal;
3. deployment RP drawn from CampaignProgress (campaign only);
4. skirmish loops (no campaign context) stay fully bypassed.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

# Headless pygame (must precede any pygame import)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.campaign_persistence import (
    BattleOutcome,
    CampaignPersistenceManager,
    CampaignProgress,
    UnitBattleState,
)
from pycc2.domain.systems.victory_conditions import GameResult, Objective
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.deployment_manager import DeploymentManager
from pycc2.services.game_loop import GameLoop
from pycc2.services.game_loop_updating import GameLoopUpdatingMixin

CAMPAIGN_ID = "wave3_test_campaign"


def _make_unit(
    unit_id: str,
    faction: Faction,
    tile: tuple[int, int],
    template_id: str,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 75,
    alive: bool = True,
) -> Unit:
    if not alive:
        hp = 0
    unit = Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale),
        weapon=WeaponComponent(
            primary_weapon_id="rifle",
            max_ammo=120,
            ammo_remaining=120,
            reserve_ammo=240,
        ),
        position=PositionComponent(tile_coord=TileCoord(*tile)),
        vision=VisionComponent(range_tiles=5),
    )
    unit.template_id = template_id
    return unit


class StubBattleStats:
    def __init__(self, allies_lost=0, axis_lost=0):
        self.allies_units_lost = allies_lost
        self.axis_units_lost = axis_lost


class StubVictoryManager:
    def __init__(self, stats=None, objectives=None):
        self.battle_stats = stats
        self._victory_evaluator = SimpleNamespace(objectives=objectives or [])


class StubLoop(GameLoopUpdatingMixin):
    """Minimal loop facade carrying only what the MC2-06 methods touch."""

    def __init__(self, units, persistence, campaign_id, victory_manager=None, scenario=None):
        self.state = SimpleNamespace(units=list(units), tick=1234, paused=False)
        self._campaign_persistence = persistence
        self._campaign_id = campaign_id
        self._victory_manager = victory_manager or StubVictoryManager()
        self._scenario_data = scenario or {}
        self.ai_service = None


@pytest.fixture
def manager(tmp_path):
    return CampaignPersistenceManager(base_dir=tmp_path)


@pytest.mark.integration
class TestVictoryPersistence:
    def test_victory_builds_battle_result_and_saves(self, manager):
        units = [
            _make_unit("a1", Faction.ALLIES, (3, 3), "us_infantry_squad", hp=70, morale=55),
            _make_unit("a2", Faction.BRITISH, (4, 3), "uk_para_officer", hp=100),
            _make_unit("x1", Faction.AXIS, (8, 8), "de_grw50_team", alive=False),
        ]
        units[0].veterancy.record_kill(xp_reward=30)
        units[1].weapon.ammo_remaining = 60
        units[1].weapon.reserve_ammo = 90

        stats = StubBattleStats(allies_lost=0, axis_lost=1)
        objectives = [
            Objective(id="vl_a", name="VL A", position=(3, 3), points=120, owner="allies"),
            Objective(id="vl_b", name="VL B", position=(8, 8), points=80, owner="axis"),
        ]
        loop = StubLoop(
            units,
            manager,
            CAMPAIGN_ID,
            victory_manager=StubVictoryManager(stats, objectives),
            scenario={"operation_id": "op_landing", "sector": "sector_1", "day": 2},
        )

        loop._persist_campaign_battle(GameResult.ALLIES_VICTORY)

        progress = manager.load_campaign_progress(CAMPAIGN_ID)
        assert progress is not None
        assert progress.total_battles_completed == 1
        assert len(progress.battle_results) == 1

        result = progress.battle_results[0]
        assert result.outcome == BattleOutcome.ALLIED_VICTORY
        assert result.operation_id == "op_landing"
        assert result.sector == "sector_1"
        assert result.day == 2
        assert result.duration_ticks == 1234
        assert result.allied_units_start == 2
        assert result.allied_units_end == 2
        assert result.axis_units_start == 1
        assert result.axis_units_end == 0
        assert result.allied_casualties == 0
        assert result.axis_casualties == 1
        assert result.allied_vp_earned == 120
        assert result.axis_vp_earned == 80

        # Unit states synced from the roster (add_battle_result copies them).
        states = {(s.unit_template_id, s.faction): s for s in progress.current_unit_states}
        a1 = states[("us_infantry_squad", "allies")]
        assert a1.is_alive is True
        assert a1.status == "active"
        assert a1.current_hp == 70.0
        assert a1.max_hp == 100.0
        assert a1.morale == 55.0
        assert a1.experience == 30
        assert a1.kills == 1
        assert a1.ammo_remaining == {"ammo_remaining": 120, "reserve_ammo": 240}

        x1 = states[("de_grw50_team", "axis")]
        assert x1.is_alive is False
        assert x1.status == "dead"

    def test_draw_maps_to_draw_outcome(self, manager):
        loop = StubLoop([], manager, CAMPAIGN_ID)
        loop._persist_campaign_battle(GameResult.TIME_OUT)
        progress = manager.load_campaign_progress(CAMPAIGN_ID)
        assert progress.battle_results[0].outcome == BattleOutcome.DRAW

    def test_missing_battle_stats_derives_casualties_from_roster(self, manager):
        units = [
            _make_unit("a1", Faction.ALLIES, (3, 3), "us_infantry_squad"),
            _make_unit("x1", Faction.AXIS, (8, 8), "de_grw50_team", alive=False),
        ]
        loop = StubLoop(units, manager, CAMPAIGN_ID)  # no battle stats
        loop._persist_campaign_battle(GameResult.ALLIES_VICTORY)
        progress = manager.load_campaign_progress(CAMPAIGN_ID)
        assert progress.battle_results[0].axis_casualties == 1
        assert progress.battle_results[0].allied_casualties == 0


@pytest.mark.integration
class TestVictoryUpdateWiring:
    def _wired_loop(self, units, persistence, campaign_id):
        loop = StubLoop(units, persistence, campaign_id)
        loop.event_bus = SimpleNamespace(
            publish_named=lambda name, data: loop.published.append((name, data))
        )
        loop.published = []
        loop.sound_system = None
        loop._victory_manager = StubVictoryManager()
        loop._victory_manager.evaluate = Mock(return_value=(GameResult.ALLIES_VICTORY, "won"))
        return loop

    def test_update_victory_persists_for_campaign(self, manager):
        loop = self._wired_loop(
            [_make_unit("a1", Faction.ALLIES, (3, 3), "us_infantry_squad")], manager, CAMPAIGN_ID
        )
        loop._update_victory()

        assert loop.state.paused is True
        assert loop.published[0][0] == "BattleWon"
        assert manager.load_campaign_progress(CAMPAIGN_ID) is not None

    def test_update_victory_skips_skirmish(self, manager):
        loop = self._wired_loop(
            [_make_unit("a1", Faction.ALLIES, (3, 3), "us_infantry_squad")], manager, None
        )
        loop._update_victory()

        assert loop.state.paused is True
        assert loop.published[0][0] == "BattleWon"
        # No campaign context → no save file written.
        assert manager.list_saved_campaigns() == []

    def test_persistence_failure_does_not_break_victory(self, manager):
        loop = self._wired_loop(
            [_make_unit("a1", Faction.ALLIES, (3, 3), "us_infantry_squad")], manager, CAMPAIGN_ID
        )
        loop._campaign_persistence = Mock(wraps=manager)
        loop._campaign_persistence.load_campaign_progress.side_effect = RuntimeError("boom")
        loop._update_victory()

        # Victory flow completes despite the persistence error.
        assert loop.state.paused is True
        assert loop.published[0][0] == "BattleWon"


@pytest.mark.integration
class TestDeploymentReplay:
    def _progress_with_history(self, manager):
        progress = CampaignProgress(campaign_id=CAMPAIGN_ID, current_operation_id="op_landing")
        progress.current_unit_states = [
            UnitBattleState(
                unit_id="a1",
                unit_template_id="us_infantry_squad",
                faction="allies",
                is_alive=True,
                current_hp=40.0,
                max_hp=100.0,
                morale=30.0,
                experience=120,
                ammo_remaining={"ammo_remaining": 4, "reserve_ammo": 8},
                kills=3,
            ),
            UnitBattleState(
                unit_id="a2",
                unit_template_id="us_at_team",
                faction="allies",
                is_alive=False,
                current_hp=0.0,
                status="dead",
            ),
        ]
        assert manager.save_campaign_progress(CAMPAIGN_ID, progress)

    def test_replay_applies_survivors_and_removes_fallen(self, manager):
        self._progress_with_history(manager)
        units = [
            _make_unit("fresh_1", Faction.ALLIES, (3, 3), "us_infantry_squad"),
            _make_unit("fresh_2", Faction.ALLIES, (4, 3), "us_at_team"),
            _make_unit("fresh_3", Faction.ALLIES, (5, 3), "uk_6pdr_at_gun"),
        ]
        loop = StubLoop(units, manager, CAMPAIGN_ID)
        loop.ai_service = SimpleNamespace(unregistered=[], unregister_ai_unit=self._record(loop))

        GameLoop._replay_campaign_unit_states(loop)

        # Fallen template removed from the roster and unregistered from AI.
        remaining_ids = [u.id for u in loop.state.units]
        assert remaining_ids == ["fresh_1", "fresh_3"]
        assert loop.ai_service.unregistered == ["fresh_2"]

        # Survivor replayed: hp / morale / xp / kills / ammo.
        survivor = loop.state.units[0]
        assert survivor.health.hp == 40
        assert survivor.health.state.name == "WOUNDED"
        assert survivor.morale.value == 30
        assert survivor.veterancy.xp == 120
        assert survivor.veterancy.kills == 3
        assert survivor.veterancy.rank.name == "REGULAR"
        assert survivor.weapon.ammo_remaining == 4
        assert survivor.weapon.reserve_ammo == 8

        # Unmatched template untouched (new-task roster keeps fresh values).
        untouched = loop.state.units[1]
        assert untouched.health.hp == 100
        assert untouched.veterancy.xp == 0

    @staticmethod
    def _record(loop):
        def _unregister(unit_id):
            loop.ai_service.unregistered.append(unit_id)

        return _unregister

    def test_replay_skips_without_campaign_context(self, manager):
        self._progress_with_history(manager)
        units = [_make_unit("fresh_1", Faction.ALLIES, (3, 3), "us_infantry_squad")]
        loop = StubLoop(units, manager, None)

        GameLoop._replay_campaign_unit_states(loop)

        assert len(loop.state.units) == 1
        assert loop.state.units[0].health.hp == 100


@pytest.mark.integration
class TestDeploymentCampaignRP:
    def test_start_uses_campaign_rp_when_provided(self):
        manager_ = DeploymentManager()
        ui = SimpleNamespace(start_deployment_with_settings=Mock(return_value=None))
        manager_.start(
            map_data={},
            faction="ally",
            deployment_ui=ui,
            campaign_rp=777,
        )
        kwargs = ui.start_deployment_with_settings.call_args.kwargs
        assert kwargs["requisition_points"] == 777

    def test_start_keeps_skirmish_base_rp_without_campaign_rp(self):
        manager_ = DeploymentManager()
        ui = SimpleNamespace(start_deployment_with_settings=Mock(return_value=None))
        manager_.start(map_data={}, faction="ally", deployment_ui=ui)
        kwargs = ui.start_deployment_with_settings.call_args.kwargs
        # Default scenario (no deployment zones) → allies are the attacker → 2400.
        assert kwargs["requisition_points"] == 2400

    def test_campaign_start_rp_reads_progress(self, manager):
        progress = CampaignProgress(campaign_id=CAMPAIGN_ID, current_operation_id="op_landing")
        progress.requisition_points_allies = 888
        progress.requisition_points_axis = 444
        manager.save_campaign_progress(CAMPAIGN_ID, progress)

        loop = StubLoop([], manager, CAMPAIGN_ID)
        assert GameLoop._campaign_start_rp(loop, "ally") == 888
        assert GameLoop._campaign_start_rp(loop, "German") == 444

    def test_campaign_start_rp_none_for_skirmish(self, manager):
        loop = StubLoop([], manager, None)
        assert GameLoop._campaign_start_rp(loop, "ally") is None

    def test_campaign_start_rp_none_without_saved_progress(self, manager):
        loop = StubLoop([], manager, CAMPAIGN_ID)
        assert GameLoop._campaign_start_rp(loop, "ally") is None


@pytest.mark.integration
class TestGameMapFixtureSanity:
    def test_game_map_grid_usable(self):
        grid = np.zeros((16, 16), dtype=np.int8)
        game_map = GameMap(id="m", name="M", width=16, height=16, tile_grid=grid)
        assert game_map.width == 16
