"""Integration tests: MC2-02 trigger migration is behavior-preserving.

Each test runs a verbatim copy of the pre-migration inline block (the
"reference" implementation, copied from game_loop_updating.py before the
MC2-02 migration) on one stub loop, and the migrated TriggerSystem-backed
thin delegate on a structurally identical twin loop, then asserts that both
produce the same observable state (对照断言).
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

# Headless pygame guard — the GameLoop wiring test pulls in pygame.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.scenario_rules import ScenarioRules
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.game_loop import GameLoop
from pycc2.services.game_loop_updating import GameLoopUpdatingMixin, _is_armor_unit

# ============================================================================
# Reference implementations — verbatim copies of the pre-migration inline code
# ============================================================================


def _reference_update_reinforcements(loop) -> None:
    """Pre-migration _update_reinforcements body (game_loop_updating.py @ :166-200)."""
    service = loop._reinforcement_service
    manager = getattr(loop, "_deployment_manager", None)
    if service is None or manager is None:
        return
    if loop.state.game_map is None:
        return

    rules = getattr(loop, "_scenario_rules", None)
    allowed_sides: set[str] | None = None
    max_per_side: int | None = None
    if rules is not None:
        if rules.has("lz_must_hold_for_reinforcements"):
            lz_ids = GameLoop._matching_vl_ids(loop, "lz", "landing")
            owners = GameLoop._vl_owner_map(loop)
            if lz_ids and not any(owners.get(vl) == "allies" for vl in lz_ids):
                allowed_sides = {"axis"}
        if rules.has("limited_reinforcements"):
            max_per_side = 2

    try:
        service.update(
            tick=loop.state.tick,
            units=loop.state.units,
            game_map=loop.state.game_map,
            factory=manager.create_reinforcement_unit,
            allowed_sides=allowed_sides,
            max_per_side=max_per_side,
        )
    except Exception:
        return


def _reference_update_logistics(loop) -> None:
    """Pre-migration _update_logistics body (game_loop_updating.py @ :202-264)."""
    loop._logistics_counter += 1
    if loop._logistics_counter < 60:
        return
    loop._logistics_counter = 0

    spawn_points = loop._scenario_data.get("spawn_points", []) if loop._scenario_data else []
    if not spawn_points:
        return

    rules = getattr(loop, "_scenario_rules", None)
    air_level = getattr(loop.state, "air_support_level", "full")
    if rules is not None and rules.has("corridor_must_remain_open"):
        corridor_ids = GameLoop._matching_vl_ids(
            loop, "corridor", "road", "junction", "highway", "crossroads"
        )
        owners = GameLoop._vl_owner_map(loop)
        if corridor_ids and any(owners.get(vl) == "axis" for vl in corridor_ids):
            return

    for unit in loop.state.units:
        if not getattr(unit, "is_alive", False):
            continue
        weapon = getattr(unit, "weapon", None)
        reserve = getattr(weapon, "reserve_ammo", -2)
        if weapon is None or reserve < 0:
            continue

        faction_name = getattr(getattr(unit, "faction", None), "name", "")
        unit_side = (
            "allies" if faction_name in ("ALLIES", "AMERICAN", "BRITISH", "POLISH") else "axis"
        )
        pos = unit.position.tile_coord
        near = any(
            sp.get("side") == unit_side
            and abs(int(sp.get("position", [0, 0])[0]) - pos.x)
            + abs(int(sp.get("position", [0, 0])[1]) - pos.y)
            <= 3
            for sp in spawn_points
            if isinstance(sp, dict)
        )
        if not near:
            continue

        amount = max(1, weapon.max_ammo // 10)
        if rules is not None and rules.has("supply_dwindling"):
            amount = int(amount * getattr(loop, "_supply_decay", 1.0))
        if unit_side == "allies":
            if air_level == "none":
                continue
            if air_level == "limited":
                amount //= 2
        if amount <= 0:
            continue

        cap = weapon.max_ammo * 2
        if weapon.reserve_ammo < cap:
            weapon.reserve_ammo = min(cap, weapon.reserve_ammo + amount)

    if rules is not None and rules.has("supply_dwindling"):
        loop._supply_decay = max(0.0, getattr(loop, "_supply_decay", 1.0) * 0.85)


def _reference_update_scenario_effects(loop) -> None:
    """Pre-migration _update_scenario_effects body (game_loop_updating.py @ :266-300)."""
    rules = getattr(loop, "_scenario_rules", None)
    if rules is None or not rules.rules:
        return
    units = loop.state.units

    if rules.has("fanatic_defenders"):
        for unit in units:
            if unit.is_alive and unit.faction.name == "AXIS" and unit.morale.value < 30:
                unit.morale.value = 30

    if not rules.has("combined_arms_bonus"):
        return
    loop._combined_arms_counter = getattr(loop, "_combined_arms_counter", 0) + 1
    if loop._combined_arms_counter % 30 != 0:
        return

    armor = [unit for unit in units if unit.is_alive and _is_armor_unit(unit)]
    if not armor:
        return
    for unit in units:
        if not unit.is_alive:
            continue
        pos = unit.position.tile_coord
        supported = any(
            other.faction == unit.faction
            and max(
                abs(other.position.tile_coord.x - pos.x),
                abs(other.position.tile_coord.y - pos.y),
            )
            <= 4
            for other in armor
        )
        unit.scenario_accuracy_mod = 1.10 if supported else 1.0


# ============================================================================
# Twin stub loop helpers (mirrors TestPF12RuleConsumers in test_scenario_rules)
# ============================================================================


def _map(width: int = 20, height: int = 20) -> GameMap:
    return GameMap(
        id="trigger_test",
        name="Trigger Test Map",
        width=width,
        height=height,
        tile_grid=np.zeros((height, width), dtype=np.int8),
    )


def _objective(oid: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=oid,
        name=oid,
        position=(2, 2),
        radius=1,
        required=True,
        owner=None,
        points=10,
    )


def _make_unit(faction=Faction.ALLIES, x: int = 1, y: int = 1):
    return Unit(
        id=f"u_{faction.name}_{x}_{y}",
        name="Rifle",
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(
            primary_weapon_id="rifle",
            max_ammo=120,
            ammo_remaining=120,
            reserve_ammo=200,
        ),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(),
    )


def _make_tank(faction=Faction.ALLIES, x: int = 7, y: int = 5):
    return Unit(
        id="tank",
        name="Tank",
        faction=faction,
        unit_type=UnitType.TANK,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(primary_weapon_id="cannon", max_ammo=40, ammo_remaining=40),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(),
    )


def _make_twin_loops(
    rules: list[str],
    units_factory,
    objectives: list | None = None,
    owners: dict | None = None,
    air: str = "full",
    decay: float = 1.0,
    start_counter: int = 59,
):
    """Build two structurally identical stub loops (reference, migrated).

    Each loop gets its own unit set (via ``units_factory``) and its own
    bound helper lambdas (default-arg binding avoids late-binding closure bugs).
    """
    loops = []
    for _ in range(2):
        game_map = _map()
        game_map.objectives = list(objectives or [])
        loop = SimpleNamespace(
            state=SimpleNamespace(
                game_map=game_map,
                units=units_factory(),
                air_support_level=air,
                tick=0,
            ),
            _scenario_rules=ScenarioRules.from_map_data({"special_rules": rules}),
            _victory_manager=SimpleNamespace(get_vl_owners=lambda: dict(owners or {})),
            _scenario_data={
                "spawn_points": [
                    {"side": "allies", "position": [0, 0]},
                    {"side": "axis", "position": [19, 19]},
                ]
            },
            _logistics_counter=start_counter,
            _supply_decay=decay,
            _combined_arms_counter=0,
            _reinforcement_service=None,
            _deployment_manager=None,
        )
        loop._matching_vl_ids = lambda *needles, _l=loop: GameLoop._matching_vl_ids(_l, *needles)
        loop._vl_owner_map = lambda _l=loop: GameLoop._vl_owner_map(_l)
        loops.append(loop)
    return loops[0], loops[1]


class _RecordingReinforcementService:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    def update(self, **kwargs):
        self.kwargs = kwargs
        return []


# ============================================================================
# Logistics migration (corridor block / resupply / supply decay)
# ============================================================================


class TestLogisticsMigrationEquivalence:
    def test_supply_dwindling_matches_reference(self):
        reference_loop, migrated_loop = _make_twin_loops(
            ["supply_dwindling"], lambda: [_make_unit()]
        )
        _reference_update_logistics(reference_loop)
        GameLoopUpdatingMixin._update_logistics(migrated_loop)

        ref_unit = reference_loop.state.units[0]
        mig_unit = migrated_loop.state.units[0]
        assert mig_unit.weapon.reserve_ammo == ref_unit.weapon.reserve_ammo == 212
        assert migrated_loop._supply_decay == reference_loop._supply_decay == 0.85

    def test_supply_dwindling_zero_decay_matches_reference(self):
        reference_loop, migrated_loop = _make_twin_loops(
            ["supply_dwindling"], lambda: [_make_unit()], decay=0.0
        )
        _reference_update_logistics(reference_loop)
        GameLoopUpdatingMixin._update_logistics(migrated_loop)

        mig_unit = migrated_loop.state.units[0]
        ref_unit = reference_loop.state.units[0]
        assert mig_unit.weapon.reserve_ammo == ref_unit.weapon.reserve_ammo == 200
        assert migrated_loop._supply_decay == reference_loop._supply_decay == 0.0

    def test_corridor_lost_blocks_resupply_and_decay_in_both(self):
        reference_loop, migrated_loop = _make_twin_loops(
            ["corridor_must_remain_open", "supply_dwindling"],
            lambda: [_make_unit()],
            objectives=[_objective("vl_corridor")],
            owners={"vl_corridor": "axis"},
        )
        _reference_update_logistics(reference_loop)
        GameLoopUpdatingMixin._update_logistics(migrated_loop)

        mig_unit = migrated_loop.state.units[0]
        ref_unit = reference_loop.state.units[0]
        assert mig_unit.weapon.reserve_ammo == ref_unit.weapon.reserve_ammo == 200
        # A blocked pass must also skip the decay in both implementations.
        assert migrated_loop._supply_decay == reference_loop._supply_decay == 1.0

    def test_corridor_held_keeps_resupply_in_both(self):
        reference_loop, migrated_loop = _make_twin_loops(
            ["corridor_must_remain_open"],
            lambda: [_make_unit()],
            objectives=[_objective("vl_corridor")],
            owners={"vl_corridor": "allies"},
        )
        _reference_update_logistics(reference_loop)
        GameLoopUpdatingMixin._update_logistics(migrated_loop)

        mig_unit = migrated_loop.state.units[0]
        ref_unit = reference_loop.state.units[0]
        assert mig_unit.weapon.reserve_ammo == ref_unit.weapon.reserve_ammo == 212

    def test_air_support_gating_matches_reference(self):
        reference_loop, migrated_loop = _make_twin_loops(
            [], lambda: [_make_unit(), _make_unit(Faction.AXIS, 19, 18)], air="limited"
        )
        _reference_update_logistics(reference_loop)
        GameLoopUpdatingMixin._update_logistics(migrated_loop)

        # Limited air halves allied resupply (12 → 6); axis is unaffected (12).
        ref_ally, ref_axis = reference_loop.state.units
        mig_ally, mig_axis = migrated_loop.state.units
        assert mig_ally.weapon.reserve_ammo == ref_ally.weapon.reserve_ammo == 206
        assert mig_axis.weapon.reserve_ammo == ref_axis.weapon.reserve_ammo == 212

    def test_counter_gate_preserved_in_both(self):
        """The 60-tick logistics gate must behave identically."""
        reference_loop, migrated_loop = _make_twin_loops(
            [], lambda: [_make_unit()], start_counter=0
        )
        for _ in range(59):
            _reference_update_logistics(reference_loop)
            GameLoopUpdatingMixin._update_logistics(migrated_loop)
            assert migrated_loop.state.units[0].weapon.reserve_ammo == 200
            assert reference_loop.state.units[0].weapon.reserve_ammo == 200

        _reference_update_logistics(reference_loop)
        GameLoopUpdatingMixin._update_logistics(migrated_loop)
        assert migrated_loop.state.units[0].weapon.reserve_ammo == 212
        assert reference_loop.state.units[0].weapon.reserve_ammo == 212


# ============================================================================
# Scenario effects migration (fanatic defenders / combined arms)
# ============================================================================


class TestScenarioEffectsMigrationEquivalence:
    def test_fanatic_defenders_matches_reference(self):
        def units_factory():
            axis = _make_unit(Faction.AXIS, 19, 18)
            ally = _make_unit()
            axis.morale.value = 5
            ally.morale.value = 5
            return [axis, ally]

        reference_loop, migrated_loop = _make_twin_loops(["fanatic_defenders"], units_factory)
        _reference_update_scenario_effects(reference_loop)
        GameLoopUpdatingMixin._update_scenario_effects(migrated_loop)

        for ref_unit, mig_unit in zip(
            reference_loop.state.units, migrated_loop.state.units, strict=True
        ):
            assert mig_unit.morale.value == ref_unit.morale.value
        assert migrated_loop.state.units[0].morale.value == 30
        assert migrated_loop.state.units[1].morale.value == 5

    def test_combined_arms_matches_reference_at_tick_30(self):
        def units_factory():
            infantry = _make_unit(x=5, y=5)
            tank = _make_tank(x=7, y=5)
            return [infantry, tank]

        reference_loop, migrated_loop = _make_twin_loops(["combined_arms_bonus"], units_factory)
        for _ in range(30):
            _reference_update_scenario_effects(reference_loop)
            GameLoopUpdatingMixin._update_scenario_effects(migrated_loop)

        for ref_unit, mig_unit in zip(
            reference_loop.state.units, migrated_loop.state.units, strict=True
        ):
            assert mig_unit.scenario_accuracy_mod == ref_unit.scenario_accuracy_mod == 1.10

    def test_combined_arms_cadence_identical(self):
        def units_factory():
            infantry = _make_unit(x=5, y=5)
            tank = _make_tank(x=7, y=5)
            return [infantry, tank]

        reference_loop, migrated_loop = _make_twin_loops(["combined_arms_bonus"], units_factory)
        for tick in range(1, 61):
            _reference_update_scenario_effects(reference_loop)
            GameLoopUpdatingMixin._update_scenario_effects(migrated_loop)
            # The mod is a persistent value: applied at tick 30 and kept after.
            expected = 1.10 if tick >= 30 else 1.0
            for ref_unit, mig_unit in zip(
                reference_loop.state.units, migrated_loop.state.units, strict=True
            ):
                assert mig_unit.scenario_accuracy_mod == ref_unit.scenario_accuracy_mod == expected

    def test_combined_arms_absent_when_unsupported(self):
        reference_loop, migrated_loop = _make_twin_loops(
            ["combined_arms_bonus"], lambda: [_make_unit()]
        )
        for _ in range(30):
            _reference_update_scenario_effects(reference_loop)
            GameLoopUpdatingMixin._update_scenario_effects(migrated_loop)
        assert migrated_loop.state.units[0].scenario_accuracy_mod == 1.0

    def test_no_rules_is_noop_in_both(self):
        reference_loop, migrated_loop = _make_twin_loops([], lambda: [_make_unit()])
        _reference_update_scenario_effects(reference_loop)
        GameLoopUpdatingMixin._update_scenario_effects(migrated_loop)
        assert migrated_loop.state.units[0].scenario_accuracy_mod == 1.0
        assert migrated_loop._combined_arms_counter == 0


# ============================================================================
# Reinforcement delegate trigger
# ============================================================================


class TestReinforcementMigrationEquivalence:
    def _twin_loops_with_service(self, rules: list[str], owners: dict | None = None):
        loops = _make_twin_loops(rules, lambda: [], owners=owners)
        for loop in loops:
            loop._reinforcement_service = _RecordingReinforcementService()
            loop._deployment_manager = SimpleNamespace(create_reinforcement_unit=lambda **kw: None)
        return loops

    def test_limited_reinforcements_matches_reference(self):
        reference_loop, migrated_loop = self._twin_loops_with_service(["limited_reinforcements"])
        _reference_update_reinforcements(reference_loop)
        GameLoopUpdatingMixin._update_reinforcements(migrated_loop)
        ref_kwargs = reference_loop._reinforcement_service.kwargs
        mig_kwargs = migrated_loop._reinforcement_service.kwargs
        # Scalar keys only: the kwargs contain map/unit objects not comparable with ==.
        assert mig_kwargs["max_per_side"] == ref_kwargs["max_per_side"] == 2
        assert mig_kwargs["allowed_sides"] == ref_kwargs["allowed_sides"] is None
        assert mig_kwargs["tick"] == ref_kwargs["tick"] == 0

    def test_lz_rule_blocked_matches_reference(self):
        reference_loop, migrated_loop = self._twin_loops_with_service(
            ["lz_must_hold_for_reinforcements"], owners={"vl_lz": "axis"}
        )
        for loop in (reference_loop, migrated_loop):
            loop.state.game_map.objectives = [_objective("vl_lz")]
        _reference_update_reinforcements(reference_loop)
        GameLoopUpdatingMixin._update_reinforcements(migrated_loop)
        assert reference_loop._reinforcement_service.kwargs["allowed_sides"] == {"axis"}
        assert migrated_loop._reinforcement_service.kwargs["allowed_sides"] == {"axis"}

    def test_lz_rule_held_matches_reference(self):
        reference_loop, migrated_loop = self._twin_loops_with_service(
            ["lz_must_hold_for_reinforcements"], owners={"vl_lz": "allies"}
        )
        for loop in (reference_loop, migrated_loop):
            loop.state.game_map.objectives = [_objective("vl_lz")]
        _reference_update_reinforcements(reference_loop)
        GameLoopUpdatingMixin._update_reinforcements(migrated_loop)
        assert migrated_loop._reinforcement_service.kwargs["allowed_sides"] is None

    def test_due_entries_gate_on_due_aware_service(self):
        """A service exposing due_entries is gated on it (design §3 condition)."""

        class _DueAwareService(_RecordingReinforcementService):
            def __init__(self, due: list[dict]) -> None:
                super().__init__()
                self._due = due

            def due_entries(self, tick: int) -> list[dict]:
                return self._due

        reference_loop, migrated_loop = self._twin_loops_with_service([])
        reference_loop._reinforcement_service = _RecordingReinforcementService()
        migrated_loop._reinforcement_service = _DueAwareService(due=[])

        _reference_update_reinforcements(reference_loop)
        GameLoopUpdatingMixin._update_reinforcements(migrated_loop)
        # Nothing due → trigger never delegates → update not called.
        assert migrated_loop._reinforcement_service.kwargs is None

        migrated_loop._reinforcement_service._due = [{"template_id": "t", "side": "allies"}]
        GameLoopUpdatingMixin._update_reinforcements(migrated_loop)
        assert migrated_loop._reinforcement_service.kwargs is not None
        assert migrated_loop._reinforcement_service.kwargs["tick"] == 0


# ============================================================================
# Trigger table observability
# ============================================================================


def _trigger_stats(loop) -> dict[str, tuple[int, int | None]]:
    return {
        trigger_id: (count, last)
        for trigger_id, count, last in loop._trigger_system.list_triggers()
    }


class TestTriggerTableObservability:
    def test_logistics_pass_fires_expected_triggers(self):
        _reference_loop, migrated_loop = _make_twin_loops(
            ["supply_dwindling"], lambda: [_make_unit()]
        )
        GameLoopUpdatingMixin._update_logistics(migrated_loop)
        stats = _trigger_stats(migrated_loop)
        assert stats["corridor_supply_block"] == (0, None)
        assert stats["supply_resupply_pass"][0] == 1
        assert stats["supply_dwindling_decay"][0] == 1

    def test_corridor_block_trigger_observed(self):
        _reference_loop, migrated_loop = _make_twin_loops(
            ["corridor_must_remain_open"],
            lambda: [_make_unit()],
            objectives=[_objective("vl_corridor")],
            owners={"vl_corridor": "axis"},
        )
        GameLoopUpdatingMixin._update_logistics(migrated_loop)
        stats = _trigger_stats(migrated_loop)
        assert stats["corridor_supply_block"] == (1, 1)
        assert stats["supply_resupply_pass"] == (0, None)
        assert stats["supply_dwindling_decay"] == (0, None)

    def test_scenario_group_only_ticks_scenario_triggers(self):
        _reference_loop, migrated_loop = _make_twin_loops(
            ["fanatic_defenders"], lambda: [_make_unit(Faction.AXIS, 19, 18)]
        )
        migrated_loop.state.units[0].morale.value = 5

        GameLoopUpdatingMixin._update_logistics(migrated_loop)  # logistics group only
        assert _trigger_stats(migrated_loop)["fanatic_defenders_floor"] == (0, None)

        GameLoopUpdatingMixin._update_scenario_effects(migrated_loop)  # scenario group
        assert _trigger_stats(migrated_loop)["fanatic_defenders_floor"] == (1, 2)

    def test_reinforcement_group_skipped_by_other_groups(self):
        _reference_loop, migrated_loop = _make_twin_loops([], lambda: [])
        service = _RecordingReinforcementService()
        migrated_loop._reinforcement_service = service
        migrated_loop._deployment_manager = SimpleNamespace(
            create_reinforcement_unit=lambda **kw: None
        )

        GameLoopUpdatingMixin._update_scenario_effects(migrated_loop)
        GameLoopUpdatingMixin._update_logistics(migrated_loop)
        assert service.kwargs is None  # reinforcement trigger not ticked yet

        GameLoopUpdatingMixin._update_reinforcements(migrated_loop)
        assert service.kwargs is not None


@pytest.mark.integration
class TestRealGameLoopWiring:
    """A real GameLoop carries the pre-built trigger table and injected director."""

    def test_assembler_builds_trigger_system(self, pygame_display):
        import pygame

        from pycc2.domain.value_objects.vec2 import Vec2
        from pycc2.infrastructure.events.event_bus import EventBus
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
        from pycc2.presentation.rendering.window_config import WindowManager
        from pycc2.services.game_loop_types import GameState

        if not pygame.font.get_init():
            pygame.font.init()

        game_map = _map(16, 16)
        camera = Camera(position=Vec2(0, 0), viewport_width=64, viewport_height=64)
        state = GameState(game_map=game_map, units=[], camera=camera)
        loop = GameLoop(
            renderer=SpriteRenderer(),
            window_manager=Mock(spec=WindowManager),
            event_bus=EventBus(),
            state=state,
            use_full_hud=False,
        )

        assert loop._trigger_system is not None
        trigger_ids = {
            trigger_id for trigger_id, _count, _last in loop._trigger_system.list_triggers()
        }
        assert trigger_ids == {
            "corridor_supply_block",
            "supply_resupply_pass",
            "supply_dwindling_decay",
            "fanatic_defenders_floor",
            "combined_arms_bonus",
            "reinforcement_due",
        }
