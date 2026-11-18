"""Integration tests for MC2-03 skill growth (docs/MC2_WAVE2_DESIGN_20261118.md §4).

Covers the full chain CombatDirector.record_stats → VeterancyComponent.skill_stats
(fire-and-miss raises uses, hits raise uses+successes, kills feed the derived rank)
and the campaign persistence read-back of skill_stats (save → load equality).
"""

from __future__ import annotations

import os
from unittest.mock import Mock

import pytest

# Headless pygame (must precede any pygame import)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.veterancy_component import (
    DEFAULT_SKILL,
    VeterancyComponent,
    VeteranSkillStats,
)
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.campaign_state import CampaignState, PersistentUnit
from pycc2.domain.systems.victory_conditions import BattleStats
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.combat_director import CombatDirector


class StubEventBus:
    def subscribe(self, event_type, handler):
        pass

    def publish(self, event):
        pass

    def publish_named(self, name, data):
        pass


def make_unit(unit_id: str, faction: Faction, tile_x: int = 5, tile_y: int = 5) -> Unit:
    """Create a real unit with a live VeterancyComponent."""
    unit = Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=10, ammo_remaining=10),
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(range_tiles=4),
    )
    unit.veterancy = VeterancyComponent()
    return unit


def make_director() -> CombatDirector:
    return CombatDirector(event_bus=StubEventBus(), display_config=Mock())


@pytest.mark.integration
class TestRecordStatsSkillChain:
    """record_stats must feed the shooter's gunnery skill on every shot."""

    def test_miss_raises_uses_only(self):
        director = make_director()
        attacker = make_unit("a1", Faction.ALLIES)
        target = make_unit("e1", Faction.AXIS)
        battle_stats = BattleStats()

        director.record_stats(
            {"attacker_id": "a1", "target_id": "e1", "damage": 0, "killed": False},
            [attacker, target],
            battle_stats,
        )

        stats = attacker.veterancy.skill_stats[DEFAULT_SKILL]
        assert stats.uses == 1
        assert stats.successes == 0
        assert attacker.veterancy.hit_rate == 0.0
        assert battle_stats.shots_fired_allies == 1
        assert battle_stats.shots_hit_allies == 0

    def test_hit_raises_uses_and_successes(self):
        director = make_director()
        attacker = make_unit("a1", Faction.ALLIES)
        target = make_unit("e1", Faction.AXIS)
        battle_stats = BattleStats()

        director.record_stats(
            {"attacker_id": "a1", "target_id": "e1", "damage": 30, "killed": False},
            [attacker, target],
            battle_stats,
        )

        stats = attacker.veterancy.skill_stats[DEFAULT_SKILL]
        assert stats.uses == 1
        assert stats.successes == 1
        assert attacker.veterancy.hit_rate == pytest.approx(1.0)
        assert battle_stats.shots_fired_allies == 1
        assert battle_stats.shots_hit_allies == 1

    def test_kill_feeds_rank_and_legacy_counters(self):
        director = make_director()
        attacker = make_unit("a1", Faction.ALLIES)
        target = make_unit("e1", Faction.AXIS)
        battle_stats = BattleStats()

        director.record_stats(
            {"attacker_id": "a1", "target_id": "e1", "damage": 100, "killed": True},
            [attacker, target],
            battle_stats,
        )

        vc = attacker.veterancy
        assert vc.kills == 1
        assert vc.xp == 15
        assert vc.skill_rank == pytest.approx(min(5.0, 1 * 0.25 + 1.0 * 2.0))
        assert battle_stats.allies_kills == 1

    def test_target_without_veterancy_does_not_break_recording(self):
        director = make_director()
        attacker = make_unit("a1", Faction.ALLIES)
        target = make_unit("e1", Faction.AXIS)
        target.veterancy = None
        battle_stats = BattleStats()

        director.record_stats(
            {"attacker_id": "a1", "target_id": "e1", "damage": 10, "killed": False},
            [attacker, target],
            battle_stats,
        )

        assert attacker.veterancy.skill_stats[DEFAULT_SKILL].uses == 1

    def test_attacker_without_veterancy_is_skipped(self):
        director = make_director()
        attacker = make_unit("a1", Faction.ALLIES)
        attacker.veterancy = None
        target = make_unit("e1", Faction.AXIS)
        battle_stats = BattleStats()

        director.record_stats(
            {"attacker_id": "a1", "target_id": "e1", "damage": 10, "killed": False},
            [attacker, target],
            battle_stats,
        )

        assert battle_stats.shots_fired_allies == 1  # battle stats still recorded


@pytest.mark.integration
class TestVeterancySaveLoadRoundTrip:
    """skill_stats must survive the campaign persistence save/load path."""

    def test_persistent_unit_roundtrip_keeps_skill_stats(self):
        vc = VeterancyComponent(kills=3, xp=45)
        vc.record_shot(hit=True)
        vc.record_shot(hit=True)
        vc.record_shot(hit=False)

        unit = PersistentUnit(
            unit_id="u1",
            name="Squad Tom",
            unit_type="INFANTRY_SQUAD",
            veterancy=vc,
        )
        data = unit.to_dict()
        restored = PersistentUnit.from_dict(data)

        saved = restored.veterancy.skill_stats[DEFAULT_SKILL]
        assert saved.uses == 3
        assert saved.successes == 2
        assert restored.veterancy.hit_rate == pytest.approx(2.0 / 3.0)
        assert restored.veterancy.skill_rank == pytest.approx(vc.skill_rank)
        assert restored.veterancy.kills == 3

    def test_campaign_state_roundtrip_keeps_skill_stats(self):
        state = CampaignState()
        vc = VeterancyComponent()
        vc.record_shot(hit=True)
        state.allied_units.append(
            PersistentUnit(
                unit_id="u2",
                name="Squad Dick",
                unit_type="INFANTRY_SQUAD",
                veterancy=vc,
            )
        )

        data = state.to_dict()
        restored = CampaignState.from_dict(data)

        assert restored.allied_units[0].veterancy.skill_stats[DEFAULT_SKILL].successes == 1
        assert isinstance(
            restored.allied_units[0].veterancy.skill_stats[DEFAULT_SKILL], VeteranSkillStats
        )
