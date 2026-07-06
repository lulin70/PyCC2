"""Interface contract tests for cross-module boundaries (TD-035).

These tests freeze the public surface area of core domain components that are
consumed by the campaign persistence layer (``CampaignPersistenceManager.
apply_inheritance_to_units``). They exist to prevent the class of regression
documented in TD-022 / TD-035 where the consumer (campaign_persistence) and
the supplier (HealthComponent/MoraleComponent/StateMachine/VeterancyComponent)
drifted apart on attribute and method names.

Why contract tests (not unit tests):
    ``tests/unit/test_campaign_persistence_io.py::TestApplyInheritanceBugs``
    documents four historical interface mismatches using ``pytest.raises(
    AttributeError)``. Those tests record the *failure* mode; the tests in
    this file record the *contract* — the positive surface area the consumer
    relies on. Together they form a consumer-driven contract:

        supplier surface  →  consumer usage  →  contract test
        -------------------------------------------------------
        HealthComponent.hp / max_hp / _update_state
                           →  apply_inheritance_to_units L297-299
                           →  TestHealthComponentContract
        MoraleComponent.value
                           →  apply_inheritance_to_units L303
                           →  TestMoraleComponentContract
        StateMachine.force_transition
                           →  apply_inheritance_to_units L322
                           →  TestStateMachineContract
        VeterancyComponent.add_xp
                           →  apply_inheritance_to_units L311
                           →  TestVeterancyComponentContract

    The final class (``TestApplyInheritanceConsumerContract``) is an
    end-to-end contract: it instantiates a *real* ``Unit`` (not a fake) and
    asserts that ``apply_inheritance_to_units`` runs without raising
    ``AttributeError`` — i.e. the consumer and supplier surfaces are
    mutually consistent today.

Real components, no mocks:
    Per the project testing philosophy, all components instantiated here are
    the real production classes. No Mock/Fake/MagicMock is used for the
    subjects under contract; only ``tmp_path`` is a pytest fixture.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Headless pygame guard — Unit import chain pulls in pygame transitively.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.components.health_component import HealthComponent, HealthState
from pycc2.domain.components.morale_component import MoraleComponent, MoraleState
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.veterancy_component import VeterancyComponent, VeteranRank
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitState, UnitType
from pycc2.domain.state_machine import StateMachine, TransitionError
from pycc2.domain.systems.campaign_persistence import (
    BattleOutcome,
    BattleResult,
    CampaignPersistenceManager,
    CampaignProgress,
    UnitBattleState,
)
from pycc2.domain.value_objects.tile_coord import TileCoord

# ========================================================================
# HealthComponent contract
# ========================================================================


class TestHealthComponentContract:
    """Freeze the public surface consumed by apply_inheritance_to_units.

    Consumer (campaign_persistence.py L297-299, L316-317):
        unit.health_component.hp = ...
        unit.health_component.max_hp   (read)
        unit.health_component._update_state()
    """

    def test_constructible_with_hp_and_max_hp(self):
        """Contract: HealthComponent(hp, max_hp) constructs successfully."""
        hc = HealthComponent(hp=100, max_hp=100)
        assert hc.hp == 100
        assert hc.max_hp == 100

    def test_hp_field_is_writable(self):
        """Contract: hp is a writable field (consumer assigns to it)."""
        hc = HealthComponent(hp=100, max_hp=100)
        hc.hp = 50
        assert hc.hp == 50

    def test_max_hp_field_is_writable(self):
        """Contract: max_hp is a writable field."""
        hc = HealthComponent(hp=50, max_hp=100)
        hc.max_hp = 150
        assert hc.max_hp == 150

    def test_current_hp_is_readonly_property(self):
        """Contract: current_hp is a read-only @property (legacy alias for hp).

        Documented in TestApplyInheritanceBugs.test_real_health_component_current_hp_is_readonly.
        The consumer must assign to ``hp`` directly, never to ``current_hp``.
        """
        hc = HealthComponent(hp=100, max_hp=100)
        assert hc.current_hp == hc.hp
        with pytest.raises(AttributeError):
            hc.current_hp = 50

    def test_update_state_method_exists(self):
        """Contract: _update_state() is callable (consumer invokes it after hp change)."""
        hc = HealthComponent(hp=100, max_hp=100)
        hc.hp = 10
        hc._update_state()
        assert hc.state == HealthState.CRITICAL

    def test_take_damage_returns_int(self):
        """Contract: take_damage(amount) -> int (actual HP lost)."""
        hc = HealthComponent(hp=100, max_hp=100)
        lost = hc.take_damage(30)
        assert isinstance(lost, int)
        assert lost == 30
        assert hc.hp == 70

    def test_heal_returns_int(self):
        """Contract: heal(amount) -> int (actual HP restored)."""
        hc = HealthComponent(hp=50, max_hp=100)
        restored = hc.heal(20)
        assert isinstance(restored, int)
        assert restored == 20
        assert hc.hp == 70

    def test_is_alive_property_exists(self):
        """Contract: is_alive is a readable boolean property."""
        hc = HealthComponent(hp=100, max_hp=100)
        assert hc.is_alive is True
        hc.take_damage(100)
        assert hc.is_alive is False

    def test_slots_blocks_arbitrary_attrs(self):
        """Contract: slots=True blocks new attributes (prevents silent typos)."""
        hc = HealthComponent(hp=100, max_hp=100)
        with pytest.raises(AttributeError):
            hc.tyop_field = 42


# ========================================================================
# MoraleComponent contract
# ========================================================================


class TestMoraleComponentContract:
    """Freeze the public surface consumed by apply_inheritance_to_units.

    Consumer (campaign_persistence.py L303):
        unit.morale_component.value = ...
    """

    def test_constructible_with_value(self):
        """Contract: MoraleComponent(value) constructs successfully."""
        mc = MoraleComponent(value=80)
        assert mc.value == 80

    def test_value_field_is_writable(self):
        """Contract: value is a writable field (consumer assigns to it)."""
        mc = MoraleComponent(value=80)
        mc.value = 50
        assert mc.value == 50

    def test_no_current_morale_attribute(self):
        """Contract: there is NO 'current_morale' attribute.

        Documented in TestApplyInheritanceBugs.test_real_morale_component_has_no_current_morale.
        The consumer must assign to ``value``, never to ``current_morale``.
        """
        mc = MoraleComponent(value=80)
        assert not hasattr(mc, "current_morale")
        with pytest.raises(AttributeError):
            mc.current_morale = 50

    def test_apply_delta_method_exists(self):
        """Contract: apply_delta(delta) mutates value."""
        mc = MoraleComponent(value=80)
        mc.apply_delta(-10)
        assert mc.value == 70

    def test_state_property_exists(self):
        """Contract: state is a readable MoraleState property."""
        mc = MoraleComponent(value=80)
        assert isinstance(mc.state, MoraleState)
        assert mc.state == MoraleState.RALLIED

    def test_is_combat_effective_property_exists(self):
        """Contract: is_combat_effective is a readable boolean property."""
        mc = MoraleComponent(value=80)
        assert mc.is_combat_effective is True

    def test_start_and_stop_routing_methods_exist(self):
        """Contract: start_routing() and stop_routing() are callable."""
        mc = MoraleComponent(value=80)
        mc.start_routing()
        assert mc.state == MoraleState.ROUTING
        mc.stop_routing()
        assert mc.state != MoraleState.ROUTING

    def test_slots_blocks_arbitrary_attrs(self):
        """Contract: slots=True blocks new attributes."""
        mc = MoraleComponent(value=80)
        with pytest.raises(AttributeError):
            mc.tyop_field = 42


# ========================================================================
# StateMachine contract
# ========================================================================


class TestStateMachineContract:
    """Freeze the public surface consumed by apply_inheritance_to_units.

    Consumer (campaign_persistence.py L322):
        unit.state_machine.force_transition(UnitState.DEAD)
    """

    def test_constructible_with_initial_and_transitions(self):
        """Contract: StateMachine(initial, transitions) constructs successfully."""
        sm = StateMachine(
            initial=UnitState.IDLE,
            transitions={UnitState.IDLE: {UnitState.DEAD}},
        )
        assert sm.current == UnitState.IDLE

    def test_force_transition_method_exists(self):
        """Contract: force_transition(target) is callable (consumer uses it)."""
        sm = StateMachine(
            initial=UnitState.IDLE,
            transitions={UnitState.IDLE: {UnitState.DEAD}},
        )
        sm.force_transition(UnitState.DEAD)
        assert sm.current == UnitState.DEAD

    def test_no_force_state_method(self):
        """Contract: there is NO 'force_state' method.

        Documented in TestApplyInheritanceBugs.test_real_state_machine_has_no_force_state.
        The consumer must call ``force_transition``, never ``force_state``.
        """
        sm = StateMachine(
            initial=UnitState.IDLE,
            transitions={UnitState.IDLE: {UnitState.DEAD}},
        )
        assert not hasattr(sm, "force_state")
        with pytest.raises(AttributeError):
            sm.force_state(UnitState.DEAD)

    def test_current_property_is_readonly(self):
        """Contract: current is a read-only @property."""
        sm = StateMachine(
            initial=UnitState.IDLE,
            transitions={UnitState.IDLE: {UnitState.DEAD}},
        )
        with pytest.raises(AttributeError):
            sm.current = UnitState.DEAD

    def test_history_property_is_readonly(self):
        """Contract: history is a read-only @property."""
        sm = StateMachine(
            initial=UnitState.IDLE,
            transitions={UnitState.IDLE: {UnitState.DEAD}},
        )
        with pytest.raises(AttributeError):
            sm.history = []

    def test_try_transition_returns_bool(self):
        """Contract: try_transition(target) -> bool (True on success)."""
        sm = StateMachine(
            initial=UnitState.IDLE,
            transitions={UnitState.IDLE: {UnitState.DEAD}},
        )
        assert sm.try_transition(UnitState.DEAD) is True
        assert sm.current == UnitState.DEAD

    def test_transition_or_raise_raises_on_invalid(self):
        """Contract: transition_or_raise raises TransitionError on invalid target."""
        sm = StateMachine(
            initial=UnitState.IDLE,
            transitions={UnitState.IDLE: {UnitState.DEAD}},
        )
        with pytest.raises(TransitionError):
            sm.transition_or_raise(UnitState.MOVING)

    def test_reset_method_exists(self):
        """Contract: reset(state=None) clears history and optionally sets state."""
        sm = StateMachine(
            initial=UnitState.IDLE,
            transitions={UnitState.IDLE: {UnitState.DEAD}},
        )
        sm.force_transition(UnitState.DEAD)
        sm.reset(UnitState.IDLE)
        assert sm.current == UnitState.IDLE
        assert sm.history == []


# ========================================================================
# VeterancyComponent contract
# ========================================================================


class TestVeterancyComponentContract:
    """Freeze the public surface consumed by apply_inheritance_to_units.

    Consumer (campaign_persistence.py L311):
        unit.veterancy_component.add_xp(prev_state.experience)
    """

    def test_constructible_with_defaults(self):
        """Contract: VeterancyComponent() constructs with all defaults."""
        vc = VeterancyComponent()
        assert vc.xp == 0
        assert vc.kills == 0
        assert vc.battles_survived == 0

    def test_add_xp_returns_bool(self):
        """Contract: add_xp(amount) -> bool (True if rank changed)."""
        vc = VeterancyComponent()
        # 0 xp -> 100 xp promotes RECRUIT -> REGULAR
        rank_changed = vc.add_xp(100)
        assert isinstance(rank_changed, bool)
        assert rank_changed is True
        assert vc.rank == VeteranRank.REGULAR

    def test_add_xp_below_threshold_returns_false(self):
        """Contract: add_xp below promotion threshold returns False."""
        vc = VeterancyComponent()
        rank_changed = vc.add_xp(50)
        assert rank_changed is False
        assert vc.rank == VeteranRank.RECRUIT

    def test_rank_property_is_readonly(self):
        """Contract: rank is a read-only @property."""
        vc = VeterancyComponent()
        with pytest.raises(AttributeError):
            vc.rank = VeteranRank.ELITE

    def test_xp_field_is_writable(self):
        """Contract: xp is a writable field (add_xp mutates it)."""
        vc = VeterancyComponent()
        vc.xp = 50
        assert vc.xp == 50

    def test_record_kill_method_exists(self):
        """Contract: record_kill(xp_reward=15) -> bool."""
        vc = VeterancyComponent()
        result = vc.record_kill()
        assert isinstance(result, bool)
        assert vc.kills == 1

    def test_record_battle_survived_method_exists(self):
        """Contract: record_battle_survived(xp_bonus=25) -> bool."""
        vc = VeterancyComponent()
        result = vc.record_battle_survived()
        assert isinstance(result, bool)
        assert vc.battles_survived == 1

    def test_slots_blocks_arbitrary_attrs(self):
        """Contract: slots=True blocks new attributes."""
        vc = VeterancyComponent()
        with pytest.raises(AttributeError):
            vc.tyop_field = 42


# ========================================================================
# CampaignPersistence serialization contract
# ========================================================================


class TestCampaignPersistenceSerializationContract:
    """Freeze the save/load round-trip contract for campaign_persistence.

    Consumer (campaign_persistence.py L322, save_campaign_progress /
    load_campaign_progress): BattleOutcome must survive a save/load cycle
    as an enum (not a string), otherwise calculate_reinforcement_bonus
    gives incorrect results.
    """

    def test_battle_outcome_survives_save_load_roundtrip(self, tmp_path: Path):
        """Contract: BattleOutcome is reconstructed as enum after save/load.

        Documented in TestApplyInheritanceBugs.test_battle_outcome_reconstructed_after_load
        as the fourth interface-mismatch bug class.
        """
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="north",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
        )
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        progress.add_battle_result(br)
        mgr.save_campaign_progress("c1", progress)

        loaded = mgr.load_campaign_progress("c1")
        assert loaded is not None
        loaded_outcome = loaded.battle_results[0].outcome
        assert isinstance(loaded_outcome, BattleOutcome)
        assert loaded_outcome == BattleOutcome.ALLIED_VICTORY

    def test_all_battle_outcomes_survive_roundtrip(self, tmp_path: Path):
        """Contract: every BattleOutcome enum member survives save/load."""
        outcomes = list(BattleOutcome)
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c_all", current_operation_id="op1")
        for i, outcome in enumerate(outcomes):
            br = BattleResult(
                battle_id=f"b{i}",
                operation_id="op1",
                sector="s",
                day=i + 1,
                outcome=outcome,
            )
            progress.add_battle_result(br)
        mgr.save_campaign_progress("c_all", progress)

        loaded = mgr.load_campaign_progress("c_all")
        assert loaded is not None
        assert len(loaded.battle_results) == len(outcomes)
        for original, loaded_br in zip(outcomes, loaded.battle_results, strict=False):
            assert isinstance(loaded_br.outcome, BattleOutcome)
            assert loaded_br.outcome == original

    def test_unit_battle_state_survives_roundtrip(self, tmp_path: Path):
        """Contract: UnitBattleState fields survive save/load."""
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        units = [
            UnitBattleState(
                unit_id="u1",
                unit_template_id="tmpl_a",
                faction="allies",
                is_alive=True,
                current_hp=70.0,
                max_hp=100.0,
                morale=60.0,
                experience=100,
                kills=2,
                ammo_remaining={"primary": 20},
                status="active",
            ),
        ]
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            unit_states=units,
        )
        progress = CampaignProgress(campaign_id="c_unit", current_operation_id="op1")
        progress.add_battle_result(br)
        mgr.save_campaign_progress("c_unit", progress)

        loaded = mgr.load_campaign_progress("c_unit")
        assert loaded is not None
        loaded_unit = loaded.current_unit_states[0]
        assert loaded_unit.unit_id == "u1"
        assert loaded_unit.unit_template_id == "tmpl_a"
        assert loaded_unit.faction == "allies"
        assert loaded_unit.is_alive is True
        assert loaded_unit.current_hp == 70.0
        assert loaded_unit.max_hp == 100.0
        assert loaded_unit.morale == 60.0
        assert loaded_unit.experience == 100
        assert loaded_unit.kills == 2
        assert loaded_unit.ammo_remaining == {"primary": 20}
        assert loaded_unit.status == "active"


# ========================================================================
# apply_inheritance_to_units end-to-end consumer contract
# ========================================================================


def _make_real_unit(unit_id: str, hp: int = 100, morale: int = 85) -> Unit:
    """Build a real Unit with all components apply_inheritance_to_units touches."""
    return Unit(
        id=unit_id,
        name=f"Unit {unit_id}",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=hp, max_hp=100),
        morale=MoraleComponent(value=morale),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(3, 3)),
        vision=VisionComponent(range_tiles=5),
        veterancy=VeterancyComponent(),
    )


class TestApplyInheritanceConsumerContract:
    """End-to-end contract: apply_inheritance_to_units works on real Unit.

    This is the contract that TD-035 demands: instantiate the REAL domain
    components (no fakes, no duck-typing) and assert the consumer (campaign
    persistence) can drive them without raising AttributeError.

    If this test passes, the supplier surface (HealthComponent.hp /
    MoraleComponent.value / StateMachine.force_transition /
    VeterancyComponent.add_xp) and the consumer surface
    (apply_inheritance_to_units L297-322) are mutually consistent.

    If it fails with AttributeError, an interface drift has occurred and the
    specific failing line in apply_inheritance_to_units identifies the
    broken contract.
    """

    def test_apply_inheritance_to_alive_unit(self, tmp_path: Path):
        """Contract: alive prev_state → unit.hp/morale/veterancy updated, no error."""
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        prev_state = UnitBattleState(
            unit_id="u1",
            unit_template_id="u1",  # matches unit.id (Unit has no unit_template_id)
            faction="allies",
            is_alive=True,
            current_hp=70.0,
            max_hp=100.0,
            morale=60.0,
            experience=100,
            ammo_remaining={"primary": 20},
        )
        br = BattleResult(
            battle_id="b1",
            operation_id="op1",
            sector="north",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            unit_states=[prev_state],
        )
        progress = CampaignProgress(campaign_id="c1", current_operation_id="op1")
        progress.add_battle_result(br)

        unit = _make_real_unit("u1", hp=100, morale=85)
        original_xp = unit.veterancy.xp if unit.veterancy else 0

        # Must not raise AttributeError.
        updated = mgr.apply_inheritance_to_units(progress, [unit])

        assert updated is not None
        # HP scaled by ratio: prev 70/100 → new hp = 100 * 0.7 = 70
        assert unit.health.hp == 70
        # Morale: prev 60 + recovery. total_battles_completed=1 after add_battle_result,
        # so recovery = min(20, 10 + 1*2) = 12 → 60 + 12 = 72.
        assert unit.morale.value == 72
        # Veterancy: add_xp(100) called
        assert unit.veterancy is not None
        assert unit.veterancy.xp == original_xp + 100

    def test_apply_inheritance_to_dead_unit(self, tmp_path: Path):
        """Contract: dead prev_state → unit.hp=0, state_machine.force_transition(DEAD)."""
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        prev_state = UnitBattleState(
            unit_id="u_dead",
            unit_template_id="u_dead",
            faction="allies",
            is_alive=False,
            current_hp=0.0,
            max_hp=100.0,
            morale=0.0,
        )
        br = BattleResult(
            battle_id="b_dead",
            operation_id="op1",
            sector="s",
            day=1,
            outcome=BattleOutcome.AXIS_VICTORY,
            unit_states=[prev_state],
        )
        progress = CampaignProgress(campaign_id="c_dead", current_operation_id="op1")
        progress.add_battle_result(br)

        unit = _make_real_unit("u_dead", hp=100, morale=85)
        assert unit.state_machine.current == UnitState.IDLE

        # Must not raise AttributeError.
        updated = mgr.apply_inheritance_to_units(progress, [unit])

        assert updated is not None
        assert unit.health.hp == 0
        assert unit.state_machine.current == UnitState.DEAD

    def test_apply_inheritance_no_match_does_not_raise(self, tmp_path: Path):
        """Contract: unit with no matching prev_state is skipped, no error."""
        mgr = CampaignPersistenceManager(base_dir=tmp_path)
        progress = CampaignProgress(campaign_id="c_empty", current_operation_id="op1")
        # No battle results → no prev_state for any unit.

        unit = _make_real_unit("u_no_match", hp=100, morale=85)

        # Must not raise.
        updated = mgr.apply_inheritance_to_units(progress, [unit])

        assert updated is not None
        # Unit unchanged.
        assert unit.health.hp == 100
        assert unit.morale.value == 85
